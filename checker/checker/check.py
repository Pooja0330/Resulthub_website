"""Safer ResultHub checker.

Reads checker/sources.json, detects new result-like links, writes site/results.json
when AUTO_PUBLISH=1, and sends Telegram alerts. This is a heuristic, not a guarantee
that an exam result has been declared; review sources and keep auto-publish disabled
until the source list has been tested.
"""
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "checker" / "sources.json"
STATE = ROOT / "checker" / "state.json"
RES = ROOT / "site" / "results.json"

AUTO = os.getenv("AUTO_PUBLISH", "0").strip() == "1"
TOKEN = os.getenv("TG_TOKEN", "").strip()
CHANNEL = os.getenv("TG_CHANNEL", "").strip()
ADMIN = os.getenv("TG_ADMIN", "").strip()
TIMEOUT = (8, 20)
MAX_NEW_PER_SOURCE = int(os.getenv("MAX_NEW_PER_SOURCE", "5"))
USER_AGENT = "GoResultHubBot/1.0 (+https://goresulthub.com; official-result-link-monitor)"
WANT = re.compile(r"\b(result|merit list|score.?card|final selection|cut.?off|declar|qualified candidates|selected candidates)\b", re.I)
SKIP = re.compile(r"\b(admit card|answer key|syllabus|apply online|application form|vacanc(?:y|ies)|exam city|hall ticket|corrigendum|tender|recruitment notice)\b", re.I)
CATEGORY_RULES = [
    (r"UPSC|IAS|IPS|NDA|CDS|AFCAT|agniveer|army|navy", "Civil Services & Defence"),
    (r"NEET|JEE|CUET|CAT|CLAT|JIPMAT|CMAT|BITSAT|AIIMS", "Entrance"),
    (r"UGC|CSIR|NET|TET|teacher|CTET", "Teaching & NET"),
    (r"IBPS|SBI PO|SBI Clerk|RBI|bank", "Banking"),
    (r"SSC|RRB|railway", "SSC & Railways"),
    (r"CA Final|CA Inter|ICAI|ICSI|CS Executive|CMA", "CA / CS"),
    (r"GATE|engineering", "Engineering"),
    (r"GRE|GMAT|TOEFL|IELTS|SAT", "Abroad Exams"),
    (r"board|CBSE|ICSE|ISC|class 10|class 12", "Boards"),
    (r"PSC|UPPSC|BPSC|MPSC|RPSC|MPPSC|CGPSC|TNPSC|OPSC|JPSC", "State PSC"),
]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})


