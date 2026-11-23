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
HUBS = [
    # slug, categories, H1, title tag, meta description, blurb
    ("latest-results.html", {"result", "merit_list", "cutoff"}, "Latest Exam Results",
     "Latest Exam Results, Merit Lists & Cutoffs | GoResultHub",
     "Newest exam results, merit lists and cutoff announcements from UPSC, SSC, banking, railway, state boards and universities, each linked to the official website.",
     "Newest results, merit lists and cutoffs detected on official examination websites."),
    ("admit-cards.html", {"admit_card"}, "Latest Admit Cards & Hall Tickets",
     "Latest Admit Cards, Hall Tickets & Call Letters | GoResultHub",
     "Newest admit cards, hall tickets, call letters and city-intimation slips for government and entrance exams, linked to the official download pages.",
     "Admit cards, hall tickets and call letters as soon as they appear on official sites."),
    ("answer-keys.html", {"answer_key"}, "Latest Answer Keys & Response Sheets",
     "Latest Answer Keys & Response Sheets | GoResultHub",
     "Newest provisional and final answer keys, response sheets and objection windows from SSC, UPSC, NTA, banking and state recruitment bodies.",
     "Provisional and final answer keys with links to the issuing authority."),
    ("latest-jobs.html", {"notification", "exam_schedule"}, "Latest Government Job Notifications & Exam Schedules",
     "Latest Government Job Notifications & Exam Dates | GoResultHub",
     "Newest recruitment notifications, vacancies and exam schedules from central and state government bodies, linked to the official notice.",
     "Recruitment notifications and exam schedules published by official authorities."),
]
BASE_SITEMAP = [
    "/", "/latest-results.html", "/admit-cards.html", "/answer-keys.html", "/latest-jobs.html", "/state.html", "/how-to-check-exam-results.html",
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

BOILERPLATE = "potential update detected"
NOISE_RE = re.compile(r"open_in_new|\bhome\b.*\babout us\b|\bcontact us\b.*\bfaq\b", re.I)

def is_boilerplate(item):
    return BOILERPLATE in str(item.get("description") or "").lower()

def age_days(item):
    stamp = date_value(item.get("detected_at") or item.get("published"))
    if not stamp:
        return 9999
    try:
        return (datetime.now(timezone.utc).date() - datetime.fromisoformat(stamp).date()).days
    except ValueError:
        return 9999

def is_indexable(item):
    """Old auto-detected listings that carry no original text are thin content:
    keep them reachable but out of the index and sitemap. Fresh ones stay indexed."""
    if item.get("archive"):
        return False
    return not (is_boilerplate(item) and age_days(item) > 45)

def is_live_item(item):
    title = str(item.get("title") or item.get("exam") or "").strip()
    ident = str(item.get("id") or "")
    if item.get("archive") or item.get("reported_only") or ident.startswith("pib-"):
        return False
    return 8 <= len(title) <= 200 and not NOISE_RE.search(title)

def sort_key(item):
    return str(item.get("detected_at") or item.get("published") or "")

def short(value, limit):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    return value if len(value) <= limit else value[:limit - 1].rstrip() + "…"

def render_detail(item, related=None):
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
    application = safe_https(item.get("application_url") or item.get("apply_url") or item.get("registration_url") or item.get("portal_url"))
    is_pdf = lambda value: bool(value and re.search(r"\.pdf(?:$|[?#])", value, re.I))
    pdf_notice = official if is_pdf(official) else ""
    # Prefer an official application/HTML page over a PDF as the primary action.
    primary = application or (portal if is_pdf(official) and portal and not is_pdf(portal) else official) or portal
    secondary_portal = portal if portal and portal != primary else ""
    description = str(item.get("description") or "").strip()
    if not description or BOILERPLATE in description.lower():
        when = date_value(detected) or "recently"
        description = (f"{authority} has listed \u201c{short(title, 140)}\u201d in its {category.lower()} section. "
                       f"GoResultHub detected this listing on {when}. Open the official link to read the full notice "
                       f"and confirm dates, eligibility and instructions.")
    description = re.sub(r"\s+", " ", description)[:300]
    published_date = date_value(published) or date_value(detected)
    robots = "index,follow,max-image-preview:large" if is_indexable(item) else "noindex,follow"
    schema = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": short(title, 110),
        "description": description,
        "mainEntityOfPage": canonical,
        "url": canonical,
        "inLanguage": "en-IN",
        "articleSection": category,
        "isPartOf": {"@type": "WebSite", "name": "GoResultHub", "url": BASE + "/"},
        "datePublished": published_date or None,
        "dateModified": date_value(detected) or published_date or None,
        "author": {"@type": "Organization", "name": "GoResultHub", "url": BASE + "/"},
        "publisher": {"@type": "Organization", "name": "GoResultHub", "url": BASE + "/"},
    }
    schema_text = safe_json({k: v for k, v in schema.items() if v is not None})
    crumbs_text = safe_json({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": category, "item": canonical},
        ]})
    related_html = ""
    if related:
        rows = "".join(f'<li><a href="{esc(str(r.get("id")))}.html">{esc(short(r.get("title") or r.get("exam"), 120))}</a></li>'
                       for r in related)
        related_html = f'<h2>More recent exam updates</h2><ul class="seo-related">{rows}</ul>'
    title_tag = short(title, 62)
    official_link = (f'<a class="seo-primary" href="{esc(primary)}" rel="nofollow noopener">'
                     + ("Open official application / webpage ↗" if application or (primary and primary != official) else "Open official notice / result ↗") + "</a>" if primary else "")
    pdf_link = (f'<a class="seo-secondary" href="{esc(pdf_notice)}" rel="nofollow noopener">Download official PDF notice ↗</a>'
                if pdf_notice and pdf_notice != primary else "")
    portal_link = (f'<a class="seo-secondary" href="{esc(secondary_portal)}" rel="nofollow noopener">Visit authority website ↗</a>'
                   if secondary_portal else "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title_tag)} | GoResultHub</title><meta name="description" content="{esc(description)}">
<meta name="robots" content="{robots}"><link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{esc(title)}">
<script type="application/ld+json">{schema_text}</script>
<script type="application/ld+json">{crumbs_text}</script>
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
.seo-related{{line-height:1.9;padding-left:20px}}.seo-related a{{color:#174f9c;font-weight:700}}
.seo-muted{{font-size:.86rem;line-height:1.65;color:#6b7b90;margin-top:24px}}
</style></head><body>
<header class="top"><a class="brand" href="../"><span class="logo">GR</span><span>GoResultHub<small>Exam updates with links to official websites</small></span></a><nav><a href="../#updates">Latest updates</a><a href="../state.html">Browse states</a><a href="../about.html">About</a></nav></header>
<main class="seo-wrap"><p class="seo-kicker">GORESULTHUB · {esc(category.upper())}</p>
<article class="seo-card"><p><a href="../">Home</a> / <a href="../#updates">Latest updates</a> / {esc(category)}</p>
<h1>{esc(title)}</h1><p class="seo-summary">{esc(description)}</p>
<div class="seo-meta"><span class="seo-chip">{esc(category)}</span><span class="seo-chip">{esc(authority)}</span><span class="seo-chip">{esc(state)}</span></div>
<div class="seo-note"><b>Detected by GoResultHub:</b> {esc(detected or "Date not recorded")}<br>
<b>Publication date:</b> {esc(published or "Not separately shown by the issuing authority")}<br><b>Source:</b> {esc(authority)}</div>
<div class="seo-actions">{official_link}{pdf_link}{portal_link}<a class="seo-secondary" href="../#updates">More exam updates</a></div>
<h2>How to check this update</h2><ol><li>Open the official notice or result link above.</li><li>Confirm the exam name, year, dates and instructions on the issuing authority's website.</li><li>If a candidate login is required, enter your details only on the verified official portal.</li><li>Download the notice or scorecard directly from the authority if available.</li></ol>
{related_html}
<p class="seo-muted">GoResultHub is an independent information directory and is not affiliated with any government, board, university or recruitment authority. Detection time means when GoResultHub indexed this listing, not necessarily when the authority published it. Always verify details on the issuing authority's website.</p>
</article></main>
<footer><div><a class="brand footbrand" href="../"><span class="logo">GR</span><span>GoResultHub<small>Exam updates with links to official websites</small></span></a><p>Exam updates and links to issuing authorities.</p></div><div class="footlinks"><a href="../privacy.html">Privacy</a><a href="../terms.html">Terms</a><a href="../disclaimer.html">Disclaimer</a></div><p class="copyright">© GoResultHub</p></footer>
<script src="../cookie-consent.js" defer></script><script src="../monetization.js" defer></script>
</body></html>
"""

def hub_nav(prefix=""):
    links = "".join(f'<a href="{prefix}{slug}">{esc(h1)}</a>' for slug, _c, h1, *_r in HUBS)
    return f'<nav class="seo-hubnav" aria-label="Browse by type">{links}</nav>'

def render_hub(hub, items):
    slug, _cats, h1, title_tag, meta, blurb = hub
    canonical = f"{BASE}/{slug}"
    rows = []
    for it in items:
        when = date_value(it.get("detected_at") or it.get("published"))
        auth = it.get("source_name") or it.get("authority") or "Official source"
        rows.append(f'<li><a href="updates/{esc(str(it["id"]))}.html">{esc(short(it.get("title") or it.get("exam"), 150))}</a>'
                    f'<small>{esc(short(auth, 60))}' + (f" · {esc(when)}" if when else "") + "</small></li>")
    item_list = safe_json({
        "@context": "https://schema.org", "@type": "ItemList", "name": h1, "url": canonical,
        "itemListElement": [{"@type": "ListItem", "position": i + 1,
                             "url": f'{BASE}/updates/{it["id"]}.html',
                             "name": short(it.get("title") or it.get("exam"), 110)}
                            for i, it in enumerate(items[:25])]})
    today = datetime.now(timezone.utc).strftime("%d %B %Y")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title_tag)}</title><meta name="description" content="{esc(meta)}">
<meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title_tag)}"><meta property="og:description" content="{esc(meta)}"><meta property="og:url" content="{esc(canonical)}">
<meta name="twitter:card" content="summary"><script type="application/ld+json">{item_list}</script>
<link rel="icon" type="image/svg+xml" href="favicon.svg"><link rel="stylesheet" href="styles.css">
<style>.seo-wrap{{max-width:960px;margin:32px auto 56px;padding:0 18px}}.seo-card{{background:#fff;border:1px solid #dce6f2;border-radius:19px;padding:clamp(22px,4vw,42px)}}
.seo-card h1{{font-size:clamp(1.7rem,4vw,2.5rem);color:#17345b;margin:8px 0}}.seo-hubnav{{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}}
.seo-hubnav a{{background:#edf4ff;border:1px solid #d6e5fb;border-radius:999px;padding:7px 12px;font-weight:750;font-size:.85rem;color:#174f9c;text-decoration:none}}
.seo-list{{list-style:none;padding:0;margin:18px 0}}.seo-list li{{padding:12px 0;border-bottom:1px solid #e6edf6}}
.seo-list a{{font-weight:800;color:#174f9c;text-decoration:none;line-height:1.5}}.seo-list small{{display:block;color:#6b7b90;margin-top:3px}}</style></head><body>
<header class="top"><a class="brand" href="./"><span class="logo">GR</span><span>GoResultHub<small>Exam updates with links to official websites</small></span></a><nav><a href="./#updates">Latest updates</a><a href="state.html">Browse states</a><a href="about.html">About</a></nav></header>
<main class="seo-wrap"><article class="seo-card"><p><a href="./">Home</a> / {esc(h1)}</p><h1>{esc(h1)}</h1>
<p>{esc(blurb)} Updated {esc(today)}. GoResultHub links every item to the issuing authority \u2014 always confirm details there.</p>
{hub_nav()}<ol class="seo-list">{"".join(rows) or "<li>No updates indexed yet. Please check back shortly.</li>"}</ol></article></main>
<footer><div><a class="brand footbrand" href="./"><span class="logo">GR</span><span>GoResultHub<small>Exam updates with links to official websites</small></span></a></div><div class="footlinks"><a href="privacy.html">Privacy</a><a href="terms.html">Terms</a><a href="disclaimer.html">Disclaimer</a><a href="contact.html">Contact</a></div><p class="copyright">\u00a9 GoResultHub</p></footer>
<script src="cookie-consent.js" defer></script><script src="monetization.js" defer></script>
</body></html>
"""

START, END = "<!--SEO-LATEST-START-->", "<!--SEO-LATEST-END-->"

def inject_homepage(items):
    """Put the newest listings into index.html as plain HTML so crawlers, social
    previews and slow phones see real content before app.js runs. app.js replaces it."""
    path = SITE / "index.html"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    rows = "".join(
        f'<li><a href="updates/{esc(str(it["id"]))}.html">{esc(short(it.get("title") or it.get("exam"), 140))}</a> '
        f'<small>{esc(short(it.get("source_name") or it.get("authority") or "Official source", 50))}</small></li>'
        for it in items[:30])
    block = (f'{START}<div class="seo-static-latest"><ul style="list-style:none;padding:0;margin:0;line-height:1.9">{rows}</ul>'
             f'{hub_nav()}</div>{END}')
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _m: block, text, flags=re.S)
    else:
        marker = '<div class="empty">Loading updates\u2026</div>'
        if marker not in text:
            return
        text = text.replace(marker, block + marker, 1)
    path.write_text(text, encoding="utf-8")

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
    live = sorted((i for i in unique.values() if is_live_item(i)), key=sort_key, reverse=True)
    by_cat = {}
    for it in live:
        by_cat.setdefault(str(it.get("category") or ""), []).append(it)
    today_iso = datetime.now(timezone.utc).date().isoformat()
    for hub in HUBS:
        items = [i for i in live if str(i.get("category") or "") in hub[1]][:100]
        (SITE / hub[0]).write_text(render_hub(hub, items), encoding="utf-8")
        urls[f"{BASE}/{hub[0]}"] = today_iso
    inject_homepage(live)
    urls[f"{BASE}/"] = today_iso
    written = 0
    for ident, item in unique.items():
        pool = [r for r in by_cat.get(str(item.get("category") or ""), []) if r.get("id") != ident][:6]
        page = render_detail(item, pool)
        if not page:
            continue
        (updates_dir / f"{ident}.html").write_text(page, encoding="utf-8")
        if is_indexable(item):
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
