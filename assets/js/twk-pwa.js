/**
 * TUWAYKIAPP PWA Install Banner
 * Posición: top-right. Captura beforeinstallprompt y persiste
 * la decisión del usuario en localStorage por 30 días.
 */
(function () {
  "use strict";

  var DISMISS_KEY  = "twk_pwa_dismissed";
  var DISMISS_DAYS = 30;

  function wasDismissedRecently() {
    var ts = localStorage.getItem(DISMISS_KEY);
    if (!ts) return false;
    return Date.now() - parseInt(ts, 10) < DISMISS_DAYS * 86400 * 1000;
  }

  function injectKeyframes() {
    if (document.getElementById("twk-pwa-kf")) return;
    var s = document.createElement("style");
    s.id = "twk-pwa-kf";
    s.textContent =
      "@keyframes twkSlideIn{from{opacity:0;transform:translateX(24px)}to{opacity:1;transform:translateX(0)}}" +
      "#twk-pwa-banner button:hover{opacity:.85}";
    document.head.appendChild(s);
  }

  function buildBanner() {
    /* ── contenedor principal ─────────────────────────────── */
    var banner = document.createElement("div");
    banner.id = "twk-pwa-banner";
    banner.setAttribute("role", "dialog");
    banner.setAttribute("aria-label", "Instalar TUWAYKIAPP");
    banner.style.cssText = [
      "position:fixed",
      "top:72px",
      "right:16px",
      "z-index:99999",
      "background:#fff",
      "border-radius:16px",
      "box-shadow:0 8px 32px rgba(0,0,0,0.14),0 2px 8px rgba(0,0,0,0.08)",
      "padding:16px 18px 14px 16px",
      "display:flex",
      "flex-direction:column",
      "gap:10px",
      "width:300px",
      "border:1px solid #e2e8f0",
      "animation:twkSlideIn .3s cubic-bezier(.16,1,.3,1) both",
      "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif",
    ].join(";");

    /* ── botón cerrar (X) ─────────────────────────────────── */
    var btnClose = document.createElement("button");
    btnClose.setAttribute("aria-label", "Cerrar");
    btnClose.innerHTML = "&#x2715;";
    btnClose.style.cssText = [
      "position:absolute",
      "top:10px",
      "right:12px",
      "background:none",
      "border:none",
      "font-size:14px",
      "color:#94a3b8",
      "cursor:pointer",
      "line-height:1",
      "padding:2px 4px",
    ].join(";");
    banner.style.position = "fixed"; // asegura contexto para absolute
    banner.appendChild(btnClose);

    /* ── fila superior: ícono + título ───────────────────── */
    var header = document.createElement("div");
    header.style.cssText = "display:flex;align-items:center;gap:10px;padding-right:18px";

    var iconWrap = document.createElement("div");
    iconWrap.style.cssText =
      "flex-shrink:0;width:44px;height:44px;border-radius:11px;overflow:hidden";
    var icon = document.createElement("img");
    icon.src    = "/icon-192.png";
    icon.alt    = "TUWAYKIAPP";
    icon.width  = 44;
    icon.height = 44;
    icon.style.cssText = "width:44px;height:44px;display:block";
    iconWrap.appendChild(icon);

    var titleWrap = document.createElement("div");
    var title = document.createElement("p");
    title.textContent = "Instalar TUWAYKIAPP";
    title.style.cssText =
      "margin:0 0 2px;font-weight:700;font-size:14px;color:#0f172a;line-height:1.2";
    var subtitle = document.createElement("p");
    subtitle.textContent = "Agrega la app a tu pantalla de inicio para acceso rápido";
    subtitle.style.cssText =
      "margin:0;font-size:12px;color:#64748b;line-height:1.4";
    titleWrap.appendChild(title);
    titleWrap.appendChild(subtitle);

    header.appendChild(iconWrap);
    header.appendChild(titleWrap);

    /* ── fila de botones ─────────────────────────────────── */
    var btnRow = document.createElement("div");
    btnRow.style.cssText = "display:flex;gap:8px;justify-content:flex-end";

    var btnDismiss = document.createElement("button");
    btnDismiss.textContent = "Ahora no";
    btnDismiss.style.cssText = [
      "padding:7px 14px",
      "background:transparent",
      "color:#64748b",
      "border:1px solid #e2e8f0",
      "border-radius:8px",
      "font-size:13px",
      "font-weight:500",
      "cursor:pointer",
      "white-space:nowrap",
    ].join(";");

    var btnInstall = document.createElement("button");
    btnInstall.style.cssText = [
      "padding:7px 16px",
      "background:#4f46e5",
      "color:#fff",
      "border:none",
      "border-radius:8px",
      "font-size:13px",
      "font-weight:600",
      "cursor:pointer",
      "white-space:nowrap",
      "display:flex",
      "align-items:center",
      "gap:6px",
    ].join(";");
    // ícono de descarga inline SVG
    btnInstall.innerHTML =
      '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
      "Instalar";

    btnRow.appendChild(btnDismiss);
    btnRow.appendChild(btnInstall);

    /* ── ensamblado ──────────────────────────────────────── */
    banner.appendChild(header);
    banner.appendChild(btnRow);

    return { banner: banner, btnInstall: btnInstall, btnDismiss: btnDismiss, btnClose: btnClose };
  }

  var deferredPrompt = null;

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;

    if (wasDismissedRecently()) return;

    injectKeyframes();
    var ui = buildBanner();
    document.body.appendChild(ui.banner);

    function dismiss() {
      ui.banner.remove();
      localStorage.setItem(DISMISS_KEY, String(Date.now()));
    }

    ui.btnInstall.addEventListener("click", function () {
      ui.banner.remove();
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then(function (result) {
        if (result.outcome === "accepted") {
          localStorage.setItem(DISMISS_KEY, String(Date.now()));
        }
        deferredPrompt = null;
      });
    });

    ui.btnDismiss.addEventListener("click", dismiss);
    ui.btnClose.addEventListener("click", dismiss);
  });

  /* Registrar Service Worker */
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function (err) {
        console.warn("[TWK-PWA] SW registration failed:", err);
      });
    });
  }
})();
