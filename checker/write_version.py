#!/usr/bin/env python3
"""Write site/data/version.json: a tiny (~250 byte) heartbeat for the website.

Browsers poll THIS file every ~20 seconds instead of downloading the 1.8 MB
results.json. They fetch the big feeds only when `hash` changes, which keeps
GitHub Pages bandwidth low and makes new notices appear within seconds of a
deploy. `hash` covers feed CONTENT only, so a scan that finds nothing new does
not trigger any re-download.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site" / "data"


def main():
    digest = hashlib.sha1()
    count = 0
    for name in ("results.json", "pib-news.json"):
        path = DATA / name
        raw = path.read_bytes() if path.exists() else b""
        digest.update(raw)
        try:
            value = json.loads(raw.decode("utf-8")) if raw else []
            if name == "results.json" and isinstance(value, list):
                count = len(value)
        except ValueError:
            pass
    last_checked = ""
    try:
        last_checked = json.loads((DATA / "status.json").read_text(encoding="utf-8")).get("last_checked_at", "")
    except (OSError, ValueError):
        pass
    payload = {
        "hash": digest.hexdigest()[:16],
        "results_count": count,
        "last_checked_at": last_checked,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (DATA / "version.json").write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print("version.json written:", payload)


if __name__ == "__main__":
    main()
