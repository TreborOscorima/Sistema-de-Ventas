"""Home page — sitio de empresa TUWAYKIAPP (marca madre + productos TUWAYKISHOP / TUWAYKIFOOD)."""

import reflex as rx

from app.constants import WHATSAPP_NUMBER

from ._state import _life_href, _site_href
from ._scripts import (
    _global_styles,
    _sw_cleanup_script,
    _analytics_bootstrap_script,
    _cookie_consent_script,
    _cookie_consent_banner,
    _track_event_script,
    home_jsonld_components,
)

_WA_URL = f"https://wa.me/{WHATSAPP_NUMBER}"
_FONT_DISPLAY = {"fontFamily": "'Space Grotesk', sans-serif"}


# ─── Bloques reutilizables ──────────────────────────────────────────────


def _eyebrow(text: str, *, color: str = "indigo") -> rx.Component:
    """Etiqueta pequeña en mayúsculas sobre los títulos de sección."""
    return rx.el.span(
        text,
        class_name=(
            f"inline-block text-xs font-bold uppercase tracking-widest text-{color}-600"
        ),
    )


def _wa_button(label: str, event: str, *, solid: bool = True) -> rx.Component:
    base = "inline-flex items-center justify-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold transition-colors"
    style = (
        "bg-emerald-600 text-white hover:bg-emerald-700"
        if solid
        else "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
    )
    return rx.el.a(
        rx.icon("message-circle", class_name="h-4 w-4"),
        label,
        href=_WA_URL,
        target="_blank",
        rel="noopener noreferrer",
        on_click=rx.call_script(_track_event_script(event, "home")),
        class_name=f"{base} {style}",
    )


# ─── Header ─────────────────────────────────────────────────────────────


def _home_header() -> rx.Component:
    nav_cls = "text-sm font-medium text-slate-600 transition-colors hover:text-indigo-600"
    return rx.el.header(
        rx.el.div(
            rx.el.a(
                rx.icon("layers", class_name="h-8 w-8 text-indigo-600"),
                rx.el.span(
                    "TUWAYKIAPP",
                    class_name="text-2xl font-extrabold tracking-tight text-slate-900",
                ),
                href=_site_href("/"),
                class_name="flex items-center gap-2.5",
            ),
            rx.el.nav(
                rx.el.a("Nosotros", href="#nosotros", class_name=nav_cls),
                rx.el.a("Sistemas", href="#sistemas", class_name=nav_cls),
                rx.el.a("Por qué TUWAYKIAPP", href="#por-que", class_name=nav_cls),
                class_name="hidden items-center gap-8 md:flex",
            ),
            rx.el.a(
                rx.icon("message-circle", class_name="h-4 w-4"),
                "WhatsApp",
                href=_WA_URL,
                target="_blank",
                rel="noopener noreferrer",
                on_click=rx.call_script(_track_event_script("click_whatsapp_home", "home_header")),
                class_name="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-700",
            ),
            class_name="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8",
        ),
        class_name="sticky top-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur",
    )


# ─── Hero ───────────────────────────────────────────────────────────────


def _hero_section() -> rx.Component:
    caps = ["En la nube", "Multi-empresa", "Multi-sucursal", "Datos seguros", "Soporte cercano"]
    return rx.el.section(
        # Glow decorativo
        rx.el.div(
            class_name="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[420px] bg-gradient-to-b from-indigo-50 via-white to-transparent",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon("layers", class_name="h-4 w-4 text-indigo-600"),
                rx.el.span(
                    "Plataforma de gestión empresarial",
                    class_name="text-xs font-bold uppercase tracking-widest text-indigo-600",
                ),
                class_name="mx-auto inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-4 py-1.5",
            ),
            rx.el.h1(
                "Software de gestión para hacer crecer tu negocio",
                class_name="mx-auto mt-6 max-w-3xl text-4xl font-extrabold leading-tight tracking-tight text-slate-900 sm:text-6xl",
                style=_FONT_DISPLAY,
            ),
            rx.el.p(
                "En TUWAYKIAPP creamos software de gestión en la nube para distintas industrias. "
                "No desarrollamos un solo sistema: cada solución está pensada a la medida de su rubro "
                "— simple de usar, segura y lista para escalar.",
                class_name="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-600",
            ),
            rx.el.div(
                rx.el.a(
                    "Ver nuestros sistemas",
                    rx.icon("arrow-down", class_name="h-4 w-4"),
                    href="#sistemas",
                    class_name="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-indigo-700",
                ),
                _wa_button("Hablar con nosotros", "click_whatsapp_hero", solid=False),
                class_name="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row",
            ),
            # Strip de capacidades
            rx.el.div(
                *[
                    rx.el.span(
                        rx.icon("circle-check", class_name="h-4 w-4 text-indigo-500"),
                        c,
                        class_name="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500",
                    )
                    for c in caps
                ],
                class_name="mt-12 flex flex-wrap items-center justify-center gap-x-6 gap-y-3",
            ),
            class_name="mx-auto w-full max-w-5xl px-4 text-center sm:px-6 lg:px-8",
        ),
        class_name="relative overflow-hidden pt-20 pb-16 sm:pt-28 sm:pb-24",
    )