def load_json(path, default):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def telegram(chat, message):
    if not TOKEN or not chat:
        print("Telegram skipped (TG_TOKEN or chat target missing).")
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": chat, "text": message[:4000], "disable_web_page_preview": True},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(payload.get("description", "Telegram API returned ok=false"))
        return True
    except Exception as exc:
        print(f"Telegram send failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


def category(text, default):
    for pattern, label in CATEGORY_RULES:
        if re.search(pattern, text, re.I):
            return label
    return default or "Other Govt Jobs"


def extract_links(html, base_url, allowed_hosts):
    soup = BeautifulSoup(html, "html.parser")
    found = {}
    for a in soup.find_all("a", href=True):
        title = " ".join(a.get_text(" ", strip=True).split())
        href = a.get("href", "").strip()
        if len(title) < 12 or len(title) > 200 or not WANT.search(title) or SKIP.search(title):
            continue
        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            continue
        # Prevent a source page from making the checker publish unrelated third-party links.
        if not any(parsed.hostname == host or parsed.hostname.endswith("." + host) for host in allowed_hosts):
            continue
        if parsed.hostname.lower() in {"facebook.com", "x.com", "twitter.com", "youtube.com"}:
            continue
        found[url] = title
    return found


def main():
    sources = load_json(SRC, [])
    state = load_json(STATE, {"seen": {}, "fails": {}, "last_run": None})
    results = load_json(RES, [])
    if not isinstance(sources, list):
        raise SystemExit("checker/sources.json must contain a JSON array.")
    if not isinstance(results, list):
        raise SystemExit("site/results.json must contain a JSON array.")

    today = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y")
    discovered = []
    for source in sources:
        name = source.get("name", "Unnamed source")
        source_url = source.get("url", "")
        parsed = urlparse(source_url)
        if parsed.scheme != "https" or not parsed.hostname:
            print(f"SKIP invalid/non-HTTPS source: {name}")
            continue
        allowed_hosts = set(source.get("allowed_hosts", [])) | {parsed.hostname.lower()}
        try:
            response = SESSION.get(source_url, timeout=TIMEOUT)
            response.raise_for_status()
            if "text/html" not in response.headers.get("Content-Type", "text/html").lower():
                print(f"SKIP non-HTML source: {name}")
                continue
            found = extract_links(response.text, response.url, allowed_hosts)
            state.setdefault("fails", {})[name] = 0
        except Exception as exc:
            count = state.setdefault("fails", {}).get(name, 0) + 1
            state["fails"][name] = count
            print(f"FAIL {name}: {type(exc).__name__}: {exc}", file=sys.stderr)
            if count == 3:
                telegram(ADMIN, f"GoResultHub checker warning: {name} failed 3 consecutive checks. Please review the source URL.")
            continue

        old = set(state.setdefault("seen", {}).get(name, []))
        # On first run, baseline current links rather than blasting old links as new results.
        if name not in state["seen"]:
            state["seen"][name] = sorted(found)
            print(f"BASELINE {name}: recorded {len(found)} existing result-like links; no alerts.")
            continue

        fresh = [(url, title) for url, title in found.items() if url not in old]
        if len(fresh) > MAX_NEW_PER_SOURCE:
            telegram(ADMIN, f"GoResultHub review needed: {name} produced {len(fresh)} new result-like links. Nothing from this source was auto-published; check for a website layout change.")
            print(f"REVIEW {name}: {len(fresh)} new links exceeds limit {MAX_NEW_PER_SOURCE}")
            # Do not mark these as seen, so the owner can inspect and run again after review.
            continue

        for url, title in fresh:
            discovered.append({
                "t": title,
                "c": category(title + " " + name, source.get("cat")),
                "d": today,
                "u": url,
                "info": f"New result-related link detected on the official {name} source. Verify the notice before relying on it.",
                "source": name,
                "verified": False,
            })
        state["seen"][name] = sorted(old | set(found.keys()))
        print(f"OK {name}: {len(found)} matching links; {len(fresh)} new.")

    # Avoid duplicate URLs already on the website, even if sources overlap.
    existing_urls = {item.get("u") for item in results if isinstance(item, dict)}
    unique = []
    for item in discovered:
        if item["u"] not in existing_urls:
            unique.append(item)
            existing_urls.add(item["u"])

    for item in unique:
        title = item["t"]
        url = item["u"]
        if AUTO:
            # The item is still explicitly labelled as detected/unverified.
            results.insert(0, item)
            telegram(CHANNEL, f"Possible result update — verify before sharing\n{title}\nOfficial source: {url}\nDetected: {today}\nGoResultHub does not collect candidate credentials.")
        else:
            telegram(ADMIN, f"DRAFT — review before publishing\n{title}\n{url}\nDetected: {today}\nAdd only after confirming the official notice.")

    if AUTO and unique:
        save_json(RES, results[:250])

    state["last_run"] = dt.datetime.now(dt.timezone.utc).isoformat()
    save_json(STATE, state)
    print(f"Finished: {len(unique)} new unique links; AUTO_PUBLISH={AUTO}.")
    if not TOKEN:
        print("NOTICE: TG_TOKEN is not configured; Telegram alerts are disabled.")


if __name__ == "__main__":
    main()
