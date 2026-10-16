/* GoResultHub monetization settings.
 * Add only real IDs after ad-network approval. Optional ads load only after visitor consent.
 */
window.GRH_MONETIZATION = window.GRH_MONETIZATION || {
  adsenseClient: "",
  adSlots: { homeTop: "", homeMid: "", homeBottom: "", stateTop: "", stateBottom: "" },
  sponsoredResources: []
};
(function () {
  "use strict";
  const config = window.GRH_MONETIZATION || {};
  const client = String(config.adsenseClient || "").trim();
  const slots = config.adSlots || {};
  let adsStarted = false;
  function initializeAds() {
    const prefs = window.GRH_COOKIE_PREFERENCES;
    if (!prefs || prefs.ads !== true || adsStarted) return;
    const adClientIsValid = /^ca-pub-\d{8,24}$/.test(client);
    const activeSlots = Array.from(document.querySelectorAll("[data-ad-slot]")).filter(wrapper => {
      const slotId = String(slots[wrapper.dataset.adSlot] || "").trim();
      return adClientIsValid && /^\d{5,20}$/.test(slotId) && wrapper.dataset.adInitialized !== "true";
    });
    if (!activeSlots.length) return;
    adsStarted = true;
    const existing = document.querySelector('script[data-grh-adsense="true"]');
    const renderSlots = () => activeSlots.forEach(wrapper => {
      if (wrapper.dataset.adInitialized === "true") return;
      const ins = document.createElement("ins");
      ins.className = "adsbygoogle";
      ins.style.display = "block";
      ins.dataset.adClient = client;
      ins.dataset.adSlot = String(slots[wrapper.dataset.adSlot]).trim();
      ins.dataset.adFormat = "auto";
      ins.dataset.fullWidthResponsive = "true";
      wrapper.replaceChildren(ins);
      wrapper.hidden = false;
      wrapper.dataset.adInitialized = "true";
      try { (window.adsbygoogle = window.adsbygoogle || []).push({}); }
      catch (error) { console.warn("Ad unit could not be initialized.", error); }
    });
    if (existing && window.adsbygoogle) { renderSlots(); return; }
    const script = document.createElement("script");
    script.dataset.grhAdsense = "true";
    script.async = true;
    script.crossOrigin = "anonymous";
    script.src = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=" + encodeURIComponent(client);
    script.onload = renderSlots;
    script.onerror = () => { adsStarted = false; console.warn("Ad provider script did not load."); };
    document.head.appendChild(script);
  }
  window.addEventListener("grh:cookie-preferences-changed", initializeAds);
  initializeAds();

  const partnerSection = document.querySelector("#partnerResources");
  const partnerList = document.querySelector("[data-sponsored-list]");
  const resources = Array.isArray(config.sponsoredResources) ? config.sponsoredResources : [];
  const safeResources = resources.filter(item => {
    try { const url = new URL(String(item.url || "")); return (url.protocol === "https:" || url.protocol === "http:") && String(item.title || "").trim() && String(item.description || "").trim(); }
    catch (_) { return false; }
  }).slice(0, 6);
  if (partnerSection && partnerList && safeResources.length) {
    partnerList.innerHTML = safeResources.map(item => {
      const title = escapeHtml(item.title), description = escapeHtml(item.description), url = escapeHtml(item.url);
      const label = String(item.type || "Sponsored").toLowerCase() === "affiliate" ? "Affiliate link" : "Sponsored";
      return '<article class="sponsor-card"><span class="sponsor-label">' + label + '</span><h3>' + title + '</h3><p>' + description + '</p><a href="' + url + '" target="_blank" rel="sponsored noopener noreferrer">View resource ↗</a></article>';
    }).join("");
    partnerSection.hidden = false;
  }
  function escapeHtml(value) { return String(value).replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char])); }
})();
