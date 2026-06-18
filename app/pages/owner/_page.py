import reflex as rx

from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    INPUT_STYLES,
    RADIUS,
    SHADOWS,
    TRANSITIONS,
    TYPOGRAPHY,
)
from ._shared import _app_href, OWNER_LOGIN_PATH
from ._companies_section import _product_tabs, _search_bar, _companies_table, _pagination
from ._action_modal import _action_modal, _reset_password_modal
from ._audit_section import _audit_section
from ._billing_section import _platform_billing_section, _billing_modal


# ─── Vista de acceso denegado ─────────────────────────────

def _access_denied() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("shield-x", class_name="h-16 w-16 text-red-400"),
            rx.el.h2(
                "Acceso Restringido",
                class_name="text-2xl font-bold text-slate-800 mt-4",
            ),
            rx.el.p(
                "Este panel es de uso exclusivo para administradores de la plataforma.",
                class_name=f"{TYPOGRAPHY['body_secondary']} mt-2 text-center max-w-md",
            ),
            rx.el.p(
                "Si llegaste aquí por error, regresa al sistema principal.",
                class_name="text-slate-400 text-sm mt-1 text-center max-w-md",
            ),
            rx.el.a(
                rx.el.button(
                    rx.icon("arrow-left", class_name="h-4 w-4"),
                    "Ir al Sistema de Ventas",
                    class_name=BUTTON_STYLES["primary"],
                ),
                href=_app_href("/"),
                class_name="mt-6",
            ),
            class_name="flex flex-col items-center justify-center py-20",
        ),
        class_name="w-full min-h-screen bg-slate-50 flex items-center justify-center",
        style={"fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif"},
    )


# ═══════════════════════════════════════════════════════════
# LAYOUT INDEPENDIENTE DEL BACKOFFICE
# ═══════════════════════════════════════════════════════════

def _owner_header() -> rx.Component:
    """Header propio del backoffice — completamente independiente del sistema de ventas."""
    return rx.el.header(
        rx.el.div(
            # Logo / Marca del backoffice
            rx.el.div(
                rx.el.div(
                    rx.icon("shield-check", class_name="h-5 w-5 text-white"),
                    class_name=f"p-2 bg-slate-800 {RADIUS['lg']}",
                ),
                rx.el.div(
                    rx.el.span(
                        "TUWAYKIAPP",
                        class_name="text-sm sm:text-base font-bold text-slate-800 tracking-tight",
                    ),
                    rx.el.span(
                        "Admin Plataforma",
                        class_name="text-xs text-slate-400 uppercase tracking-widest",
                    ),
                    class_name="flex flex-col leading-tight",
                ),
                class_name="flex items-center justify-center sm:justify-start gap-3",
            ),
            # Acciones del header — info de usuario + logout + link al sistema
            rx.el.div(
                # Link al sistema de ventas
                rx.el.a(
                    rx.el.button(
                        rx.icon("layout-dashboard", class_name="h-4 w-4"),
                        "Sistema de Ventas",
                        class_name=f"flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 px-3 py-2 {RADIUS['md']} hover:bg-slate-100 {TRANSITIONS['fast']}",
                    ),
                    href=_app_href("/"),
                ),
                # Separador
                rx.el.div(class_name="hidden sm:block w-px h-8 bg-slate-200"),
                # Usuario actual (sesión propia del owner, no del sistema de ventas)
                rx.el.div(
                    rx.image(
                        src="https://api.dicebear.com/9.x/initials/svg?seed=" + State.owner_session_email + "&backgroundColor=1e293b&textColor=ffffff",
                        class_name=f"h-8 w-8 {RADIUS['full']} ring-2 ring-slate-200",
                    ),
                    rx.el.div(
                        rx.el.p(
                            State.owner_session_email,
                            class_name="text-sm font-semibold text-slate-800 truncate max-w-[180px] sm:max-w-none",
                        ),
                        rx.el.p(
                            "Propietario",
                            class_name=f"text-xs text-slate-500 bg-slate-100 px-1.5 py-0.5 {RADIUS['full']} inline-block",
                        ),
                        class_name="flex flex-col",
                    ),
                    class_name="flex items-center gap-2",
                ),
                # Logout del backoffice (no afecta sesión de ventas)
                rx.el.button(
                    rx.icon("log-out", class_name="h-4 w-4"),
                    on_click=State.owner_logout,
                    title="Cerrar sesión del backoffice",
                    aria_label="Cerrar sesión del backoffice",
                    class_name=f"p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 {RADIUS['md']} {TRANSITIONS['fast']}",
                ),
                class_name="flex items-center gap-2 sm:gap-3 flex-wrap justify-center sm:justify-end w-full sm:w-auto",
            ),
            class_name="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-0 w-full",
        ),
        class_name=f"sticky top-0 z-40 bg-white/95 backdrop-blur-sm border-b border-slate-200 {SHADOWS['sm']}",
    )


