#!/usr/bin/env python3
"""Best-effort official-site link monitor. Never invents notices or dates."""
import json, re, hashlib, datetime, urllib.request, urllib.parse, html
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "site/data/results.json"
SOURCES = [
 {"name":"UPSC","url":"https://upsc.gov.in/whats-new","family":"UPSC / Central Recruitment","region":"Central"},
 {"name":"SSC","url":"https://ssc.gov.in/","family":"SSC / Central Recruitment","region":"Central"},
 {"name":"NTA","url":"https://www.nta.ac.in/","family":"Entrance & Eligibility","region":"Central"},
 {"name":"RRB Chandigarh","url":"https://www.rrbcdg.gov.in/","family":"Railways","region":"Central"},
 {"name":"IBPS","url":"https://www.ibps.in/","family":"Banking","region":"Central"},
 {"name":"SBI Careers","url":"https://sbi.co.in/web/careers","family":"Banking","region":"Central"},
 {"name":"CGPSC","url":"https://psc.cg.gov.in/","family":"State PSC / Recruitment","region":"Chhattisgarh"},
 {"name":"UPPSC","url":"https://uppsc.up.nic.in/","family":"State PSC / Recruitment","region":"Uttar Pradesh"},
 {"name":"BPSC","url":"https://bpsc.bihar.gov.in/","family":"State PSC / Recruitment","region":"Bihar"},
 {"name":"RPSC","url":"https://rpsc.rajasthan.gov.in/","family":"State PSC / Recruitment","region":"Rajasthan"},
]
PATTERNS = [
 ("admit_card", r"admit card|hall ticket|call letter|e-admit"),
 ("answer_key", r"answer key|response sheet"),
 ("result", r"results?\b|score card|scorecard"),
 ("merit_list", r"merit list|selection list"),
 ("cutoff", r"cut.?off"),
 ("notification", r"notification|recruitment|advertisement|vacanc|examination notice|exam notice|corrigendum|application form"),
]
class Links(HTMLParser):
 def __init__(self): super().__init__(); self.href=None; self.text=[]; self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=="a": self.href=dict(attrs).get("href"); self.text=[]
 def handle_data(self,data):
  if self.href is not None: self.text.append(data)
 def handle_endtag(self,tag):
  if tag=="a" and self.href is not None:
   self.links.append((self.href," ".join(" ".join(self.text).split())))
   self.href=None; self.text=[]
def scan(source):
 req=urllib.request.Request(source["url"],headers={"User-Agent":"GoResultHub/1.0 (public official link monitor; contact: workpmahant0330@gmail.com)","Accept":"text/html"})
 with urllib.request.urlopen(req,timeout=18) as response:
  if "text/html" not in response.headers.get("Content-Type",""): return []
  body=response.read(1500000).decode("utf-8","replace")
 parser=Links(); parser.feed(body)
 host=urllib.parse.urlsplit(source["url"]).hostname
 items=[]
 for href,title in parser.links:
  title=html.unescape(title).strip()
  if not 15<=len(title)<=180: continue
  category=next((key for key,pattern in PATTERNS if re.search(pattern,title,re.I)),None)
  if not category: continue
  url=urllib.parse.urljoin(source["url"],href)
  parts=urllib.parse.urlsplit(url)
  if parts.scheme!="https" or not parts.hostname: continue
  # Accept only same authority or its subdomains; no third-party redirects.
  if parts.hostname!=host and not parts.hostname.endswith("."+host): continue
  if url.rstrip("/")==source["url"].rstrip("/"): continue
  url=urllib.parse.urlunsplit((parts.scheme,parts.netloc,parts.path,parts.query,""))
  items.append({"id":hashlib.sha256((source["name"]+"|"+url).encode()).hexdigest()[:20],"title":title,"category":category,"exam_category":source["family"],"region":source["region"],"source_name":source["name"],"url":url,"verified":False,"description":"Detected link on an official website. Confirm details on the linked page."})
 return items
def main():
 OUTPUT.parent.mkdir(parents=True,exist_ok=True)
 try: old=json.loads(OUTPUT.read_text(encoding="utf-8"))
 except (OSError,ValueError): old=[]
 if not isinstance(old,list): old=[]
 by_id={str(x.get("id") or x.get("url")):x for x in old if isinstance(x,dict) and x.get("url")}
 added=0; success=0
 for source in SOURCES:
  try:
   found=scan(source); success+=1
   for item in found:
    if item["id"] not in by_id:
     item["detected_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
     by_id[item["id"]]=item; added+=1
   print(f'{source["name"]}: {len(found)} candidate links')
  except Exception as exc: print(f'{source["name"]}: skipped ({type(exc).__name__}: {exc})')
 if success==0: print("All sources unavailable; retaining existing data"); return
 items=sorted(by_id.values(),key=lambda x:x.get("detected_at",""),reverse=True)[:400]
 OUTPUT.write_text(json.dumps(items,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(f"Added {added} new links; total {len(items)}")
if __name__=="__main__": main()
