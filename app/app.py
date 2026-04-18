import os

import reflex as rx
import app.models  # Importar modelos para que Reflex detecte las tablas

# Evitar warnings de metadata duplicada en Reflex/SQLAlchemy.
rx.ModelRegistry.models = {rx.Model}
rx.ModelRegistry._metadata = rx.Model.metadata

# IMPORTANTE: registrar listeners de aislamiento multi-tenant ANTES de cualquier query.
# El side-effect fue removido de app/utils/db.py para que los tests no dependan de
# import-order. Ahora es responsabilidad explícita del bootstrap.
from app.utils.tenant import register_tenant_listeners
register_tenant_listeners()

from app.state import State
from app.components.sidebar import sidebar
from app.pages.ingreso import ingreso_page
from app.pages.compras import compras_page
from app.pages.reposicion import reposicion_page
from app.pages.venta import venta_page
from app.pages.inventario import inventario_page
from app.pages.caja import cashbox_page
from app.pages.historial import historial_page
from app.pages.configuracion import configuracion_page
from app.pages.cambiar_contrasena import cambiar_contrasena_page
from app.pages.login import login_page
from app.pages.periodo_prueba_finalizado import periodo_prueba_finalizado_page
from app.pages.cuenta_suspendida import cuenta_suspendida_page
from app.pages.registro import registro_page
from app.pages.marketing import marketing_page
from app.pages.terminos import terminos_page
from app.pages.privacidad import privacidad_page
from app.pages.cookies import cookies_page
from app.pages.servicios import servicios_page
from app.pages.cuentas import cuentas_page
from app.pages.clientes import clientes_page
from app.pages.dashboard import dashboard_page
from app.pages.reportes import reportes_page
from app.pages.documentos_fiscales import documentos_fiscales_page
from app.pages.owner import owner_page, owner_login_page
from app.components.notification import NotificationHolder
from app.api import health_app

from app.utils.env import APP_SURFACE

PUBLIC_SITE_URL = (os.getenv("PUBLIC_SITE_URL") or "https://tuwayki.app").strip().rstrip("/")
LANDING_TITLE = "TUWAYKIAPP | Sistema de Ventas para tiendas, servicios y reservas"
LANDING_DESCRIPTION = (
    "Centraliza ventas, caja, inventario, clientes y reservas en una sola plataforma SaaS "
    "multiempresa, segura y lista para escalar."
)
LANDING_IMAGE = f"{PUBLIC_SITE_URL}/dashboard-hero-real.png"


def _landing_meta(canonical_url: str, *, indexable: bool = True) -> list[dict | rx.Component]:
    return [
        rx.el.link(rel="canonical", href=canonical_url),
        {"name": "robots", "content": "index,follow" if indexable else "noindex,follow"},
        {"property": "og:type", "content": "website"},
        {"property": "og:title", "content": LANDING_TITLE},
        {"property": "og:description", "content": LANDING_DESCRIPTION},
        {"property": "og:url", "content": canonical_url},
        {"property": "og:image", "content": LANDING_IMAGE},
        {"name": "twitter:card", "content": "summary_large_image"},
        {"name": "twitter:title", "content": LANDING_TITLE},
        {"name": "twitter:description", "content": LANDING_DESCRIPTION},
        {"name": "twitter:image", "content": LANDING_IMAGE},
    ]


def cashbox_banner() -> rx.Component:
    """Banner de advertencia que solicita apertura de caja cuando está cerrada."""
    return rx.cond(
        State.cashbox_is_open_cached,
        rx.fragment(),
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("triangle-alert", class_name="h-5 w-5 text-amber-600"),
                    rx.el.div(
                        rx.el.p(
                            "Apertura de caja requerida",
                            class_name="font-semibold text-amber-800",
                        ),
                        rx.el.p(
                            "Ingresa el monto inicial para comenzar la jornada. Sin apertura no podrás vender ni gestionar la caja.",
                            class_name="text-sm text-amber-700",
                        ),
                        class_name="flex flex-col gap-1",
                    ),
                    class_name="flex items-start gap-3",
                ),
                rx.el.form(
                    rx.el.input(
                        name="amount",
                        type="number",
                        step="0.01",
                        placeholder="Caja inicial (ej: 150.00)",
                        class_name="w-full md:w-52 h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                    ),
                    rx.el.button(
                        rx.icon("play", class_name="h-4 w-4"),
                        "Aperturar caja",
                        type="submit",
                        class_name="flex items-center gap-2 h-10 px-4 rounded-md bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700",
                    ),
                    on_submit=State.handle_cashbox_form_submit,
                    class_name="flex flex-col md:flex-row items-stretch md:items-center gap-3",
                ),
                class_name="flex flex-col md:flex-row justify-between gap-4",
            ),
            class_name="bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 rounded-xl shadow-sm",
        ),
    )