def _owner_content() -> rx.Component:
    """Contenido principal: tabla de empresas + auditoría."""
    return rx.el.div(
        # Header de la página
        rx.el.div(
            rx.el.div(
                rx.el.h1(
                    "Control de Empresas",
                    class_name="text-xl sm:text-2xl font-bold text-slate-800",
                ),
                rx.el.p(
                    "Administra clientes de Sistema de Ventas y TUWAYKIFOOD — planes, suscripciones y activaciones",
                    class_name=f"{TYPOGRAPHY['body_secondary']} mt-1",
                ),
                class_name="flex flex-col text-center sm:text-left",
            ),
            class_name="mb-5 sm:mb-6",
        ),
        _platform_billing_section(),
        _product_tabs(),
        _search_bar(),
        rx.cond(
            State.owner_loading,
            rx.el.div(
                rx.icon("loader-circle", class_name="h-6 w-6 text-slate-500 animate-spin"),
                rx.el.p("Cargando empresas...", class_name=TYPOGRAPHY["body_secondary"]),
                class_name="flex items-center gap-3 py-8 justify-center",
            ),
            rx.fragment(),
        ),
        _companies_table(),
        _pagination(),
        _audit_section(),
        _action_modal(),
        _reset_password_modal(),
        _billing_modal(),
        class_name="w-full max-w-7xl mx-auto px-3 sm:px-6 py-4 sm:py-6 fade-in-up",
    )


# ─── Página principal ─────────────────────────────────────

def owner_page() -> rx.Component:
    """Mini-sistema independiente del backoffice de owners.

    Layout completamente separado del Sistema de Ventas:
    - Sin sidebar del sistema de ventas
    - Header propio con marca "Admin Plataforma"
    - Fondo y estilo visual diferenciado
    - Login propio e independiente del sistema principal
    - Accesible SOLO para propietarios de plataforma autenticados
    """
    return rx.el.main(
        # Barra superior distintiva (gris oscuro para diferenciarse del sistema)
        rx.el.div(
            class_name="fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-slate-600 via-slate-800 to-slate-600 z-[60]",
        ),
        rx.cond(
            State.is_hydrated,
            rx.cond(
                State.is_owner_authenticated,
                # ───── BACKOFFICE: Layout propio ─────
                rx.el.div(
                    _owner_header(),
                    _owner_content(),
                    class_name="min-h-screen bg-slate-50",
                ),
                # ───── No autenticado en owner → redirigir a login owner ─────
                rx.el.div(
                    rx.el.div(
                        rx.icon("shield-alert", class_name="h-12 w-12 text-slate-400"),
                        rx.el.h2(
                            "Autenticación requerida",
                            class_name="text-xl font-bold text-slate-800 mt-4",
                        ),
                        rx.el.p(
                            "Debes iniciar sesión en el panel de administración.",
                            class_name=f"{TYPOGRAPHY['body_secondary']} mt-2",
                        ),
                        rx.el.a(
                            rx.el.button(
                                rx.icon("log-in", class_name="h-4 w-4"),
                                "Iniciar Sesión",
                                class_name=BUTTON_STYLES["primary"],
                            ),
                            href=OWNER_LOGIN_PATH,
                            class_name="mt-6",
                        ),
                        class_name="flex flex-col items-center justify-center py-20",
                    ),
                    class_name="w-full min-h-screen bg-slate-50 flex items-center justify-center",
                ),
            ),
            # ───── Skeleton loading ─────
            rx.el.div(
                rx.el.div(
                    rx.el.div(class_name="h-16 bg-white border-b border-slate-200"),
                    rx.el.div(
                        rx.el.div(class_name="h-8 w-64 rounded bg-slate-200 animate-pulse"),
                        rx.el.div(class_name="h-4 w-48 rounded bg-slate-200/60 animate-pulse mt-2"),
                        rx.el.div(class_name="h-64 rounded-xl bg-slate-200/30 animate-pulse mt-6"),
                        class_name="max-w-7xl mx-auto px-6 py-6",
                    ),
                    class_name="min-h-screen bg-slate-50",
                ),
            ),
        ),
        class_name="notranslate text-slate-900 w-full min-h-screen",
        style={"fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif"},
        **{"translate": "no"},
    )


# ═══════════════════════════════════════════════════════════
# PÁGINA DE LOGIN DEL OWNER BACKOFFICE
# ═══════════════════════════════════════════════════════════

