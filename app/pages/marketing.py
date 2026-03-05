"""Landing page publica de TUWAYKIAPP — SaaS B2B multi-sucursal."""

import os
from urllib.parse import quote

import reflex as rx

from app.constants import WHATSAPP_NUMBER

# ── Environment ──────────────────────────────────────────────
GA4_MEASUREMENT_ID = (os.getenv("GA4_MEASUREMENT_ID") or "").strip()
META_PIXEL_ID = (os.getenv("META_PIXEL_ID") or "").strip()
PUBLIC_SITE_URL = (os.getenv("PUBLIC_SITE_URL") or "").strip().rstrip("/")
PUBLIC_APP_URL = (os.getenv("PUBLIC_APP_URL") or "").strip().rstrip("/")


# ── State ────────────────────────────────────────────────────
class MarketingState(rx.State):
    """Estado reactivo para la landing page."""

    show_announcement: bool = True
    active_tab: str = "nube"

    def dismiss_announcement(self):
        self.show_announcement = False

    def set_tab_nube(self):
        self.active_tab = "nube"

    def set_tab_local(self):
        self.active_tab = "local"


# ── Helpers ──────────────────────────────────────────────────
def _site_href(path: str = "/") -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    if PUBLIC_SITE_URL:
        return f"{PUBLIC_SITE_URL}{normalized}"
    return normalized


def _app_href(path: str = "/") -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    if PUBLIC_APP_URL:
        return f"{PUBLIC_APP_URL}{normalized}"
    return normalized


def _wa_link(message: str) -> str:
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(message)}"


# ── Analytics ────────────────────────────────────────────────
def _analytics_bootstrap_script() -> str:
    ga4_id = GA4_MEASUREMENT_ID.replace("'", "\\'")
    pixel_id = META_PIXEL_ID.replace("'", "\\'")
    return (
        "(function(){"
        f"var ga4Id='{ga4_id}';"
        f"var metaPixelId='{pixel_id}';"
        # --- Expose a reusable loader so the consent button can call it ---
        "window.__twLoadAnalytics=window.__twLoadAnalytics||function(){"
        "if(ga4Id){"
        "window.dataLayer=window.dataLayer||[];"
        "window.gtag=window.gtag||function(){window.dataLayer.push(arguments);};"
        "if(!window.__twGa4Loaded){"
        "var gs=document.createElement('script');gs.async=true;gs.src='https://www.googletagmanager.com/gtag/js?id='+ga4Id;document.head.appendChild(gs);"
        "window.gtag('js',new Date());"
        "window.gtag('config',ga4Id,{send_page_view:false});"
        "window.__twGa4Loaded=true;"
        "}"
        "}"
        "if(metaPixelId && !window.__twMetaLoaded){"
        "!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?"
        "n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;"
        "n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;"
        "t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}"
        "(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');"
        "window.fbq('init',metaPixelId);"
        "window.__twMetaLoaded=true;"
        "}"
        "};"
        # --- tuwayTrack always available (local fallback even without consent) ---
        "window.tuwayTrack=window.tuwayTrack||function(name,payload){"
        "payload=payload||{};"
        "var data=Object.assign({event:name,page:window.location.pathname,ts:new Date().toISOString()},payload);"
        "window.dataLayer=window.dataLayer||[];"
        "window.dataLayer.push(data);"
        "if(typeof window.gtag==='function'){window.gtag('event',name,data);}"
        "if(typeof window.fbq==='function'){window.fbq('trackCustom',name,data);}"
        "try{var q=JSON.parse(localStorage.getItem('tuway_events')||'[]');q.push(data);localStorage.setItem('tuway_events',JSON.stringify(q.slice(-200)));}catch(e){}"
        "};"
        # --- Auto-load analytics if user already consented previously ---
        "var consent=localStorage.getItem('tw_cookie_consent');"
        "if(consent==='all'){window.__twLoadAnalytics();}"
        # --- Track landing view (always, uses local fallback if no consent) ---
        "try{if(!sessionStorage.getItem('tw_view_landing_sent')){window.tuwayTrack('view_landing',{source:'landing'});sessionStorage.setItem('tw_view_landing_sent','1');}}"
        "catch(e){window.tuwayTrack('view_landing',{source:'landing'});}"
        "})();"
    )


def _cookie_consent_script() -> str:
    """JS that manages the cookie consent banner visibility and user choice."""
    return (
        "(function(){"
        "var consent=localStorage.getItem('tw_cookie_consent');"
        "if(consent){document.getElementById('tw-cookie-banner')&&(document.getElementById('tw-cookie-banner').style.display='none');return;}"
        "setTimeout(function(){"
        "var b=document.getElementById('tw-cookie-banner');"
        "if(b){b.style.display='flex';}"
        "},800);"
        "})();"
    )


def _cookie_accept_all_script() -> str:
    return (
        "localStorage.setItem('tw_cookie_consent','all');"
        "document.getElementById('tw-cookie-banner').style.display='none';"
        "if(typeof window.__twLoadAnalytics==='function'){window.__twLoadAnalytics();}"
    )


def _cookie_reject_script() -> str:
    return (
        "localStorage.setItem('tw_cookie_consent','essential');"
        "document.getElementById('tw-cookie-banner').style.display='none';"
    )


def _cookie_consent_banner() -> rx.Component:
    """Banner de consentimiento de cookies — GDPR/ePrivacy compliant."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("cookie", class_name="h-5 w-5 text-amber-600 shrink-0 mt-0.5"),
                rx.el.div(
                    rx.el.p(
                        "Utilizamos cookies esenciales para el funcionamiento del sitio. "
                        "Las cookies de analítica y marketing solo se activan con tu consentimiento. ",
                        rx.el.a(
                            "Más información",
                            href="/cookies",
                            class_name="underline text-indigo-600 hover:text-indigo-700",
                        ),
                        class_name="text-sm text-slate-700 leading-relaxed",
                    ),
                    class_name="flex-1",
                ),
                class_name="flex items-start gap-3",
            ),
            rx.el.div(
                rx.el.button(
                    "Solo esenciales",
                    on_click=rx.call_script(_cookie_reject_script()),
                    class_name="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50 cursor-pointer",
                ),
                rx.el.button(
                    "Aceptar todas",
                    on_click=rx.call_script(_cookie_accept_all_script()),
                    class_name="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 cursor-pointer",
                ),
                class_name="flex items-center gap-3 mt-3 sm:mt-0",
            ),
            class_name="mx-auto flex w-full max-w-7xl flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-4 py-4 sm:px-6",
        ),
        id="tw-cookie-banner",
        style={"display": "none"},
        class_name="fixed bottom-0 left-0 right-0 z-[100] border-t border-slate-200 bg-white/95 backdrop-blur-sm shadow-2xl",
    )


def _track_event_script(event_name: str, source: str = "") -> str:
    safe_event = (event_name or "").replace("'", "\\'")
    safe_source = (source or "").replace("'", "\\'")
    return (
        "(function(){"
        "if(typeof window.tuwayTrack!=='function'){return;}"
        f"window.tuwayTrack('{safe_event}',{{source:'{safe_source}'}});"
        "})();"
    )


# ── Reveal (minimal IntersectionObserver — sin glow, sin MutationObserver) ──
def _reveal_script() -> str:
    return (
        "setTimeout(function(){"
        "var els=document.querySelectorAll('.reveal,.reveal-stagger');"
        "if(!els.length)return;"
        "if(!window.IntersectionObserver){"
        "els.forEach(function(el){el.classList.add('in-view');});"
        "return;}"
        "var io=new IntersectionObserver(function(entries){"
        "entries.forEach(function(e){"
        "if(e.isIntersecting){e.target.classList.add('in-view');io.unobserve(e.target);}"
        "});"
        "},{threshold:0.01,rootMargin:'0px 0px 80px 0px'});"
        "els.forEach(function(el){io.observe(el);});"
        "},300);"
    )


# ── Styles (minimal) ────────────────────────────────────────
def _global_styles() -> str:
    return """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');