# ─── Nosotros ───────────────────────────────────────────────────────────


def _pillar(icon: str, title: str, text: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, class_name="h-6 w-6 text-indigo-600"),
            class_name="inline-flex items-center justify-center rounded-xl bg-indigo-50 p-3",
        ),
        rx.el.h3(title, class_name="mt-4 text-lg font-bold text-slate-900"),
        rx.el.p(text, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
        class_name="rounded-2xl border border-slate-200 bg-white p-6",
    )


def _about_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                _eyebrow("Quiénes somos"),
                rx.el.h2(
                    "Tecnología que ordena y potencia tu operación",
                    class_name="mt-3 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl",
                    style=_FONT_DISPLAY,
                ),
                rx.el.p(
                    "Construimos herramientas de gestión pensadas para la realidad de los negocios "
                    "de Latinoamérica, sea cual sea su rubro. Reemplazamos las planillas, los cuadernos "
                    "y los sistemas sueltos por plataformas en la nube, seguras y multi-empresa, que te "
                    "dan control real de tu operación, tus datos y tu dinero.",
                    class_name="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-slate-600",
                ),
                class_name="mx-auto max-w-2xl text-center",
            ),
            rx.el.div(
                _pillar(
                    "layout-grid",
                    "Todo en un solo lugar",
                    "Ventas, inventario, caja, clientes y reportes conectados entre sí, sin pasar datos de un lado a otro.",
                ),
                _pillar(
                    "cloud",
                    "En la nube y seguro",
                    "Accede desde cualquier dispositivo, con los datos de cada empresa protegidos y aislados.",
                ),
                _pillar(
                    "trending-up",
                    "Listo para escalar",
                    "De un local a múltiples sucursales, sin migrar de sistema ni perder el histórico.",
                ),
                class_name="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3",
            ),
            class_name="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8",
        ),
        id="nosotros",
        class_name="scroll-mt-20 bg-slate-50 py-20 sm:py-24",
    )


# ─── Productos ──────────────────────────────────────────────────────────


def _product_card_ventas() -> rx.Component:
    chips = ["POS + Stock", "Caja y arqueo", "Reservas", "Reportes", "Multi-sucursal"]
    return rx.el.a(
        rx.el.div(
            rx.el.div(
                rx.icon("box", class_name="h-10 w-10 text-indigo-600"),
                class_name="inline-flex items-center justify-center rounded-2xl bg-indigo-50 p-3",
            ),
            rx.el.div(
                rx.el.h3(
                    "TUWAYKISHOP",
                    class_name="text-2xl font-extrabold tracking-tight text-slate-900",
                ),
                rx.el.p(
                    "Sistema de Ventas",
                    class_name="mt-0.5 text-sm font-bold text-indigo-600 uppercase tracking-widest",
                ),
                class_name="mt-5",
            ),
            rx.el.p(
                "Punto de venta, inventario, caja, reservas y reportes en una sola plataforma. "
                "Para tiendas, canchas, talleres y negocios multi-sucursal.",
                class_name="mt-4 text-sm leading-relaxed text-slate-600",
            ),
            rx.el.div(
                *[
                    rx.el.span(
                        f,
                        class_name="inline-flex items-center rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700",
                    )
                    for f in chips
                ],
                class_name="mt-5 flex flex-wrap gap-2",
            ),
            rx.el.div(
                rx.el.span(
                    "Ver sistema",
                    rx.icon("arrow-right", class_name="h-4 w-4"),
                    class_name="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors group-hover:bg-indigo-700",
                ),
                class_name="mt-8",
            ),
            class_name="flex h-full flex-col p-8 sm:p-10",
        ),
        href=_site_href("/ventas"),
        on_click=rx.call_script(_track_event_script("click_product_ventas", "home_selector")),
        class_name=(
            "group block rounded-3xl border-2 border-slate-200 bg-white "
            "transition-all duration-200 hover:border-indigo-400 hover:shadow-xl hover:-translate-y-1"
        ),
    )


