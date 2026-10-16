(() => {
  "use strict";
  const FEED = "data/results.json";
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const safe = value => { try { const u = new URL(value, location.href); return u.protocol === "https:" ? u.href : ""; } catch (_) { return ""; } };
  const detail = item => "notice.html?id=" + encodeURIComponent(item.id || "") + "&q=" + encodeURIComponent(item.title || item.exam || "Exam update");
  const stamp = item => new Date(item.detected_at || item.published || item.date || 0).getTime() || 0;
  const sorted = items => items.filter(x => !x.archive).slice().sort((a,b) => stamp(b)-stamp(a));
  const stateName = () => new URLSearchParams(location.search).get("state") || "";
  const stateFor = item => {
    const raw = String(item.state || item.region || "").trim();
    if (raw && raw !== "Central" && raw !== "All India") return raw;
    const hay = [item.source_id,item.source_name,item.title,item.exam,item.url,item.source_url].join(" ").toLowerCase();
    const patterns = [
      ["Andhra Pradesh",/andhra pradesh|psc\.ap\.gov|bse\.ap\.gov|slprb\.ap/],["Arunachal Pradesh",/arunachal|appsc\.gov/],
      ["Assam",/assam|apsc\.nic|sebaonline/],["Bihar",/bihar|bpsc|biharboard|csbc\.bihar/],["Chhattisgarh",/chhattisgarh|cgbse|cgstate\.gov/],
      ["Goa",/goa|gbshse/],["Gujarat",/gujarat|gseb|gpsc\.gujarat|ojas\.gujarat/],["Haryana",/haryana|hpsc|hssc|bseh/],
      ["Himachal Pradesh",/himachal|hprca|hpbose/],["Jharkhand",/jharkhand|jpsc/],["Karnataka",/karnataka|kseab|kpsc\.kar/],
      ["Kerala",/kerala|keralapsc|pareekshabhavan/],["Madhya Pradesh",/madhya pradesh|mpbse|mppsc|esb\.mp/],
      ["Maharashtra",/maharashtra|mahahsscboard|mahresult|mpsc\.gov\.in|cetcell\.mahacet/],["Manipur",/manipur|mpscmanipur|manipuruniv/],
      ["Meghalaya",/meghalaya|mpsc\.meghalaya|mbose|nehu/],["Mizoram",/mizoram|mpsc\.mizoram|mbse\.edu/],["Nagaland",/nagaland|npsc\.nagaland|nbsenl/],
      ["Odisha",/odisha|opsc|ossc|osssc|bseodisha|results\.odisha/],["Punjab",/punjab|ppsc\.gov|pseb|sssb\.punjab/],
      ["Rajasthan",/rajasthan|rpsc|rssb|rajeduboard/],["Sikkim",/sikkim|spsc\.sikkim|cus\.ac/],["Tamil Nadu",/tamil nadu|tnpsc|dge\.tn|trb\.tn|tnusrb/],
      ["Telangana",/telangana|tspsc|tgprb|bse\.telangana|cgg\.gov/],["Tripura",/tripura|tpsc|tbse/],["Uttar Pradesh",/uttar pradesh|upmsp|uppsc|upsssc|uppbpb/],
      ["Uttarakhand",/uttarakhand|psc\.uk\.gov|ubse/],["West Bengal",/west bengal|wbpsc|wbbse|prb\.wb/],["Delhi",/delhi|dsssb|delhi\.gov/],
      ["Jammu and Kashmir",/jammu and kashmir|jkbose|jkssb|jkpsc/],["Ladakh",/ladakh/],["Puducherry",/puducherry|pondicherry|py\.gov/],
      ["Andaman and Nicobar Islands",/andaman|nicobar/],["Chandigarh",/chandigarh/],["Dadra and Nagar Haveli and Daman and Diu",/dadra|daman and diu|ddd\.gov/],["Lakshadweep",/lakshadweep/]
    ];
    for (const [name, re] of patterns) if (re.test(hay)) return name;
    return "Central";
  };
  const linkFor = item => '<a class="shortcut-notice-link" href="' + esc(detail(item)) + '">' + esc(item.title || item.exam || "Official exam update") + '</a>';
  const miniList = (items, empty) => items.length ? '<ul class="shortcut-notice-list">' + items.slice(0,2).map(item => '<li>' + linkFor(item) + '<small>' + esc(item.source_name || item.authority || "Official source") + (stamp(item) ? ' · ' + esc(new Date(stamp(item)).toLocaleDateString("en-IN",{day:"numeric",month:"short"})) : '') + '</small></li>').join("") + '</ul>' : '<p class="shortcut-notice-empty">' + esc(empty) + '</p>';
  function renderHomepage(items) {
    document.querySelectorAll(".quick-exam-card").forEach(card => {
      if (card.querySelector(".shortcut-notices")) return;
      const keywords = String(card.dataset.keywords || "") + " " + (card.querySelector("h4")?.textContent || "");
      const terms = keywords.toLowerCase().split(/[^a-z0-9]+/).filter(t => t.length > 2 && !["exam","exams","result","results","notification","notifications","official","national","government","recruitment","updates","update","admit","card","cards","portal"].includes(t));
      let matches = items.filter(item => {
        const hay = [item.title,item.exam,item.source_name,item.authority,item.exam_category,item.category].join(" ").toLowerCase();
        return terms.some(term => hay.includes(term));
      });
      if (!matches.length) matches = items.filter(item => {
        const family = [item.source_id,item.source_name,item.title,item.exam].join(" ").toLowerCase();
        return (keywords.toLowerCase().includes("ssc") && /\bssc\b|staff selection commission/.test(family)) ||
          (keywords.toLowerCase().includes("upsc") && /\bupsc\b|union public service commission/.test(family)) ||
          (keywords.toLowerCase().includes("bank") && /ibps|\bsbi\b|banking|reserve bank/.test(family)) ||
          (keywords.toLowerCase().includes("jee") && /\bjee\b/.test(family)) ||
          (keywords.toLowerCase().includes("neet") && /\bneet\b/.test(family)) ||
          (keywords.toLowerCase().includes("psc") && /\bpsc\b|public service commission/.test(family));
      });
      const box = document.createElement("section");
      box.className = "shortcut-notices";
      box.innerHTML = '<h5>Latest notifications</h5>' + miniList(matches.slice(0,2), "No matching update indexed yet.");
      card.appendChild(box);
    });
  }
  function renderStatePortals(items) {
    const box = document.querySelector("#officialPortals");
    const chosen = stateName();
    if (!box || !chosen || !box.querySelector("a")) return;
    Array.from(box.querySelectorAll("a")).forEach(anchor => {
      if (anchor.closest(".state-portal-card")) return;
      const href = safe(anchor.href);
      const label = anchor.textContent.replace(/[↗→]/g, "").trim();
      if (!href) return;
      const related = items.filter(item => {
        const itemState = stateFor(item);
        const sourceText = [item.source_name,item.authority,item.source_id,item.title,item.exam,item.url,item.source_url].join(" ").toLowerCase();
        const host = new URL(href).hostname.replace(/^www\./,"").split(".")[0].toLowerCase();
        const labelTerms = label.toLowerCase().split(/[^a-z0-9]+/).filter(t => t.length > 3);
        const sourceMatch = sourceText.includes(host) || labelTerms.some(t => sourceText.includes(t));
        return itemState === chosen && sourceMatch;
      }).slice(0,2);
      const card = document.createElement("article");
      card.className = "state-portal-card";
      const portalLink = anchor.cloneNode(true);
      portalLink.className = "state-portal-main-link";
      portalLink.textContent = label + " ↗";
      card.appendChild(portalLink);
      const preview = document.createElement("div");
      preview.className = "state-portal-notices";
      preview.innerHTML = '<strong>Latest notifications</strong>' + miniList(related, "No portal-specific update indexed yet. See the latest state updates below.");
      card.appendChild(preview);
      anchor.replaceWith(card);
    });
  }
  async function init() {
    try {
      const response = await fetch(FEED + "?shortcut_notifications=" + Date.now(), {cache:"no-store"});
      if (!response.ok) throw new Error("Feed unavailable");
      const data = await response.json();
      if (!Array.isArray(data)) throw new Error("Invalid feed");
      const items = sorted(data);
      renderHomepage(items);
      renderStatePortals(items);
      const portalBox = document.querySelector("#officialPortals");
      if (portalBox) {
        const observer = new MutationObserver(() => renderStatePortals(items));
        observer.observe(portalBox, {childList:true});
      }
    } catch (error) {
      document.querySelectorAll(".quick-exam-card").forEach(card => {
        if (!card.querySelector(".shortcut-notices")) {
          const box=document.createElement("section");box.className="shortcut-notices";
          box.innerHTML="<h5>Latest notifications</h5><p class=\"shortcut-notice-empty\">Notifications are temporarily unavailable.</p>";card.appendChild(box);
        }
      });
    }
  }
  init();
})();