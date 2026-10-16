(() => {
  "use strict";
  const FEED_URL = "data/results.json";
  const STORAGE_KEY = "grh_seen_official_updates_v1";
  const MAX_SEEN = 500;
  const POLL_MS = 60000;
  const $ = (s) => document.querySelector(s);
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const safeUrl = (value) => {
    try { const u = new URL(value, location.href); return u.protocol === "https:" ? u.href : null; }
    catch (_) { return null; }
  };
  const categoryName = (value) => ({
    notification:"Notification",result:"Result",admit_card:"Admit card",answer_key:"Answer key",
    merit_list:"Merit list",cutoff:"Cutoff",exam_schedule:"Exam schedule"
  }[value] || "Official update");

  const isPib = item => /pib|press information bureau|press releases|government & pib/i.test([item.id,item.source_id,item.source_name,item.authority,item.exam_category].filter(Boolean).join(" "));
  const isExamPriority = item => !isPib(item) && item.archive !== true && /result|notification|admit_card|answer_key|merit_list|cutoff|exam_schedule/i.test(String(item.category||"")) && !/annual results old|old archive|historical|public notices information bulletin syllabus universities|home \/ annual results old/i.test(String(item.title||""));
  const priorityScore = item => isExamPriority(item) ? 0 : isPib(item) ? 2 : 1;
  const itemKindLabel = item => isPib(item) ? "GOVERNMENT & PIB" : isExamPriority(item) ? "EXAM ALERT" : "OFFICIAL UPDATE";
  const itemKindClass = item => isPib(item) ? "is-pib" : isExamPriority(item) ? "is-exam" : "is-general";
  const cleanTitle = item => String(item.title || item.exam || "Official exam update").replace(/\s+/g," ").replace(/\s*[|·•].*$/,"").trim();
  const normalizedTitle = item => cleanTitle(item).toLowerCase().replace(/[^a-z0-9]+/g," ").trim();
  const isNoise = item => {
    const title=normalizedTitle(item);
    const url=String(item.url||item.official_url||item.source_url||"").toLowerCase();
    if (!title || title.length<8) return true;
    // Suppress navigation/menu text scraped as if it were an announcement.
    const menuPatterns = [
      /\bhome current vacancies vacancies call letters results summer placements research internship scholarships post based rosters/,
      /\bmpbse portal results time table rti contact us\b/,
      /\brecruitment notifications exam schedule interview schedule postwise syllabus physical efficiency tests/,
      /\bhome about us about nta about nic information information bulletin/,
      /\bhome about nta information information bulletin syllabus universities archive/,
      /\bpublic notices information bulletin syllabus universities\b/,
      /\bhome annual results old\b/,
      /\bcandidates corner e services/
    ];
    if (menuPatterns.some(pattern=>pattern.test(title))) return true;
    const navTerms = title.match(/\b(home|about us|about nta|contact us|faq|help desk|payment related|universities|archive|syllabus|information bulletin|public notices|current vacancies|call letters|summer placements|research internship|rosters|rti)\b/g) || [];
    if (navTerms.length >= 3 && title.split(" ").length > 7) return true;
    // These pages are generally site navigation, contact, FAQ, archive, or index pages,
    // not individual exam announcements.
    if (/\/(faq|contact-us|contactus|about-nta|archive|index|home)(\.html)?(\?|$|#)/.test(url)) return true;
    if (/^(home|about us|contact us|faq|help desk|latest updates|official website|read more|click here)$/.test(title)) return true;
    return false;
  };
  const uniqueItems = items => {
    const keys=new Set();
    return items.filter(item=>{
      if(isNoise(item))return false;
      const key=normalizedTitle(item)+"|"+String(item.source_name||item.authority||item.source_id||"").toLowerCase().replace(/\s+/g," ").trim();
      if(keys.has(key))return false;
      keys.add(key);return true;
    });
  };
  const identity = item => normalizedTitle(item)+"|"+String(item.source_name||item.authority||item.source_id||"").toLowerCase().replace(/\s+/g," ").trim();
  const readSeen = () => {
    try { const x=JSON.parse(localStorage.getItem(STORAGE_KEY)||"[]"); return new Set(Array.isArray(x)?x:[]); }
    catch (_) { return new Set(); }
  };
  const writeSeen = (seen) => { try { localStorage.setItem(STORAGE_KEY, JSON.stringify([...seen].slice(-MAX_SEEN))); } catch (_) {} };
  const ui = document.createElement("div");
  ui.id = "grh-live-alerts";
  ui.innerHTML = '<button type="button" class="grh-bell" aria-expanded="false" aria-controls="grh-alert-panel" aria-label="Open latest official updates"><span aria-hidden="true">🔔</span><span class="grh-bell-label">Live updates</span><span class="grh-badge" hidden>0</span></button><section id="grh-alert-panel" class="grh-alert-panel" hidden aria-label="Latest official updates"><header><div><strong>Latest official updates</strong><small>From the GoResultHub official-source checker</small></div><button type="button" class="grh-enable-notifications">Enable alerts</button><button type="button" class="grh-close" aria-label="Close updates">×</button></header><p class="grh-alert-status" aria-live="polite">Checking for updates…</p><div class="grh-alert-list"></div><footer>Updates appear after the checker detects them. Always confirm details on the issuing authority’s website.</footer></section><div class="grh-toast-stack" aria-live="polite" aria-atomic="false"></div>';
  document.body.appendChild(ui);
  const bell = $(".grh-bell"), panel = $("#grh-alert-panel"), list = $(".grh-alert-list"), status = $(".grh-alert-status"), badge = $(".grh-badge"), stack = $(".grh-toast-stack");
  let seen = readSeen(), initialized = false, unread = 0, busy = false;
  const allItems = [];
  function updateBadge() {
    badge.textContent = String(unread);
    badge.hidden = unread < 1;
  }
  function renderPanel(items) {
    const current = items.slice(0, 6);
    list.innerHTML = current.length ? current.map(item => {
      const url="https://goresulthub.com/notice.html?id="+encodeURIComponent(item.id||"")+"&q="+encodeURIComponent(item.title || item.exam || "");
      const date=item.published || item.detected_at || "";
      const description=String(item.description || item.exam || "Open this update for full details.").replace(/\s+/g," ").trim();
      const shortDescription=description.length>125?description.slice(0,122).trimEnd()+"…":description;
      return '<article class="grh-alert-item '+itemKindClass(item)+'"><span class="grh-alert-type">'+esc(categoryName(item.category))+'</span><span class="grh-alert-kind">'+itemKindLabel(item)+'</span><strong>'+esc(cleanTitle(item))+'</strong><p class="grh-alert-description">'+esc(shortDescription)+'</p><small>'+esc(item.source_name || item.authority || "Official source")+(date?' · '+esc(date):'')+'</small>'+(url?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">View on GoResultHub ↗</a>':'<span class="grh-no-link">Official link not available in feed</span>')+'</article>';
    }).join("") : '<p class="grh-alert-empty">No updates have been indexed yet. Keep this page open; the panel checks the published feed periodically.</p>';
  }
  function toast(item) {
    const url="https://goresulthub.com/notice.html?id="+encodeURIComponent(item.id||"")+"&q="+encodeURIComponent(item.title || item.exam || "");
    const node=document.createElement("article");
    node.className="grh-toast "+itemKindClass(item);
    const description=String(item.description || item.exam || "Open this update for full details.").replace(/\s+/g," ").trim();
    const shortDescription=description.length>95?description.slice(0,92).trimEnd()+"…":description;
    node.innerHTML='<div class="grh-toast-top"><span>'+itemKindLabel(item)+'</span><button type="button" aria-label="Dismiss">×</button></div><strong>'+esc(cleanTitle(item))+'</strong><small>'+esc(shortDescription)+'</small><small>'+esc(item.source_name || item.authority || "Official source")+' · '+esc(categoryName(item.category))+'</small>'+(url?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">View update ↗</a>':'');
    node.querySelector("button").addEventListener("click",()=>node.remove());
    stack.prepend(node);
    while(stack.children.length>3)stack.lastElementChild.remove();
  }
  async function poll() {
    if (busy) return;
    busy = true;
    try {
      const response=await fetch(FEED_URL,{cache:"no-cache"});
      if(!response.ok)throw new Error("Feed request failed ("+response.status+")");
      const data=await response.json();
      if(!Array.isArray(data))throw new Error("Feed format was not recognised");
      const sorted=uniqueItems(data).sort((a,b)=>priorityScore(a)-priorityScore(b)||String(b.detected_at||b.published||b.date||"").localeCompare(String(a.detected_at||a.published||a.date||"")));
      allItems.splice(0,allItems.length,...sorted);
      renderPanel(allItems);
      status.textContent=data.length+" indexed updates · last checked "+new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"});
      if(!initialized) {
        data.forEach(item=>seen.add(identity(item)));
        writeSeen(seen);
        // On first visit, surface a small set of genuinely recent indexed items.
        // Older archive records stay in the panel but are not presented as new.
        const cutoff=Date.now()-7*24*60*60*1000;
        const recent=sorted.filter(item=>{
          if(item.archive===true || /archive|historical|annual results old/i.test(String(item.title||""))) return false;
          if(!isPib(item) && !isExamPriority(item)) return false;
          const stamp=new Date(item.detected_at||item.published||item.date||0).getTime();
          return Number.isFinite(stamp)&&stamp>=cutoff;
        }).slice(0,5);
        recent.slice().reverse().forEach(toast);
        if(recent.length){
          unread=recent.length;
          updateBadge();
          status.textContent="Latest "+recent.length+" recent update"+(recent.length===1?"":"s")+" shown · "+new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"});
        }
        initialized=true;
      } else {
        const fresh=[];
        for(const item of sorted) {
          const id=identity(item);
          if(item.archive===true || isNoise(item)) continue;
          if(!seen.has(id))fresh.push(item);
        }
        fresh.slice(0,5).reverse().forEach(toast);
        fresh.forEach(item=>seen.add(identity(item)));
        if(fresh.length) {
          unread+=fresh.length;
          updateBadge();
          status.textContent=fresh.length+" new update"+(fresh.length===1?"":"s")+" detected · "+new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"});
          if("Notification" in window && Notification.permission==="granted") {
            fresh.slice(0,3).forEach(item=>{
              try {
                const n=new Notification("GoResultHub: "+categoryName(item.category),{body:item.title||"A new official exam update was detected.",icon:"favicon.ico"});
                n.onclick=()=>{window.focus();const url="https://goresulthub.com/notice.html?id="+encodeURIComponent(item.id||"")+"&q="+encodeURIComponent(item.title||item.exam||"");window.open(url,"_blank","noopener");n.close();};
              } catch (_) {}
            });
          }
          writeSeen(seen);
        }
      }
    } catch (_) {
      status.textContent="Could not refresh the updates feed. It will retry automatically.";
    } finally { busy=false; }
  }
  bell.addEventListener("click",()=>{
    // The floating button doubles as a "dismiss all" control whenever
    // the panel or toast popups are visible. Never reveal another toast
    // as a side effect of dismissing the current notifications.
    const hasVisibleNotifications=!panel.hidden||stack.children.length>0;
    if(hasVisibleNotifications){
      panel.hidden=true;
      stack.replaceChildren();
      bell.setAttribute("aria-expanded","false");
      unread=0;
      updateBadge();
      return;
    }
    panel.hidden=false;
    bell.setAttribute("aria-expanded","true");
    unread=0;
    updateBadge();
    renderPanel(allItems);
  });
  $(".grh-enable-notifications").addEventListener("click",async()=>{
    const button=$(".grh-enable-notifications");
    button.disabled=true;
    try{
      const message=await window.GoResultHubLiveAlerts.requestPermission();
      status.textContent=message;
      button.textContent=("Notification" in window && Notification.permission==="granted")?"Alerts enabled":"Enable alerts";
    }catch(error){status.textContent="Could not enable browser alerts. Check your browser permissions.";}
    finally{button.disabled=false;}
  });
  $(".grh-close").addEventListener("click",()=>{panel.hidden=true;bell.setAttribute("aria-expanded","false");});
  document.addEventListener("click",(event)=>{
    if(!ui.contains(event.target)){panel.hidden=true;bell.setAttribute("aria-expanded","false");}
  });
  document.addEventListener("visibilitychange",()=>{if(!document.hidden)poll();});
  poll();
  window.setInterval(poll,POLL_MS);
  window.GoResultHubLiveAlerts={
    requestPermission: async () => {
      if(!("Notification" in window)) return "This browser does not support desktop notifications.";
      if(Notification.permission==="granted") return "Desktop notifications are already enabled.";
      if(Notification.permission==="denied") return "Notifications are blocked in your browser settings.";
      const result=await Notification.requestPermission();
      return result==="granted"?"Desktop notifications enabled.":"Desktop notifications were not enabled.";
    }
  };
})();