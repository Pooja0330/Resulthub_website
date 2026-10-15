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

# This checker is review-only. It never publishes results automatically.
AUTO_PUBLISH = False

TIMEOUT = max(
    4, min(int(os.getenv("SOURCE_TIMEOUT_SECONDS", "8")), 20)
)
WORKERS = max(
    2, min(int(os.getenv("SOURCE_WORKERS", "10")), 20)
)
MAX_REVIEW_ITEMS = 12
MAX_AGE_DAYS = 90

HEADERS = {
    "User-Agent": "GoResultHubExamMonitor/2.1",
    "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8"
}

EXAM_CONTEXT = re.compile(
    r"\b(exam|examination|entrance|competitive examination|"
    r"civil services|upsc|ssc|ibps|sbi|rrb|railway recruitment|"
    r"nta|jee|neet|cuet|gate|clerk|probationary officer|"
    r"group d|assistant loco pilot|technician recruitment|"
    r"police recruitment|public service commission|"
    r"board examination|ugc net|ctet|tet|teacher eligibility test|"
    r"admit card|hall ticket|answer key|scorecard|merit list|"
    r"exam result|examination result|recruitment examination|"
    r"prelims|preliminary examination|mains examination)\b",
    re.I
)

SKIP = re.compile(
    r"\b(tender|quotation|procurement|vendor registration|"
    r"privacy policy|photo gallery|annual report|press release|"
    r"media advisory|estate section|classroom booking|"
    r"associate professor|assistant professor|professor appointment|"
    r"guest faculty|non.?teaching recruitment|"
    r"school relocation|change of school venue|"
    r"office order|holiday list|meeting notice)\b",
    re.I
)

RULES = [
    ("result", re.compile(
        r"\b(result declared|exam results?|examination results?|"
        r"scorecards?|marks list|rank list|rank card)\b", re.I
    )),
    ("merit_list", re.compile(
        r"\b(merit list|final selection|selected candidates|"
        r"qualified candidates|provisional selection|"
        r"selection list|final panel|allotment list)\b", re.I
    )),
    ("cutoff", re.compile(
        r"\b(cut.?off marks?|cutoff marks?|qualifying marks?)\b", re.I
    )),
    ("admit_card", re.compile(
        r"\b(admit cards?|hall tickets?|call letters?|"
        r"exam city intimation|city intimation slip)\b", re.I
    )),
    ("answer_key", re.compile(
        r"\b(answer keys?|response sheets?|objection tracker)\b", re.I
    )),
    ("exam_schedule", re.compile(
        r"\b(exam date|examination date|exam schedule|"
        r"examination schedule|date sheet|exam calendar|"
        r"exam postponement|exam rescheduled|"
        r"examination postponed|examination rescheduled)\b", re.I
    )),
    ("notification", re.compile(
        r"\b(exam notification|examination notification|"
        r"recruitment notification|recruitment advertisement|"
        r"vacancy notification|information bulletin|"
        r"application dates|registration opens|apply online|"
        r"online application|application notice)\b", re.I
    ))
]

# Recognize common explicit dates in link titles.
DATE_PATTERNS = [
    re.compile(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b"),
    re.compile(
        r"\b(\d{1,2})\s+"
        r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
        r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
        r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        r"\s+(20\d{2})\b", re.I
    )
]

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12
}

def host_allowed(url, allowed_hosts):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()

        if parsed.scheme != "https" or not host:
            return False

        return any(
            host == str(item).lower()
            or host.endswith("." + str(item).lower())
            for item in allowed_hosts
            if item
        )
    except Exception:
        return False

def extract_title_date(text):
    for pattern in DATE_PATTERNS:
        match = pattern.search(text or "")
        if not match:
            continue

        try:
            groups = match.groups()

            if pattern is DATE_PATTERNS[0]:
                year, month, day = map(int, groups)
            elif pattern is DATE_PATTERNS[1]:
                day, month, year = map(int, groups)
            else:
                day = int(groups[0])
                month = MONTHS[groups[1][:3].lower()]
                year = int(groups[2])

            return datetime(year, month, day, tzinfo=timezone.utc)
        except (ValueError, IndexError):
            continue

    return None

