const $ = s => document.querySelector(s);
let allItems = [];
let lastStatus = null;
let page = 1;
const PAGE_SIZE = 30;

let selectedState = "";
let selectedRegion = "";
let selectedBrowse = "";
const STATE_NAMES = [
 "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat","Haryana",
 "Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh","Maharashtra","Manipur",
 "Meghalaya","Mizoram","Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana",
 "Tripura","Uttar Pradesh","Uttarakhand","West Bengal",
 "Andaman and Nicobar Islands","Chandigarh","Dadra and Nagar Haveli and Daman and Diu","Delhi",
 "Jammu and Kashmir","Ladakh","Lakshadweep","Puducherry"
];
const STATE_PORTALS = {
 "Andhra Pradesh":[["AP Public Service Commission","https://psc.ap.gov.in/"],["AP School Board","https://bse.ap.gov.in/"],["AP Police Recruitment","https://slprb.ap.gov.in/"],["Andhra University","https://www.andhrauniversity.edu.in/"],["Jawaharlal Nehru Technological University Anantapur","https://jntua.ac.in/"]],
 "Arunachal Pradesh":[["Arunachal Pradesh PSC","https://appsc.gov.in/"],["Rajiv Gandhi University","https://rgu.ac.in/"]],
 "Assam":[["Assam PSC","https://apsc.nic.in/"],["Assam Board","https://site.sebaonline.org/"],["Assam Government","https://assam.gov.in/"],["Gauhati University","https://gauhati.ac.in/"],["Dibrugarh University","https://dibru.ac.in/"]],
 "Bihar":[["Bihar State Health Society results archive","https://shs.bihar.gov.in/result"],["Bihar PSC","https://bpsc.bihar.gov.in/"],["Bihar School Board","https://biharboardonline.bihar.gov.in/"],["Constable Recruitment","https://csbc.bihar.gov.in/"],["Police Subordinate Services","https://bpssc.bihar.gov.in/"],["Bihar Technical Service Commission","https://btsc.bihar.gov.in/"],["Patna University","https://patnauniversity.ac.in/"],["Magadh University","https://www.magadhuniversity.ac.in/"]],
 "Chhattisgarh":[["Chhattisgarh PSC","https://psc.cg.gov.in/"],["Chhattisgarh Board","https://cgbse.nic.in/"],["CG Vyapam","https://vyapam.cgstate.gov.in/"]],
 "Goa":[["Goa technical education old results","https://www.dte.goa.gov.in/board-of-technical-education/old-results"],["Goa Board of Secondary and Higher Secondary Education","https://www.gbshse.in/"],["Goa Government","https://www.goa.gov.in/"],["Goa University","https://www.unigoa.ac.in/"]],
 "Gujarat":[["Gujarat PSC","https://gpsc.gujarat.gov.in/"],["Gujarat Board","https://www.gseb.org/"],["OJAS Recruitment","https://ojas.gujarat.gov.in/"],["Gujarat University","https://www.gujaratuniversity.ac.in/"]],
 "Haryana":[["Kurukshetra University old results archive","https://kuk.ac.in/results/"],["Haryana PSC","https://hpsc.gov.in/"],["Haryana Staff Selection Commission","https://www.hssc.gov.in/"],["Haryana Board","https://bseh.org.in/"],["Kurukshetra University","https://www.kuk.ac.in/"]],
 "Himachal Pradesh":[["Himachal Pradesh Recruitment Authority","https://hprca.hp.gov.in/"],["HP Board of School Education","https://hpbose.org/"],["Himachal Pradesh University","https://hpuniv.ac.in/"],["Himachal Pradesh Technical University","https://www.himtu.ac.in/"]],
 "Jharkhand":[["Jharkhand PSC","https://www.jpsc.gov.in/"],["Ranchi University","https://www.ranchiuniversity.ac.in/"]],
 "Karnataka":[["Karnataka PSC","https://kpsc.kar.nic.in/"],["Karnataka School Examination and Assessment Board","https://kseab.karnataka.gov.in/"],["Visvesvaraya Technological University","https://vtu.ac.in/"]],
 "Kerala":[["Kerala PSC","https://www.keralapsc.gov.in/"],["Kerala Board of Public Examinations","https://pareekshabhavan.kerala.gov.in/"],["Kerala Results","https://results.kerala.nic.in/"],["University of Calicut","https://uoc.ac.in/"],["University of Kerala","https://www.keralauniversity.ac.in/"]],
 "Madhya Pradesh":[["MP PSC","https://mppsc.mp.gov.in/"],["MP Board","https://mpbse.nic.in/"],["MP Employees Selection Board","https://esb.mp.gov.in/"]],
 "Maharashtra":[["MPSC announcements","https://mpsc.gov.in/announcement_and_circular/4"],["MPSC results & merit lists","https://mpsc.gov.in/results_merit_list/14"],["MPSC final recommendations","https://mpsc.gov.in/results_final_recomm_list/15"],["MPSC answer keys","https://mpsc.gov.in/answer_keys_of_examinations/45"],["MPSC interview schedules","https://mpsc.gov.in/schedule_interviews/21"],["Maharashtra Board SSC results","https://www.mahahsscboard.in/en/result/SSC"],["Maharashtra Board HSC results","https://www.mahahsscboard.in/en/result/HSC"],["Maharashtra Board home","https://www.mahahsscboard.in/"],["Maharashtra Results portal","https://mahresult.nic.in/"],["Maharashtra CET Cell / MHT-CET","https://cetcell.mahacet.org/"],["Maharashtra Government","https://maharashtra.gov.in/"],["MahaSwayam Recruitment","https://rojgar.mahaswayam.gov.in/"],["University of Mumbai","https://mu.ac.in/"],["Savitribai Phule Pune University","https://unipune.ac.in/"]],
 "Manipur":[["Manipur PSC","https://mpscmanipur.gov.in/"],["Board of Secondary Education Manipur","https://bsem.nic.in/"],["Manipur University","https://www.manipuruniv.ac.in/"]],
 "Meghalaya":[["Meghalaya PSC","https://mpsc.meghalaya.gov.in/"],["Meghalaya Board of School Education","https://mbose.in/"],["North-Eastern Hill University","https://nehu.ac.in/"]],
 "Mizoram":[["Mizoram PSC","https://mpsc.mizoram.gov.in/"],["Mizoram Board of School Education","https://mbse.edu.in/"],["Mizoram University","https://mzu.edu.in/"]],
 "Nagaland":[["Nagaland PSC","https://npsc.nagaland.gov.in/"],["Nagaland Board of School Education","https://nbsenl.edu.in/"],["Nagaland University","https://nagalanduniversity.ac.in/"]],
 "Odisha":[["Odisha PSC","https://opsc.gov.in/"],["Odisha Staff Selection Commission","https://www.ossc.gov.in/"],["Odisha Sub-ordinate Staff Selection Commission","https://www.osssc.gov.in/"],["Odisha Board","https://bseodisha.ac.in/"],["Odisha Results Portal","https://results.odisha.gov.in/"],["Utkal University","https://utkaluniversity.ac.in/"],["Sambalpur University","https://www.suniv.ac.in/"]],
 "Punjab":[["Punjab PSC","https://ppsc.gov.in/"],["Punjab School Education Board","https://www.pseb.ac.in/"],["Punjab Subordinate Services Selection Board","https://sssb.punjab.gov.in/"]],
 "Rajasthan":[["Rajasthan University old results","https://result.uniraj.ac.in/index1.php?rid=4132"],["Rajasthan PSC","https://rpsc.rajasthan.gov.in/"],["Rajasthan Staff Selection Board","https://rssb.rajasthan.gov.in/"],["Rajasthan Board","https://rajeduboard.rajasthan.gov.in/"],["University of Rajasthan","https://www.uniraj.ac.in/"]],
 "Sikkim":[["Sikkim PSC","https://spsc.sikkim.gov.in/"],["Sikkim Human Resource Development Department","https://sikkimhrdd.org/"],["Sikkim University","https://cus.ac.in/"]],
 "Tamil Nadu":[["Tamil Nadu PSC","https://www.tnpsc.gov.in/"],["Tamil Nadu Directorate of Government Examinations","https://dge.tn.gov.in/"],["Teachers Recruitment Board","https://www.trb.tn.gov.in/"],["Uniformed Services Recruitment Board","https://www.tnusrb.tn.gov.in/"],["Anna University","https://www.annauniv.edu/"]],
 "Telangana":[["Telangana PSC","https://www.tspsc.gov.in/"],["Telangana Board","https://bse.telangana.gov.in/"],["Telangana Results","https://results.cgg.gov.in/"],["Telangana Police Recruitment","https://www.tgprb.in/"],["Osmania University","https://www.osmania.ac.in/"],["Jawaharlal Nehru Technological University Hyderabad","https://jntuh.ac.in/"]],
 "Tripura":[["Tripura PSC","https://tpsc.tripura.gov.in/"],["Tripura Board of Secondary Education","https://tbse.tripura.gov.in/"],["Tripura University","https://www.tripurauniv.ac.in/"]],
 "Uttar Pradesh":[["Lucknow University old results archive","https://www.lkouniv.ac.in/en/article/annual-results-old"],["UP PSC","https://uppsc.up.nic.in/"],["UP Subordinate Services Selection Commission","https://upsssc.gov.in/"],["UP Board","https://upmsp.edu.in/"],["UP Police Recruitment","https://uppbpb.gov.in/"],["Banaras Hindu University","https://www.bhu.ac.in/"],["Aligarh Muslim University","https://www.amu.ac.in/"]],
 "Uttarakhand":[["Uttarakhand PSC","https://psc.uk.gov.in/"],["Uttarakhand Board of School Education","https://ubse.uk.gov.in/"],["Kumaun University","https://www.kunainital.ac.in/"]],
 "West Bengal":[["WBPSC results archive","https://psc.wb.gov.in/results.jsp"],["West Bengal PSC","https://psc.wb.gov.in/"],["West Bengal Board of Secondary Education","https://wbbse.wb.gov.in/"],["West Bengal School Service Commission","https://www.westbengalssc.com/"],["West Bengal Police Recruitment Board","https://prb.wb.gov.in/"],["University of Calcutta","https://www.caluniv.ac.in/"],["Jadavpur University","https://jadavpuruniversity.in/"]],
 "Andaman and Nicobar Islands":[["Andaman and Nicobar Administration","https://andaman.gov.in/"]],
 "Chandigarh":[["Chandigarh Administration","https://chandigarh.gov.in/"],["Panjab University","https://puchd.ac.in/"]],
 "Dadra and Nagar Haveli and Daman and Diu":[["Dadra and Nagar Haveli and Daman and Diu Administration","https://ddd.gov.in/"]],
 "Delhi":[["DSSSB old results","https://dsssb.delhi.gov.in/doit/tab-content/old-result?page=0"],["Delhi University historical results archive","https://exam.du.ac.in/index1.html"],["Delhi University historical results archive","https://exam.du.ac.in/index1.html"],["Delhi Subordinate Services Selection Board","https://dsssb.delhi.gov.in/"],["Delhi Government","https://delhi.gov.in/"],["University of Delhi Examination Branch","https://exam.du.ac.in/"],["Jawaharlal Nehru University","https://jnu.ac.in/"],["Jamia Millia Islamia","https://www.jmi.ac.in/"],["Indira Gandhi National Open University","https://www.ignou.ac.in/"]],
 "Jammu and Kashmir":[["Jammu and Kashmir PSC","https://jkpsc.nic.in/"],["Jammu and Kashmir Services Selection Board","https://jkssb.nic.in/"],["J&K Board of School Education","https://jkbose.nic.in/"],["University of Jammu","https://www.jammuuniversity.ac.in/"],["University of Kashmir","https://www.kashmiruniversity.net/"]],
 "Ladakh":[["Ladakh Administration","https://ladakh.gov.in/"]],
 "Lakshadweep":[["Lakshadweep Administration","https://lakshadweep.gov.in/"]],
 "Puducherry":[["Pondicherry University old results","https://exam.pondiuni.edu.in/oasis/mainpageold.html"],["Puducherry Government","https://py.gov.in/"]]
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
 const stateQuery=($("#stateQuickSearch")?.value||"").trim().toLowerCase();
  const visibleStates=STATE_NAMES.filter(name=>!stateQuery||name.toLowerCase().includes(stateQuery));
  $("#stateList").innerHTML=visibleStates.map(name=>'<button type="button" class="state-link'+(selectedState===name?' active':'')+'" data-state="'+esc(name)+'"><span>'+esc(name)+'</span><span class="state-count">'+stateCount(name)+'</span></button>').join("");
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
function absoluteTimeText(v){if(!v)return "Exact detection time unavailable";const d=new Date(v);if(Number.isNaN(d.getTime()))return "Exact detection time unavailable";return d.toLocaleString("en-IN",{day:"numeric",month:"short",year:"numeric",hour:"numeric",minute:"2-digit",second:"2-digit",hour12:true,timeZone:"Asia/Kolkata"})+" IST"}
function relativeTimeText(v){if(!v)return "time unavailable";const d=new Date(v),ms=Date.now()-d.getTime();if(Number.isNaN(d.getTime()))return "time unavailable";if(ms<60_000)return "just now";if(ms<3_600_000){const n=Math.floor(ms/60_000);return n+" minute"+(n===1?"":"s")+" ago"}if(ms<86_400_000){const n=Math.floor(ms/3_600_000);return n+" hour"+(n===1?"":"s")+" ago"}const n=Math.floor(ms/86_400_000);return n===1?"yesterday":n+" days ago"}
function detectedTimeMarkup(v){if(!v)return "Detection time not available";const d=new Date(v);if(Number.isNaN(d.getTime()))return "Detection time not available";return '<time class="relative-detection-time" datetime="'+esc(d.toISOString())+'" title="'+esc(absoluteTimeText(v))+'">'+esc(relativeTimeText(v))+'</time><span class="exact-detection-time"> · '+esc(absoluteTimeText(v))+'</span>'}
function refreshRelativeTimes(){document.querySelectorAll("time.relative-detection-time").forEach(el=>{el.textContent=relativeTimeText(el.dateTime);el.title=absoluteTimeText(el.dateTime);});}
function inferredFamily(x){
 const t=[x.source_id,x.source_name,x.title,x.exam,x.state].join(" ").toLowerCase();
 if(/\bjee\s*advanced\b/.test(t)) return "JEE Advanced";
 if(/cg\s*vyapam|cgpeb|chhattisgarh professional examination board/.test(t)) return "CG Vyapam / CGPEB";
 if(/cuet\s*pg/.test(t)) return "CUET PG";
 if(/cuet\s*ug/.test(t)) return "CUET UG";
 if(/\bjee\s*(main|mains)\b/.test(t)) return "JEE Main";
 if(/\bneet\s*(pg|post.?graduate)\b/.test(t)||/natboard\.edu/.test(t)) return "NEET PG";
 if(/\bneet\s*(ug|under.?graduate)\b/.test(t)||String(x.source_id||"")==="neet") return "NEET UG";
 if(/\b(upsc|union public service commission)\b/.test(t)&&/\b(main|mains)\b/.test(t)) return "UPSC Mains";
 if(/\b(upsc|union public service commission)\b/.test(t)&&/\b(preliminary|prelims)\b/.test(t)) return "UPSC Prelims";
 if(/\b(psc|public service commission|state services|state service|mpsc|uppsc|bpsc|rpsc|kpsc|tnpsc|opsc|gpsc|hpsc|jpsc|wbpsc)\b/.test(t)&&/\b(main|mains)\b/.test(t)) return "State PSC Mains";
 if(/\b(psc|public service commission|state services|state service|mpsc|uppsc|bpsc|rpsc|kpsc|tnpsc|opsc|gpsc|hpsc|jpsc|wbpsc)\b/.test(t)&&/\b(preliminary|prelims)\b/.test(t)) return "State PSC Prelims";
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
function browseMatches(x, view){
 if(!view)return true;
 const family=inferredFamily(x);
 const title=[x.title,x.exam,x.source_name,x.authority,x.source_id].join(" ").toLowerCase();
 if(view==="latest-results")return x.category==="result"||x.category==="merit_list"||x.category==="cutoff";
 if(view==="upcoming-results")return /upcoming results?|results? expected|expected result|result declaration date|result date announced|result will be declared|result to be declared|tentative result date/.test(title);
 if(view==="boards")return family==="School Board Results"||/school board|board of secondary education|board of school education|class 10|class 12|sslc|hsc|madhyamik|cbse|cisce|nios/.test(title);
 if(view==="competitive")return ["UPSC / Central Recruitment","SSC / Central Recruitment","Banking","Railways","Entrance & Eligibility","JEE Main","JEE Advanced","NEET UG","NEET PG","UPSC Prelims","UPSC Mains","State PSC Prelims","State PSC Mains","State PSC / Recruitment","State Recruitment / Police","Teaching / Eligibility","Defence"].includes(family);
 if(view==="recruitments")return x.category==="notification"&&(/recruit|vacanc|application|apply online|selection|post of|appointment|constable|police|staff|officer|assistant|teacher|faculty|careers|career/.test(title)||["State PSC / Recruitment","State Recruitment / Police","Teaching / Eligibility","Defence","UPSC / Central Recruitment","SSC / Central Recruitment","Banking","Railways"].includes(family));
 if(view==="universities")return /university|universit|college|deemed institute|academic council/.test(title);
 if(view==="admissions")return /admission|admissions|counselling|counseling|seat allotment|allotment|entrance application|registration form|application form|prospectus|cuet|jee main|neet ug/.test(title);
 if(view==="admit-cards")return x.category==="admit_card";
 if(view==="answer-keys")return x.category==="answer_key";
 if(view==="exam-calendar")return x.category==="exam_schedule";
 if(view==="notifications")return x.category==="notification";
 return true;
}
function renderFeatured(){
 const sortLatest=(a,b)=>new Date(b.detected_at||b.published||b.date||0)-new Date(a.detected_at||a.published||a.date||0);
 const makeList=(items,emptyText)=>items.length?items.slice(0,5).map(x=>{
  const url=safeUrl(x.url||x.official_url)||safeUrl(x.source_url);
  const date=x.published||x.detected_at||"Date not supplied";
  return '<article class="featured-item"><div><span class="tag">'+esc(label(x.category))+'</span><h3>'+esc(x.title||x.exam||"Exam update")+'</h3><p>'+esc(x.source_name||x.authority||"Official source")+' · '+esc(date)+'</p></div>'+(url?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">Open ↗</a>':'')+'</article>';
 }).join(""):'<p class="empty">'+esc(emptyText)+'</p>';
 const resultBox=$("#featuredResults"), scheduleBox=$("#featuredSchedules"), upcomingBox=$("#featuredUpcoming");
 if(resultBox){
  const rows=allItems.filter(x=>!x.archive&&(x.category==="result"||x.category==="merit_list"||x.category==="cutoff")).sort(sortLatest);
  resultBox.innerHTML=makeList(rows,"No recent result notices are indexed yet. Check the official state and exam portals below.");
 }
 if(scheduleBox){
  const rows=allItems.filter(x=>!x.archive&&x.category==="exam_schedule").sort(sortLatest);
  scheduleBox.innerHTML=makeList(rows,"No exam schedule notices are currently indexed. Official calendars and schedules appear here when detected.");
 }
 if(upcomingBox){
  const rows=allItems.filter(x=>/upcoming results?|results? expected|expected result|result declaration date|result date announced|result will be declared|result to be declared|tentative result date/i.test([x.title,x.exam,x.description].join(" "))).sort(sortLatest);
  upcomingBox.innerHTML=makeList(rows,"No authority has explicitly published an upcoming-result notice in the indexed feed yet. We will list one here when detected.");
 }
 document.querySelectorAll("[data-browse]").forEach(button=>button.classList.toggle("active",button.dataset.browse===selectedBrowse));
}
const ARCHIVE_LINKS = [["UPSC written results archive","https://www.upsc.gov.in/exams-related-info/written-result/archives"],["CBSE previous results archive","https://resultsarchives.nic.in/cbseresults/"],["DSSSB old results","https://dsssb.delhi.gov.in/doit/tab-content/old-result?page=0"],["Delhi University exam results","https://exam.du.ac.in/index1.html"],["Maharashtra results portal","https://mahresult.nic.in/"],["Rajasthan University old results","https://result.uniraj.ac.in/index1.php?rid=4132"],["Pondicherry University old results","https://exam.pondiuni.edu.in/oasis/mainpageold.html"],["West Bengal PSC results","https://psc.wb.gov.in/results.jsp"],["University of Lucknow old results","https://www.lkouniv.ac.in/en/article/annual-results-old"],["Kurukshetra University results","https://kuk.ac.in/results/"]];
function recordYear(x){
 // Prefer the actual publication year for the year filter; exam-cycle year is fallback only.
 const date=String(x.published||"").match(/(?:19|20)\\d{2}/);if(date)return date[0];
 const explicit=String(x.exam_year||"").match(/(?:19|20)\\d{2}/);if(explicit)return explicit[0];
 const titleYear=String([x.title,x.exam].join(" ")).match(/(?:19|20)\\d{2}/);return titleYear?titleYear[0]:"";
}
function renderYearBrowser(){
 const box=$("#yearBrowser");if(!box)return;const selected=$("#examYear").value,counts={};
 allItems.forEach(item=>{const year=recordYear(item);if(year)counts[year]=(counts[year]||0)+1;});
 box.innerHTML=Array.from({length:27},(_,i)=>2026-i).map(year=>'<button type="button" class="year-chip'+(selected===String(year)?' active':'')+'" data-year="'+year+'" aria-pressed="'+(selected===String(year)?'true':'false')+'"><span>'+year+'</span><small>'+(counts[String(year)]||0)+'</small></button>').join('')+'<button type="button" class="year-chip'+(!selected?' active':'')+'" data-year="" aria-pressed="'+(!selected?'true':'false')+'"><span>All years</span><small>'+allItems.length+'</small></button>';
 box.querySelectorAll("[data-year]").forEach(button=>button.addEventListener("click",()=>{$("#examYear").value=button.dataset.year;page=1;render();$("#updates").scrollIntoView({behavior:"smooth",block:"start"});}));
}
function renderYearArchiveHelp(){
 const box=$("#yearArchiveHelp");if(!box)return;const year=$("#examYear").value,list=filteredItems();
 if(!year||year==="unknown"||list.length){box.classList.add("hidden");box.innerHTML="";return;}
 box.classList.remove("hidden");box.innerHTML='<h3>No individual records indexed for '+esc(year)+' yet</h3><p>This means GoResultHub has not indexed matching year-specific entries; it does not mean no exams or results existed in '+esc(year)+'. Check these official archive starting points while historical coverage is expanded.</p><div class="archive-help-links">'+ARCHIVE_LINKS.map(([label,url])=>'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+' ↗</a>').join("")+'</div>';
}
function isPibItem(x){return /pib|press information bureau|press releases|government & pib/i.test([x.source_id,x.source_name,x.authority,x.exam_category].filter(Boolean).join(" "));}
function mainPriority(x){if(isPibItem(x))return 2;if(x.archive===true)return 3;if(x.verified===true&&!/archive/i.test(String(x.title||"")))return 0;return 1;}
function displayTitle(x){const title=String(x.title||x.exam||"Exam update");if(isPibItem(x)&&/[\\u0900-\\u097F]/.test(title))return "Government & PIB update (Hindi-language release)";return title;}
function filteredItems(){
 const q=$("#q").value.trim().toLowerCase(), terms=q.split(/\s+/).filter(Boolean), c=$("#category").value, ec=$("#examCategory").value, r=$("#region").value, y=$("#examYear").value;
 const list=allItems.filter(x=>{
  const family=inferredFamily(x);
  const hay=[x.title,x.exam,x.source_name,x.state,x.region,x.category,family].join(" ").toLowerCase();
  const itemState=stateForItem(x);
   const stateFilter=selectedState||selectedRegion||r;
   const year=recordYear(x);
   const queryMatch=!terms.length||terms.every(term=>hay.includes(term))||terms.some(term=>hay.includes(term));
    const effectiveStateFilter=stateFilter==="All India"?"":stateFilter;
    return queryMatch&&(!c||x.category===c)&&(!ec||family===ec)&&(!effectiveStateFilter||itemState===effectiveStateFilter)&&(!y||(y==="unknown"?!year:year===y))&&browseMatches(x,selectedBrowse);
 });
 if($("#sort").value==="title") list.sort((a,b)=>(a.title||"").localeCompare(b.title||""));
 else list.sort((a,b)=>new Date(b.published||b.detected_at||b.date||0)-new Date(a.published||a.detected_at||a.date||0)||mainPriority(a)-mainPriority(b));
 return list;
}
function render(){
 try{
 renderStateSidebar();
  const list=filteredItems(), pages=Math.max(1,Math.ceil(list.length/PAGE_SIZE));
  renderStateResources();
 page=Math.min(page,pages);
 const visible=list.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE);
 $("#count").textContent=`${list.length} update${list.length===1?"":"s"}`;
  $("#updatesList").innerHTML=visible.map(x=>{
   const url=safeUrl(x.url||x.official_url);
   const sourceBadge=x.archive?"Historical archive":(x.verified===true?"✓ Verified official source":"Official website link");
   const explicitYear=x.exam_year||((String(x.title||x.exam||"").match(/\b20\d{2}\b/)||[])[0]||"");
   const noticeDate=x.published||"";
   const dateDetails=(explicitYear?`Exam year: ${esc(explicitYear)} · `:"")+(noticeDate?`Notice date: ${esc(noticeDate)} · `:"Notice date not shown by authority · ")+`Detected by GoResultHub: ${detectedTimeMarkup(x.detected_at||x.date)}`;
   return `<article class="card"><div class="meta"><span class="tag">${esc(label(x.category))}</span><span class="unverified">${esc(sourceBadge)}</span></div><h3>${esc(displayTitle(x))}</h3><p>${esc(x.description||x.source_name||"View the official website for full details and eligibility.")}</p><div class="source">${esc(x.source_name||x.authority||"Issuing authority")} · ${dateDetails}</div>${url?(x.direct===true||/\/(?:login|candidate-login|candidatelogin|score.?display|result.?status)(?:[/?#]|$)/i.test(new URL(url).pathname)?` <a class="link secondary" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open official login ↗</a>`:` <a class="link secondary" href="${esc("notice.html?id="+encodeURIComponent(x.id||"")+"&q="+encodeURIComponent(x.title||x.exam||"Exam update"))}" rel="noopener">View update on GoResultHub ↗</a>`):`<span>Official link unavailable</span>`}<button type="button" class="share-update" data-share-title="${esc(x.title||x.exam||"Exam update")}" data-share-url="${esc("https://goresulthub.com/notice.html?id="+encodeURIComponent(x.id||"")+"&q="+encodeURIComponent(x.title||x.exam||""))}">Share this update ↗</button></article>`;
  }).join("");
 $("#empty").classList.toggle("hidden",list.length>0);
 if(!list.length) $("#updatesList").innerHTML="";
 const pager=$("#pagination");
 if(pager){
  pager.innerHTML=list.length>PAGE_SIZE?`<button type="button" id="prevPage" class="secondary" ${page===1?"disabled":""}>Previous</button><span>Page ${page} of ${pages}</span><button type="button" id="nextPage" class="secondary" ${page===pages?"disabled":""}>Next</button>`:"";
  $("#prevPage")?.addEventListener("click",()=>{page--;render();$("#updates").scrollIntoView({behavior:"smooth"});});
  $("#nextPage")?.addEventListener("click",()=>{page++;render();$("#updates").scrollIntoView({behavior:"smooth"});});
 }
 renderFeatured();
 }catch(error){console.error("GoResultHub render failed:",error);const count=$("#count"),list=$("#updatesList");if(count)count.textContent="Display error";if(list)list.innerHTML='<div class="empty">Updates were downloaded but could not be displayed. Please refresh the page or use Retry loading updates.</div>';}
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
   $("#monitorDetail").textContent="Last checked "+when+" IST · "+(lastStatus.sources_succeeded||0)+"/"+(lastStatus.sources_enabled||0)+" sources reachable · "+(lastStatus.sources_failed||0)+" failed · "+(lastStatus.alerts_pending||0)+" alerts pending delivery · checks run about every hour"+(stale?" · latest scan is over 4 hours old":"");
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
   const r=await fetch("data/results.json",{cache:"no-cache"});
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
   console.error("GoResultHub results load/render failed:",e);$("#count").textContent=allItems.length?"Updates need a refresh":"Updates unavailable";$("#updatesList").innerHTML='<div class="empty">Updates could not finish loading. <button type="button" id="retryUpdates">Retry loading updates</button></div>';$("#retryUpdates")?.addEventListener("click",()=>{allItems=[];loadResults()});
  }finally{resultsRequest=null}
 })();
 return resultsRequest;
}
async function refresh(){if(document.visibilityState==="visible")await Promise.all([loadResults(),loadStatus()])}
function resetUpdateFilters(){
 $("#category").value="";$("#examCategory").value="";$("#region").value="";$("#examYear").value="";$("#sort").value="new";
 selectedState="";selectedRegion="";selectedBrowse="";page=1;
 document.querySelectorAll("[data-browse]").forEach(button=>button.classList.remove("active"));
}
function init(){
 $("#year").textContent=new Date().getFullYear();
 resetUpdateFilters();
 // Start with a clean homepage on every load; search text is not a persistent filter.
 $("#q").value="";
 if(window.location.search){history.replaceState(null,"",window.location.pathname+window.location.hash);}
 try{const cached=JSON.parse(localStorage.getItem("goresult-results-cache")||"null");if(Array.isArray(cached?.items)){allItems=cached.items;render()}}catch(e){}
 refresh();
 if(refreshTimer)clearInterval(refreshTimer);
 refreshTimer=setInterval(refresh,15*60*1000);
 document.addEventListener("visibilitychange",()=>{if(document.visibilityState==="visible")refresh()});
  // Clear stale filter UI when browsers restore the page from the back-forward cache.
  window.addEventListener("pageshow",event=>{if(event.persisted){resetUpdateFilters();render();}});
 if("serviceWorker" in navigator)navigator.serviceWorker.register("sw.js").catch(()=>{});
}
function clearUpdateFilters(){
 $("#category").value="";$("#examCategory").value="";$("#region").value="";$("#examYear").value="";
 selectedState="";selectedRegion="";selectedBrowse="";
}
function runSearch(scroll=true){
 const term=$("#q").value.trim();clearUpdateFilters();
 if(quickSearch)quickSearch.value=term;
 const shortcutCount=filterQuickExams(term);page=1;render();
 if(scroll){const target=term&&shortcutCount?$("#find-exams"):$("#updates");target.scrollIntoView({behavior:"smooth",block:"start"});}
}
$("#searchForm").addEventListener("submit",e=>{e.preventDefault();runSearch(true)});
$("#q").addEventListener("input",()=>{clearUpdateFilters();if(quickSearch)quickSearch.value=$("#q").value;filterQuickExams($("#q").value);page=1;render()});
["category","examCategory","region","sort","examYear"].forEach(id=>$("#"+id).addEventListener("change",()=>{if(id==="region"){const v=$("#region").value;selectedState=STATE_NAMES.includes(v)?v:"";selectedRegion=v==="Central"?"Central":"";}page=1;render()}));
 $("#clearFilters")?.addEventListener("click",()=>{$("#q").value="";$("#quickExamSearch").value="";$("#category").value="";$("#examCategory").value="";$("#region").value="";$("#examYear").value=String(new Date().getFullYear());$("#sort").value="new";selectedState="";selectedRegion="";selectedBrowse="";filterQuickExams("");page=1;render();$("#updates").scrollIntoView({behavior:"smooth",block:"start"});});