def _product_card_food() -> rx.Component:
    chips = ["Carta QR", "Mesas", "Pedidos tablet", "Cocina / KDS", "Caja por turno"]
    return rx.el.a(
        rx.el.div(
            rx.el.div(
                rx.icon("utensils", class_name="h-10 w-10 text-orange-600"),
                class_name="inline-flex items-center justify-center rounded-2xl bg-orange-50 p-3",
            ),
            rx.el.div(
                rx.el.h3(
                    "TUWAYKIFOOD",
                    class_name="text-2xl font-extrabold tracking-tight text-slate-900",
                ),
                rx.el.p(
                    "Sistema para Restobares",
                    class_name="mt-0.5 text-sm font-bold text-orange-600 uppercase tracking-widest",
                ),
                class_name="mt-5",
            ),
            rx.el.p(
                "Carta digital con QR, gestión de mesas, pedidos por tablet y comanda automática en cocina. "
                "Todo conectado con la caja del turno.",
                class_name="mt-4 text-sm leading-relaxed text-slate-600",
            ),
            rx.el.div(
                *[
                    rx.el.span(
                        f,
                        class_name="inline-flex items-center rounded-full bg-orange-50 px-2.5 py-0.5 text-xs font-semibold text-orange-700",
                    )
                    for f in chips
                ],
                class_name="mt-5 flex flex-wrap gap-2",
            ),
            rx.el.div(
                rx.el.span(
                    "Ver sistema",
                    rx.icon("arrow-right", class_name="h-4 w-4"),
                    class_name="inline-flex items-center gap-2 rounded-xl bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors group-hover:bg-orange-600",
                ),
                class_name="mt-8",
            ),
            class_name="flex h-full flex-col p-8 sm:p-10",
        ),
        href=_site_href("/food"),
        on_click=rx.call_script(_track_event_script("click_product_food", "home_selector")),
        class_name=(
            "group block rounded-3xl border-2 border-slate-200 bg-white "
            "transition-all duration-200 hover:border-orange-400 hover:shadow-xl hover:-translate-y-1"
        ),
    )


def _product_card_life() -> rx.Component:
    """Tarjeta del sistema de gestión para salud (TUWAYKILIFE) — enlaza al login."""
    chips = ["Turnos", "Historia clínica", "Pacientes", "Agenda", "Multi-sucursal"]
    return rx.el.a(
        rx.el.span(
            rx.icon("sparkles", class_name="h-3.5 w-3.5"),
            "Nuevo",
            class_name="absolute right-5 top-5 inline-flex items-center gap-1.5 rounded-full bg-teal-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-teal-700",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon("heart-pulse", class_name="h-10 w-10 text-teal-600"),
                class_name="inline-flex items-center justify-center rounded-2xl bg-teal-50 p-3",
            ),
            rx.el.div(
                rx.el.h3(
                    "TUWAYKILIFE",
                    class_name="text-2xl font-extrabold tracking-tight text-slate-900",
                ),
                rx.el.p(
                    "Sistema para Clínicas",
                    class_name="mt-0.5 text-sm font-bold text-teal-600 uppercase tracking-widest",
                ),
                class_name="mt-5",
            ),
            rx.el.p(
                "Gestión de turnos, historias clínicas, pacientes y agenda médica. "
                "Para clínicas, consultorios y centros de salud de todas las especialidades.",
                class_name="mt-4 text-sm leading-relaxed text-slate-600",
            ),
            rx.el.div(
                *[
                    rx.el.span(
                        f,
                        class_name="inline-flex items-center rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-semibold text-teal-700",
                    )
                    for f in chips
                ],
                class_name="mt-5 flex flex-wrap gap-2",
            ),
            rx.el.div(
                rx.el.span(
                    "Ver sistema",
                    rx.icon("arrow-right", class_name="h-4 w-4"),
                    class_name="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors group-hover:bg-teal-700",
                ),
                class_name="mt-8",
            ),
            class_name="flex h-full flex-col p-8 sm:p-10",
        ),
        href=_life_href("/login"),
        on_click=rx.call_script(_track_event_script("click_product_life", "home_selector")),
        class_name=(
            "group relative block rounded-3xl border-2 border-slate-200 bg-white "
            "transition-all duration-200 hover:border-teal-400 hover:shadow-xl hover:-translate-y-1"
        ),
    )


