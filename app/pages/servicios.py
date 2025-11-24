import reflex as rx
from app.state import State


def servicio_card(title: str, description: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(title, class_name="text-lg font-semibold text-gray-800"),
            rx.el.p(description, class_name="text-sm text-gray-600"),
            class_name="flex flex-col gap-2",
        ),
        class_name="w-full bg-white border border-gray-200 rounded-lg p-4 sm:p-5 shadow-sm",
    )


def servicios_page() -> rx.Component:
    return rx.el.div(
        rx.el.h1("Servicios", class_name="text-2xl font-bold text-gray-800"),
        rx.el.p(
            "Gestiona los servicios que ofreces a tus clientes.",
            class_name="text-sm text-gray-600",
        ),
        rx.match(
            State.service_active_tab,
            ("campo", servicio_card("Alquiler de Campo", "Reserva y control de alquiler de campo.")),
            ("piscina", servicio_card("Alquiler de Piscina", "Registro y seguimiento de alquiler de piscina.")),
            servicio_card("Alquiler de Campo", "Reserva y control de alquiler de campo."),
        ),
        class_name="p-4 sm:p-6 w-full max-w-7xl mx-auto flex flex-col gap-4",
    )
