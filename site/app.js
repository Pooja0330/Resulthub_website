const $ = s => document.querySelector(s);
let allItems = [];
let lastStatus = null;
const label = s => String(s||"update").replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase());
function safeUrl(u){try{const x=new URL(u);return x.protocol==="https:"?x.href:null}catch{return null}}
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function dateText(v){if(!v)return "Date not supplied";const d=new Date(v);return Number.isNaN(d.getTime())?"Date not supplied":d.toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}
function render(){
 const q=$("#q").value.trim().toLowerCase(), c=$("#category").value, ec=$("#examCategory").value, r=$("#region").value;
 let list=allItems.filter(x=>{
  const hay=[x.title,x.exam,x.source_name,x.state,x.region,x.category,x.exam_category].join(" ").toLowerCase();
  return (!q||hay.includes(q))&&(!c||x.category===c)&&(!ec||x.exam_category===ec)&&(!r||r==="All India"||((x.region||x.state||"Central")===r));
 });
 if($("#sort").value==="title") list.sort((a,b)=>(a.title||"").localeCompare(b.title||""));
 else list.sort((a,b)=>new Date(b.detected_at||b.date||0)-new Date(a.detected_at||a.date||0));
 $("#count").textContent=`${list.length} update${list.length===1?"":"s"}`;
 $("#updatesList").innerHTML=list.map(x=>{
  const url=safeUrl(x.url||x.official_url);
  const sourcePage=safeUrl(x.source_url);
  const sourceBadge=x.verified===true?"✓ Verified official source":(x.archive?"Official archive / portal":"Official website link");
  return `<article class="card"><div class="meta"><span class="tag">${esc(label(x.category))}</span><span class="unverified">${esc(sourceBadge)}</span></div><h3>${esc(x.title||x.exam||"Exam update")}</h3><p>${esc(x.description||x.source_name||"View the official website for full details and eligibility.")}</p><div class="source">${esc(x.source_name||x.authority||"Issuing authority")} · ${esc(dateText(x.detected_at||x.date))}</div>${sourcePage&&sourcePage!==url?`<a class="link" href="${esc(sourcePage)}" target="_blank" rel="noopener noreferrer">Start at official authority website ↗</a>`:""}${url?` <a class="link secondary" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open direct notice/result (may be PDF) ↗</a>`:`<span>Official link unavailable</span>`}</article>`;
 }).join("");
 $("#empty").classList.toggle("hidden",list.length>0);
 if(!list.length) $("#updatesList").innerHTML="";
}
async function loadStatus(){
 try{
  const r=await fetch("data/status.json?t="+Date.now(),{cache:"no-store"});
  if(!r.ok) throw new Error("Status unavailable");
  lastStatus=await r.json();
  const checked=lastStatus.last_checked_at?new Date(lastStatus.last_checked_at):null;
  const when=checked&&!Number.isNaN(checked.getTime())?checked.toLocaleString("en-IN",{dateStyle:"medium",timeStyle:"short",timeZone:"Asia/Kolkata"}):"Not available";
  const healthy=lastStatus.status==="healthy";
  $("#monitorStatus").textContent=healthy?"Automatic monitoring active":(lastStatus.status==="partial"?"Monitoring partially available":"Monitoring status unavailable");
  $("#monitorDetail").textContent="Last checked "+when+" IST · "+(lastStatus.sources_succeeded||0)+"/"+(lastStatus.sources_enabled||0)+" sources reachable · "+(lastStatus.sources_failed||0)+" failed · checks run about every 2 hours";
 }catch(e){
  $("#monitorStatus").textContent="Monitoring status unavailable";
  $("#monitorDetail").textContent="The website is online, but the latest checker status could not be loaded.";
 }
}
async function loadResults(){
 try{
  const r=await fetch("data/results.json?t="+Date.now(),{cache:"no-store"});
  if(!r.ok) throw new Error("Data not available");
  const data=await r.json(); allItems=Array.isArray(data)?data:[];
  render();
 }catch(e){
  if(!allItems.length){$("#count").textContent="Updates unavailable";$("#updatesList").innerHTML='<div class="empty">Updates are temporarily unavailable. Please try again later.</div>';}
 }
}
async function init(){
 $("#year").textContent=new Date().getFullYear();
 await Promise.all([loadResults(),loadStatus()]);
 window.setInterval(()=>{loadResults();loadStatus();},5*60*1000);
}
$("#searchForm").addEventListener("submit",e=>{e.preventDefault();render()});
["q","category","examCategory","region","sort"].forEach(id=>$("#"+id).addEventListener(id==="q"?"input":"change",render));
document.querySelectorAll(".pills [data-family]").forEach(button => {
  button.addEventListener("click", () => {
    $("#examCategory").value = button.dataset.family;
    $("#updates").scrollIntoView({ behavior: "smooth" });
    render();
  });
});
$("#supportBtn").addEventListener("click",()=>{$("#supportNote").textContent="Secure support payments are not configured yet. We will enable this after a payment provider and checkout URL are set up.";});
init();
