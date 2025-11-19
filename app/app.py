import reflex as rx
from app.state import State
from app.states.auth_state import AuthState
from app.components.sidebar import sidebar
from app.pages.ingreso import ingreso_page
from app.pages.venta import venta_page
from app.pages.inventario import inventario_page
from app.pages.caja import cashbox_page
from app.pages.historial import historial_page
from app.pages.configuracion import configuracion_page
from app.pages.login import login_page


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
        AuthState.is_authenticated,
        rx.el.main(
            _toast_provider(),
            rx.el.div(
                sidebar(),
                rx.el.div(
                    rx.match(
                        State.current_page,
                        ("Ingreso", ingreso_page()),
                        ("Venta", venta_page()),
                        ("Gestion de Caja", cashbox_page()),
                        ("Inventario", inventario_page()),
                        ("Historial", historial_page()),
                        ("Configuracion", configuracion_page()),
                        rx.el.div("Página no encontrada"),
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
