"""GoResultHub official-source monitor. Review-first; never bypasses TLS verification."""
import os, json, re, hashlib, sys
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests, feedparser
from bs4 import BeautifulSoup

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def path(p): return os.path.join(ROOT,p)
def load(p, default):
    try:
        with open(path(p),encoding='utf-8') as f: return json.load(f)
    except (FileNotFoundError,json.JSONDecodeError): return default
def save(p,data):
    os.makedirs(os.path.dirname(path(p)),exist_ok=True)
    tmp=path(p)+'.tmp'
    with open(tmp,'w',encoding='utf-8') as f: json.dump(data,f,indent=2,ensure_ascii=False)
    os.replace(tmp,path(p))
TOKEN=os.getenv('TG_TOKEN','').strip(); ADMIN=os.getenv('TG_ADMIN','').strip(); CHANNEL=os.getenv('TG_CHANNEL','').strip()
AUTO=os.getenv('AUTO_PUBLISH','0').strip()=='1'
TIMEOUT=max(4,min(int(os.getenv('SOURCE_TIMEOUT_SECONDS','8')),30))
WORKERS=max(2,min(int(os.getenv('SOURCE_WORKERS','10')),20))
HEADERS={'User-Agent':'GoResultHubOfficialMonitor/1.1 (+checks public official exam notice pages; contact site owner for issues)','Accept':'text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8'}
RULES=[
('result',r'\b(result|results|scorecard|score card|marks list|result declared|rank card|rank list)\b'),
('merit_list',r'\b(merit list|selection list|selected candidates|final selection|qualified candidates|provisional selection|panel list|allotment list)\b'),
('cutoff',r'\b(cut.?off|cutoff)\b'),
('admit_card',r'\b(admit card|hall ticket|call letter|e.?admit card|exam city|city intimation)\b'),
('answer_key',r'\b(answer key|response sheet|answer sheet|objection tracker)\b'),
('notification',r'\b(notification|advertisement|recruitment|exam calendar|examination notice|exam notice|vacancy|apply online|registration open|application form|application dates|corrigendum|information bulletin|schedule)\b')]
SKIP=re.compile(r'\b(tender|quotation|vendor|procurement|press release|media advisory|syllabus|annual report|privacy policy|photo gallery)\b',re.I)
def allowed(url,hosts):
    try:
        p=urlparse(url); h=(p.hostname or '').lower()
        return p.scheme=='https' and any(h==x.lower() or h.endswith('.'+x.lower()) for x in hosts)
    except Exception:return False
def cat(text):
    if not text or SKIP.search(text): return None
    for c,pat in RULES:
        if re.search(pat,text,re.I): return c
    return None
def send(chat,msg):
    if not TOKEN or not chat: return False
    try:
        r=requests.post('https://api.telegram.org/bot'+TOKEN+'/sendMessage',json={'chat_id':chat,'text':msg[:3900],'disable_web_page_preview':True},timeout=(4,10))
        r.raise_for_status()
        return bool(r.json().get('ok'))
    except Exception as e:
        print('Telegram error',type(e).__name__,str(e)[:200]); return False
def collect(src):
    if src.get('kind')=='rss':
        r=requests.get(src['url'],headers=HEADERS,timeout=(4,TIMEOUT)); r.raise_for_status()
        if not allowed(r.url,src['allowed_hosts']): raise RuntimeError('Redirected outside allowlisted official hosts')
        feed=feedparser.parse(r.content)
        if not feed.entries and getattr(feed,'bozo',False): raise RuntimeError('RSS parse failed')
        raw=[(e.get('title',''),e.get('link','')) for e in feed.entries]
    else:
        r=requests.get(src['url'],headers=HEADERS,timeout=(4,TIMEOUT)); r.raise_for_status()
        if not allowed(r.url,src['allowed_hosts']): raise RuntimeError('Redirected outside allowlisted official hosts: '+r.url)
        ct=r.headers.get('content-type','').lower()
        if 'html' not in ct and 'xml' not in ct: raise RuntimeError('Non-HTML page needs a dedicated PDF/API adapter')
        soup=BeautifulSoup(r.text,'html.parser')
        raw=[(' '.join(a.get_text(' ',strip=True).split()),urljoin(r.url,a.get('href',''))) for a in soup.select('a[href]')]
    out=[]
    for title,url in raw:
        title=' '.join(str(title).split()); url=str(url).split('#')[0]
        category=cat(title)
        if title and category and allowed(url,src['allowed_hosts']):
            out.append({'title':title[:280],'url':url,'category':category})
    return out
def check_one(src):
    try: return src,collect(src),None
    except Exception as e: return src,[],f'{type(e).__name__}: {e}'[:500]
def main():
    registry=load('checker/sources.json',{'sources':[]})
    state=load('checker/state.json',{'seen':{},'last_run':None,'source_health':{}})
    seen=state.setdefault('seen',{}); health=state.setdefault('source_health',{})
    results=load('site/data/results.json',[])
    if not isinstance(results,list): print('ERROR: site/data/results.json must be an array'); sys.exit(2)
    enabled=[x for x in registry.get('sources',[]) if x.get('enabled',True)]
    now=datetime.now(timezone.utc).isoformat(); found=[]; fails=0
    print(f'Starting {len(enabled)} enabled sources with {WORKERS} workers; timeout={TIMEOUT}s; TLS verification enabled')
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures=[pool.submit(check_one,src) for src in enabled]
        for fut in as_completed(futures):
            src,items,error=fut.result()
            if error:
                fails+=1; health[src['id']]={'status':'failed','checked_at':now,'error':error}
                print(f"FAIL {src['name']}: {error}"); continue
            fresh=[]
            for x in items:
                key=hashlib.sha256(x['url'].encode()).hexdigest()[:20]
                if key in seen: continue
                seen[key]={'source':src['id'],'first_seen':now,'url':x['url']}
                x.update({'id':key,'source_id':src['id'],'source_name':src['name'],'source_url':src['url'],'detected_at':now,'verified':False,'status':'review'})
                fresh.append(x)
            found.extend(fresh); health[src['id']]={'status':'ok','checked_at':now,'matches':len(items),'new':len(fresh)}
            print(f"OK {src['name']}: {len(items)} matching links, {len(fresh)} new")
    # Publishing requires explicit opt-in AND only candidate detection; still marks items unverified.
    if found and AUTO:
        existing={x.get('url') for x in results if isinstance(x,dict)}
        add=[x for x in found if x['url'] not in existing]
        save('site/data/results.json',add+results)
        for x in add:
            msg=f"GoResultHub candidate (UNVERIFIED: review before relying on it)\n{x['source_name']} | {x['category']}\n{x['title']}\nOfficial page: {x['url']}"
            if CHANNEL: send(CHANNEL,msg)
            if ADMIN: send(ADMIN,'AUTO-PUBLISHED CANDIDATE — verify manually:\n'+msg)
        print('AUTO: added unverified candidates',len(add))
    elif found:
        for x in found:
            send(ADMIN,f"REVIEW DRAFT — not published\n{x['source_name']} | {x['category']}\n{x['title']}\n{x['url']}")
        print('REVIEW: candidate links sent to admin; not published')
    else: print('No new candidate links')
    state['last_run']=now; state['last_run_failures']=fails; state['last_run_new_candidates']=len(found)
    state['source_registry_count']=len(enabled); save('checker/state.json',state)
    print(f'Finished; sources={len(enabled)}; AUTO_PUBLISH={AUTO}; failures={fails}; new_candidates={len(found)}')
if __name__=='__main__': main()
