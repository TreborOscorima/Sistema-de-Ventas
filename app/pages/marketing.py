import reflex as rx
import os


GA4_MEASUREMENT_ID = (os.getenv("GA4_MEASUREMENT_ID") or "").strip()
META_PIXEL_ID = (os.getenv("META_PIXEL_ID") or "").strip()


def _nav_link(label: str, href: str) -> rx.Component:
    return rx.el.a(
        label,
        href=href,
        class_name=(
            "text-sm font-medium text-slate-600 hover:text-slate-900 "
            "transition-colors duration-150"
        ),
    )


def _metric_card(value: str, label: str) -> rx.Component:
    return rx.el.div(
        rx.el.p(value, class_name="text-2xl sm:text-3xl font-extrabold text-slate-900"),
        rx.el.p(label, class_name="text-xs sm:text-sm text-slate-600"),
        class_name=(
            "rounded-2xl border border-slate-200/80 bg-white/90 backdrop-blur px-4 py-4 shadow-sm "
            "transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        ),
    )


def _module_card(icon: str, title: str, description: str, outcome: str) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            class_name="h-1 w-16 rounded-full bg-gradient-to-r from-emerald-400 to-cyan-400",
        ),
        rx.el.div(
            rx.icon(icon, class_name="h-5 w-5 text-emerald-700"),
            class_name="inline-flex items-center justify-center rounded-xl bg-emerald-100 p-2",
        ),
        rx.el.h3(title, class_name="mt-4 text-base font-bold text-slate-900"),
        rx.el.p(description, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
        rx.el.div(
            rx.icon("badge-check", class_name="h-4 w-4 text-emerald-700"),
            rx.el.p(outcome, class_name="text-sm font-medium text-slate-700"),
            class_name="mt-4 flex items-start gap-2",
        ),
        class_name=(
            "group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm "
            "transition-all duration-200 hover:-translate-y-1 hover:shadow-lg hover:border-emerald-200"
        ),
    )