def is_recent_enough(title):
    date_found = extract_title_date(title)

    # If a recognizable date is present, reject old or implausibly future dates.
    # Undated titles are not automatically considered current.
    if date_found is None:
        return None

    now = datetime.now(timezone.utc)

    if date_found < now - timedelta(days=MAX_AGE_DAYS):
        return False

    if date_found > now + timedelta(days=400):
        return False

    return True

def classify(title, source_name):
    if not title:
        return None

    if SKIP.search(title):
        return None

    # The title itself must contain exam context.
    # A generic university or department name is not sufficient.
    if not EXAM_CONTEXT.search(title):
        return None

    for category, pattern in RULES:
        if pattern.search(title):
            return category

    return None

def telegram_send(chat_id, message):
    if not TOKEN or not chat_id:
        return False

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message[:3900],
                "disable_web_page_preview": True
            },
            timeout=(4, 10)
        )
        response.raise_for_status()

        body = response.json()
        if not body.get("ok"):
            print("Telegram API rejected message")
            return False

        return True
    except Exception as exc:
        print(
            "Telegram delivery failed:",
            type(exc).__name__,
            str(exc)[:180]
        )
        return False

def fetch_source(source):
    name = source.get("name", source.get("id", "Unknown source"))
    url = source.get("url", "")
    allowed_hosts = source.get("allowed_hosts", [])

    if isinstance(allowed_hosts, str):
        allowed_hosts = [allowed_hosts]

    if not url or not allowed_hosts:
        raise RuntimeError("Missing URL or allowed_hosts")

    if not host_allowed(url, allowed_hosts):
        raise RuntimeError("Configured URL is not an allowlisted HTTPS URL")

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=(4, TIMEOUT),
        allow_redirects=True
    )
    response.raise_for_status()

    if not host_allowed(response.url, allowed_hosts):
        raise RuntimeError("Redirected outside allowlisted HTTPS hosts")

    content_type = response.headers.get("content-type", "").lower()
    kind = source.get("kind", "html").lower()

    if kind == "rss":
        feed = feedparser.parse(response.content)

        if not feed.entries and getattr(feed, "bozo", False):
            raise RuntimeError("RSS feed parsing failed")

        links = [
            (
                str(entry.get("title", "")).strip(),
                str(entry.get("link", "")).strip()
            )
            for entry in feed.entries
        ]
    else:
        if "html" not in content_type and "xml" not in content_type:
            raise RuntimeError(
                "Source is not HTML/XML; a dedicated adapter may be needed"
            )

        soup = BeautifulSoup(response.text, "html.parser")
        links = []

        for anchor in soup.select("a[href]"):
            title = " ".join(anchor.get_text(" ", strip=True).split())
            link = urljoin(response.url, anchor.get("href", ""))
            links.append((title, link))

    candidates = []
    for title, link in links:
        title = " ".join(title.split())
        link = link.split("#")[0].strip()

        if not title or len(title) < 8:
            continue

        if not host_allowed(link, allowed_hosts):
            continue

        category = classify(title, name)
        if not category:
            continue

        recent = is_recent_enough(title)

        # Do not alert on clearly old or clearly future-dated titles.
        # Undated links are held back to avoid flooding admins with archives.
        if recent is not True:
            continue

        candidates.append({
            "title": title[:260],
            "url": link,
            "category": category,
            "source_name": name,
            "source_url": url
        })

    return candidates

def test_channel():
    if not CHANNEL:
        print("ERROR: TG_CHANNEL is empty")
        sys.exit(1)

    ok = telegram_send(
        CHANNEL,
        "GoResultHub channel delivery test. No exam result is being announced."
    )

    if not ok:
        print("ERROR: Channel test failed. Check TG_CHANNEL and bot permissions.")
        sys.exit(1)

    print("SUCCESS: Test message posted to the channel.")
    
