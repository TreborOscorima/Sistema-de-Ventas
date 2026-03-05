"""Página de Política de Cookies — TUWAYKIAPP."""

import reflex as rx

from app.components.legal_layout import legal_page_shell

LAST_UPDATED = "4 de marzo de 2026"


def cookies_page() -> rx.Component:
    """Página pública de Política de Cookies."""
    return legal_page_shell(
        "Política de Cookies",
        LAST_UPDATED,
                    # 1. ¿Qué son las cookies?
                    rx.el.h2("1. ¿Qué son las Cookies?", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "Las cookies son pequeños archivos de texto que se almacenan en su navegador cuando visita un sitio web. "
                        "Se utilizan para recordar preferencias, analizar el uso del sitio y mejorar la experiencia del usuario.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 2. Cookies que utilizamos
                    rx.el.h2("2. Cookies que Utilizamos", class_name="text-xl font-bold text-slate-900 mt-8"),

                    # Esenciales
                    rx.el.h3("2.1 Cookies Esenciales (siempre activas)", class_name="text-lg font-semibold text-slate-800 mt-4"),
                    rx.el.p(
                        "Son necesarias para el funcionamiento básico del sitio. No requieren consentimiento.",
                        class_name="mt-2 text-slate-700 leading-relaxed",
                    ),
                    rx.el.div(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    rx.el.th("Cookie", class_name="text-left px-4 py-2 text-sm font-semibold text-slate-700"),
                                    rx.el.th("Propósito", class_name="text-left px-4 py-2 text-sm font-semibold text-slate-700"),
                                    rx.el.th("Duración", class_name="text-left px-4 py-2 text-sm font-semibold text-slate-700"),
                                ),
                            ),
                            rx.el.tbody(
                                rx.el.tr(
                                    rx.el.td("session_token", class_name="px-4 py-2 text-sm text-slate-600"),
                                    rx.el.td("Autenticación de usuario", class_name="px-4 py-2 text-sm text-slate-600"),
                                    rx.el.td("Sesión", class_name="px-4 py-2 text-sm text-slate-600"),
                                ),
                                rx.el.tr(
                                    rx.el.td("tw_cookie_consent", class_name="px-4 py-2 text-sm text-slate-600"),
                                    rx.el.td("Almacena su elección de cookies", class_name="px-4 py-2 text-sm text-slate-600"),
                                    rx.el.td("365 días", class_name="px-4 py-2 text-sm text-slate-600"),
                                ),
                            ),
                            class_name="w-full",
                        ),
                        class_name="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white",
                    ),

                    # Analítica
                    rx.el.h3("2.2 Cookies de Analítica (requieren consentimiento)", class_name="text-lg font-semibold text-slate-800 mt-6"),
                    rx.el.p(
                        "Nos ayudan a entender cómo los visitantes interactúan con el sitio para mejorar la experiencia.",
                        class_name="mt-2 text-slate-700 leading-relaxed",
                    ),
                    rx.el.div(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    rx.el.th("Cookie", class_name="text-left px-4 py-2 text-sm font-semibold text-slate-700"),
                                    rx.el.th("Proveedor", class_name="text-left px-4 py-2 text-sm font-semibold text-slate-700"),
                                    rx.el.th("Propósito", class_name="text-left px-4 py-2 text-sm font-semibold text-slate-700"),
                                    rx.el.th("Duración", class_name="text-left px-4 py-2 text-sm font-semibold text-slate-700"),
                                ),
                            ),
                            rx.el.tbody(
                                rx.el.tr(
                                    rx.el.td("_ga, _ga_*", class_name="px-4 py-2 text-sm text-slate-600"),
                                    rx.el.td("Google Analytics 4", class_name="px-4 py-2 text-sm text-slate-600"),
                                    rx.el.td("Medición de tráfico y comportamiento", class_name="px-4 py-2 text-sm text-slate-600"),
                                    rx.el.td("2 años", class_name="px-4 py-2 text-sm text-slate-600"),
                                ),
                            ),
                            class_name="w-full",
                        ),
                        class_name="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white",
                    ),

                    # Marketing
                    rx.el.h3("2.3 Cookies de Marketing (requieren consentimiento)", class_name="text-lg font-semibold text-slate-800 mt-6"),
                    rx.el.p(
                        "Permiten medir la efectividad de campañas publicitarias y mostrar contenido relevante.",
                        class_name="mt-2 text-slate-700 leading-relaxed",
                    ),
                    rx.el.div(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    rx.el.th("Cookie", class_name="text-left px-4 py-2 text-sm font-semibold text-slate-700"),
                                    rx.el.th("Proveedor", class_name="text-left px-4 py-2 text-sm font-semibold text-slate-700"),
                                    rx.el.th("Propósito", class_name="text-left px-4 py-2 text-sm font-semibold text-slate-700"),
                                    rx.el.th("Duración", class_name="text-left px-4 py-2 text-sm font-semibold text-slate-700"),
                                ),
                            ),
                            rx.el.tbody(
                                rx.el.tr(
                                    rx.el.td("_fbp", class_name="px-4 py-2 text-sm text-slate-600"),
                                    rx.el.td("Meta (Facebook)", class_name="px-4 py-2 text-sm text-slate-600"),
                                    rx.el.td("Seguimiento de conversiones", class_name="px-4 py-2 text-sm text-slate-600"),
                                    rx.el.td("3 meses", class_name="px-4 py-2 text-sm text-slate-600"),
                                ),
                            ),
                            class_name="w-full",
                        ),
                        class_name="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white",
                    ),

                    # 3. Cómo gestionamos el consentimiento
                    rx.el.h2("3. Gestión del Consentimiento", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "Al visitar nuestro sitio por primera vez, verá un banner de cookies que le permite:",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),
                    rx.el.ul(
                        rx.el.li(rx.el.strong("Aceptar todas:"), " se activan cookies esenciales, de analítica y de marketing."),
                        rx.el.li(rx.el.strong("Solo esenciales:"), " solo se activan las cookies necesarias para el funcionamiento del sitio."),
                        class_name="mt-2 list-disc pl-6 space-y-1 text-slate-700",
                    ),
                    rx.el.p(
                        "Las cookies de analítica (Google Analytics 4) y marketing (Meta Pixel) NO se cargan hasta que usted "
                        "dé su consentimiento explícito haciendo clic en \"Aceptar todas\".",
                        class_name="mt-3 text-slate-700 leading-relaxed font-medium",
                    ),

                    # 4. Cómo cambiar preferencias
                    rx.el.h2("4. Cómo Cambiar sus Preferencias", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "Puede cambiar sus preferencias de cookies en cualquier momento:",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),
                    rx.el.ul(
                        rx.el.li("Borrando las cookies de su navegador (se le mostrará el banner nuevamente)."),
                        rx.el.li("Utilizando la configuración de privacidad de su navegador."),
                        rx.el.li("Eliminando el valor 'tw_cookie_consent' del almacenamiento local de su navegador."),
                        class_name="mt-2 list-disc pl-6 space-y-1 text-slate-700",
                    ),

                    # 5. localStorage
                    rx.el.h2("5. Almacenamiento Local (localStorage)", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "Además de cookies, utilizamos localStorage del navegador para almacenar preferencias de la interfaz "
                        "y datos de eventos de analítica en modo de depuración. Estos datos permanecen en su dispositivo y "
                        "no se transmiten a terceros sin su consentimiento.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 6. Contacto
                    rx.el.h2("6. Contacto", class_name="text-xl font-bold text-slate-900 mt-8 mb-3"),
                    rx.el.p(
                        "Para consultas sobre nuestra política de cookies:",
                        class_name="text-slate-700 leading-relaxed",
                    ),
                    rx.el.ul(
                        rx.el.li("WhatsApp: +54 9 11 6837-6517"),
                        rx.el.li(rx.el.span("Sitio web: ", rx.el.a("tuwayki.app", href="https://tuwayki.app", class_name="text-indigo-600 hover:underline"))),
                        class_name="mt-2 list-disc pl-6 space-y-1 text-slate-700",
                    ),

    )
