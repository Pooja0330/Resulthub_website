import os
import re
import json
import sys
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
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

def classify(title):
    # Sources are registered official exam/recruitment portals. Match notice titles
    # by announcement type rather than requiring every title to repeat an exam keyword.
    # Public messages are labelled as potential updates and link back to the official source.
    if not title or SKIP.search(title):
        return None
    for category, pattern in RULES:
        if pattern.search(title):
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
            timeout=(4, 12),
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
    response = requests.get(url, headers=HEADERS, timeout=(4, TIMEOUT), allow_redirects=True)
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
        category = classify(title)
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

    # Publish newly detected official-source links as clearly labelled alerts.
    # These are candidate notices, not a claim that a candidate-specific result is verified.
    public_posts = 0
    if candidates and CHANNEL:
        for item in candidates:
            message = (
                "🔔 GoResultHub | Potential Exam Update\n\n"
                f"Authority: {item['source_name']}\n"
                f"Update type: {item['category'].replace('_', ' ').title()}\n\n"
                f"{item['title']}\n\n"
                f"Official source link:\n{item['url']}\n\n"
                "Please open the official source and verify the notice before relying on it."
            )
            if telegram_send(CHANNEL, message):
                public_posts += 1
                print("Published candidate alert:", item["title"])
            else:
                print("Candidate alert delivery failed:", item["title"])
    elif candidates:
        print("TG_CHANNEL missing; candidate alerts were not published")
    else:
        print("No new candidates passed the filters")

    # Explicitly approved items are read from checker/approved.json.
    # Approval means a human checked the live official notice; the code cannot prove that itself.
    approval_data = load_json("checker/approved.json", {"pending": []})
    pending = approval_data.get("pending", []) if isinstance(approval_data, dict) else []
    if not isinstance(pending, list):
        sys.exit("ERROR: checker/approved.json must contain a pending list")
    remaining = []
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
        f"Public posts to channel: {public_posts}\n\n"
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
