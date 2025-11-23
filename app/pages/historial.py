import reflex as rx
from app.state import State


def stat_card(icon: str, title: str, value: rx.Var, color: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, class_name=f"h-6 w-6 {color}"),
            class_name="p-3 bg-gray-100 rounded-lg",
        ),
        rx.el.div(
            rx.el.p(title, class_name="text-sm font-medium text-gray-500"),
            rx.el.p(value, class_name="text-2xl font-bold text-gray-800"),
            class_name="flex-grow",
        ),
        class_name="flex items-center gap-4 bg-white p-4 rounded-xl shadow-sm border",
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
                f"${State.total_ventas_efectivo.to_string()}",
                "text-green-600",
            ),
            stat_card(
                "smartphone",
                "Ventas con Yape",
                f"${State.total_ventas_yape.to_string()}",
                "text-red-600",
            ),
            stat_card(
                "qr-code",
                "Ventas con Plin",
                f"${State.total_ventas_plin.to_string()}",
                "text-indigo-600",
            ),
            stat_card(
                "wallet",
                "Ventas Mixtas",
                f"${State.total_ventas_mixtas.to_string()}",
                "text-blue-600",
            ),
            class_name="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.label(
                        "Filtrar por tipo",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.select(
                        rx.el.option("Todos", value="Todos"),
                        rx.el.option("Ingreso", value="Ingreso"),
                        rx.el.option("Venta", value="Venta"),
                        default_value=State.staged_history_filter_type,
                        on_change=State.set_staged_history_filter_type,
                        class_name="w-full p-2 border rounded-md",
                    ),
                ),
                rx.el.div(
                    rx.el.label(
                        "Buscar por producto",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.input(
                        placeholder="Ej: Coca-Cola 600ml",
                        on_change=State.set_staged_history_filter_product,
                        class_name="w-full p-2 border rounded-md",
                        default_value=State.staged_history_filter_product,
                    ),
                ),
                rx.el.div(
                    rx.el.label(
                        "Fecha Inicio",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.input(
                        type="date",
                        on_change=State.set_staged_history_filter_start_date,
                        default_value=State.staged_history_filter_start_date,
                        class_name="w-full p-2 border rounded-md",
                    ),
                ),
                rx.el.div(
                    rx.el.label(
                        "Fecha Fin",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.input(
                        type="date",
                        on_change=State.set_staged_history_filter_end_date,
                        default_value=State.staged_history_filter_end_date,
                        class_name="w-full p-2 border rounded-md",
                    ),
                ),
                rx.el.button(
                    "Buscar",
                    on_click=State.apply_history_filters,
                    class_name="mt-6 bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700",
                ),
                rx.el.button(
                    "Limpiar",
                    on_click=State.reset_history_filters,
                    class_name="mt-6 bg-gray-200 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-300",
                ),
                rx.el.button(
                    "Exportar a Excel",
                    on_click=State.export_to_excel,
                    class_name="mt-6 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700",
                ),
                class_name="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 items-end",
            ),
            class_name="bg-white p-6 rounded-lg shadow-md mb-6",
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
                rx.el.tbody(
                    rx.foreach(
                        State.paginated_history,
                        lambda movement: rx.el.tr(
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
                            rx.el.td(
                                movement["product_description"], class_name="py-3 px-4"
                            ),
                            rx.el.td(
                                movement["quantity"].to_string(),
                                class_name="py-3 px-4 text-center",
                            ),
                            rx.el.td(
                                movement["unit"], class_name="py-3 px-4 text-center"
                            ),
                            rx.el.td(
                                f"${movement['total'].to_string()}",
                                class_name="py-3 px-4 text-right font-medium",
                            ),
                            rx.el.td(
                                rx.cond(
                                    movement.get("payment_method"),
                                    rx.el.span(
                                        movement.get("payment_method"),
                                        class_name="font-medium",
                                    ),
                                    rx.el.span("-", class_name="text-gray-400"),
                                ),
                                class_name="py-3 px-4",
                            ),
                            rx.el.td(
                                movement.get("payment_details", "-"),
                                class_name="py-3 px-4 text-sm text-gray-600",
                            ),
                            class_name="border-b",
                        ),
                    )
                ),
            ),
            rx.cond(
                State.filtered_history.length() == 0,
                rx.el.p(
                    "No hay movimientos que coincidan con los filtros.",
                    class_name="text-gray-500 text-center py-8",
                ),
                rx.fragment(),
            ),
            class_name="bg-white p-6 rounded-lg shadow-md overflow-x-auto",
        ),
        rx.el.div(
            rx.el.button(
                "Anterior",
                on_click=lambda: State.set_history_page(State.current_page_history - 1),
                is_disabled=State.current_page_history <= 1,
                class_name="px-4 py-2 bg-gray-200 rounded-md disabled:opacity-50",
            ),
            rx.el.span(f"Página {State.current_page_history} de {State.total_pages}"),
            rx.el.button(
                "Siguiente",
                on_click=lambda: State.set_history_page(State.current_page_history + 1),
                is_disabled=State.current_page_history >= State.total_pages,
                class_name="px-4 py-2 bg-gray-200 rounded-md disabled:opacity-50",
            ),
            class_name="flex justify-center items-center gap-4 mt-6",
        ),
        class_name="p-6",
    )