def _toast_provider() -> rx.Component:
    """Proveedor global de notificaciones toast (posición, estilos y duración)."""
    return rx.toast.provider(
        position="top-center",  # top-center garantiza visibilidad sobre cualquier modal/overlay
        close_button=True,
        rich_colors=True,
        toast_options=rx.toast.options(
            duration=4000,
            style={
                "background": "#111827",
                "color": "white",
                "fontSize": "16px",
                "padding": "14px 24px",
                "borderRadius": "12px",
                "boxShadow": "0 25px 60px rgba(15,23,42,0.45)",
                "border": "1px solid rgba(255,255,255,0.15)",
                "textAlign": "center",
                "zIndex": "2147483647",  # max z-index — siempre sobre modales
            },
        ),
    )



def _content_skeleton() -> rx.Component:
    """Skeleton solo para el área de contenido (sin sidebar)."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(class_name="h-6 w-48 rounded bg-slate-200 animate-pulse"),
            rx.el.div(class_name="h-4 w-32 rounded bg-slate-200/60 animate-pulse mt-2"),
            rx.el.div(
                *[rx.el.div(class_name="h-24 rounded-xl bg-slate-200/40 animate-pulse") for _ in range(3)],
                class_name="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6",
            ),
            rx.el.div(class_name="h-64 rounded-xl bg-slate-200/30 animate-pulse mt-6"),
            class_name="w-full max-w-5xl p-4 sm:p-6",
        ),
        class_name="flex-1 h-full overflow-y-auto",
    )


def authenticated_layout(page_content: rx.Component) -> rx.Component:
    """Layout optimizado para SPA: Sidebar fijo y persistente.

    Los elementos estáticos (sidebar, barra gradiente, toasts) viven
    FUERA de la condición is_hydrated para que React jamás los destruya
    ni recree al navegar entre rutas, eliminando el parpadeo de 3-4 s.
    """
    return rx.el.main(
        # 1. ELEMENTOS ESTÁTICOS: Fuera de la hidratación para evitar
        #    que React los destruya/recree al cambiar de ruta.
        # Tooltip global + runtime sync se sirven desde /assets estático:
        # navegador los cachea (immutable) en lugar de re-parsear inline en cada HTML.
        rx.el.link(rel="stylesheet", href="/css/twk-tooltip.css"),
        rx.script(src="/js/twk-tooltip.js", defer=True),
        rx.el.button(
            "sync",
            on_click=State.handle_cross_tab_runtime_sync,
            custom_attrs={
                "data-twk-runtime-sync": "1",
                "aria-hidden": "true",
                "tabindex": "-1",
            },
            type="button",
            class_name="hidden",
        ),
        rx.script(src="/js/twk-runtime-sync.js", defer=True),
        rx.el.div(
            class_name=(
                "fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r "
                "from-amber-400 via-rose-500 to-indigo-500 z-[60]"
            ),
        ),
        sidebar(),
        _toast_provider(),
        NotificationHolder(),

        # 2. ÁREA DE CONTENIDO DINÁMICO
        rx.el.div(
            rx.cond(
                State.is_hydrated,
                rx.cond(
                    State.is_authenticated,
                    rx.el.div(
                        rx.cond(State.runtime_ctx_loaded, cashbox_banner(), rx.fragment()),
                        rx.cond(
                            State.navigation_items.length() == 0,
                            rx.el.div(
                                rx.el.h1(
                                    "Acceso restringido",
                                    class_name="text-2xl font-bold text-red-600",
                                ),
                                rx.el.p(
                                    "Tu usuario no tiene modulos habilitados. Solicita permisos al administrador.",
                                    class_name="text-slate-600 mt-2 text-center",
                                ),
                                class_name="flex flex-col items-center justify-center h-full p-6",
                            ),
                            page_content,
                        ),
                        class_name="w-full h-full flex flex-col gap-4 p-4 sm:p-6",
                    ),
                    login_page(),
                ),
                # Skeleton solo en el área de contenido
                _content_skeleton(),
            ),
            class_name=rx.cond(
                State.sidebar_open,
                "h-screen bg-slate-50 overflow-y-auto overscroll-y-contain transition-[margin] duration-300 md:ml-64 xl:ml-72",
                "h-screen bg-slate-50 overflow-y-auto overscroll-y-contain transition-[margin] duration-300",
            ),
            style={"height": "100dvh"},
        ),
        # SIN 'flex' para preservar el block-model y auto-fill del ancho
        class_name="text-slate-900 w-full h-screen",
        style={
            "fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif",
            "height": "100dvh",
        },
    )


def index() -> rx.Component:
    """Página principal - landing de marketing."""
    return marketing_page()


def page_ingreso() -> rx.Component:
    return authenticated_layout(ingreso_page())


def page_compras() -> rx.Component:
    return authenticated_layout(compras_page())


def page_reposicion() -> rx.Component:
    return authenticated_layout(reposicion_page())


def page_venta() -> rx.Component:
    return authenticated_layout(venta_page())


def page_caja() -> rx.Component:
    return authenticated_layout(cashbox_page())


def page_clientes() -> rx.Component:
    return authenticated_layout(clientes_page())


def page_cuentas() -> rx.Component:
    return authenticated_layout(cuentas_page())


def page_dashboard() -> rx.Component:
    return authenticated_layout(dashboard_page())


def page_reportes() -> rx.Component:
    return authenticated_layout(reportes_page())


def page_inventario() -> rx.Component:
    return authenticated_layout(inventario_page())


def page_historial() -> rx.Component:
    return authenticated_layout(historial_page())


def page_servicios() -> rx.Component:
    return authenticated_layout(servicios_page())


def page_configuracion() -> rx.Component:
    return authenticated_layout(configuracion_page())


def page_documentos_fiscales() -> rx.Component:
    return authenticated_layout(documentos_fiscales_page())


def page_cambiar_contrasena() -> rx.Component:
    return cambiar_contrasena_page()

def page_periodo_prueba_finalizado() -> rx.Component:
    return periodo_prueba_finalizado_page()

def page_cuenta_suspendida() -> rx.Component:
    return cuenta_suspendida_page()

def page_registro() -> rx.Component:
    return registro_page()


def page_login() -> rx.Component:
    """Página de login del sistema (superficie app/sys)."""
    return authenticated_layout(rx.fragment())


def page_marketing() -> rx.Component:
    return marketing_page()

def page_terminos() -> rx.Component:
    return terminos_page()

def page_privacidad() -> rx.Component:
    return privacidad_page()

def page_cookies() -> rx.Component:
    return cookies_page()


def page_owner_backoffice() -> rx.Component:
    return owner_page()


app = rx.App(
    theme=rx.theme(appearance="light"),
    api_transformer=health_app,
    head_components=[
        # Accesibilidad + estilos base (cacheables, Cache-Control immutable en nginx).
        rx.el.link(rel="stylesheet", href="/css/accessibility.css"),
        rx.el.link(rel="stylesheet", href="/css/twk-app.css"),
        # Preconnect + Google Fonts (display=swap evita FOIT).
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
        # Scripts globales (defer → no bloquean render). Contenido idempotente.
        rx.script(src="/js/twk-sidebar-scroll.js", defer=True),
        rx.script(src="/js/twk-keyboard-shortcuts.js", defer=True),
    ],
)

PRIVATE_META = [{"name": "robots", "content": "noindex,nofollow"}]


def page_owner_login() -> rx.Component:
    return owner_login_page()


def _add_private_page(
    component,
    *,
    route: str,
    title: str,
    on_load=None,
):
    kwargs = {
        "route": route,
        "title": title,
        "meta": PRIVATE_META,
    }
    if on_load is not None:
        kwargs["on_load"] = on_load
    app.add_page(component, **kwargs)


def _register_landing_routes():
    if APP_SURFACE == "landing":
        app.add_page(
            page_marketing,
            route="/",
            title=LANDING_TITLE,
            description=LANDING_DESCRIPTION,
            image=LANDING_IMAGE,
            meta=_landing_meta(f"{PUBLIC_SITE_URL}/", indexable=True),
        )
        # Alias temporal de compatibilidad.
        app.add_page(
            page_marketing,
            route="/home",
            title=LANDING_TITLE,
            description=LANDING_DESCRIPTION,
            image=LANDING_IMAGE,
            meta=_landing_meta(f"{PUBLIC_SITE_URL}/", indexable=False),
        )
    else:
        # Modo all: mantener landing en /home hasta completar migración de dominios.
        app.add_page(
            page_marketing,
            route="/home",
            title=LANDING_TITLE,
            description=LANDING_DESCRIPTION,
            image=LANDING_IMAGE,
            meta=_landing_meta(f"{PUBLIC_SITE_URL}/", indexable=False),
        )

    # Páginas legales públicas (indexables en todas las superficies).
    _legal_indexable = APP_SURFACE == "landing"
    app.add_page(
        page_terminos,
        route="/terminos",
        title="Términos y Condiciones - TUWAYKIAPP",
        description="Términos y condiciones de uso de TUWAYKIAPP.",
        meta=_landing_meta(f"{PUBLIC_SITE_URL}/terminos", indexable=_legal_indexable),
    )
    app.add_page(
        page_privacidad,
        route="/privacidad",
        title="Política de Privacidad - TUWAYKIAPP",
        description="Política de privacidad de TUWAYKIAPP.",
        meta=_landing_meta(f"{PUBLIC_SITE_URL}/privacidad", indexable=_legal_indexable),
    )
    app.add_page(
        page_cookies,
        route="/cookies",
        title="Política de Cookies - TUWAYKIAPP",
        description="Política de cookies de TUWAYKIAPP.",
        meta=_landing_meta(f"{PUBLIC_SITE_URL}/cookies", indexable=_legal_indexable),
    )


def _register_app_routes():
    _add_private_page(
        page_login,
        route="/login",
        title="Iniciar sesión - TUWAYKIAPP",
        on_load=State.page_init_login,
    )
    _add_private_page(
        page_cambiar_contrasena,
        route="/cambiar-clave",
        title="Cambiar Contrasena - TUWAYKIAPP",
        on_load=State.page_init_cambiar_clave,
    )
    _add_private_page(
        page_periodo_prueba_finalizado,
        route="/periodo-prueba-finalizado",
        title="Periodo de Prueba Finalizado - TUWAYKIAPP",
    )
    _add_private_page(
        page_cuenta_suspendida,
        route="/cuenta-suspendida",
        title="Cuenta Suspendida - TUWAYKIAPP",
    )
    _add_private_page(
        page_registro,
        route="/registro",
        title="Registro - TUWAYKIAPP",
    )

    _add_private_page(
        page_ingreso,
        route="/ingreso",
        title="Compras e Ingresos - TUWAYKIAPP",
        on_load=State.page_init_ingreso,
    )
    _add_private_page(
        page_compras,
        route="/compras",
        title="Compras - TUWAYKIAPP",
        on_load=State.page_init_compras,
    )
    _add_private_page(
        page_reposicion,
        route="/reposicion",
        title="Reposición Automática - TUWAYKIAPP",
    )
    _add_private_page(
        page_venta,
        route="/venta",
        title="Venta - TUWAYKIAPP",
        on_load=State.page_init_venta,
    )
    _add_private_page(
        page_caja,
        route="/caja",
        title="Gestión de Caja - TUWAYKIAPP",
        on_load=State.page_init_caja,
    )
    _add_private_page(
        page_clientes,
        route="/clientes",
        title="Clientes | Sistema de Ventas",
        on_load=State.page_init_clientes,
    )
    _add_private_page(
        page_cuentas,
        route="/cuentas",
        title="Cuentas Corrientes | Sistema de Ventas",
        on_load=State.page_init_cuentas,
    )
    _add_private_page(
        page_dashboard,
        route="/",
        title="Dashboard - TUWAYKIAPP",
        on_load=State.page_init_default,
    )
    _add_private_page(
        page_dashboard,
        route="/dashboard",
        title="Dashboard - TUWAYKIAPP",
        on_load=State.page_init_default,
    )
    _add_private_page(
        page_inventario,
        route="/inventario",
        title="Inventario - TUWAYKIAPP",
        on_load=State.page_init_inventario,
    )
    _add_private_page(
        page_historial,
        route="/historial",
        title="Historial - TUWAYKIAPP",
        on_load=State.page_init_historial,
    )
    _add_private_page(
        page_reportes,
        route="/reportes",
        title="Reportes - TUWAYKIAPP",
        on_load=State.page_init_reportes,
    )
    _add_private_page(
        page_servicios,
        route="/servicios",
        title="Servicios - TUWAYKIAPP",
        on_load=State.page_init_servicios,
    )
    _add_private_page(
        page_configuracion,
        route="/configuracion",
        title="Configuración - TUWAYKIAPP",
        on_load=State.page_init_configuracion,
    )
    _add_private_page(
        page_documentos_fiscales,
        route="/documentos-fiscales",
        title="Documentos Fiscales - TUWAYKIAPP",
        on_load=State.page_init_documentos_fiscales,
    )


def _register_owner_routes():
    # Rutas legacy (compatibilidad) y rutas cortas para admin.tuwayki.app.
    _add_private_page(
        page_owner_backoffice,
        route="/owner",
        title="Panel Owner - TUWAYKIAPP",
        on_load=State.page_init_owner,
    )
    _add_private_page(
        page_owner_login,
        route="/owner/login",
        title="Login - Platform Admin",
        on_load=State.page_init_owner_login,
    )

    if APP_SURFACE == "owner":
        _add_private_page(
            page_owner_backoffice,
            route="/",
            title="Panel Owner - TUWAYKIAPP",
            on_load=State.page_init_owner,
        )
        _add_private_page(
            page_owner_login,
            route="/login",
            title="Login - Platform Admin",
            on_load=State.page_init_owner_login,
        )


if APP_SURFACE in {"all", "landing"}:
    _register_landing_routes()

if APP_SURFACE in {"all", "app"}:
    _register_app_routes()

if APP_SURFACE in {"all", "owner"}:
    _register_owner_routes()
