import reflex as rx
from app.state import State
from app.components.ui import (
    pagination_controls,
    empty_state,
    select_filter,
    date_range_filter,
    BUTTON_STYLES,
    permission_guard,
)


def history_filters() -> rx.Component:
    """Seccion de filtros para la pagina de historial."""
    def _build_filters() -> list[rx.Component]:
        start_filter, end_filter = date_range_filter(
            start_value=State.staged_history_filter_start_date,
            end_value=State.staged_history_filter_end_date,
            on_start_change=State.set_staged_history_filter_start_date,
            on_end_change=State.set_staged_history_filter_end_date,
        )
        filters = [
            select_filter(
                "Filtrar por tipo",
                [("Todos", "Todos"), ("Venta", "Venta")],
                State.staged_history_filter_type,
                State.set_staged_history_filter_type,
            ),
            rx.el.div(
                rx.el.label(
                    "Categoria",
                    class_name="text-sm font-medium text-gray-600",
                ),
                rx.el.select(
                    rx.foreach(
                        State.available_category_options,
                        lambda option: rx.el.option(
                            option[0], value=option[1]
                        ),
                    ),
                    value=State.staged_history_filter_category,
                    on_change=State.set_staged_history_filter_category,
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
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
        ]
        return [
            rx.el.div(filter_item, class_name="min-w-[160px] flex-1")
            for filter_item in filters
        ]

    def _build_actions() -> list[rx.Component]:
        return [
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
                "Exportar",
                on_click=State.export_to_excel,
                class_name=BUTTON_STYLES["success"],
            ),
        ]

    return rx.el.div(
        rx.el.div(
            *_build_filters(),
            class_name="flex flex-wrap lg:flex-nowrap gap-3 items-end",
        ),
        rx.el.div(
            *_build_actions(),
            class_name="flex flex-wrap gap-2 justify-end",
        ),
        class_name="flex flex-col gap-3 pb-4 border-b border-gray-200",
    )


def payment_method_badge(method: rx.Var[str]) -> rx.Component:
    return rx.cond(
        method,
        rx.match(
            method,
            (
                "No especificado",
                rx.el.span(
                    "No especificado",
                    class_name="text-xs font-semibold text-gray-400",
                ),
            ),
            ("-", rx.el.span("-", class_name="text-xs font-semibold text-gray-400")),
            ("Crédito", rx.badge("Crédito", color_scheme="yellow")),
            ("Credito", rx.badge("Crédito", color_scheme="yellow")),
            (
                "Crédito c/ Inicial",
                rx.badge("Crédito c/ Inicial", color_scheme="yellow"),
            ),
            (
                "Credito c/ Inicial",
                rx.badge("Crédito c/ Inicial", color_scheme="yellow"),
            ),
            ("Efectivo", rx.badge("Efectivo", color_scheme="green")),
            ("Yape", rx.badge("Yape", color_scheme="purple")),
            (
                "Billetera Digital (Yape)",
                rx.badge("Yape", color_scheme="purple"),
            ),
            ("Plin", rx.badge("Plin", color_scheme="pink")),
            (
                "Billetera Digital (Plin)",
                rx.badge("Plin", color_scheme="pink"),
            ),
            (
                "Transferencia",
                rx.badge("Transferencia", color_scheme="orange"),
            ),
            (
                "Transferencia Bancaria",
                rx.badge("Transferencia", color_scheme="orange"),
            ),
            ("Pago Mixto", rx.badge("Pago Mixto", color_scheme="orange")),
            ("T. Debito", rx.badge("T. Debito", color_scheme="blue")),
            ("T. Credito", rx.badge("T. Credito", color_scheme="blue")),
            (
                "Tarjeta de Débito",
                rx.badge("Tarjeta de Débito", color_scheme="blue"),
            ),
            (
                "Tarjeta de Crédito",
                rx.badge("Tarjeta de Crédito", color_scheme="blue"),
            ),
            rx.badge(method, color_scheme="gray"),
        ),
        rx.el.span(
            "No especificado",
            class_name="text-xs font-semibold text-gray-400",
        ),
    )


def history_table_row(movement: rx.Var[dict]) -> rx.Component:
    """Renderiza una fila del listado de historial."""
    return rx.el.tr(
        rx.el.td(movement["timestamp"], class_name="py-3 px-4"),
        rx.el.td(
            movement["client_name"],
            class_name="py-3 px-4",
        ),
        rx.el.td(
            State.currency_symbol,
            movement["total"].to_string(),
            class_name="py-3 px-4 text-right font-semibold",
        ),
        rx.el.td(
            payment_method_badge(movement.get("payment_method")),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            movement.get("user", "Desconocido"),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.el.button(
                rx.icon("eye", class_name="h-4 w-4"),
                "Ver Detalle",
                on_click=lambda _, sale_id=movement["sale_id"]: State.open_sale_detail(sale_id),
                class_name=BUTTON_STYLES["link_primary"],
            ),
            class_name="py-3 px-4 text-center",
        ),
        class_name="border-b",
    )

def sale_detail_modal() -> rx.Component:
    return rx.radix.primitives.dialog.root(
        rx.radix.primitives.dialog.portal(
            rx.radix.primitives.dialog.overlay(
                class_name="fixed inset-0 bg-black/40 z-40 modal-overlay"
            ),
            rx.radix.primitives.dialog.content(
                rx.el.div(
                    rx.el.h3("Detalle de venta", class_name="text-lg font-semibold text-gray-800"),
                    rx.el.p(
                        "Productos y resumen del comprobante seleccionado.",
                        class_name="text-sm text-gray-600",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.cond(
                    State.selected_sale_id == "",
                    rx.el.p("Venta no disponible.", class_name="text-sm text-gray-600"),
                    rx.el.div(
                        rx.el.div(
                            rx.el.div(
                                rx.el.span("Fecha", class_name="text-xs uppercase text-gray-500"),
                                rx.el.span(
                                    State.selected_sale_summary["timestamp"],
                                    class_name="text-sm font-semibold text-gray-900",
                                ),
                                class_name="flex flex-col gap-1",
                            ),
                            rx.el.div(
                                rx.el.span("Cliente", class_name="text-xs uppercase text-gray-500"),
                                rx.el.span(
                                    State.selected_sale_summary["client_name"],
                                    class_name="text-sm font-semibold text-gray-900",
                                ),
                                class_name="flex flex-col gap-1",
                            ),
                            rx.el.div(
                                rx.el.span("Usuario", class_name="text-xs uppercase text-gray-500"),
                                rx.el.span(
                                    State.selected_sale_summary["user"],
                                    class_name="text-sm font-semibold text-gray-900",
                                ),
                                class_name="flex flex-col gap-1",
                            ),
                            class_name="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-gray-50 border border-gray-100 rounded-md p-3",
                        ),
                        rx.el.div(
                            rx.el.div(
                                rx.el.span("Metodo de pago", class_name="text-xs uppercase text-gray-500"),
                                payment_method_badge(State.selected_sale_summary["payment_method"]),
                                class_name="flex flex-col gap-1",
                            ),
                            rx.el.div(
                                rx.el.span("Total", class_name="text-xs uppercase text-gray-500"),
                                rx.el.span(
                                    State.currency_symbol,
                                    State.selected_sale_summary["total"].to_string(),
                                    class_name="text-lg font-semibold text-gray-900",
                                ),
                                class_name="flex flex-col gap-1",
                            ),
                            class_name="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-gray-50 border border-gray-100 rounded-md p-3",
                        ),
                        rx.el.div(
                            rx.el.h4("Productos", class_name="text-sm font-semibold text-gray-700"),
                            rx.cond(
                                State.selected_sale_items_view.length() == 0,
                                rx.el.p(
                                    "Sin productos registrados.",
                                    class_name="text-sm text-gray-600",
                                ),
                                rx.el.div(
                                    rx.el.table(
                                        rx.el.thead(
                                            rx.el.tr(
                                                rx.el.th("Producto", class_name="py-2 px-3 text-left"),
                                                rx.el.th("Cantidad", class_name="py-2 px-3 text-right"),
                                                rx.el.th("Precio", class_name="py-2 px-3 text-right"),
                                                rx.el.th("Subtotal", class_name="py-2 px-3 text-right"),
                                                class_name="bg-gray-100 text-sm",
                                            )
                                        ),
                                        rx.el.tbody(
                                            rx.foreach(
                                                State.selected_sale_items_view,
                                                lambda item: rx.el.tr(
                                                    rx.el.td(item["description"], class_name="py-2 px-3 text-sm"),
                                                    rx.el.td(item["quantity"].to_string(), class_name="py-2 px-3 text-right text-sm"),
                                                    rx.el.td(
                                                        State.currency_symbol,
                                                        item["unit_price"].to_string(),
                                                        class_name="py-2 px-3 text-right text-sm",
                                                    ),
                                                    rx.el.td(
                                                        State.currency_symbol,
                                                        item["subtotal"].to_string(),
                                                        class_name="py-2 px-3 text-right text-sm font-semibold",
                                                    ),
                                                    class_name="border-b",
                                                ),
                                            )
                                        ),
                                        class_name="min-w-full text-sm",
                                    ),
                                    class_name="max-h-64 overflow-y-auto overflow-x-auto border rounded-lg",
                                ),
                            ),
                            class_name="flex flex-col gap-2",
                        ),
                        class_name="flex flex-col gap-4",
                    ),
                ),
                rx.el.div(
                    rx.el.button(
                        "Cerrar",
                        on_click=State.close_sale_detail,
                        class_name="px-4 py-2 rounded-md border text-gray-700 hover:bg-gray-50 min-h-[40px]",
                    ),
                    class_name="flex justify-end gap-3",
                ),
                class_name=(
                    "bg-white rounded-lg shadow-lg p-5 w-full max-w-3xl space-y-4 "
                    "data-[state=open]:animate-in data-[state=closed]:animate-out "
                    "data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0 "
                    "data-[state=open]:zoom-in-95 data-[state=closed]:zoom-out-95 "
                    "data-[state=open]:slide-in-from-top-4 data-[state=closed]:slide-out-to-top-4 "
                    "fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-3xl -translate-x-1/2 -translate-y-1/2 shadow-xl focus:outline-none"
                ),
            ),
        ),
        open=State.sale_detail_modal_open,
        on_open_change=State.set_sale_detail_modal_open,
    )


def credit_sales_card() -> rx.Component:
    return rx.card(
        rx.el.div(
            rx.el.div(
                rx.icon("credit-card", class_name="h-6 w-6 text-amber-600"),
                class_name="p-3 rounded-lg bg-amber-100",
            ),
            rx.el.div(
                rx.el.p(
                    "Saldo por cobrar (Credito)",
                    class_name="text-sm font-medium text-gray-500",
                ),
                rx.el.p(
                    rx.el.span(
                        State.currency_symbol, State.credit_outstanding.to_string()
                    ),
                    class_name="text-2xl font-bold text-gray-800",
                ),
                class_name="flex-1",
            ),
            class_name="flex items-center gap-4",
        ),
        class_name="bg-white p-4 rounded-xl shadow-sm border",
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
    content = rx.fragment(
        rx.el.div(
            rx.el.div(
                rx.el.h1(
                    "Historial de Ventas",
                    class_name="text-2xl font-bold text-gray-800",
                ),
                rx.el.p(
                    "Consulta y exporta el registro de todas las ventas realizadas.",
                    class_name="text-sm text-gray-500 mt-1",
                ),
                class_name="mb-6",
            ),
            rx.el.div(
                credit_sales_card(),
                rx.foreach(State.dynamic_payment_cards, render_dynamic_card),
                class_name="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-6",
            ),
            rx.el.div(
                history_filters(),
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("Fecha y Hora", class_name="py-3 px-4 text-left"),
                            rx.el.th("Cliente", class_name="py-3 px-4 text-left"),
                            rx.el.th("Total", class_name="py-3 px-4 text-right"),
                            rx.el.th("Metodo de Pago", class_name="py-3 px-4 text-left"),
                            rx.el.th("Usuario", class_name="py-3 px-4 text-left"),
                            rx.el.th("Acciones", class_name="py-3 px-4 text-center"),
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
            # Nota: Los reportes financieros ahora se generan desde el módulo Reportes
            # para mantener un único punto de verdad para datos contables
            rx.el.div(
                rx.el.div(
                    rx.icon("info", class_name="w-5 h-5 text-blue-500"),
                    rx.el.div(
                        rx.el.p("¿Necesitas reportes financieros?", class_name="font-medium text-gray-800"),
                        rx.el.p(
                            "Los reportes de ingresos por método de pago, detalle de cobros y cierres de caja ahora se generan desde el módulo ",
                            rx.link("Reportes", href="/reportes", class_name="text-blue-600 hover:underline font-medium"),
                            " para garantizar datos 100% exactos y consolidados.",
                            class_name="text-sm text-gray-600",
                        ),
                        class_name="flex-1",
                    ),
                    class_name="flex items-start gap-3",
                ),
                class_name="bg-blue-50 border border-blue-200 rounded-lg p-4",
            ),
            class_name="p-4 sm:p-6 w-full max-w-7xl mx-auto flex flex-col gap-6",
        ),
        sale_detail_modal(),
        on_mount=State.reload_history,
    )
    return permission_guard(
        has_permission=State.can_view_historial,
        content=content,
        redirect_message="Acceso denegado a Historial",
    )