@keyframes tickerMove {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}
.glass-nav {
  backdrop-filter: blur(12px);
  background: rgba(255,255,255,0.88);
}
.ticker-wrap {
  overflow: hidden;
  mask-image: linear-gradient(to right, transparent, black 10%, black 90%, transparent);
}
.ticker-track {
  display: flex;
  width: max-content;
  gap: 16px;
  animation: tickerMove 30s linear infinite;
}
.faq-item .faq-chevron { transition: transform 180ms ease; }
.faq-item[open] .faq-chevron { transform: rotate(90deg); }
.tab-btn { color: #64748b; background: transparent; }
.tab-btn.active {
  color: #0f172a;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  border-radius: 8px;
}
@media (prefers-reduced-motion: no-preference) {
  .reveal {
    opacity: 0; transform: translateY(12px);
    transition: opacity 350ms ease, transform 350ms ease;
  }
  .reveal.in-view { opacity: 1; transform: none; }
  .reveal-stagger > * {
    opacity: 0; transform: translateY(8px);
    transition: opacity 300ms ease, transform 300ms ease;
  }
  .reveal-stagger.in-view > * { opacity: 1; transform: none; }
  .reveal-stagger.in-view > *:nth-child(1) { transition-delay: 30ms; }
  .reveal-stagger.in-view > *:nth-child(2) { transition-delay: 60ms; }
  .reveal-stagger.in-view > *:nth-child(3) { transition-delay: 90ms; }
  .reveal-stagger.in-view > *:nth-child(4) { transition-delay: 120ms; }
  .reveal-stagger.in-view > *:nth-child(5) { transition-delay: 150ms; }
  .reveal-stagger.in-view > *:nth-child(6) { transition-delay: 180ms; }
}
/* Fallback: make visible after 2.5s if JS fails */
@keyframes revealFallback { to { opacity: 1; transform: none; } }
.reveal:not(.in-view) { animation: revealFallback 0s 2.5s forwards; }
.reveal-stagger:not(.in-view) > * { animation: revealFallback 0s 2.5s forwards; }
"""


# ── Static Data ──────────────────────────────────────────────
TRUST_BADGES = [
    ("building-2", "Multiempresa real"),
    ("shield-check", "Permisos granulares"),
    ("wallet", "Cobros y caja unificados"),
    ("bar-chart-3", "Reportes accionables"),
]

LOGOS = [
    ("RM", "Rivera Market", "Retail multi-caja"),
    ("NS", "Nova Sports", "Reservas deportivas"),
    ("AB", "Alfa Bodega", "Inventario intensivo"),
    ("CN", "Centro Nexus", "Multi-sucursal"),
    ("SP", "ServiPlus", "Servicios y cobranzas"),
]

MODULES = [
    {
        "icon": "shopping-cart",
        "title": "Punto de venta",
        "description": "Cobra rapido, genera tickets y mantene trazabilidad por usuario.",
        "bullets": ["Efectivo, tarjeta y transferencia", "Descuento de stock automatico", "Historial por sucursal"],
    },
    {
        "icon": "package",
        "title": "Inventario inteligente",
        "description": "Stock por sucursal con alertas, movimientos auditables y Kardex.",
        "bullets": ["Categorias, unidades y valorizacion", "Stock minimo con sugerencias", "Kardex con trazabilidad"],
    },
    {
        "icon": "calendar-plus",
        "title": "Reservas y servicios",
        "description": "Agenda operativa con adelantos y cobro final unificado.",
        "bullets": ["Reservas por horario y estado", "Cobro parcial y total", "Menos huecos en agenda"],
    },
    {
        "icon": "wallet",
        "title": "Gestion de caja",
        "description": "Apertura, cierre y auditoria diaria con evidencia de movimientos.",
        "bullets": ["Arqueo y diferencias visibles", "Ingresos/egresos con motivo", "Control por turno y responsable"],
    },
    {
        "icon": "users",
        "title": "Usuarios y permisos",
        "description": "Multi-tenant con roles claros por empresa y sucursal.",
        "bullets": ["Perfiles por funcion", "Acceso por modulo", "Escala sin perder seguridad"],
    },
    {
        "icon": "pie-chart",
        "title": "Reportes ejecutivos",
        "description": "Indicadores por periodo y categoria para decidir con datos.",
        "bullets": ["Dashboards por sucursal", "Top productos y categorias", "Lectura rapida de rentabilidad"],
    },
]

STEPS = [
    ("01", "Activa tu cuenta", "Empresa, sucursal inicial y credenciales de equipo."),
    ("02", "Configura operacion", "Moneda, catalogo, permisos y reglas de trabajo."),
    ("03", "Empieza a vender", "Ventas y cobros con trazabilidad automatica."),
    ("04", "Controla en tiempo real", "Caja, stock y reservas en una sola vista."),
    ("05", "Escala con datos", "Reportes para optimizar y crecer con orden."),
]

FAQ_ITEMS = [
    ("Cuanto tarda implementarlo?", "Puedes comenzar el mismo dia. El onboarding toma minutos y escalas por modulos."),
    ("Necesito tarjeta para el trial?", "No. Prueba gratis de 15 dias sin tarjeta. Valida el flujo completo antes de decidir."),
    ("Sirve para varias empresas o sucursales?", "Si. Arquitectura multi-tenant: cada empresa y sucursal opera con aislamiento total."),
    ("Puedo vender productos y servicios?", "Si. Punto de venta, reservas, adelantos, cobro final y caja en un solo sistema."),
    ("Que incluye el soporte?", "Acompanamiento funcional, resolucion de dudas y guia para adopcion ordenada."),
    ("Que pasa cuando termina el trial?", "Eliges Standard, Professional o Enterprise. Tu configuracion se mantiene intacta."),
]

STRENGTH_METRICS = [
    {"icon": "shield-check", "title": "Multi-tenant real", "detail": "Aislamiento total de datos entre empresas y sucursales. Cada negocio opera con privacidad absoluta."},
    {"icon": "database", "title": "Trazabilidad completa", "detail": "Cada movimiento de caja, venta y ajuste queda registrado con usuario, timestamp y sucursal."},
    {"icon": "git-branch", "title": "Arquitectura escalable", "detail": "Agrega sucursales, usuarios y modulos sin migrar datos ni detener operaciones."},
    {"icon": "lock", "title": "Permisos granulares", "detail": "Control de acceso por rol, modulo y sucursal. Define exactamente quien ve y hace que."},
]

# ── Shared Links ─────────────────────────────────────────────
_demo_link = _wa_link("Hola, quiero una demo en vivo de TUWAYKIAPP.")
_local_link = _wa_link("Hola, me interesa TUWAYKIAPP en modalidad Local (pago anual). Quiero coordinar precio y detalles.")
_standard_link = _wa_link("Hola, quiero el Plan Standard (USD 45/mes) de TUWAYKIAPP.")
_professional_link = _wa_link("Hola, quiero el Plan Professional (USD 75/mes) de TUWAYKIAPP.")
_enterprise_link = _wa_link("Hola, quiero el Plan Enterprise (USD 175/mes) de TUWAYKIAPP.")


# ── UI Components ────────────────────────────────────────────
def _nav_link(label: str, href: str, event_name: str = "", source: str = "") -> rx.Component:
    props = {}
    if event_name:
        props["on_click"] = rx.call_script(_track_event_script(event_name, source))
    return rx.el.a(
        label,
        href=href,
        class_name="text-sm font-semibold text-slate-600 transition-colors hover:text-slate-900",
        **props,
    )


def _metric_card(value: str, label: str, detail: str) -> rx.Component:
    return rx.el.div(
        rx.el.p(value, class_name="text-2xl font-extrabold text-slate-900 sm:text-3xl"),
        rx.el.p(label, class_name="mt-1 text-sm font-semibold text-slate-700"),
        rx.el.p(detail, class_name="mt-1 text-xs text-slate-500"),
        class_name="rounded-2xl border border-slate-200 bg-white px-5 py-5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
    )


def _trust_pill(icon: str, label: str) -> rx.Component:
    return rx.el.div(
        rx.icon(icon, class_name="h-4 w-4 text-emerald-700"),
        rx.el.span(label, class_name="text-xs font-semibold text-slate-700 sm:text-sm"),
        class_name="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 shadow-sm",
    )


def _logo_chip(mark: str, name: str, segment: str) -> rx.Component:
    return rx.el.div(
        rx.el.span(mark, class_name="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-xs font-bold text-white"),
        rx.el.div(
            rx.el.p(name, class_name="text-sm font-semibold text-slate-800"),
            rx.el.p(segment, class_name="text-xs text-slate-500"),
            class_name="leading-tight",
        ),
        class_name="inline-flex min-w-[210px] items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm",
    )


def _browser_frame(src: str, alt: str) -> rx.Component:
    """Tarjeta con barra de navegador simulada que envuelve una captura."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.span(class_name="h-2.5 w-2.5 rounded-full bg-slate-300"),
                rx.el.span(class_name="h-2.5 w-2.5 rounded-full bg-slate-300"),
                rx.el.span(class_name="h-2.5 w-2.5 rounded-full bg-slate-300"),
                class_name="flex items-center gap-1.5",
            ),
            class_name="flex items-center border-b border-slate-100 bg-slate-50/60 px-4 py-3",
        ),
        rx.el.div(
            rx.el.img(
                src=src,
                alt=alt,
                class_name="h-auto w-full object-cover",
            ),
            class_name="bg-white p-1",
        ),
        class_name="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-200/40 ring-1 ring-slate-900/5",
    )


