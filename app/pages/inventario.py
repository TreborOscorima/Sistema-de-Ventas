import reflex as rx
from app.state import State
from app.components.ui import pagination_controls, permission_guard


def edit_product_modal() -> rx.Component:
    return rx.cond(
        State.is_editing_product,
        rx.el.div(
            rx.el.div(
                on_click=State.cancel_edit_product,
                class_name="fixed inset-0 bg-black/40 modal-overlay",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.h3(
                        "Editar Producto",
                        class_name="text-xl font-semibold text-gray-800",
                    ),
                    rx.el.button(
                        rx.icon("x", class_name="h-4 w-4"),
                        on_click=State.cancel_edit_product,
                        class_name="p-2 rounded-full hover:bg-gray-100",
                    ),
                    class_name="flex items-start justify-between gap-4 mb-4",
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.label("Código de Barra", class_name="block text-sm font-medium text-gray-700"),
                        rx.el.input(
                            value=State.editing_product["barcode"],
                            on_change=lambda v: State.handle_edit_product_change("barcode", v),
                            class_name="w-full p-2 border rounded-md",
                        ),
                    ),
                    rx.el.div(
                        rx.el.label("Descripción", class_name="block text-sm font-medium text-gray-700"),
                        rx.el.input(
                            value=State.editing_product["description"],
                            on_change=lambda v: State.handle_edit_product_change("description", v),
                            class_name="w-full p-2 border rounded-md",
                        ),
                    ),
                    rx.el.div(
                        rx.el.label("Categoría", class_name="block text-sm font-medium text-gray-700"),
                        rx.el.select(
                            rx.foreach(
                                State.categories,
                                lambda cat: rx.el.option(cat, value=cat)
                            ),
                            value=State.editing_product["category"],
                            on_change=lambda v: State.handle_edit_product_change("category", v),
                            class_name="w-full p-2 border rounded-md",
                        ),
                    ),
                    rx.el.div(
                        rx.el.label("Stock", class_name="block text-sm font-medium text-gray-700"),
                        rx.el.input(
                            type="number",
                            value=State.editing_product["stock"].to_string(),
                            on_change=lambda v: State.handle_edit_product_change("stock", v),
                            class_name="w-full p-2 border rounded-md",
                        ),
                    ),
                    rx.el.div(
                        rx.el.label("Unidad", class_name="block text-sm font-medium text-gray-700"),
                        rx.el.select(
                            rx.el.option("Unidad", value="Unidad"),
                            rx.el.option("Kg", value="Kg"),
                            rx.el.option("Lt", value="Lt"),
                            rx.el.option("Paquete", value="Paquete"),
                            rx.el.option("Caja", value="Caja"),
                            value=State.editing_product["unit"],
                            on_change=lambda v: State.handle_edit_product_change("unit", v),
                            class_name="w-full p-2 border rounded-md",
                        ),
                    ),
                    rx.el.div(
                        rx.el.label("Precio Compra", class_name="block text-sm font-medium text-gray-700"),
                        rx.el.input(
                            type="number",
                            value=State.editing_product["purchase_price"].to_string(),
                            on_change=lambda v: State.handle_edit_product_change("purchase_price", v),
                            class_name="w-full p-2 border rounded-md",
                        ),
                    ),
                    rx.el.div(
                        rx.el.label("Precio Venta", class_name="block text-sm font-medium text-gray-700"),
                        rx.el.input(
                            type="number",
                            value=State.editing_product["sale_price"].to_string(),
                            on_change=lambda v: State.handle_edit_product_change("sale_price", v),
                            class_name="w-full p-2 border rounded-md",
                        ),
                    ),
                    class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=State.cancel_edit_product,
                        class_name="px-4 py-2 rounded-md border text-gray-700 hover:bg-gray-50",
                    ),
                    rx.el.button(
                        "Guardar Cambios",
                        on_click=State.save_edited_product,
                        class_name="px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700",
                    ),
                    class_name="flex flex-col sm:flex-row sm:justify-end gap-3 mt-6",
                ),
                class_name="relative z-10 w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto",
            ),
            class_name="fixed inset-0 z-50 flex items-start sm:items-center justify-center px-4 py-6 overflow-hidden",
        ),
        rx.fragment(),
    )


