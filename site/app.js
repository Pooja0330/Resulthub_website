const $ = s => document.querySelector(s);
let allItems = [];
const label = s => String(s||"update").replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase());
function safeUrl(u){try{const x=new URL(u);return x.protocol==="https:"?x.href:null}catch{return null}}
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function dateText(v){if(!v)return "Date not supplied";const d=new Date(v);return Number.isNaN(d.getTime())?"Date not supplied":d.toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}
function render(){
 const q=$("#q").value.trim().toLowerCase(), c=$("#category").value, r=$("#region").value;
 let list=allItems.filter(x=>{
  const hay=[x.title,x.exam,x.source_name,x.state,x.region,x.category].join(" ").toLowerCase();
  return (!q||hay.includes(q))&&(!c||x.category===c)&&(!r||r==="All India"||((x.region||x.state||"Central")===r));
 });
 if($("#sort").value==="title") list.sort((a,b)=>(a.title||"").localeCompare(b.title||""));
 else list.sort((a,b)=>new Date(b.detected_at||b.date||0)-new Date(a.detected_at||a.date||0));
 $("#count").textContent=`${list.length} update${list.length===1?"":"s"}`;
 $("#updatesList").innerHTML=list.map(x=>{
  const url=safeUrl(x.url||x.official_url);
  return `<article class="card"><div class="meta"><span class="tag">${esc(label(x.category))}</span><span class="unverified">${x.verified===true?"✓ Verified by GoResultHub":"Official-source link · verify details"}</span></div><h3>${esc(x.title||x.exam||"Exam update")}</h3><p>${esc(x.description||x.source_name||"Check the issuing authority for full details and eligibility.")}</p><div class="source">${esc(x.source_name||x.authority||"Issuing authority")} · ${esc(dateText(x.detected_at||x.date))}</div>${url?`<a class="link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open official source ↗</a>`:`<span>Official link unavailable</span>`}</article>`;
 }).join("");
 $("#empty").classList.toggle("hidden",list.length>0);
 if(!list.length) $("#updatesList").innerHTML="";
}
async function init(){
 $("#year").textContent=new Date().getFullYear();
 try{
  const r=await fetch("data/results.json",{cache:"no-store"});
  if(!r.ok) throw new Error("Data not available");
  const data=await r.json(); allItems=Array.isArray(data)?data:[];
  render();
 }catch(e){allItems=[];$("#count").textContent="Updates unavailable";$("#updatesList").innerHTML='<div class="empty">Updates are temporarily unavailable. Please try again later.</div>';}
}
$("#searchForm").addEventListener("submit",e=>{e.preventDefault();render()});
["q","category","region","sort"].forEach(id=>$("#"+id).addEventListener(id==="q"?"input":"change",render));
$("#supportBtn").addEventListener("click",()=>{$("#supportNote").textContent="Secure support payments are not configured yet. We will enable this after a payment provider and checkout URL are set up.";});
init();