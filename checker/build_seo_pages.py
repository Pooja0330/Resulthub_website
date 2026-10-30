#!/usr/bin/env python3
"""Generate crawlable GoResultHub detail pages and an up-to-date XML sitemap.

Only GoResultHub's own feed metadata is rendered. Issuing-authority URLs remain
external links; no third-party article text is copied.
"""
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
BASE = "https://goresulthub.com"
BASE_SITEMAP = [
    "/", "/state.html", "/how-to-check-exam-results.html",
    "/state-board-results.html", "/entrance-exam-updates.html",
    "/central-government-exams.html", "/about.html", "/contact.html",
    "/editorial-policy.html", "/privacy.html", "/disclaimer.html", "/terms.html",
]

def esc(value):
    return html.escape(str(value or "").strip(), quote=True)

def safe_https(value):
    value = str(value or "").strip()
    try:
        parsed = urlparse(value)
        return value if parsed.scheme == "https" and parsed.netloc else ""
    except Exception:
        return ""

def safe_json(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))

def date_value(value):
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).date().isoformat()
    except (TypeError, ValueError):
        return ""

def render_detail(item):
    ident = str(item.get("id") or "").strip()
    title = str(item.get("title") or item.get("exam") or "Exam update").strip()
    if not ident or not re.fullmatch(r"[A-Za-z0-9_-]{6,80}", ident):
        return ""
    canonical = f"{BASE}/updates/{ident}.html"
    authority = str(item.get("source_name") or item.get("authority") or "Issuing authority").strip()
    category = str(item.get("category") or "notification").replace("_", " ").title()
    state = str(item.get("state") or item.get("region") or "All India").strip()
    detected = str(item.get("detected_at") or "").strip()
    published = str(item.get("published") or "").strip()
    official = safe_https(item.get("url") or item.get("official_url"))
    portal = safe_https(item.get("source_url"))
    description = str(item.get("description") or
                      f"{title}. View the official notice and verify current details with {authority}.").strip()
    description = re.sub(r"\s+", " ", description)[:300]
    schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": description,
        "url": canonical,
        "isPartOf": {"@type": "WebSite", "name": "GoResultHub", "url": BASE + "/"},
        "about": {"@type": "Thing", "name": category},
        "dateModified": detected if date_value(detected) else None,
        "publisher": {"@type": "Organization", "name": "GoResultHub", "url": BASE + "/"},
    }
    schema_text = safe_json({k: v for k, v in schema.items() if v is not None})
    official_link = (f'<a class="seo-primary" href="{esc(official)}" rel="nofollow noopener">Open official notice / result ↗</a>'
                     if official else "")
    portal_link = (f'<a class="seo-secondary" href="{esc(portal)}" rel="nofollow noopener">Visit authority website ↗</a>'
                   if portal else "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | GoResultHub</title><meta name="description" content="{esc(description)}">
<meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{esc(title)}">
<script type="application/ld+json">{schema_text}</script>
<link rel="icon" type="image/svg+xml" href="../favicon.svg"><link rel="stylesheet" href="../styles.css">
<style>
.seo-wrap{{max-width:960px;margin:32px auto 56px;padding:0 18px}}
.seo-card{{background:#fff;border:1px solid #dce6f2;border-radius:19px;padding:clamp(22px,4vw,42px);box-shadow:0 10px 28px #153b6b0b}}
.seo-kicker{{color:#2c67a9;font-size:.75rem;font-weight:900;letter-spacing:.12em}}
.seo-card h1{{font-size:clamp(1.8rem,4vw,2.7rem);line-height:1.15;color:#17345b;margin:12px 0}}
.seo-summary{{font-size:1.04rem;line-height:1.75;color:#536780}}
.seo-meta{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}}
.seo-chip{{background:#f2f7ff;border:1px solid #dce7f5;border-radius:999px;padding:7px 11px;font-size:.8rem;color:#214e87;font-weight:750}}
.seo-actions{{display:flex;flex-wrap:wrap;gap:10px;margin:22px 0}}
.seo-actions a{{display:inline-flex;padding:13px 16px;border-radius:11px;font-weight:850;text-decoration:none}}
.seo-primary{{background:#174f9c;color:#fff!important}} .seo-secondary{{background:#edf4ff;color:#174f9c;border:1px solid #d6e5fb}}
.seo-note{{background:#f5f8fc;border:1px solid #e0e8f2;border-radius:12px;padding:14px;color:#4d617a;line-height:1.7}}
.seo-muted{{font-size:.86rem;line-height:1.65;color:#6b7b90;margin-top:24px}}
</style></head><body>
<header class="top"><a class="brand" href="../"><span class="logo">GR</span><span>GoResultHub<small>Exam updates with links to official websites</small></span></a><nav><a href="../#updates">Latest updates</a><a href="../state.html">Browse states</a><a href="../about.html">About</a></nav></header>
<main class="seo-wrap"><p class="seo-kicker">GORESULTHUB · {esc(category.upper())}</p>
<article class="seo-card"><p><a href="../">Home</a> / <a href="../#updates">Latest updates</a> / {esc(category)}</p>
<h1>{esc(title)}</h1><p class="seo-summary">{esc(description)}</p>
<div class="seo-meta"><span class="seo-chip">{esc(category)}</span><span class="seo-chip">{esc(authority)}</span><span class="seo-chip">{esc(state)}</span></div>
<div class="seo-note"><b>Detected by GoResultHub:</b> {esc(detected or "Date not recorded")}<br>
<b>Publication date:</b> {esc(published or "Not separately shown by the issuing authority")}<br><b>Source:</b> {esc(authority)}</div>
<div class="seo-actions">{official_link}{portal_link}<a class="seo-secondary" href="../#updates">More exam updates</a></div>
<h2>How to check this update</h2><ol><li>Open the official notice or result link above.</li><li>Confirm the exam name, year, dates and instructions on the issuing authority's website.</li><li>If a candidate login is required, enter your details only on the verified official portal.</li><li>Download the notice or scorecard directly from the authority if available.</li></ol>
<p class="seo-muted">GoResultHub is an independent information directory and is not affiliated with any government, board, university or recruitment authority. Detection time means when GoResultHub indexed this listing, not necessarily when the authority published it. Always verify details on the issuing authority's website.</p>
</article></main>
<footer><div><a class="brand footbrand" href="../"><span class="logo">GR</span><span>GoResultHub<small>Exam updates with links to official websites</small></span></a><p>Exam updates and links to issuing authorities.</p></div><div class="footlinks"><a href="../privacy.html">Privacy</a><a href="../terms.html">Terms</a><a href="../disclaimer.html">Disclaimer</a></div><p class="copyright">© GoResultHub</p></footer>
</body></html>
"""

def load_feed(path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []

def build():
    updates_dir = SITE / "updates"
    updates_dir.mkdir(parents=True, exist_ok=True)
    feeds = load_feed(SITE / "data" / "results.json") + load_feed(SITE / "data" / "pib-news.json")
    unique = {}
    for item in feeds:
        if isinstance(item, dict):
            ident = str(item.get("id") or "").strip()
            if ident and ident not in unique:
                unique[ident] = item
    urls = {BASE + path: "" for path in BASE_SITEMAP}
    written = 0
    for ident, item in unique.items():
        page = render_detail(item)
        if not page:
            continue
        (updates_dir / f"{ident}.html").write_text(page, encoding="utf-8")
        urls[f"{BASE}/updates/{ident}.html"] = date_value(item.get("detected_at") or item.get("published"))
        written += 1
    for path in updates_dir.glob("*.html"):
        if path.stem not in unique:
            path.unlink()
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, modified in sorted(urls.items()):
        rows.append("  <url><loc>" + html.escape(url) + "</loc>" +
                    ("<lastmod>" + modified + "</lastmod>" if modified else "") + "</url>")
    rows.append("</urlset>")
    (SITE / "sitemap.xml").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"SEO pages generated: {written}; sitemap URLs: {len(urls)}")
    return written

if __name__ == "__main__":
    build()
