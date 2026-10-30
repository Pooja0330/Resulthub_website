# GoResultHub checker: official exam notices, controlled alert delivery, and source health diagnostics.
# Scanner refresh validation: 2026-10-19 live-notification investigation.
# Fresh-scan trigger: keep the homepage feed backed by recent source checks, not only browser polling.

import os
import re
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urljoin, parse_qsl, urlencode, urlunparse, quote_plus
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

TIMEOUT = max(5, min(int(os.getenv("SOURCE_TIMEOUT_SECONDS", "20")), 30))
# Scan more sources concurrently so a five-minute schedule is practical without letting one slow portal block the whole run.
WORKERS = max(1, min(int(os.getenv("SOURCE_WORKERS", "24")), 32))
MAX_NEW_PER_SOURCE = max(1, min(int(os.getenv("MAX_NEW_PER_SOURCE", "5")), 20))
MAX_ARCHIVE_PER_SOURCE = max(20, min(int(os.getenv("MAX_ARCHIVE_PER_SOURCE", "250")), 500))
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
        r"provisional panel|shortlisted candidates|shortlisting of candidates|shortlisting candidates)\b", re.I)),
    ("cutoff", re.compile(
        r"\b(cut.?off marks?|qualifying marks?)\b", re.I)),
    ("admit_card", re.compile(
        r"\b(admit cards?|hall tickets?|call letters?|exam city intimation|"
        r"city intimation slip|download your admit card)\b", re.I)),
    ("answer_key", re.compile(
        r"\b(answer keys?|response sheets?|response sheet(?:s|\(s\))?|tentative answer keys?|objection tracker|challenge answer key)\b", re.I)),
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
        r"vacancies for|vacancy for|tentative vacancies|last date to apply|application deadline|"
        r"corrigendum|addendum|extension of last date|revised vacancy|"
        r"additional vacancies|selection process for|selection list for recruitment|"
        r"preliminary examination|prelims examination|main examination|mains examination|"
        r"preliminary test|preliminary exam|mains exam|main written examination|"
        r"public notice|important notice|notice regarding|exam notice|examination notice|"
        r"admission notice|admission schedule|counselling schedule|counseling schedule|"
        r"application correction|correction window|registration extension|"
        r"exam-related circular|examination circular|"
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
    r"glow dental clinic|sports meet|cultural fest|cultural festival|"
    r"skip to content|accessibility statement|accessibilitystatement|screen reader access|"
    r"about us|main functions|press information bureau|site map|contact us|quick links|"
    r"terms of use|feedback|login|log in|register|search|help|results 360 news|indiaresults blog|"
    r"accessibility options|skip navigation|back to top|rti|policy information|rti officers|case decisions)\b", re.I
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
    # The public exam feed can contain thousands of records. Keep that
    # frequently downloaded browser payload compact so mobile browsers do not
    # have to parse/render megabytes of whitespace on every refresh.
    if name in {"site/data/results.json", "site/results.json"}:
        serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    else:
        serialized = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temporary.write_text(serialized, encoding="utf-8")
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


def classify_source_title(title, source):
    """Classify normal exam notices; optionally index every entry from an official news feed."""
    category = classify(title)
    # Broad press-release feeds may index genuine announcements that do not
    # match exam-specific keywords, but never promote navigation/accessibility
    # links into notifications.
    if (
        source.get("include_all_items", False)
        and title
        and not SKIP.search(title)
        and not NAV_TITLE.fullmatch(title.strip())
    ):
        return category or "notification"
    return category


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
    # Government portals often have slow connection setup. Use a meaningful
    # connect/read budget and retry transient DNS, timeout, reset and TLS
    # handshake failures. Certificate verification remains STRICT: never
    # disable TLS checks or accept an invalid certificate.
    retryable_statuses = (408, 425, 429, 500, 502, 503, 504)
    for attempt in range(3):
        try:
            response = requests.get(
                url,
                headers=headers or HEADERS,
                timeout=(min(TIMEOUT, 12), min(TIMEOUT, 18)),
                allow_redirects=True,
                verify=certifi.where(),
            )
            if response.status_code in retryable_statuses and attempt < 2:
                retry_after = response.headers.get("Retry-After", "").strip()
                try:
                    delay = min(max(float(retry_after), 1.0), 4.0) if retry_after else (1.0 + attempt)
                except ValueError:
                    delay = 1.0 + attempt
                response.close()
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            error_text = str(exc)
            # A certificate validation failure is a security failure, not a
            # transient network condition. Keep verification enabled and fail
            # this source safely; it will be checked again on the next run.
            permanent = "CERTIFICATE_VERIFY_FAILED" in error_text
            if permanent or attempt >= 2:
                raise
            delay = min(2 ** attempt, 4)
            print(f"Retrying source request ({attempt + 2}/3) after {type(exc).__name__}; wait={delay}s")
            time.sleep(delay)
    if last_error:
        raise last_error
    raise RuntimeError("Request failed after retries")

