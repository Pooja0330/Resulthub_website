import os
import json
import re
import hashlib
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import feedparser
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def path(name):
    return os.path.join(ROOT, name)

def load(name, default):
    try:
        with open(path(name), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save(name, data):
    target = path(name)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    temp = target + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp, target)

TOKEN = os.getenv("TG_TOKEN", "").strip()
ADMIN = os.getenv("TG_ADMIN", "").strip()
CHANNEL = os.getenv("TG_CHANNEL", "").strip()
AUTO = os.getenv("AUTO_PUBLISH", "0").strip() == "1"

TIMEOUT = max(4, min(int(os.getenv("SOURCE_TIMEOUT_SECONDS", "8")), 20))
WORKERS = max(2, min(int(os.getenv("SOURCE_WORKERS", "10")), 20))

HEADERS = {
    "User-Agent": "GoResultHubMonitor/2.0",
    "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8"
}

# Categories are deliberately limited to exam-related announcements.
RULES = [
    ("result", r"\b(results?|scorecards?|marks lists?|rank cards?|rank lists?)\b"),
    ("merit_list", r"\b(merit list|selection list|selected candidates|final selection|qualified candidates|provisional selection|panel list|allotment list)\b"),
    ("cutoff", r"\b(cut.?off|cutoff)\b"),
    ("admit_card", r"\b(admit cards?|hall tickets?|call letters?|exam city|city intimation)\b"),
    ("answer_key", r"\b(answer keys?|response sheets?|objection tracker)\b"),
    ("exam_schedule", r"\b(exam dates?|examination dates?|exam schedule|examination schedule|date sheet|time table|timetable|exam calendar)\b"),
    ("notification", r"\b(examination notification|exam notification|recruitment notification|vacancy notification|information bulletin|application dates|registration open|apply online|corrigendum)\b")
]

SKIP = re.compile(
    r"\b(tender|quotation|vendor|procurement|press release|media advisory|"
    r"annual report|privacy policy|photo gallery|faculty appointment|"
    r"associate professor|assistant professor|professor recruitment|"
    r"guest faculty|non.?teaching staff|estate section|classroom booking)\b",
    re.I
)

EXAM_CONTEXT = re.compile(
    r"\b(exam|examination|entrance|competitive|recruitment|civil services|"
    r"upsc|ssc|ibps|sbi|rrb|railway|nta|jee|neet|cuet|gate|clerk|"
    r"probationary officer|group d|alp|technician|police constable|"
    r"public service commission|board exam|board examination|ugc net|"
    r"set exam|teacher eligibility|tet|ctet|prelims|mains examination|"
    r"admission test|university examination)\b",
    re.I
)

def allowed(url, hosts):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        return (
            parsed.scheme == "https"
            and bool(host)
            and any(host == h.lower() or host.endswith("." + h.lower())
                    for h in hosts)
        )
    except Exception:
        return False

def cat(text):
    if not text or SKIP.search(text):
        return None

    # Avoid generic notices unrelated to exams.
    if not EXAM_CONTEXT.search(text):
        return None

    for category, pattern in RULES:
        if re.search(pattern, text, re.I):
            return category

    return None

def send(chat, message):
    if not TOKEN or not chat:
        return False

    try:
        response = requests.post(
            "https://api.telegram.org/bot" + TOKEN + "/sendMessage",
            json={
                "chat_id": chat,
                "text": message[:3900],
                "disable_web_page_preview": True
            },
            timeout=(4, 10)
        )
        response.raise_for_status()
        return bool(response.json().get("ok"))
    except Exception as exc:
        print("Telegram delivery error:", type(exc).__name__, str(exc)[:200])
        return False

