import reflex as rx
from app.state import State
from app.components.sidebar import sidebar
from app.pages.ingreso import ingreso_page
from app.pages.venta import venta_page
from app.pages.inventario import inventario_page
from app.pages.historial import historial_page


def index() -> rx.Component:
    return rx.el.main(
        rx.el.div(
            sidebar(),
            rx.el.div(
                rx.match(
                    State.current_page,
                    ("Ingreso", ingreso_page()),
                    ("Venta", venta_page()),
                    ("Inventario", inventario_page()),
                    ("Historial", historial_page()),
                    rx.el.div("Página no encontrada"),
                ),
                class_name="flex-1 h-screen overflow-y-auto",
            ),
            class_name="flex min-h-screen w-full bg-gray-100",
        ),
        class_name="font-['Inter']",
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
    ],
)
app.add_page(index)