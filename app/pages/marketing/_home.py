"""Home page — selector de productos TUWAYKI."""

import reflex as rx

from app.constants import WHATSAPP_NUMBER

from ._state import _site_href, _food_href, _wa_link
from ._scripts import (
    _global_styles,
    _sw_cleanup_script,
    _analytics_bootstrap_script,
    _cookie_consent_script,
    _cookie_consent_banner,
    _track_event_script,
)


def _home_header() -> rx.Component:
    return rx.el.header(
        rx.el.div(
            rx.el.a(
                rx.icon("layers", class_name="h-8 w-8 text-indigo-600"),
                rx.el.span(
                    "TUWAYKI",
                    class_name="text-2xl font-extrabold tracking-tight text-slate-900",
                ),
                href=_site_href("/"),
                class_name="flex items-center gap-2.5",
            ),
            rx.el.a(
                rx.icon("message-circle", class_name="h-4 w-4"),
                "WhatsApp",
                href=f"https://wa.me/{WHATSAPP_NUMBER}",
                target="_blank",
                rel="noopener noreferrer",
                on_click=rx.call_script(_track_event_script("click_whatsapp_home", "home_header")),
                class_name="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-700",
            ),
            class_name="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8",
        ),
        class_name="fixed top-0 left-0 right-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur",
    )


def _product_card_ventas() -> rx.Component:
    chips = ["POS + Stock", "Caja y arqueo", "Reservas", "Reportes", "Multi-sucursal"]
    return rx.el.a(
        rx.el.div(
            rx.el.div(
                rx.icon("box", class_name="h-10 w-10 text-indigo-600"),
                class_name="inline-flex items-center justify-center rounded-2xl bg-indigo-50 p-3",
            ),
            rx.el.div(
                rx.el.h2(
                    "TUWAYKIAPP",
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
            class_name="p-8 sm:p-10",
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
                rx.el.h2(
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
            class_name="p-8 sm:p-10",
        ),
        href=_site_href("/food"),
        on_click=rx.call_script(_track_event_script("click_product_food", "home_selector")),
        class_name=(
            "group block rounded-3xl border-2 border-slate-200 bg-white "
            "transition-all duration-200 hover:border-orange-400 hover:shadow-xl hover:-translate-y-1"
        ),
    )


def _home_footer() -> rx.Component:
    return rx.el.footer(
        rx.el.div(
            rx.el.p(
                "TUWAYKI © 2026 · Todos los derechos reservados.",
                class_name="text-sm text-slate-400",
            ),
            rx.el.div(
                rx.el.a(
                    "Términos",
                    href=_site_href("/terminos"),
                    class_name="text-sm text-slate-400 transition-colors hover:text-slate-600",
                ),
                rx.el.a(
                    "Privacidad",
                    href=_site_href("/privacidad"),
                    class_name="text-sm text-slate-400 transition-colors hover:text-slate-600",
                ),
                class_name="flex gap-6",
            ),
            class_name="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-6 sm:px-6 lg:px-8",
        ),
        class_name="border-t border-slate-200 bg-white",
    )


def home_page() -> rx.Component:
    """Página principal — selector de productos TUWAYKI."""
    return rx.el.div(
        rx.el.style(_global_styles()),
        rx.script(_sw_cleanup_script()),
        rx.script(_analytics_bootstrap_script()),
        rx.script(_cookie_consent_script()),
        _home_header(),
        rx.el.main(
            rx.el.div(
                # Badge
                rx.el.div(
                    rx.el.span(
                        rx.icon("layers", class_name="h-4 w-4 text-indigo-600"),
                        rx.el.span(
                            "Elige tu producto",
                            class_name="text-xs font-bold text-indigo-600 uppercase tracking-widest",
                        ),
                        class_name="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-4 py-1.5",
                    ),
                    class_name="flex justify-center",
                ),
                # Headline
                rx.el.h1(
                    "¿Qué tipo de negocio tienes?",
                    class_name="mt-6 text-center text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                rx.el.p(
                    "Tenemos un sistema diseñado para tu industria. "
                    "Elige el que corresponde a tu negocio.",
                    class_name="mt-4 text-center text-base text-slate-600 sm:text-lg",
                ),
                # Cards
                rx.el.div(
                    _product_card_ventas(),
                    _product_card_food(),
                    class_name="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2",
                ),
                # Sub-nota
                rx.el.p(
                    "¿Tienes dudas? ",
                    rx.el.a(
                        "Escríbenos por WhatsApp",
                        href=f"https://wa.me/{WHATSAPP_NUMBER}",
                        target="_blank",
                        rel="noopener noreferrer",
                        class_name="font-semibold text-emerald-600 underline underline-offset-2 hover:text-emerald-700",
                    ),
                    " y te orientamos.",
                    class_name="mt-10 text-center text-sm text-slate-500",
                ),
                class_name="mx-auto w-full max-w-4xl px-4 py-28 sm:px-6 lg:px-8",
            ),
        ),
        _home_footer(),
        _cookie_consent_banner(),
        class_name="notranslate min-h-screen bg-slate-50",
        style={"fontFamily": "'Manrope', sans-serif"},
        **{"translate": "no"},
    )
