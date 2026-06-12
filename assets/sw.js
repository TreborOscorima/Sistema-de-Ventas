/* TUWAYKIAPP Service Worker v2
 *
 * Strategy:
 *  - HTML pages      : network-first  (always fresh after each deploy)
 *  - /_next/static/* : cache-first    (content-hashed — safe to cache indefinitely)
 *  - /api/*          : bypass SW      (always network)
 *  - Icons           : pre-cached at install
 *
 * Cache version MUST be bumped on any change to this file so
 * the activate handler deletes the previous cache from all clients.
 */
const CACHE = "twk-v2";
const PRECACHE = [
  "/icon-192.png",
  "/icon-512.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;

  const url = new URL(e.request.url);

  // API and WebSocket upgrade: bypass SW entirely.
  if (url.pathname.startsWith("/api/")) return;

  // Next.js content-hashed static assets: cache-first + populate cache on miss.
  // Safe because every filename contains a build-specific hash.
  if (url.pathname.startsWith("/_next/static/")) {
    e.respondWith(
      caches.match(e.request).then((cached) => {
        if (cached) return cached;
        return fetch(e.request).then((res) => {
          const clone = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, clone));
          return res;
        });
      })
    );
    return;
  }

  // HTML pages and everything else: network-first.
  // Falls back to cache only when the network is unavailable (offline).
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