def main():
    registry = load_json("checker/sources.json", {"sources": []})
    state = load_json("checker/state.json", {
        "seen": {},
        "source_health": {},
        "last_run": None
    })

    if not isinstance(registry, dict) or not isinstance(
        registry.get("sources"), list
    ):
        print("ERROR: sources.json must contain a 'sources' list")
        sys.exit(2)

    seen = state.setdefault("seen", {})
    health = state.setdefault("source_health", {})

    sources = [
        source for source in registry["sources"]
        if source.get("enabled", True)
    ]

    now = datetime.now(timezone.utc).isoformat()
    candidates = []
    failures = 0
    successful = 0

    print(
        f"GoResultHub checker: {len(sources)} enabled sources; "
        f"{WORKERS} workers; timeout={TIMEOUT}s"
    )

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        jobs = {
            executor.submit(fetch_source, source): source
            for source in sources
        }

        for future in as_completed(jobs):
            source = jobs[future]
            source_id = source.get("id", source.get("name", "unknown"))

            try:
                items = future.result()
                successful += 1
                fresh = []

                for item in items:
                    key = hashlib.sha256(
                        item["url"].encode("utf-8")
                    ).hexdigest()[:24]

                    if key in seen:
                        continue

                    # Mark only candidates that pass the relevance/date filters.
                    seen[key] = {
                        "first_seen": now,
                        "source_id": source_id,
                        "url": item["url"]
                    }
                    item["id"] = key
                    fresh.append(item)

                candidates.extend(fresh)
                health[source_id] = {
                    "status": "ok",
                    "checked_at": now,
                    "new_candidates": len(fresh)
                }

                print(
                    f"OK {source.get('name', source_id)}: "
                    f"{len(fresh)} new review candidates"
                )

            except Exception as exc:
                failures += 1
                health[source_id] = {
                    "status": "failed",
                    "checked_at": now,
                    "error": f"{type(exc).__name__}: {str(exc)[:250]}"
                }
                print(
                    f"FAIL {source.get('name', source_id)}: "
                    f"{type(exc).__name__}: {str(exc)[:250]}"
                )

    # Save monitoring state; never write candidate links to the public website.
    state["last_run"] = now
    state["last_run_failures"] = failures
    state["last_run_successful_sources"] = successful
    state["last_run_new_candidates"] = len(candidates)
    state["source_registry_count"] = len(sources)
    save_json("checker/state.json", state)

    # One compact private digest per run, not one message per link.
    if candidates and ADMIN:
        lines = [
            "GoResultHub — PRIVATE REVIEW DIGEST",
            f"Checked: {now}",
            f"New candidates: {len(candidates)}",
            "",
            "These are candidate links, not verified announcements.",
            "Confirm the date, exam name and official notice before publishing.",
            ""
        ]

        for item in candidates[:MAX_REVIEW_ITEMS]:
            lines.extend([
                f"• {item['source_name']} — {item['category']}",
                item["title"],
                item["url"],
                ""
            ])

        if len(candidates) > MAX_REVIEW_ITEMS:
            lines.append(
                f"Additional candidates omitted from this message: "
                f"{len(candidates) - MAX_REVIEW_ITEMS}"
            )

        lines.extend([
            "",
            "No public channel posts were made."
        ])

        delivered = telegram_send(ADMIN, "\n".join(lines))
        print("Private review digest delivered:", delivered)

    elif candidates:
        print("Candidates found, but TG_ADMIN is not configured; no digest sent.")
    else:
        print("No new candidates passed the relevance and date filters.")

    print(
        f"SUMMARY: successful_sources={successful}; "
        f"failed_sources={failures}; "
        f"new_candidates={len(candidates)}; "
        f"public_posts=0"
    )

    # A run with zero successful sources must fail visibly in GitHub Actions.
    if sources and successful == 0:
        print("ERROR: no source could be checked successfully")
        sys.exit(1)

if __name__ == "__main__":
    main()
