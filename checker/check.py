import os
import re
import json
import sys
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import feedparser
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def file_path(name):
    return os.path.join(ROOT, name)

def load_json(name, default):
    try:
        with open(file_path(name), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(name, data):
    target = file_path(name)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    temporary = target + ".tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temporary, target)

TOKEN = os.getenv("TG_TOKEN", "").strip()
ADMIN = os.getenv("TG_ADMIN", "").strip()
CHANNEL = os.getenv("TG_CHANNEL", "").strip()
TIMEOUT = max(4, min(int(os.getenv("SOURCE_TIMEOUT_SECONDS", "8")), 20))
WORKERS = max(2, min(int(os.getenv("SOURCE_WORKERS", "10")), 20))
MAX_REVIEW_ITEMS = 12
MAX_AGE_DAYS = 90

HEADERS = {
    "User-Agent": "GoResultHubExamMonitor/2.2 (+official-source monitor)",
    "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
}

EXAM_CONTEXT = re.compile(
    r"\b(exam|examination|entrance|competitive examination|civil services|"
    r"upsc|ias|ips|ssc|ibps|sbi|rrb|railway|nta|jee|neet|cuet|gate|"
    r"clerk|probationary officer|group d|assistant loco pilot|technician|"
    r"public service commission|board examination|ugc net|ctet|tet|"
    r"admit card|hall ticket|answer key|scorecard|merit list|exam result|"
    r"examination result|recruitment examination|prelims|mains)\b", re.I
)
SKIP = re.compile(
    r"\b(tender|quotation|procurement|vendor registration|privacy policy|"
    r"photo gallery|annual report|press release|media advisory|estate section|"
    r"classroom booking|associate professor|assistant professor|"
    r"professor appointment|guest faculty|school relocation|holiday list|"
    r"meeting notice)\b", re.I
)
RULES = [
    ("result", re.compile(r"\b(result declared|exam results?|examination results?|scorecards?|marks list|rank list|rank card)\b", re.I)),
    ("merit_list", re.compile(r"\b(merit list|final selection|selected candidates|qualified candidates|provisional selection|selection list|final panel|allotment list)\b", re.I)),
    ("cutoff", re.compile(r"\b(cut.?off marks?|cutoff marks?|qualifying marks?)\b", re.I)),
    ("admit_card", re.compile(r"\b(admit cards?|hall tickets?|call letters?|exam city intimation|city intimation slip)\b", re.I)),
    ("answer_key", re.compile(r"\b(answer keys?|response sheets?|objection tracker)\b", re.I)),
    ("exam_schedule", re.compile(r"\b(exam date|examination date|exam schedule|examination schedule|date sheet|exam calendar|exam postponement|exam rescheduled|examination postponed|examination rescheduled)\b", re.I)),
    ("notification", re.compile(r"\b(exam notification|examination notification|recruitment notification|recruitment advertisement|vacancy notification|information bulletin|application dates|registration opens|apply online|online application|application notice)\b", re.I)),
]
DATE_PATTERNS = [
    re.compile(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b"),
    re.compile(r"\b(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(20\d{2})\b", re.I),
]
MONTHS = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}

def build_session():
    session = requests.Session()
    retry = Retry(
        total=1, connect=1, read=0, status=1,
        backoff_factor=0.2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=WORKERS, pool_maxsize=WORKERS)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session

SESSION = build_session()

def host_allowed(url, allowed_hosts):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host:
            return False
        if isinstance(allowed_hosts, str):
            allowed_hosts = [allowed_hosts]
        return any(host == str(h).lower() or host.endswith("." + str(h).lower()) for h in allowed_hosts if h)
    except Exception:
        return False

def extract_title_date(text):
    for i, pattern in enumerate(DATE_PATTERNS):
        match = pattern.search(text or "")
        if not match:
            continue
        try:
            g = match.groups()
            if i == 0:
                year, month, day = map(int, g)
            elif i == 1:
                day, month, year = map(int, g)
            else:
                day, month, year = int(g[0]), MONTHS[g[1][:3].lower()], int(g[2])
            return datetime(year, month, day, tzinfo=timezone.utc)
        except (ValueError, IndexError):
            continue
    return None

def classify(title, source=None, link=""):
    """
    Broad discovery classifier. These are private review candidates, not verified
    announcements; therefore prefer recall over precision and require human review.
    """
    text = " ".join(str(part or "") for part in (title, link)).replace("_", " ").replace("-", " ")
    if not title or SKIP.search(title):
        return None
    for category, pattern in RULES:
        if pattern.search(text):
            return category
    # Official authority pages often use short labels such as "What's New",
    # "Latest Updates", "Recruitment", or "Notice". Use the registry categories
    # only as a fallback and keep all matches private for human review.
    low = text.lower()
    fallback = [
        ("result", r"\b(results?|score ?card|marks|rank|score)\b"),
        ("merit_list", r"\b(merit|selection|selected|qualified|allotment|provisional|final panel)\b"),
        ("admit_card", r"\b(admit|hall ticket|call letter|exam city|intimation slip)\b"),
        ("answer_key", r"\b(answer key|response sheet|objection)\b"),
        ("exam_schedule", r"\b(schedule|date sheet|exam calendar|postponed|rescheduled|examination date)\b"),
        ("notification", r"\b(notification|notices?|recruitment|advertisement|vacanc(?:y|ies)|apply online|application|what.s new|latest updates?)\b"),
    ]
    source_categories = set((source or {}).get("categories", []))
    for category, expression in fallback:
        if category in source_categories and re.search(expression, low, re.I):
            return category
    # Short titles need exam/recruitment context unless their source is an
    # exam authority and the link itself names a recognizable update type.
    if EXAM_CONTEXT.search(text):
        for category, pattern in RULES:
            if pattern.search(text):
                return category
    return None

def telegram_send(chat_id, message):
    if not TOKEN or not chat_id:
        print("Telegram skipped: token or destination missing")
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": message[:3900], "disable_web_page_preview": True},
            timeout=(6, 15),
        )
        try:
            body = response.json()
        except ValueError:
            print("Telegram returned non-JSON response; HTTP", response.status_code)
            return False
        if response.status_code >= 400 or not body.get("ok"):
            print("Telegram delivery failed:", response.status_code, body.get("description", "Unknown error"))
            return False
        return True
    except requests.RequestException as exc:
        print("Telegram delivery failed:", type(exc).__name__, str(exc)[:180])
        return False