def _clarity_card(title: str, detail: str, points: list[str]) -> rx.Component:
    point_rows = [
        rx.el.li(
            rx.icon("badge-check", class_name="h-4 w-4 text-emerald-700"),
            rx.el.span(point, class_name="text-sm text-slate-700"),
            class_name="flex items-start gap-2",
        )
        for point in points
    ]

    return rx.el.article(
        rx.el.h3(title, class_name="text-lg font-bold text-slate-900"),
        rx.el.p(detail, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
        rx.el.ul(*point_rows, class_name="mt-4 space-y-2"),
        class_name=(
            "rounded-2xl border border-slate-200 bg-white p-5 shadow-sm "
            "transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        ),
    )


def _step_card(step: str, title: str, detail: str) -> rx.Component:
    return rx.el.div(
        rx.el.span(
            step,
            class_name=(
                "inline-flex h-8 w-8 items-center justify-center rounded-full "
                "bg-slate-900 text-xs font-bold text-white"
            ),
        ),
        rx.el.div(
            rx.el.h3(title, class_name="text-base font-semibold text-slate-900"),
            rx.el.p(detail, class_name="mt-1 text-sm text-slate-600"),
            class_name="flex-1",
        ),
        class_name=(
            "flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 "
            "transition-all duration-200 hover:border-slate-300 hover:shadow-sm"
        ),
    )


def _plan_card(
    title: str,
    subtitle: str,
    points: list[str],
    price_label: str,
    cta_label: str,
    cta_href: str,
    tone: str = "standard",
    badge_text: str = "",
) -> rx.Component:
    is_enterprise = tone == "enterprise"
    is_professional = tone == "professional"

    card_class = (
        "rounded-2xl border bg-white p-6 shadow-sm transition-all duration-200 "
        "hover:-translate-y-1 hover:shadow-xl"
    )
    subtitle_class = "mt-2 text-sm text-slate-600"
    point_text_class = "text-sm text-slate-700"
    check_color = "text-emerald-700"
    cta_class = (
        "mt-6 inline-flex w-full items-center justify-center rounded-xl bg-slate-900 px-4 "
        "py-2.5 text-sm font-semibold text-white hover:bg-slate-800 transition-colors duration-150"
    )

    if is_professional:
        card_class += " ring-2 ring-emerald-400 border-emerald-200"
    else:
        card_class += " border-slate-200"

    if is_enterprise:
        card_class = (
            "rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-lg transition-all "
            "duration-200 hover:-translate-y-1 hover:shadow-2xl"
        )
        subtitle_class = "mt-2 text-sm text-slate-300"
        point_text_class = "text-sm text-slate-200"
        check_color = "text-emerald-300"
        cta_class = (
            "mt-6 inline-flex w-full items-center justify-center rounded-xl bg-emerald-500 px-4 "
            "py-2.5 text-sm font-semibold text-white hover:bg-emerald-400 transition-colors duration-150"
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

    point_rows = [
        rx.el.li(
            rx.icon("check", class_name=f"h-4 w-4 {check_color}"),
            rx.el.span(point, class_name=point_text_class),
            class_name="flex items-start gap-2",
        )
        for point in points
    ]

    price_block = (
        rx.el.div(
            rx.el.p(
                price_label,
                class_name=(
                    "mt-4 text-3xl font-extrabold tracking-tight text-white"
                    if is_enterprise
                    else "mt-4 text-3xl font-extrabold tracking-tight text-slate-900"
                ),
            ),
            rx.el.p(
                "USD / mes",
                class_name="text-xs font-semibold uppercase tracking-wide text-slate-300"
                if is_enterprise
                else "text-xs font-semibold uppercase tracking-wide text-slate-500",
            ),
        )
        if price_label
        else rx.fragment()
    )

    return rx.el.article(
        badge,
        rx.el.h3(
            title,
            class_name="mt-2 text-lg font-bold text-white" if is_enterprise else "mt-2 text-lg font-bold text-slate-900",
        ),
        rx.el.p(subtitle, class_name=subtitle_class),
        price_block,
        rx.el.ul(*point_rows, class_name="mt-5 space-y-2"),
        rx.el.a(
            cta_label,
            href=cta_href,
            target="_blank" if cta_href.startswith("https://") else None,
            rel="noopener noreferrer" if cta_href.startswith("https://") else None,
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
            rx.icon("chevron-right", class_name="h-4 w-4 text-slate-500"),
            class_name="flex cursor-pointer list-none items-center justify-between gap-3",
        ),
        rx.el.p(answer, class_name="mt-3 text-sm leading-relaxed text-slate-600"),
        class_name=(
            "rounded-xl border border-slate-200 bg-white p-4 transition-all duration-200 "
            "open:border-emerald-200 open:shadow-sm"
        ),
        **open_props,
    )


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


def _trust_pill(icon: str, label: str) -> rx.Component:
    return rx.el.div(
        rx.icon(icon, class_name="h-4 w-4 text-emerald-700"),
        rx.el.span(label, class_name="text-xs font-semibold text-slate-700 sm:text-sm"),
        class_name=(
            "inline-flex items-center gap-2 rounded-xl border border-emerald-100 bg-white/90 "
            "px-3 py-2 shadow-sm backdrop-blur"
        ),
    )


def _client_logo(mark: str, name: str, segment: str) -> rx.Component:
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
            "inline-flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2 "
            "shadow-sm"
        ),
    )


def _hero_preview_card() -> rx.Component:
    return rx.el.aside(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    "Captura real del producto",
                    class_name="text-xs font-semibold uppercase tracking-wide text-slate-500",
                ),
                rx.el.h3(
                    "Dashboard operativo de TUWAYKIAPP",
                    class_name="mt-1 text-lg font-bold text-slate-900",
                ),
            ),
            rx.el.span(
                rx.icon("badge-check", class_name="h-4 w-4"),
                "Vista real",
                class_name=(
                    "inline-flex items-center gap-1 rounded-full border border-emerald-200 "
                    "bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700"
                ),
            ),
            class_name="flex items-start justify-between gap-4",
        ),
        rx.el.div(
            rx.el.div(
                src="/dashboard-hero-real.png",
                alt="Captura real del dashboard de TUWAYKIAPP",
                class_name="h-auto w-full object-cover",
            ),
            class_name=(
                "mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white "
                "shadow-[0_20px_45px_-30px_rgba(15,23,42,0.5)]"
            ),
        ),
        rx.el.div(
            rx.el.p(
                "Incluye: ventas, caja, categorias y alertas en una sola vista",
                class_name="text-xs font-semibold uppercase tracking-wide text-slate-500",
            ),
            rx.el.div(
                rx.el.div(
                    rx.icon("bar-chart-3", class_name="h-4 w-4 text-indigo-600"),
                    rx.el.span(
                        "Metricas en tiempo real",
                        class_name="text-xs font-medium text-slate-700",
                    ),
                    class_name="grid grid-cols-[auto_1fr_auto] items-center gap-2 rounded-lg bg-white px-3 py-2",
                ),
                rx.el.div(
                    rx.icon("calendar-check", class_name="h-4 w-4 text-cyan-600"),
                    rx.el.span(
                        "Flujos de reserva y cobro",
                        class_name="text-xs font-medium text-slate-700",
                    ),
                    class_name="grid grid-cols-[auto_1fr] items-center gap-2 rounded-lg bg-white px-3 py-2",
                ),
                rx.el.div(
                    rx.icon("badge-check", class_name="h-4 w-4 text-emerald-700"),
                    rx.el.span(
                        "Control por sucursal y tenant",
                        class_name="text-xs font-medium text-slate-700",
                    ),
                    class_name="grid grid-cols-[auto_1fr] items-center gap-2 rounded-lg bg-white px-3 py-2",
                ),
                class_name="mt-3 space-y-2",
            ),
            class_name="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3",
        ),
        class_name=(
            "float-card relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white/95 p-5 "
            "shadow-[0_30px_80px_-35px_rgba(15,23,42,0.45)] backdrop-blur"
        ),
    )