def _products_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                _eyebrow("Nuestros sistemas"),
                rx.el.h2(
                    "Un sistema diseñado para tu industria",
                    class_name="mt-3 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl",
                    style=_FONT_DISPLAY,
                ),
                rx.el.p(
                    "Elige el sistema que corresponde a tu rubro. Cada uno está diseñado para su "
                    "industria y comparte la misma base sólida de TUWAYKIAPP: nube, seguridad y control real.",
                    class_name="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-slate-600",
                ),
                class_name="mx-auto max-w-2xl text-center",
            ),
            rx.el.div(
                _product_card_ventas(),
                _product_card_food(),
                _product_card_life(),
                class_name="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3",
            ),
            class_name="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8",
        ),
        id="sistemas",
        class_name="scroll-mt-20 bg-white py-20 sm:py-24",
    )


# ─── Por qué TUWAYKIAPP ─────────────────────────────────────────────────


def _feature(icon: str, title: str, text: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, class_name="h-5 w-5 text-indigo-600"),
            class_name="inline-flex shrink-0 items-center justify-center rounded-lg bg-indigo-50 p-2.5",
        ),
        rx.el.div(
            rx.el.h3(title, class_name="text-base font-bold text-slate-900"),
            rx.el.p(text, class_name="mt-1 text-sm leading-relaxed text-slate-600"),
        ),
        class_name="flex items-start gap-4",
    )


def _features_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                _eyebrow("Por qué TUWAYKIAPP"),
                rx.el.h2(
                    "Pensado para que operes tranquilo",
                    class_name="mt-3 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl",
                    style=_FONT_DISPLAY,
                ),
                rx.el.p(
                    "La misma tecnología que usan las grandes plataformas, al alcance de tu negocio.",
                    class_name="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-slate-600",
                ),
                class_name="mx-auto max-w-2xl text-center",
            ),
            rx.el.div(
                _feature(
                    "cloud",
                    "100% en la nube",
                    "Sin instalaciones complejas. Actualizaciones automáticas y acceso desde cualquier dispositivo.",
                ),
                _feature(
                    "building-2",
                    "Multi-empresa y multi-sucursal",
                    "Gestiona uno o varios locales con datos separados y una visión central de todo.",
                ),
                _feature(
                    "shield-check",
                    "Datos seguros y aislados",
                    "Arquitectura multi-tenant: la información de cada empresa está protegida y separada.",
                ),
                _feature(
                    "message-circle",
                    "Soporte cercano",
                    "Te acompañamos por WhatsApp, en tu idioma y en tu horario, cuando lo necesites.",
                ),
                _feature(
                    "gift",
                    "Prueba gratis 15 días",
                    "Empieza sin tarjeta y sin compromiso. Decide cuando ya viste el sistema funcionando.",
                ),
                _feature(
                    "globe",
                    "Adaptado a tu país",
                    "Moneda, impuestos y métodos de pago configurables según la región donde operas.",
                ),
                class_name="mt-12 grid grid-cols-1 gap-x-10 gap-y-8 md:grid-cols-2",
            ),
            class_name="mx-auto w-full max-w-5xl px-4 sm:px-6 lg:px-8",
        ),
        id="por-que",
        class_name="scroll-mt-20 bg-slate-50 py-20 sm:py-24",
    )


# ─── CTA final ──────────────────────────────────────────────────────────


def _cta_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.h2(
                    "¿Listo para ordenar tu negocio?",
                    class_name="text-3xl font-extrabold tracking-tight text-white sm:text-4xl",
                    style=_FONT_DISPLAY,
                ),
                rx.el.p(
                    "Empieza hoy con una prueba gratuita de 15 días. Sin tarjeta, sin compromiso.",
                    class_name="mx-auto mt-4 max-w-xl text-base leading-relaxed text-slate-300",
                ),
                rx.el.div(
                    rx.el.a(
                        "Elegir mi sistema",
                        rx.icon("arrow-up", class_name="h-4 w-4"),
                        href="#sistemas",
                        class_name="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-6 py-3 text-sm font-semibold text-slate-900 transition-colors hover:bg-slate-100",
                    ),
                    _wa_button("Hablar por WhatsApp", "click_whatsapp_cta"),
                    class_name="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row",
                ),
                class_name="mx-auto max-w-2xl text-center",
            ),
            class_name="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8",
        ),
        class_name="bg-slate-900 py-20 sm:py-24",
    )