def inventory_adjustment_modal() -> rx.Component:
    return rx.cond(
        State.inventory_check_modal_open,
        rx.el.div(
            rx.el.div(
                on_click=State.close_inventory_check_modal,
                class_name="fixed inset-0 bg-black/40 modal-overlay",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.h3(
                        "Registro de Inventario Fisico",
                        class_name="text-xl font-semibold text-gray-800",
                    ),
                    rx.el.button(
                        rx.icon("x", class_name="h-4 w-4"),
                        on_click=State.close_inventory_check_modal,
                        class_name="p-2 rounded-full hover:bg-gray-100",
                    ),
                    class_name="flex items-start justify-between gap-4",
                ),
                rx.el.p(
                    "Indique el resultado del inventario fisico y registre notas para sustentar cualquier re ajuste.",
                    class_name="text-sm text-gray-600 mt-2",
                ),
                rx.el.div(
                    rx.el.button(
                        rx.icon("circle_check", class_name="h-4 w-4"),
                        "Inventario Perfecto",
                        on_click=lambda: State.set_inventory_check_status("perfecto"),
                        class_name=rx.cond(
                            State.inventory_check_status == "perfecto",
                            "px-4 py-2 rounded-lg bg-indigo-600 text-white font-semibold flex items-center justify-center gap-2",
                            "px-4 py-2 rounded-lg border text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-2",
                        ),
                    ),
                    rx.el.button(
                        rx.icon("triangle_alert", class_name="h-4 w-4"),
                        "Re Ajuste de Inventario",
                        on_click=lambda: State.set_inventory_check_status("ajuste"),
                        class_name=rx.cond(
                            State.inventory_check_status == "ajuste",
                            "px-4 py-2 rounded-lg bg-amber-600 text-white font-semibold flex items-center justify-center gap-2",
                            "px-4 py-2 rounded-lg border text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-2",
                        ),
                    ),
                    class_name="grid grid-cols-1 md:grid-cols-2 gap-3",
                ),
                rx.cond(
                    State.inventory_check_status == "ajuste",
                    rx.el.div(
                        rx.el.h4(
                            "Productos con diferencias",
                            class_name="text-sm font-semibold text-gray-700",
                        ),
                        rx.el.div(
                            rx.el.label(
                                "Buscar producto",
                                class_name="text-sm font-medium text-gray-600",
                            ),
                            rx.el.div(
                                rx.el.input(
                                    placeholder="Ej: Gaseosa 500ml",
                                    value=State.inventory_adjustment_item[
                                        "description"
                                    ],
                                    on_change=lambda value: State.handle_inventory_adjustment_change(
                                        "description", value
                                    ),
                                    class_name="w-full p-2 border rounded-md",
                                ),
                                rx.cond(
                                    State.inventory_adjustment_suggestions.length()
                                    > 0,
                                    rx.el.div(
                                        rx.foreach(
                                            State.inventory_adjustment_suggestions,
                                            lambda suggestion: rx.el.button(
                                                suggestion,
                                                on_click=lambda _,
                                                suggestion=suggestion: State.select_inventory_adjustment_product(
                                                    suggestion
                                                ),
                                                class_name="w-full text-left px-3 py-2 hover:bg-gray-100",
                                            ),
                                        ),
                                        class_name="absolute z-20 w-full mt-1 border rounded-md bg-white shadow-lg max-h-48 overflow-y-auto",
                                    ),
                                    rx.fragment(),
                                ),
                                class_name="relative",
                            ),
                            class_name="mt-3",
                        ),
                        rx.el.div(
                            rx.el.div(
                                rx.el.label(
                                    "Codigo de barra",
                                    class_name="text-xs text-gray-500 uppercase",
                                ),
                                rx.el.input(
                                    value=State.inventory_adjustment_item["barcode"],
                                    is_disabled=True,
                                    class_name="w-full p-2 border rounded-md bg-gray-100",
                                ),
                            ),
                            rx.el.div(
                                rx.el.label(
                                    "Categoria",
                                    class_name="text-xs text-gray-500 uppercase",
                                ),
                                rx.el.input(
                                    value=State.inventory_adjustment_item["category"],
                                    is_disabled=True,
                                    class_name="w-full p-2 border rounded-md bg-gray-100",
                                ),
                            ),
                            rx.el.div(
                                rx.el.label(
                                    "Unidad",
                                    class_name="text-xs text-gray-500 uppercase",
                                ),
                                rx.el.input(
                                    value=State.inventory_adjustment_item["unit"],
                                    is_disabled=True,
                                    class_name="w-full p-2 border rounded-md bg-gray-100",
                                ),
                            ),
                            rx.el.div(
                                rx.el.label(
                                    "Stock disponible",
                                    class_name="text-xs text-gray-500 uppercase",
                                ),
                                rx.el.input(
                                    value=State.inventory_adjustment_item[
                                        "current_stock"
                                    ].to_string(),
                                    is_disabled=True,
                                    class_name="w-full p-2 border rounded-md bg-gray-100",
                                ),
                            ),
                            class_name="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4",
                        ),
                        rx.el.div(
                            rx.el.div(
                                rx.el.label(
                                    "Cantidad a ajustar",
                                    class_name="text-sm font-medium text-gray-700",
                                ),
                                rx.el.input(
                                    type="number",
                                    min="0",
                                    step="0.01",
                                    value=State.inventory_adjustment_item[
                                        "adjust_quantity"
                                    ].to_string(),
                                    on_change=lambda value: State.handle_inventory_adjustment_change(
                                        "adjust_quantity", value
                                    ),
                                    class_name="w-full p-2 border rounded-md",
                                ),
                            ),
                            rx.el.div(
                                rx.el.label(
                                    "Motivo del ajuste",
                                    class_name="text-sm font-medium text-gray-700",
                                ),
                                rx.el.textarea(
                                    placeholder="Ej: Producto dañado, consumo interno, vencido, etc.",
                                    value=State.inventory_adjustment_item["reason"],
                                    on_change=lambda value: State.handle_inventory_adjustment_change(
                                        "reason", value
                                    ),
                                    class_name="w-full h-24 p-2 border rounded-md",
                                ),
                            ),
                            class_name="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4",
                        ),
                        rx.el.button(
                            rx.icon("plus", class_name="h-4 w-4"),
                            "Agregar producto al ajuste",
                            on_click=State.add_inventory_adjustment_item,
                            class_name="mt-4 flex items-center justify-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 min-h-[42px]",
                        ),
                        rx.cond(
                            State.inventory_adjustment_items.length() > 0,
                            rx.el.div(
                                rx.el.table(
                                    rx.el.thead(
                                        rx.el.tr(
                                            rx.el.th(
                                                "Producto",
                                                class_name="py-2 px-3 text-left",
                                            ),
                                            rx.el.th(
                                                "Unidad",
                                                class_name="py-2 px-3 text-center",
                                            ),
                                            rx.el.th(
                                                "Stock",
                                                class_name="py-2 px-3 text-center",
                                            ),
                                            rx.el.th(
                                                "Cantidad Ajuste",
                                                class_name="py-2 px-3 text-center",
                                            ),
                                            rx.el.th(
                                                "Motivo",
                                                class_name="py-2 px-3 text-left",
                                            ),
                                            rx.el.th(
                                                "Accion",
                                                class_name="py-2 px-3 text-center",
                                            ),
                                            class_name="bg-gray-100",
                                        )
                                    ),
                                    rx.el.tbody(
                                        rx.foreach(
                                            State.inventory_adjustment_items,
                                            lambda item: rx.el.tr(
                                                rx.el.td(
                                                    item["description"],
                                                    class_name="py-2 px-3 font-medium",
                                                ),
                                                rx.el.td(
                                                    item["unit"],
                                                    class_name="py-2 px-3 text-center",
                                                ),
                                                rx.el.td(
                                                    item["current_stock"].to_string(),
                                                    class_name="py-2 px-3 text-center text-gray-500",
                                                ),
                                                rx.el.td(
                                                    item["adjust_quantity"].to_string(),
                                                    class_name="py-2 px-3 text-center text-red-600 font-semibold",
                                                ),
                                                rx.el.td(
                                                    rx.cond(
                                                        item["reason"] == "",
                                                        "-",
                                                        item["reason"],
                                                    ),
                                                    class_name="py-2 px-3 text-sm text-gray-600",
                                                ),
                                                rx.el.td(
                                                    rx.el.button(
                                                        rx.icon(
                                                            "trash-2",
                                                            class_name="h-4 w-4",
                                                        ),
                                                        on_click=lambda _,
                                                        temp_id=item[
                                                            "temp_id"
                                                        ]: State.remove_inventory_adjustment_item(
                                                            temp_id
                                                        ),
                                                        class_name="p-2 text-red-500 hover:bg-red-100 rounded-full",
                                                    ),
                                                    class_name="py-2 px-3 text-center",
                                                ),
                                                class_name="border-b",
                                            ),
                                        )
                                    ),
                                    class_name="w-full text-sm",
                                ),
                                class_name="mt-6 rounded-lg border overflow-x-auto",
                            ),
                            rx.el.p(
                                "Aun no hay productos seleccionados para el ajuste.",
                                class_name="mt-4 text-sm text-gray-500",
                            ),
                        ),
                        rx.el.div(
                            rx.el.label(
                                "Notas generales del ajuste",
                                class_name="text-sm font-semibold text-gray-700 mt-4",
                            ),
                            rx.el.textarea(
                                placeholder="Detalles adicionales que respalden el ajuste realizado.",
                                value=State.inventory_adjustment_notes,
                                on_change=lambda value: State.set_inventory_adjustment_notes(
                                    value
                                ),
                                class_name="w-full mt-2 p-3 border rounded-lg h-32",
                            ),
                        ),
                        class_name="mt-4 space-y-4",
                    ),
                    rx.fragment(),
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=State.close_inventory_check_modal,
                        class_name="px-4 py-2 rounded-md border text-gray-700 hover:bg-gray-50",
                    ),
                    rx.el.button(
                        rx.icon("save", class_name="h-4 w-4"),
                        "Guardar Registro",
                        on_click=State.submit_inventory_check,
                        class_name="flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700",
                    ),
                    class_name="flex flex-col gap-3 sm:flex-row sm:justify-end",
                ),
                class_name="relative z-10 w-full max-w-3xl rounded-xl bg-white p-4 sm:p-6 shadow-xl max-h-[90vh] overflow-y-auto space-y-4",
            ),
            class_name="fixed inset-0 z-50 flex items-start md:items-center justify-center px-4 py-6 overflow-hidden",
        ),
        rx.fragment(),
    )


