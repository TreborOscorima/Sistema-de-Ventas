"""Page section functions and floating elements for the marketing landing page."""

import reflex as rx

from app.constants import WHATSAPP_NUMBER

from ._state import (
    MarketingState,
    _site_href,
    _app_href,
    _food_href,
    _demo_link,
    _local_link,
    _standard_link,
    _professional_link,
    _enterprise_link,
    _food_demo_link,
    TRUST_BADGES,
    INDUSTRIES,
    MODULES,
    STEPS,
    FAQ_ITEMS,
    STRENGTH_METRICS,
    USE_CASES,
    EXTRA_CAPABILITIES,
    SCREENSHOT_TABS,
    FOOD_FEATURES,
)
from ._scripts import _track_event_script
from ._components import (
    _nav_link,
    _metric_card,
    _trust_pill,
    _industry_chip,
    _browser_frame,
    _hero_annotation_badge,
    _hero_preview_card,
    _comparison_card,
    _module_card,
    _timeline_step,
    _use_case_card,
    _extra_capability_chip,
    _strength_card,
    _plan_card,
    _faq_item,
    _footer_link,
)


def _announcement_banner() -> rx.Component:
    return rx.cond(
        MarketingState.show_announcement,
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    rx.el.span("Disponible", class_name="mr-2 rounded bg-emerald-500 px-1.5 py-0.5 text-xs font-bold uppercase text-white"),
                    "Presupuestos · Documentos Fiscales · Etiquetas · Promociones · Marketing · Cuentas corrientes",
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
                _nav_link("Módulos", "#modulos", "click_nav_modulos", "header_nav"),
                _nav_link("Ver el sistema", "#capturas", "click_nav_capturas", "header_nav"),
                _nav_link("Cómo funciona", "#como-funciona", "click_nav_como_funciona", "header_nav"),
                _nav_link("Planes", "#planes", "click_nav_planes", "header_nav"),
                _nav_link("FAQ", "#faq", "click_nav_faq", "header_nav"),
                class_name="hidden items-center gap-6 md:flex",
            ),
            rx.el.div(
                rx.el.a(
                    "Ingresar",
                    href=_app_href("/login"),
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
                    rx.el.div(
                        _nav_link("Módulos", "#modulos", "click_nav_modulos_mobile", "mobile_menu"),
                        _nav_link("Ver el sistema", "#capturas", "click_nav_capturas_mobile", "mobile_menu"),
                        _nav_link("Cómo funciona", "#como-funciona", "click_nav_como_funciona_mobile", "mobile_menu"),
                        _nav_link("Planes", "#planes", "click_nav_planes_mobile", "mobile_menu"),
                        _nav_link("FAQ", "#faq", "click_nav_faq_mobile", "mobile_menu"),
                        class_name="flex flex-col gap-4 py-1",
                    ),
                    rx.el.div(class_name="border-t border-slate-100"),
                    rx.el.div(
                        rx.el.a(
                            "Ingresar", href=_app_href("/login"),
                            on_click=rx.call_script(_track_event_script("click_nav_login_mobile", "mobile_menu")),
                            class_name="inline-flex w-full items-center justify-center rounded-xl border-2 border-indigo-600 px-4 py-2 text-sm font-semibold text-indigo-600 hover:bg-indigo-50",
                        ),
                        rx.el.a(
                            "Iniciar prueba gratis", href=_app_href("/registro"),
                            on_click=rx.call_script(_track_event_script("click_trial_cta", "mobile_menu_primary_cta")),
                            class_name="inline-flex w-full items-center justify-center rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700",
                        ),
                        class_name="flex flex-col gap-2",
                    ),
                    class_name="absolute right-0 mt-3 w-64 rounded-xl border border-slate-200 bg-white p-4 shadow-lg md:hidden flex flex-col gap-3",
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
                rx.el.div(
                    rx.el.span(
                        "Sistema de gestión todo-en-uno",
                        class_name="inline-flex rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700 shadow-sm",
                    ),
                    rx.el.span(
                        "Tiendas · canchas · servicios · multi-sucursal",
                        class_name="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-500 shadow-sm",
                    ),
                    class_name="flex flex-wrap items-center gap-2",
                ),
                rx.el.h1(
                    "Vende, controla tu stock y cierra caja — todo en un solo sistema.",
                    class_name="mt-5 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl sm:leading-tight",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                rx.el.p(
                    "TUWAYKIAPP reemplaza las planillas, los cuadernos y los sistemas sueltos. "
                    "Punto de venta, inventario, reservas, caja y reportes conectados — "
                    "con trazabilidad completa de cada peso, cada producto y cada usuario.",
                    class_name="mt-5 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg",
                ),
                rx.el.div(
                    *[_trust_pill(icon, label) for icon, label in TRUST_BADGES],
                    class_name="reveal-stagger mt-7 grid grid-cols-1 gap-2 sm:grid-cols-2",
                ),
                rx.el.div(
                    rx.el.a(
                        "Comenzar trial de 15 días",
                        href=_app_href("/registro"),
                        on_click=rx.call_script(_track_event_script("click_trial_cta", "hero_primary_cta")),
                        class_name="inline-flex items-center justify-center rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 shadow-sm",
                    ),
                    rx.el.a(
                        rx.icon("message-circle", class_name="h-4 w-4"),
                        "Agendar demo guiada",
                        href=_demo_link,
                        target="_blank", rel="noopener noreferrer",
                        on_click=rx.call_script(_track_event_script("click_demo_cta", "hero_secondary_cta")),
                        class_name="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white/80 px-5 py-3 text-sm font-semibold text-slate-700 transition-colors hover:bg-white",
                    ),
                    class_name="mt-8 flex flex-col gap-3 sm:flex-row",
                ),
                rx.el.p(
                    "Sin tarjeta de crédito · Sin compromiso · Cancela cuando quieras",
                    class_name="mt-3 text-xs text-slate-400",
                ),
                class_name="reveal max-w-2xl",
            ),
            _hero_preview_card(),
            class_name=rx.cond(
                MarketingState.show_announcement,
                "grid grid-cols-1 items-start gap-10 lg:grid-cols-2 mx-auto w-full max-w-7xl px-4 pt-16 pb-16 sm:px-6 lg:px-8 lg:pt-20",
                "grid grid-cols-1 items-start gap-10 lg:grid-cols-2 mx-auto w-full max-w-7xl px-4 pt-24 pb-16 sm:px-6 lg:px-8 lg:pt-28",
            ),
        ),
        class_name="hero-section w-full",
    )


