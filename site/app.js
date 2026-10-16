const $ = s => document.querySelector(s);
let allItems = [];
let lastStatus = null;
let page = 1;
const PAGE_SIZE = 30;
let resultsRequest = null;
let statusRequest = null;
let refreshTimer = null;
const label = s => String(s||"update").replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase());
function safeUrl(u){try{const x=new URL(u);return x.protocol==="https:"?x.href:null}catch{return null}}
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function dateText(v){if(!v)return "Date not supplied";const d=new Date(v);return Number.isNaN(d.getTime())?"Date not supplied":d.toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}
function inferredFamily(x){
 const t=[x.source_id,x.source_name,x.title,x.exam,x.state].join(" ").toLowerCase();
 if(/railway recruitment|\brrb\b|\brrc\b|ntpc|group d|assistant loco pilot|\balp\b/.test(t)) return "Railways";
 if(/\bibps\b|state bank of india|\bsbi\b|reserve bank of india|\brbi\b|banking|\blic\b|insurance regulatory|niacl|uiic|pfrda/.test(t)) return "Banking";
 if(/staff selection commission|\bssc (cgl|chsl|mts|gd|stenographer)\b/.test(t)) return "SSC / Central Recruitment";
 if(/union public service commission|\bupsc\b/.test(t)) return "UPSC / Central Recruitment";
 if(/national testing agency|\bnta\b|\bjee\b|\bneet\b|\bcuet\b|\bgate\b|ugc net|csir net/.test(t)) return "Entrance & Eligibility";
 if(/school board|board of school education|school education board|\bboard\b|\bcbse\b|\bcisce\b|\bnios\b|class 10|class 12|sslc|hsc|madhyamik/.test(t)) return "School Board Results";
 if(/police|constable|slprb/.test(t)) return "State Recruitment / Police";
 if(/public service commission|subordinate services selection commission|staff selection commission|state service commission|\bpsc\b|\bselection commission\b/.test(t)) return "State PSC / Recruitment";
 if(/ctet|\btet\b|teacher|teaching|kvs|nvs/.test(t)) return "Teaching / Eligibility";
 if(/defence|defense|army|navy|air force|agniveer|crpf|bsf|cisf|itbp|ssb/.test(t)) return "Defence";
 if(/icai|icsi|icmai|chartered accountant|company secretary|national medical commission/.test(t)) return "Professional Exams";
 return x.exam_category||"UPSC / Central Recruitment";
}
function filteredItems(){
 const q=$("#q").value.trim().toLowerCase(), c=$("#category").value, ec=$("#examCategory").value, r=$("#region").value;
 const list=allItems.filter(x=>{
  const family=inferredFamily(x);
  const hay=[x.title,x.exam,x.source_name,x.state,x.region,x.category,family].join(" ").toLowerCase();
  return (!q||hay.includes(q))&&(!c||x.category===c)&&(!ec||family===ec)&&(!r||r==="All India"||((x.region||x.state||"Central")===r));
 });
 if($("#sort").value==="title") list.sort((a,b)=>(a.title||"").localeCompare(b.title||""));
 else list.sort((a,b)=>new Date(b.detected_at||b.date||0)-new Date(a.detected_at||a.date||0));
 return list;
}
function render(){
 const list=filteredItems(), pages=Math.max(1,Math.ceil(list.length/PAGE_SIZE));
 page=Math.min(page,pages);
 const visible=list.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE);
 $("#count").textContent=`${list.length} update${list.length===1?"":"s"}`;
 $("#updatesList").innerHTML=visible.map(x=>{
  const url=safeUrl(x.url||x.official_url), sourcePage=safeUrl(x.source_url);
  const sourceBadge=x.verified===true?"✓ Verified official source":(x.archive?"Official archive / portal":"Official website link");
  return `<article class="card"><div class="meta"><span class="tag">${esc(label(x.category))}</span><span class="unverified">${esc(sourceBadge)}</span></div><h3>${esc(x.title||x.exam||"Exam update")}</h3><p>${esc(x.description||x.source_name||"View the official website for full details and eligibility.")}</p><div class="source">${esc(x.source_name||x.authority||"Issuing authority")} · ${esc(dateText(x.detected_at||x.date))}</div>${sourcePage&&sourcePage!==url?`<a class="link" href="${esc(sourcePage)}" target="_blank" rel="noopener noreferrer">Start at official authority website ↗</a>`:""}${url?` <a class="link secondary" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open direct notice/result (may be PDF) ↗</a>`:`<span>Official link unavailable</span>`}</article>`;
 }).join("");
 $("#empty").classList.toggle("hidden",list.length>0);
 if(!list.length) $("#updatesList").innerHTML="";
 const pager=$("#pagination");
 if(pager){
  pager.innerHTML=list.length>PAGE_SIZE?`<button type="button" id="prevPage" class="secondary" ${page===1?"disabled":""}>Previous</button><span>Page ${page} of ${pages}</span><button type="button" id="nextPage" class="secondary" ${page===pages?"disabled":""}>Next</button>`:"";
  $("#prevPage")?.addEventListener("click",()=>{page--;render();$("#updates").scrollIntoView({behavior:"smooth"});});
  $("#nextPage")?.addEventListener("click",()=>{page++;render();$("#updates").scrollIntoView({behavior:"smooth"});});
 }
}
async function loadStatus(){
 if(statusRequest)return statusRequest;
 statusRequest=(async()=>{
  try{
   const r=await fetch("data/status.json");
   if(!r.ok) throw new Error("Status unavailable");
   lastStatus=await r.json();
   const checked=lastStatus.last_checked_at?new Date(lastStatus.last_checked_at):null;
   const when=checked&&!Number.isNaN(checked.getTime())?checked.toLocaleString("en-IN",{dateStyle:"medium",timeStyle:"short",timeZone:"Asia/Kolkata"}):"Not available";
   const healthy=lastStatus.status==="healthy";
   const stale=checked&&!Number.isNaN(checked.getTime())&&(Date.now()-checked.getTime()>4*60*60*1000);
   $("#monitorStatus").textContent=stale?"Checker status is stale":(healthy?"Automatic monitoring active":(lastStatus.status==="partial"?"Monitoring partially available":(lastStatus.status==="pending"?"Initial scan pending":"Monitoring status unavailable")));
   $("#monitorDetail").textContent="Last checked "+when+" IST · "+(lastStatus.sources_succeeded||0)+"/"+(lastStatus.sources_enabled||0)+" sources reachable · "+(lastStatus.sources_failed||0)+" failed · "+(lastStatus.alerts_pending||0)+" alerts pending delivery · checks run about every 2 hours"+(stale?" · latest scan is over 4 hours old":"");
  }catch(e){
   $("#monitorStatus").textContent="Monitoring status unavailable";
   $("#monitorDetail").textContent="The website is online, but the latest checker status could not be loaded.";
  }finally{statusRequest=null}
 })();
 return statusRequest;
}
async function loadResults(){
 if(resultsRequest)return resultsRequest;
 resultsRequest=(async()=>{
  try{
   const r=await fetch("data/results.json");
   if(!r.ok) throw new Error("Data not available");
   const data=await r.json();
   if(!Array.isArray(data))throw new Error("Invalid data format");
   allItems=data;
   try{localStorage.setItem("goresult-results-cache",JSON.stringify({savedAt:Date.now(),items:data}))}catch(e){}
   page=1;render();
  }catch(e){
   if(!allItems.length){
    try{const cached=JSON.parse(localStorage.getItem("goresult-results-cache")||"null");if(Array.isArray(cached?.items)){allItems=cached.items;render();$("#monitorDetail").textContent="Showing the last saved updates because the live feed is temporarily unavailable."}}catch(ignore){}
   }
   if(!allItems.length){$("#count").textContent="Updates unavailable";$("#updatesList").innerHTML='<div class="empty">Updates are temporarily unavailable. Please try again later.</div>';}
  }finally{resultsRequest=null}
 })();
 return resultsRequest;
}
async function refresh(){if(document.visibilityState==="visible")await Promise.all([loadResults(),loadStatus()])}
function init(){
 $("#year").textContent=new Date().getFullYear();
 try{const cached=JSON.parse(localStorage.getItem("goresult-results-cache")||"null");if(Array.isArray(cached?.items)){allItems=cached.items;render()}}catch(e){}
 refresh();
 if(refreshTimer)clearInterval(refreshTimer);
 refreshTimer=setInterval(refresh,15*60*1000);
 document.addEventListener("visibilitychange",()=>{if(document.visibilityState==="visible")refresh()});
 if("serviceWorker" in navigator)navigator.serviceWorker.register("sw.js").catch(()=>{});
}
$("#searchForm").addEventListener("submit",e=>{e.preventDefault();page=1;render()});
["q","category","examCategory","region","sort"].forEach(id=>$("#"+id).addEventListener(id==="q"?"input":"change",()=>{page=1;render()}));
document.querySelectorAll(".pills [data-family]").forEach(button=>button.addEventListener("click",()=>{$("#examCategory").value=button.dataset.family;page=1;$("#updates").scrollIntoView({behavior:"smooth"});render()}));
$("#supportBtn").addEventListener("click",()=>{$("#supportNote").textContent="Secure support payments are not configured yet. We will enable this after a payment provider and checkout URL are set up.";});
init();
