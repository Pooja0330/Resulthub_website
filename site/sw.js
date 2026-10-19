const CACHE_NAME = "goresult-hub-v16";
const DATA_PATHS = ["data/results.json", "data/status.json", "data/pib-news.json"];
self.addEventListener("install", event => { self.skipWaiting(); });
self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key.startsWith("goresult-hub-") && key !== CACHE_NAME).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});
self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  const scopePath = new URL(self.registration.scope).pathname;
  if (!url.pathname.startsWith(scopePath)) return;

  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    const dataPath = DATA_PATHS.find(path => url.pathname.endsWith(path));
    if (dataPath) {
      // Always request the current feed from the network; use a stable cache key
      // only as an outage fallback so timestamp query strings do not fragment the cache.
      const fallbackKey = new Request(new URL(dataPath, self.registration.scope).toString());
      try {
        const freshRequest = new Request(request, { cache: "no-store" });
        const response = await fetch(freshRequest);
        if (response.ok) await cache.put(fallbackKey, response.clone());
        return response;
      } catch (error) {
        const cached = await cache.match(fallbackKey);
        if (cached) return cached;
        throw error;
      }
    }

    // Network-first for HTML/JS/CSS so visitors receive fixes promptly.
    try {
      const response = await fetch(request);
      if (response.ok) await cache.put(request, response.clone());
      return response;
    } catch (error) {
      const cached = await cache.match(request);
      if (cached) return cached;
      throw error;
    }
  })());
});