# ─── Footer ─────────────────────────────────────────────────────────────


def _footer_link(text: str, href: str, *, external: bool = False) -> rx.Component:
    extra = {"target": "_blank", "rel": "noopener noreferrer"} if external else {}
    return rx.el.a(
        text,
        href=href,
        class_name="text-sm text-slate-500 transition-colors hover:text-slate-800",
        **extra,
    )


def _footer_col(title: str, *links: rx.Component) -> rx.Component:
    return rx.el.div(
        rx.el.p(
            title,
            class_name="text-sm font-bold text-slate-900",
        ),
        rx.el.div(*links, class_name="mt-4 flex flex-col gap-3"),
    )


def _home_footer() -> rx.Component:
    return rx.el.footer(
        rx.el.div(
            rx.el.div(
                # Marca + descripción
                rx.el.div(
                    rx.el.a(
                        rx.icon("layers", class_name="h-7 w-7 text-indigo-600"),
                        rx.el.span(
                            "TUWAYKIAPP",
                            class_name="text-lg font-extrabold tracking-tight text-slate-900",
                        ),
                        href=_site_href("/"),
                        class_name="inline-flex items-center gap-2.5",
                    ),
                    rx.el.p(
                        "Software de gestión en la nube para negocios de Latinoamérica. "
                        "Un sistema para cada industria.",
                        class_name="mt-3 max-w-xs text-sm leading-relaxed text-slate-600",
                    ),
                    rx.el.a(
                        rx.icon("message-circle", class_name="h-4 w-4"),
                        f"WhatsApp +{WHATSAPP_NUMBER}",
                        href=_WA_URL,
                        target="_blank",
                        rel="noopener noreferrer",
                        class_name="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-emerald-600 hover:text-emerald-700",
                    ),
                    class_name="max-w-sm",
                ),
                # Columnas
                rx.el.div(
                    _footer_col(
                        "Productos",
                        _footer_link("TUWAYKISHOP — Ventas", _site_href("/ventas")),
                        _footer_link("TUWAYKIFOOD — Restobares", _site_href("/food")),
                    ),
                    _footer_col(
                        "Empresa",
                        _footer_link("Nosotros", "#nosotros"),
                        _footer_link("Por qué TUWAYKIAPP", "#por-que"),
                        _footer_link("Contacto", _WA_URL, external=True),
                    ),
                    _footer_col(
                        "Legal",
                        _footer_link("Términos y condiciones", _site_href("/terminos")),
                        _footer_link("Política de privacidad", _site_href("/privacidad")),
                        _footer_link("Política de cookies", _site_href("/cookies")),
                    ),
                    class_name="grid grid-cols-2 gap-8 sm:grid-cols-3",
                ),
                class_name="flex flex-col justify-between gap-12 lg:flex-row",
            ),
            rx.el.div(
                rx.el.p(
                    "TUWAYKIAPP © 2026. Todos los derechos reservados.",
                    class_name="text-sm text-slate-500",
                ),
                rx.el.p(
                    "Creado por Trebor Oscorima",
                    class_name="text-sm text-slate-400",
                ),
                class_name="mt-12 flex flex-col items-start justify-between gap-2 border-t border-slate-200 pt-6 sm:flex-row sm:items-center",
            ),
            class_name="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:px-8",
        ),
        class_name="border-t border-slate-200 bg-white",
    )


# ─── Página ─────────────────────────────────────────────────────────────


def home_page() -> rx.Component:
    """Página principal — sitio de empresa TUWAYKIAPP (TUWAYKISHOP / TUWAYKIFOOD)."""
    return rx.el.div(
        rx.el.style(_global_styles()),
        rx.script(_sw_cleanup_script()),
        rx.script(_analytics_bootstrap_script()),
        rx.script(_cookie_consent_script()),
        *home_jsonld_components(),
        _home_header(),
        rx.el.main(
            _hero_section(),
            _about_section(),
            _products_section(),
            _features_section(),
            _cta_section(),
        ),
        _home_footer(),
        _cookie_consent_banner(),
        class_name="notranslate min-h-screen scroll-smooth bg-white",
        style={"fontFamily": "'Manrope', sans-serif"},
        **{"translate": "no"},
    )
