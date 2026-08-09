"""Script generators, JSON-LD and global CSS for the marketing landing page."""

import json

import reflex as rx

from ._state import GA4_MEASUREMENT_ID, META_PIXEL_ID, PUBLIC_SITE_URL, FAQ_ITEMS


def _jsonld_script(data: dict | list) -> rx.Component:
    # El JSON debe ir como hijo (texto) del <script>. Pasarlo por
    # `dangerously_set_inner_html` NO funciona en Reflex: se trata como estilo y
    # el <script> queda vacío (Google no ve datos estructurados). El JSON no
    # contiene `<`, `>` ni `&`, así que es seguro como nodo de texto.
    return rx.el.script(
        json.dumps(data, ensure_ascii=False),
        type="application/ld+json",
    )


def _jsonld_organization() -> dict:
    base = PUBLIC_SITE_URL or "https://tuwayki.app"
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "TUWAYKIAPP",
        "alternateName": ["TUWAYKI", "tuwayki.app"],
        "url": base,
        "logo": f"{base}/icon-512.png",
        "description": (
            "TUWAYKIAPP desarrolla software de gestión en la nube para distintas "
            "industrias: TUWAYKISHOP (ventas y multi-sucursal) y TUWAYKIFOOD "
            "(restaurantes y restobares)."
        ),
        "slogan": "Un sistema de gestión para cada tipo de negocio.",
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "sales",
            "availableLanguage": "Spanish",
        },
    }


def _jsonld_ventas_app() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "TUWAYKISHOP",
        "alternateName": ["Tuwaykishop", "TUWAYKI SHOP"],
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "description": (
            "TUWAYKISHOP es el sistema de ventas de TUWAYKIAPP: punto de venta, "
            "inventario, caja, reservas y reportes en una sola plataforma. Para "
            "tiendas, canchas, ferreterías y negocios multi-sucursal."
        ),
        "url": f"{PUBLIC_SITE_URL or 'https://tuwayki.app'}/shop/",
        "publisher": {
            "@type": "Organization",
            "name": "TUWAYKIAPP",
            "url": PUBLIC_SITE_URL or "https://tuwayki.app",
        },
        "offers": {
            "@type": "AggregateOffer",
            "priceCurrency": "USD",
            "lowPrice": "35",
            "highPrice": "175",
            "offerCount": "3",
        },
    }


def _jsonld_food_app() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "TUWAYKIFOOD",
        "alternateName": ["Tuwaykifood", "TUWAYKI FOOD"],
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "description": (
            "TUWAYKIFOOD es el sistema para restaurantes y restobares de TUWAYKIAPP: "
            "carta digital con QR, gestión de mesas, pedidos por tablet y comanda "
            "automática en cocina."
        ),
        "url": f"{PUBLIC_SITE_URL or 'https://tuwayki.app'}/food/",
        "publisher": {
            "@type": "Organization",
            "name": "TUWAYKIAPP",
            "url": PUBLIC_SITE_URL or "https://tuwayki.app",
        },
    }


def _jsonld_life_app() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "TUWAYKILIFE",
        "alternateName": ["Tuwaykilife", "TUWAYKI LIFE"],
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "description": (
            "TUWAYKILIFE es el sistema para clínicas y consultorios de TUWAYKIAPP: "
            "agenda y turnos, historia clínica, pacientes, punto de cobro y caja, "
            "multi-especialidad y multi-sucursal."
        ),
        "url": f"{PUBLIC_SITE_URL or 'https://tuwayki.app'}/life/",
        "publisher": {
            "@type": "Organization",
            "name": "TUWAYKIAPP",
            "url": PUBLIC_SITE_URL or "https://tuwayki.app",
        },
    }


def _jsonld_faq(items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in items
        ],
    }


def _jsonld_breadcrumbs(items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": name,
                "item": url,
            }
            for i, (name, url) in enumerate(items)
        ],
    }