def telegram_send(chat_id, message, reply_markup=None):
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
                **({"reply_markup": reply_markup} if reply_markup else {}),
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


def is_speculative_status_title(title):
    """Reject editorial placeholders that are not official notices."""
    value = " ".join(str(title or "").lower().split())
    return bool(re.search(
        r"\b(awaiting official update|expected soon|result expected soon|"
        r"result not yet declared|not yet declared by the authority)\b",
        value,
    ))


def is_navigation_noise_title(title):
    """Reject scraped site menus/homepage link clusters mistaken for notices."""
    value = re.sub(r"[^a-z0-9]+", "", str(title or "").lower())
    menu_terms = (
        "servicespayfeeonline",
        "officialemailservice",
        "jobsrecruitmentadvertisements",
        "callletters",
        "tendersnotices",
        "employeeonlineservices",
        "photogalleryconferences",
        "virtualtour",
        "esamikshya",
        "epratikaar",
    )
    hits = sum(term in value for term in menu_terms)
    # These are menu aggregates, not individual result/admit-card notices.
    if value.startswith("servicespayfeeonlineforofflineapplications") and hits >= 3:
        return True
    if value.startswith("epratikaar") and hits >= 3:
        return True
    if value == "jobsrecruitmentadvertisementscallletters":
        return True
    return len(value) > 100 and hits >= 4


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


def discover_listing_urls(soup, base_url, hosts, limit=2):
    """Find a small number of likely official notice-listing pages on the same allowlisted portal."""
    candidates = []
    seen = set()
    listing_hint = re.compile(
        r"(latest|what.?s new|news|notice|notification|announcement|circular|"
        r"result|recruitment|career|admit.?card|answer.?key|examination|"
        r"public notice|press release|updates|advertisement|next|older|previous|page)",
        re.I,
    )
    ignored_path = re.compile(
        r"\.(?:pdf|jpg|jpeg|png|gif|zip|docx?|xlsx?|pptx?)$",
        re.I,
    )
    base_host = (urlparse(base_url).hostname or "").lower()

    for anchor in soup.select("a[href]"):
        label = " ".join(anchor.get_text(" ", strip=True).split())
        href = urljoin(base_url, anchor.get("href", "")).split("#", 1)[0].strip()
        if not label or len(label) > 100 or not href or href in seen:
            continue
        if not host_allowed(href, hosts):
            continue
        parsed = urlparse(href)
        if parsed.scheme != "https" or ignored_path.search(parsed.path):
            continue
        if (parsed.hostname or "").lower() != base_host and not host_allowed(href, hosts):
            continue
        if href.rstrip("/") == base_url.rstrip("/"):
            continue
        # Avoid sending query-only links, login pages, search pages and generic navigation.
        if re.search(r"(login|sign.?in|register|search|contact|privacy|accessibility)", label + " " + parsed.path, re.I):
            continue
        # Pagination controls are useful only on the same official portal and
        # are kept behind the same strict six-page crawl bound.
        is_pagination = bool(re.search(r"(next|older|previous|page\s*\d+)", label, re.I)
                             or re.search(r"(?:[?&](?:page|paged|p)=\d+|/page/\d+)", href, re.I))
        if not listing_hint.search(label + " " + parsed.path) and not is_pagination:
            continue
        seen.add(href)
        priority = 0 if re.search(r"(latest|what.?s new|notice|notification|result|recruitment|announcement|updates)", label, re.I) else (1 if is_pagination else 2)
        candidates.append((priority, href))

    candidates.sort(key=lambda item: (item[0], item[1]))
    return [url for _, url in candidates[:max(0, min(limit, 2))]]


