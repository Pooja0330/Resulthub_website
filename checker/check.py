"""ResultHub checker: finds new result links on official pages and posts them."""
import json, os, re, datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "checker", "sources.json")
STATE = os.path.join(ROOT, "checker", "state.json")
RES = os.path.join(ROOT, "site", "results.json")
AUTO = os.environ.get("AUTO_PUBLISH", "0") == "1"
TOKEN = os.environ.get("TG_TOKEN", "")
CHANNEL = os.environ.get("TG_CHANNEL", "")   # e.g. @resulthub_india
ADMIN = os.environ.get("TG_ADMIN", "")       # your own Telegram chat id
HEAD = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
WANT = re.compile(r"result|merit list|score ?card|final selection|cut[- ]?off|declar", re.I)
SKIP = re.compile(r"admit card|answer key|syllabus|apply|application|vacanc|schedule|city|hall ticket|extended|corrigendum", re.I)
CATS = [(r"\bNDA\b|\bCDS\b|AFCAT|agniveer", "Defence"),
        (r"NEET|JEE|CUET|\bCAT\b|CLAT|JIPMAT|CMAT", "Entrance"),
        (r"UGC|\bNET\b|\bTET\b|teacher|principal", "Teaching & NET")]

def load(p, default):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default

def save(p, data):
    json.dump(data, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

def get(url):
    try:
        r = requests.get(url, headers=HEAD, timeout=30)
    except requests.exceptions.SSLError:
        r = requests.get(url, headers=HEAD, timeout=30, verify=False)
    r.raise_for_status()
    return r.text

def links(html, base):
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        text = " ".join(a.get_text().split())
        href = a["href"].strip()
        if href.startswith(("#", "javascript", "mailto")):
            continue
        if 12 <= len(text) <= 200 and WANT.search(text) and not SKIP.search(text):
            yield text, urljoin(base, href)

def category(text, default):
    for pat, cat in CATS:
        if re.search(pat, text, re.I):
            return cat
    return default

def tg(chat, text):
    if not (TOKEN and chat):
        print("TG skipped:", text[:80]); return
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id": chat, "text": text, "disable_web_page_preview": True}, timeout=30)

def main():
    sources = load(SRC, []); state = load(STATE, {"seen": {}, "fails": {}}); results = load(RES, [])
    today = datetime.date.today().strftime("%d %b %Y"); new = []
    for s in sources:
        name = s["name"]
        try:
            html = get(s["url"])
        except Exception as e:
            n = state["fails"].get(name, 0) + 1; state["fails"][name] = n
            if n == 3:
                tg(ADMIN, f"Checker warning: {name} failed 3 times ({type(e).__name__}). The site may block this server or have changed.")
            print("FAIL", name, e); continue
        state["fails"][name] = 0
        found = {h: t for t, h in links(html, s["url"])}
        first = name not in state["seen"]
        old = set(state["seen"].get(name, []))
        fresh = [h for h in found if h not in old]
        if not first and len(fresh) > 5:
            tg(ADMIN, f"Checker warning: {name} showed {len(fresh)} new links at once. Possible layout change, skipped.")
        elif not first:
            for h in fresh:
                new.append({"t": found[h], "c": category(found[h], s["cat"]), "d": today, "u": h,
                            "info": "Open the official page to check your result."})
        state["seen"][name] = sorted(old | set(found))
    for it in new:
        if AUTO:
            results.insert(0, it)
            tg(CHANNEL, f"Result update: {it['t']}\n{it['u']}\nPlease verify on the official website.")
        else:
            tg(ADMIN, "DRAFT (not published)\n" + it["t"] + "\n" + it["u"] +
               "\n\nTo publish, paste this line at the top of site/results.json:\n" + json.dumps(it, ensure_ascii=False))
    if AUTO and new:
        save(RES, results[:200])
    save(STATE, state)
    print("new items:", len(new), "auto:", AUTO)

if __name__ == "__main__":
    main()