def _hero_preview_card() -> rx.Component:
    return rx.el.aside(
        _browser_frame("/dashboard-hero-real.png?v=3", "Dashboard de TUWAYKIAPP"),
        _browser_frame("/Punto-de-Venta.png?v=1", "Punto de Venta de TUWAYKIAPP"),
        class_name="reveal flex flex-col gap-6",
    )


def _comparison_card(title: str, icon: str, points: list[str], tone: str = "negative") -> rx.Component:
    icon_bg = "bg-rose-50 text-rose-600" if tone == "negative" else "bg-emerald-50 text-emerald-700"
    border = "border-rose-100" if tone == "negative" else "border-emerald-100"
    bullet_icon = "x" if tone == "negative" else "check"
    bullet_color = "text-rose-500" if tone == "negative" else "text-emerald-600"
    rows = [
        rx.el.li(
            rx.icon(bullet_icon, class_name=f"h-4 w-4 {bullet_color} mt-0.5"),
            rx.el.span(point, class_name="text-sm text-slate-700"),
            class_name="flex items-start gap-2",
        )
        for point in points
    ]
    return rx.el.article(
        rx.el.div(rx.icon(icon, class_name="h-5 w-5"), class_name=f"inline-flex rounded-xl p-2.5 {icon_bg}"),
        rx.el.h3(title, class_name="mt-4 text-lg font-bold text-slate-900"),
        rx.el.ul(*rows, class_name="mt-4 space-y-2.5"),
        class_name=f"rounded-2xl border {border} bg-white p-7",
    )


