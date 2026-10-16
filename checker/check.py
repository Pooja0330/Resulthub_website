# GoResultHub checker: official exam notices, controlled alert delivery, and source health diagnostics.

import os
import re
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urljoin, parse_qsl, urlencode, urlunparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import certifi
from xml.sax.saxutils import escape as xml_escape
import feedparser
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
TOKEN = os.getenv("TG_TOKEN", "").strip()
ADMIN = os.getenv("TG_ADMIN", "").strip()
CHANNEL = os.getenv("TG_CHANNEL", "").strip()
TG_RATE_LIMITED = False

TIMEOUT = max(6, min(int(os.getenv("SOURCE_TIMEOUT_SECONDS", "12")), 20))
# Lower concurrency reduces connection pressure against slow government portals.
WORKERS = max(1, min(int(os.getenv("SOURCE_WORKERS", "8")), 8))
MAX_NEW_PER_SOURCE = max(1, min(int(os.getenv("MAX_NEW_PER_SOURCE", "5")), 20))
MAX_AGE_DAYS = 90

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 GoResultHubMonitor/3.1",
    "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.7",
}

RULES = [
    ("result", re.compile(
        r"\b(result|results|scorecards?|score cards?|marks list|rank list|rank card)\b", re.I)),
    ("merit_list", re.compile(
        r"\b(merit list|final selection|selected candidates|qualified candidates|"
        r"provisional selection|selection list|final panel|allotment list|"
        r"provisional panel|shortlisted candidates)\b", re.I)),
    ("cutoff", re.compile(
        r"\b(cut.?off marks?|qualifying marks?)\b", re.I)),
    ("admit_card", re.compile(
        r"\b(admit cards?|hall tickets?|call letters?|exam city intimation|"
        r"city intimation slip|download your admit card)\b", re.I)),
    ("answer_key", re.compile(
        r"\b(answer keys?|response sheets?|objection tracker|challenge answer key)\b", re.I)),
    ("exam_schedule", re.compile(
        r"\b(exam date|examination date|exam schedule|examination schedule|"
        r"date sheet|exam calendar|exam postponement|exam rescheduled|"
        r"examination postponed|examination rescheduled|interview schedule|"
        r"written examination schedule|revised exam date)\b", re.I)),
    ("notification", re.compile(
        r"\b(exam notification|examination notification|recruitment notification|"
        r"recruitment advertisement|vacancy notification|information bulletin|"
        r"application dates|registration opens|apply online|online application|"
        r"application notice|applications invited|invites applications|"
        r"invited applications|application invited|inviting online application|"
        r"recruitment of|recruitment to|recruitment for|recruitment drive|"
        r"recruitment process|notification for recruitment|advertisement no\.?|"
        r"advertisement for|advertisement dated|recruitment notice|"
        r"vacancies for|vacancy for|last date to apply|application deadline|"
        r"corrigendum|addendum|extension of last date|revised vacancy|"
        r"additional vacancies|selection process for|selection list for recruitment|"
        r"preliminary examination|prelims examination|main examination|mains examination|"
        r"preliminary test|preliminary exam|mains exam|main written examination|"
        r"civil services \(preliminary\)|civil services \(main\)|state services \(preliminary\)|"
        r"state services \(main\))\b", re.I)),
]


SKIP = re.compile(
    r"\b(tender|quotation|procurement|request for proposal|request for quotation|"
    r"expression of interest|vendor registration|agency appointment|"
    r"public relations|social media agency|media agency|privacy policy|"
    r"photo gallery|annual report|media advisory|holiday list|meeting notice|"
    r"investor presentation|corporate announcement|"
    r"conference|workshop|symposium|seminar|research proposal|research grant|"
    r"inter college migration|inter-college migration|printing and supply|"
    r"purchase of books|faculty research programme|faculty research program|"
    r"glow dental clinic|sports meet|cultural fest|cultural festival)\b", re.I
)

NAV_TITLE = re.compile(
    r"^(home|result|results|recruitment|careers?|advertisements?|"
    r"notifications?|notices?|latest news|read more|click here|"
    r"view all|view more|recruitment calendar|stages of recruitment|"
    r"reporting vacancies|detailed advertisement|call letters?|admit cards?|"
    r"answer keys?|cut.?off marks?|current openings|recruitment results|"
    r"recruitment archives|latest updates)$", re.I
)


