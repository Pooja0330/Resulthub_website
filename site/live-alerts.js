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
  const identity = (item) => String(item.id || item.url || item.official_url || [item.title,item.source_id,item.published].join("|"));
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
    const current = items.slice(0, 12);
    list.innerHTML = current.length ? current.map(item => {
      const url="https://goresulthub.com/?q="+encodeURIComponent(item.title || item.exam || "");
      const date=item.published || item.detected_at || "";
      return '<article class="grh-alert-item"><span class="grh-alert-type">'+esc(categoryName(item.category))+'</span><strong>'+esc(item.title || item.exam || "Official exam update")+'</strong><small>'+esc(item.source_name || item.authority || "Official source")+(date?' · '+esc(date):'')+'</small>'+(url?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">View on GoResultHub ↗</a>':'<span class="grh-no-link">Official link not available in feed</span>')+'</article>';
    }).join("") : '<p class="grh-alert-empty">No updates have been indexed yet. Keep this page open; the panel checks the published feed periodically.</p>';
  }
  function toast(item) {
    const url="https://goresulthub.com/?q="+encodeURIComponent(item.title || item.exam || "");
    const node=document.createElement("article");
    node.className="grh-toast";
    node.innerHTML='<div class="grh-toast-top"><span>NEW OFFICIAL UPDATE</span><button type="button" aria-label="Dismiss">×</button></div><strong>'+esc(item.title || item.exam || "New exam update")+'</strong><small>'+esc(item.source_name || item.authority || "Official source")+' · '+esc(categoryName(item.category))+'</small>'+(url?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">View update ↗</a>':'');
    node.querySelector("button").addEventListener("click",()=>node.remove());
    stack.prepend(node);
    while(stack.children.length>3)stack.lastElementChild.remove();
  }
  async function poll() {
    if (busy) return;
    busy = true;
    try {
      const response=await fetch(FEED_URL+"?live_check="+Date.now(),{cache:"no-store"});
      if(!response.ok)throw new Error("Feed request failed ("+response.status+")");
      const data=await response.json();
      if(!Array.isArray(data))throw new Error("Feed format was not recognised");
      const sorted=data.slice().sort((a,b)=>String(b.detected_at||b.published||"").localeCompare(String(a.detected_at||a.published||"")));
      allItems.splice(0,allItems.length,...sorted);
      renderPanel(allItems);
      status.textContent=data.length+" indexed updates · last checked "+new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"});
      if(!initialized) {
        data.forEach(item=>seen.add(identity(item)));
        writeSeen(seen);
        initialized=true;
      } else {
        const fresh=[];
        for(const item of sorted) {
          const id=identity(item);
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
                n.onclick=()=>{window.focus();const url="https://goresulthub.com/?q="+encodeURIComponent(item.title||item.exam||"");window.open(url,"_blank","noopener");n.close();};
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
    const opening=panel.hidden;
    panel.hidden=!opening;
    bell.setAttribute("aria-expanded",String(opening));
    if(opening){unread=0;updateBadge();renderPanel(allItems);}
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