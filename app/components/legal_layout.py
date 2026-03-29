"""Componentes compartidos para páginas legales — TUWAYKIAPP.

Estilo unificado con la landing: mismo header, footer consistente, tipografía Space Grotesk.
"""

import os

import reflex as rx

from app.components.ui import BUTTON_STYLES

PUBLIC_SITE_URL = (os.getenv("PUBLIC_SITE_URL") or "").strip().rstrip("/")
PUBLIC_APP_URL = (os.getenv("PUBLIC_APP_URL") or "").strip().rstrip("/")


def _site_href(path: str = "/") -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{PUBLIC_SITE_URL}{normalized}" if PUBLIC_SITE_URL else normalized


def _app_href(path: str = "/") -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{PUBLIC_APP_URL}{normalized}" if PUBLIC_APP_URL else normalized


def legal_header() -> rx.Component:
    """Header para páginas legales — mismo estilo que la landing."""
    return rx.el.header(
        rx.el.div(
            rx.el.a(
                rx.icon("box", class_name="h-8 w-8 text-indigo-600"),
                rx.el.span(
                    "TUWAYKIAPP",
                    class_name="text-2xl font-extrabold tracking-tight text-slate-900",
                ),
                href=_site_href("/"),
                class_name="flex items-center gap-2.5",
            ),
            rx.el.div(
                rx.el.a(
                    "Ingresar",
                    href=_app_href("/"),
                    class_name=BUTTON_STYLES["link_primary"],
                ),
                rx.el.a(
                    "Iniciar prueba gratis",
                    href=_app_href("/registro"),
                    class_name=BUTTON_STYLES["success"],
                ),
                class_name="flex items-center gap-3",
            ),
            class_name="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8",
        ),
        class_name="sticky top-0 z-50 border-b border-slate-200/80 bg-white/95 backdrop-blur-sm",
    )


def legal_back_link() -> rx.Component:
    return rx.el.a(
        rx.icon("arrow-left", class_name="h-4 w-4"),
        "Volver al inicio",
        href=_site_href("/"),
        class_name="inline-flex items-center gap-2 text-sm font-medium text-emerald-600 hover:text-emerald-700 transition-colors",
    )


def legal_footer() -> rx.Component:
    """Footer para páginas legales — consistente con la landing."""
    return rx.el.footer(
        rx.el.div(
            rx.el.div(
                rx.el.a(
                    rx.icon("box", class_name="h-6 w-6 text-indigo-600"),
                    rx.el.span(
                        "TUWAYKIAPP",
                        class_name="text-base font-extrabold tracking-tight text-slate-900",
                    ),
                    href=_site_href("/"),
                    class_name="inline-flex items-center gap-2",
                ),
                rx.el.div(
                    rx.el.a(
                        "Términos y condiciones",
                        href=_site_href("/terminos"),
                        class_name="text-sm text-slate-500 hover:text-slate-700 transition-colors",
                    ),
                    rx.el.span("·", class_name="text-slate-300"),
                    rx.el.a(
                        "Política de privacidad",
                        href=_site_href("/privacidad"),
                        class_name="text-sm text-slate-500 hover:text-slate-700 transition-colors",
                    ),
                    rx.el.span("·", class_name="text-slate-300"),
                    rx.el.a(
                        "Política de cookies",
                        href=_site_href("/cookies"),
                        class_name="text-sm text-slate-500 hover:text-slate-700 transition-colors",
                    ),
                    class_name="flex flex-wrap items-center gap-2",
                ),
                class_name="flex flex-col items-center gap-4 sm:flex-row sm:justify-between",
            ),
            rx.el.div(
                rx.el.p(
                    "TUWAYKIAPP © 2026. Todos los derechos reservados.",
                    class_name="text-sm text-slate-400 text-center",
                ),
                class_name="mt-4 border-t border-slate-100 pt-4",
            ),
            class_name="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 lg:px-8",
        ),
        class_name="border-t border-slate-200 bg-white",
    )


def legal_page_shell(title: str, last_updated: str, *content: rx.Component) -> rx.Component:
    """Wrapper completo para una página legal."""
    return rx.el.div(
        legal_header(),
        rx.el.main(
            rx.el.div(
                legal_back_link(),
                rx.el.h1(
                    title,
                    class_name="mt-6 text-3xl font-extrabold tracking-tight text-slate-900 font-grotesk",
                ),
                rx.el.p(
                    f"Última actualización: {last_updated}",
                    class_name="mt-2 text-sm text-slate-500",
                ),
                rx.el.div(
                    *content,
                    class_name="prose max-w-none",
                ),
                class_name="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 lg:px-8",
            ),
            class_name="min-h-screen bg-slate-50",
        ),
        legal_footer(),
        class_name="min-h-screen bg-slate-50",
    )