def path(name):
    return ROOT / name


def load_json(name, default):
    try:
        with path(name).open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(name, value):
    target = path(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, target)


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def extract_notice_date(text):
    """Return a date only when the official listing labels it as a notice/upload date."""
    value = " ".join(str(text or "").split())
    date_pattern = (
        r"(\d{1,2}[./-]\d{1,2}[./-]\d{4}|"
        r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|"
        r"\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4})"
    )
    match = re.search(
        r"\b(?:date of upload|upload date|notice date|notification date|"
        r"published on|posted on|updated on|uploaded on|issued on|dated)\s*[:\-]?\s*"
        + date_pattern, value, re.I,
    )
    if not match:
        return ""
    raw = match.group(1).strip()
    for fmt in (
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%m/%d/%Y", "%m-%d-%Y",
        "%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y",
        "%d %b %Y", "%d %B %Y", "%d %b, %Y", "%d %B, %Y",
    ):
        try:
            return datetime.strptime(raw, fmt).strftime("%d %b %Y")
        except ValueError:
            continue
    return raw


def exam_year_from_title(title):
    """Return a year only when explicitly present in the notice title."""
    match = re.search(r"\b(20\d{2})\b", str(title or ""))
    return match.group(1) if match else ""


def format_notice_date(value):
    """Normalize a known source date; never substitute today's date."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    for fmt in (
        "%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y",
        "%d %b, %Y", "%d %B, %Y",
    ):
        try:
            return datetime.strptime(raw, fmt).strftime("%d %b %Y")
        except ValueError:
            continue
    try:
        from email.utils import parsedate_to_datetime
        parsed = parsedate_to_datetime(raw)
        return parsed.strftime("%d %b %Y") if parsed else ""
    except (TypeError, ValueError, OverflowError):
        return ""


def host_allowed(url, hosts):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host:
            return False
        if isinstance(hosts, str):
            hosts = [hosts]
        return any(
            host == str(h).lower()
            or host.endswith("." + str(h).lower())
            for h in hosts if h
        )
    except Exception:
        return False


def classify(title):
    if not title or SKIP.search(title) or NAV_TITLE.fullmatch(title.strip()):
        return None
    for category, pattern in RULES:
        if pattern.search(title):
            return category
    return None


def infer_exam_category(title="", source_name="", source_id="", state=""):
    """Map notices to stable website filters instead of source-name labels."""
    text_value = " ".join(str(v or "") for v in (source_id, source_name, title, state)).lower()
    source = str(source_id or "").lower()
    name = str(source_name or "").lower()
    if source.startswith(("rrb-", "rrc-", "rrcb")) or "railway recruitment" in name or re.search(r"\b(rrb|rrc|ntpc|group d|assistant loco pilot|alp)\b", text_value):
        return "Railways"
    if source in {"ibps", "ibps-recent-updates", "ibps-po-mt", "sbi-careers", "sbi-current-openings", "sbi-recruitment-results", "rbi-opportunities"} or re.search(r"\b(ibps|state bank of india|sbi careers|reserve bank of india|rbi|banking|lic|insurance regulatory|niacl|uiic|pfrda)\b", text_value):
        return "Banking"
    if source.startswith("ssc") or "staff selection commission" in name or re.search(r"\bssc (cgl|chsl|mts|gd|stenographer)\b", text_value):
        return "SSC / Central Recruitment"
    if source.startswith("upsc") or "union public service commission" in name or re.search(r"\bupsc\b", text_value):
        return "UPSC / Central Recruitment"
    # Split high-demand exam families and preliminary/main stages.
    if re.search(r"\bjee\s*advanced\b", text_value) or source.startswith("jeeadv"):
        return "JEE Advanced"
    if re.search(r"\bjee\s*(main|mains)\b", text_value) or source.startswith("jeemain"):
        return "JEE Main"
    if re.search(r"\bneet\s*(pg|post.?graduate)\b", text_value) or source.startswith("neet-pg"):
        return "NEET PG"
    if re.search(r"\bneet\s*(ug|under.?graduate)\b", text_value) or source == "neet":
        return "NEET UG"
    if ("upsc" in text_value or source.startswith("upsc")) and re.search(r"\b(main|mains)\b", text_value):
        return "UPSC Mains"
    if ("upsc" in text_value or source.startswith("upsc")) and re.search(r"\b(preliminary|prelims)\b", text_value):
        return "UPSC Prelims"
    if re.search(r"\b(psc|public service commission|state services|state service|mpsc|uppsc|bpsc|rpsc|kpsc|tnpsc|opsc|gpsc|hpsc|jpsc|wbpsc)\b", text_value) and re.search(r"\b(main|mains)\b", text_value):
        return "State PSC Mains"
    if re.search(r"\b(psc|public service commission|state services|state service|mpsc|uppsc|bpsc|rpsc|kpsc|tnpsc|opsc|gpsc|hpsc|jpsc|wbpsc)\b", text_value) and re.search(r"\b(preliminary|prelims)\b", text_value):
        return "State PSC Prelims"
    if source.startswith(("nta", "jee", "neet", "cuet", "ugcnet", "gate")) or re.search(r"\b(nta|jee|neet|cuet|gate|ugc net|csir net|entrance exam)\b", text_value):
        return "Entrance & Eligibility"
    if re.search(r"\b(school board|board of school education|school education board|board of secondary education|secondary education board|cbse|cisce|nios|class 10|class 12|sslc|hsc|madhyamik)\b", text_value):
        return "School Board Results"
    if re.search(r"\b(police|constable|slprb|prpb)\b", text_value):
        return "State Recruitment / Police"
    if re.search(r"\b(ctet|tet|teacher|teaching|kvs|nvs|school service commission)\b", text_value):
        return "Teaching / Eligibility"
    if re.search(r"\b(defence|defense|army|navy|air force|agniveer|coast guard|crpf|bsf|cisf|itbp|ssb)\b", text_value):
        return "Defence"
    if re.search(r"\b(psc|public service commission|state service commission|technical service commission|direct recruitment commission|staff selection commission|subordinate services selection commission|recruitment board)\b", text_value):
        return "State PSC / Recruitment"
    if source.startswith(("icai", "icsi", "icmai", "nmc")) or re.search(r"\b(icai|icsi|icmai|chartered accountant|company secretary|medical commission)\b", text_value):
        return "Professional Exams"
    if source.startswith(("kvs", "nvs", "ctet")) or re.search(r"\b(kvs|nvs|ctet|tet|teacher|teaching)\b", text_value):
        return "Teaching / Eligibility"
    if source.startswith(("mahresult", "tnresults", "keralaresults", "wbresults", "karnataka-results", "odisha-results", "ap-results", "telangana-results")):
        return "School Board Results"
    if source.startswith(("nabard", "niacl", "uiic", "lic", "pfrda")) or re.search(r"\b(nabard|new india assurance|uiic|lic|pfrda)\b", text_value):
        return "Banking"
    if source.startswith(("epfindia", "indiapost")):
        return "UPSC / Central Recruitment"
    if state:
        return "State PSC / Recruitment"
    return "UPSC / Central Recruitment"


def normalize_notice_url(url):
    """Normalize tracking noise without collapsing distinct CMS notice URLs."""
    try:
        parsed = urlparse(str(url).strip())
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            return ""
        host = parsed.hostname.lower()
        if host.startswith("www."):
            host = host[4:]
        path_value = re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/"
        # Keep content-identifying query parameters (e.g. articleid); remove only
        # common analytics/click-tracking parameters.
        query_pairs = []
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            key_lower = key.lower()
            if (
                key_lower.startswith("utm_")
                or key_lower in {"fbclid", "gclid", "dclid", "msclkid", "yclid", "ref_src"}
            ):
                continue
            query_pairs.append((key, value))
        query = urlencode(sorted(query_pairs))
        return urlunparse(("https", host, path_value, "", query, ""))
    except Exception:
        return ""


def get_with_retries(url, headers=None):
    last_error = None

    # Retry transient failures with bounded backoff. Keep TLS verification enabled:
    # certificate errors should be diagnosed, never hidden by disabling verification.
    # Three bounded attempts improve resilience to intermittent government-portal outages.
    for attempt in range(3):
        try:
            response = requests.get(
                url,
                headers=headers or HEADERS,
                timeout=(min(TIMEOUT, 10), min(TIMEOUT, 12)),
                allow_redirects=True,
                verify=certifi.where(),
            )

            if response.status_code in (408, 425, 429, 500, 502, 503, 504):
                if attempt < 2:
                    retry_after = response.headers.get("Retry-After", "").strip()
                    try:
                        delay = min(max(float(retry_after), 1.0), 10.0) if retry_after else 1.5 * (attempt + 1)
                    except ValueError:
                        delay = 1.5 * (attempt + 1)
                    time.sleep(delay)
                    continue

            response.raise_for_status()
            return response

        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc

            # Fail fast on errors that a retry cannot fix. Several official portals
            # return persistent DNS/TLS failures from hosted runners; retrying those
            # three times wastes the run budget needed to scan other authorities.
            error_text = f"{type(exc).__name__}: {exc}"
            permanent_network_error = (
                isinstance(exc, requests.exceptions.SSLError)
                or "NameResolutionError" in error_text
                or "Temporary failure in name resolution" in error_text
                or "CERTIFICATE_VERIFY_FAILED" in error_text
                or "Failed to establish a new connection" in error_text
            )
            if permanent_network_error:
                raise

            # Timeouts and connection resets can be transient. Use two attempts
            # total so a small set of slow sites cannot stall the whole registry.
            if attempt < 1:
                time.sleep(1.0)
                continue
            raise

    if last_error:
        raise last_error

    raise RuntimeError("Request failed after retries")


def telegram_send(chat_id, message):
    global TG_RATE_LIMITED
    if TG_RATE_LIMITED:
        print('Telegram is rate-limited; skipping further sends this run')
        return False
    if not TOKEN or not chat_id:
        print("Telegram delivery skipped: token or destination missing")
        return False

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message[:3900],
                "disable_web_page_preview": True,
            },
            timeout=(5, 15),
        )

        try:
            result = response.json()
        except ValueError:
            print("Telegram returned an invalid response:", response.status_code)
            return False

        if response.status_code == 429 or result.get("error_code") == 429:
            retry_after = result.get("parameters", {}).get("retry_after", 0)
            TG_RATE_LIMITED = True
            print("Telegram rate limit reached (429); retry_after=" + str(retry_after) + "s. Stopping sends; alerts remain queued.")
            return False

        if response.status_code >= 400 or not result.get("ok"):
            print(
                "Telegram delivery failed:",
                response.status_code,
                result.get("description", "Unknown error"),
            )
            return False

        print("Telegram delivery confirmed")
        return True

    except requests.RequestException as exc:
        print("Telegram network error:", type(exc).__name__, str(exc)[:150])
        return False


def is_stale_notice(title, published=""):
    """Reject clearly old notices when the title or feed gives an explicit date."""
    candidates = []
    text_value = str(title or "")
    for match in re.finditer(
        r"\b(?:(?:posted|published|updated|uploaded|issued|dated)\s+(?:on\s+)?)"
        r"(\d{1,2}[./-]\d{1,2}[./-]\d{4}|"
        r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|"
        r"\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4})",
        text_value,
        re.I,
    ):
        candidates.append(match.group(1).strip())
    if published:
        candidates.append(str(published).strip())

    for value in candidates:
        parsed_date = None
        for fmt in (
            "%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y",
            "%d %b %Y", "%d %B %Y", "%d %b, %Y", "%d %B, %Y",
            "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
            "%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y",
        ):
            try:
                parsed_date = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue
        if parsed_date is None:
            try:
                from email.utils import parsedate_to_datetime
                parsed_date = parsedate_to_datetime(value)
                if parsed_date and parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                parsed_date = None
        if parsed_date and parsed_date < datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS):
            return True
    return False


def fetch_source(source):
    name = source.get("name", source.get("id", "Unknown"))
    url = source.get("url", "")
    hosts = source.get("allowed_hosts", [])

    if not url or not hosts or not host_allowed(url, hosts):
        raise ValueError("Source URL is missing or not allowlisted")

    response = get_with_retries(url)

    if not host_allowed(response.url, hosts):
        raise ValueError(f"Redirected outside the official allowlist: {urlparse(response.url).hostname or 'unknown host'}")

    kind = str(source.get("kind", "html")).lower()
    content_type = response.headers.get("content-type", "").lower()

    if kind == "rss":
        feed = feedparser.parse(response.content)
        if not feed.entries and getattr(feed, "bozo", False):
            raise ValueError("RSS feed could not be parsed")

        links = [
            (
                str(entry.get("title", "")).strip(),
                str(entry.get("link", "")).strip(),
                str(entry.get("published", "")).strip(),
            )
            for entry in feed.entries
        ]
    else:
        if "html" not in content_type and "xml" not in content_type:
            raise ValueError("Source did not return HTML or XML")

        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for a in soup.select("a[href]"):
            title = " ".join(a.get_text(" ", strip=True).split())
            context = ""
            for parent in list(a.parents)[:7]:
                if getattr(parent, "name", None) in ("tr", "li", "article", "div"):
                    candidate_context = " ".join(parent.get_text(" ", strip=True).split())
                    if 20 <= len(candidate_context) <= 350:
                        context = candidate_context
                        break

            # Include compact card/row text when a link label is generic.
            if len(title) < 12 or not classify(title):
                if context and classify(context) and title.lower() not in context.lower():
                    title = (context + " — " + title).strip(" —")

            published = extract_notice_date(context) or extract_notice_date(title)
            links.append((
                title,
                urljoin(response.url, a.get("href", "")),
                published,
            ))

    found = []
    seen_urls = set()

    for title, link, published in links:
        title = " ".join(title.split())
        link = link.split("#")[0].strip()

        if len(title) < 4 or not host_allowed(link, hosts):
            continue

        category = classify(title)
        if not category or link in seen_urls:
            continue
        if is_stale_notice(title, published):
            continue

        seen_urls.add(link)

        found.append({
            "title": title[:260],
            "url": link,
            "category": category,
            "source_name": name,
            "source_id": source.get("id", name),
            "source_url": url,
            "published": published[:100],
        })

    # Official portals often list years of archived notices. Keep only a
    # bounded set of the first matching links (normally newest-first) per source.
    # This cap is also used to limit stale backlog and Telegram alert pressure.
    return found[:MAX_NEW_PER_SOURCE]


def build_result(item, detected_at):
    # Match the JSON fields consumed by site/app.js.
    return {
        "id": item["id"],
        "title": item["title"],
        "exam": item["title"],
        "exam_category": item.get("exam_category") or infer_exam_category(
            item.get("title", ""), item.get("source_name", ""), item.get("source_id", ""),
            item.get("state", "")),
        "category": item["category"],
        "source_name": item["source_name"],
        "source_id": item.get("source_id", ""),
        "authority": item["source_name"],
        "url": item["url"],
        "official_url": item["url"],
        "source_url": item.get("source_url", ""),
        "published": format_notice_date(item.get("published", "")),
        "exam_year": exam_year_from_title(item.get("title", "")),
        "region": item.get("region", "Central"),
        "state": item.get("state", ""),
        "description": (
            "Potential update detected on an allowlisted official website. "
            "Open the source to confirm the notice, dates and eligibility."
        ),
        "verified": False,
        "archive": False,
        "detected_at": detected_at,
    }


def main():
    registry = load_json("checker/sources.json", {"sources": []})
    state = load_json(
        "checker/state.json",
        {"seen": {}, "source_health": {}, "pending_alerts": {}},
    )
    approval = load_json("checker/approved.json", {"pending": []})
    results = load_json("site/data/results.json", [])

    if not isinstance(registry, dict) or not isinstance(registry.get("sources"), list):
        raise SystemExit("Invalid checker/sources.json: expected a sources list")

    if not isinstance(results, list):
        raise SystemExit("Invalid site/data/results.json: expected a JSON list")

    source_by_id = {str(s.get("id", "")): s for s in registry["sources"] if s.get("id")}
    source_by_name = {str(s.get("name", "")).strip().lower(): s for s in registry["sources"] if s.get("name")}

    # Clean old low-quality navigation links from the public website and keep
    # category labels aligned with the stricter title classifier.
    cleaned_results = []
    removed_result_rows = 0
    for item in results:
        if not isinstance(item, dict):
            removed_result_rows += 1
            continue
        title = str(item.get("title") or item.get("exam") or "").strip()
        # Repair stale/mislabelled state metadata from the authoritative source registry.
        source_meta = source_by_id.get(str(item.get("source_id", ""))) or source_by_name.get(
            str(item.get("source_name") or item.get("authority") or "").strip().lower(), {}
        )
        registered_state = str(source_meta.get("state") or "").strip()
        if registered_state:
            item["state"] = registered_state
            item["region"] = str(source_meta.get("region") or registered_state)
        category = classify(title)
        # Keep curated archive landing pages, but remove dated non-archive
        # notices outside the live 90-day window.
        if not category or (not item.get("archive", False) and is_stale_notice(title, item.get("published", ""))):
            removed_result_rows += 1
            continue
        item["title"] = title
        item["exam"] = str(item.get("exam") or title)
        item["category"] = category
        item["exam_category"] = item.get("exam_category") or infer_exam_category(
            title, item.get("source_name") or item.get("authority", ""),
            item.get("source_id", ""), item.get("state", ""),
        )
        cleaned_results.append(item)
    results = cleaned_results
    print(f"Website data cleanup: removed {removed_result_rows} generic/irrelevant rows; {len(results)} remain")

    seen = state.setdefault("seen", {})
    health = state.setdefault("source_health", {})
    pending = state.setdefault("pending_alerts", {})
    held = state.setdefault("held_alerts", {})
    # Existing website entries are authoritative for dedupe too. This protects
    # against repeated alerts if state.json is reset, missing, or not readable.
    published_urls = {
        normalize_notice_url(item.get("url") or item.get("official_url") or "")
        for item in results if isinstance(item, dict)
    }
    published_urls.discard("")
    # Keep a persistent delivery queue. Pending alerts must survive failed sends and
    # be retried on later scheduled runs; only a small batch is attempted per run.
    if not isinstance(pending, dict):
        pending = {}
        state["pending_alerts"] = pending

    sources = [s for s in registry["sources"] if s.get("enabled", True)]
    candidates = []
    successful = 0
    failures = 0
    checked_at = now_utc()

    print(f"GoResultHub checker: {len(sources)} sources enabled")

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        jobs = {executor.submit(fetch_source, s): s for s in sources}

        for future in as_completed(jobs):
            source = jobs[future]
            sid = source.get("id", source.get("name", "unknown"))

            try:
                items = future.result()
                successful += 1
                health[sid] = {
                    "status": "ok",
                    "checked_at": checked_at,
                    "new_candidates": 0,
                }

                for item in items:
                    normalized_url = normalize_notice_url(item.get("url", ""))
                    if not normalized_url:
                        continue

                    key = hashlib.sha256(
                        normalized_url.encode("utf-8")
                    ).hexdigest()[:24]

                    # Never create a fresh alert for a notice already published
                    # on the site, even if persistent checker state is missing.
                    if normalized_url in published_urls:
                        seen.setdefault(key, {
                            "first_seen": checked_at,
                            "source_id": item.get("source_id", ""),
                            "url": item.get("url", ""),
                            "dedupe_reason": "already_present_on_website",
                        })
                        continue

                    if key in seen or key in pending or key in held:
                        continue

                    item["id"] = key
                    item["region"] = source.get("region", "Central")
                    item["state"] = source.get("state", "")
                    item["exam_category"] = source.get(
                        "exam_category",
                        infer_exam_category(item.get("title", ""), source.get("name", ""),
                                            source.get("id", ""), source.get("state", "")),
                    )
                    item["detected_at"] = checked_at

                    pending[key] = {
                        "item": item,
                        "detected_at": checked_at,
                        "attempts": 0,
                    }
                    candidates.append(item)
                    health[sid]["new_candidates"] += 1

                print(f"OK {source.get('name', sid)}: {len(items)} links scanned")

            except Exception as exc:
                failures += 1
                health[sid] = {
                    "status": "failed",
                    "checked_at": checked_at,
                    "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                }
                print(f"FAIL {source.get('name', sid)}: {type(exc).__name__}: {str(exc)[:180]}")

    # Keep all previously published records; add new candidate records once.
    existing_ids = {
        str(item.get("id"))
        for item in results
        if isinstance(item, dict) and item.get("id")
    }

    published_urls = {
        normalize_notice_url(item.get("url") or item.get("official_url") or "")
        for item in results if isinstance(item, dict)
    }
    published_urls.discard("")
    for item in candidates:
        normalized_url = normalize_notice_url(item.get("url", ""))
        if item["id"] not in existing_ids and normalized_url not in published_urls:
            results.append(build_result(item, item["detected_at"]))
            existing_ids.add(item["id"])
            published_urls.add(normalized_url)

    # Review the persistent queue before sending. Invalid or irrelevant legacy
    # items are held for review, while valid failed deliveries remain retryable.
    source_by_name = {str(s.get("name", "")): s for s in sources}
    for key in list(pending.keys()):
        record = pending.get(key, {})
        item = record.get("item", {}) if isinstance(record, dict) else {}
        title = str(item.get("title", "")).strip() if isinstance(item, dict) else ""
        url = str(item.get("url", "")).strip() if isinstance(item, dict) else ""
        source = source_by_name.get(str(item.get("source_name", ""))) if isinstance(item, dict) else None
        stale_pending = isinstance(item, dict) and is_stale_notice(title, item.get("published", ""))
        if not isinstance(item, dict) or not classify(title) or stale_pending:
            held[key] = {
                "item": item if isinstance(item, dict) else {},
                "detected_at": record.get("detected_at", checked_at) if isinstance(record, dict) else checked_at,
                "held_at": checked_at,
                "hold_reason": (
                    "Explicitly dated notice is outside the live 90-day window; held for review."
                    if stale_pending else
                    "Generic, irrelevant, or unclassifiable title; held for review."
                ),
            }
            pending.pop(key, None)
            continue
        if not source or not host_allowed(url, source.get("allowed_hosts", [])):
            held[key] = {
                "item": item,
                "detected_at": record.get("detected_at", checked_at),
                "held_at": checked_at,
                "hold_reason": "Notice URL could not be validated against its official source allowlist.",
            }
            pending.pop(key, None)

    public_sent = 0
    public_attempts = 0
    # Limit attempts as well as successful deliveries. A Telegram 429 must not
    # cause the checker to hammer the API for every queued alert.
    max_public_alerts_per_run = max(
        1, min(int(os.getenv("MAX_PUBLIC_ALERTS_PER_RUN", "5")), 5)
    )
    # Retry valid pending alerts from previous runs as well as newly discovered
    # alerts. Failed sends therefore remain queued instead of being stranded.
    for key in list(pending.keys()):
        if TG_RATE_LIMITED:
            print('Telegram rate limited; alerts remain queued')
            break
        if public_attempts >= max_public_alerts_per_run:
            print(
                f"Public alert attempt limit reached ({max_public_alerts_per_run}); "
                f"{len(pending)} alerts remain queued"
            )
            break

        record = pending.get(key, {})
        item = record.get("item", {})
        if not item:
            pending.pop(key, None)
            continue

        direct_url = str(item.get("url", "")).strip()
        source_page = str(item.get("source_url", "")).strip()
        message = (
            "🔔 GoResultHub | Potential Exam Update\n\n"
            f"Authority: {item.get('source_name', 'Official authority')}\n"
            f"Type: {str(item.get('category', 'update')).replace('_', ' ').title()}\n"
            f"Exam year: {exam_year_from_title(item.get('title', '')) or 'Not stated in title'}\n"
            f"Notice date: {format_notice_date(item.get('published', '')) or 'Not shown on source listing'}\n\n"
            f"{item.get('title', 'New official link')}\n\n"
            + f"📄 OPEN NOTICE / RESULT:\n{direct_url}\n\n"
            + f"🌐 OFFICIAL AUTHORITY WEBSITE:\n{source_page or 'Official website link unavailable; search the authority name on its official portal.'}\n"
        )

        if not CHANNEL:
            print("TG_CHANNEL is missing; public alert remains pending")
            break

        public_attempts += 1
        if telegram_send(CHANNEL, message):
            # Stay comfortably below Telegram's per-chat send rate.
            time.sleep(1.1)
            seen[key] = {
                "first_seen": record.get("detected_at", checked_at),
                "source_id": item.get("source_id", ""),
                "url": item.get("url", ""),
                "telegram_sent_at": now_utc(),
            }
            pending.pop(key, None)
            public_sent += 1
        else:
            record["attempts"] = int(record.get("attempts", 0)) + 1
            record["last_attempt_at"] = now_utc()
            pending[key] = record

    # Process explicitly approved queue items, if configured.
    approved_items = approval.get("pending", []) if isinstance(approval, dict) else []
    remaining_approved = []
    approved_attempts = 0
    max_approved_alerts_per_run = 5

    for approved_index, item in enumerate(approved_items):
        if approved_attempts >= max_approved_alerts_per_run:
            remaining_approved.extend(approved_items[approved_index:])
            print(f"Approved alert attempt limit reached ({max_approved_alerts_per_run}); remaining items stay queued")
            break
        if TG_RATE_LIMITED:
            # Preserve this item and every later item; never lose queued alerts
            # just because Telegram temporarily rate-limited this run.
            remaining_approved.extend(approved_items[approved_index:])
            break
        if not isinstance(item, dict):
            continue

        if item.get("approved") is not True:
            remaining_approved.append(item)
            continue

        source = next(
            (s for s in sources if s.get("name") == item.get("source_name")),
            None,
        )
        url = str(item.get("url", "")).strip()

        if not source or not host_allowed(url, source.get("allowed_hosts", [])):
            print("Approved item rejected: URL/source mismatch")
            remaining_approved.append(item)
            continue

        if not CHANNEL:
            remaining_approved.append(item)
            continue

        source_page = str(source.get("url", "")).strip()
        direct_url = url
        message = (
            "📢 GoResultHub | Approved Exam Update\n\n"
            f"Authority: {item['source_name']}\n"
            f"Type: {str(item.get('category', 'update')).replace('_', ' ').title()}\n"
            f"Exam year: {exam_year_from_title(item.get('title', '')) or 'Not stated in title'}\n"
            f"Notice date: {format_notice_date(item.get('published', '')) or 'Not shown on source listing'}\n\n"
            f"{item.get('title', '')}\n\n"
            + f"📄 OPEN NOTICE / RESULT:\n{direct_url}\n\n"
            + f"🌐 OFFICIAL AUTHORITY WEBSITE:\n{source_page or 'Official website link unavailable; search the authority name on its official portal.'}\n"
        )

        approved_attempts += 1
        if not telegram_send(CHANNEL, message):
            remaining_approved.append(item)
        else:
            time.sleep(1.1)

    # Save data only after the run's work is complete.
    state.update({
        "last_run": checked_at,
        "last_run_failures": failures,
        "last_run_successful_sources": successful,
        "last_run_new_candidates": len(candidates),
        "last_run_public_posts": public_sent,
        "pending_alert_count": len(pending),
        "held_for_review_count": len(held),
        "source_registry_count": len(sources),
    })

    save_json("checker/state.json", state)
    save_json("checker/approved.json", {"pending": remaining_approved})
    save_json("site/data/results.json", results)
failure_types = {}
    for source_health in health.values():
        if source_health.get("status") != "failed":
            continue
        error = str(source_health.get("error", "Unknown"))
        kind = error.split(":", 1)[0] or "Unknown"
        failure_types[kind] = failure_types.get(kind, 0) + 1
    failure_breakdown = ", ".join(
        f"{kind}: {count}"
        for kind, count in sorted(failure_types.items(), key=lambda pair: (-pair[1], pair[0]))[:5]
    ) or "none"

    # Public, non-sensitive health snapshot for the website live status panel.
    save_json("site/data/status.json", {
        "last_checked_at": checked_at,
        "sources_enabled": len(sources),
        "sources_succeeded": successful,
        "sources_failed": failures,
        "new_candidates": len(candidates),
        "telegram_posts_sent": public_sent,
        "alerts_pending": len(pending),
        "status": "healthy" if successful > 0 and failures == 0 else ("partial" if successful > 0 else "unavailable"),
        "failure_types": failure_breakdown,
        "note": "Some sources may be unavailable or use formats automated scanning cannot read."
    })

    summary = (
        "GoResultHub | CHECKER SUMMARY\n\n"
        f"Checked (UTC): {checked_at}\n"
        f"Official sources enabled: {len(sources)}\n"
        f"Sources scanned successfully: {successful}\n"
        f"Sources not scanned: {failures}\n"
        f"Failure types: {failure_breakdown}\n"
        f"New candidate links: {len(candidates)}\n"
        f"Main-channel alerts sent: {public_sent}\n"
        f"Alerts pending delivery: {len(pending)}\n"
        f"Older alerts held for review: {len(held)}\n"
    )

    if failures:
        summary += "\nSome official sites timed out, blocked automated access, or had DNS/TLS issues. See workflow logs for per-source details.\n"

    if ADMIN and not TG_RATE_LIMITED:
        telegram_send(ADMIN, summary)
    elif ADMIN and TG_RATE_LIMITED:
        print('Telegram summary skipped because Telegram rate-limited this run')
    else:
        print("TG_ADMIN missing; private summary not sent")

    print(summary)

    if sources and successful == 0:
        raise SystemExit("No official sources could be checked successfully")


if __name__ == "__main__":
    main()