def ventas_jsonld_components() -> list[rx.Component]:
    base = PUBLIC_SITE_URL or "https://tuwayki.app"
    return [
        _jsonld_script(_jsonld_organization()),
        _jsonld_script(_jsonld_ventas_app()),
        _jsonld_script(_jsonld_faq(FAQ_ITEMS)),
        _jsonld_script(_jsonld_breadcrumbs([
            ("Inicio", f"{base}/"),
            ("Sistema de Ventas", f"{base}/shop/"),
        ])),
    ]


def food_jsonld_components() -> list[rx.Component]:
    from ._food_sections import FOOD_FAQ_ITEMS as _food_faq
    base = PUBLIC_SITE_URL or "https://tuwayki.app"
    return [
        _jsonld_script(_jsonld_organization()),
        _jsonld_script(_jsonld_food_app()),
        _jsonld_script(_jsonld_faq(_food_faq)),
        _jsonld_script(_jsonld_breadcrumbs([
            ("Inicio", f"{base}/"),
            ("TUWAYKIFOOD", f"{base}/food/"),
        ])),
    ]


def life_jsonld_components() -> list[rx.Component]:
    from ._life_sections import LIFE_FAQ_ITEMS as _life_faq
    base = PUBLIC_SITE_URL or "https://tuwayki.app"
    return [
        _jsonld_script(_jsonld_organization()),
        _jsonld_script(_jsonld_life_app()),
        _jsonld_script(_jsonld_faq(_life_faq)),
        _jsonld_script(_jsonld_breadcrumbs([
            ("Inicio", f"{base}/"),
            ("TUWAYKILIFE", f"{base}/life/"),
        ])),
    ]


def home_jsonld_components() -> list[rx.Component]:
    base = PUBLIC_SITE_URL or "https://tuwayki.app"
    return [
        _jsonld_script(_jsonld_organization()),
        _jsonld_script({
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "TUWAYKIAPP",
            "alternateName": ["TUWAYKI", "tuwayki.app"],
            "url": base,
        }),
        # Declara los productos en el home para que Google asocie la empresa
        # con cada sistema (TUWAYKISHOP / TUWAYKIFOOD).
        _jsonld_script(_jsonld_ventas_app()),
        _jsonld_script(_jsonld_food_app()),
        _jsonld_script({
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": "Sistemas de TUWAYKIAPP",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "TUWAYKISHOP — Sistema de Ventas",
                    "url": f"{base}/shop/",
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "TUWAYKIFOOD — Sistema para Restobares",
                    "url": f"{base}/food/",
                },
            ],
        }),
    ]


def _sw_cleanup_script() -> str:
    """Unregister any service worker on the landing page.
    Landing is marketing-only — no offline need. A stale SW causes
    unstyled pages after deploys (cache-first HTML served from old cache).
    This runs once and is a no-op if no SW is registered.
    """
    return (
        "if('serviceWorker' in navigator){"
        "navigator.serviceWorker.getRegistrations().then(function(regs){"
        "regs.forEach(function(r){r.unregister();});"
        "});}"
    )


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
        # Close mobile menu when any hash link is clicked
        "document.addEventListener('click',function(e){"
        "var link=e.target.closest('a[href^=\"#\"]');"
        "if(link){var d=document.querySelector('header details');if(d)d.removeAttribute('open');}"
        "});"
    )


# ── Styles (minimal) ────────────────────────────────────────
def _global_styles() -> str:
    return """
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
.twk-tab-panel { display: none !important; }
.twk-tab-panel.active { display: grid !important; }
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
/* Hero section gradient background */
.hero-section {
  background: linear-gradient(160deg, #ffffff 0%, #eef2ff 40%, #f0fdf4 100%);
  position: relative;
}
.hero-section::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
  background-size: 28px 28px;
  opacity: 0.45;
  pointer-events: none;
}
/* Ensure hero content sits above the dot grid */
.hero-section > * { position: relative; }
"""
