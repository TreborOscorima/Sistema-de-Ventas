import reflex as rx
from app.state import State
from app.components.ui import (
    stat_card,
    pagination_controls,
    empty_state,
    select_filter,
    date_range_filter,
    filter_action_buttons,
    card_container,
    BUTTON_STYLES,
)


def history_filters() -> rx.Component:
    """Filter section for the history page."""
    start_filter, end_filter = date_range_filter(
        start_value=State.staged_history_filter_start_date,
        end_value=State.staged_history_filter_end_date,
        on_start_change=State.set_staged_history_filter_start_date,
        on_end_change=State.set_staged_history_filter_end_date,
    )
    
    return rx.el.div(
        select_filter(
            "Filtrar por tipo",
            [("Todos", "Todos"), ("Ingreso", "Ingreso"), ("Venta", "Venta")],
            State.staged_history_filter_type,
            State.set_staged_history_filter_type,
        ),
        rx.el.div(
            rx.el.label(
                "Buscar por producto",
                class_name="text-sm font-medium text-gray-600",
            ),
            rx.el.input(
                placeholder="Ej: Coca-Cola 600ml",
                on_change=State.set_staged_history_filter_product,
                class_name="w-full p-2 border rounded-md",
                default_value=State.staged_history_filter_product,
            ),
            class_name="flex flex-col gap-1",
        ),
        start_filter,
        end_filter,
        rx.el.div(
            filter_action_buttons(
                on_search=State.apply_history_filters,
                on_clear=State.reset_history_filters,
                on_export=State.export_to_excel,
                export_text="Exportar a Excel",
            ),
            class_name="sm:col-span-2 xl:col-span-1",
        ),
        class_name="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4 items-end",
    )


def history_table_row(movement: rx.Var[dict]) -> rx.Component:
    """Render a single row in the history table."""
    return rx.el.tr(
        rx.el.td(movement["timestamp"], class_name="py-3 px-4"),
        rx.el.td(
            rx.el.span(
                movement["type"],
                class_name=rx.cond(
                    movement["type"] == "Ingreso",
                    "px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800",
                    "px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800",
                ),
            )
        ),
        rx.el.td(movement["product_description"], class_name="py-3 px-4"),
        rx.el.td(movement["quantity"].to_string(), class_name="py-3 px-4 text-center"),
        rx.el.td(movement["unit"], class_name="py-3 px-4 text-center"),
        rx.el.td(
            State.currency_symbol,
            movement["total"].to_string(),
            class_name="py-3 px-4 text-right font-medium",
        ),
        rx.el.td(
            rx.cond(
                movement.get("payment_method"),
                rx.el.span(movement.get("payment_method"), class_name="font-medium"),
                rx.el.span("-", class_name="text-gray-400"),
            ),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            movement.get("payment_details", "-"),
            class_name="py-3 px-4 text-sm text-gray-600",
        ),
        class_name="border-b",
    )


def historial_page() -> rx.Component:
    return rx.el.div(
        rx.el.h1(
            "Historial y Estadísticas",
            class_name="text-2xl font-bold text-gray-800 mb-6",
        ),
        rx.el.div(
            stat_card(
                "banknote",
                "Ventas con Efectivo",
                rx.el.span(State.currency_symbol, State.total_ventas_efectivo.to_string()),
                "text-green-600",
            ),
            stat_card(
                "smartphone",
                "Ventas con Yape",
                rx.el.span(State.currency_symbol, State.total_ventas_yape.to_string()),
                "text-red-600",
            ),
            stat_card(
                "qr-code",
                "Ventas con Plin",
                rx.el.span(State.currency_symbol, State.total_ventas_plin.to_string()),
                "text-indigo-600",
            ),
            stat_card(
                "wallet",
                "Ventas Mixtas",
                rx.el.span(State.currency_symbol, State.total_ventas_mixtas.to_string()),
                "text-blue-600",
            ),
            class_name="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6",
        ),
        rx.el.div(
            history_filters(),
            class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md mb-6",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("Fecha y Hora", class_name="py-3 px-4 text-left"),
                        rx.el.th("Tipo", class_name="py-3 px-4 text-left"),
                        rx.el.th("Descripcion", class_name="py-3 px-4 text-left"),
                        rx.el.th("Cantidad", class_name="py-3 px-4 text-center"),
                        rx.el.th("Unidad", class_name="py-3 px-4 text-center"),
                        rx.el.th("Total", class_name="py-3 px-4 text-right"),
                        rx.el.th("Metodo de Pago", class_name="py-3 px-4 text-left"),
                        rx.el.th("Detalle Pago", class_name="py-3 px-4 text-left"),
                        class_name="bg-gray-100",
                    )
                ),
                rx.el.tbody(rx.foreach(State.paginated_history, history_table_row)),
            ),
            rx.cond(
                State.filtered_history.length() == 0,
                empty_state("No hay movimientos que coincidan con los filtros."),
                rx.fragment(),
            ),
            class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md overflow-x-auto flex flex-col gap-4",
        ),
        pagination_controls(
            current_page=State.current_page_history,
            total_pages=State.total_pages,
            on_prev=lambda: State.set_history_page(State.current_page_history - 1),
            on_next=lambda: State.set_history_page(State.current_page_history + 1),
        ),
        class_name="p-4 sm:p-6 w-full max-w-7xl mx-auto flex flex-col gap-6",
    )
