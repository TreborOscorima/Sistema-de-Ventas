/* TUWAYKIAPP Service Worker — cache-first para assets estáticos */
const CACHE = "twk-v1";
const STATIC = [
  "/",
  "/manifest.json",
  "/icon-192.png",
  "/icon-512.png",
  "/css/twk-app.css",
  "/css/accessibility.css",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(STATIC))
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
  /* Solo interceptamos GET; las llamadas a /api/ siempre van a la red */
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.pathname.startsWith("/api/")) return;

  e.respondWith(
    caches.match(e.request).then(
      (cached) => cached || fetch(e.request)
    )
  );
});
