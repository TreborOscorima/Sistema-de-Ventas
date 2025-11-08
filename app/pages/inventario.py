import reflex as rx
from app.state import State


def inventario_page() -> rx.Component:
    return rx.el.div(
        rx.el.h1(
            "Inventario Actual", class_name="text-2xl font-bold text-gray-800 mb-6"
        ),
        rx.el.div(
            rx.el.input(
                placeholder="Buscar producto...",
                on_change=State.set_inventory_search_term,
                class_name="w-full p-2 border rounded-md mb-4",
            ),
            class_name="bg-white p-6 rounded-lg shadow-md mb-6",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("Descripción", class_name="py-3 px-4 text-left"),
                        rx.el.th("Stock", class_name="py-3 px-4 text-center"),
                        rx.el.th("Unidad", class_name="py-3 px-4 text-center"),
                        rx.el.th("P. Compra", class_name="py-3 px-4 text-right"),
                        rx.el.th(
                            "P. Venta Sugerido", class_name="py-3 px-4 text-right"
                        ),
                        rx.el.th(
                            "Valor Total Stock", class_name="py-3 px-4 text-right"
                        ),
                        class_name="bg-gray-100",
                    )
                ),
                rx.el.tbody(
                    rx.foreach(
                        State.inventory_list,
                        lambda product: rx.el.tr(
                            rx.el.td(
                                product["description"],
                                class_name="py-3 px-4 font-medium",
                            ),
                            rx.el.td(
                                rx.el.div(
                                    product["stock"].to_string(),
                                    rx.cond(
                                        product["stock"] <= 5,
                                        rx.el.span(
                                            "Bajo",
                                            class_name="ml-2 text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-800",
                                        ),
                                        rx.cond(
                                            product["stock"] <= 10,
                                            rx.el.span(
                                                "Moderado",
                                                class_name="ml-2 text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800",
                                            ),
                                            rx.fragment(),
                                        ),
                                    ),
                                    class_name=rx.cond(
                                        product["stock"] <= 5,
                                        "flex items-center justify-center font-bold text-red-600",
                                        "flex items-center justify-center",
                                    ),
                                )
                            ),
                            rx.el.td(
                                product["unit"], class_name="py-3 px-4 text-center"
                            ),
                            rx.el.td(
                                f"${product['purchase_price'].to_string()}",
                                class_name="py-3 px-4 text-right",
                            ),
                            rx.el.td(
                                f"${product['sale_price'].to_string()}",
                                class_name="py-3 px-4 text-right text-green-600",
                            ),
                            rx.el.td(
                                f"${product['stock'] * product['purchase_price']:.2f}",
                                class_name="py-3 px-4 text-right font-bold",
                            ),
                            class_name="border-b",
                        ),
                    )
                ),
            ),
            rx.cond(
                State.inventory_list.length() == 0,
                rx.el.p(
                    "El inventario está vacío.",
                    class_name="text-gray-500 text-center py-8",
                ),
                rx.fragment(),
            ),
            class_name="bg-white p-6 rounded-lg shadow-md overflow-x-auto",
        ),
        class_name="p-6",
    )