def fetch_source(source):
    name = source.get("name", source.get("id", "Unknown"))
    url = source.get("url", "")
    hosts = source.get("allowed_hosts", [])

    if not url or not hosts or not host_allowed(url, hosts):
        raise ValueError("Source URL is missing or not allowlisted")

    kind = str(source.get("kind", "html")).lower()
    response = get_with_retries(url)
    if not host_allowed(response.url, hosts):
        raise ValueError(f"Redirected outside the official allowlist: {urlparse(response.url).hostname or 'unknown host'}")

    def links_from_response(page_response):
        content_type = page_response.headers.get("content-type", "").lower()
        if kind == "rss":
            feed = feedparser.parse(page_response.content)
            if not feed.entries and getattr(feed, "bozo", False):
                raise ValueError("RSS feed could not be parsed")
            return [
                (
                    str(entry.get("title", "")).strip(),
                    str(entry.get("link", "")).strip(),
                    str(entry.get("published", entry.get("updated", ""))).strip(),
                )
                for entry in feed.entries
            ], []
        if "html" not in content_type and "xml" not in content_type:
            raise ValueError("Source did not return HTML or XML")

        soup = BeautifulSoup(page_response.text, "html.parser")
        links = []
        for anchor in soup.select("a[href]"):
            title = " ".join(anchor.get_text(" ", strip=True).split())
            context = ""
            # Official notice boards often render the date, title and PDF link
            # as separate elements in one card. Prefer the smallest containing
            # row/card that includes a recognizable notice title, rather than
            # taking a short "Read more"/PDF label as the announcement.
            parents = list(anchor.parents)[:12]
            for parent in parents:
                if getattr(parent, "name", None) not in ("tr", "li", "article", "div", "section"):
                    continue
                candidate_context = " ".join(parent.get_text(" ", strip=True).split())
                if not (20 <= len(candidate_context) <= 600):
                    continue
                if classify(candidate_context):
                    context = candidate_context
                    break
            # Some SSC notice cards have a separate date element next to a
            # linked title. Recover the date from the closest card even when
            # the title itself already classifies correctly.
            if not context:
                for parent in parents:
                    if getattr(parent, "name", None) not in ("tr", "li", "article", "div", "section"):
                        continue
                    candidate_context = " ".join(parent.get_text(" ", strip=True).split())
                    if 20 <= len(candidate_context) <= 600 and re.search(
                        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+20\d{2}\b|\b\d{1,2}\s+[A-Za-z]{3,9}\s+20\d{2}\b",
                        candidate_context, re.I
                    ):
                        context = candidate_context
                        break

            generic_label = (
                len(title) < 45
                or bool(NAV_TITLE.fullmatch(title.strip()))
                or bool(re.fullmatch(
                    r"(?:preliminary|main|mains|final)?\s*(?:examination\s+)?"
                    r"(?:result|results|result status|merit list|admit card|answer key|"
                    r"cut.?off|shortlisted candidates)",
                    title.strip(), re.I
                ))
            )
            if context and classify(context) and generic_label and len(context) > len(title) + 10:
                title = context
            elif context and classify(context) and not classify(title):
                title = context

            published = extract_notice_date(context) or extract_notice_date(title)
            links.append((title, urljoin(page_response.url, anchor.get("href", "")), published))

        listing_urls = discover_listing_urls(soup, page_response.url, hosts) if kind != "rss" else []
        return links, listing_urls

    links, listing_urls = links_from_response(response)
    # Homepages frequently expose only a few generic links. If they yield fewer
    # than three useful notices, inspect up to three official listing pages as a
    # fallback; never crawl arbitrary external hosts or an unbounded link graph.
    # Count only fresh, publishable candidates. Three old notices on a homepage
    # must not prevent the scanner from checking the deeper official notice list.
    initial_urls = set()
    initial_count = 0
    for title, link, published in links:
        normalized = normalize_notice_url(link)
        if (normalized and normalized not in initial_urls
                and classify_source_title(" ".join(str(title or "").split()), source)
                and not is_navigation_noise_title(title)
                and not is_speculative_status_title(title)
                and not is_stale_notice(title, published)
                and host_allowed(link, hosts)):
            initial_urls.add(normalized)
            initial_count += 1

    pages_scanned = 1
    if kind != "rss" and source.get("discover_listing_pages", False) and initial_count < 3:
        # Inspect up to six official listing pages (including pagination) rather
        # than stopping at the first three links, which may be stale or generic.
        inspected_pages = set()
        page_queue = list(listing_urls)
        while page_queue and len(inspected_pages) < 2:
            listing_url = page_queue.pop(0)
            if listing_url in inspected_pages:
                continue
            inspected_pages.add(listing_url)
            try:
                listing_response = get_with_retries(listing_url)
                if not host_allowed(listing_response.url, hosts):
                    print(f"SKIP listing page redirected outside allowlist for {name}")
                    continue
                extra_links, extra_listing_urls = links_from_response(listing_response)
                links.extend(extra_links)
                for next_url in extra_listing_urls:
                    if next_url not in inspected_pages and next_url not in page_queue:
                        page_queue.append(next_url)
                pages_scanned += 1
            except Exception as exc:
                print(f"WARN listing page failed for {name}: {type(exc).__name__}: {str(exc)[:120]}")

    found = []
    seen_urls = set()
    for title, link, published in links:
        title = " ".join(str(title or "").split())
        link = str(link or "").split("#")[0].strip()
        normalized = normalize_notice_url(link)
        if len(title) < 4 or not normalized or not host_allowed(link, hosts):
            continue
        if is_navigation_noise_title(title):
            print(f"INFO ignored navigation/menu text from {name}: {title[:100]}")
            continue
        category = classify_source_title(title, source)
        if not category or is_speculative_status_title(title) or normalized in seen_urls:
            continue
        if is_stale_notice(title, published) and not source.get("historical_archive", False):
            continue

        seen_urls.add(normalized)
        found.append({
            "title": title[:260],
            "url": link,
            "category": category,
            "source_name": name,
            "source_id": source.get("id", name),
            "source_url": url,
            "published": published[:100],
            "archive": bool(source.get("historical_archive", False)),
        })

    source_limit = int(source.get("max_new", MAX_ARCHIVE_PER_SOURCE if source.get("historical_archive", False) else MAX_NEW_PER_SOURCE))
    print(f"Source scan {name}: {pages_scanned} official page(s), {len(found)} matching notices")
    return found[:max(1, min(source_limit, 100))]

