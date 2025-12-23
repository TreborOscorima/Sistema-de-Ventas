import reflex as rx
from app.state import State
from app.components.ui import (
    date_range_filter,
    select_filter,
    section_header,
    card_container,
    BUTTON_STYLES,
    pagination_controls,
)


def soccer_ball_icon(class_name: str = "h-5 w-5") -> rx.Component:
    """SVG simple de balón de fútbol para evitar iconos desconocidos."""
    return rx.el.svg(
        rx.el.circle(cx="12", cy="12", r="9", fill="none", stroke="currentColor", stroke_width="2"),
        rx.el.polygon(
            points="12 7 15 9 14 13 10 13 9 9",
            fill="none",
            stroke="currentColor",
            stroke_width="2",
        ),
        rx.el.line(x1="12", y1="7", x2="10", y2="4", stroke="currentColor", stroke_width="2"),
        rx.el.line(x1="12", y1="7", x2="14", y2="4", stroke="currentColor", stroke_width="2"),
        rx.el.line(x1="10", y1="13", x2="8", y2="16", stroke="currentColor", stroke_width="2"),
        rx.el.line(x1="14", y1="13", x2="16", y2="16", stroke="currentColor", stroke_width="2"),
        rx.el.line(x1="9", y1="9", x2="6", y2="9", stroke="currentColor", stroke_width="2"),
        rx.el.line(x1="15", y1="9", x2="18", y2="9", stroke="currentColor", stroke_width="2"),
        rx.el.line(x1="12", y1="7", x2="12", y2="11", stroke="currentColor", stroke_width="2"),
        viewBox="0 0 24 24",
        class_name=class_name,
        stroke="currentColor",
        fill="none",
        stroke_linecap="round",
        stroke_linejoin="round",
    )


def sport_selector() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p("Alquiler de campo", class_name="text-lg font-semibold text-gray-800"),
            rx.el.p(
                "Elige el deporte para gestionar reservas, pagos y cancelaciones.",
                class_name="text-sm text-gray-600",
            ),
            class_name="flex flex-col gap-1",
        ),
        rx.el.div(
            rx.el.button(
                rx.el.div(
                    class_name="absolute inset-0 bg-black/45 pointer-events-none",
                ),
                rx.el.div(
                    soccer_ball_icon(class_name="h-5 w-5 text-white"),
                    rx.el.span("Campos de Futbol", class_name="font-semibold text-white"),
                    rx.el.span(
                        "Reservas, pagos y comprobantes para futbol.",
                        class_name="text-sm text-white/80",
                    ),
                    class_name="relative z-10 flex flex-col items-start gap-1",
                ),
                on_click=lambda: State.set_field_rental_sport("futbol"),
                style={
                    "backgroundImage": "url('/campo-futbol.png')",
                    "backgroundSize": "cover",
                    "backgroundPosition": "center",
                },
                class_name=rx.cond(
                    State.field_rental_sport == "futbol",
                    "relative overflow-hidden flex flex-col items-start gap-1 rounded-lg px-4 py-3 text-white shadow ring-2 ring-emerald-400 min-h-[140px] sm:min-h-[160px]",
                    "relative overflow-hidden flex flex-col items-start gap-1 rounded-lg px-4 py-3 text-white border border-white/20 hover:opacity-95 min-h-[140px] sm:min-h-[160px]",
                ),
            ),
            rx.el.button(
                rx.el.div(
                    class_name="absolute inset-0 bg-black/45 pointer-events-none",
                ),
                rx.el.div(
                    rx.icon("volleyball", class_name="h-5 w-5 text-white"),
                    rx.el.span("Campos de Voley", class_name="font-semibold text-white"),
                    rx.el.span(
                        "Control rapido de reservas para voley.",
                        class_name="text-sm text-white/80",
                    ),
                    class_name="relative z-10 flex flex-col items-start gap-1",
                ),
                on_click=lambda: State.set_field_rental_sport("voley"),
                style={
                    "backgroundImage": "url('/campo-voley.png')",
                    "backgroundSize": "cover",
                    "backgroundPosition": "center",
                },
                class_name=rx.cond(
                    State.field_rental_sport == "voley",
                    "relative overflow-hidden flex flex-col items-start gap-1 rounded-lg px-4 py-3 text-white shadow ring-2 ring-indigo-400 min-h-[140px] sm:min-h-[160px]",
                    "relative overflow-hidden flex flex-col items-start gap-1 rounded-lg px-4 py-3 text-white border border-white/20 hover:opacity-95 min-h-[140px] sm:min-h-[160px]",
                ),
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 gap-3",
        ),
        class_name="bg-white border border-gray-200 rounded-lg p-4 sm:p-5 shadow-sm flex flex-col gap-3",
    )


def time_slot_button(slot: rx.Var[dict]) -> rx.Component:
    return rx.el.button(
        rx.el.div(
            rx.el.span(
                slot["start"],
                " - ",
                slot["end"],
                class_name="text-sm font-semibold",
            ),
            rx.el.span(
                rx.cond(
                    slot["reserved"],
                    "Reservado",
                    rx.cond(
                        slot["selected"],
                        "Seleccionado",
                        "Seleccionar",
                    ),
                ),
                class_name="text-xs opacity-70",
            ),
            class_name="flex flex-col items-start",
        ),
        on_click=lambda _, start=slot["start"], end=slot["end"]: State.toggle_schedule_slot(start, end),
        class_name=rx.cond(
            slot["reserved"],
            "w-full text-left rounded-lg border border-red-200 bg-red-50 text-red-700 px-3 py-2 cursor-not-allowed",
            rx.cond(
                slot["selected"],
                "w-full text-left rounded-lg bg-indigo-600 text-white px-3 py-2 shadow",
                "w-full text-left rounded-lg border px-3 py-2 hover:bg-gray-50",
            ),
        ),
        disabled=slot["reserved"],
    )


