import reflex as rx
from app.state import State
from app.components.sidebar import sidebar
from app.pages.ingreso import ingreso_page
from app.pages.venta import venta_page
from app.pages.inventario import inventario_page
from app.pages.caja import cashbox_page
from app.pages.historial import historial_page
from app.pages.configuracion import configuracion_page
from app.pages.login import login_page
from app.pages.servicios import servicios_page


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


def index() -> rx.Component:
    return rx.cond(
        State.is_authenticated,
        rx.el.main(
            _toast_provider(),
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
                            rx.match(
                                State.active_page,
                                ("Ingreso", ingreso_page()),
                            ("Venta", venta_page()),
                            ("Gestion de Caja", cashbox_page()),
                            ("Inventario", inventario_page()),
                            ("Historial", historial_page()),
                            ("Servicios", servicios_page()),
                            ("Configuracion", configuracion_page()),
                                rx.el.div("Pagina no encontrada"),
                            ),
                        ),
                        class_name="w-full max-w-7xl mx-auto flex flex-col gap-4 p-4 sm:p-6",
                    ),
                    class_name="flex-1 h-screen overflow-y-auto",
                ),
                class_name="flex min-h-screen w-full bg-gray-100",
            ),
            class_name="font-['Inter']",
        ),
        login_page(),
    )


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
    ],
)
app.add_page(index)
