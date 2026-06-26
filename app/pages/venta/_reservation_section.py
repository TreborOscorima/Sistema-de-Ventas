import reflex as rx
from app.state import State


def _data_pill(icon_name: str, label: str, value) -> rx.Component:
    return rx.el.div(
        rx.icon(icon_name, class_name="h-3.5 w-3.5 text-slate-400 shrink-0"),
        rx.el.span(label, class_name="text-xs text-slate-400"),
        rx.el.span(value, class_name="text-xs font-semibold text-slate-700"),
        class_name="flex items-center gap-1",
    )


def reservation_info_card() -> rx.Component:
    """Card compacta de reserva/servicio si existe."""
    return rx.cond(
        State.reservation_payment_id != "",
        rx.el.div(
            # Header + datos en una sola fila
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.icon("calendar-check", class_name="h-4 w-4 text-white"),
                        class_name="p-1.5 bg-emerald-600 rounded-lg shrink-0",
                    ),
                    rx.el.span("Cobro de Servicio", class_name="font-bold text-slate-800 text-sm"),
                    rx.el.div(
                        class_name="w-px h-4 bg-slate-200 mx-1",
                    ),
                    # Datos inline compactos
                    _data_pill("user", "Cliente:", State.reservation_selected_for_payment["client_name"]),
                    rx.el.div(class_name="w-px h-3 bg-slate-200"),
                    _data_pill("map-pin", "Campo:", State.reservation_selected_for_payment["field_name"]),
                    rx.el.div(class_name="w-px h-3 bg-slate-200"),
                    _data_pill("clock", "Horario:", State.reservation_selected_for_payment["start_datetime"]),
                    rx.el.div(class_name="w-px h-3 bg-slate-200"),
                    _data_pill("phone", "Tel:", State.reservation_selected_for_payment["phone"]),
                    class_name="flex items-center gap-2 flex-wrap flex-1 min-w-0",
                ),
                rx.el.button(
                    rx.icon("x", class_name="h-4 w-4"),
                    on_click=State.clear_pending_reservation,
                    title="Cerrar cobro de servicio",
                    aria_label="Cerrar cobro de servicio",
                    class_name="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors shrink-0",
                ),
                class_name="flex items-center justify-between gap-2 min-w-0",
            ),
            # Resumen de montos
            rx.el.div(
                rx.el.div(
                    rx.el.span("Total Reserva", class_name="text-xs text-slate-500"),
                    rx.el.span(
                        State.currency_symbol,
                        State.reservation_selected_for_payment["total_amount"],
                        class_name="text-base font-bold text-slate-700",
                    ),
                    class_name="flex flex-col items-center py-1.5 px-2 bg-slate-50 rounded-lg",
                ),
                rx.el.div(
                    rx.el.span("Adelanto Pagado", class_name="text-xs text-slate-500"),
                    rx.el.span(
                        State.currency_symbol,
                        State.reservation_selected_for_payment["advance_amount"],
                        class_name="text-base font-bold text-emerald-600",
                    ),
                    class_name="flex flex-col items-center py-1.5 px-2 bg-emerald-50 rounded-lg",
                ),
                rx.el.div(
                    rx.el.span("Saldo a Cobrar", class_name="text-xs text-slate-500"),
                    rx.el.span(
                        State.currency_symbol,
                        State.selected_reservation_balance_display,
                        class_name="text-xl font-bold text-indigo-600",
                    ),
                    class_name="flex flex-col items-center py-1.5 px-2 bg-indigo-50 rounded-lg border-2 border-indigo-200",
                ),
                class_name="grid grid-cols-3 gap-1 mt-2",
            ),
            class_name="bg-white border-2 border-emerald-200 rounded-xl p-2.5 shadow-sm",
        ),
        rx.fragment(),
    )


def _presupuesto_banner() -> rx.Component:
    """Banner flotante de presupuesto cargado en el carrito."""
    return rx.cond(
        State.loaded_quotation_id > 0,
        rx.el.div(
            rx.icon("file-text", class_name="w-4 h-4 text-indigo-600 shrink-0"),
            rx.el.span(
                "Presupuesto #",
                State.loaded_quotation_id.to_string(),
                " cargado — al confirmar quedará marcado como Procesado.",
                class_name="text-xs text-indigo-700",
            ),
            rx.el.button(
                rx.icon("x", class_name="w-3.5 h-3.5"),
                on_click=State.dismiss_loaded_quotation,
                class_name="ml-auto p-0.5 rounded text-indigo-400 hover:text-indigo-700 hover:bg-indigo-100",
                title="Descartar vínculo con presupuesto",
            ),
            class_name=(
                "flex items-center gap-2 px-3 py-2 "
                "bg-indigo-50 border border-indigo-200 rounded-xl shadow-sm"
            ),
        ),
        rx.fragment(),
    )


def _reservation_products_breakdown() -> rx.Component:
    """Desglose Servicio + Productos = Total cuando ambos coexisten."""
    return rx.cond(
        (State.reservation_payment_id != "")
        & (State.new_sale_items.length() > 0),
        rx.el.div(
            rx.el.div(
                rx.el.span("Servicio", class_name="text-xs text-slate-500"),
                rx.el.span(
                    State.currency_symbol,
                    State.selected_reservation_balance.to_string(),
                    class_name="text-sm font-semibold text-slate-700",
                ),
                class_name="flex flex-col items-center",
            ),
            rx.icon("plus", class_name="h-4 w-4 text-slate-400"),
            rx.el.div(
                rx.el.span("Productos", class_name="text-xs text-slate-500"),
                rx.el.span(
                    State.currency_symbol,
                    State.products_cart_subtotal_display,
                    class_name="text-sm font-semibold text-slate-700",
                ),
                class_name="flex flex-col items-center",
            ),
            rx.icon("equal", class_name="h-4 w-4 text-slate-400"),
            rx.el.div(
                rx.el.span("Total a Cobrar", class_name="text-xs font-medium text-indigo-600"),
                rx.el.span(
                    State.currency_symbol,
                    State.sale_total_display,
                    class_name="text-base font-bold text-indigo-700",
                ),
                class_name="flex flex-col items-center",
            ),
            class_name=(
                "flex flex-wrap items-center justify-center gap-4 py-2 px-4 "
                "bg-slate-50 border border-slate-200 rounded-xl"
            ),
        ),
        rx.fragment(),
    )