def _module_card(icon: str, title: str, description: str, bullets: list[str]) -> rx.Component:
    rows = [
        rx.el.li(
            rx.icon("check", class_name="h-4 w-4 text-emerald-700 mt-0.5"),
            rx.el.span(item, class_name="text-sm text-slate-700"),
            class_name="flex items-start gap-2",
        )
        for item in bullets
    ]
    return rx.el.article(
        rx.el.div(rx.icon(icon, class_name="h-5 w-5 text-slate-700"), class_name="inline-flex items-center justify-center rounded-xl bg-slate-100 p-2.5"),
        rx.el.h3(title, class_name="mt-4 text-base font-bold text-slate-900"),
        rx.el.p(description, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
        rx.el.ul(*rows, class_name="mt-4 space-y-2"),
        class_name="rounded-2xl border border-slate-200 bg-white p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
    )


def _timeline_step(step: str, title: str, detail: str) -> rx.Component:
    return rx.el.article(
        rx.el.span(step, class_name="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white"),
        rx.el.div(
            rx.el.h3(title, class_name="text-base font-semibold text-slate-900"),
            rx.el.p(detail, class_name="mt-1 text-sm text-slate-600"),
            class_name="flex-1",
        ),
        class_name="flex items-start gap-4 rounded-2xl border border-slate-200 bg-white p-5",
    )


def _strength_card(icon: str, title: str, detail: str) -> rx.Component:
    return rx.el.article(
        rx.el.div(rx.icon(icon, class_name="h-6 w-6 text-slate-900"), class_name="inline-flex items-center justify-center rounded-xl bg-slate-100 p-3"),
        rx.el.h3(title, class_name="mt-4 text-base font-bold text-slate-900"),
        rx.el.p(detail, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
        class_name="rounded-2xl border border-slate-200 bg-white p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
    )


def _plan_card(
    title: str, subtitle: str, price_label: str, points: list[str],
    cta_label: str, cta_href: str, event_name: str,
    tone: str = "standard", badge_text: str = "",
) -> rx.Component:
    is_enterprise = tone == "enterprise"
    is_professional = tone == "professional"

    card_cls = "rounded-2xl border bg-white p-7 transition-all duration-200 hover:-translate-y-1 hover:shadow-md"
    t_cls = "mt-3 text-lg font-bold text-slate-900"
    s_cls = "mt-2 text-sm text-slate-600"
    p_cls = "text-sm text-slate-700"
    chk = "text-emerald-600"
    pr_cls = "mt-6 text-4xl font-extrabold tracking-tight text-slate-900"
    per_cls = "text-xs font-semibold uppercase tracking-wide text-slate-500"
    cta_cls = "mt-8 inline-flex w-full items-center justify-center rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-800"

    if is_professional:
        card_cls += " border-slate-300 ring-1 ring-slate-900/5"
    else:
        card_cls += " border-slate-200"

    if is_enterprise:
        card_cls = "rounded-2xl border border-slate-800 bg-slate-900 p-7 transition-all duration-200 hover:-translate-y-1 hover:shadow-lg"
        t_cls = "mt-3 text-lg font-bold text-white"
        s_cls = "mt-2 text-sm text-slate-400"
        p_cls = "text-sm text-slate-300"
        chk = "text-emerald-400"
        pr_cls = "mt-6 text-4xl font-extrabold tracking-tight text-white"
        per_cls = "text-xs font-semibold uppercase tracking-wide text-slate-400"
        cta_cls = "mt-8 inline-flex w-full items-center justify-center rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition-colors hover:bg-slate-50"

    badge_cls = (
        "inline-flex rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-300"
        if is_enterprise
        else "inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700"
    )
    badge = rx.el.span(badge_text, class_name=badge_cls) if badge_text else rx.fragment()

    rows = [
        rx.el.li(
            rx.icon("check", class_name=f"h-4 w-4 {chk} mt-0.5"),
            rx.el.span(pt, class_name=p_cls),
            class_name="flex items-start gap-3",
        )
        for pt in points
    ]
    return rx.el.article(
        badge,
        rx.el.h3(title, class_name=t_cls),
        rx.el.p(subtitle, class_name=s_cls),
        rx.el.div(
            rx.el.p(price_label, class_name=pr_cls),
            rx.el.p("USD / mes", class_name=per_cls),
        ),
        rx.el.ul(*rows, class_name="mt-8 space-y-3"),
        rx.el.a(
            cta_label, href=cta_href, target="_blank", rel="noopener noreferrer",
            on_click=rx.call_script(_track_event_script(event_name, f"plan_{title.lower()}")),
            class_name=cta_cls,
        ),
        class_name=card_cls,
    )


def _faq_item(question: str, answer: str, open_by_default: bool = False) -> rx.Component:
    open_props = {"open": True} if open_by_default else {}
    return rx.el.details(
        rx.el.summary(
            rx.el.div(
                rx.icon("circle-help", class_name="h-4 w-4 text-slate-400"),
                rx.el.p(question, class_name="text-sm font-semibold text-slate-900"),
                class_name="flex items-center gap-2.5",
            ),
            rx.icon("chevron-right", class_name="faq-chevron h-4 w-4 text-slate-400"),
            class_name="flex cursor-pointer list-none items-center justify-between gap-3",
        ),
        rx.el.p(answer, class_name="mt-3 text-sm leading-relaxed text-slate-600"),
        class_name="faq-item rounded-2xl border border-slate-200 bg-white p-5 transition-all duration-200 open:border-slate-300 open:shadow-sm",
        **open_props,
    )


def _footer_link(label: str, href: str, event_name: str, source: str, external: bool = False) -> rx.Component:
    return rx.el.a(
        label, href=href,
        target="_blank" if external else None,
        rel="noopener noreferrer" if external else None,
        on_click=rx.call_script(_track_event_script(event_name, source)),
        class_name="text-sm text-slate-600 transition-colors hover:text-slate-900",
    )


# ── Section Functions ────────────────────────────────────────

def _announcement_banner() -> rx.Component:
    return rx.cond(
        MarketingState.show_announcement,
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    rx.el.span("Nuevo", class_name="mr-2 rounded bg-emerald-500 px-1.5 py-0.5 text-[10px] font-bold uppercase text-white"),
                    "Modulo de Reservas con cobro parcial integrado",
                    class_name="text-sm font-medium text-white",
                ),
                rx.el.button(
                    rx.icon("x", class_name="h-4 w-4"),
                    on_click=MarketingState.dismiss_announcement,
                    class_name="ml-4 text-slate-400 hover:text-white transition-colors cursor-pointer",
                    aria_label="Cerrar aviso",
                ),
                class_name="mx-auto flex max-w-7xl items-center justify-center px-4 py-2",
            ),
            class_name="bg-slate-900",
        ),
        rx.fragment(),
    )


