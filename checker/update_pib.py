#!/usr/bin/env python3
"""Fetch PIB press releases independently of the longer exam-source scan."""
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

import feedparser
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "site" / "data" / "pib-news.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GoResultHubOfficialFeed/1.0)",
    "Accept": "application/rss+xml,application/xml,text/html;q=0.9,*/*;q=0.8",
}
FEEDS = [
    "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1",
    "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3",
    "https://pib.gov.in/RssMain.aspx?ModId=18&Lang=1&Regid=1",
]
HTML_LISTING = "https://www.pib.gov.in/AllRelease.aspx?lang=1&reg=1"
RELEASE_PATH = re.compile(r"^/(?:PressReleaseIframePage|PressReleasePage|PressReleaseDetail)\.aspx$", re.I)


def official_release_url(raw, base):
    url = urljoin(base, str(raw or "").strip()).split("#", 1)[0]
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ("pib.gov.in", "www.pib.gov.in"):
        return ""
    if not RELEASE_PATH.fullmatch(parsed.path):
        return ""
    prid = parse_qs(parsed.query, keep_blank_values=True).get("PRID", [""])[0]
    if not prid.isdigit():
        return ""
    return "https://www.pib.gov.in/PressReleasePage.aspx?PRID=" + prid


def item_record(title, raw_url, base, published=""):
    title = " ".join(str(title or "").split())
    url = official_release_url(raw_url, base)
    if len(title) < 12 or not url:
        return None
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    return {
        "id": "pib-" + digest,
        "title": title,
        "url": url,
        "official_url": url,
        "source_id": "pib-independent-feed",
        "source_name": "Press Information Bureau (PIB) — Official Press Release",
        "authority": "Press Information Bureau (PIB)",
        "exam_category": "Government & PIB Updates",
        "category": "notification",
        "region": "Central",
        "state": "",
        "published": str(published or ""),
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "archive": False,
        "verified": True,
    }


def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    found = {}
    errors = []
    previous_by_url = {}
    if OUTPUT.exists():
        try:
            previous_data = json.loads(OUTPUT.read_text(encoding="utf-8"))
            if isinstance(previous_data, list):
                previous_by_url = {
                    str(item.get("url") or item.get("official_url") or ""): item
                    for item in previous_data if isinstance(item, dict)
                }
        except (OSError, ValueError):
            previous_by_url = {}
    for url in FEEDS:
        try:
            response = session.get(url, timeout=12)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if not feed.entries and getattr(feed, "bozo", False):
                raise ValueError("RSS parse failed")
            for entry in feed.entries:
                item = item_record(entry.get("title"), entry.get("link"), response.url,
                                   entry.get("published", entry.get("updated", "")))
                if item:
                    found[item["url"]] = item
        except Exception as exc:
            errors.append(urlparse(url).path + ": " + type(exc).__name__)
    try:
        response = session.get(HTML_LISTING, timeout=12)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.select("a[href]"):
            title = " ".join(anchor.get_text(" ", strip=True).split())
            item = item_record(title, anchor.get("href"), response.url)
            if item:
                found[item["url"]] = item
    except Exception as exc:
        errors.append("AllRelease: " + type(exc).__name__)

    if not found:
        # Keep last known-good data instead of replacing it with an empty feed
        # during a transient PIB outage.
        if OUTPUT.exists():
            try:
                previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
                if isinstance(previous, list) and previous:
                    print("PIB sources unavailable; preserved last known-good feed. " + "; ".join(errors))
                    return
            except (OSError, ValueError):
                pass
        raise SystemExit("No valid official PIB release URLs retrieved. " + "; ".join(errors))

    for item in found.values():
        previous = previous_by_url.get(item["url"], {})
        if previous.get("detected_at"):
            item["detected_at"] = previous["detected_at"]
    records = sorted(found.values(), key=lambda item: item.get("published", ""), reverse=True)[:100]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)
    print(f"Saved {len(records)} distinct official PIB releases.")
    if errors:
        print("Some PIB endpoints were unavailable: " + "; ".join(errors))


if __name__ == "__main__":
    main()
