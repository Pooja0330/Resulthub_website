/* GoResultHub privacy-friendly cookie preferences.
 * Essential functionality is always enabled. Optional advertising is loaded only after opt-in.
 * This static site does not currently load analytics tools.
 */
(() => {
  "use strict";
  const KEY = "grh_cookie_preferences";
  const COOKIE = "grh_cookie_consent";
  const $ = (selector) => document.querySelector(selector);
  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  function readCookie() {
    try {
      const match = document.cookie.match(new RegExp("(?:^|; )" + COOKIE + "=([^;]*)"));
      return match ? JSON.parse(decodeURIComponent(match[1])) : null;
    } catch (_) { return null; }
  }
  function readPrefs() {
    try {
      const value = readCookie() || JSON.parse(localStorage.getItem(KEY) || "null");
      if (value && value.version === 1) return { essential: true, analytics: false, ads: value.ads === true, savedAt: value.savedAt || "" };
    } catch (_) {}
    return null;
  }
  function savePrefs(prefs) {
    const value = { version: 1, essential: true, analytics: false, ads: prefs.ads === true, savedAt: new Date().toISOString() };
    const secure = location.protocol === "https:" ? "; Secure" : "";
    document.cookie = COOKIE + "=" + encodeURIComponent(JSON.stringify(value)) + "; Max-Age=31536000; Path=/; SameSite=Lax" + secure;
    try { localStorage.setItem(KEY, JSON.stringify(value)); } catch (_) {}
    window.GRH_COOKIE_PREFERENCES = value;
    window.dispatchEvent(new CustomEvent("grh:cookie-preferences-changed", { detail: value }));
    hideBanner();
  }
  const wrap = document.createElement("div");
  wrap.id = "grh-cookie-consent";
  wrap.innerHTML = '<section class="grh-cookie-banner" role="dialog" aria-modal="false" aria-labelledby="grh-cookie-title" hidden><div class="grh-cookie-copy"><strong id="grh-cookie-title">Your privacy choices</strong><p>GoResultHub uses essential storage to keep the website working and remember your preferences. Optional advertising cookies are off unless you allow them. <a href="privacy.html">Privacy policy</a>.</p><div class="grh-cookie-options" hidden><label><input type="checkbox" checked disabled> Essential storage (always on)</label><label><input type="checkbox" id="grh-cookie-ads"> Allow advertising cookies and related technologies</label><p class="grh-cookie-note">We do not currently run analytics. You can change this choice at any time.</p></div></div><div class="grh-cookie-actions"><button type="button" class="grh-cookie-reject">Reject optional</button><button type="button" class="grh-cookie-settings">Settings</button><button type="button" class="grh-cookie-save" hidden>Save choices</button><button type="button" class="grh-cookie-accept">Accept all</button></div></section><button type="button" class="grh-cookie-manage" aria-label="Open cookie settings">Cookie settings</button>';
  document.body.appendChild(wrap);
  const banner = $(".grh-cookie-banner"), options = $(".grh-cookie-options"), ads = $("#grh-cookie-ads"), settings = $(".grh-cookie-settings"), save = $(".grh-cookie-save"), accept = $(".grh-cookie-accept");
  function hideBanner() { banner.hidden = true; options.hidden = true; settings.hidden = false; save.hidden = true; accept.hidden = false; }
  function showBanner(edit) {
    const prefs = readPrefs();
    ads.checked = !!(prefs && prefs.ads);
    banner.hidden = false;
    options.hidden = !edit;
    settings.hidden = !!edit;
    save.hidden = !edit;
    accept.hidden = !!edit;
  }
  window.GRH_COOKIE_PREFERENCES = readPrefs();
  $(".grh-cookie-manage").addEventListener("click", () => showBanner(true));
  settings.addEventListener("click", () => showBanner(true));
  $(".grh-cookie-reject").addEventListener("click", () => savePrefs({ ads: false }));
  accept.addEventListener("click", () => savePrefs({ ads: true }));
  save.addEventListener("click", () => savePrefs({ ads: ads.checked }));
  if (!readPrefs()) showBanner(false);
})();