document.querySelectorAll(".pills [data-family]").forEach(button=>button.addEventListener("click",()=>{$("#examCategory").value=button.dataset.family;page=1;$("#updates").scrollIntoView({behavior:"smooth"});render()}));
document.querySelectorAll("[data-quick-search]").forEach(button=>button.addEventListener("click",()=>{const term=button.dataset.quickSearch||"";$("#q").value=term;if(quickSearch)quickSearch.value=term;filterQuickExams(term);$("#category").value="";$("#examCategory").value="";$("#region").value="";$("#examYear").value="";selectedState="";selectedRegion="";selectedBrowse="";page=1;render();$("#updates").scrollIntoView({behavior:"smooth",block:"start"});}));
$("#stateQuickSearch")?.addEventListener("input",()=>renderStateSidebar());
const quickSearch=$("#quickExamSearch");
function filterQuickExams(value){const term=(value||"").trim().toLowerCase();let shown=0;document.querySelectorAll(".quick-exam-card").forEach(card=>{const match=!term||(card.dataset.keywords+" "+card.innerText).toLowerCase().includes(term);card.classList.toggle("hidden",!match);if(match)shown++;});document.querySelectorAll(".quick-exam-group").forEach(group=>group.classList.toggle("hidden",!group.querySelector(".quick-exam-card:not(.hidden)")));$("#quickExamEmpty")?.classList.toggle("hidden",shown>0);return shown;}
 quickSearch?.addEventListener("input",()=>filterQuickExams(quickSearch.value));