def _testimonial_card(quote: str, role: str) -> rx.Component:
    return rx.el.article(
        rx.el.p(
            f'"{quote}"',
            class_name="text-sm leading-relaxed text-slate-700",
        ),
        rx.el.div(
            rx.icon("message-circle", class_name="h-4 w-4 text-emerald-700"),
            rx.el.p(role, class_name="text-xs font-semibold uppercase tracking-wide text-slate-500"),
            class_name="mt-4 flex items-center gap-2",
        ),
        class_name=(
            "rounded-2xl border border-slate-200 bg-white p-5 shadow-sm "
            "transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        ),
    )


def marketing_page() -> rx.Component:
    demo_link = (
        "https://wa.me/5491168376517?text="
        "Hola,%20quiero%20una%20demo%20en%20vivo%20de%20TUWAYKIAPP."
    )
    standard_link = (
        "https://wa.me/5491168376517?text="
        "Hola,%20quiero%20el%20Plan%20Standard%20(USD%2045/mes)%20de%20TUWAYKIAPP."
    )
    professional_link = (
        "https://wa.me/5491168376517?text="
        "Hola,%20quiero%20el%20Plan%20Professional%20(USD%2075/mes)%20de%20TUWAYKIAPP."
    )
    enterprise_link = (
        "https://wa.me/5491168376517?text="
        "Hola,%20quiero%20el%20Plan%20Enterprise%20(USD%20175/mes)%20de%20TUWAYKIAPP."
    )

    return rx.el.div(
        rx.el.style(
            "@import url('https://fonts.googleapis.com/css2?"
            "family=Sora:wght@400;600;700;800&family=Public+Sans:wght@400;500;600&display=swap');"
            "@keyframes floatY{0%,100%{transform:translateY(0px);}50%{transform:translateY(-16px);}}"
            "@keyframes pulseSoft{0%,100%{opacity:.35;}50%{opacity:.7;}}"
            "@keyframes cardLift{0%,100%{transform:translateY(0px);}50%{transform:translateY(-6px);}}"
            ".orb-a{animation:floatY 10s ease-in-out infinite;}"
            ".orb-b{animation:floatY 13s ease-in-out infinite reverse;}"
            ".orb-c{animation:pulseSoft 8s ease-in-out infinite;}"
            ".float-card{animation:cardLift 8s ease-in-out infinite;}"
        ),
        rx.el.script(_analytics_bootstrap_script()),
        rx.el.div(
            rx.el.div(
                class_name=(
                    "orb-a absolute -top-32 -left-24 h-80 w-80 rounded-full bg-emerald-300/30 blur-3xl"
                ),
            ),
            rx.el.div(
                class_name=(
                    "orb-b absolute top-40 -right-24 h-80 w-80 rounded-full bg-sky-300/30 blur-3xl"
                ),
            ),
            rx.el.div(
                class_name=(
                    "orb-c absolute bottom-0 left-1/3 h-72 w-72 rounded-full bg-cyan-300/20 blur-3xl"
                ),
            ),
            class_name="pointer-events-none absolute inset-0 overflow-hidden",
        ),
        rx.el.header(
            rx.el.div(
                rx.el.a(
                    rx.icon("box", class_name="h-5 w-5 text-slate-900"),
                    rx.el.span("TUWAYKIAPP", class_name="font-bold text-slate-900"),
                    href="/sitio",
                    class_name="flex items-center gap-2",
                ),
                rx.el.nav(
                    _nav_link("Modulos", "#modulos"),
                    _nav_link("Planes", "#planes"),
                    _nav_link("FAQ", "#faq"),
                    _nav_link("Ingresar", "/"),
                    class_name="hidden items-center gap-6 md:flex",
                ),
                rx.el.a(
                    "Demo + Trial",
                    href="/registro",
                    on_click=rx.call_script(
                        _track_event_script("click_trial_cta", "header_demo_trial")
                    ),
                    class_name=(
                        "inline-flex items-center justify-center rounded-xl bg-emerald-600 "
                        "px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 "
                        "transition-colors duration-150"
                    ),
                ),
                class_name=(
                    "mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8"
                ),
            ),
            class_name=(
                "sticky top-0 z-50 border-b border-slate-200/70 bg-white/85 backdrop-blur supports-[backdrop-filter]:bg-white/75"
            ),
        ),
        rx.el.main(
            rx.el.section(
                rx.el.div(
                    rx.el.div(
                        rx.el.span(
                            "SaaS multiempresa para tiendas, servicios y reservas",
                            class_name=(
                                "inline-flex rounded-full border border-emerald-200 bg-emerald-50 "
                                "px-3 py-1 text-xs font-semibold text-emerald-700"
                            ),
                        ),
                        rx.el.h1(
                            "Convierte cada venta en control operativo y crecimiento rentable.",
                            class_name=(
                                "mt-4 text-3xl font-extrabold tracking-tight text-slate-900 "
                                "sm:text-5xl sm:leading-tight"
                            ),
                        ),
                        rx.el.p(
                            "TUWAYKIAPP conecta ventas, caja, inventario y servicios en un solo flujo "
                            "para que tu equipo cobre mas rapido, cometa menos errores y escale con control.",
                            class_name="mt-4 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg",
                        ),
                        rx.el.div(
                            rx.el.p(
                                "Incluye desde el primer dia:",
                                class_name="text-xs font-semibold uppercase tracking-wide text-slate-500",
                            ),
                            rx.el.div(
                                rx.icon("badge-check", class_name="h-4 w-4 text-emerald-700"),
                                rx.el.span("Punto de venta agil con multiples metodos de pago", class_name="text-sm text-slate-700"),
                                class_name="flex items-center gap-2",
                            ),
                            rx.el.div(
                                rx.icon("badge-check", class_name="h-4 w-4 text-emerald-700"),
                                rx.el.span("Inventario y caja con trazabilidad diaria", class_name="text-sm text-slate-700"),
                                class_name="flex items-center gap-2",
                            ),
                            rx.el.div(
                                rx.icon("badge-check", class_name="h-4 w-4 text-emerald-700"),
                                rx.el.span("Reservas y cobro de servicios en el mismo sistema", class_name="text-sm text-slate-700"),
                                class_name="flex items-center gap-2",
                            ),
                            rx.el.div(
                                rx.icon("badge-check", class_name="h-4 w-4 text-emerald-700"),
                                rx.el.span("Roles por tenant y operacion en desktop/tablet/mobile", class_name="text-sm text-slate-700"),
                                class_name="flex items-center gap-2",
                            ),
                            class_name="mt-5 space-y-2.5",
                        ),
                        rx.el.div(
                            rx.el.a(
                                "Comenzar trial de 15 dias",
                                href="/registro",
                                on_click=rx.call_script(
                                    _track_event_script(
                                        "click_trial_cta", "hero_primary_cta"
                                    )
                                ),
                                class_name=(
                                    "inline-flex items-center justify-center rounded-xl bg-slate-900 "
                                    "px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800 "
                                    "transition-colors duration-150"
                                ),
                            ),
                            rx.el.a(
                                rx.icon("message-circle", class_name="h-4 w-4"),
                                "Agendar demo guiada",
                                href=demo_link,
                                target="_blank",
                                rel="noopener noreferrer",
                                class_name=(
                                    "inline-flex items-center gap-2 rounded-xl border border-slate-300 "
                                    "bg-white px-5 py-3 text-sm font-semibold text-slate-700 "
                                    "hover:bg-slate-50 transition-colors duration-150"
                                ),
                            ),
                            class_name="mt-7 flex flex-col gap-3 sm:flex-row",
                        ),
                        rx.el.div(
                            _metric_card("+35%", "mejor control de caja diaria"),
                            _metric_card("-60%", "menos diferencias de stock"),
                            _metric_card("15 dias", "trial gratis sin tarjeta"),
                            class_name="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3",
                        ),
                        class_name="max-w-2xl",
                    ),
                    _hero_preview_card(),
                    class_name="grid grid-cols-1 items-start gap-8 lg:grid-cols-[1.05fr_0.95fr]",
                ),
                class_name="mx-auto w-full max-w-6xl px-4 pb-10 pt-14 sm:px-6 lg:px-8 lg:pt-16",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.div(
                        rx.el.p(
                            "Confiado para operaciones de alta exigencia",
                            class_name=(
                                "text-xs font-semibold uppercase tracking-[0.18em] text-slate-500"
                            ),
                        ),
                        rx.el.h3(
                            "Ideal para tiendas, negocios con reservas y operaciones multi-sucursal.",
                            class_name="mt-2 text-xl font-bold text-slate-900 sm:text-2xl",
                        ),
                    ),
                    rx.el.div(
                        _trust_pill("building-2", "Tiendas con punto de venta"),
                        _trust_pill("calendar-check", "Negocios con reservas y servicios"),
                        _trust_pill("users", "Equipos multiusuario y sucursales"),
                        _trust_pill("badge-check", "Roles y permisos por tenant"),
                        _trust_pill("pie-chart", "Reportes por periodo y categoria"),
                        class_name="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5",
                    ),
                    class_name=(
                        "mx-auto w-full max-w-6xl rounded-3xl border border-slate-200/80 bg-white/90 "
                        "p-6 shadow-sm backdrop-blur sm:p-8"
                    ),
                ),
                class_name="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.p(
                        "Empresas que ya prueban la plataforma",
                        class_name="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500",
                    ),
                    rx.el.div(
                        _client_logo("RM", "Rivera Market", "Retail multi-caja"),
                        _client_logo("NS", "Nova Sports", "Reservas deportivas"),
                        _client_logo("AB", "Alfa Bodega", "Inventario intensivo"),
                        _client_logo("CN", "Centro Nexus", "Operacion multi-sucursal"),
                        _client_logo("SP", "ServiPlus", "Servicios y cobranzas"),
                        class_name="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5",
                    ),
                    class_name=(
                        "mx-auto w-full max-w-6xl rounded-3xl border border-slate-200/80 bg-white "
                        "px-6 py-5 shadow-sm"
                    ),
                ),
                class_name="mx-auto w-full max-w-6xl px-4 pt-6 sm:px-6 lg:px-8",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Que resuelve TUWAYKIAPP en tu operacion diaria",
                        class_name="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.p(
                        "Un sistema unificado para vender, cobrar, controlar stock y gestionar servicios sin hojas de calculo.",
                        class_name="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                    ),
                    rx.el.div(
                        _clarity_card(
                            "Ventas y cobros",
                            "Registro rapido de ventas y cobro inmediato desde un solo punto.",
                            [
                                "POS rapido con codigo de barras o busqueda",
                                "Pagos efectivos, tarjeta, transferencias y mixtos",
                                "Tickets y movimientos de caja en un mismo flujo",
                            ],
                        ),
                        _clarity_card(
                            "Inventario y control",
                            "Stock actualizado por sucursal con alertas para evitar quiebres.",
                            [
                                "Categorias, unidades, variantes y ajuste de inventario",
                                "Control de stock bajo y valorizacion",
                                "Historial de ingresos, compras y movimientos",
                            ],
                        ),
                        _clarity_card(
                            "Reservas y reportes",
                            "Servicios con agenda, adelantos y reportes accionables para decidir.",
                            [
                                "Reservas con cobro parcial/final y estado de pago",
                                "Roles por tenant y permisos por usuario",
                                "Reportes ejecutivos por periodo, sucursal y categoria",
                            ],
                        ),
                        class_name="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3",
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8",
                ),
                class_name="mx-auto w-full max-w-6xl",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Todo lo que necesitas para operar con orden",
                        class_name="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.p(
                        "Cada modulo se conecta con el resto para evitar doble carga y sostener trazabilidad completa.",
                        class_name="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                    ),
                    rx.el.div(
                        _module_card(
                            "shopping-cart",
                            "Ventas de producto",
                            "Cobros rapidos con multiples metodos de pago, tickets y control por usuario.",
                            "Menos tiempo en caja y menos errores en el cierre.",
                        ),
                        _module_card(
                            "package",
                            "Inventario inteligente",
                            "Stock por sucursal, categorias, unidades y movimientos con historial detallado.",
                            "Reposicion mas precisa y menos quiebres de stock.",
                        ),
                        _module_card(
                            "calendar-plus",
                            "Reservas y servicios",
                            "Agenda de campos/servicios con adelantos, cobro final y comprobantes.",
                            "Mayor ocupacion y flujo de caja mas predecible.",
                        ),
                        _module_card(
                            "wallet",
                            "Caja y arqueo",
                            "Apertura, cierre, movimientos y auditoria de ingresos/egresos.",
                            "Visibilidad diaria del efectivo real.",
                        ),
                        _module_card(
                            "users",
                            "Usuarios y roles por tenant",
                            "Permisos por empresa y sucursal con aislamiento multi-tenant.",
                            "Mas seguridad y control operativo.",
                        ),
                        _module_card(
                            "pie-chart",
                            "Reportes ejecutivos",
                            "Metricas por periodo, sucursal y categoria para decisiones comerciales.",
                            "Detecta oportunidades y corrige desvíos a tiempo.",
                        ),
                        class_name="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3",
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8",
                    id="modulos",
                ),
                class_name="mx-auto w-full max-w-6xl",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.div(
                        rx.el.p(
                            "Resultados de operacion",
                            class_name="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500",
                        ),
                        rx.el.h2(
                            "Equipos comerciales ganan velocidad y control desde la primera semana.",
                            class_name="mt-2 text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                        ),
                        rx.el.p(
                            "La mejora no viene solo por software, sino por estandarizar procesos y visibilidad en tiempo real.",
                            class_name="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                        ),
                        class_name="max-w-4xl",
                    ),
                    rx.el.div(
                        _testimonial_card(
                            "Reducimos retrabajo en caja y ahora cerramos turnos con menos diferencia de efectivo.",
                            "Operacion retail multi-caja",
                        ),
                        _testimonial_card(
                            "El control de reservas con adelantos nos ordeno el flujo y disminuyo huecos de agenda.",
                            "Negocio de servicios con reservas",
                        ),
                        _testimonial_card(
                            "Con roles por tenant y reportes por sucursal pudimos delegar sin perder control.",
                            "Operacion multi-sucursal",
                        ),
                        class_name="mt-7 grid grid-cols-1 gap-4 md:grid-cols-3",
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8",
                ),
                class_name="mx-auto w-full max-w-6xl",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Flujos clave que puedes ejecutar hoy",
                        class_name="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.p(
                        "Desde el primer dia puedes operar punta a punta sin depender de hojas de calculo.",
                        class_name="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                    ),
                    rx.el.div(
                        _step_card(
                            "01",
                            "Alta de empresa y sucursal",
                            "Registro rapido con usuario admin, empresa inicial y configuracion base.",
                        ),
                        _step_card(
                            "02",
                            "Roles por tenant",
                            "Crea perfiles por empresa para separar funciones y accesos.",
                        ),
                        _step_card(
                            "03",
                            "Venta de producto",
                            "Genera ticket, descuenta stock y registra el movimiento de caja.",
                        ),
                        _step_card(
                            "04",
                            "Reserva y cobro de servicio",
                            "Agenda, cobra adelanto, confirma pago final y deja trazabilidad completa.",
                        ),
                        _step_card(
                            "05",
                            "Cierre y reporte",
                            "Valida caja diaria y consulta reportes para ajustar decisiones comerciales.",
                        ),
                        class_name="mt-8 grid grid-cols-1 gap-3 md:grid-cols-2",
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8",
                ),
                class_name="mx-auto w-full max-w-6xl bg-slate-50",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Planes para crecer sin friccion",
                        class_name="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.p(
                        "Empieza con precios claros por mes y escala a medida que crece tu operacion.",
                        class_name="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                    ),
                    rx.el.p(
                        "Sin contratos forzosos. Te acompanamos en onboarding y activacion comercial.",
                        class_name="mt-2 text-sm font-medium text-slate-500",
                    ),
                    rx.el.div(
                        _plan_card(
                            "Standard",
                            "Para negocios en crecimiento con operacion diaria estable.",
                            [
                                "Hasta 5 sucursales y 10 usuarios",
                                "Reportes mas profundos",
                                "Acompanamiento de implementacion",
                                "Soporte comercial continuo",
                            ],
                            "$45",
                            "Hablar con ventas",
                            standard_link,
                            tone="standard",
                        ),
                        _plan_card(
                            "Professional",
                            "Para operaciones multi-sucursal con mayor exigencia de control.",
                            [
                                "Hasta 10 sucursales y usuarios ilimitados",
                                "Configuracion avanzada",
                                "Prioridad de soporte",
                                "Gobernanza operativa",
                                "Escalabilidad para alto volumen",
                            ],
                            "$75",
                            "Solicitar propuesta",
                            professional_link,
                            tone="professional",
                            badge_text="Mas elegido",
                        ),
                        _plan_card(
                            "Enterprise",
                            "Para companias que requieren maxima escala, control y personalizacion.",
                            [
                                "Plan totalmente personalizable",
                                "Arquitectura y onboarding dedicado",
                                "Soporte prioritario y SLA",
                                "Integraciones y flujos a medida",
                                "Estrategia de escalamiento enterprise",
                            ],
                            "$175",
                            "Solicitar Enterprise",
                            enterprise_link,
                            tone="enterprise",
                            badge_text="Escala total",
                        ),
                        class_name="mt-8 grid grid-cols-1 items-stretch gap-4 lg:grid-cols-3",
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8",
                    id="planes",
                ),
                class_name="mx-auto w-full max-w-6xl",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Preguntas frecuentes",
                        class_name="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.div(
                        _faq_item(
                            "Cuanto tarda implementarlo?",
                            "Puedes comenzar el mismo dia. El onboarding base toma minutos.",
                            open_by_default=True,
                        ),
                        _faq_item(
                            "Necesito tarjeta para el trial?",
                            "No. Puedes activar la prueba de 15 dias sin tarjeta.",
                        ),
                        _faq_item(
                            "Sirve para varias empresas o sucursales?",
                            "Si. El sistema es multi-tenant y maneja aislamiento por empresa.",
                        ),
                        _faq_item(
                            "Puedo cobrar productos y servicios en el mismo sistema?",
                            "Si. Incluye flujo de ventas, reservas, adelantos y cobro final.",
                        ),
                        _faq_item(
                            "Que pasa cuando termino el trial?",
                            "Si te interesa continuar, eliges Standard, Professional o Enterprise sin perder continuidad operativa.",
                        ),
                        class_name="mt-7 grid grid-cols-1 gap-3 md:grid-cols-2",
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
                                class_name=(
                                    "inline-flex items-center justify-center rounded-xl bg-emerald-600 "
                                    "px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 "
                                    "transition-colors duration-150"
                                ),
                            ),
                            rx.el.a(
                                "Iniciar prueba",
                                href="/registro",
                                on_click=rx.call_script(
                                    _track_event_script(
                                        "click_trial_cta", "faq_secondary_cta"
                                    )
                                ),
                                class_name=(
                                    "inline-flex items-center justify-center rounded-xl border border-slate-300 "
                                    "bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 "
                                    "transition-colors duration-150"
                                ),
                            ),
                            class_name="flex flex-col gap-2 sm:flex-row",
                        ),
                        class_name=(
                            "mt-7 flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 "
                            "sm:flex-row sm:items-center sm:justify-between"
                        ),
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8",
                    id="faq",
                ),
                class_name="mx-auto w-full max-w-6xl bg-slate-50",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.div(
                        rx.el.h2(
                            "Listo para operar con mas control desde esta semana?",
                            class_name="text-2xl font-extrabold tracking-tight text-white sm:text-3xl",
                        ),
                        rx.el.p(
                            "Activa tu prueba gratis, crea tu empresa y empieza a vender con trazabilidad completa.",
                            class_name="mt-3 max-w-2xl text-sm leading-relaxed text-slate-200 sm:text-base",
                        ),
                        rx.el.div(
                            rx.el.a(
                                "Crear cuenta ahora",
                                href="/registro",
                                on_click=rx.call_script(
                                    _track_event_script(
                                        "click_trial_cta", "bottom_banner_primary_cta"
                                    )
                                ),
                                class_name=(
                                    "inline-flex items-center justify-center rounded-xl bg-emerald-500 "
                                    "px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-400 "
                                    "transition-colors duration-150"
                                ),
                            ),
                            rx.el.a(
                                "Ver login del sistema",
                                href="/",
                                class_name=(
                                    "inline-flex items-center justify-center rounded-xl border border-slate-500 "
                                    "px-5 py-3 text-sm font-semibold text-slate-100 hover:bg-slate-800 "
                                    "transition-colors duration-150"
                                ),
                            ),
                            class_name="mt-6 flex flex-col gap-3 sm:flex-row",
                        ),
                        class_name="max-w-3xl",
                    ),
                    class_name=(
                        "mx-auto w-full max-w-6xl rounded-3xl bg-slate-900 px-6 py-10 sm:px-10"
                    ),
                ),
                class_name="mx-auto w-full max-w-6xl px-4 pb-12 sm:px-6 lg:px-8",
            ),
            class_name="relative mx-auto w-full",
        ),
        rx.el.footer(
            rx.el.div(
                rx.el.div(
                    rx.el.p(
                        "TUWAYKIAPP | Sistema de Ventas SaaS para negocios multi-sucursal.",
                        class_name="text-sm text-slate-500",
                    ),
                    rx.el.div(
                        rx.el.a(
                            "Prueba gratis",
                            href="/registro",
                            on_click=rx.call_script(
                                _track_event_script("click_trial_cta", "footer_trial_link")
                            ),
                            class_name="text-sm text-slate-600 hover:text-slate-900",
                        ),
                        rx.el.a(
                            "Demo",
                            href=demo_link,
                            target="_blank",
                            rel="noopener noreferrer",
                            class_name="text-sm text-slate-600 hover:text-slate-900",
                        ),
                        rx.el.a(
                            "Ingresar",
                            href="/",
                            class_name="text-sm text-slate-600 hover:text-slate-900",
                        ),
                        class_name="flex items-center gap-4",
                    ),
                    class_name="flex w-full flex-col items-start justify-between gap-3 sm:flex-row sm:items-center",
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.span("Creado por", class_name="text-slate-400"),
                        rx.el.a(
                            "Trebor Oscorima",
                            href="https://www.facebook.com/trebor.oscorima/?locale=es_LA",
                            target="_blank",
                            rel="noopener noreferrer",
                            class_name="font-semibold text-indigo-600 hover:text-indigo-700",
                        ),
                        rx.el.span("🧉⚽️"),
                        rx.el.a(
                            "WhatsApp +5491168376517",
                            href="https://wa.me/5491168376517",
                            target="_blank",
                            rel="noopener noreferrer",
                            class_name="text-slate-400 hover:text-emerald-600",
                        ),
                        class_name="flex flex-wrap items-center justify-center gap-1.5 text-xs sm:text-sm",
                    ),
                    class_name="mt-4 w-full border-t border-slate-200 pt-4",
                ),
                class_name="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8",
            ),
            class_name="border-t border-slate-200 bg-white",
        ),
        class_name=(
            "relative min-h-screen bg-gradient-to-b from-slate-50 via-cyan-50/30 to-slate-100"
        ),
        style={"fontFamily": "'Sora', 'Public Sans', sans-serif"},
    )