def _header_section() -> rx.Component:
    return rx.el.header(
        rx.el.div(
            rx.el.a(
                rx.icon("box", class_name="h-8 w-8 text-indigo-600"),
                rx.el.span("TUWAYKIAPP", class_name="text-2xl font-extrabold tracking-tight text-slate-900"),
                href=_site_href("/"),
                class_name="flex items-center gap-2.5",
            ),
            rx.el.nav(
                _nav_link("Modulos", "#modulos", "click_nav_modulos", "header_nav"),
                _nav_link("Como funciona", "#como-funciona", "click_nav_como_funciona", "header_nav"),
                _nav_link("Planes", "#planes", "click_nav_planes", "header_nav"),
                _nav_link("FAQ", "#faq", "click_nav_faq", "header_nav"),
                class_name="hidden items-center gap-6 md:flex",
            ),
            rx.el.div(
                rx.el.a(
                    "Ingresar",
                    href=_app_href("/"),
                    on_click=rx.call_script(_track_event_script("click_nav_login", "header_nav")),
                    class_name="hidden items-center justify-center rounded-xl border-2 border-indigo-600 bg-white px-4 py-2 text-sm font-semibold text-indigo-600 transition-colors hover:bg-indigo-50 md:inline-flex",
                ),
                rx.el.a(
                    "Iniciar prueba gratis",
                    href=_app_href("/registro"),
                    on_click=rx.call_script(_track_event_script("click_trial_cta", "header_primary_cta")),
                    class_name="hidden items-center justify-center rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 md:inline-flex",
                ),
                class_name="hidden items-center gap-3 md:flex",
            ),
            rx.el.details(
                rx.el.summary(
                    rx.icon("menu", class_name="h-5 w-5 text-slate-700"),
                    class_name="inline-flex h-10 w-10 cursor-pointer items-center justify-center rounded-lg border border-slate-200 bg-white md:hidden",
                ),
                rx.el.div(
                    _nav_link("Modulos", "#modulos", "click_nav_modulos_mobile", "mobile_menu"),
                    _nav_link("Como funciona", "#como-funciona", "click_nav_como_funciona_mobile", "mobile_menu"),
                    _nav_link("Planes", "#planes", "click_nav_planes_mobile", "mobile_menu"),
                    _nav_link("FAQ", "#faq", "click_nav_faq_mobile", "mobile_menu"),
                    rx.el.a(
                        "Ingresar", href=_app_href("/"),
                        on_click=rx.call_script(_track_event_script("click_nav_login_mobile", "mobile_menu")),
                        class_name="inline-flex w-full items-center justify-center rounded-xl border-2 border-indigo-600 px-4 py-2 text-sm font-semibold text-indigo-600 hover:bg-indigo-50",
                    ),
                    rx.el.a(
                        "Iniciar prueba gratis", href=_app_href("/registro"),
                        on_click=rx.call_script(_track_event_script("click_trial_cta", "mobile_menu_primary_cta")),
                        class_name="inline-flex w-full items-center justify-center rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700",
                    ),
                    class_name="absolute right-0 mt-3 w-64 rounded-xl border border-slate-200 bg-white p-3 shadow-lg md:hidden",
                ),
                class_name="relative md:hidden",
            ),
            class_name="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8",
        ),
        class_name="glass-nav fixed top-0 left-0 right-0 z-50 border-b border-slate-200/80",
    )


def _hero_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Plataforma SaaS multi-sucursal",
                    class_name="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700 shadow-sm",
                ),
                rx.el.h1(
                    "Deja de cruzar planillas. Controla ventas, stock y caja desde un solo lugar.",
                    class_name="mt-5 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl sm:leading-tight",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                rx.el.p(
                    "Operaciones multi-sucursal centralizadas: punto de venta, inventario, "
                    "reservas y cierre de caja con trazabilidad completa por usuario y sede.",
                    class_name="mt-5 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg",
                ),
                rx.el.div(
                    *[_trust_pill(icon, label) for icon, label in TRUST_BADGES],
                    class_name="reveal-stagger mt-7 grid grid-cols-1 gap-2 sm:grid-cols-2",
                ),
                rx.el.div(
                    rx.el.a(
                        "Comenzar trial de 15 dias",
                        href=_app_href("/registro"),
                        on_click=rx.call_script(_track_event_script("click_trial_cta", "hero_primary_cta")),
                        class_name="inline-flex items-center justify-center rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-emerald-700",
                    ),
                    rx.el.a(
                        rx.icon("message-circle", class_name="h-4 w-4"),
                        "Agendar demo guiada",
                        href=_demo_link,
                        target="_blank", rel="noopener noreferrer",
                        on_click=rx.call_script(_track_event_script("click_demo_cta", "hero_secondary_cta")),
                        class_name="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50",
                    ),
                    class_name="mt-8 flex flex-col gap-3 sm:flex-row",
                ),
                class_name="reveal max-w-2xl",
            ),
            _hero_preview_card(),
            class_name="grid grid-cols-1 items-start gap-10 lg:grid-cols-[0.95fr_1.05fr]",
        ),
        class_name="mx-auto w-full max-w-7xl px-4 pt-24 pb-16 sm:px-6 lg:px-8 lg:pt-28",
    )


def _metrics_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            _metric_card("+38%", "mejor visibilidad diaria", "Caja, ventas y reservas en una vista"),
            _metric_card("-52%", "menos errores operativos", "Flujos estandarizados y trazables"),
            _metric_card("15 dias", "trial gratuito", "Sin tarjeta, sin friccion"),
            _metric_card("24/7", "acceso cloud", "Desktop, tablet y mobile"),
            class_name="reveal-stagger grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4",
        ),
        class_name="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8",
    )


def _logos_section() -> rx.Component:
    ticker_nodes = [_logo_chip(m, n, s) for _ in range(2) for m, n, s in LOGOS]
    return rx.el.section(
        rx.el.div(
            rx.el.p(
                "Empresas que ya validan su operacion con TUWAYKIAPP",
                class_name="reveal text-xs font-semibold uppercase tracking-[0.18em] text-slate-500",
            ),
            rx.el.div(
                rx.el.div(*ticker_nodes, class_name="ticker-track"),
                class_name="ticker-wrap mt-6",
            ),
            class_name="mx-auto w-full max-w-7xl rounded-3xl border border-slate-200 bg-white px-6 py-6 shadow-sm",
        ),
        class_name="mx-auto w-full max-w-7xl px-4 pt-10 sm:px-6 lg:px-8",
    )


def _comparison_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.p("Problema vs solucion", class_name="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500"),
                rx.el.h2(
                    "Deja de improvisar. Centraliza la operacion.",
                    class_name="mt-2 text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                rx.el.p(
                    "Visualiza el antes y despues cuando dejas de cruzar Excel para saber si la caja cuadra.",
                    class_name="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                ),
                class_name="reveal max-w-4xl",
            ),
            rx.el.div(
                _comparison_card(
                    "Operacion fragmentada", "triangle-alert",
                    [
                        "Caja en Excel, ventas en otro sistema, reservas por WhatsApp",
                        "Errores por doble carga y falta de trazabilidad entre areas",
                        "Decisiones tardias porque no hay datos consolidados",
                    ],
                    tone="negative",
                ),
                _comparison_card(
                    "Operacion unificada", "sparkles",
                    [
                        "Venta, caja, stock y reservas en un solo flujo integrado",
                        "Datos consistentes por sucursal y por usuario responsable",
                        "Reportes en tiempo real para actuar antes, no despues",
                    ],
                    tone="positive",
                ),
                class_name="reveal-stagger mt-10 grid grid-cols-1 gap-4 lg:grid-cols-2",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8",
        ),
    )