document.querySelectorAll("[data-browse]").forEach(button=>button.addEventListener("click",()=>{
 selectedBrowse=button.dataset.browse||"";
 selectedState="";selectedRegion="";
 $("#region").value="";$("#q").value="";$("#category").value="";$("#examCategory").value="";
 page=1;render();
 $("#updates").scrollIntoView({behavior:"smooth",block:"start"});
}));

document.addEventListener("click",event=>{
 const anchor=event.target.closest(".quick-exam-card a, .sidebar-exams a");
 if(!anchor||!anchor.href)return;
 const raw=anchor.getAttribute("href")||"";
 if(!raw.startsWith("https://"))return;
 let destination; try{destination=new URL(raw,location.href)}catch(e){return}
 if(destination.hostname==="goresulthub.com"||destination.hostname.endsWith(".goresulthub.com"))return;
 event.preventDefault();
 const card=anchor.closest(".quick-exam-card");
 const title=(card&&card.querySelector("h4")&&card.querySelector("h4").textContent.trim())||anchor.textContent.replace(/[↗→]/g,"").trim()||"Exam information";
 const description=(card&&card.querySelector("p")&&card.querySelector("p").textContent.trim())||"Find official notifications, applications, admit cards, answer keys, result notices and candidate login options from the issuing authority.";
 const source=destination.hostname.replace(/^www[.]/,"");
 location.href="go.html?title="+encodeURIComponent(title)+"&description="+encodeURIComponent(description)+"&url="+encodeURIComponent(destination.href)+"&source="+encodeURIComponent(source);
});
document.addEventListener("click",async event=>{
 const button=event.target.closest("[data-share-url]");
 if(!button)return;
 const shareUrl=button.dataset.shareUrl||"https://goresulthub.com/";
 const shareTitle=button.dataset.shareTitle||"GoResultHub exam update";
 try{
  if(navigator.share)await navigator.share({title:shareTitle,text:"Check this exam update on GoResultHub:",url:shareUrl});
  else if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(shareUrl);button.textContent="Link copied ✓";setTimeout(()=>{button.textContent="Share this update ↗"},1800);}
  else window.prompt("Copy this GoResultHub link:",shareUrl);
 }catch(error){if(error?.name!=="AbortError")console.warn("Share was not completed",error);}
});
init();
setInterval(refreshRelativeTimes,30000);