def time_slots_grid() -> rx.Component:
    return rx.el.div(
        rx.foreach(State.schedule_slots, lambda slot: time_slot_button(slot)),
        class_name="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2",
    )


def schedule_controls() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.button(
                rx.icon("calendar-check", class_name="h-4 w-4"),
                "Día",
                on_click=lambda: State.set_schedule_view("dia"),
                class_name=rx.cond(
                    State.schedule_view_mode == "dia",
                    "flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-600 text-white shadow",
                    "flex items-center gap-2 px-4 py-2 rounded-full border hover:bg-gray-50",
                ),
            ),
            rx.el.button(
                rx.icon("calendar-range", class_name="h-4 w-4"),
                "Semana",
                on_click=lambda: State.set_schedule_view("semana"),
                class_name=rx.cond(
                    State.schedule_view_mode == "semana",
                    "flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-600 text-white shadow",
                    "flex items-center gap-2 px-4 py-2 rounded-full border hover:bg-gray-50",
                ),
            ),
            rx.el.button(
                rx.icon("calendar", class_name="h-4 w-4"),
                "Mes",
                on_click=lambda: State.set_schedule_view("mes"),
                class_name=rx.cond(
                    State.schedule_view_mode == "mes",
                    "flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-600 text-white shadow",
                    "flex items-center gap-2 px-4 py-2 rounded-full border hover:bg-gray-50",
                ),
            ),
            class_name="grid grid-cols-3 gap-2 w-full sm:w-auto",
        ),
        rx.match(
            State.schedule_view_mode,
            (
                "dia",
                rx.el.div(
                    rx.el.label("Fecha (día)", class_name="text-sm font-medium text-gray-700"),
                    rx.el.input(
                        type="date",
                        value=State.schedule_selected_date,
                        on_change=State.set_schedule_date,
                        class_name="p-2 border rounded-md",
                    ),
                    class_name="flex flex-col gap-1",
                ),
            ),
            (
                "semana",
                rx.el.div(
                    rx.el.label("Semana", class_name="text-sm font-medium text-gray-700"),
                    rx.el.input(
                        type="week",
                        value=State.schedule_selected_week,
                        on_change=State.set_schedule_week,
                        class_name="p-2 border rounded-md",
                    ),
                    rx.el.div(
                        rx.foreach(
                            State.schedule_week_days,
                            lambda item, idx: rx.el.button(
                                item["label"],
                                on_click=lambda _, offset=idx: State.select_week_day(offset),
                                class_name=rx.cond(
                                    State.schedule_selected_date == item["date"],
                                    "px-3 py-2 rounded-md bg-emerald-600 text-white",
                                    "px-3 py-2 rounded-md border hover:bg-gray-50",
                                ),
                            ),
                        ),
                        class_name="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 mt-2",
                    ),
                    class_name="flex flex-col gap-2",
                ),
            ),
            (
                "mes",
                rx.el.div(
                    rx.el.label("Mes", class_name="text-sm font-medium text-gray-700"),
                    rx.el.input(
                        type="month",
                        value=State.schedule_selected_month,
                        on_change=State.set_schedule_month,
                        class_name="p-2 border rounded-md",
                    ),
                    rx.el.div(
                        rx.foreach(
                            State.schedule_month_days,
                            lambda item: rx.el.button(
                                item["label"],
                                on_click=lambda _, date=item["date"]: State.select_month_day(date),
                                class_name=rx.cond(
                                    State.schedule_selected_date == item["date"],
                                    "px-3 py-2 rounded-md bg-emerald-600 text-white",
                                    "px-3 py-2 rounded-md border hover:bg-gray-50",
                                ),
                            ),
                        ),
                        class_name="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-7 gap-2 mt-2",
                    ),
                    class_name="flex flex-col gap-2",
                ),
            ),
            rx.fragment(),
        ),
        class_name="flex flex-col gap-3",
    )


def schedule_planner() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h3("Planificador horario", class_name="text-lg font-semibold text-gray-800"),
            rx.el.p(
                "Selecciona fecha y franja horaria entre 00:00 y 23:59 para registrar la reserva.",
                class_name="text-sm text-gray-600",
            ),
            class_name="flex flex-col gap-1",
        ),
        schedule_controls(),
        rx.el.div(
            rx.el.h4("Horas del dia", class_name="text-sm font-semibold text-gray-700"),
            time_slots_grid(),
            class_name="flex flex-col gap-2",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span("Seleccion actual", class_name="text-xs uppercase text-gray-500"),
                rx.el.span(
                    State.schedule_selected_date,
                    " ",
                    State.schedule_selection_label,
                    class_name="text-sm font-semibold text-gray-900",
                ),
                rx.el.span(
                    rx.cond(
                        State.schedule_selection_valid,
                        "Listo para registrar la reserva en bloque.",
                        rx.cond(
                            State.schedule_selected_slots_count == 0,
                            "Selecciona uno o varios horarios disponibles.",
                            "Elige horarios consecutivos para reservar en un solo bloque.",
                        ),
                    ),
                    class_name="text-xs text-gray-600",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("rotate-ccw", class_name="h-4 w-4"),
                    "Limpiar seleccion",
                    on_click=State.clear_schedule_selection,
                    disabled=rx.cond(State.schedule_selected_slots_count == 0, True, False),
                    class_name=rx.cond(
                        State.schedule_selected_slots_count == 0,
                        "flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-gray-200 text-gray-500 cursor-not-allowed min-h-[38px]",
                        "flex items-center justify-center gap-2 px-3 py-2 rounded-md border text-gray-700 hover:bg-gray-50 min-h-[38px]",
                    ),
                ),
                rx.el.button(
                    rx.icon("calendar-plus", class_name="h-4 w-4"),
                    "Reservar seleccion",
                    on_click=State.open_selected_slots_modal,
                    disabled=rx.cond(State.schedule_selection_valid, False, True),
                    class_name=rx.cond(
                        State.schedule_selection_valid,
                        "flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 min-h-[38px]",
                        "flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-gray-200 text-gray-500 cursor-not-allowed min-h-[38px]",
                    ),
                ),
                class_name="flex flex-col sm:flex-row gap-2 sm:items-center",
            ),
            class_name="rounded-md border border-dashed border-gray-200 p-3 bg-gray-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3",
        ),
        class_name="bg-white border border-gray-200 rounded-lg p-4 sm:p-5 shadow-sm flex flex-col gap-4",
    )