def _modules_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.h2(
                "Modulos conectados para operar sin friccion",
                class_name="reveal text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                style={"fontFamily": "'Space Grotesk', sans-serif"},
            ),
            rx.el.p(
                "Seis capacidades clave que trabajan juntas para sostener crecimiento y control.",
                class_name="reveal mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
            ),
            rx.el.div(
                *[_module_card(m["icon"], m["title"], m["description"], m["bullets"]) for m in MODULES],
                class_name="reveal-stagger mt-10 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8",
            id="modulos",
        ),
    )


def _timeline_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.h2(
                "Como funciona",
                class_name="reveal text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                style={"fontFamily": "'Space Grotesk', sans-serif"},
            ),
            rx.el.p(
                "Implementacion en cinco pasos para salir a operar rapido.",
                class_name="reveal mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
            ),
            rx.el.div(
                *[_timeline_step(s, t, d) for s, t, d in STEPS],
                class_name="reveal-stagger mt-10 grid grid-cols-1 gap-3 md:grid-cols-2",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8",
            id="como-funciona",
        ),
        class_name="bg-slate-50",
    )


def _strength_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.h2(
                "Construido para operaciones reales",
                class_name="reveal text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                style={"fontFamily": "'Space Grotesk', sans-serif"},
            ),
            rx.el.p(
                "Arquitectura pensada para negocios multi-sucursal que necesitan control, no promesas.",
                class_name="reveal mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
            ),
            rx.el.div(
                *[_strength_card(m["icon"], m["title"], m["detail"]) for m in STRENGTH_METRICS],
                class_name="reveal-stagger mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8",
        ),
    )


def _cloud_panel() -> rx.Component:
    """Panel de planes en la nube."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("circle-check", class_name="h-5 w-5 text-emerald-600"),
                    rx.el.span("Ventajas", class_name="text-sm font-bold text-slate-900"),
                    class_name="flex items-center gap-2 mb-3",
                ),
                rx.el.ul(
                    *[
                        rx.el.li(
                            rx.icon("check", class_name="h-3.5 w-3.5 text-emerald-600 mt-0.5"),
                            rx.el.span(t, class_name="text-sm text-slate-700"),
                            class_name="flex items-start gap-2",
                        )
                        for t in [
                            "Accede desde cualquier dispositivo con internet",
                            "Actualizaciones automaticas sin intervencion",
                            "Backups diarios en la nube incluidos",
                            "Soporte tecnico remoto inmediato",
                            "Escalable: crece sin cambiar de infraestructura",
                            "Sin costos de hardware ni mantenimiento de servidor",
                        ]
                    ],
                    class_name="space-y-1.5",
                ),
                class_name="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4",
            ),
            rx.el.div(
                rx.el.div(
                    rx.icon("circle-alert", class_name="h-5 w-5 text-amber-600"),
                    rx.el.span("Consideraciones", class_name="text-sm font-bold text-slate-900"),
                    class_name="flex items-center gap-2 mb-3",
                ),
                rx.el.ul(
                    *[
                        rx.el.li(
                            rx.icon("minus", class_name="h-3.5 w-3.5 text-amber-600 mt-0.5"),
                            rx.el.span(t, class_name="text-sm text-slate-600"),
                            class_name="flex items-start gap-2",
                        )
                        for t in [
                            "Requiere conexion a internet estable",
                            "Pago mensual recurrente segun el plan",
                            "Los datos se alojan en servidores externos",
                        ]
                    ],
                    class_name="space-y-1.5",
                ),
                class_name="rounded-xl border border-amber-200 bg-amber-50/50 p-4",
            ),
            class_name="grid grid-cols-1 gap-4 sm:grid-cols-2 mt-8",
        ),
        rx.el.div(
            rx.el.p("Planes disponibles", class_name="text-lg font-bold text-slate-900 mb-4"),
            rx.el.div(
                _plan_card("Standard", "Ideal para negocios que quieren orden operativo desde el inicio.", "$45",
                    ["Hasta 5 sucursales", "Hasta 10 usuarios", "Punto de venta + caja + inventario", "Reportes base y soporte comercial"],
                    "Elegir Standard", _standard_link, "click_plan_standard", tone="standard"),
                _plan_card("Professional", "Para operaciones de mayor volumen y necesidad de control avanzado.", "$75",
                    ["Hasta 10 sucursales", "Usuarios ilimitados", "Configuraciones avanzadas", "Prioridad de soporte", "Mayor profundidad de reportes"],
                    "Elegir Professional", _professional_link, "click_plan_professional", tone="professional", badge_text="Mas elegido"),
                _plan_card("Enterprise", "Para companias con demanda de escala, personalizacion y SLA dedicado.", "$175",
                    ["Plan personalizable por operacion", "Onboarding y arquitectura dedicada", "Integraciones y flujos a medida", "Acompanamiento prioritario", "Gobernanza enterprise"],
                    "Solicitar Enterprise", _enterprise_link, "click_plan_enterprise", tone="enterprise", badge_text="Escala total"),
                class_name="grid grid-cols-1 items-stretch gap-4 lg:grid-cols-3",
            ),
            class_name="mt-8",
        ),
    )


def _local_panel() -> rx.Component:
    """Panel de licencia local."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("circle-check", class_name="h-5 w-5 text-emerald-600"),
                    rx.el.span("Ventajas", class_name="text-sm font-bold text-slate-900"),
                    class_name="flex items-center gap-2 mb-3",
                ),
                rx.el.ul(
                    *[
                        rx.el.li(
                            rx.icon("check", class_name="h-3.5 w-3.5 text-emerald-600 mt-0.5"),
                            rx.el.span(t, class_name="text-sm text-slate-700"),
                            class_name="flex items-start gap-2",
                        )
                        for t in [
                            "Funciona sin conexion a internet",
                            "Pago unico anual — sin mensualidades",
                            "Tus datos permanecen 100% en tu equipo",
                            "Control total sobre tu infraestructura",
                            "Ideal para zonas con internet inestable",
                            "Rendimiento optimo sin depender de la red",
                        ]
                    ],
                    class_name="space-y-1.5",
                ),
                class_name="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4",
            ),
            rx.el.div(
                rx.el.div(
                    rx.icon("circle-alert", class_name="h-5 w-5 text-amber-600"),
                    rx.el.span("Consideraciones", class_name="text-sm font-bold text-slate-900"),
                    class_name="flex items-center gap-2 mb-3",
                ),
                rx.el.ul(
                    *[
                        rx.el.li(
                            rx.icon("minus", class_name="h-3.5 w-3.5 text-amber-600 mt-0.5"),
                            rx.el.span(t, class_name="text-sm text-slate-600"),
                            class_name="flex items-start gap-2",
                        )
                        for t in [
                            "Requiere un equipo dedicado (PC o servidor local)",
                            "Los backups y mantenimiento los gestiona tu equipo",
                            "Solo se accede desde la red local (sin acceso remoto)",
                            "Las actualizaciones requieren instalacion manual",
                        ]
                    ],
                    class_name="space-y-1.5",
                ),
                class_name="rounded-xl border border-amber-200 bg-amber-50/50 p-4",
            ),
            class_name="grid grid-cols-1 gap-4 sm:grid-cols-2 mt-8",
        ),
        rx.el.div(
            rx.el.article(
                rx.el.span("Pago unico", class_name="inline-flex rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700"),
                rx.el.h3("Licencia Local", class_name="mt-2 text-lg font-bold text-slate-900"),
                rx.el.p("Instalamos el sistema en tu equipo. Un solo pago anual con soporte incluido.", class_name="mt-2 text-sm text-slate-600"),
                rx.el.div(
                    rx.el.p("Consultar", class_name="mt-4 text-4xl font-extrabold tracking-tight text-slate-900"),
                    rx.el.p("USD / pago anual", class_name="text-xs font-semibold uppercase tracking-wide text-slate-500"),
                ),
                rx.el.ul(
                    *[
                        rx.el.li(
                            rx.icon("check", class_name="h-4 w-4 text-indigo-600"),
                            rx.el.span(t, class_name="text-sm text-slate-700"),
                            class_name="flex items-start gap-2",
                        )
                        for t in [
                            "Sistema completo (ventas, caja, inventario, reportes)",
                            "Instalacion y configuracion inicial incluida",
                            "Soporte tecnico por 12 meses",
                            "Capacitacion inicial para tu equipo",
                            "Actualizaciones durante el periodo contratado",
                        ]
                    ],
                    class_name="mt-5 space-y-2",
                ),
                rx.el.a(
                    rx.icon("message-circle", class_name="h-4 w-4"),
                    "Consultar precio por WhatsApp",
                    href=_local_link, target="_blank", rel="noopener noreferrer",
                    on_click=rx.call_script(_track_event_script("click_plan_local", "plan_local")),
                    class_name="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700",
                ),
                class_name="rounded-2xl border border-slate-300 bg-white p-7 ring-1 ring-slate-900/5 transition-all duration-200 hover:-translate-y-1 hover:shadow-md max-w-md mx-auto",
            ),
            class_name="mt-8",
        ),
    )


