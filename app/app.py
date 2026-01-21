import reflex as rx
import app.models  # Importar modelos para que Reflex detecte las tablas
from app.state import State
from app.components.sidebar import sidebar
from app.pages.ingreso import ingreso_page
from app.pages.venta import venta_page
from app.pages.inventario import inventario_page
from app.pages.caja import cashbox_page
from app.pages.historial import historial_page
from app.pages.configuracion import configuracion_page
from app.pages.cambiar_contrasena import cambiar_contrasena_page
from app.pages.login import login_page
from app.pages.servicios import servicios_page
from app.pages.cuentas import cuentas_page
from app.pages.clientes import clientes_page
from app.pages.dashboard import dashboard_page
from app.pages.reportes import reportes_page
from app.components.notification import NotificationHolder


def cashbox_banner() -> rx.Component:
    return rx.cond(
        State.cashbox_is_open,
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
                rx.el.div(
                    rx.el.input(
                        type="number",
                        step="0.01",
                        placeholder="Caja inicial (ej: 150.00)",
                        value=State.cashbox_open_amount_input,
                        on_change=State.set_cashbox_open_amount_input,
                        class_name="w-full md:w-52 p-2 border rounded-md shadow-sm focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400",
                    ),
                    rx.el.button(
                        rx.icon("play", class_name="h-4 w-4"),
                        "Aperturar caja",
                        on_click=State.open_cashbox_session,
                        class_name="flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 shadow min-h-[42px]",
                    ),
                    class_name="flex flex-col md:flex-row items-stretch md:items-center gap-3",
                ),
                class_name="flex flex-col md:flex-row justify-between gap-4",
            ),
            class_name="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-lg shadow-sm",
        ),
    )


def currency_selector() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("coins", class_name="h-5 w-5 text-amber-600"),
            rx.el.span("Moneda de trabajo", class_name="text-sm font-semibold text-gray-800"),
            class_name="flex items-center gap-2",
        ),
        rx.el.select(
            rx.foreach(
                State.available_currencies,
                lambda currency: rx.el.option(currency["name"], value=currency["code"]),
            ),
            value=State.selected_currency_code,
            on_change=State.set_currency,
            class_name="w-full sm:w-auto p-2 border rounded-md bg-white",
        ),
        rx.el.span(
            "Mostrando importes en ",
            rx.el.span(State.currency_name, class_name="font-semibold"),
            class_name="text-sm text-gray-600",
        ),
        class_name="flex flex-col sm:flex-row sm:items-center gap-3 bg-white border rounded-lg shadow-sm p-4",
    )


def _toast_provider() -> rx.Component:
    return rx.toast.provider(
        position="bottom-center",
        close_button=True,
        rich_colors=True,
        toast_options=rx.toast.options(
            duration=4000,
            style={
                "background": "#111827",
                "color": "white",
                "fontSize": "18px",
                "padding": "18px 28px",
                "borderRadius": "14px",
                "boxShadow": "0 25px 60px rgba(15,23,42,0.35)",
                "border": "1px solid rgba(255,255,255,0.15)",
                "textAlign": "center",
            },
        ),
    )


# Mapeo de rutas a páginas
ROUTE_TO_PAGE = {
    "/": "Ingreso",
    "/ingreso": "Ingreso",
    "/venta": "Venta",
    "/caja": "Gestion de Caja",
    "/clientes": "Clientes",
    "/cuentas": "Cuentas Corrientes",
    "/inventario": "Inventario",
    "/historial": "Historial",
    "/servicios": "Servicios",
    "/configuracion": "Configuracion",
}

PAGE_TO_ROUTE = {
    "Ingreso": "/ingreso",
    "Venta": "/venta",
    "Gestion de Caja": "/caja",
    "Clientes": "/clientes",
    "Cuentas Corrientes": "/cuentas",
    "Inventario": "/inventario",
    "Historial": "/historial",
    "Servicios": "/servicios",
    "Configuracion": "/configuracion",
}


def authenticated_layout(page_content: rx.Component) -> rx.Component:
    """Layout wrapper para páginas autenticadas."""
    return rx.cond(
        State.is_authenticated,
        rx.el.main(
            rx.el.div(
                class_name=(
                    "fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r "
                    "from-amber-400 via-rose-500 to-indigo-500 z-[60]"
                ),
            ),
            _toast_provider(),
            NotificationHolder(),
            rx.el.div(
                sidebar(),
                rx.el.div(
                    rx.el.div(
                        cashbox_banner(),
                        rx.cond(
                            State.navigation_items.length() == 0,
                            rx.el.div(
                                rx.el.h1(
                                    "Acceso restringido",
                                    class_name="text-2xl font-bold text-red-600",
                                ),
                                rx.el.p(
                                    "Tu usuario no tiene modulos habilitados. Solicita permisos al administrador.",
                                    class_name="text-gray-600 mt-2 text-center",
                                ),
                                class_name="flex flex-col items-center justify-center h-full p-6",
                            ),
                            page_content,
                        ),
                        class_name="w-full max-w-7xl mx-auto flex flex-col gap-4 p-4 sm:p-6",
                    ),
                    class_name="flex-1 h-screen overflow-y-auto",
                ),
                class_name="flex min-h-screen w-full bg-gray-100",
            ),
            class_name="font-['Inter']",
        ),
        rx.fragment(NotificationHolder(), login_page()),
    )