def fetch_source(source):
    name = source.get("name", source.get("id", "Unknown source"))
    url = source.get("url", "")
    hosts = source.get("allowed_hosts", [])
    if not url or not hosts or not host_allowed(url, hosts):
        raise RuntimeError("Missing URL/allowed_hosts or URL host is not allowlisted")
    response = SESSION.get(url, timeout=(min(8, TIMEOUT), TIMEOUT), allow_redirects=True)
    response.raise_for_status()
    if not host_allowed(response.url, hosts):
        raise RuntimeError("Redirected outside allowlisted HTTPS hosts")
    kind = source.get("kind", "html").lower()
    content_type = response.headers.get("content-type", "").lower()
    if kind == "rss":
        feed = feedparser.parse(response.content)
        if not feed.entries and getattr(feed, "bozo", False):
            raise RuntimeError("RSS feed parsing failed")
        links = [(str(e.get("title", "")).strip(), str(e.get("link", "")).strip(), e.get("published", "")) for e in feed.entries]
    else:
        if "html" not in content_type and "xml" not in content_type:
            raise RuntimeError("Not HTML/XML; this source may require a PDF or JavaScript adapter")
        soup = BeautifulSoup(response.text, "html.parser")
        links = [(" ".join(a.get_text(" ", strip=True).split()), urljoin(response.url, a.get("href", "")), "") for a in soup.select("a[href]")]
    candidates = []
    for title, link, published in links:
        title = " ".join(title.split())
        link = link.split("#")[0].strip()
        if len(title) < 8 or not host_allowed(link, hosts):
            continue
        category = classify(title, source, link)
        if not category:
            continue
        # Avoid old items if an explicit date is present. Undated links are kept for review,
        # but are never treated as verified or published automatically.
        date_found = extract_title_date(title)
        if date_found:
            now = datetime.now(timezone.utc)
            if date_found < now - timedelta(days=MAX_AGE_DAYS) or date_found > now + timedelta(days=400):
                continue
        candidates.append({"title": title[:260], "url": link, "category": category, "source_name": name, "source_url": url, "published": str(published)[:100]})
    return candidates