def owner_login_page() -> rx.Component:
    """Página de login exclusiva del Owner Backoffice.

    Completamente independiente del login del Sistema de Ventas (/ingreso).
    Solo usuarios con is_platform_owner=True pueden acceder.
    """
    return rx.el.main(
        # Barra superior
        rx.el.div(
            class_name="fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-slate-600 via-slate-800 to-slate-600 z-[60]",
        ),
        rx.cond(
            State.is_hydrated,
            rx.cond(
                # Si ya está autenticado como owner, redirigir al backoffice
                State.is_owner_authenticated,
                rx.el.div(
                    rx.el.div(
                        rx.icon("loader-circle", class_name="h-8 w-8 text-slate-400 animate-spin"),
                        rx.el.p(
                            "Redirigiendo al panel...",
                            class_name="text-slate-500 mt-4",
                        ),
                        class_name="flex flex-col items-center justify-center py-20",
                    ),
                    class_name="w-full min-h-screen bg-slate-50 flex items-center justify-center",
                ),
                # Formulario de login
                rx.el.div(
                    rx.el.div(
                        # Logo
                        rx.el.div(
                            rx.el.div(
                                rx.icon("shield-check", class_name="h-7 w-7 sm:h-8 sm:w-8 text-white"),
                                class_name=f"p-3 bg-slate-800 {RADIUS['xl']}",
                            ),
                            rx.el.div(
                                rx.el.span(
                                    "TUWAYKIAPP",
                                    class_name="text-lg sm:text-xl font-bold text-slate-800 tracking-tight",
                                ),
                                rx.el.span(
                                    "Admin Plataforma",
                                    class_name="text-xs text-slate-400 uppercase tracking-widest",
                                ),
                                class_name="flex flex-col leading-tight",
                            ),
                            class_name="flex items-center justify-center gap-3 mb-8 w-full",
                        ),
                        # Título
                        rx.el.h1(
                            "Panel de Administración",
                            class_name="text-xl sm:text-2xl font-bold text-slate-800 text-center",
                        ),
                        rx.el.p(
                            "Ingrese sus credenciales de administrador de plataforma.",
                            class_name=f"{TYPOGRAPHY['body_secondary']} mt-1 mb-6 text-center",
                        ),
                        # Error message
                        rx.cond(
                            State.owner_login_error != "",
                            rx.el.div(
                                rx.el.div(
                                    rx.icon("circle-alert", class_name="h-4 w-4 text-red-500 flex-shrink-0"),
                                    rx.el.p(
                                        State.owner_login_error,
                                        class_name="text-sm text-red-600",
                                    ),
                                    class_name="flex items-center gap-2",
                                ),
                                role="alert",
                                class_name=f"p-3 bg-red-50 border border-red-200 {RADIUS['lg']} mb-4",
                            ),
                        ),
                        # Formulario
                        rx.el.form(
                            rx.el.div(
                                rx.el.label(
                                    "Email o Usuario",
                                    html_for="owner_email",
                                    class_name=f"block {TYPOGRAPHY['label']} mb-1.5",
                                ),
                                rx.el.input(
                                    name="owner_email",
                                    type="text",
                                    placeholder="admin@tuwaykiapp.local",
                                    auto_complete="username",
                                    required=True,
                                    class_name=INPUT_STYLES["default"] + " w-full",
                                ),
                                class_name="mb-4",
                            ),
                            rx.el.div(
                                rx.el.label(
                                    "Contraseña",
                                    html_for="owner_password",
                                    class_name=f"block {TYPOGRAPHY['label']} mb-1.5",
                                ),
                                rx.el.input(
                                    name="owner_password",
                                    type="password",
                                    placeholder="••••••••",
                                    auto_complete="current-password",
                                    required=True,
                                    class_name=INPUT_STYLES["default"] + " w-full",
                                ),
                                class_name="mb-6",
                            ),
                            rx.el.button(
                                rx.cond(
                                    State.owner_login_loading,
                                    rx.fragment(
                                        rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"),
                                        "Verificando...",
                                    ),
                                    rx.fragment(
                                        rx.icon("log-in", class_name="h-4 w-4"),
                                        "Iniciar Sesión",
                                    ),
                                ),
                                type="submit",
                                disabled=State.owner_login_loading,
                                class_name=f"w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-800 text-white font-medium {RADIUS['lg']} hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed {TRANSITIONS['fast']}",
                            ),
                            on_submit=State.owner_login,
                            reset_on_submit=False,
                        ),
                        # Separador
                        rx.el.div(
                            rx.el.div(class_name="flex-1 h-px bg-slate-200"),
                            rx.el.span(
                                "Acceso restringido",
                                class_name="px-3 text-xs text-slate-400 uppercase tracking-wide",
                            ),
                            rx.el.div(class_name="flex-1 h-px bg-slate-200"),
                            class_name="flex items-center mt-6 mb-4",
                        ),
                        rx.el.p(
                            "Este panel es de uso exclusivo para administradores de la plataforma TUWAYKIAPP. "
                            "El acceso no autorizado será registrado.",
                            class_name="text-xs text-slate-400 text-center leading-relaxed",
                        ),
                        class_name=f"w-full max-w-md bg-white {RADIUS['xl']} {SHADOWS['lg']} p-5 sm:p-8 border border-slate-200",
                    ),
                    class_name="w-full min-h-screen bg-slate-50 flex items-center justify-center px-3 sm:px-4",
                ),
            ),
            # Skeleton loading
            rx.el.div(
                rx.el.div(
                    rx.icon("loader-circle", class_name="h-8 w-8 text-slate-300 animate-spin"),
                    class_name="flex items-center justify-center py-20",
                ),
                class_name="w-full min-h-screen bg-slate-50 flex items-center justify-center",
            ),
        ),
        class_name="text-slate-900 w-full min-h-screen",
        style={"fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif"},
    )
