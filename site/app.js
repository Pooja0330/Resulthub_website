const $ = s => document.querySelector(s);
let allItems = [];
let lastStatus = null;
let page = 1;
const PAGE_SIZE = 30;

let selectedState = "";
let selectedRegion = "";
const STATE_NAMES = [
 "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat","Haryana",
 "Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh","Maharashtra","Manipur",
 "Meghalaya","Mizoram","Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana",
 "Tripura","Uttar Pradesh","Uttarakhand","West Bengal",
 "Andaman and Nicobar Islands","Chandigarh","Dadra and Nagar Haveli and Daman and Diu","Delhi",
 "Jammu and Kashmir","Ladakh","Lakshadweep","Puducherry"
];
const STATE_PORTALS = {
 "Andhra Pradesh":[["AP Public Service Commission","https://psc.ap.gov.in/"],["AP School Board","https://bse.ap.gov.in/"],["AP Police Recruitment","https://slprb.ap.gov.in/"]],
 "Arunachal Pradesh":[["Arunachal Pradesh PSC","https://appsc.gov.in/"]],
 "Assam":[["Assam PSC","https://apsc.nic.in/"],["Assam Board","https://site.sebaonline.org/"],["Assam Government","https://assam.gov.in/"]],
 "Bihar":[["Bihar PSC","https://bpsc.bihar.gov.in/"],["Bihar School Board","https://biharboardonline.bihar.gov.in/"],["Constable Recruitment","https://csbc.bihar.gov.in/"],["Police Subordinate Services","https://bpssc.bihar.gov.in/"],["Bihar Technical Service Commission","https://btsc.bihar.gov.in/"]],
 "Chhattisgarh":[["Chhattisgarh PSC","https://psc.cg.gov.in/"],["Chhattisgarh Board","https://cgbse.nic.in/"],["CG Vyapam","https://vyapam.cgstate.gov.in/"]],
 "Goa":[["Goa Board of Secondary and Higher Secondary Education","https://www.gbshse.in/"],["Goa Government","https://www.goa.gov.in/"]],
 "Gujarat":[["Gujarat PSC","https://gpsc.gujarat.gov.in/"],["Gujarat Board","https://www.gseb.org/"],["OJAS Recruitment","https://ojas.gujarat.gov.in/"]],
 "Haryana":[["Haryana PSC","https://hpsc.gov.in/"],["Haryana Staff Selection Commission","https://www.hssc.gov.in/"],["Haryana Board","https://bseh.org.in/"]],
 "Himachal Pradesh":[["Himachal Pradesh Recruitment Authority","https://hprca.hp.gov.in/"],["HP Board of School Education","https://hpbose.org/"]],
 "Jharkhand":[["Jharkhand PSC","https://www.jpsc.gov.in/"]],
 "Karnataka":[["Karnataka PSC","https://kpsc.kar.nic.in/"],["Karnataka School Examination and Assessment Board","https://kseab.karnataka.gov.in/"]],
 "Kerala":[["Kerala PSC","https://www.keralapsc.gov.in/"],["Kerala Board of Public Examinations","https://pareekshabhavan.kerala.gov.in/"],["Kerala Results","https://results.kerala.nic.in/"]],
 "Madhya Pradesh":[["MP PSC","https://mppsc.mp.gov.in/"],["MP Board","https://mpbse.nic.in/"],["MP Employees Selection Board","https://esb.mp.gov.in/"]],
 "Maharashtra":[["Maharashtra PSC","https://mpsc.gov.in/"],["Maharashtra Board","https://mahahsscboard.in/"],["Maharashtra Results","https://mahresult.nic.in/"],["MahaSwayam Recruitment","https://rojgar.mahaswayam.gov.in/"]],
 "Manipur":[["Manipur PSC","https://mpscmanipur.gov.in/"],["Board of Secondary Education Manipur","https://bsem.nic.in/"]],
 "Meghalaya":[["Meghalaya PSC","https://mpsc.meghalaya.gov.in/"],["Meghalaya Board of School Education","https://mbose.in/"]],
 "Mizoram":[["Mizoram PSC","https://mpsc.mizoram.gov.in/"],["Mizoram Board of School Education","https://mbse.edu.in/"]],
 "Nagaland":[["Nagaland PSC","https://npsc.nagaland.gov.in/"],["Nagaland Board of School Education","https://nbsenl.edu.in/"]],
 "Odisha":[["Odisha PSC","https://opsc.gov.in/"],["Odisha Staff Selection Commission","https://www.ossc.gov.in/"],["Odisha Sub-ordinate Staff Selection Commission","https://www.osssc.gov.in/"],["Odisha Board","https://bseodisha.ac.in/"],["Odisha Results Portal","https://results.odisha.gov.in/"]],
 "Punjab":[["Punjab PSC","https://ppsc.gov.in/"],["Punjab School Education Board","https://www.pseb.ac.in/"],["Punjab Subordinate Services Selection Board","https://sssb.punjab.gov.in/"]],
 "Rajasthan":[["Rajasthan PSC","https://rpsc.rajasthan.gov.in/"],["Rajasthan Staff Selection Board","https://rssb.rajasthan.gov.in/"],["Rajasthan Board","https://rajeduboard.rajasthan.gov.in/"]],
 "Sikkim":[["Sikkim PSC","https://spsc.sikkim.gov.in/"],["Sikkim Human Resource Development Department","https://sikkimhrdd.org/"]],
 "Tamil Nadu":[["Tamil Nadu PSC","https://www.tnpsc.gov.in/"],["Tamil Nadu Directorate of Government Examinations","https://dge.tn.gov.in/"],["Teachers Recruitment Board","https://www.trb.tn.gov.in/"],["Uniformed Services Recruitment Board","https://www.tnusrb.tn.gov.in/"]],
 "Telangana":[["Telangana PSC","https://www.tspsc.gov.in/"],["Telangana Board","https://bse.telangana.gov.in/"],["Telangana Results","https://results.cgg.gov.in/"],["Telangana Police Recruitment","https://www.tgprb.in/"]],
 "Tripura":[["Tripura PSC","https://tpsc.tripura.gov.in/"],["Tripura Board of Secondary Education","https://tbse.tripura.gov.in/"]],
 "Uttar Pradesh":[["UP PSC","https://uppsc.up.nic.in/"],["UP Subordinate Services Selection Commission","https://upsssc.gov.in/"],["UP Board","https://upmsp.edu.in/"],["UP Police Recruitment","https://uppbpb.gov.in/"]],
 "Uttarakhand":[["Uttarakhand PSC","https://psc.uk.gov.in/"],["Uttarakhand Board of School Education","https://ubse.uk.gov.in/"]],
 "West Bengal":[["West Bengal PSC","https://psc.wb.gov.in/"],["West Bengal Board of Secondary Education","https://wbbse.wb.gov.in/"],["West Bengal School Service Commission","https://www.westbengalssc.com/"],["West Bengal Police Recruitment Board","https://prb.wb.gov.in/"]],
 "Andaman and Nicobar Islands":[["Andaman and Nicobar Administration","https://andaman.gov.in/"]],
 "Chandigarh":[["Chandigarh Administration","https://chandigarh.gov.in/"]],
 "Dadra and Nagar Haveli and Daman and Diu":[["Dadra and Nagar Haveli and Daman and Diu Administration","https://ddd.gov.in/"]],
 "Delhi":[["Delhi Subordinate Services Selection Board","https://dsssb.delhi.gov.in/"],["Delhi Government","https://delhi.gov.in/"]],
 "Jammu and Kashmir":[["Jammu and Kashmir PSC","https://jkpsc.nic.in/"],["Jammu and Kashmir Services Selection Board","https://jkssb.nic.in/"],["J&K Board of School Education","https://jkbose.nic.in/"]],
 "Ladakh":[["Ladakh Administration","https://ladakh.gov.in/"]],
 "Lakshadweep":[["Lakshadweep Administration","https://lakshadweep.gov.in/"]],
 "Puducherry":[["Puducherry Government","https://py.gov.in/"]]
};
const STATE_PATTERNS = [
 ["Andhra Pradesh",/andhra pradesh|andhra-board|ap-results|appsc|psc\.ap\.gov\.in|bse\.ap\.gov\.in|slprb\.ap\.gov\.in/],
 ["Arunachal Pradesh",/arunachal|appsc\.gov\.in/],
 ["Assam",/assam|apsc\.nic\.in|sebaonline|assam-board/],
 ["Bihar",/bihar|bpsc|bseb|csbc|bpssc|bssc|btsc/],
 ["Chhattisgarh",/chhattisgarh|cgbse|cgpsc|vyapam\.cgstate/],
 ["Goa",/goa board|gbshse|goa-board/],
 ["Gujarat",/gujarat|gseb|gpsc|ojas/],
 ["Haryana",/haryana|hpsc|hssc|bseh/],
 ["Himachal Pradesh",/himachal|hprca|hpbose/],
 ["Jharkhand",/jharkhand|jpsc/],
 ["Karnataka",/karnataka|kseab|kpsc\.kar|karnataka-kpsc|karnataka-police/],
 ["Kerala",/kerala|keralapsc|pareekshabhavan/],
 ["Madhya Pradesh",/madhya pradesh|mpbse|mppsc|esb\.mp|mpesb/],
 ["Maharashtra",/maharashtra|mahahsscboard|mahresult|mahaswayam|maha-rojgar|mpsc\.gov\.in/],
 ["Manipur",/manipur|mpscmanipur|bsem\.nic/],
 ["Meghalaya",/meghalaya|mpsc\.meghalaya|mbose/],
 ["Mizoram",/mizoram|mpsc\.mizoram|mbse\.edu/],
 ["Nagaland",/nagaland|npsc\.nagaland|nbsenl/],
 ["Odisha",/odisha|opsc|ossc|osssc|bseodisha|results\.odisha/],
 ["Punjab",/punjab|ppsc\.gov\.in|punjab public service commission|pseb|sssb\.punjab/],
 ["Rajasthan",/rajasthan|rpsc|rssb|rajeduboard/],
 ["Sikkim",/sikkim|spsc\.sikkim|sikkimhrdd/],
 ["Tamil Nadu",/tamil nadu|tnpsc|tnresults|dge\.tn|trb\.tn|tnusrb|tnmrbrecruit/],
 ["Telangana",/telangana|tspsc|tgprb|bse\.telangana|cgg\.gov|tslprb/],
 ["Tripura",/tripura|tpsc|tbse/],
 ["Uttar Pradesh",/uttar pradesh|\bupmsp\b|uppsc|upsssc|uppbpb/],
 ["Uttarakhand",/uttarakhand|uttarakhand-psc|psc\.uk\.gov|ubse/],
 ["West Bengal",/west bengal|wbpsc|wbbse|wbssc|prb\.wb|wbresults/],
 ["Andaman and Nicobar Islands",/andaman|nicobar/],
 ["Chandigarh",/chandigarh/],
 ["Dadra and Nagar Haveli and Daman and Diu",/dadra|daman and diu|ddd\.gov/],
 ["Delhi",/delhi|dsssb|delhi\.gov/],
 ["Jammu and Kashmir",/jammu and kashmir|jkbose|jkssb|jkpsc/],
 ["Ladakh",/ladakh/],
 ["Lakshadweep",/lakshadweep/],
 ["Puducherry",/puducherry|pondicherry|py\.gov/]
];
function stateForItem(x){
 const sourceLabel=[x.source_id,x.source_name].join(" ").toLowerCase();
 if((!x.state||x.state==="Central")&&(/\brrb\b|\brrc\b|railway recruitment/.test(sourceLabel)))return "Central";
 const raw=String(x.state||"").trim();
 if(STATE_NAMES.includes(raw))return raw;
 const region=String(x.region||"").trim();
 if(STATE_NAMES.includes(region))return region;
 const hay=[x.source_id,x.source_name,x.title,x.exam,x.url,x.official_url,x.source_url].join(" ").toLowerCase();
 for(const [name,pattern] of STATE_PATTERNS)if(pattern.test(hay))return name;
 return "Central";
}
function stateCount(name){return allItems.filter(x=>stateForItem(x)===name).length}
function renderStateSidebar(){
 const region=$("#region");
 if(region){
  const current=selectedState||selectedRegion||"";
  region.innerHTML='<option value="">All India</option><option value="Central">Central</option>'+STATE_NAMES.map(n=>'<option value="'+esc(n)+'">'+esc(n)+'</option>').join("");
  region.value=current;
 }
 $("#allIndiaCount").textContent=allItems.length;
 $("#allStatesBtn").classList.toggle("active",!selectedState&&!selectedRegion);
 $("#stateList").innerHTML=STATE_NAMES.map(name=>'<button type="button" class="state-link'+(selectedState===name?' active':'')+'" data-state="'+esc(name)+'"><span>'+esc(name)+'</span><span class="state-count">'+stateCount(name)+'</span></button>').join("");
 $("#stateList").querySelectorAll("[data-state]").forEach(button=>button.addEventListener("click",()=>{
  window.location.href="state.html?state="+encodeURIComponent(button.dataset.state);
  return;
  selectedState=button.dataset.state;
  selectedRegion="";
  $("#region").value=selectedState;
  $("#q").value="";$("#category").value="";$("#examCategory").value="";
  page=1;render();$("#updates").scrollIntoView({behavior:"smooth",block:"start"});
 }));
 $("#allStatesBtn").onclick=()=>{
  selectedState="";selectedRegion="";$("#region").value="";page=1;render();
 };
}
function renderStateResources(){
 const box=$("#stateResources");
 if(!box)return;
 if(!selectedState){box.classList.add("hidden");box.innerHTML="";return}
 const links=STATE_PORTALS[selectedState]||[];
 const count=stateCount(selectedState);
 box.classList.remove("hidden");
 box.innerHTML='<div class="state-resource-heading"><div><p class="eyebrow">STATE / UT PORTALS</p><h3>'+esc(selectedState)+'</h3><p>'+count+' matching update'+(count===1?'':'s')+' indexed on GoResultHub.</p></div><button type="button" class="state-clear" id="clearState">Show All India</button></div>'+
 (count===0?'<p class="state-empty-note">No state-specific updates are currently indexed for this location. Check the official portals below; new notices will appear here when the monitor detects them.</p>':'')+
 '<div class="state-portal-links">'+links.map(([label,url])=>'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+' ↗</a>').join("")+'</div>';
 $("#clearState").onclick=()=>{$("#allStatesBtn").click();};
}

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
 if(/school board|board of school education|school education board|board of secondary education|secondary education board|\bcbse\b|\bcisce\b|\bnios\b|class 10|class 12|sslc|hsc|madhyamik/.test(t)) return "School Board Results";
 if(/police|constable|slprb/.test(t)) return "State Recruitment / Police";
 if(/public service commission|technical service commission|direct recruitment commission|subordinate services selection commission|staff selection commission|state service commission|\bpsc\b|\bselection commission\b/.test(t)) return "State PSC / Recruitment";
 if(/ctet|\btet\b|teacher|teaching|kvs|nvs|school service commission/.test(t)) return "Teaching / Eligibility";
 if(/defence|defense|army|navy|air force|agniveer|crpf|bsf|cisf|itbp|ssb/.test(t)) return "Defence";
 if(/icai|icsi|icmai|chartered accountant|company secretary|national medical commission/.test(t)) return "Professional Exams";
 return x.exam_category||"UPSC / Central Recruitment";
}
function filteredItems(){
 const q=$("#q").value.trim().toLowerCase(), c=$("#category").value, ec=$("#examCategory").value, r=$("#region").value;
 const list=allItems.filter(x=>{
  const family=inferredFamily(x);
  const hay=[x.title,x.exam,x.source_name,x.state,x.region,x.category,family].join(" ").toLowerCase();
  const itemState=stateForItem(x);
   const stateFilter=selectedState||selectedRegion||r;
   return (!q||hay.includes(q))&&(!c||x.category===c)&&(!ec||family===ec)&&(!stateFilter||itemState===stateFilter);
 });
 if($("#sort").value==="title") list.sort((a,b)=>(a.title||"").localeCompare(b.title||""));
 else list.sort((a,b)=>new Date(b.detected_at||b.date||0)-new Date(a.detected_at||a.date||0));
 return list;
}
function render(){
 renderStateSidebar();
  const list=filteredItems(), pages=Math.max(1,Math.ceil(list.length/PAGE_SIZE));
  renderStateResources();
 page=Math.min(page,pages);
 const visible=list.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE);
 $("#count").textContent=`${list.length} update${list.length===1?"":"s"}`;
  $("#updatesList").innerHTML=visible.map(x=>{
   const url=safeUrl(x.url||x.official_url), sourcePage=safeUrl(x.source_url);
   const sourceBadge=x.verified===true?"✓ Verified official source":(x.archive?"Official archive / portal":"Official website link");
   const explicitYear=x.exam_year||((String(x.title||x.exam||"").match(/\b20\d{2}\b/)||[])[0]||"");
   const noticeDate=x.published||"";
   const dateDetails=(explicitYear?`Exam year: ${esc(explicitYear)} · `:"")+(noticeDate?`Notice date: ${esc(noticeDate)} · `:"Notice date not shown by authority · ")+`Detected: ${esc(dateText(x.detected_at||x.date))}`;
   return `<article class="card"><div class="meta"><span class="tag">${esc(label(x.category))}</span><span class="unverified">${esc(sourceBadge)}</span></div><h3>${esc(x.title||x.exam||"Exam update")}</h3><p>${esc(x.description||x.source_name||"View the official website for full details and eligibility.")}</p><div class="source">${esc(x.source_name||x.authority||"Issuing authority")} · ${dateDetails}</div>${sourcePage&&sourcePage!==url?`<a class="link" href="${esc(sourcePage)}" target="_blank" rel="noopener noreferrer">Start at official authority website ↗</a>`:""}${url?` <a class="link secondary" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open direct notice/result (may be PDF) ↗</a>`:`<span>Official link unavailable</span>`}</article>`;
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
["q","category","examCategory","region","sort"].forEach(id=>$("#"+id).addEventListener(id==="q"?"input":"change",()=>{if(id==="region"){const v=$("#region").value;selectedState=STATE_NAMES.includes(v)?v:"";selectedRegion=v==="Central"?"Central":"";}page=1;render()}));
document.querySelectorAll(".pills [data-family]").forEach(button=>button.addEventListener("click",()=>{$("#examCategory").value=button.dataset.family;page=1;$("#updates").scrollIntoView({behavior:"smooth"});render()}));
$("#supportBtn").addEventListener("click",()=>{$("#supportNote").textContent="Secure support payments are not configured yet. We will enable this after a payment provider and checkout URL are set up.";});
init();
