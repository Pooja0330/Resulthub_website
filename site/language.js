/* GoResultHub language selector: English is the source/default language.
 * Visitors may choose a translation using Google's public website translation widget.
 */
(() => {
  "use strict";
  const box = document.createElement("div");
  box.id = "grh-language-control";
  box.innerHTML = '<button type="button" class="grh-language-drag" aria-label="Move language selector" title="Drag to move">⠿</button><span class="grh-language-label">Language</span><div id="google_translate_element"></div>';
  document.body.appendChild(box);
  // Keep the selector clear of the live-updates button and let visitors reposition it.
  try {
    const saved = JSON.parse(localStorage.getItem("grh_language_position") || "null");
    if (saved && Number.isFinite(saved.left) && Number.isFinite(saved.top)) {
      box.style.left = Math.max(4, Math.min(saved.left, window.innerWidth - 180)) + "px";
      box.style.top = Math.max(4, Math.min(saved.top, window.innerHeight - 60)) + "px";
      box.style.right = "auto"; box.style.bottom = "auto";
    }
  } catch (_) {}
  const dragHandle = box.querySelector(".grh-language-drag");
  let drag = null;
  dragHandle.addEventListener("pointerdown", event => {
    if (event.button !== 0 && event.pointerType === "mouse") return;
    const rect = box.getBoundingClientRect();
    drag = {x:event.clientX, y:event.clientY, left:rect.left, top:rect.top};
    dragHandle.setPointerCapture(event.pointerId);
    event.preventDefault();
  });
  dragHandle.addEventListener("pointermove", event => {
    if (!drag) return;
    const left = Math.max(4, Math.min(window.innerWidth - box.offsetWidth - 4, drag.left + event.clientX - drag.x));
    const top = Math.max(4, Math.min(window.innerHeight - box.offsetHeight - 4, drag.top + event.clientY - drag.y));
    box.style.left = left + "px"; box.style.top = top + "px";
    box.style.right = "auto"; box.style.bottom = "auto";
  });
  const finishDrag = () => {
    if (!drag) return;
    drag = null;
    try { const rect=box.getBoundingClientRect(); localStorage.setItem("grh_language_position",JSON.stringify({left:rect.left,top:rect.top})); } catch (_) {}
  };
  dragHandle.addEventListener("pointerup", finishDrag);
  dragHandle.addEventListener("pointercancel", finishDrag);
  window.addEventListener("resize", () => {
    const rect=box.getBoundingClientRect();
    box.style.left=Math.max(4,Math.min(rect.left,window.innerWidth-box.offsetWidth-4))+"px";
    box.style.top=Math.max(4,Math.min(rect.top,window.innerHeight-box.offsetHeight-4))+"px";
    box.style.right="auto";box.style.bottom="auto";
  });
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