def collect(source):
    response = requests.get(
        source["url"],
        headers=HEADERS,
        timeout=(4, TIMEOUT)
    )
    response.raise_for_status()

    hosts = source.get("allowed_hosts", [])
    if not allowed(response.url, hosts):
        raise RuntimeError("Redirected outside allowlisted HTTPS hosts")

    if source.get("kind") == "rss":
        feed = feedparser.parse(response.content)
        if not feed.entries and getattr(feed, "bozo", False):
            raise RuntimeError("RSS feed could not be parsed")

        links = [
            (entry.get("title", ""), entry.get("link", ""))
            for entry in feed.entries
        ]
    else:
        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type and "xml" not in content_type:
            raise RuntimeError("Unsupported content type; needs a dedicated adapter")

        soup = BeautifulSoup(response.text, "html.parser")
        links = [
            (
                " ".join(anchor.get_text(" ", strip=True).split()),
                urljoin(response.url, anchor.get("href", ""))
            )
            for anchor in soup.select("a[href]")
        ]

    candidates = []
    for title, url in links:
        title = " ".join(str(title).split())
        url = str(url).split("#")[0]
        category = cat(title)

        if title and category and allowed(url, hosts):
            candidates.append({
                "title": title[:280],
                "url": url,
                "category": category
            })

    return candidates

def check_one(source):
    try:
        return source, collect(source), None
    except Exception as exc:
        return source, [], f"{type(exc).__name__}: {str(exc)}"[:400]

def main():
    registry = load("checker/sources.json", {"sources": []})
    state = load("checker/state.json", {
        "seen": {},
        "last_run": None,
        "source_health": {}
    })

    if not isinstance(registry, dict) or not isinstance(registry.get("sources"), list):
        print("ERROR: checker/sources.json must contain a sources list")
        sys.exit(2)

    seen = state.setdefault("seen", {})
    health = state.setdefault("source_health", {})
    results = load("site/data/results.json", [])

    if not isinstance(results, list):
        print("ERROR: site/data/results.json must be a JSON array")
        sys.exit(2)

    enabled = [
        source for source in registry["sources"]
        if source.get("enabled", True)
        and source.get("url")
        and source.get("allowed_hosts")
    ]

    now = datetime.now(timezone.utc).isoformat()
    found = []
    failures = 0

    print(
        f"Checking {len(enabled)} sources with {WORKERS} workers; "
        f"timeout={TIMEOUT}s; TLS verification enabled"
    )

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(check_one, source) for source in enabled]

        for future in as_completed(futures):
            source, items, error = future.result()
            source_id = source.get("id", source.get("name", "unknown"))

            if error:
                failures += 1
                health[source_id] = {
                    "status": "failed",
                    "checked_at": now,
                    "error": error
                }
                print(f"FAIL {source.get('name', source_id)}: {error}")
                continue

            fresh = []
            for item in items:
                key = hashlib.sha256(item["url"].encode()).hexdigest()[:20]

                if key in seen:
                    continue

                seen[key] = {
                    "source": source_id,
                    "first_seen": now,
                    "url": item["url"]
                }

                item.update({
                    "id": key,
                    "source_id": source_id,
                    "source_name": source.get("name", source_id),
                    "source_url": source["url"],
                    "detected_at": now,
                    "verified": False,
                    "status": "review"
                })
                fresh.append(item)

            found.extend(fresh)
            health[source_id] = {
                "status": "ok",
                "checked_at": now,
                "matches": len(items),
                "new": len(fresh)
            }
            print(
                f"OK {source.get('name', source_id)}: "
                f"{len(items)} matches, {len(fresh)} new"
            )

    # Keep review drafts private. AUTO_PUBLISH is intentionally opt-in.
    if found and not AUTO:
        for item in found:
            message = (
                "REVIEW DRAFT — NOT PUBLISHED\n"
                f"{item['source_name']} | {item['category']}\n"
                f"{item['title']}\n"
                f"Official source page: {item['url']}\n\n"
                "This link is unverified. Review it before sharing."
            )
            if ADMIN:
                send(ADMIN, message)

        print("REVIEW: drafts sent to admin; nothing published")

    elif found and AUTO:
        # Explicit opt-in still does not prove a candidate is genuine.
        print(
            "WARNING: AUTO_PUBLISH=1 but candidates remain unverified. "
            "No candidates were published by this safe version."
        )

    else:
        print("No new candidate links")

    state["last_run"] = now
    state["last_run_failures"] = failures
    state["last_run_new_candidates"] = len(found)
    state["source_registry_count"] = len(enabled)

    save("checker/state.json", state)

    print(
        f"Finished; sources={len(enabled)}; failures={failures}; "
        f"new_candidates={len(found)}; AUTO_PUBLISH={AUTO}"
    )

if __name__ == "__main__":
    main()
