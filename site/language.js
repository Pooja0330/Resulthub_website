/* GoResultHub: English is the required display language.
 * Google Translate is constrained to English; original official links remain unchanged.
 */
(() => {
  "use strict";
  document.documentElement.lang = "en";
  document.documentElement.setAttribute("translate", "yes");

  // Ask Google's website translation widget to use automatic source detection
  // and English as the only target language.
  try {
    const cookie = "googtrans=/auto/en; path=/; max-age=31536000; SameSite=Lax";
    document.cookie = cookie;
    if (location.hostname) document.cookie = "googtrans=/auto/en; domain=" + location.hostname + "; path=/; max-age=31536000; SameSite=Lax";
  } catch (_) {}

  const box = document.createElement("div");
  box.id = "grh-language-control";
  box.setAttribute("aria-label", "Website language");
  box.innerHTML = '<span class="grh-language-label">Page language: English</span><div id="google_translate_element"></div>';
  document.body.appendChild(box);

  window.googleTranslateElementInit = function () {
    if (!window.google || !google.translate || !google.translate.TranslateElement) return;
    new google.translate.TranslateElement({
      pageLanguage: "auto",
      includedLanguages: "en",
      autoDisplay: true,
      layout: google.translate.TranslateElement.InlineLayout.SIMPLE
    }, "google_translate_element");
  };

  const script = document.createElement("script");
  script.src = "https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit";
  script.async = true;
  script.onerror = () => {
    const note = document.createElement("span");
    note.className = "grh-language-fallback";
    note.textContent = "English is the website's default language.";
    box.appendChild(note);
  };
  document.head.appendChild(script);
})();