def reservation_modal() -> rx.Component:
    return rx.cond(
        State.reservation_modal_open,
        rx.el.div(
            rx.el.div(
                on_click=State.close_reservation_modal,
                class_name="fixed inset-0 bg-black/40 modal-overlay",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.h3(
                        rx.cond(
                            State.reservation_modal_mode == "view",
                            "Detalle de reserva",
                            "Nueva reserva",
                        ),
                        class_name="text-lg font-semibold text-gray-800",
                    ),
                    rx.el.p(
                        rx.cond(
                            State.reservation_modal_mode == "view",
                            "Consulta el estado y acciones de la reserva seleccionada.",
                            "Completa los datos para crear la reserva en el horario elegido.",
                        ),
                        class_name="text-sm text-gray-600",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.span("Horario", class_name="text-xs uppercase text-gray-500"),
                    rx.el.span(
                        State.reservation_form["date"],
                        " ",
                        State.reservation_form["start_time"],
                        " - ",
                        State.reservation_form["end_time"],
                        class_name="text-sm font-semibold text-gray-900",
                    ),
                    rx.el.span(
                        rx.cond(
                            State.field_rental_sport == "futbol",
                            "Campos de Futbol",
                            "Campos de Voley",
                        ),
                        class_name="text-xs text-gray-600",
                    ),
                    class_name="rounded-md border border-dashed border-gray-200 p-3 bg-gray-50 flex flex-col gap-1",
                ),
                rx.cond(
                    State.reservation_modal_mode == "view",
                    rx.cond(
                        State.modal_reservation == None,
                        rx.el.p("Reserva no encontrada.", class_name="text-sm text-gray-600"),
                        rx.el.div(
                            rx.el.div(
                                rx.el.div(
                                    rx.el.span("Cliente", class_name="text-xs uppercase text-gray-500"),
                                    rx.el.span(
                                        State.modal_reservation["client_name"],
                                        class_name="text-sm font-semibold text-gray-900",
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.span("Telefono", class_name="text-xs uppercase text-gray-500"),
                                    rx.el.span(
                                        State.modal_reservation["phone"],
                                        class_name="text-sm font-semibold text-gray-900",
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.span("Campo", class_name="text-xs uppercase text-gray-500"),
                                    rx.el.span(
                                        State.modal_reservation["field_name"],
                                        class_name="text-sm font-semibold text-gray-900",
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.span("Estado", class_name="text-xs uppercase text-gray-500"),
                                    reservation_status_badge(State.modal_reservation),
                                    class_name="flex flex-col gap-1",
                                ),
                                class_name="grid grid-cols-1 sm:grid-cols-2 gap-3",
                            ),
                            rx.el.div(
                                rx.el.div(
                                    rx.el.span("Total", class_name="text-xs uppercase text-gray-500"),
                                    rx.el.span(
                                        State.currency_symbol,
                                        State.modal_reservation["total_amount"].to_string(),
                                        class_name="text-sm font-semibold text-gray-900",
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.span("Pagado", class_name="text-xs uppercase text-gray-500"),
                                    rx.el.span(
                                        State.currency_symbol,
                                        State.modal_reservation["paid_amount"].to_string(),
                                        class_name="text-sm font-semibold text-gray-900",
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.span("Saldo", class_name="text-xs uppercase text-gray-500"),
                                    rx.el.span(
                                        State.currency_symbol,
                                        State.selected_reservation_balance.to_string(),
                                        class_name="text-sm font-semibold text-gray-900",
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                class_name="grid grid-cols-1 sm:grid-cols-3 gap-3",
                            ),
                            rx.el.div(
                                rx.fragment(),
                                class_name="grid grid-cols-1 sm:grid-cols-3 gap-2",
                            ),
                            class_name="flex flex-col gap-4",
                        ),
        ),
        rx.el.div(
            rx.el.div(
                rx.el.label("Cliente", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                                placeholder="Nombre completo",
                                value=State.reservation_form["client_name"],
                                on_change=lambda value: State.update_reservation_form("client_name", value),
                                class_name="w-full p-2 border rounded-md",
                            ),
                            class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Telefono", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    placeholder="999 999 999",
                    value=State.reservation_form["phone"],
                    on_change=lambda value: State.update_reservation_form("phone", value),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Deporte", class_name="text-sm font-medium text-gray-700"),
                rx.el.select(
                    rx.el.option("Selecciona un deporte", value=""),
                    rx.foreach(
                        State.field_prices_for_current_sport,
                        lambda price: rx.el.option(
                            price["sport"] + " - " + price["name"],
                            value=price["id"],
                        ),
                    ),
                    value=State.reservation_form["selected_price_id"],
                    on_change=State.select_reservation_field_price,
                    class_name="w-full p-2 border rounded-md bg-white",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Campo", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    placeholder="Cancha / Campo",
                    value=State.reservation_form["field_name"],
                                on_change=lambda value: State.update_reservation_form("field_name", value),
                                class_name="w-full p-2 border rounded-md",
                            ),
                            class_name="flex flex-col gap-1",
                        ),
            rx.el.div(
                rx.el.label("Adelanto", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    type="number",
                    step="0.01",
                    value=State.reservation_form["advance_amount"],
                    on_change=lambda value: State.update_reservation_form("advance_amount", value),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
                        rx.el.div(
                            rx.el.label("Monto total", class_name="text-sm font-medium text-gray-700"),
                            rx.el.input(
                                type="number",
                                step="0.01",
                                value=State.reservation_form["total_amount"],
                                on_change=lambda value: State.update_reservation_form("total_amount", value),
                                class_name="w-full p-2 border rounded-md",
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                        rx.el.div(
                            rx.el.label("Estado", class_name="text-sm font-medium text-gray-700"),
                            rx.el.select(
                                rx.el.option("Pendiente", value="pendiente"),
                                rx.el.option("Pagado", value="pagado"),
                                value=State.reservation_form["status"],
                                on_change=lambda value: State.update_reservation_form("status", value),
                                class_name="w-full p-2 border rounded-md bg-white",
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                        class_name="grid grid-cols-1 sm:grid-cols-2 gap-3",
                    ),
                ),
                rx.el.div(
                    rx.cond(
                        State.reservation_modal_mode == "view",
                        rx.el.button(
                            rx.icon("printer", class_name="h-4 w-4"),
                            "Imprimir Comprobante",
                            on_click=lambda: State.print_reservation_receipt(State.reservation_modal_reservation_id),
                            class_name="flex items-center justify-center gap-2 px-4 py-2 rounded-md border text-gray-700 hover:bg-gray-50 min-h-[42px]",
                        ),
                        rx.fragment(),
                    ),
                    rx.el.button(
                        "Cerrar",
                        on_click=State.close_reservation_modal,
                        class_name="px-4 py-2 rounded-md border text-gray-700 hover:bg-gray-50 min-h-[42px]",
                    ),
                    rx.cond(
                        State.reservation_modal_mode == "new",
                        rx.el.button(
                            rx.icon("check", class_name="h-4 w-4"),
                            "Guardar reserva",
                            on_click=State.create_field_reservation,
                            disabled=rx.cond(
                                (State.reservation_form["client_name"] == "")
                                | (State.reservation_form["date"] == "")
                                | (State.reservation_form["start_time"] == "")
                                | (State.reservation_form["end_time"] == "")
                                | (State.reservation_form["total_amount"] == "0")
                                | (State.reservation_form["total_amount"] == "")
                                | (State.schedule_selected_date == ""),
                                True,
                                False,
                            ),
                            class_name=rx.cond(
                                (State.reservation_form["client_name"] == "")
                                | (State.reservation_form["date"] == "")
                                | (State.reservation_form["start_time"] == "")
                                | (State.reservation_form["end_time"] == "")
                                | (State.reservation_form["total_amount"] == "0")
                                | (State.reservation_form["total_amount"] == "")
                                | (State.schedule_selected_date == ""),
                                "flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-gray-200 text-gray-500 cursor-not-allowed min-h-[42px]",
                                "flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 min-h-[42px]",
                            ),
                        ),
                        rx.fragment(),
                    ),
                    class_name="flex justify-end gap-3 pt-4",
                ),
                class_name="relative z-10 w-full max-w-3xl rounded-xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto",
            ),
            class_name="fixed inset-0 z-50 flex items-center justify-center px-4",
        ),
        rx.fragment(),
    )


def reservation_form_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h3("Registro de reservas", class_name="text-lg font-semibold text-gray-800"),
            rx.el.p(
                "Captura los datos del cliente, horario y adelantos opcionales.",
                class_name="text-sm text-gray-600",
            ),
            class_name="flex flex-col gap-1",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.label("Nombre completo", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    placeholder="Ej: Juan Perez",
                    value=State.reservation_form["client_name"],
                    on_change=lambda value: State.update_reservation_form("client_name", value),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("DNI (opcional)", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    placeholder="Documento",
                    value=State.reservation_form["dni"],
                    on_change=lambda value: State.update_reservation_form("dni", value),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Telefono (opcional)", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    placeholder="999 999 999",
                    value=State.reservation_form["phone"],
                    on_change=lambda value: State.update_reservation_form("phone", value),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Campo", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    placeholder="Campo A / Cancha 1",
                    value=State.reservation_form["field_name"],
                    on_change=lambda value: State.update_reservation_form("field_name", value),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Fecha", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    type="date",
                    value=State.reservation_form["date"],
                    on_change=lambda value: State.update_reservation_form("date", value),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Hora inicio", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    type="time",
                    value=State.reservation_form["start_time"],
                    on_change=lambda value: State.update_reservation_form("start_time", value),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Hora fin", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    type="time",
                    value=State.reservation_form["end_time"],
                    on_change=lambda value: State.update_reservation_form("end_time", value),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Adelanto", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    type="number",
                    step="0.01",
                    value=State.reservation_form["advance_amount"],
                    on_change=lambda value: State.update_reservation_form("advance_amount", value),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Monto total", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    type="number",
                    step="0.01",
                    value=State.reservation_form["total_amount"],
                    on_change=lambda value: State.update_reservation_form("total_amount", value),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Estado", class_name="text-sm font-medium text-gray-700"),
                rx.el.select(
                    rx.el.option("Pendiente", value="pendiente"),
                    rx.el.option("Pagado", value="pagado"),
                    value=State.reservation_form["status"],
                    on_change=lambda value: State.update_reservation_form("status", value),
                    class_name="w-full p-2 border rounded-md bg-white",
                ),
                class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4",
        ),
        rx.el.div(
            rx.el.button(
                rx.icon("check", class_name="h-4 w-4"),
                "Guardar reserva",
                on_click=State.create_field_reservation,
                class_name="flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 min-h-[44px]",
            ),
            class_name="flex justify-end",
        ),
        class_name="bg-white border border-gray-200 rounded-lg p-4 sm:p-5 shadow-sm flex flex-col gap-4",
    )


def reservation_delete_modal() -> rx.Component:
    return rx.radix.primitives.dialog.root(
        rx.radix.primitives.dialog.portal(
            rx.radix.primitives.dialog.overlay(
                class_name="fixed inset-0 bg-black/40 z-40 modal-overlay"
            ),
            rx.radix.primitives.dialog.content(
                rx.el.div(
                    rx.el.h3("Eliminar reserva", class_name="text-lg font-semibold text-gray-800"),
                    rx.el.p(
                        "Esta accion marcara la reserva como Eliminada y liberara el horario. Ingresa un sustento obligatorio.",
                        class_name="text-sm text-gray-600",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.cond(
                    State.reservation_selected_for_delete == None,
                    rx.el.p("Reserva no encontrada.", class_name="text-sm text-gray-600"),
                    rx.el.div(
                        rx.el.div(
                            rx.el.span("Cliente", class_name="text-xs uppercase text-gray-500"),
                            rx.el.span(
                                State.reservation_selected_for_delete["client_name"],
                                class_name="text-sm font-semibold text-gray-900",
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                        rx.el.div(
                            rx.el.span("Horario", class_name="text-xs uppercase text-gray-500"),
                            rx.el.span(
                                State.reservation_selected_for_delete["start_datetime"],
                                " - ",
                                State.reservation_selected_for_delete["end_datetime"],
                                class_name="text-sm font-semibold text-gray-900",
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                        class_name="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-gray-50 border border-gray-100 rounded-md p-3",
                    ),
                ),
                rx.el.div(
                    rx.el.label("Sustento de eliminacion", class_name="text-sm font-medium text-gray-700"),
                    rx.el.textarea(
                        placeholder="Ej: Registro duplicado o datos incorrectos",
                        value=State.reservation_delete_reason,
                        on_change=State.set_reservation_delete_reason,
                        auto_focus=True,
                        class_name="w-full p-2 border rounded-md min-h-[100px]",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=lambda _: State.close_reservation_delete_modal(),
                        class_name="px-4 py-2 rounded-md border text-gray-700 hover:bg-gray-50 min-h-[40px]",
                    ),
                    rx.el.button(
                        rx.icon("trash-2", class_name="h-4 w-4"),
                        "Eliminar",
                        on_click=lambda _: State.confirm_reservation_delete(),
                        disabled=State.reservation_delete_button_disabled,
                        class_name=rx.cond(
                            State.reservation_delete_button_disabled,
                            "flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-gray-200 text-gray-500 cursor-not-allowed min-h-[40px]",
                            "flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-red-600 text-white hover:bg-red-700 min-h-[40px]",
                        ),
                    ),
                    class_name="flex justify-end gap-3",
                ),
                class_name=(
                    "bg-white rounded-lg shadow-lg p-5 w-full max-w-xl space-y-4 "
                    "data-[state=open]:animate-in data-[state=closed]:animate-out "
                    "data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0 "
                    "data-[state=open]:zoom-in-95 data-[state=closed]:zoom-out-95 "
                    "data-[state=open]:slide-in-from-top-4 data-[state=closed]:slide-out-to-top-4 "
                    "fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-xl -translate-x-1/2 -translate-y-1/2 shadow-xl focus:outline-none"
                ),
            ),
        ),
        open=State.reservation_delete_modal_open,
        on_open_change=State.set_reservation_delete_modal_open,
    )


def reservation_status_badge(reservation: rx.Var[dict]) -> rx.Component:
    return rx.cond(
        reservation["status"] == "pagado",
        rx.el.span(
            "Pagado",
            class_name="px-2 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-700",
        ),
        rx.cond(
            reservation["status"] == "cancelado",
            rx.el.span(
                "Cancelado",
                class_name="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-700",
            ),
            rx.cond(
                reservation["status"] == "eliminado",
                rx.el.span(
                    "Eliminado",
                    class_name="px-2 py-1 text-xs font-semibold rounded-full bg-gray-200 text-gray-700",
                ),
                rx.el.span(
                    "Pendiente",
                    class_name="px-2 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-700",
                ),
            ),
        ),
    )


def reservation_row(reservation: rx.Var[dict]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(reservation["client_name"], class_name="py-3 px-4"),
        rx.el.td(reservation["field_name"], class_name="py-3 px-4"),
        rx.el.td(
            rx.el.div(
                rx.el.span(reservation["start_datetime"], class_name="text-sm font-medium"),
                rx.el.span(reservation["end_datetime"], class_name="text-xs text-gray-500"),
                class_name="flex flex-col",
            ),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.span(State.currency_symbol, reservation["total_amount"].to_string(), class_name="font-semibold"),
                rx.el.span(
                    "Pagado ",
                    State.currency_symbol,
                    reservation["paid_amount"].to_string(),
                    class_name="text-xs text-gray-600",
                ),
                class_name="flex flex-col gap-1",
            ),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.el.div(
                reservation_status_badge(reservation),
                rx.cond(
                    reservation["status"] == "eliminado",
                    rx.el.span(
                        "Sustento: ",
                        reservation.get("delete_reason", ""),
                        class_name="text-xs text-gray-500",
                    ),
                    rx.fragment(),
                ),
                class_name="flex flex-col gap-1",
            ),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda _, rid=reservation["id"]: State.start_reservation_delete(rid),
                    disabled=reservation["status"] != "pendiente",
                    aria_label="Eliminar reserva",
                    class_name=rx.cond(
                        reservation["status"] != "pendiente",
                        "p-2 rounded-full bg-gray-200 text-gray-500 cursor-not-allowed",
                        "p-2 rounded-full border text-red-600 hover:bg-red-50",
                    ),
                ),
                rx.el.button(
                    rx.icon("eye", class_name="h-4 w-4"),
                    rx.el.span("Ver", class_name="text-sm font-semibold"),
                    on_click=lambda _, rid=reservation["id"]: State.view_reservation_details(rid),
                    class_name="flex items-center gap-2 px-3 py-2 rounded-md border text-blue-600 hover:bg-blue-50",
                ),
                rx.el.button(
                    rx.icon("printer", class_name="h-4 w-4"),
                    rx.el.span("Imprimir", class_name="text-sm font-semibold"),
                    on_click=lambda _, rid=reservation["id"]: State.print_reservation_receipt(rid),
                    class_name="flex items-center gap-2 px-3 py-2 rounded-md border text-gray-600 hover:bg-gray-50",
                ),
                rx.el.button(
                    rx.icon("credit-card", class_name="h-4 w-4"),
                    rx.el.span("Pagar", class_name="text-sm font-semibold"),
                    on_click=lambda _, rid=reservation["id"]: State.go_to_sale_for_reservation(rid),
                    disabled=rx.cond(
                        reservation["status"] == "eliminado",
                        True,
                        rx.cond(
                            reservation["status"] == "cancelado",
                            True,
                            rx.cond(reservation["status"] == "pagado", True, False),
                        ),
                    ),
                    class_name=rx.cond(
                        reservation["status"] == "eliminado",
                        "flex items-center gap-2 px-3 py-2 rounded-md bg-gray-200 text-gray-500 cursor-not-allowed",
                        rx.cond(
                            reservation["status"] == "cancelado",
                            "flex items-center gap-2 px-3 py-2 rounded-md bg-gray-200 text-gray-500 cursor-not-allowed",
                            rx.cond(
                                reservation["status"] == "pagado",
                                "flex items-center gap-2 px-3 py-2 rounded-md bg-gray-200 text-gray-500 cursor-not-allowed",
                                "flex items-center gap-2 px-3 py-2 rounded-md bg-emerald-600 text-white hover:bg-emerald-700",
                            ),
                        ),
                    ),
                ),
                class_name="flex flex-col sm:flex-row sm:flex-wrap gap-2",
            ),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.el.span(
                State.currency_symbol,
                (reservation["total_amount"] - reservation["advance_amount"]).to_string(),
                class_name="font-semibold",
            ),
            class_name="py-3 px-4 text-right",
        ),
        class_name="border-b",
    )


def reservations_table() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h3("Reservas registradas", class_name="text-lg font-semibold text-gray-800"),
            rx.el.p(
                "Revisa el estado de cada reserva por deporte.",
                class_name="text-sm text-gray-600",
            ),
            class_name="flex flex-col gap-1",
        ),
        rx.el.div(
            rx.el.input(
                placeholder="Buscar por cliente, campo o horario...",
                value=State.reservation_staged_search,
                on_change=State.set_reservation_staged_search,
                class_name="w-full p-2 border rounded-md",
            ),
            rx.el.select(
                rx.el.option("Todos", value="todos"),
                rx.el.option("Pendiente", value="pendiente"),
                rx.el.option("Pagado", value="pagado"),
                rx.el.option("Cancelado", value="cancelado"),
                rx.el.option("Eliminado", value="eliminado"),
                value=State.reservation_staged_status,
                on_change=State.set_reservation_staged_status,
                class_name="p-2 border rounded-md bg-white",
            ),
            rx.el.input(
                type="date",
                value=State.reservation_staged_start_date,
                on_change=State.set_reservation_staged_start_date,
                class_name="p-2 border rounded-md",
            ),
            rx.el.input(
                type="date",
                value=State.reservation_staged_end_date,
                on_change=State.set_reservation_staged_end_date,
                class_name="p-2 border rounded-md",
            ),
            rx.el.button(
                rx.icon("search", class_name="h-4 w-4"),
                "Buscar",
                on_click=State.apply_reservation_filters,
                class_name="flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 min-h-[42px]",
            ),
            rx.el.button(
                rx.icon("rotate-ccw", class_name="h-4 w-4"),
                "Limpiar",
                on_click=State.reset_reservation_filters,
                class_name="flex items-center justify-center gap-2 px-4 py-2 rounded-md border text-gray-700 hover:bg-gray-50 min-h-[42px]",
            ),
            rx.el.button(
                rx.icon("download", class_name="h-4 w-4"),
                "Exportar Excel",
                on_click=State.export_reservations_excel,
                class_name="flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-emerald-600 text-white hover:bg-emerald-700 min-h-[42px]",
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[2fr,1fr,1fr,1fr,auto,auto,auto] gap-2 items-center",
        ),
        rx.el.table(
            rx.el.thead(
                rx.el.tr(
                    rx.el.th("Cliente", class_name="py-2 px-4 text-left"),
                    rx.el.th("Campo", class_name="py-2 px-4 text-left"),
                    rx.el.th("Horario", class_name="py-2 px-4 text-left"),
                    rx.el.th("Monto", class_name="py-2 px-4 text-left"),
                    rx.el.th("Estado", class_name="py-2 px-4 text-left"),
                    rx.el.th("Acciones", class_name="py-2 px-4 text-left"),
                    rx.el.th("Saldo", class_name="py-2 px-4 text-right"),
                    class_name="bg-gray-100",
                )
            ),
            rx.el.tbody(rx.foreach(State.paginated_reservations, reservation_row)),
            class_name="min-w-full",
        ),
        rx.cond(
            State.service_reservations_for_sport.length() == 0,
            rx.el.p(
                "Aun no hay reservas en este deporte.",
                class_name="text-center text-gray-500 py-4",
            ),
            pagination_controls(
                current_page=State.reservation_current_page,
                total_pages=State.reservation_total_pages,
                on_prev=State.prev_reservation_page,
                on_next=State.next_reservation_page,
            ),
        ),
        class_name="bg-white border border-gray-200 rounded-lg p-4 sm:p-5 shadow-sm overflow-x-auto flex flex-col gap-3",
    )


def payments_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h3("Pagos y adelantos", class_name="text-lg font-semibold text-gray-800"),
            rx.el.p(
                "Registra pagos parciales, saldo pendiente y genera comprobante.",
                class_name="text-sm text-gray-600",
            ),
            class_name="flex flex-col gap-1",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.label("Reserva", class_name="text-sm font-medium text-gray-700"),
                rx.el.select(
                    rx.el.option("Selecciona una reserva", value=""),
                    rx.foreach(
                        State.active_reservation_options,
                        lambda option: rx.el.option(option["label"], value=option["id"]),
                    ),
                    value=State.reservation_payment_id,
                    on_change=State.select_reservation_for_payment,
                    class_name="w-full p-2 border rounded-md bg-white",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Monto a registrar", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    type="number",
                    step="0.01",
                    placeholder="Ej: 80.00",
                    value=State.reservation_payment_amount,
                    on_change=State.set_reservation_payment_amount,
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-1 lg:grid-cols-2 gap-4",
        ),
        rx.el.div(
            rx.el.button(
                rx.icon("wallet", class_name="h-4 w-4"),
                "Registrar pago",
                on_click=State.apply_reservation_payment,
                class_name="flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-emerald-600 text-white hover:bg-emerald-700 min-h-[44px]",
            ),
            rx.el.button(
                rx.icon("badge-check", class_name="h-4 w-4"),
                "Pagar saldo",
                on_click=State.pay_reservation_balance,
                class_name="flex items-center justify-center gap-2 px-4 py-2 rounded-md border text-indigo-700 hover:bg-indigo-50 min-h-[44px]",
            ),
            class_name="flex flex-col sm:flex-row gap-3",
        ),
        rx.cond(
            State.reservation_selected_for_payment == None,
            rx.el.div(
                rx.el.p("Selecciona una reserva para ver el saldo pendiente.", class_name="text-sm text-gray-600"),
                class_name="rounded-lg border border-dashed border-gray-200 p-3",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.span("Estado", class_name="text-xs uppercase text-gray-500"),
                    reservation_status_badge(State.reservation_selected_for_payment),
                    class_name="flex items-center gap-2",
                ),
                rx.el.div(
                    rx.el.span("Saldo pendiente", class_name="text-xs uppercase text-gray-500"),
                    rx.el.span(
                        State.currency_symbol,
                        State.selected_reservation_balance.to_string(),
                        class_name="text-lg font-semibold text-gray-900",
                    ),
                    class_name="flex items-center justify-between",
                ),
                rx.el.div(
                    rx.el.span("Horario", class_name="text-xs uppercase text-gray-500"),
                    rx.el.span(
                        State.reservation_selected_for_payment["start_datetime"],
                        " - ",
                        State.reservation_selected_for_payment["end_datetime"],
                        class_name="text-sm font-medium text-gray-800",
                    ),
                    class_name="flex items-center justify-between",
                ),
                class_name="rounded-lg border border-emerald-100 bg-emerald-50 p-3 flex flex-col gap-2",
            ),
        ),
        class_name="bg-white border border-gray-200 rounded-lg p-4 sm:p-5 shadow-sm flex flex-col gap-4",
    )


def cancellation_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h3("Cancelacion de reservas", class_name="text-lg font-semibold text-gray-800"),
            rx.el.p(
                "Selecciona la reserva, registra el motivo y marca el estado como cancelado.",
                class_name="text-sm text-gray-600",
            ),
            class_name="flex flex-col gap-1",
        ),
        rx.el.div(
            rx.el.label("Reserva a cancelar", class_name="text-sm font-medium text-gray-700"),
            rx.el.select(
                rx.el.option("Selecciona una reserva", value=""),
                rx.foreach(
                    State.active_reservation_options,
                    lambda option: rx.el.option(option["label"], value=option["id"]),
                ),
                value=State.reservation_cancel_selection,
                on_change=State.select_reservation_to_cancel,
                class_name="w-full p-2 border rounded-md bg-white",
            ),
            class_name="flex flex-col gap-1",
        ),
        rx.el.div(
            rx.el.label("Motivo de cancelacion", class_name="text-sm font-medium text-gray-700"),
            rx.el.textarea(
                placeholder="Describe el motivo",
                value=State.reservation_cancel_reason,
                on_change=State.set_reservation_cancel_reason,
                class_name="w-full p-2 border rounded-md min-h-[100px]",
            ),
            class_name="flex flex-col gap-1",
        ),
        rx.el.button(
            rx.icon("ban", class_name="h-4 w-4"),
            "Cancelar reserva",
            on_click=State.cancel_reservation,
            class_name="flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-red-600 text-white hover:bg-red-700 min-h-[44px]",
        ),
        class_name="bg-white border border-gray-200 rounded-lg p-4 sm:p-5 shadow-sm flex flex-col gap-3",
    )


def log_type_badge(entry: rx.Var[dict]) -> rx.Component:
    return rx.el.span(
        rx.cond(
            entry["type"] == "reserva",
            "Reserva creada",
            rx.cond(
                entry["type"] == "cancelacion",
                "Cancelacion",
                rx.cond(
                    entry["type"] == "eliminacion",
                    "Eliminacion",
                    rx.cond(entry["type"] == "adelanto", "Adelanto", "Pago"),
                ),
            ),
        ),
        class_name="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-700",
    )


def admin_log_row(entry: rx.Var[dict]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(entry["timestamp"], class_name="py-3 px-4"),
        rx.el.td(log_type_badge(entry), class_name="py-3 px-4"),
        rx.el.td(entry["client_name"], class_name="py-3 px-4"),
        rx.el.td(entry["field_name"], class_name="py-3 px-4"),
        rx.el.td(
            rx.el.span(
                State.currency_symbol,
                entry["amount"].to_string(),
                class_name="font-semibold",
            ),
            class_name="py-3 px-4 text-right",
        ),
        rx.el.td(
            rx.el.span(entry["status"].capitalize(), class_name="text-sm font-medium"),
            class_name="py-3 px-4",
        ),
        rx.el.td(entry["notes"], class_name="py-3 px-4 text-sm text-gray-600"),
        class_name="border-b",
    )


def admin_log_filters() -> rx.Component:
    """Filter section for the admin log."""
    start_filter, end_filter = date_range_filter(
        start_value=State.service_log_filter_start_date,
        end_value=State.service_log_filter_end_date,
        on_start_change=State.set_service_log_filter_start_date,
        on_end_change=State.set_service_log_filter_end_date,
        start_label="Fecha inicio",
        end_label="Fecha fin",
    )
    
    return rx.el.div(
        start_filter,
        end_filter,
        select_filter(
            "Deporte",
            [("Todos", "todos"), ("Futbol", "futbol"), ("Voley", "voley")],
            State.service_log_filter_sport,
            State.set_service_log_filter_sport,
        ),
        select_filter(
            "Estado",
            [
                ("Todos", "todos"),
                ("Pendiente", "pendiente"),
                ("Pagado", "pagado"),
                ("Cancelado", "cancelado"),
                ("Eliminado", "eliminado"),
            ],
            State.service_log_filter_status,
            State.set_service_log_filter_status,
        ),
        rx.el.button(
            rx.icon("eraser", class_name="h-4 w-4"),
            "Limpiar filtros",
            on_click=State.reset_service_log_filters,
            class_name=BUTTON_STYLES["secondary"],
        ),
        class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end",
    )


def admin_log_table() -> rx.Component:
    """Table showing administrative log entries."""
    return rx.el.div(
        section_header(
            "Registro administrativo",
            "Movimientos de reservas, cancelaciones y pagos con filtros por fecha, deporte y estado.",
        ),
        admin_log_filters(),
        rx.el.table(
            rx.el.thead(
                rx.el.tr(
                    rx.el.th("Fecha y hora", class_name="py-2 px-4 text-left"),
                    rx.el.th("Movimiento", class_name="py-2 px-4 text-left"),
                    rx.el.th("Cliente", class_name="py-2 px-4 text-left"),
                    rx.el.th("Campo", class_name="py-2 px-4 text-left"),
                    rx.el.th("Monto", class_name="py-2 px-4 text-right"),
                    rx.el.th("Estado", class_name="py-2 px-4 text-left"),
                    rx.el.th("Notas", class_name="py-2 px-4 text-left"),
                    class_name="bg-gray-100",
                )
            ),
            rx.el.tbody(rx.foreach(State.filtered_service_admin_log, admin_log_row)),
            class_name="min-w-full",
        ),
        rx.cond(
            State.filtered_service_admin_log.length() == 0,
            rx.el.p(
                "No hay movimientos para los filtros seleccionados.",
                class_name="text-center text-gray-500 py-4",
            ),
            rx.fragment(),
        ),
        class_name="bg-white border border-gray-200 rounded-lg p-4 sm:p-5 shadow-sm overflow-x-auto flex flex-col gap-4",
    )


def campo_tab() -> rx.Component:
    return rx.el.div(
        sport_selector(),
        schedule_planner(),
        reservations_table(),
        reservation_delete_modal(),
        reservation_modal(),
        class_name="flex flex-col gap-4",
    )


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
            "Gestiona el alquiler de campo con reservas, adelantos, cancelaciones y registros administrativos.",
            class_name="text-sm text-gray-600",
        ),
        rx.match(
            State.service_active_tab,
            ("campo", campo_tab()),
            ("piscina", servicio_card("Alquiler de Piscina", "Registro y seguimiento de alquiler de piscina.")),
            servicio_card("Alquiler de Campo", "Reserva y control de alquiler de campo."),
        ),
        class_name="p-4 sm:p-6 w-full max-w-7xl mx-auto flex flex-col gap-4",
    )