def main():
    registry = load_json("checker/sources.json", {"sources": []})
    state = load_json("checker/state.json", {"seen": {}, "source_health": {}, "last_run": None})
    if not isinstance(registry, dict) or not isinstance(registry.get("sources"), list):
        sys.exit("ERROR: sources.json must contain a sources list")
    seen = state.setdefault("seen", {})
    health = state.setdefault("source_health", {})
    sources = [s for s in registry["sources"] if s.get("enabled", True)]
    now = datetime.now(timezone.utc).isoformat()
    candidates, failures, successful = [], 0, 0
    print(f"GoResultHub checker: {len(sources)} enabled sources; {WORKERS} workers")
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        jobs = {executor.submit(fetch_source, source): source for source in sources}
        for future in as_completed(jobs):
            source = jobs[future]
            source_id = source.get("id", source.get("name", "unknown"))
            try:
                items = future.result()
                successful += 1
                fresh = []
                for item in items:
                    key = hashlib.sha256(item["url"].encode("utf-8")).hexdigest()[:24]
                    if key in seen:
                        continue
                    seen[key] = {"first_seen": now, "source_id": source_id, "url": item["url"]}
                    item["id"] = key
                    fresh.append(item)
                candidates.extend(fresh)
                health[source_id] = {"status": "ok", "checked_at": now, "new_candidates": len(fresh)}
                print(f"OK {source.get('name', source_id)}: {len(fresh)} new candidates")
            except Exception as exc:
                failures += 1
                health[source_id] = {"status": "failed", "checked_at": now, "error": f"{type(exc).__name__}: {str(exc)[:250]}"}
                print(f"FAIL {source.get('name', source_id)}: {type(exc).__name__}: {str(exc)[:250]}")
    state.update({"last_run": now, "last_run_failures": failures, "last_run_successful_sources": successful, "last_run_new_candidates": len(candidates), "source_registry_count": len(sources)})
    save_json("checker/state.json", state)

    # Publish detected official-source links into the website feed as UNVERIFIED
    # discoveries. This makes the site update automatically without falsely
    # claiming the checker has confirmed a result declaration.
    results = load_json("site/data/results.json", [])
    if not isinstance(results, list):
        print("WARNING: site/data/results.json is not a list; skipping website feed update")
        results = []
    existing_urls = {str(x.get("url") or x.get("official_url") or "").split("#")[0] for x in results if isinstance(x, dict)}
    published_to_site = 0
    for item in candidates:
        item_url = str(item.get("url", "")).split("#")[0]
        if not item_url or item_url in existing_urls:
            continue
        source = next((s for s in sources if s.get("name") == item.get("source_name")), {})
        categories = source.get("categories", []) if isinstance(source, dict) else []
        exam_family = str(source.get("exam_category") or source.get("family") or "Central / State Exam Updates")
        region = str(source.get("region") or "All India")
        entry = {
            "id": "live-" + item.get("id", hashlib.sha256(item_url.encode("utf-8")).hexdigest()[:24]),
            "title": item.get("title", "Official exam update"),
            "exam": item.get("title", "Official exam update"),
            "exam_category": exam_family,
            "category": item.get("category", "notification"),
            "source_name": item.get("source_name", "Official authority"),
            "authority": item.get("source_name", "Official authority"),
            "url": item_url,
            "official_url": item_url,
            "region": region,
            "state": "",
            "description": "Automatically detected link from an official authority page. Check the authority website to confirm the notice, exam, and applicable date.",
            "detected_at": now,
            "verified": False,
            "archive": False,
            "auto_detected": True
        }
        results.append(entry)
        existing_urls.add(item_url)
        published_to_site += 1
    if published_to_site:
        # Keep the feed manageable while retaining the latest discoveries first.
        results.sort(key=lambda x: str(x.get("detected_at", "")), reverse=True)
        save_json("site/data/results.json", results[:1000])
    print(f"Website feed: {published_to_site} new unverified official-source links added")

    # Candidate links are also sent to Telegram for private review.
    if candidates:
        print(f"Found {len(candidates)} new candidate links for private review")
    else:
        print("No new candidates passed the filters")

    # Explicitly approved items are read from checker/approved.json.
    # Approval means a human checked the live official notice; the code cannot prove that itself.
    approval_data = load_json("checker/approved.json", {"pending": []})
    pending = approval_data.get("pending", []) if isinstance(approval_data, dict) else []
    if not isinstance(pending, list):
        sys.exit("ERROR: checker/approved.json must contain a pending list")
    remaining, public_posts = [], 0
    for item in pending:
        if not isinstance(item, dict):
            continue
        if item.get("approved") is not True:
            remaining.append(item)
            continue
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        source_name = str(item.get("source_name", "")).strip()
        category = str(item.get("category", "")).strip()
        source = next((s for s in sources if s.get("name") == source_name), None)
        hosts = source.get("allowed_hosts", []) if source else []
        if not title or not category or not source or not host_allowed(url, hosts):
            print("Rejected approved item: missing title/category or source host mismatch")
            remaining.append(item)
            continue
        if not CHANNEL:
            print("TG_CHANNEL missing; approved item kept pending")
            remaining.append(item)
            continue
        message = (f"📢 GoResultHub | Exam Update\n\nAuthority: {source_name}\nUpdate type: {category.replace('_', ' ').title()}\n\n{title}\n\nOfficial source:\n{url}\n\nPlease verify candidate-specific details on the official portal.")
        if telegram_send(CHANNEL, message):
            public_posts += 1
            print("Published manually approved item:", title)
        else:
            remaining.append(item)
    save_json("checker/approved.json", {"pending": remaining})
    summary = (
        "GoResultHub | CHECKER RUN SUMMARY\n\n"
        f"Checked (UTC): {now}\n"
        f"Enabled sources: {len(sources)}\n"
        f"Successful sources: {successful}\n"
        f"Failed sources: {failures}\n"
        f"New candidate links: {len(candidates)}\n"
        f"Public posts from approved queue: {public_posts}\n\n"
    )
    if candidates:
        summary += "New candidates need manual review; they have not been verified or published automatically.\n\n"
        for item in candidates[:MAX_REVIEW_ITEMS]:
            summary += f"• {item['source_name']} | {item['category']}\n{item['title']}\n{item['url']}\n\n"
        if len(candidates) > MAX_REVIEW_ITEMS:
            summary += f"Additional candidates omitted: {len(candidates) - MAX_REVIEW_ITEMS}\n"
    else:
        summary += "No new candidates passed the current filters on this run.\n"
    if failures:
        summary += "\nSome sources failed; this run does not represent complete coverage. Check the Actions log for errors."
    if ADMIN:
        delivered = telegram_send(ADMIN, summary)
        print("Private run summary delivered:", delivered)
    else:
        print("TG_ADMIN missing; cannot send private run summary")
    print(f"SUMMARY: successful_sources={successful}; failed_sources={failures}; new_candidates={len(candidates)}; public_posts={public_posts}")
    if sources and successful == 0:
        sys.exit("ERROR: no source could be checked successfully")

if __name__ == "__main__":
    main()