def _pricing_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.h2(
                "Elige como quieres usar TUWAYKIAPP",
                class_name="reveal text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                style={"fontFamily": "'Space Grotesk', sans-serif"},
            ),
            rx.el.p(
                "Dos modalidades, el mismo sistema completo. Elige la que mejor se adapte a tu negocio.",
                class_name="reveal mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("cloud", class_name="h-4 w-4"), "Servicio en la Nube",
                    on_click=MarketingState.set_tab_nube,
                    class_name=rx.cond(
                        MarketingState.active_tab == "nube",
                        "tab-btn active inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all cursor-pointer",
                        "tab-btn inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all cursor-pointer",
                    ),
                ),
                rx.el.button(
                    rx.icon("hard-drive", class_name="h-4 w-4"), "Instalacion Local",
                    on_click=MarketingState.set_tab_local,
                    class_name=rx.cond(
                        MarketingState.active_tab == "local",
                        "tab-btn active inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all cursor-pointer",
                        "tab-btn inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all cursor-pointer",
                    ),
                ),
                class_name="reveal mt-10 inline-flex gap-2 rounded-xl bg-slate-100 p-1.5",
            ),
            rx.cond(
                MarketingState.active_tab == "nube",
                _cloud_panel(),
                _local_panel(),
            ),
            class_name="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8",
            id="planes",
        ),
    )


def _faq_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.h2(
                "Preguntas frecuentes",
                class_name="reveal text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                style={"fontFamily": "'Space Grotesk', sans-serif"},
            ),
            rx.el.div(
                *[_faq_item(q, a, open_by_default=i == 0) for i, (q, a) in enumerate(FAQ_ITEMS)],
                class_name="reveal-stagger mt-8 grid grid-cols-1 gap-3 md:grid-cols-2",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.p("Aun tienes dudas antes de activar tu trial?", class_name="text-base font-semibold text-slate-900"),
                    rx.el.p("Nuestro equipo te ayuda a elegir plan y a estimar implementacion segun tu operacion.", class_name="mt-1 text-sm text-slate-600"),
                    class_name="flex-1",
                ),
                rx.el.div(
                    rx.el.a(
                        "Hablar por WhatsApp", href=_demo_link, target="_blank", rel="noopener noreferrer",
                        on_click=rx.call_script(_track_event_script("click_demo_cta", "faq_whatsapp_cta")),
                        class_name="inline-flex items-center justify-center rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700",
                    ),
                    rx.el.a(
                        "Iniciar prueba", href=_app_href("/registro"),
                        on_click=rx.call_script(_track_event_script("click_trial_cta", "faq_trial_cta")),
                        class_name="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50",
                    ),
                    class_name="flex flex-col gap-2 sm:flex-row",
                ),
                class_name="reveal mt-8 flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8",
            id="faq",
        ),
        class_name="bg-slate-50",
    )


def _cta_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.h2(
                    "Tu operacion merece mas que planillas y sistemas desconectados",
                    class_name="text-2xl font-extrabold tracking-tight text-white sm:text-3xl",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                rx.el.p(
                    "Activa tu prueba de 15 dias sin tarjeta. Centraliza ventas, inventario, caja y reservas desde hoy.",
                    class_name="mt-4 max-w-2xl text-sm leading-relaxed text-slate-300 sm:text-base",
                ),
                rx.el.div(
                    rx.el.a(
                        "Crear cuenta ahora", href=_app_href("/registro"),
                        on_click=rx.call_script(_track_event_script("click_trial_cta", "bottom_banner_primary_cta")),
                        class_name="inline-flex items-center justify-center rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-emerald-400",
                    ),
                    rx.el.a(
                        "Agendar demo", href=_demo_link, target="_blank", rel="noopener noreferrer",
                        on_click=rx.call_script(_track_event_script("click_demo_cta", "bottom_banner_secondary_cta")),
                        class_name="inline-flex items-center justify-center rounded-xl border border-slate-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-slate-800",
                    ),
                    class_name="mt-8 flex flex-col gap-3 sm:flex-row",
                ),
                class_name="reveal mx-auto w-full max-w-7xl overflow-hidden rounded-3xl bg-slate-900 border border-slate-800 px-8 py-14 sm:px-12 sm:py-16 shadow-2xl",
            ),
        ),
        class_name="mx-auto w-full max-w-7xl px-4 pb-16 sm:px-6 lg:px-8",
    )