def index() -> rx.Component:
    """Página principal - redirige a Ingreso."""
    return authenticated_layout(ingreso_page())


def page_ingreso() -> rx.Component:
    return authenticated_layout(ingreso_page())


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

def page_cambiar_contrasena() -> rx.Component:
    return cambiar_contrasena_page()


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
        rx.el.style(
            """
            [data-sonner-toaster][data-x-position='right'][data-y-position='bottom'] {
                display: none !important;
            }
            """
        ),
        rx.script(
            """
            (function() {
                document.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape') {
                        var modalOverlays = document.querySelectorAll('.modal-overlay');
                        if (modalOverlays.length > 0) {
                            modalOverlays[modalOverlays.length - 1].click();
                            return;
                        }

                        var radixOverlay = document.querySelector('[data-radix-dialog-overlay]');
                        if (radixOverlay) {
                            radixOverlay.click();
                            return;
                        }

                        var sidebarOverlay = document.querySelector('.sidebar-overlay');
                        if (sidebarOverlay) {
                            sidebarOverlay.click();
                        }
                    }
                });
            })();
            """
        ),
    ],
)

# Eventos de carga comunes para todas las páginas
_common_on_load = [
    State.ensure_roles_and_permissions,
    State.ensure_password_change,
    State.ensure_default_data,
    State.ensure_payment_methods,
    State.load_categories,
    State.load_field_prices,
    State.load_config_data,
    State.check_overdue_alerts,
]

# Página principal (redirige a ingreso)
app.add_page(index, route="/", on_load=[State.sync_page_from_route] + _common_on_load)

# Cambio de contrasena (solo cuando aplica)
app.add_page(
    page_cambiar_contrasena,
    route="/cambiar-clave",
    title="Cambiar Contrasena - TUWAYKIAPP",
    on_load=[State.ensure_password_change],
)

# Páginas individuales con rutas separadas
app.add_page(
    page_ingreso,
    route="/ingreso",
    title="Ingreso - TUWAYKIAPP",
    on_load=[State.ensure_view_ingresos, State.sync_page_from_route] + _common_on_load,
)
app.add_page(
    page_venta,
    route="/venta",
    title="Venta - TUWAYKIAPP",
    on_load=[State.ensure_view_ventas, State.sync_page_from_route] + _common_on_load,
)
app.add_page(
    page_caja,
    route="/caja",
    title="Gestión de Caja - TUWAYKIAPP",
    on_load=[State.ensure_view_cashbox, State.sync_page_from_route] + _common_on_load,
)
app.add_page(page_clientes, route="/clientes", title="Clientes | Sistema de Ventas", on_load=[State.ensure_view_clientes, State.sync_page_from_route] + _common_on_load)
app.add_page(page_cuentas, route="/cuentas", title="Cuentas Corrientes | Sistema de Ventas", on_load=[State.ensure_view_cuentas, State.sync_page_from_route] + _common_on_load)
app.add_page(
    page_dashboard,
    route="/dashboard",
    title="Dashboard - TUWAYKIAPP",
    on_load=[State.sync_page_from_route] + _common_on_load,
)
app.add_page(
    page_inventario,
    route="/inventario",
    title="Inventario - TUWAYKIAPP",
    on_load=[State.ensure_view_inventario, State.sync_page_from_route] + _common_on_load,
)
app.add_page(
    page_historial,
    route="/historial",
    title="Historial - TUWAYKIAPP",
    on_load=[State.ensure_view_historial, State.sync_page_from_route] + _common_on_load,
)
app.add_page(
    page_reportes,
    route="/reportes",
    title="Reportes - TUWAYKIAPP",
    on_load=[State.ensure_export_data, State.sync_page_from_route] + _common_on_load,
)
app.add_page(
    page_servicios,
    route="/servicios",
    title="Servicios - TUWAYKIAPP",
    on_load=[State.ensure_view_servicios, State.sync_page_from_route, State.load_reservations] + _common_on_load,
)
app.add_page(
    page_configuracion,
    route="/configuracion",
    title="Configuración - TUWAYKIAPP",
    on_load=[State.ensure_admin_access, State.load_users, State.sync_page_from_route]
    + _common_on_load,
)
