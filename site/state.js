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
 "Maharashtra":[["MPSC announcements","https://mpsc.gov.in/announcement_and_circular/4"],["MPSC results & merit lists","https://mpsc.gov.in/results_merit_list/14"],["MPSC final recommendations","https://mpsc.gov.in/results_final_recomm_list/15"],["MPSC answer keys","https://mpsc.gov.in/answer_keys_of_examinations/45"],["MPSC interview schedules","https://mpsc.gov.in/schedule_interviews/21"],["Maharashtra Board SSC results","https://www.mahahsscboard.in/en/result/SSC"],["Maharashtra Board HSC results","https://www.mahahsscboard.in/en/result/HSC"],["Maharashtra Board home","https://www.mahahsscboard.in/"],["Maharashtra Results portal","https://mahresult.nic.in/"],["Maharashtra CET Cell / MHT-CET","https://cetcell.mahacet.org/"],["Maharashtra Government","https://maharashtra.gov.in/"],["MahaSwayam Recruitment","https://rojgar.mahaswayam.gov.in/"]],
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

const $ = s => document.querySelector(s);
const esc = s => String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const safeUrl = u => { try { const x=new URL(u); return x.protocol==="https:"?x.href:null; } catch { return null; } };
const titleCase = s => String(s||"update").replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase());
const params = new URLSearchParams(location.search);
const state = params.get("state") || "";
const pageSize = 30;
let allItems = [], page = 1, selectedCategory = "", selectedFamily = "";
const families = ["All exam families","UPSC / Central Recruitment","SSC / Central Recruitment","Banking","Railways","School Board Results","Entrance & Eligibility","State PSC / Recruitment","State Recruitment / Police","Teaching / Eligibility","Defence","Professional Exams"];
const categories = [["","All updates"],["notification","Notifications"],["result","Results"],["admit_card","Admit cards"],["answer_key","Answer keys"],["merit_list","Merit lists"],["cutoff","Cutoffs"],["exam_schedule","Exam schedules"]];
function inferredFamily(x){
 const t=[x.source_id,x.source_name,x.title,x.exam,x.state].join(" ").toLowerCase();
 if(/\bjee\s*advanced\b/.test(t)) return "JEE Advanced";
 if(/\bjee\s*(main|mains)\b/.test(t)) return "JEE Main";
 if(/\bneet\s*(pg|post.?graduate)\b/.test(t)||/natboard\.edu/.test(t)) return "NEET PG";
 if(/\bneet\s*(ug|under.?graduate)\b/.test(t)||String(x.source_id||"")==="neet") return "NEET UG";
 if(/\b(upsc|union public service commission)\b/.test(t)&&/\b(main|mains)\b/.test(t)) return "UPSC Mains";
 if(/\b(upsc|union public service commission)\b/.test(t)&&/\b(preliminary|prelims)\b/.test(t)) return "UPSC Prelims";
 if(/\b(psc|public service commission|state services|state service|mpsc|uppsc|bpsc|rpsc|kpsc|tnpsc|opsc|gpsc|hpsc|jpsc|wbpsc)\b/.test(t)&&/\b(main|mains)\b/.test(t)) return "State PSC Mains";
 if(/\b(psc|public service commission|state services|state service|mpsc|uppsc|bpsc|rpsc|kpsc|tnpsc|opsc|gpsc|hpsc|jpsc|wbpsc)\b/.test(t)&&/\b(preliminary|prelims)\b/.test(t)) return "State PSC Prelims";
 if(/railway recruitment|\brrb\b|\brrc\b|ntpc|group d|assistant loco pilot|\balp\b/.test(t))return "Railways";
 if(/\bibps\b|state bank of india|\bsbi\b|reserve bank of india|\brbi\b|banking|\blic\b|insurance regulatory|niacl|uiic|pfrda/.test(t))return "Banking";
 if(/staff selection commission|\bssc (cgl|chsl|mts|gd|stenographer)\b/.test(t))return "SSC / Central Recruitment";
 if(/union public service commission|\bupsc\b/.test(t))return "UPSC / Central Recruitment";
 if(/national testing agency|\bnta\b|\bjee\b|\bneet\b|\bcuet\b|\bgate\b|ugc net|csir net/.test(t))return "Entrance & Eligibility";
 if(/school board|board of school education|school education board|board of secondary education|secondary education board|\bcbse\b|\bcisce\b|\bnios\b|class 10|class 12|sslc|hsc|madhyamik/.test(t))return "School Board Results";
 if(/police|constable|slprb/.test(t))return "State Recruitment / Police";
 if(/public service commission|technical service commission|direct recruitment commission|subordinate services selection commission|staff selection commission|state service commission|\bpsc\b|selection commission/.test(t))return "State PSC / Recruitment";
 if(/ctet|\btet\b|teacher|teaching|kvs|nvs|school service commission/.test(t))return "Teaching / Eligibility";
 if(/defence|defense|army|navy|air force|agniveer|crpf|bsf|cisf|itbp|ssb/.test(t))return "Defence";
 if(/icai|icsi|icmai|chartered accountant|company secretary|national medical commission/.test(t))return "Professional Exams";
 return x.exam_category||"UPSC / Central Recruitment";
}
function stateCount(name){return allItems.filter(x=>stateForItem(x)===name).length}
function renderStateLinks(){
 $("#stateDirectory").innerHTML=STATE_NAMES.map(n=>'<a class="state-directory-link'+(n===state?' active':'')+'" href="state.html?state='+encodeURIComponent(n)+'">'+esc(n)+' <span>'+stateCount(n)+'</span></a>').join("");
}
function renderPortals(){
 const links=STATE_PORTALS[state]||[];
 $("#officialPortals").innerHTML=links.length?links.map(([label,url])=>'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+' ↗</a>').join(""):'<p>No portal links have been configured yet.</p>';
}
function render(){
 const filtered=allItems.filter(x=>stateForItem(x)===state&&(!selectedCategory||x.category===selectedCategory)&&(!selectedFamily||inferredFamily(x)===selectedFamily));
 filtered.sort((a,b)=>new Date(b.detected_at||b.date||0)-new Date(a.detected_at||a.date||0));
 const pages=Math.max(1,Math.ceil(filtered.length/pageSize)); page=Math.min(page,pages);
 $("#stateCount").textContent=filtered.length+" update"+(filtered.length===1?"":"s");
 $("#stateUpdates").innerHTML=filtered.slice((page-1)*pageSize,page*pageSize).map(x=>{
  const url=safeUrl(x.url||x.official_url), source=safeUrl(x.source_url);
  const date=x.published||x.detected_at||x.date;
  const dateText=date&&!Number.isNaN(new Date(date).getTime())?new Date(date).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"}):"Date not supplied";
  const tag=titleCase(x.category);
  return '<article class="card"><div class="meta"><span class="tag">'+esc(tag)+'</span><span class="unverified">'+(x.verified===true?'✓ Verified official source':'Official source link')+'</span></div><h3>'+esc(x.title||x.exam||"Exam update")+'</h3><p>'+esc(x.description||x.source_name||"Open the official authority link for full details.")+'</p><div class="source">'+esc(x.source_name||x.authority||"Issuing authority")+' · '+esc(dateText)+'</div>'+(source&&source!==url?'<a class="link" href="'+esc(source)+'" target="_blank" rel="noopener noreferrer">Official authority ↗</a>':'')+(url?'<a class="link secondary" href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">Open notice / result ↗</a>':'<span>Direct notice link not available; use the official portals above.</span>')+'</article>';
 }).join("");
 $("#noStateUpdates").classList.toggle("hidden",filtered.length>0);
 $("#statePagination").innerHTML=filtered.length>pageSize?'<button id="previous" class="secondary" '+(page===1?'disabled':'')+'>Previous</button><span>Page '+page+' of '+pages+'</span><button id="next" class="secondary" '+(page===pages?'disabled':'')+'>Next</button>':'';
 $("#previous")?.addEventListener("click",()=>{page--;render();window.scrollTo({top:0,behavior:"smooth"})});
 $("#next")?.addEventListener("click",()=>{page++;render();window.scrollTo({top:0,behavior:"smooth"})});
}
async function init(){
 const valid=STATE_NAMES.includes(state);
 const chosen=valid?state:"";
 if(!valid){
  $("#stateTitle").textContent="Select a state or Union Territory";
  $("#stateIntro").textContent="Choose a location below to view its exam notifications and results.";
  $("#stateCount").textContent="Choose a state to begin";
  $("#stateFilters").classList.add("hidden");
 }else{
  document.title=chosen+" Exam Notifications & Results | GoResultHub";
  $("#stateTitle").textContent=chosen+" Exam Notifications & Results";
  $("#stateIntro").textContent="Browse available recruitment notifications, exam schedules, admit cards, answer keys, merit lists and results for "+chosen+". Each update links to the relevant official authority when available.";
  $("#stateFilters").classList.remove("hidden");
  renderPortals();
 }
 renderStateLinks();
 try{
  const r=await fetch("data/results.json");
  if(!r.ok)throw new Error("Feed unavailable");
  const data=await r.json(); if(!Array.isArray(data))throw new Error("Invalid feed");
  allItems=data;
  renderStateLinks();
 }catch(e){
  $("#noStateUpdates").textContent="The updates feed is temporarily unavailable. Please retry later or use the official portals listed above.";
  $("#noStateUpdates").classList.remove("hidden");
 }
 if(valid)render();
 $("#examFamily").addEventListener("change",()=>{selectedFamily=$("#examFamily").value;page=1;render()});
 $("#updateType").addEventListener("change",()=>{selectedCategory=$("#updateType").value;page=1;render()});
 $("#allIndiaLink").href="index.html";
}
init();
