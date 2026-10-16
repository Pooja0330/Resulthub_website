# GoResultHub checker: direct notice links plus official authority-page links.

import os
import re
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import certifi
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
        r"\b(result declared|result declaration|results of|result of|result for|final result|"
        r"provisional result|result published|result notification|exam results?|"
        r"examination results?|board exam results?|board results?|class 10 results?|class 12 results?|"
        r"ssc results?|hsc results?|scorecards?|score cards?|marks list|rank list|"
        r"rank card|result announcement)\b", re.I)),
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
        r"additional vacancies|selection process for|selection list for recruitment)\b", re.I)),
]


SKIP = re.compile(
    r"\b(tender|quotation|procurement|vendor registration|privacy policy|"
    r"photo gallery|annual report|media advisory|holiday list|meeting notice)\b", re.I
)

NAV_TITLE = re.compile(
    r"^(home|result|results|recruitment|careers?|advertisements?|"
    r"notifications?|notices?|latest news|read more|click here|"
    r"view all|view more|recruitment calendar|stages of recruitment|"
    r"reporting vacancies|detailed advertisement)$", re.I
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


def get_with_retries(url, headers=None):
    last_error = None

    # Keep a failed source from delaying the entire scheduled run.
    # Retry transient errors; use certifi's current CA bundle and never disable TLS verification.
    for attempt in range(2):
        try:
            response = requests.get(
                url,
                headers=headers or HEADERS,
                timeout=(5, min(TIMEOUT, 8)),
                allow_redirects=True,
                verify=certifi.where(),
            )

            if response.status_code in (408, 425, 429, 500, 502, 503, 504):
                if attempt < 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue

            response.raise_for_status()
            return response

        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
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


def fetch_source(source):
    name = source.get("name", source.get("id", "Unknown"))
    url = source.get("url", "")
    hosts = source.get("allowed_hosts", [])

    if not url or not hosts or not host_allowed(url, hosts):
        raise ValueError("Source URL is missing or not allowlisted")

    response = get_with_retries(url)

    if not host_allowed(response.url, hosts):
        raise ValueError("Redirected outside the official allowlist")

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
        links = [
            (
                " ".join(a.get_text(" ", strip=True).split()),
                urljoin(response.url, a.get("href", "")),
                "",
            )
            for a in soup.select("a[href]")
        ]

    found = []
    seen_urls = set()

    for title, link, published in links:
        title = " ".join(title.split())
        link = link.split("#")[0].strip()

        # Official portals often use short labels such as "Result".
        if len(title) < 4 or not host_allowed(link, hosts):
            continue

        category = classify(title)
        if not category or link in seen_urls:
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

    return found


def build_result(item, detected_at):
    # Match the JSON fields consumed by site/app.js.
    return {
        "id": item["id"],
        "title": item["title"],
        "exam": item["title"],
        "exam_category": item.get("exam_category", "Government Exams"),
        "category": item["category"],
        "source_name": item["source_name"],
        "authority": item["source_name"],
        "url": item["url"],
        "official_url": item["url"],
        "source_url": item.get("source_url", ""),
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

    # Clean old low-quality navigation links from the public website and keep
    # category labels aligned with the stricter title classifier.
    cleaned_results = []
    removed_result_rows = 0
    for item in results:
        if not isinstance(item, dict):
            removed_result_rows += 1
            continue
        title = str(item.get("title") or item.get("exam") or "").strip()
        category = classify(title)
        if not category:
            removed_result_rows += 1
            continue
        item["category"] = category
        cleaned_results.append(item)
    results = cleaned_results
    print(f"Website data cleanup: removed {removed_result_rows} generic/irrelevant rows; {len(results)} remain")

    seen = state.setdefault("seen", {})
    health = state.setdefault("source_health", {})
    pending = state.setdefault("pending_alerts", {})
    held = state.setdefault("held_alerts", {})
    # Hold existing queued items for review once; only discoveries from this run
    # can be sent automatically, preventing a large stale backlog from flooding Telegram.
    preexisting_pending_keys = set(pending.keys()) if isinstance(pending, dict) else set()

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
                    key = hashlib.sha256(
                        item["url"].encode("utf-8")
                    ).hexdigest()[:24]

                    if key in seen or key in pending or key in held:
                        continue

                    item["id"] = key
                    item["region"] = source.get("region", "Central")
                    item["state"] = source.get("state", "")
                    item["exam_category"] = source.get(
                        "exam_category",
                        source.get("name", "Government Exams"),
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

    for item in candidates:
        if item["id"] not in existing_ids:
            results.append(build_result(item, item["detected_at"]))
            existing_ids.add(item["id"])

    # Keep the old backlog for review instead of automatically drip-feeding it.
    for key in list(preexisting_pending_keys):
        record = pending.pop(key, None)
        if not record:
            continue
        item = record.get("item", {})
        title = str(item.get("title", ""))
        reason = "Existing backlog held for review after stricter filtering."
        if not classify(title):
            reason = "Generic navigation or irrelevant title; held for review."
        held[key] = {
            "item": item,
            "detected_at": record.get("detected_at", checked_at),
            "held_at": checked_at,
            "hold_reason": reason,
        }

    # Only fresh discoveries from this run can be automatically sent.
    public_sent = 0
    public_attempts = 0
    # Limit attempts as well as successful deliveries. A Telegram 429 must not
    # cause the checker to hammer the API for every queued alert.
    max_public_alerts_per_run = max(
        1, min(int(os.getenv("MAX_PUBLIC_ALERTS_PER_RUN", "5")), 5)
    )
    fresh_candidate_keys = {item.get("id") for item in candidates}
    for key in list(pending.keys()):
        if key not in fresh_candidate_keys:
            continue
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
            f"Type: {str(item.get('category', 'update')).replace('_', ' ').title()}\n\n"
            f"{item.get('title', 'New official link')}\n\n"
            + f"🌐 OFFICIAL AUTHORITY WEBSITE — open this link to browse notices:\n{source_page or 'Official website link unavailable; use the authority name to find its official portal.'}\n"
            + "\nThe direct document link is intentionally omitted from this channel message because it may open a PDF. Visit the official website to locate and confirm the notice."
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

    for approved_index, item in enumerate(approved_items):
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
        message = (
            "📢 GoResultHub | Exam Update\n\n"
            f"Authority: {item['source_name']}\n"
            f"Type: {str(item.get('category', 'update')).replace('_', ' ').title()}\n\n"
            f"{item.get('title', '')}\n\n"
            + f"🌐 OFFICIAL AUTHORITY WEBSITE — open this link to browse notices:\n{source_page or 'Official website link unavailable; use the authority name to find its official portal.'}\n"
            + "\nThe direct document link is intentionally omitted from this channel message because it may open a PDF. Visit the official website to locate and confirm the notice."
        )

        if not telegram_send(CHANNEL, message):
            remaining_approved.append(item)

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
