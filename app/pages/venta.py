import reflex as rx
from app.state import State


def sale_item_row(item: rx.Var[dict]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(item["description"], class_name="py-3 px-4"),
        rx.el.td(item["quantity"].to_string(), class_name="py-3 px-4 text-center"),
        rx.el.td(item["unit"], class_name="py-3 px-4 text-center"),
        rx.el.td(f"${item['price'].to_string()}", class_name="py-3 px-4 text-right"),
        rx.el.td(
            f"${item['subtotal'].to_string()}",
            class_name="py-3 px-4 text-right font-semibold",
        ),
        rx.el.td(
            rx.el.button(
                rx.icon("trash-2", class_name="h-4 w-4"),
                on_click=lambda: State.remove_item_from_sale(item["temp_id"]),
                class_name="p-2 text-red-500 hover:bg-red-100 rounded-full",
            ),
            class_name="py-3 px-4 text-center",
        ),
        class_name="border-b",
    )


def venta_page() -> rx.Component:
    return rx.el.div(
        rx.el.h1(
            "Control de Movimiento: Venta de Productos",
            class_name="text-2xl font-bold text-gray-800 mb-6",
        ),
        rx.el.div(
            rx.el.h2(
                "Añadir Producto a la Venta",
                class_name="text-lg font-semibold text-gray-700 mb-4",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.label(
                        "Descripción",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.input(
                        placeholder="Buscar producto...",
                        on_change=lambda val: State.handle_sale_change(
                            "description", val
                        ),
                        class_name="w-full p-2 border rounded-md",
                        default_value=State.new_sale_item["description"],
                    ),
                    rx.cond(
                        State.autocomplete_suggestions.length() > 0,
                        rx.el.div(
                            rx.foreach(
                                State.autocomplete_suggestions,
                                lambda suggestion: rx.el.button(
                                    suggestion,
                                    on_click=lambda: State.select_product_for_sale(
                                        suggestion
                                    ),
                                    class_name="w-full text-left p-2 hover:bg-gray-100",
                                ),
                            ),
                            class_name="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-60 overflow-y-auto",
                        ),
                        rx.fragment(),
                    ),
                    class_name="flex-grow relative",
                ),
                rx.el.div(
                    rx.el.label(
                        "Cantidad",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.input(
                        type="number",
                        on_change=lambda val: State.handle_sale_change("quantity", val),
                        class_name="w-full p-2 border rounded-md",
                        default_value=State.new_sale_item["quantity"].to_string(),
                    ),
                    class_name="w-24",
                ),
                rx.el.div(
                    rx.el.label(
                        "Unidad",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.input(
                        is_disabled=True,
                        class_name="w-full p-2 border rounded-md bg-gray-100",
                        default_value=State.new_sale_item["unit"],
                    ),
                    class_name="w-32",
                ),
                rx.el.div(
                    rx.el.label(
                        "Precio Venta",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.input(
                        type="number",
                        on_change=lambda val: State.handle_sale_change("price", val),
                        class_name="w-full p-2 border rounded-md",
                        default_value=State.new_sale_item["price"].to_string(),
                    ),
                    class_name="w-32",
                ),
                rx.el.div(
                    rx.el.label(
                        "Subtotal",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.div(
                        f"${State.sale_subtotal.to_string()}",
                        class_name="w-full p-2 font-semibold text-right",
                    ),
                    class_name="w-32",
                ),
                rx.el.div(
                    rx.el.button(
                        rx.icon("plus", class_name="h-5 w-5"),
                        "Añadir",
                        on_click=State.add_item_to_sale,
                        class_name="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 mt-6",
                    )
                ),
                class_name="flex flex-wrap items-start gap-4",
            ),
            class_name="bg-white p-6 rounded-lg shadow-md mb-6",
        ),
        rx.el.div(
            rx.el.h2(
                "Productos en la Venta",
                class_name="text-lg font-semibold text-gray-700 mb-4",
            ),
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("Descripción", class_name="py-2 px-4 text-left"),
                            rx.el.th("Cantidad", class_name="py-2 px-4 text-center"),
                            rx.el.th("Unidad", class_name="py-2 px-4 text-center"),
                            rx.el.th("P. Venta", class_name="py-2 px-4 text-right"),
                            rx.el.th("Subtotal", class_name="py-2 px-4 text-right"),
                            rx.el.th("Acción", class_name="py-2 px-4 text-center"),
                        ),
                        class_name="bg-gray-100",
                    ),
                    rx.el.tbody(rx.foreach(State.new_sale_items, sale_item_row)),
                ),
                class_name="overflow-x-auto",
            ),
            rx.cond(
                State.new_sale_items.length() == 0,
                rx.el.p(
                    "Aún no has añadido productos a la venta.",
                    class_name="text-gray-500 text-center py-8",
                ),
                rx.fragment(),
            ),
            class_name="bg-white p-6 rounded-lg shadow-md",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span("Total General:", class_name="text-xl font-bold"),
                rx.el.span(
                    f"${State.sale_total.to_string()}",
                    class_name="text-xl font-bold text-indigo-700",
                ),
                class_name="flex items-center gap-4",
            ),
            rx.el.button(
                "Confirmar Venta",
                on_click=State.confirm_sale,
                class_name="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 font-semibold",
            ),
            class_name="flex justify-between items-center mt-6",
        ),
        class_name="p-6",
    )