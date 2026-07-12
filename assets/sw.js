/* TUWAYKIAPP Service Worker v3
 *
 * Strategy:
 *  - HTML pages      : network-first, fallback to offline page
 *  - /_next/static/* : cache-first    (content-hashed — safe to cache indefinitely)
 *  - /api/*          : bypass SW      (always network)
 *  - Icons + offline : pre-cached at install
 *
 * Cache version MUST be bumped on any change to this file so
 * the activate handler deletes the previous cache from all clients.
 */
const CACHE = "twk-v3";
const OFFLINE_KEY = "/_offline";
const PRECACHE = [
  "/icon-192.png",
  "/icon-512.png",
];

const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sin conexión — TUWAYKIAPP</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
background:#f8fafc;color:#1e293b;display:flex;align-items:center;
justify-content:center;min-height:100vh;padding:24px;text-align:center}
.card{max-width:420px;width:100%;background:#fff;border-radius:16px;
box-shadow:0 4px 24px rgba(0,0,0,.08);padding:40px 32px}
.icon{width:64px;height:64px;margin:0 auto 20px;border-radius:14px}
h1{font-size:20px;font-weight:700;margin-bottom:8px;color:#0f172a}
.desc{font-size:15px;color:#64748b;line-height:1.6;margin-bottom:24px}
.status{display:flex;align-items:center;justify-content:center;gap:8px;
font-size:14px;color:#94a3b8;margin-bottom:20px}
.dot{width:10px;height:10px;border-radius:50%;background:#f59e0b;
animation:pulse 1.5s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:.4;transform:scale(.9)}50%{opacity:1;transform:scale(1.1)}}
.btn{display:inline-flex;align-items:center;gap:8px;padding:10px 24px;
background:#4f46e5;color:#fff;border:none;border-radius:10px;
font-size:14px;font-weight:600;cursor:pointer;transition:background .15s}
.btn:hover{background:#4338ca}
.btn:active{transform:scale(.97)}
.btn svg{width:16px;height:16px}
.timer{font-size:13px;color:#94a3b8;margin-top:16px}
.online .dot{background:#22c55e;animation:none}
.online .status-text{color:#22c55e;font-weight:600}
</style>
</head>
<body>
<div class="card">
<img src="/icon-192.png" alt="TUWAYKIAPP" class="icon" width="64" height="64">
<h1>Sin conexión a internet</h1>
<p class="desc">No se pudo conectar al servidor. Verifica tu conexión a internet o espera unos segundos, vamos a reintentar automáticamente.</p>
<div class="status" id="status">
<span class="dot" id="dot"></span>
<span class="status-text" id="statusText">Esperando conexión…</span>
</div>
<button class="btn" id="retryBtn" onclick="tryReconnect()">
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
Reintentar ahora
</button>
<p class="timer" id="timer"></p>
</div>
<script>
var countdown=10,interval=null,checking=false;
function tryReconnect(){
if(checking)return;checking=true;
document.getElementById("statusText").textContent="Verificando conexión…";
fetch("/api/ping",{cache:"no-store",mode:"same-origin"}).then(function(r){
if(r.ok){document.getElementById("status").className="status online";
document.getElementById("statusText").textContent="Conexión restablecida";
clearInterval(interval);document.getElementById("timer").textContent="Recargando…";
setTimeout(function(){window.location.reload()},600)}else{fail()}
}).catch(fail)}
function fail(){checking=false;
document.getElementById("statusText").textContent="Esperando conexión…";
countdown=Math.min(countdown+5,30);startTimer()}
function startTimer(){var secs=countdown;clearInterval(interval);
document.getElementById("timer").textContent="Reintento automático en "+secs+"s";
interval=setInterval(function(){secs--;
if(secs<=0){clearInterval(interval);tryReconnect();return}
document.getElementById("timer").textContent="Reintento automático en "+secs+"s"},1000)}
window.addEventListener("online",function(){tryReconnect()});
startTimer();
</script>
</body>
</html>`;

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => {
      c.put(OFFLINE_KEY, new Response(OFFLINE_HTML, {
        headers: { "Content-Type": "text/html; charset=utf-8" },
      }));
      return c.addAll(PRECACHE);
    })
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
  // Falls back to cache → offline page when the network is unavailable.
  e.respondWith(
    fetch(e.request).catch(() =>
      caches.match(e.request).then((cached) => {
        if (cached) return cached;
        if (e.request.destination === "document") {
          return caches.match(OFFLINE_KEY);
        }
      })
    )
  );
});