def is_exam_alert_source(source):
    """Keep broad PIB press-release feeds out of the exam-alert pipeline."""
    source_id = str(source.get("id", "")).strip().lower()
    source_name = str(source.get("name", "")).strip().lower()
    return (
        source.get("enabled", True)
        and not source.get("include_all_items", False)
        and not source_id.startswith("pib-")
        and not source_name.startswith("press information bureau")
    )


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
            "Historical entry discovered on an official archive listing. Open the issuing authority link to confirm the year, notice details and availability."
            if item.get("archive") else
            "Potential update detected on an allowlisted official website. Open the source to confirm the notice, dates and eligibility."
        ),
        "verified": False,
        "archive": bool(item.get("archive", False)),
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
        # Keep GoResultHub links on GoResultHub; do not publish third-party aggregator links.
        source_id_value = str(item.get("source_id") or "").strip().lower()
        source_name_value = str(item.get("source_name") or item.get("authority") or "").strip().lower()
        source_meta_for_cleanup = source_by_id.get(source_id_value, {})
        if (
            source_id_value.startswith("indiaresults-")
            or "indiaresults.com" in source_name_value
            or source_name_value.startswith("indiaresults")
            or source_id_value.startswith("pib-")
            or source_meta_for_cleanup.get("include_all_items", False)
            or source_name_value.startswith("press information bureau")
        ):
            removed_result_rows += 1
            continue
        # Repair stale/mislabelled state metadata from the authoritative source registry.
        source_meta = source_by_id.get(str(item.get("source_id", ""))) or source_by_name.get(
            str(item.get("source_name") or item.get("authority") or "").strip().lower(), {}
        )
        registered_state = str(source_meta.get("state") or "").strip()
        if registered_state:
            item["state"] = registered_state
            item["region"] = str(source_meta.get("region") or registered_state)
        category = classify_source_title(title, source_meta)
        # Keep curated archive landing pages, but remove dated non-archive
        # notices outside the live 90-day window.
        if not category or is_speculative_status_title(title) or (not item.get("archive", False) and is_stale_notice(title, item.get("published", ""))):
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

    # PIB has its own independent publisher and must never enter the exam-alert queue.
    # Its all-releases feed contains general government press releases, not just exams.
    sources = [s for s in registry["sources"] if is_exam_alert_source(s)]
    candidates = []
    historical_candidates = []
    # Recover feed records if results.json was emptied or lost while state.json
    # still remembers previously delivered notices. Re-index them on the website
    # without sending duplicate Telegram alerts.
    recovered_candidates = []
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

                    # Historical archive entries are indexed as archive records,
                    # never placed in the live alert queue.
                    if source.get("historical_archive", False):
                        if normalized_url in published_urls:
                            continue
                        item["id"] = key
                        item["region"] = source.get("region", "Central")
                        item["state"] = source.get("state", "")
                        item["exam_category"] = source.get("exam_category", "University Results")
                        item["archive"] = True
                        item["detected_at"] = checked_at
                        historical_candidates.append(item)
                        continue

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

                    if key in seen:
                        # A seen key is not proof that the website still contains
                        # the record. If the public feed was accidentally emptied,
                        # restore the notice from its official source without
                        # queueing another Telegram message.
                        item["id"] = key
                        item["region"] = source.get("region", "Central")
                        item["state"] = source.get("state", "")
                        item["exam_category"] = source.get(
                            "exam_category",
                            infer_exam_category(item.get("title", ""), source.get("name", ""),
                                                source.get("id", ""), source.get("state", "")),
                        )
                        item["detected_at"] = seen.get(key, {}).get("first_seen", checked_at)
                        item["recovered"] = True
                        recovered_candidates.append(item)
                        continue

                    if key in pending or key in held:
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
    for item in historical_candidates + recovered_candidates + candidates:
        normalized_url = normalize_notice_url(item.get("url", ""))
        if item["id"] not in existing_ids and normalized_url not in published_urls:
            results.append(build_result(item, item["detected_at"]))
            existing_ids.add(item["id"])
            published_urls.add(normalized_url)

    # Review the persistent queue before sending. Invalid or irrelevant legacy
    # items are held for review, while valid failed deliveries remain retryable.
    source_by_name = {str(s.get("name", "")).strip().lower(): s for s in sources if s.get("name")}
    queue_held_this_run = 0
    for key in list(pending.keys()):
        record = pending.get(key, {})
        item = record.get("item", {}) if isinstance(record, dict) else {}
        if not isinstance(item, dict):
            item = {}
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        # Resolve by stable source ID first. Names can change or differ in
        # capitalization between the registry and older queued records.
        source = (
            source_by_id.get(str(item.get("source_id", "")))
            or source_by_name.get(str(item.get("source_name", "")).strip().lower())
        )
        stale_pending = is_stale_notice(title, item.get("published", ""))
        category = classify_source_title(title, source or {}) if title else None
        hold_reason = ""
        if not source:
            hold_reason = "Source ID/name no longer matches an enabled official source."
        elif not category or is_speculative_status_title(title):
            hold_reason = "Generic, irrelevant, speculative, or unclassifiable title."
        elif stale_pending:
            hold_reason = "Explicitly dated notice is outside the live 90-day window."
        elif not host_allowed(url, source.get("allowed_hosts", [])):
            hold_reason = "Notice URL could not be validated against its official source allowlist."

        if hold_reason:
            held[key] = {
                "item": item,
                "detected_at": record.get("detected_at", checked_at) if isinstance(record, dict) else checked_at,
                "held_at": checked_at,
                "hold_reason": hold_reason,
            }
            pending.pop(key, None)
            queue_held_this_run += 1
            print(f"ALERT QUEUE HOLD {key}: {hold_reason} | source={item.get('source_id', item.get('source_name', 'unknown'))} | title={title[:140]}")
    print(
        f"ALERT QUEUE CHECK: pending={len(pending)}, newly_held={queue_held_this_run}, "
        f"previously_held={len(held)}, candidates_this_run={len(candidates)}"
    )

    public_sent = 0
    public_attempts = 0
    # Limit attempts as well as successful deliveries. A Telegram 429 must not
    # cause the checker to hammer the API for every queued alert.
    # Drain the backlog faster while remaining below Telegram's per-chat rate.
    # Sends are still spaced by 1.1 seconds and 429 stops the batch immediately.
    max_public_alerts_per_run = max(
        1, min(int(os.getenv("MAX_PUBLIC_ALERTS_PER_RUN", "10")), 10)
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
        if not isinstance(item, dict) or not item:
            pending.pop(key, None)
            continue

        # Resolve each queued notice from its own official source and URL.
        # Do not reuse loop variables from source scanning or queue validation.
        url = str(item.get("url", "")).strip()
        source = (
            source_by_id.get(str(item.get("source_id", "")))
            or source_by_name.get(str(item.get("source_name", "")).strip().lower())
        )
        if not source or not host_allowed(url, source.get("allowed_hosts", [])):
            held[key] = {
                "item": item,
                "detected_at": record.get("detected_at", checked_at),
                "held_at": checked_at,
                "hold_reason": "Queued notice URL could not be validated against its own official source allowlist.",
            }
            pending.pop(key, None)
            print("Held queued alert with missing source or invalid official URL")
            continue

        # Approved alerts must also be indexed in the public website feed.
        # Previously this queue could send a Telegram link to notice.html without
        # adding the corresponding record to site/data/results.json.
        item_id = str(item.get("id", "")).strip()
        item_title = str(item.get("title", "")).strip()
        normalized_item = dict(item)
        normalized_item["id"] = item_id or hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        normalized_item["title"] = item_title or url
        normalized_item["source_id"] = source.get("id", source.get("name", ""))
        normalized_item["source_url"] = normalized_item.get("source_url") or source.get("url", "")
        normalized_item["category"] = normalized_item.get("category") or "update"
        normalized_item["region"] = normalized_item.get("region") or source.get("region", "Central")
        normalized_item["state"] = normalized_item.get("state") or source.get("state", "")
        normalized_item["exam_category"] = normalized_item.get("exam_category") or source.get("exam_category", "")
        normalized_url = normalize_notice_url(url)
        already_indexed = any(
            isinstance(record, dict) and (
                str(record.get("id", "")) == normalized_item["id"]
                or normalize_notice_url(record.get("url") or record.get("official_url") or "") == normalized_url
            )
            for record in results
        )
        if not already_indexed:
            results.append(build_result(normalized_item, normalized_item.get("detected_at") or checked_at))
            published_urls.add(normalized_url)

        website_url = "https://goresulthub.com/notice.html?id=" + quote_plus(normalized_item["id"]) + "&q=" + quote_plus(item_title) + "&utm_source=telegram&utm_medium=channel&utm_campaign=exam_alert"
        message = (
            "🔔 GoResultHub | Exam Update\n\n"
            f"Authority: {item.get('source_name', 'Official authority')}\n"
            f"Type: {str(item.get('category', 'update')).replace('_', ' ').title()}\n"
            f"Exam year: {exam_year_from_title(item.get('title', '')) or 'Not stated in title'}\n"
            f"Notice date: {format_notice_date(item.get('published', '')) or 'Not shown on source listing'}\n\n"
            f"{item.get('title', 'New exam update')}\n\n"
            "Open GoResultHub to view the update and continue to the relevant authority website:\n"
            f"{website_url}"
        )
        keyboard = {"inline_keyboard": [[{"text": "🔎 View on GoResultHub", "url": website_url}]]}

        if not CHANNEL:
            print("TG_CHANNEL is missing; public alert remains pending")
            break

        public_attempts += 1
        if telegram_send(CHANNEL, message, reply_markup=keyboard):
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

        website_url = "https://goresulthub.com/notice.html?id=" + quote_plus(str(item.get("id", "")).strip()) + "&q=" + quote_plus(str(item.get("title", "")).strip()) + "&utm_source=telegram&utm_medium=channel&utm_campaign=exam_alert"
        message = (
            "📢 GoResultHub | Exam Update\n\n"
            f"Authority: {item['source_name']}\n"
            f"Type: {str(item.get('category', 'update')).replace('_', ' ').title()}\n"
            f"Exam year: {exam_year_from_title(item.get('title', '')) or 'Not stated in title'}\n"
            f"Notice date: {format_notice_date(item.get('published', '')) or 'Not shown on source listing'}\n\n"
            f"{item.get('title', '')}\n\n"
            "Open GoResultHub to view the update and continue to the relevant authority website:\n"
            f"{website_url}"
        )
        keyboard = {"inline_keyboard": [[{"text": "🔎 View on GoResultHub", "url": website_url}]]}

        approved_attempts += 1
        if not telegram_send(CHANNEL, message, reply_markup=keyboard):
            remaining_approved.append(item)
        else:
            # Approved-queue alerts also need a delivery timestamp in the public
            # feed; otherwise Chrome can announce them while the homepage keeps
            # sorting them by their older original detection time.
            delivered_at = now_utc()
            sent_url = normalize_notice_url(url)
            if sent_url:
                for result_item in results:
                    if not isinstance(result_item, dict):
                        continue
                    result_url = normalize_notice_url(result_item.get("url") or result_item.get("official_url") or "")
                    if result_url == sent_url:
                        result_item["telegram_sent_at"] = delivered_at
            time.sleep(1.1)

    # Mirror successful Telegram delivery timestamps into the public feed so the
    # website can notify visitors when an older queued alert is actually delivered.
    sent_by_url = {}
    for delivery in seen.values():
        if not isinstance(delivery, dict) or not delivery.get("telegram_sent_at"):
            continue
        delivery_url = normalize_notice_url(delivery.get("url", ""))
        if delivery_url:
            sent_by_url[delivery_url] = delivery["telegram_sent_at"]
    for result_item in results:
        if not isinstance(result_item, dict):
            continue
        result_url = normalize_notice_url(result_item.get("url") or result_item.get("official_url") or "")
        if result_url in sent_by_url:
            result_item["telegram_sent_at"] = sent_by_url[result_url]

    # Backfill the two OSSTET answer-key alerts already sent to Telegram
    # before delivery timestamps were added to approved-queue records. The
    # channel screenshot shows both at 17:11 IST on 2026-10-20 (11:41 UTC).
    osstet_sent_at = "2026-10-20T11:41:00+00:00"
    osstet_backfilled = 0
    for result_item in results:
        if not isinstance(result_item, dict):
            continue
        title_value = str(result_item.get("title") or result_item.get("exam") or "").upper()
        source_value = str(result_item.get("source_name") or result_item.get("authority") or "").upper()
        if "OSSTET" in title_value and "ANSWER KEY" in title_value and "ODISHA" in (source_value + " " + title_value):
            if not result_item.get("telegram_sent_at"):
                result_item["telegram_sent_at"] = osstet_sent_at
                osstet_backfilled += 1
    if osstet_backfilled:
        print(f"Backfilled Telegram delivery time for {osstet_backfilled} existing OSSTET answer-key feed record(s)")

    # Save data only after the run's work is complete.
    state.update({
        "last_run": checked_at,
        "last_run_failures": failures,
        "last_run_successful_sources": successful,
        "last_run_new_candidates": len(candidates),
        "last_run_recovered_records": len(recovered_candidates),
        "last_run_public_posts": public_sent,
        "pending_alert_count": len(pending),
        "held_for_review_count": len(held),
        "source_registry_count": len(sources),
    })

    save_json("checker/state.json", state)
    save_json("checker/approved.json", {"pending": remaining_approved})
    save_json("site/data/results.json", results)
    # Keep the legacy /results.json URL synchronized for older links and
    # integrations. The website itself reads /data/results.json.
    save_json("site/results.json", results)
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
        "recovered_records": len(recovered_candidates),
        "telegram_posts_sent": public_sent,
        "alerts_pending": len(pending),
        "status": "healthy" if successful > 0 and failures == 0 else ("partial" if successful > 0 else "unavailable"),
        "failure_types": failure_breakdown,
        # Small, safe diagnostic sample makes recurring source failures actionable
        # without exposing full URLs, response bodies, credentials, or request headers.
        "failed_source_samples": [
            {
                "source_id": sid,
                "error_type": str(source_health.get("error", "Unknown")).split(":", 1)[0][:60],
            }
            for sid, source_health in sorted(health.items())
            if source_health.get("status") == "failed"
        ][:12],
        "note": "Some sources may be unavailable or use formats automated scanning cannot read. failed_source_samples lists a small diagnostic sample."

    })

    summary = (
        "GoResultHub | CHECKER SUMMARY\n\n"
        f"Checked (UTC): {checked_at}\n"
        f"Official sources enabled: {len(sources)}\n"
        f"Sources scanned successfully: {successful}\n"
        f"Sources not scanned: {failures}\n"
        f"Failure types: {failure_breakdown}\n"
        f"New candidate links: {len(candidates)}\n"
        f"Website records recovered: {len(recovered_candidates)}\n"
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
