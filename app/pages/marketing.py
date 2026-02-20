import os
from urllib.parse import quote

import reflex as rx

from app.constants import WHATSAPP_NUMBER

GA4_MEASUREMENT_ID = (os.getenv("GA4_MEASUREMENT_ID") or "").strip()
META_PIXEL_ID = (os.getenv("META_PIXEL_ID") or "").strip()


def _wa_link(message: str) -> str:
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(message)}"


def _analytics_bootstrap_script() -> str:
    ga4_id = GA4_MEASUREMENT_ID.replace("'", "\\'")
    pixel_id = META_PIXEL_ID.replace("'", "\\'")
    return (
        "(function(){"
        "if(window.__tuwayAnalyticsReady){return;}"
        "window.__tuwayAnalyticsReady=true;"
        f"var ga4Id='{ga4_id}';"
        f"var metaPixelId='{pixel_id}';"
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
        "window.tuwayTrack=window.tuwayTrack||function(name,payload){"
        "payload=payload||{};"
        "var data=Object.assign({event:name,page:window.location.pathname,ts:new Date().toISOString()},payload);"
        "window.dataLayer=window.dataLayer||[];"
        "window.dataLayer.push(data);"
        "if(typeof window.gtag==='function'){window.gtag('event',name,data);}"
        "if(typeof window.fbq==='function'){window.fbq('trackCustom',name,data);}"
        "try{var q=JSON.parse(localStorage.getItem('tuway_events')||'[]');q.push(data);localStorage.setItem('tuway_events',JSON.stringify(q.slice(-200)));}catch(e){}"
        "};"
        "try{if(!sessionStorage.getItem('tw_view_landing_sent')){window.tuwayTrack('view_landing',{source:'landing'});sessionStorage.setItem('tw_view_landing_sent','1');}}"
        "catch(e){window.tuwayTrack('view_landing',{source:'landing'});}"
        "})();"
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


def _ui_bootstrap_script() -> str:
    return (
        "(function(){"
        "if(window.__tuwayUiReady){return;}"
        "window.__tuwayUiReady=true;"
        "document.documentElement.classList.add('tw-anim');"
        "function bindGlow(){"
        "var cards=document.querySelectorAll('.glow-card');"
        "cards.forEach(function(card){"
        "if(card.__twGlowBound){return;}"
        "card.__twGlowBound=true;"
        "card.addEventListener('pointermove',function(ev){"
        "var r=card.getBoundingClientRect();"
        "var x=((ev.clientX-r.left)/Math.max(r.width,1))*100;"
        "var y=((ev.clientY-r.top)/Math.max(r.height,1))*100;"
        "card.style.setProperty('--mx',x+'%');"
        "card.style.setProperty('--my',y+'%');"
        "});"
        "});"
        "}"
        "function bindReveal(){"
        "var nodes=document.querySelectorAll('.reveal,.reveal-stagger');"
        "if(!('IntersectionObserver' in window)){"
        "nodes.forEach(function(el){el.classList.add('in-view');});"
        "return;"
        "}"
        "var io=new IntersectionObserver(function(entries){"
        "entries.forEach(function(entry){"
        "if(entry.isIntersecting){"
        "entry.target.classList.add('in-view');"
        "io.unobserve(entry.target);"
        "}"
        "});"
        "},{threshold:0.16,rootMargin:'0px 0px -10% 0px'});"
        "nodes.forEach(function(el){io.observe(el);});"
        "}"
        "function init(){bindGlow();bindReveal();}"
        "if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',init);}else{init();}"
        "window.addEventListener('load',init);"
        "})();"
    )


def _global_styles() -> str:
    return """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');
@keyframes gradMove {
  0% { transform: translate3d(0,0,0) scale(1); }
  50% { transform: translate3d(-1.5%, 2%, 0) scale(1.04); }
  100% { transform: translate3d(2%, -1%, 0) scale(1.02); }
}
@keyframes floatY {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-14px); }
}
@keyframes tickerMove {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}
@keyframes pulseRing {
  0% { transform: scale(0.95); opacity: 0.5; }
  70% { transform: scale(1.15); opacity: 0; }
  100% { transform: scale(1.2); opacity: 0; }
}
.mesh-bg {
  background:
    radial-gradient(55% 60% at 15% 20%, rgba(16,185,129,0.20), rgba(16,185,129,0) 70%),
    radial-gradient(45% 55% at 85% 15%, rgba(14,165,233,0.20), rgba(14,165,233,0) 70%),
    radial-gradient(35% 45% at 55% 80%, rgba(20,184,166,0.16), rgba(20,184,166,0) 70%);
  animation: gradMove 16s ease-in-out infinite alternate;
}
.orb-a { animation: floatY 10s ease-in-out infinite; }
.orb-b { animation: floatY 13s ease-in-out infinite reverse; }
.orb-c { animation: floatY 16s ease-in-out infinite; }
.glass-nav {
  backdrop-filter: blur(14px);
  background: rgba(255,255,255,0.76);
}
.glow-card {
  position: relative;
  overflow: hidden;
}
.glow-card::before {
  content: '';
  position: absolute;
  inset: -1px;
  pointer-events: none;
  background: radial-gradient(
    460px circle at var(--mx, 50%) var(--my, 50%),
    rgba(16,185,129,0.18),
    rgba(56,189,248,0.10) 25%,
    transparent 55%
  );
  opacity: 0;
  transition: opacity 220ms ease;
}
.glow-card:hover::before {
  opacity: 1;
}
.ticker-wrap {
  overflow: hidden;
  mask-image: linear-gradient(to right, transparent, black 10%, black 90%, transparent);
}
.ticker-track {
  display: flex;
  width: max-content;
  gap: 14px;
  animation: tickerMove 30s linear infinite;
}
.faq-item .faq-chevron {
  transition: transform 180ms ease;
}
.faq-item[open] .faq-chevron {
  transform: rotate(90deg);
}
.reveal {
  opacity: 1;
  transform: translateY(0);
}
.tw-anim .reveal {
  opacity: 0;
  transform: translateY(18px);
  transition: opacity 520ms ease, transform 520ms ease;
}
.tw-anim .reveal.in-view {
  opacity: 1;
  transform: translateY(0);
}
.reveal-stagger > * {
  opacity: 1;
  transform: translateY(0);
}
.tw-anim .reveal-stagger > * {
  opacity: 0;
  transform: translateY(14px);
  transition: opacity 460ms ease, transform 460ms ease;
}
.tw-anim .reveal-stagger.in-view > * {
  opacity: 1;
  transform: translateY(0);
}
.tw-anim .reveal-stagger.in-view > *:nth-child(1) { transition-delay: 40ms; }
.tw-anim .reveal-stagger.in-view > *:nth-child(2) { transition-delay: 100ms; }
.tw-anim .reveal-stagger.in-view > *:nth-child(3) { transition-delay: 160ms; }
.tw-anim .reveal-stagger.in-view > *:nth-child(4) { transition-delay: 220ms; }
.tw-anim .reveal-stagger.in-view > *:nth-child(5) { transition-delay: 280ms; }
.tw-anim .reveal-stagger.in-view > *:nth-child(6) { transition-delay: 340ms; }
.wa-pulse::before {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 9999px;
  border: 2px solid rgba(16,185,129,0.45);
  animation: pulseRing 1.8s ease-out infinite;
}
.tab-btn {
  color: #64748b;
  background: transparent;
}
.tab-btn.active {
  color: #4f46e5;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
"""


def _nav_link(label: str, href: str, event_name: str = "", source: str = "") -> rx.Component:
    props = {}
    if event_name:
        props["on_click"] = rx.call_script(_track_event_script(event_name, source))
    return rx.el.a(
        label,
        href=href,
        class_name=(
            "text-sm font-semibold text-slate-600 transition-colors duration-150 "
            "hover:text-slate-900"
        ),
        **props,
    )


def _metric_card(value: str, label: str, detail: str) -> rx.Component:
    return rx.el.div(
        rx.el.p(value, class_name="text-2xl font-extrabold text-slate-900 sm:text-3xl"),
        rx.el.p(label, class_name="mt-1 text-sm font-semibold text-slate-700"),
        rx.el.p(detail, class_name="mt-1 text-xs text-slate-500"),
        class_name=(
            "glow-card rounded-2xl border border-slate-200 bg-white/95 px-4 py-4 shadow-sm "
            "transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
        ),
    )


def _trust_pill(icon: str, label: str) -> rx.Component:
    return rx.el.div(
        rx.icon(icon, class_name="h-4 w-4 text-emerald-700"),
        rx.el.span(label, class_name="text-xs font-semibold text-slate-700 sm:text-sm"),
        class_name=(
            "inline-flex items-center gap-2 rounded-xl border border-emerald-100 bg-white/90 "
            "px-3 py-2 shadow-sm backdrop-blur"
        ),
    )


def _logo_chip(mark: str, name: str, segment: str) -> rx.Component:
    return rx.el.div(
        rx.el.span(
            mark,
            class_name=(
                "inline-flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 "
                "text-xs font-bold text-white"
            ),
        ),
        rx.el.div(
            rx.el.p(name, class_name="text-sm font-semibold text-slate-800"),
            rx.el.p(segment, class_name="text-xs text-slate-500"),
            class_name="leading-tight",
        ),
        class_name=(
            "inline-flex min-w-[210px] items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2 "
            "shadow-sm"
        ),
    )


def _hero_preview_card() -> rx.Component:
    return rx.el.aside(
        rx.el.div(
            rx.el.div(
                rx.el.span(class_name="h-2.5 w-2.5 rounded-full bg-rose-400"),
                rx.el.span(class_name="h-2.5 w-2.5 rounded-full bg-amber-400"),
                rx.el.span(class_name="h-2.5 w-2.5 rounded-full bg-emerald-400"),
                class_name="flex items-center gap-1.5",
            ),
            rx.el.span(
                rx.icon("sparkles", class_name="h-3.5 w-3.5"),
                "Vista de producto",
                class_name=(
                    "inline-flex items-center gap-1 rounded-full border border-emerald-200 "
                    "bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700"
                ),
            ),
            class_name="flex items-center justify-between",
        ),
        rx.el.div(
            rx.el.img(
                src="/dashboard-hero-real.png",
                alt="Captura del dashboard de TUWAYKIAPP",
                class_name="h-auto w-full rounded-2xl border border-slate-200 object-cover",
            ),
            rx.el.div(
                rx.el.div(
                    rx.icon("bar-chart-3", class_name="h-4 w-4 text-indigo-600"),
                    rx.el.span("Metricas en tiempo real", class_name="text-xs font-semibold text-slate-700"),
                    class_name="rounded-lg border border-slate-200 bg-white/95 px-3 py-2 shadow-sm",
                ),
                rx.el.div(
                    rx.icon("calendar-check", class_name="h-4 w-4 text-cyan-600"),
                    rx.el.span("Reservas y cobros unificados", class_name="text-xs font-semibold text-slate-700"),
                    class_name="rounded-lg border border-slate-200 bg-white/95 px-3 py-2 shadow-sm",
                ),
                class_name="absolute -bottom-3 left-4 right-4 grid gap-2 sm:grid-cols-2",
            ),
            class_name="relative mt-4 pb-10",
        ),
        class_name=(
            "glow-card reveal rounded-3xl border border-slate-200/80 bg-white/95 p-5 "
            "shadow-[0_30px_80px_-35px_rgba(15,23,42,0.45)] backdrop-blur"
        ),
    )


def _comparison_card(title: str, icon: str, points: list[str], tone: str = "negative") -> rx.Component:
    icon_bg = "bg-rose-50 text-rose-600" if tone == "negative" else "bg-emerald-50 text-emerald-700"
    border = "border-rose-200" if tone == "negative" else "border-emerald-200"
    bullet_icon = "x" if tone == "negative" else "check"
    bullet_color = "text-rose-500" if tone == "negative" else "text-emerald-600"

    rows = [
        rx.el.li(
            rx.icon(bullet_icon, class_name=f"h-4 w-4 {bullet_color}"),
            rx.el.span(point, class_name="text-sm text-slate-700"),
            class_name="flex items-start gap-2",
        )
        for point in points
    ]

    return rx.el.article(
        rx.el.div(
            rx.icon(icon, class_name="h-5 w-5"),
            class_name=f"inline-flex rounded-xl p-2 {icon_bg}",
        ),
        rx.el.h3(title, class_name="mt-4 text-lg font-bold text-slate-900"),
        rx.el.ul(*rows, class_name="mt-4 space-y-2"),
        class_name=f"glow-card rounded-2xl border {border} bg-white p-6 shadow-sm",
    )


def _module_card(icon: str, title: str, description: str, bullets: list[str]) -> rx.Component:
    rows = [
        rx.el.li(
            rx.icon("badge-check", class_name="h-4 w-4 text-emerald-700"),
            rx.el.span(item, class_name="text-sm text-slate-700"),
            class_name="flex items-start gap-2",
        )
        for item in bullets
    ]

    return rx.el.article(
        rx.el.div(
            rx.icon(icon, class_name="h-5 w-5 text-emerald-700"),
            class_name="inline-flex items-center justify-center rounded-xl bg-emerald-100 p-2",
        ),
        rx.el.h3(title, class_name="mt-4 text-base font-bold text-slate-900"),
        rx.el.p(description, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
        rx.el.ul(*rows, class_name="mt-4 space-y-2"),
        class_name=(
            "glow-card rounded-2xl border border-slate-200 bg-white p-5 shadow-sm "
            "transition-all duration-200 hover:-translate-y-1 hover:shadow-lg"
        ),
    )


def _timeline_step(step: str, title: str, detail: str) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            rx.el.span(
                step,
                class_name=(
                    "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full "
                    "bg-slate-900 text-xs font-bold text-white"
                ),
            ),
            class_name="relative z-10",
        ),
        rx.el.div(
            rx.el.h3(title, class_name="text-base font-semibold text-slate-900"),
            rx.el.p(detail, class_name="mt-1 text-sm text-slate-600"),
            class_name="flex-1",
        ),
        class_name=(
            "glow-card relative flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
        ),
    )


