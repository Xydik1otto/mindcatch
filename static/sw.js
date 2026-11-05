// Mindcatch service worker: offline-first shell.
// - precached app shell (install)
// - navigations: network-first, offline fallback to the cached shell
// - static assets: cache-first, refreshed in the background (stale-while-revalidate)
// - /api/*: never cached (live data only)

const CACHE = "mindcatch-v3";
const SHELL = ["/", "/index.html", "/app.js", "/manifest.json", "/favicon.svg"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/")) return; // live data only

  // Page loads: try the network first so updates land, fall back to the shell.
  if (e.request.mode === "navigate") {
    e.respondWith(
      fetch(e.request).then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => { c.put("/", copy); c.put("/index.html", copy); });
        return res;
      }).catch(() => caches.match("/").then(hit => hit || caches.match("/index.html")))
    );
    return;
  }

  // Static assets: cache-first + background refresh.
  e.respondWith(
    caches.match(e.request).then(hit => {
      const refresh = fetch(e.request).then(res => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, copy));
        }
        return res;
      }).catch(() => hit);
      return hit || refresh;
    })
  );
});