def _metrics_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            _metric_card("< 30 seg", "por venta registrada", "Desde escanear el producto hasta imprimir el ticket"),
            _metric_card("3 min", "para cerrar caja", "Arqueo automático con diferencias al instante"),
            _metric_card("0 planillas", "que cruzar a mano", "Caja, stock y ventas conectados en un solo flujo"),
            _metric_card("15 días", "de prueba gratuita", "Sin tarjeta de crédito, sin compromiso"),
            class_name="reveal-stagger grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4",
        ),
        class_name="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8",
    )


def _industries_section() -> rx.Component:
    ticker_nodes = [_industry_chip(icon, name, detail) for _ in range(2) for icon, name, detail in INDUSTRIES]
    return rx.el.section(
        rx.el.div(
            rx.el.p(
                "Pensado para tu industria — sin configuraciones complejas",
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
                rx.el.p("Problema vs solución", class_name="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500"),
                rx.el.h2(
                    "Deja de improvisar. Centraliza la operación.",
                    class_name="mt-2 text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                rx.el.p(
                    "Visualiza el antes y después cuando dejas de cruzar Excel para saber si la caja cuadra.",
                    class_name="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                ),
                class_name="reveal max-w-4xl",
            ),
            rx.el.div(
                _comparison_card(
                    "Operación fragmentada", "triangle-alert",
                    [
                        "Caja en Excel, ventas en otro sistema, reservas por WhatsApp",
                        "Errores por doble carga y falta de trazabilidad entre areas",
                        "Decisiones tardias porque no hay datos consolidados",
                    ],
                    tone="negative",
                ),
                _comparison_card(
                    "Operación unificada", "sparkles",
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
                "Módulos conectados para operar sin fricción",
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
                "Cómo funciona",
                class_name="reveal text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                style={"fontFamily": "'Space Grotesk', sans-serif"},
            ),
            rx.el.p(
                "Implementación en cinco pasos para salir a operar rápido.",
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


def _use_cases_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.p(
                "¿Para qué tipo de negocio?",
                class_name="reveal text-xs font-semibold uppercase tracking-[0.18em] text-slate-500",
            ),
            rx.el.h2(
                "Funciona para tu operación, sea cual sea",
                class_name="reveal mt-2 text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                style={"fontFamily": "'Space Grotesk', sans-serif"},
            ),
            rx.el.p(
                "Desde tiendas y bodegas hasta canchas deportivas y negocios de servicios. "
                "Un solo sistema que se adapta a tu industria sin configuraciones complejas.",
                class_name="reveal mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
            ),
            rx.el.div(
                *[
                    _use_case_card(uc["icon"], uc["title"], uc["description"], uc["features"], uc["accent"])
                    for uc in USE_CASES
                ],
                class_name="reveal-stagger mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8",
            id="casos-de-uso",
        ),
        class_name="bg-slate-50",
    )


def _extra_capabilities_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.h2(
                "Mucho más que ventas",
                class_name="reveal text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                style={"fontFamily": "'Space Grotesk', sans-serif"},
            ),
            rx.el.p(
                "TUWAYKIAPP no es solo un punto de venta. Es un ecosistema completo para operar, "
                "crecer y mantener el control de cada área de tu negocio.",
                class_name="reveal mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
            ),
            rx.el.div(
                *[_extra_capability_chip(icon, title, desc) for icon, title, desc in EXTRA_CAPABILITIES],
                class_name="reveal-stagger mt-10 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8",
        ),
    )


def _demo_flow_step(num: int, icon: str, title: str, desc: str, color: str) -> rx.Component:
    palettes = {
        "emerald": ("bg-emerald-50", "text-emerald-600", "bg-emerald-600", "border-emerald-100"),
        "blue":    ("bg-blue-50",    "text-blue-600",    "bg-blue-600",    "border-blue-100"),
        "violet":  ("bg-violet-50",  "text-violet-600",  "bg-violet-600",  "border-violet-100"),
        "amber":   ("bg-amber-50",   "text-amber-600",   "bg-amber-600",   "border-amber-100"),
    }
    icon_bg, icon_text, num_bg, border = palettes.get(color, palettes["emerald"])
    return rx.el.article(
        rx.el.div(
            rx.el.span(
                str(num),
                class_name=f"inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full {num_bg} text-xs font-bold text-white",
            ),
            rx.el.div(
                rx.icon(icon, class_name=f"h-5 w-5 {icon_text}"),
                class_name=f"inline-flex items-center justify-center rounded-xl {icon_bg} p-2.5",
            ),
            class_name="flex items-center gap-3",
        ),
        rx.el.h3(title, class_name="mt-4 text-base font-bold text-slate-900"),
        rx.el.p(desc, class_name="mt-2 text-sm leading-relaxed text-slate-500"),
        class_name=f"rounded-2xl border {border} bg-white p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
    )


def _demo_flow_section() -> rx.Component:
    """Flujo visual de una operación completa — reemplaza la necesidad de un video."""
    flow_steps = [
        ("shopping-cart", "Busca y cobra en segundos",
         "El cajero agrega productos al carrito por nombre o código de barras y cobra en efectivo, tarjeta o transferencia. Ticket listo en menos de 30 segundos.",
         "emerald"),
        ("package", "Stock se actualiza solo",
         "Cada venta descuenta el inventario de la sucursal en tiempo real. Sin carga manual, sin diferencias al hacer el conteo físico.",
         "blue"),
        ("wallet", "Caja cuadra al cierre",
         "El sistema registra cada ingreso y egreso con motivo, usuario y hora. Al cerrar el turno, el arqueo calcula las diferencias al instante.",
         "violet"),
        ("bar-chart-3", "Reportes listos para decidir",
         "Las ventas del día se consolidan en reportes de rentabilidad y rotación. Filtra por período, producto o sucursal y exporta en un clic.",
         "amber"),
    ]
    return rx.el.section(
        rx.el.div(
            rx.el.p(
                "Así funciona por dentro",
                class_name="reveal text-xs font-semibold uppercase tracking-[0.18em] text-slate-500",
            ),
            rx.el.h2(
                "De la venta al reporte en un solo flujo",
                class_name="reveal mt-2 text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                style={"fontFamily": "'Space Grotesk', sans-serif"},
            ),
            rx.el.p(
                "Cada módulo alimenta al siguiente. Cobra, descuenta stock, registra en caja y analiza — "
                "todo conectado, todo en tiempo real, sin que nadie tenga que hacer doble trabajo.",
                class_name="reveal mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
            ),
            rx.el.div(
                *[_demo_flow_step(i + 1, icon, title, desc, color)
                  for i, (icon, title, desc, color) in enumerate(flow_steps)],
                class_name="reveal-stagger mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4",
            ),
            rx.el.div(
                rx.el.a(
                    rx.icon("circle-play", class_name="h-4 w-4"),
                    "Ver demo en vivo por WhatsApp",
                    href=_demo_link,
                    target="_blank", rel="noopener noreferrer",
                    on_click=rx.call_script(_track_event_script("click_demo_flow_cta", "demo_flow_section")),
                    class_name="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-slate-800 shadow-sm",
                ),
                class_name="reveal mt-10 flex justify-center",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8",
        ),
        class_name="bg-slate-50",
    )


def _screenshots_section() -> rx.Component:
    """Galería de screenshots con tabs por módulo — navegación JS puro."""
    tab_buttons = []
    for idx, tab in enumerate(SCREENSHOT_TABS):
        base_cls = "twk-tab-btn tab-btn inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition-all cursor-pointer"
        btn_cls = f"{base_cls} active" if idx == 0 else base_cls
        tab_id = tab["id"]
        tab_buttons.append(
            rx.el.button(
                rx.icon(tab["icon"], class_name="h-4 w-4 shrink-0"),
                rx.el.span(tab["label"], class_name="hidden sm:inline"),
                id=f"tab-btn-{tab_id}",
                on_click=rx.call_script(
                    f"(function(){{"
                    f"document.querySelectorAll('.twk-tab-btn').forEach(function(b){{b.classList.remove('active');}});"
                    f"document.querySelectorAll('.twk-tab-panel').forEach(function(p){{p.classList.remove('active');}});"
                    f"document.getElementById('tab-btn-{tab_id}').classList.add('active');"
                    f"document.getElementById('tab-panel-{tab_id}').classList.add('active');"
                    f"}})();"
                ),
                class_name=btn_cls,
            )
        )

    panels = []
    for i, tab in enumerate(SCREENSHOT_TABS):
        panel_cls = "twk-tab-panel" + (" active" if i == 0 else "") + " grid grid-cols-1 items-center gap-8 lg:grid-cols-2"
        panels.append(
            rx.el.div(
                rx.el.div(
                    rx.el.h3(
                        tab["headline"],
                        class_name="text-xl font-extrabold text-slate-900 sm:text-2xl",
                        style={"fontFamily": "'Space Grotesk', sans-serif"},
                    ),
                    rx.el.ul(
                        *[
                            rx.el.li(
                                rx.icon("check", class_name="h-4 w-4 text-emerald-600 mt-0.5 shrink-0"),
                                rx.el.span(b, class_name="text-sm text-slate-700"),
                                class_name="flex items-start gap-2",
                            )
                            for b in tab["bullets"]
                        ],
                        class_name="mt-5 space-y-2.5",
                    ),
                    class_name="flex flex-col",
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.el.span(class_name="h-2.5 w-2.5 rounded-full bg-red-400"),
                            rx.el.span(class_name="h-2.5 w-2.5 rounded-full bg-yellow-400"),
                            rx.el.span(class_name="h-2.5 w-2.5 rounded-full bg-green-400"),
                            class_name="flex items-center gap-1.5",
                        ),
                        rx.el.div(
                            rx.el.span(
                                "tuwaykiapp.com",
                                class_name="text-xs text-slate-400 font-mono",
                            ),
                            class_name="flex-1 mx-3 bg-white rounded-md px-3 py-1 text-center border border-slate-200",
                        ),
                        class_name="flex items-center bg-slate-50 border-b border-slate-200 px-4 py-3 gap-3",
                    ),
                    rx.el.img(
                        src=tab["src"],
                        alt=tab["alt"],
                        class_name="w-full h-auto object-cover",
                        loading="lazy",
                    ),
                    class_name="overflow-hidden rounded-2xl border border-slate-200 shadow-xl shadow-slate-200/60 ring-1 ring-slate-900/5",
                ),
                id=f"tab-panel-{tab['id']}",
                class_name=panel_cls,
            )
        )

    return rx.el.section(
        rx.el.div(
            rx.el.p(
                "El sistema en acción",
                class_name="reveal text-xs font-semibold uppercase tracking-[0.18em] text-slate-500",
            ),
            rx.el.h2(
                "Mira cómo se ve por dentro",
                class_name="reveal mt-2 text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                style={"fontFamily": "'Space Grotesk', sans-serif"},
            ),
            rx.el.p(
                "Una interfaz limpia y rápida pensada para que tu equipo opere sin curva de aprendizaje.",
                class_name="reveal mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
            ),
            rx.el.div(
                *tab_buttons,
                class_name="reveal mt-8 flex flex-wrap gap-1.5 rounded-xl bg-slate-100 p-1.5",
            ),
            rx.el.div(
                *panels,
                class_name="mt-6",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8",
            id="capturas",
        ),
        class_name="bg-white",
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
                            "Actualizaciones automáticas sin intervención",
                            "Backups diarios en la nube incluidos",
                            "Soporte técnico remoto inmediato",
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
                            "Requiere conexión a internet estable",
                            "Pago mensual recurrente según el plan",
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
                _plan_card("Standard", "Ideal para negocios que quieren orden operativo desde el inicio.", "$35",
                    ["Hasta 2 sucursales", "Hasta 5 usuarios", "Punto de venta + caja + inventario", "Reportes base y soporte comercial"],
                    "Elegir Standard", _standard_link, "click_plan_standard", tone="standard"),
                _plan_card("Professional", "Para operaciones de mayor volumen y necesidad de control avanzado.", "$55",
                    ["Hasta 5 sucursales", "Hasta 10 usuarios", "Configuraciones avanzadas", "Prioridad de soporte", "Mayor profundidad de reportes"],
                    "Elegir Professional", _professional_link, "click_plan_professional", tone="professional", badge_text="Más elegido"),
                _plan_card("Enterprise", "Para compañías con demanda de escala, personalización y SLA dedicado.", "$175",
                    ["Plan personalizable por operación", "Onboarding y arquitectura dedicada", "Integraciones y flujos a medida", "Acompañamiento prioritario", "Gobernanza enterprise"],
                    "Solicitar Enterprise", _enterprise_link, "click_plan_enterprise", tone="enterprise", badge_text="Escala total"),
                class_name="grid grid-cols-1 items-stretch gap-4 md:grid-cols-2 lg:grid-cols-3",
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
                            "Funciona sin conexión a internet",
                            "Pago único anual — sin mensualidades",
                            "Tus datos permanecen 100% en tu equipo",
                            "Control total sobre tu infraestructura",
                            "Ideal para zonas con internet inestable",
                            "Rendimiento óptimo sin depender de la red",
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
                            "Las actualizaciones requieren instalación manual",
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
                            "Instalación y configuración inicial incluida",
                            "Soporte técnico por 12 meses",
                            "Capacitación inicial para tu equipo",
                            "Actualizaciones durante el período contratado",
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
                "Elige cómo quieres usar TUWAYKIAPP",
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
                    rx.icon("hard-drive", class_name="h-4 w-4"), "Instalación Local",
                    on_click=MarketingState.set_tab_local,
                    class_name=rx.cond(
                        MarketingState.active_tab == "local",
                        "tab-btn active inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all cursor-pointer",
                        "tab-btn inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all cursor-pointer",
                    ),
                ),
                class_name="reveal mt-10 flex flex-wrap justify-center gap-2 rounded-xl bg-slate-100 p-1.5",
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
                    rx.el.p("¿Aún tienes dudas antes de activar tu trial?", class_name="text-base font-semibold text-slate-900"),
                    rx.el.p("Nuestro equipo te ayuda a elegir plan y a estimar implementación según tu operación.", class_name="mt-1 text-sm text-slate-600"),
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


def _tuwaykifood_section() -> rx.Component:
    """Sección presentando TUWAYKIFOOD — sistema para restaurantes y restobares."""
    feature_cards = [
        rx.el.article(
            rx.el.div(
                rx.icon(feat[0], class_name="h-5 w-5 text-orange-600"),
                class_name="inline-flex items-center justify-center rounded-xl bg-orange-50 p-2.5",
            ),
            rx.el.h3(feat[1], class_name="mt-4 text-base font-bold text-slate-900"),
            rx.el.p(feat[2], class_name="mt-2 text-sm leading-relaxed text-slate-600"),
            class_name="reveal rounded-2xl border border-slate-200 bg-white p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
        )
        for feat in FOOD_FEATURES
    ]

    return rx.el.section(
        rx.el.div(
            # Header de sección
            rx.el.div(
                rx.el.div(
                    rx.icon("utensils", class_name="h-4 w-4 text-orange-600"),
                    rx.el.span("TUWAYKIFOOD", class_name="text-xs font-bold text-orange-600 uppercase tracking-widest"),
                    class_name="inline-flex items-center gap-2 rounded-full border border-orange-200 bg-orange-50 px-4 py-1.5",
                ),
                rx.el.h2(
                    "Sistema para restaurantes y restobares",
                    class_name="mt-6 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                rx.el.p(
                    "Carta digital con QR, gestión de mesas, pedidos por tablet y comanda automática en cocina. "
                    "Todo conectado con la caja del turno.",
                    class_name="mt-4 max-w-2xl text-base leading-relaxed text-slate-600",
                ),
                class_name="flex flex-col items-center text-center",
            ),
            # Grid de features
            rx.el.div(
                *feature_cards,
                class_name="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3",
            ),
            # CTA
            rx.el.div(
                rx.el.div(
                    rx.el.p(
                        "Próximamente disponible",
                        class_name="text-sm font-semibold text-orange-700 uppercase tracking-wide",
                    ),
                    rx.el.p(
                        "TUWAYKIFOOD estará disponible en ",
                        rx.el.strong("food.tuwayki.com", class_name="font-bold"),
                        ". Mientras tanto, agendá una demo con nosotros.",
                        class_name="mt-1 text-sm text-slate-600",
                    ),
                    class_name="flex flex-col",
                ),
                rx.el.a(
                    rx.icon("message-circle", class_name="h-4 w-4 mr-2"),
                    "Quiero saber más",
                    href=_food_demo_link,
                    target="_blank",
                    rel="noopener noreferrer",
                    on_click=rx.call_script(_track_event_script("click_food_cta", "food_section")),
                    class_name="inline-flex items-center justify-center rounded-xl bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-orange-600 whitespace-nowrap",
                ),
                class_name="reveal mt-12 flex flex-col items-center gap-5 rounded-2xl border border-orange-100 bg-orange-50 p-8 sm:flex-row sm:justify-between",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8",
        ),
        id="tuwaykifood",
        class_name="py-20 sm:py-24 bg-white",
    )


def _cta_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.h2(
                    "Tu operación merece más que planillas y sistemas desconectados",
                    class_name="text-2xl font-extrabold tracking-tight text-white sm:text-3xl text-center",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                rx.el.p(
                    "Activa tu prueba de 15 días sin tarjeta. Centraliza ventas, inventario, caja y reservas ",
                    rx.el.span("desde hoy.", class_name="whitespace-nowrap"),
                    class_name="mt-4 max-w-2xl text-sm leading-relaxed text-slate-300 sm:text-base text-center",
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
                    class_name="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center",
                ),
                class_name="reveal mx-auto w-full max-w-7xl overflow-hidden rounded-3xl bg-slate-900 border border-slate-800 px-8 py-14 sm:px-12 sm:py-16 shadow-2xl flex flex-col items-center",
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
                    rx.el.p("Sistema de gestión SaaS para negocios multi-sucursal con enfoque en control real.", class_name="mt-3 max-w-xs text-sm text-slate-600"),
                    rx.el.a(
                        "WhatsApp +5491168376517",
                        href=f"https://wa.me/{WHATSAPP_NUMBER}", target="_blank", rel="noopener noreferrer",
                        on_click=rx.call_script(_track_event_script("click_whatsapp_cta", "footer_contact")),
                        class_name="mt-3 inline-flex text-sm font-semibold text-emerald-700 hover:text-emerald-800",
                    ),
                ),
                rx.el.div(
                    rx.el.h4("Producto", class_name="text-sm font-bold text-slate-900"),
                    _footer_link("Módulos", "#modulos", "click_footer_modulos", "footer_producto"),
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
                    _footer_link("Iniciar sesion", _app_href("/login"), "click_footer_login", "footer_accesos"),
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
                    rx.el.p("TUWAYKIAPP © 2026. Todos los derechos reservados.", class_name="text-sm leading-relaxed text-slate-500"),
                    rx.el.p("Hecho con foco en escalabilidad, operación y crecimiento comercial.", class_name="text-sm leading-relaxed text-slate-500"),
                    class_name="space-y-1",
                ),
                rx.el.div(
                    rx.el.p("Creado por", class_name="text-xs text-slate-400 uppercase tracking-wider"),
                    rx.el.a(
                        "Trebor Oscorima",
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