def _testimonial_card(initials: str, name: str, role: str, quote: str) -> rx.Component:
    stars = [
        rx.icon("star", class_name="h-4 w-4 fill-amber-400 text-amber-400")
        for _ in range(5)
    ]

    return rx.el.article(
        rx.el.div(
            rx.el.span(
                initials,
                class_name=(
                    "inline-flex h-11 w-11 items-center justify-center rounded-full bg-slate-900 "
                    "text-sm font-bold text-white"
                ),
            ),
            rx.el.div(
                rx.el.p(name, class_name="text-sm font-bold text-slate-900"),
                rx.el.p(role, class_name="text-xs text-slate-500"),
                class_name="leading-tight",
            ),
            class_name="flex items-center gap-3",
        ),
        rx.el.div(*stars, class_name="mt-4 flex items-center gap-1"),
        rx.el.p(
            f'"{quote}"',
            class_name="mt-3 text-sm leading-relaxed text-slate-700",
        ),
        class_name=(
            "glow-card rounded-2xl border border-slate-200 bg-white p-5 shadow-sm "
            "transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        ),
    )


def _plan_card(
    title: str,
    subtitle: str,
    price_label: str,
    points: list[str],
    cta_label: str,
    cta_href: str,
    event_name: str,
    tone: str = "standard",
    badge_text: str = "",
) -> rx.Component:
    is_enterprise = tone == "enterprise"
    is_professional = tone == "professional"

    card_class = (
        "glow-card rounded-2xl border bg-white p-6 shadow-sm transition-all duration-200 "
        "hover:-translate-y-1 hover:shadow-xl"
    )
    subtitle_class = "mt-2 text-sm text-slate-600"
    title_class = "mt-2 text-lg font-bold text-slate-900"
    point_text_class = "text-sm text-slate-700"
    check_color = "text-emerald-700"
    price_class = "mt-4 text-4xl font-extrabold tracking-tight text-slate-900"
    period_class = "text-xs font-semibold uppercase tracking-wide text-slate-500"
    cta_class = (
        "mt-6 inline-flex w-full items-center justify-center rounded-xl bg-slate-900 px-4 py-2.5 "
        "text-sm font-semibold text-white transition-colors duration-150 hover:bg-slate-800"
    )

    if is_professional:
        card_class += " border-emerald-200 ring-2 ring-emerald-400"
    else:
        card_class += " border-slate-200"

    if is_enterprise:
        card_class = (
            "glow-card rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-lg transition-all "
            "duration-200 hover:-translate-y-1 hover:shadow-2xl"
        )
        subtitle_class = "mt-2 text-sm text-slate-300"
        title_class = "mt-2 text-lg font-bold text-white"
        point_text_class = "text-sm text-slate-200"
        check_color = "text-emerald-300"
        price_class = "mt-4 text-4xl font-extrabold tracking-tight text-white"
        period_class = "text-xs font-semibold uppercase tracking-wide text-slate-300"
        cta_class = (
            "mt-6 inline-flex w-full items-center justify-center rounded-xl bg-emerald-500 px-4 py-2.5 "
            "text-sm font-semibold text-white transition-colors duration-150 hover:bg-emerald-400"
        )

    badge = (
        rx.el.span(
            badge_text,
            class_name=(
                "inline-flex rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700"
            ),
        )
        if badge_text
        else rx.fragment()
    )

    rows = [
        rx.el.li(
            rx.icon("check", class_name=f"h-4 w-4 {check_color}"),
            rx.el.span(point, class_name=point_text_class),
            class_name="flex items-start gap-2",
        )
        for point in points
    ]

    return rx.el.article(
        badge,
        rx.el.h3(title, class_name=title_class),
        rx.el.p(subtitle, class_name=subtitle_class),
        rx.el.div(
            rx.el.p(price_label, class_name=price_class),
            rx.el.p("USD / mes", class_name=period_class),
        ),
        rx.el.ul(*rows, class_name="mt-5 space-y-2"),
        rx.el.a(
            cta_label,
            href=cta_href,
            target="_blank",
            rel="noopener noreferrer",
            on_click=rx.call_script(_track_event_script(event_name, f"plan_{title.lower()}")),
            class_name=cta_class,
        ),
        class_name=card_class,
    )


def _faq_item(question: str, answer: str, open_by_default: bool = False) -> rx.Component:
    open_props = {"open": True} if open_by_default else {}
    return rx.el.details(
        rx.el.summary(
            rx.el.div(
                rx.icon("circle-help", class_name="h-4 w-4 text-emerald-700"),
                rx.el.p(question, class_name="text-sm font-semibold text-slate-900"),
                class_name="flex items-center gap-2",
            ),
            rx.icon("chevron-right", class_name="faq-chevron h-4 w-4 text-slate-500"),
            class_name="flex cursor-pointer list-none items-center justify-between gap-3",
        ),
        rx.el.p(answer, class_name="mt-3 text-sm leading-relaxed text-slate-600"),
        class_name=(
            "faq-item glow-card rounded-xl border border-slate-200 bg-white p-4 transition-all "
            "duration-200 open:border-emerald-200 open:shadow-sm"
        ),
        **open_props,
    )


def _footer_link(
    label: str,
    href: str,
    event_name: str,
    source: str,
    external: bool = False,
) -> rx.Component:
    return rx.el.a(
        label,
        href=href,
        target="_blank" if external else None,
        rel="noopener noreferrer" if external else None,
        on_click=rx.call_script(_track_event_script(event_name, source)),
        class_name="text-sm text-slate-600 transition-colors duration-150 hover:text-slate-900",
    )


def marketing_page() -> rx.Component:
    """Página de marketing y landing page pública."""
    demo_link = _wa_link("Hola, quiero una demo en vivo de TUWAYKIAPP.")
    local_link = _wa_link("Hola, me interesa TUWAYKIAPP en modalidad Local (pago anual). Quiero coordinar precio y detalles.")
    standard_link = _wa_link("Hola, quiero el Plan Standard (USD 45/mes) de TUWAYKIAPP.")
    professional_link = _wa_link("Hola, quiero el Plan Professional (USD 75/mes) de TUWAYKIAPP.")
    enterprise_link = _wa_link("Hola, quiero el Plan Enterprise (USD 175/mes) de TUWAYKIAPP.")

    trust_badges = [
        ("building-2", "Multiempresa real"),
        ("shield-check", "Permisos y seguridad"),
        ("wallet", "Cobros y caja unificados"),
        ("bar-chart-3", "Reportes accionables"),
    ]

    logos = [
        ("RM", "Rivera Market", "Retail multi-caja"),
        ("NS", "Nova Sports", "Reservas deportivas"),
        ("AB", "Alfa Bodega", "Inventario intensivo"),
        ("CN", "Centro Nexus", "Operacion multi-sucursal"),
        ("SP", "ServiPlus", "Servicios y cobranzas"),
    ]

    modules = [
        {
            "icon": "shopping-cart",
            "title": "Punto de venta",
            "description": "Cobros rapidos, tickets y trazabilidad completa por usuario.",
            "bullets": [
                "Pagos efectivos, tarjeta y transferencia",
                "Descuento de stock automatico",
                "Historial de transacciones por sucursal",
            ],
        },
        {
            "icon": "package",
            "title": "Inventario inteligente",
            "description": "Control por sucursal con alertas y movimientos auditables.",
            "bullets": [
                "Categorias, unidades y valorizacion",
                "Stock minimo y sugerencias de reposicion",
                "Kardex con trazabilidad de ajustes",
            ],
        },
        {
            "icon": "calendar-plus",
            "title": "Reservas y servicios",
            "description": "Agenda operativa con adelantos y cobro final desde la misma plataforma.",
            "bullets": [
                "Reservas por horario y estado",
                "Cobro parcial y total",
                "Menos huecos en agenda",
            ],
        },
        {
            "icon": "wallet",
            "title": "Gestion de caja",
            "description": "Apertura, cierre y auditoria diaria con evidencia de movimientos.",
            "bullets": [
                "Arqueo y diferencias visibles",
                "Ingresos/egresos con motivo",
                "Control por turno y responsable",
            ],
        },
        {
            "icon": "users",
            "title": "Usuarios y permisos",
            "description": "Aislamiento multi-tenant con roles claros por empresa y sucursal.",
            "bullets": [
                "Perfiles por funcion",
                "Acceso por modulo",
                "Escala con control sin perder seguridad",
            ],
        },
        {
            "icon": "pie-chart",
            "title": "Reportes ejecutivos",
            "description": "Indicadores por periodo y categoria para decidir con datos.",
            "bullets": [
                "Dashboards por sucursal",
                "Top productos y categorias",
                "Lectura rapida de rentabilidad",
            ],
        },
    ]

    steps = [
        ("01", "Activa tu cuenta", "Creas empresa, sucursal inicial y credenciales de equipo."),
        ("02", "Configura operacion", "Moneda, catalogo, permisos y reglas de trabajo."),
        ("03", "Empieza a vender", "Registras ventas y cobros con trazabilidad automatica."),
        ("04", "Controla en tiempo real", "Caja, stock y reservas conectadas en una sola vista."),
        ("05", "Escala con datos", "Usas reportes para optimizar procesos y crecer con orden."),
    ]

    testimonials = [
        (
            "CM",
            "Carla Mendez",
            "Gerente de operaciones - Retail",
            "Reducimos retrabajo en caja y hoy cerramos cada turno con mucha mas claridad.",
        ),
        (
            "JL",
            "Jorge Luna",
            "Director - Negocio de servicios",
            "Reservas + cobros en un mismo flujo nos devolvio control y previsibilidad.",
        ),
        (
            "PA",
            "Paola Alvarez",
            "COO - Operacion multi-sucursal",
            "Con permisos por rol y reportes por sede, delegamos mejor sin perder control.",
        ),
    ]

    faq_items = [
        (
            "Cuanto tarda implementarlo?",
            "Puedes comenzar el mismo dia. El onboarding inicial toma minutos y luego escalas por modulos.",
        ),
        (
            "Necesito tarjeta para el trial?",
            "No. Puedes activar la prueba gratis sin tarjeta y validar el flujo completo.",
        ),
        (
            "Sirve para varias empresas o sucursales?",
            "Si. Es multi-tenant y permite operar empresas/sucursales con aislamiento de informacion.",
        ),
        (
            "Puedo vender productos y servicios en el mismo sistema?",
            "Si. Integra punto de venta, reservas, adelantos, cobro final e impacto en caja.",
        ),
        (
            "Que incluye el soporte?",
            "Incluye acompanamiento funcional, resolucion de dudas y guia para una adopcion ordenada.",
        ),
        (
            "Que pasa cuando termina el trial?",
            "Eliges Standard, Professional o Enterprise y continuas sin perder tu configuracion.",
        ),
    ]

    ticker_nodes = [
        _logo_chip(mark, name, segment)
        for _ in range(2)
        for mark, name, segment in logos
    ]

    return rx.el.div(
        rx.el.style(_global_styles()),
        rx.el.script(_analytics_bootstrap_script()),
        rx.el.script(_ui_bootstrap_script()),
        rx.el.header(
            rx.el.div(
                rx.el.a(
                    rx.icon("box", class_name="h-7 w-7 text-indigo-600"),
                    rx.el.span("TUWAYKIAPP", class_name="text-xl font-extrabold tracking-tight text-slate-900"),
                    href="/",
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
                        href="/ingreso",
                        on_click=rx.call_script(_track_event_script("click_nav_login", "header_nav")),
                        class_name=(
                            "hidden items-center justify-center rounded-xl border-2 border-indigo-600 bg-white px-4 py-2 text-sm "
                            "font-semibold text-indigo-600 transition-colors duration-150 hover:bg-indigo-50 md:inline-flex"
                        ),
                    ),
                    rx.el.a(
                        "Iniciar prueba gratis",
                        href="/registro",
                        on_click=rx.call_script(_track_event_script("click_trial_cta", "header_primary_cta")),
                        class_name=(
                            "hidden items-center justify-center rounded-xl bg-emerald-600 px-4 py-2 text-sm "
                            "font-semibold text-white transition-colors duration-150 hover:bg-emerald-700 md:inline-flex"
                        ),
                    ),
                    class_name="hidden items-center gap-3 md:flex",
                ),
                rx.el.details(
                    rx.el.summary(
                        rx.icon("menu", class_name="h-5 w-5 text-slate-700"),
                        class_name=(
                            "inline-flex h-10 w-10 cursor-pointer items-center justify-center rounded-lg border "
                            "border-slate-200 bg-white md:hidden"
                        ),
                    ),
                    rx.el.div(
                        _nav_link("Modulos", "#modulos", "click_nav_modulos_mobile", "mobile_menu"),
                        _nav_link("Como funciona", "#como-funciona", "click_nav_como_funciona_mobile", "mobile_menu"),
                        _nav_link("Planes", "#planes", "click_nav_planes_mobile", "mobile_menu"),
                        _nav_link("FAQ", "#faq", "click_nav_faq_mobile", "mobile_menu"),
                        rx.el.a(
                            "Ingresar",
                            href="/ingreso",
                            on_click=rx.call_script(
                                _track_event_script("click_nav_login_mobile", "mobile_menu")
                            ),
                            class_name=(
                                "inline-flex w-full items-center justify-center rounded-xl border-2 border-indigo-600 "
                                "px-4 py-2 text-sm font-semibold text-indigo-600 hover:bg-indigo-50"
                            ),
                        ),
                        rx.el.a(
                            "Iniciar prueba gratis",
                            href="/registro",
                            on_click=rx.call_script(
                                _track_event_script("click_trial_cta", "mobile_menu_primary_cta")
                            ),
                            class_name=(
                                "inline-flex w-full items-center justify-center rounded-xl bg-emerald-600 "
                                "px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
                            ),
                        ),
                        class_name=(
                            "absolute right-0 mt-3 w-64 rounded-xl border border-slate-200 bg-white p-3 "
                            "shadow-lg md:hidden"
                        ),
                    ),
                    class_name="relative md:hidden",
                ),
                class_name="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8",
            ),
            class_name="glass-nav sticky top-0 z-50 border-b border-slate-200/80",
        ),
        rx.el.main(
            rx.el.section(
                rx.el.div(
                    rx.el.div(class_name="mesh-bg absolute inset-0"),
                    rx.el.div(
                        rx.el.div(
                            rx.el.span(
                                "SaaS multiempresa para ventas, servicios y reservas",
                                class_name=(
                                    "inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 "
                                    "text-xs font-semibold text-emerald-700"
                                ),
                            ),
                            rx.el.h1(
                                "Controla toda tu operacion comercial desde una sola plataforma.",
                                class_name=(
                                    "mt-4 text-3xl font-extrabold tracking-tight text-slate-900 "
                                    "sm:text-5xl sm:leading-tight"
                                ),
                            ),
                            rx.el.p(
                                "TUWAYKIAPP conecta punto de venta, caja, inventario y reservas para que tu equipo "
                                "trabaje mas rapido, con menos errores y con visibilidad real de resultados.",
                                class_name="mt-4 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg",
                            ),
                            rx.el.div(
                                *[_trust_pill(icon, label) for icon, label in trust_badges],
                                class_name="reveal-stagger mt-6 grid grid-cols-1 gap-2 sm:grid-cols-2",
                            ),
                            rx.el.div(
                                rx.el.a(
                                    "Comenzar trial de 15 dias",
                                    href="/registro",
                                    on_click=rx.call_script(
                                        _track_event_script("click_trial_cta", "hero_primary_cta")
                                    ),
                                    class_name=(
                                        "inline-flex items-center justify-center rounded-xl bg-slate-900 px-5 py-3 "
                                        "text-sm font-semibold text-white transition-colors duration-150 hover:bg-slate-800"
                                    ),
                                ),
                                rx.el.a(
                                    rx.icon("message-circle", class_name="h-4 w-4"),
                                    "Agendar demo guiada",
                                    href=demo_link,
                                    target="_blank",
                                    rel="noopener noreferrer",
                                    on_click=rx.call_script(
                                        _track_event_script("click_demo_cta", "hero_secondary_cta")
                                    ),
                                    class_name=(
                                        "inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-5 "
                                        "py-3 text-sm font-semibold text-slate-700 transition-colors duration-150 hover:bg-slate-50"
                                    ),
                                ),
                                class_name="mt-7 flex flex-col gap-3 sm:flex-row",
                            ),
                            class_name="reveal max-w-2xl",
                        ),
                        _hero_preview_card(),
                        class_name="relative z-10 grid grid-cols-1 items-start gap-8 lg:grid-cols-[1.02fr_0.98fr]",
                    ),
                    rx.el.div(
                        class_name=(
                            "orb-a pointer-events-none absolute -top-16 -left-16 h-56 w-56 rounded-full "
                            "bg-emerald-300/25 blur-3xl"
                        ),
                    ),
                    rx.el.div(
                        class_name=(
                            "orb-b pointer-events-none absolute top-16 -right-16 h-56 w-56 rounded-full "
                            "bg-sky-300/25 blur-3xl"
                        ),
                    ),
                    rx.el.div(
                        class_name=(
                            "orb-c pointer-events-none absolute bottom-0 left-1/2 h-48 w-48 -translate-x-1/2 "
                            "rounded-full bg-cyan-300/20 blur-3xl"
                        ),
                    ),
                    class_name=(
                        "relative mx-auto w-full max-w-6xl overflow-hidden rounded-3xl border border-slate-200/80 "
                        "px-4 pb-12 pt-12 shadow-sm sm:px-6 lg:px-10 lg:pt-14"
                    ),
                ),
                class_name="mx-auto w-full max-w-6xl px-4 pt-8 sm:px-6 lg:px-8",
            ),
            rx.el.section(
                rx.el.div(
                    _metric_card("+38%", "mejor visibilidad diaria", "Caja, ventas y reservas en una vista"),
                    _metric_card("-52%", "menos errores operativos", "Flujos estandarizados y trazables"),
                    _metric_card("15 dias", "trial gratuito", "Sin tarjeta, sin friccion"),
                    _metric_card("24/7", "acceso cloud", "Desktop, tablet y mobile"),
                    class_name="reveal-stagger grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4",
                ),
                class_name="relative z-20 mx-auto w-full max-w-6xl px-4 -mt-8 sm:px-6 lg:px-8",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.p(
                        "Empresas que ya validan su operacion con TUWAYKIAPP",
                        class_name="reveal text-xs font-semibold uppercase tracking-[0.18em] text-slate-500",
                    ),
                    rx.el.div(
                        rx.el.div(*ticker_nodes, class_name="ticker-track"),
                        class_name="ticker-wrap mt-6",
                    ),
                    class_name=(
                        "mx-auto w-full max-w-6xl rounded-3xl border border-slate-200 bg-white px-6 py-6 shadow-sm"
                    ),
                ),
                class_name="mx-auto w-full max-w-6xl px-4 pt-8 sm:px-6 lg:px-8",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.div(
                        rx.el.p(
                            "Problema vs solucion",
                            class_name="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500",
                        ),
                        rx.el.h2(
                            "Menos improvisacion operativa. Mas control comercial.",
                            class_name="mt-2 text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                        ),
                        rx.el.p(
                            "Visualiza el antes y despues cuando centralizas la operacion en una sola plataforma.",
                            class_name="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                        ),
                        class_name="reveal max-w-4xl",
                    ),
                    rx.el.div(
                        _comparison_card(
                            "Sin TUWAYKIAPP",
                            "triangle-alert",
                            [
                                "Caja, ventas y reservas en sistemas separados",
                                "Errores por doble carga y falta de trazabilidad",
                                "Decisiones tardias por falta de reportes claros",
                            ],
                            tone="negative",
                        ),
                        _comparison_card(
                            "Con TUWAYKIAPP",
                            "sparkles",
                            [
                                "Flujo unificado de venta, caja, stock y reservas",
                                "Datos consistentes por sucursal y por usuario",
                                "Reportes en tiempo real para actuar rapido",
                            ],
                            tone="positive",
                        ),
                        class_name="reveal-stagger mt-8 grid grid-cols-1 gap-4 lg:grid-cols-2",
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:px-8",
                ),
                class_name="mx-auto w-full max-w-6xl",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Modulos conectados para operar sin friccion",
                        class_name="reveal text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.p(
                        "Seis capacidades clave que trabajan juntas para sostener crecimiento y control.",
                        class_name="reveal mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                    ),
                    rx.el.div(
                        *[
                            _module_card(module["icon"], module["title"], module["description"], module["bullets"])
                            for module in modules
                        ],
                        class_name="reveal-stagger mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3",
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:px-8",
                    id="modulos",
                ),
                class_name="mx-auto w-full max-w-6xl",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Como funciona",
                        class_name="reveal text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.p(
                        "Implementacion en cinco pasos para salir a operar rapido.",
                        class_name="reveal mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                    ),
                    rx.el.div(
                        *[_timeline_step(step, title, detail) for step, title, detail in steps],
                        class_name="reveal-stagger mt-8 grid grid-cols-1 gap-3 md:grid-cols-2",
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:px-8",
                    id="como-funciona",
                ),
                class_name="mx-auto w-full max-w-6xl bg-slate-50",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Equipos que ya mejoraron su operacion",
                        class_name="reveal text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.p(
                        "Casos de uso reales en retail, servicios y operaciones multi-sucursal.",
                        class_name="reveal mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                    ),
                    rx.el.div(
                        *[
                            _testimonial_card(initials, name, role, quote)
                            for initials, name, role, quote in testimonials
                        ],
                        class_name="reveal-stagger mt-8 grid grid-cols-1 gap-4 md:grid-cols-3",
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:px-8",
                ),
                class_name="mx-auto w-full max-w-6xl",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Elige como quieres usar TUWAYKIAPP",
                        class_name="reveal text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.p(
                        "Dos modalidades, el mismo sistema completo. Elige la que mejor se adapte a tu negocio.",
                        class_name="reveal mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                    ),
                    # ── Tabs selector ──
                    rx.el.div(
                        rx.el.button(
                            rx.icon("cloud", class_name="h-4 w-4"),
                            "Servicio en la Nube",
                            id="tab-nube",
                            class_name="tab-btn active inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all duration-200 cursor-pointer",
                            on_click=rx.call_script(
                                "document.getElementById('panel-nube').style.display='block';"
                                "document.getElementById('panel-local').style.display='none';"
                                "document.getElementById('tab-nube').classList.add('active');"
                                "document.getElementById('tab-local').classList.remove('active');"
                            ),
                        ),
                        rx.el.button(
                            rx.icon("hard-drive", class_name="h-4 w-4"),
                            "Instalacion Local",
                            id="tab-local",
                            class_name="tab-btn inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all duration-200 cursor-pointer",
                            on_click=rx.call_script(
                                "document.getElementById('panel-local').style.display='block';"
                                "document.getElementById('panel-nube').style.display='none';"
                                "document.getElementById('tab-local').classList.add('active');"
                                "document.getElementById('tab-nube').classList.remove('active');"
                            ),
                        ),
                        class_name="reveal mt-8 inline-flex gap-2 rounded-xl bg-slate-100 p-1.5",
                    ),
                    # ── Panel NUBE ──
                    rx.el.div(
                        rx.el.div(
                            rx.el.div(
                                rx.el.div(
                                    rx.icon("check-circle", class_name="h-5 w-5 text-emerald-600"),
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
                                    rx.icon("alert-circle", class_name="h-5 w-5 text-amber-600"),
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
                            class_name="grid grid-cols-1 gap-4 sm:grid-cols-2 mt-6",
                        ),
                        rx.el.div(
                            rx.el.p("Planes disponibles", class_name="text-lg font-bold text-slate-900 mb-4"),
                            rx.el.div(
                                _plan_card(
                                    "Standard",
                                    "Ideal para negocios que quieren orden operativo desde el inicio.",
                                    "$45",
                                    [
                                        "Hasta 5 sucursales",
                                        "Hasta 10 usuarios",
                                        "Punto de venta + caja + inventario",
                                        "Reportes base y soporte comercial",
                                    ],
                                    "Elegir Standard",
                                    standard_link,
                                    "click_plan_standard",
                                    tone="standard",
                                ),
                                _plan_card(
                                    "Professional",
                                    "Para operaciones de mayor volumen y necesidad de control avanzado.",
                                    "$75",
                                    [
                                        "Hasta 10 sucursales",
                                        "Usuarios ilimitados",
                                        "Configuraciones avanzadas",
                                        "Prioridad de soporte",
                                        "Mayor profundidad de reportes",
                                    ],
                                    "Elegir Professional",
                                    professional_link,
                                    "click_plan_professional",
                                    tone="professional",
                                    badge_text="Mas elegido",
                                ),
                                _plan_card(
                                    "Enterprise",
                                    "Para companias con demanda de escala, personalizacion y SLA dedicado.",
                                    "$175",
                                    [
                                        "Plan personalizable por operacion",
                                        "Onboarding y arquitectura dedicada",
                                        "Integraciones y flujos a medida",
                                        "Acompanamiento prioritario",
                                        "Gobernanza enterprise",
                                    ],
                                    "Solicitar Enterprise",
                                    enterprise_link,
                                    "click_plan_enterprise",
                                    tone="enterprise",
                                    badge_text="Escala total",
                                ),
                                class_name="reveal-stagger grid grid-cols-1 items-stretch gap-4 lg:grid-cols-3",
                            ),
                            class_name="mt-6",
                        ),
                        id="panel-nube",
                        style={"display": "block"},
                    ),
                    # ── Panel LOCAL ──
                    rx.el.div(
                        rx.el.div(
                            rx.el.div(
                                rx.el.div(
                                    rx.icon("check-circle", class_name="h-5 w-5 text-emerald-600"),
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
                                    rx.icon("alert-circle", class_name="h-5 w-5 text-amber-600"),
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
                            class_name="grid grid-cols-1 gap-4 sm:grid-cols-2 mt-6",
                        ),
                        rx.el.div(
                            rx.el.article(
                                rx.el.span(
                                    "Pago unico",
                                    class_name="inline-flex rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700",
                                ),
                                rx.el.h3("Licencia Local", class_name="mt-2 text-lg font-bold text-slate-900"),
                                rx.el.p(
                                    "Instalamos el sistema en tu equipo. Un solo pago anual con soporte incluido.",
                                    class_name="mt-2 text-sm text-slate-600",
                                ),
                                rx.el.div(
                                    rx.el.p(
                                        "Consultar",
                                        class_name="mt-4 text-4xl font-extrabold tracking-tight text-slate-900",
                                    ),
                                    rx.el.p(
                                        "USD / pago anual",
                                        class_name="text-xs font-semibold uppercase tracking-wide text-slate-500",
                                    ),
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
                                    href=local_link,
                                    target="_blank",
                                    rel="noopener noreferrer",
                                    on_click=rx.call_script(
                                        _track_event_script("click_plan_local", "plan_local")
                                    ),
                                    class_name=(
                                        "mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl "
                                        "bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white "
                                        "transition-colors duration-150 hover:bg-indigo-700"
                                    ),
                                ),
                                class_name=(
                                    "glow-card rounded-2xl border border-indigo-200 ring-2 ring-indigo-400 "
                                    "bg-white p-6 shadow-sm transition-all duration-200 hover:-translate-y-1 "
                                    "hover:shadow-xl max-w-md mx-auto"
                                ),
                            ),
                            class_name="mt-6",
                        ),
                        id="panel-local",
                        style={"display": "none"},
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:px-8",
                    id="planes",
                ),
                class_name="mx-auto w-full max-w-6xl",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Preguntas frecuentes",
                        class_name="reveal text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.div(
                        *[
                            _faq_item(question, answer, open_by_default=index == 0)
                            for index, (question, answer) in enumerate(faq_items)
                        ],
                        class_name="reveal-stagger mt-7 grid grid-cols-1 gap-3 md:grid-cols-2",
                    ),
                    rx.el.div(
                        rx.el.div(
                            rx.el.p(
                                "Aun tienes dudas antes de activar tu trial?",
                                class_name="text-base font-semibold text-slate-900",
                            ),
                            rx.el.p(
                                "Nuestro equipo te ayuda a elegir plan y a estimar implementacion segun tu operacion.",
                                class_name="mt-1 text-sm text-slate-600",
                            ),
                            class_name="flex-1",
                        ),
                        rx.el.div(
                            rx.el.a(
                                "Hablar por WhatsApp",
                                href=demo_link,
                                target="_blank",
                                rel="noopener noreferrer",
                                on_click=rx.call_script(
                                    _track_event_script("click_demo_cta", "faq_whatsapp_cta")
                                ),
                                class_name=(
                                    "inline-flex items-center justify-center rounded-xl bg-emerald-600 px-4 py-2.5 "
                                    "text-sm font-semibold text-white transition-colors duration-150 hover:bg-emerald-700"
                                ),
                            ),
                            rx.el.a(
                                "Iniciar prueba",
                                href="/registro",
                                on_click=rx.call_script(
                                    _track_event_script("click_trial_cta", "faq_trial_cta")
                                ),
                                class_name=(
                                    "inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white "
                                    "px-4 py-2.5 text-sm font-semibold text-slate-700 transition-colors duration-150 hover:bg-slate-50"
                                ),
                            ),
                            class_name="flex flex-col gap-2 sm:flex-row",
                        ),
                        class_name=(
                            "reveal mt-7 flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 "
                            "sm:flex-row sm:items-center sm:justify-between"
                        ),
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:px-8",
                    id="faq",
                ),
                class_name="mx-auto w-full max-w-6xl bg-slate-50",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            class_name=(
                                "pointer-events-none orb-a absolute -top-10 -left-10 h-36 w-36 rounded-full "
                                "bg-emerald-400/25 blur-2xl"
                            ),
                        ),
                        rx.el.div(
                            class_name=(
                                "pointer-events-none orb-b absolute -bottom-10 -right-10 h-36 w-36 rounded-full "
                                "bg-sky-400/20 blur-2xl"
                            ),
                        ),
                        rx.el.h2(
                            "Listo para profesionalizar tu operacion comercial?",
                            class_name="text-2xl font-extrabold tracking-tight text-white sm:text-3xl",
                        ),
                        rx.el.p(
                            "Activa tu prueba gratis y centraliza ventas, inventario, caja y reservas desde hoy.",
                            class_name="mt-3 max-w-2xl text-sm leading-relaxed text-slate-200 sm:text-base",
                        ),
                        rx.el.div(
                            rx.el.a(
                                "Crear cuenta ahora",
                                href="/registro",
                                on_click=rx.call_script(
                                    _track_event_script("click_trial_cta", "bottom_banner_primary_cta")
                                ),
                                class_name=(
                                    "inline-flex items-center justify-center rounded-xl bg-emerald-500 px-5 py-3 "
                                    "text-sm font-semibold text-white transition-colors duration-150 hover:bg-emerald-400"
                                ),
                            ),
                            rx.el.a(
                                "Agendar demo",
                                href=demo_link,
                                target="_blank",
                                rel="noopener noreferrer",
                                on_click=rx.call_script(
                                    _track_event_script("click_demo_cta", "bottom_banner_secondary_cta")
                                ),
                                class_name=(
                                    "inline-flex items-center justify-center rounded-xl border border-slate-500 px-5 py-3 "
                                    "text-sm font-semibold text-slate-100 transition-colors duration-150 hover:bg-slate-800"
                                ),
                            ),
                            class_name="mt-6 flex flex-col gap-3 sm:flex-row",
                        ),
                        class_name=(
                            "reveal relative mx-auto w-full max-w-6xl overflow-hidden rounded-3xl bg-slate-900 px-6 py-10 sm:px-10"
                        ),
                    ),
                ),
                class_name="mx-auto w-full max-w-6xl px-4 pb-12 sm:px-6 lg:px-8",
            ),
            class_name="relative mx-auto w-full",
        ),
        rx.el.footer(
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.a(
                            rx.icon("box", class_name="h-7 w-7 text-indigo-600"),
                            rx.el.span("TUWAYKIAPP", class_name="text-lg font-extrabold tracking-tight text-slate-900"),
                            href="/",
                            class_name="inline-flex items-center gap-2.5",
                        ),
                        rx.el.p(
                            "Sistema de ventas SaaS para negocios multi-sucursal con enfoque en control real.",
                            class_name="mt-3 max-w-xs text-sm text-slate-600",
                        ),
                        rx.el.a(
                            "WhatsApp +5491168376517",
                            href=f"https://wa.me/{WHATSAPP_NUMBER}",
                            target="_blank",
                            rel="noopener noreferrer",
                            on_click=rx.call_script(
                                _track_event_script("click_whatsapp_cta", "footer_contact")
                            ),
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
                        _footer_link(
                            "Agendar demo",
                            demo_link,
                            "click_footer_demo",
                            "footer_empresa",
                            external=True,
                        ),
                        _footer_link(
                            "Hablar con ventas",
                            demo_link,
                            "click_footer_sales",
                            "footer_empresa",
                            external=True,
                        ),
                        _footer_link(
                            "Soporte",
                            demo_link,
                            "click_footer_support",
                            "footer_empresa",
                            external=True,
                        ),
                        class_name="flex flex-col gap-2",
                    ),
                    rx.el.div(
                        rx.el.h4("Accesos", class_name="text-sm font-bold text-slate-900"),
                        _footer_link("Iniciar sesion", "/ingreso", "click_footer_login", "footer_accesos"),
                        _footer_link("Crear cuenta", "/registro", "click_footer_signup", "footer_accesos"),
                        _footer_link(
                            "WhatsApp directo",
                            f"https://wa.me/{WHATSAPP_NUMBER}",
                            "click_footer_whatsapp",
                            "footer_accesos",
                            external=True,
                        ),
                        class_name="flex flex-col gap-2",
                    ),
                    class_name="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-4",
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.p(
                            "TUWAYKIAPP \u00a9 2026. Todos los derechos reservados.",
                            class_name="text-sm text-slate-500",
                        ),
                        rx.el.p(
                            "Hecho con foco en escalabilidad, operacion y crecimiento comercial.",
                            class_name="text-sm text-slate-500",
                        ),
                    ),
                    rx.el.div(
                        rx.el.p("Creado por", class_name="text-xs text-slate-400 uppercase tracking-wider"),
                        rx.el.a(
                            "Trebor Oscorima ",
                            rx.el.span("\ud83e\uddc9\u26bd\ufe0f", class_name="ml-1"),
                            href="https://www.facebook.com/trebor.oscorima/?locale=es_LA",
                            target="_blank",
                            rel="noopener noreferrer",
                            class_name="text-sm font-semibold text-slate-700 hover:text-indigo-600 transition-colors",
                        ),
                        rx.el.a(
                            rx.icon("message-circle", class_name="h-3.5 w-3.5"),
                            "+5491168376517",
                            href="https://wa.me/5491168376517",
                            target="_blank",
                            rel="noopener noreferrer",
                            class_name="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600 hover:text-emerald-700 transition-colors",
                        ),
                        class_name="flex flex-col gap-0.5 items-end",
                    ),
                    class_name="mt-8 flex flex-col items-start justify-between gap-4 border-t border-slate-200 pt-4 sm:flex-row sm:items-center",
                ),
                class_name="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8",
            ),
            class_name="border-t border-slate-200 bg-white",
        ),
        rx.el.a(
            rx.el.span(class_name="wa-pulse absolute inset-0"),
            rx.icon("message-circle", class_name="relative z-10 h-5 w-5"),
            rx.el.span("WhatsApp", class_name="relative z-10 hidden text-sm font-semibold sm:inline"),
            href=demo_link,
            target="_blank",
            rel="noopener noreferrer",
            on_click=rx.call_script(_track_event_script("click_whatsapp_cta", "floating_button")),
            class_name=(
                "fixed bottom-5 right-5 z-[60] inline-flex items-center gap-2 rounded-full bg-emerald-600 px-4 "
                "py-3 text-white shadow-lg transition-all duration-150 hover:-translate-y-0.5 hover:bg-emerald-700"
            ),
            aria_label="Contactar por WhatsApp",
        ),
        class_name="relative min-h-screen bg-gradient-to-b from-slate-50 via-cyan-50/30 to-slate-100",
        style={"fontFamily": "'Space Grotesk', 'Manrope', sans-serif"},
    )
