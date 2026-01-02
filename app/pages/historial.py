import reflex as rx
from app.state import State
from app.components.ui import (
    pagination_controls,
    empty_state,
    select_filter,
    date_range_filter,
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
        # Primera fila: Filtros
        rx.el.div(
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
            class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end",
        ),
        # Segunda fila: Botones de acción
        rx.el.div(
            rx.el.button(
                rx.icon("search", class_name="h-4 w-4"),
                "Buscar",
                on_click=State.apply_history_filters,
                class_name=BUTTON_STYLES["primary"],
            ),
            rx.el.button(
                "Limpiar",
                on_click=State.reset_history_filters,
                class_name=BUTTON_STYLES["secondary"],
            ),
            rx.el.button(
                rx.icon("download", class_name="h-4 w-4"),
                "Exportar a Excel",
                on_click=State.export_to_excel,
                class_name=BUTTON_STYLES["success"],
            ),
            rx.el.button(
                rx.icon("refresh-cw", class_name="h-4 w-4"),
                "Actualizar",
                on_click=State.reload_history,
                class_name="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md shadow-sm transition-colors",
            ),
            class_name="flex flex-wrap gap-3 mt-4 justify-start lg:justify-end",
        ),
        class_name="flex flex-col",
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


def render_dynamic_card(card: rx.Var[dict]) -> rx.Component:
    icon_class = rx.match(
        card["color"],
        ("blue", "h-6 w-6 text-blue-600"),
        ("indigo", "h-6 w-6 text-indigo-600"),
        ("violet", "h-6 w-6 text-violet-600"),
        ("pink", "h-6 w-6 text-pink-600"),
        ("cyan", "h-6 w-6 text-cyan-600"),
        ("orange", "h-6 w-6 text-orange-600"),
        ("amber", "h-6 w-6 text-amber-600"),
        ("gray", "h-6 w-6 text-gray-600"),
        "h-6 w-6 text-gray-600",
    )
    icon_wrapper = rx.match(
        card["color"],
        ("blue", "p-3 rounded-lg bg-blue-100"),
        ("indigo", "p-3 rounded-lg bg-indigo-100"),
        ("violet", "p-3 rounded-lg bg-violet-100"),
        ("pink", "p-3 rounded-lg bg-pink-100"),
        ("cyan", "p-3 rounded-lg bg-cyan-100"),
        ("orange", "p-3 rounded-lg bg-orange-100"),
        ("amber", "p-3 rounded-lg bg-amber-100"),
        ("gray", "p-3 rounded-lg bg-gray-100"),
        "p-3 rounded-lg bg-gray-100",
    )
    icon_component = rx.match(
        card["icon"],
        ("coins", rx.icon("coins", class_name=icon_class)),
        ("credit-card", rx.icon("credit-card", class_name=icon_class)),
        ("qr-code", rx.icon("qr-code", class_name=icon_class)),
        ("landmark", rx.icon("landmark", class_name=icon_class)),
        ("layers", rx.icon("layers", class_name=icon_class)),
        ("circle-help", rx.icon("circle-help", class_name=icon_class)),
        rx.icon("circle-help", class_name=icon_class),
    )
    return rx.card(
        rx.el.div(
            rx.el.div(
                icon_component,
                class_name=icon_wrapper,
            ),
            rx.el.div(
                rx.el.p(card["name"], class_name="text-sm font-medium text-gray-500"),
                rx.el.p(
                    rx.el.span(
                        State.currency_symbol, card["amount"].to_string()
                    ),
                    class_name="text-2xl font-bold text-gray-800",
                ),
                class_name="flex-1",
            ),
            class_name="flex items-center gap-4",
        ),
        class_name="bg-white p-4 rounded-xl shadow-sm border",
    )


def historial_page() -> rx.Component:
    return rx.fragment(
        rx.el.div(
            rx.el.h1(
                "Historial y Estadísticas",
                class_name="text-2xl font-bold text-gray-800 mb-6",
            ),
            rx.el.div(
                rx.foreach(State.dynamic_payment_cards, render_dynamic_card),
                class_name="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-6",
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
        ),
        on_mount=State.reload_history,
    )