def inventario_page() -> rx.Component:
    content = rx.el.div(
        rx.el.h1(
            "Inventario Actual", class_name="text-2xl font-bold text-gray-800 mb-6"
        ),
        rx.el.div(
            rx.el.h2(
                "Categorías",
                class_name="text-lg font-semibold text-gray-700 mb-4",
            ),
            rx.el.div(
                rx.el.input(
                    placeholder="Nombre de la categoría",
                    value=State.new_category_name,
                    on_change=lambda value: State.update_new_category_name(value),
                    class_name="flex-1 p-2 border rounded-md",
                ),
                rx.el.button(
                    rx.icon("plus", class_name="h-4 w-4"),
                    "Agregar",
                    on_click=State.add_category,
                    class_name="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 min-h-[42px]",
                ),
                class_name="flex flex-wrap gap-3 mb-4",
            ),
            rx.el.div(
                rx.foreach(
                    State.categories,
                    lambda category: rx.el.div(
                        rx.el.span(category, class_name="font-medium"),
                        rx.cond(
                            category == "General",
                            rx.fragment(),
                            rx.el.button(
                                rx.icon("x", class_name="h-3 w-3"),
                                on_click=lambda category=category: State.remove_category(
                                    category
                                ),
                                class_name="text-red-500 hover:text-red-700",
                            ),
                        ),
                        class_name="flex items-center gap-2 bg-gray-100 px-3 py-1 rounded-full",
                    ),
                ),
                class_name="flex flex-wrap gap-2",
            ),
            class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md mb-6",
        ),
        rx.el.div(
            rx.el.input(
                placeholder="Buscar producto...",
                on_change=State.set_inventory_search_term,
                class_name="w-full p-2 border rounded-md",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("download", class_name="h-4 w-4"),
                    "Exportar Inventario",
                    on_click=State.export_inventory_to_excel,
                    class_name="flex items-center justify-center gap-2 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 min-h-[42px]",
                ),
                rx.el.button(
                    rx.icon("clipboard_check", class_name="h-4 w-4"),
                    "Registrar Inventario Fisico",
                    on_click=State.open_inventory_check_modal,
                    class_name="flex items-center justify-center gap-2 bg-amber-600 text-white px-4 py-2 rounded-md hover:bg-amber-700 min-h-[42px]",
                ),
                class_name="flex flex-col gap-2 w-full md:w-auto md:flex-row",
            ),
            class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("Codigo de Barra", class_name="py-3 px-4 text-left"),
                        rx.el.th("Descripción", class_name="py-3 px-4 text-left"),
                        rx.el.th("Categoría", class_name="py-3 px-4 text-left"),
                        rx.el.th("Stock", class_name="py-3 px-4 text-center"),
                        rx.el.th("Unidad", class_name="py-3 px-4 text-center"),
                        rx.el.th("Precio Compra", class_name="py-3 px-4 text-right"),
                        rx.el.th(
                            "Precio Venta", class_name="py-3 px-4 text-right"
                        ),
                        rx.el.th(
                            "Valor Total Stock", class_name="py-3 px-4 text-right"
                        ),
                        rx.el.th("Acciones", class_name="py-3 px-4 text-center"),
                        class_name="bg-gray-100",
                    )
                ),
                rx.el.tbody(
                    rx.foreach(
                        State.inventory_paginated_list,
                        lambda product: rx.el.tr(
                            rx.el.td(
                                product["barcode"],
                                class_name="py-3 px-4",
                            ),
                            rx.el.td(
                                product["description"],
                                class_name="py-3 px-4 font-medium",
                            ),
                            rx.el.td(
                                product["category"],
                                class_name="py-3 px-4 text-left",
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
                                State.currency_symbol,
                                product["purchase_price"].to_string(),
                                class_name="py-3 px-4 text-right",
                            ),
                            rx.el.td(
                                State.currency_symbol,
                                product["sale_price"].to_string(),
                                class_name="py-3 px-4 text-right text-green-600",
                            ),
                            rx.el.td(
                                State.currency_symbol,
                                f"{product['stock'] * product['purchase_price']:.2f}",
                                class_name="py-3 px-4 text-right font-bold",
                            ),
                            rx.el.td(
                                rx.el.div(
                                    rx.el.button(
                                        rx.icon("pencil", class_name="h-4 w-4"),
                                        on_click=lambda: State.open_edit_product(product),
                                        class_name="p-2 text-blue-600 hover:bg-blue-50 rounded-full",
                                        title="Editar",
                                    ),
                                    rx.el.button(
                                        rx.icon("trash-2", class_name="h-4 w-4"),
                                        on_click=lambda: State.delete_product(product["id"]),
                                        class_name="p-2 text-red-600 hover:bg-red-50 rounded-full",
                                        title="Eliminar",
                                    ),
                                    class_name="flex items-center justify-center gap-2",
                                ),
                                class_name="py-3 px-4",
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
            rx.cond(
                State.inventory_total_pages > 1,
                pagination_controls(
                    current_page=State.inventory_display_page,
                    total_pages=State.inventory_total_pages,
                    on_prev=lambda: State.set_inventory_page(State.inventory_display_page - 1),
                    on_next=lambda: State.set_inventory_page(State.inventory_display_page + 1),
                ),
                rx.fragment(),
            ),
            class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md overflow-x-auto flex flex-col gap-4",
        ),
        inventory_adjustment_modal(),
        edit_product_modal(),
        class_name="p-4 sm:p-6 w-full max-w-7xl mx-auto flex flex-col gap-6",
    )
    return permission_guard(
        has_permission=State.can_view_inventario,
        content=content,
        redirect_message="Acceso denegado a Inventario",
    )