def _footer_section() -> rx.Component:
    return rx.el.footer(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.a(
                        rx.icon("box", class_name="h-7 w-7 text-indigo-600"),
                        rx.el.span("TUWAYKIAPP", class_name="text-lg font-extrabold tracking-tight text-slate-900"),
                        href=_site_href("/"), class_name="inline-flex items-center gap-2.5",
                    ),
                    rx.el.p("Sistema de ventas SaaS para negocios multi-sucursal con enfoque en control real.", class_name="mt-3 max-w-xs text-sm text-slate-600"),
                    rx.el.a(
                        "WhatsApp +5491168376517",
                        href=f"https://wa.me/{WHATSAPP_NUMBER}", target="_blank", rel="noopener noreferrer",
                        on_click=rx.call_script(_track_event_script("click_whatsapp_cta", "footer_contact")),
                        class_name="mt-3 inline-flex text-sm font-semibold text-emerald-700 hover:text-emerald-800",
                    ),
                ),
                rx.el.div(
                    rx.el.h4("Producto", class_name="text-sm font-bold text-slate-900"),
                    _footer_link("Modulos", "#modulos", "click_footer_modulos", "footer_producto"),
                    _footer_link("Planes", "#planes", "click_footer_planes", "footer_producto"),
                    _footer_link("FAQ", "#faq", "click_footer_faq", "footer_producto"),
                    class_name="flex flex-col gap-2",
                ),
                rx.el.div(
                    rx.el.h4("Empresa", class_name="text-sm font-bold text-slate-900"),
                    _footer_link("Agendar demo", _demo_link, "click_footer_demo", "footer_empresa", external=True),
                    _footer_link("Hablar con ventas", _demo_link, "click_footer_sales", "footer_empresa", external=True),
                    _footer_link("Soporte", _demo_link, "click_footer_support", "footer_empresa", external=True),
                    class_name="flex flex-col gap-2",
                ),
                rx.el.div(
                    rx.el.h4("Accesos", class_name="text-sm font-bold text-slate-900"),
                    _footer_link("Iniciar sesion", _app_href("/"), "click_footer_login", "footer_accesos"),
                    _footer_link("Crear cuenta", _app_href("/registro"), "click_footer_signup", "footer_accesos"),
                    _footer_link("WhatsApp directo", f"https://wa.me/{WHATSAPP_NUMBER}", "click_footer_whatsapp", "footer_accesos", external=True),
                    class_name="flex flex-col gap-2",
                ),
                rx.el.div(
                    rx.el.h4("Legal", class_name="text-sm font-bold text-slate-900"),
                    _footer_link("Términos y condiciones", _site_href("/terminos"), "click_footer_terms", "footer_legal"),
                    _footer_link("Política de privacidad", _site_href("/privacidad"), "click_footer_privacy", "footer_legal"),
                    _footer_link("Política de cookies", _site_href("/cookies"), "click_footer_cookies", "footer_legal"),
                    class_name="flex flex-col gap-2",
                ),
                class_name="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-5",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.p("TUWAYKIAPP \u00a9 2026. Todos los derechos reservados.", class_name="text-sm leading-relaxed text-slate-500"),
                    rx.el.p("Hecho con foco en escalabilidad, operacion y crecimiento comercial.", class_name="text-sm leading-relaxed text-slate-500"),
                    class_name="space-y-1",
                ),
                rx.el.div(
                    rx.el.p("Creado por", class_name="text-xs text-slate-400 uppercase tracking-wider"),
                    rx.el.a(
                        "Trebor Oscorima ",
                        rx.el.span("\ud83e\uddc9\u26bd\ufe0f", class_name="ml-1"),
                        href="https://www.facebook.com/trebor.oscorima/?locale=es_LA", target="_blank", rel="noopener noreferrer",
                        class_name="text-sm font-semibold text-slate-700 hover:text-indigo-600 transition-colors",
                    ),
                    rx.el.a(
                        rx.icon("message-circle", class_name="h-3.5 w-3.5"), "+5491168376517",
                        href="https://wa.me/5491168376517", target="_blank", rel="noopener noreferrer",
                        class_name="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600 hover:text-emerald-700 transition-colors",
                    ),
                    class_name="mt-1 flex flex-col gap-0.5 items-start text-left sm:mt-0 sm:items-end sm:text-right",
                ),
                class_name="mt-8 flex flex-col items-start justify-between gap-4 border-t border-slate-200 pt-4 sm:flex-row sm:items-center",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8",
        ),
        class_name="border-t border-slate-200 bg-white",
    )


def _floating_whatsapp() -> rx.Component:
    return rx.el.a(
        rx.icon("message-circle", class_name="h-5 w-5"),
        rx.el.span("WhatsApp", class_name="hidden text-sm font-semibold sm:inline"),
        href=_demo_link, target="_blank", rel="noopener noreferrer",
        on_click=rx.call_script(_track_event_script("click_whatsapp_cta", "floating_button")),
        class_name="fixed bottom-5 right-5 z-[60] inline-flex items-center gap-2 rounded-full bg-emerald-600 px-4 py-3 text-white shadow-lg transition-all hover:-translate-y-0.5 hover:bg-emerald-700",
        aria_label="Contactar por WhatsApp",
    )


# ── Page ─────────────────────────────────────────────────────
def marketing_page() -> rx.Component:
    """Pagina de marketing y landing page publica."""
    return rx.el.div(
        rx.el.style(_global_styles()),
        rx.script(_analytics_bootstrap_script()),
        rx.script(_cookie_consent_script()),
        rx.script(_reveal_script()),
        _announcement_banner(),
        _header_section(),
        rx.el.main(
            _hero_section(),
            _metrics_section(),
            _logos_section(),
            _comparison_section(),
            _modules_section(),
            _timeline_section(),
            _strength_section(),
            _pricing_section(),
            _faq_section(),
            _cta_section(),
            class_name="relative",
        ),
        _footer_section(),
        _floating_whatsapp(),
        _cookie_consent_banner(),
        class_name="relative min-h-screen bg-slate-50",
        style={"fontFamily": "'Manrope', sans-serif"},
    )
