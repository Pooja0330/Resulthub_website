/* GoResultHub language selector: English is the source/default language.
 * Visitors may choose a translation using Google's public website translation widget.
 */
(() => {
  "use strict";
  const box = document.createElement("div");
  box.id = "grh-language-control";
  box.innerHTML = '<span class="grh-language-label">Language</span><div id="google_translate_element"></div>';
  document.body.appendChild(box);
  window.googleTranslateElementInit = function () {
    if (!window.google || !google.translate || !google.translate.TranslateElement) return;
    new google.translate.TranslateElement({
      pageLanguage: "en",
      includedLanguages: "en,hi,bn,ta,te,mr,gu,pa,or,as,ur,kn,ml,es,fr,de,ar,zh-CN,ja,ko,pt,ru",
      autoDisplay: false,
      layout: google.translate.TranslateElement.InlineLayout.SIMPLE
    }, "google_translate_element");
  };
  const script = document.createElement("script");
  script.src = "https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit";
  script.async = true;
  script.onerror = () => {
    const note = document.createElement("span");
    note.className = "grh-language-fallback";
    note.textContent = "Translation is temporarily unavailable.";
    box.appendChild(note);
  };
  document.head.appendChild(script);
})();
