import reflex as rx
from app.state import State
from app.components.ui import page_title, permission_guard


def item_entry_row(item: rx.Var[dict]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(item["barcode"], class_name="py-3 px-4"),
        rx.el.td(item["description"], class_name="py-3 px-4"),
        rx.el.td(item.get("category", "General"), class_name="py-3 px-4"),
        rx.el.td(item["quantity"].to_string(), class_name="py-3 px-4 text-center"),
        rx.el.td(item["unit"], class_name="py-3 px-4 text-center"),
        rx.el.td(
            State.currency_symbol,
            item["price"].to_string(),
            class_name="py-3 px-4 text-right",
        ),
        rx.el.td(
            State.currency_symbol,
            item["sale_price"].to_string(),
            class_name="py-3 px-4 text-right text-green-600",
        ),
        rx.el.td(
            State.currency_symbol,
            item["subtotal"].to_string(),
            class_name="py-3 px-4 text-right font-semibold",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.select(
                    rx.foreach(
                        State.categories,
                        lambda category: rx.el.option(category, value=category),
                    ),
                    value=item.get("category", "General"),
                    on_change=lambda value, temp_id=item["temp_id"]: State.update_entry_item_category(
                        temp_id, value
                    ),
                    class_name="w-40 p-2 border rounded-md",
                ),
                rx.el.button(
                    rx.icon("pencil", class_name="h-4 w-4"),
                    on_click=lambda: State.edit_item_from_entry(item["temp_id"]),
                    class_name="p-2 text-blue-500 hover:bg-blue-100 rounded-full",
                ),
                rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda: State.remove_item_from_entry(item["temp_id"]),
                    class_name="p-2 text-red-500 hover:bg-red-100 rounded-full",
                ),
                class_name="flex justify-center items-center gap-2",
            ),
            class_name="py-3 px-4 text-center",
        ),
        class_name="border-b",
    )


def ingreso_page() -> rx.Component:
    purchase_header = rx.el.div(
        rx.el.h2(
            "Datos del Documento de Compra",
            class_name="text-lg font-semibold text-gray-700",
        ),
        rx.el.p(
            "Completa la información básica del documento y selecciona el proveedor.",
            class_name="text-sm text-gray-500",
        ),
        class_name="flex flex-col gap-1 mb-4",
    )

    purchase_fields = rx.el.div(
        rx.el.div(
            rx.el.label(
                "Tipo de Documento",
                class_name="block text-sm font-medium text-gray-600 mb-1",
            ),
            rx.el.select(
                rx.el.option("Boleta", value="boleta"),
                rx.el.option("Factura", value="factura"),
                value=State.purchase_doc_type,
                on_change=State.set_purchase_doc_type,
                class_name="w-full p-2 border rounded-md bg-white",
            ),
            class_name="w-full",
        ),
        rx.el.div(
            rx.el.label(
                "Serie",
                class_name="block text-sm font-medium text-gray-600 mb-1",
            ),
            rx.el.input(
                placeholder="Ej: F001",
                on_change=State.set_purchase_series,
                value=State.purchase_series,
                class_name="w-full p-2 border rounded-md",
            ),
            class_name="w-full",
        ),
        rx.el.div(
            rx.el.label(
                "Numero",
                class_name="block text-sm font-medium text-gray-600 mb-1",
            ),
            rx.el.input(
                placeholder="Ej: 000123",
                on_change=State.set_purchase_number,
                value=State.purchase_number,
                class_name="w-full p-2 border rounded-md",
            ),
            class_name="w-full",
        ),
        rx.el.div(
            rx.el.label(
                "Fecha de Emision",
                class_name="block text-sm font-medium text-gray-600 mb-1",
            ),
            rx.el.input(
                type="date",
                on_change=State.set_purchase_issue_date,
                value=State.purchase_issue_date,
                class_name="w-full p-2 border rounded-md",
            ),
            class_name="w-full",
        ),
        class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
    )

    purchase_notes = rx.el.div(
        rx.el.label(
            "Notas (opcional)",
            class_name="block text-sm font-medium text-gray-600 mb-1",
        ),
        rx.el.textarea(
            placeholder="Observaciones del documento o compra",
            on_change=State.set_purchase_notes,
            value=State.purchase_notes,
            class_name="w-full p-2 border rounded-md min-h-[80px]",
        ),
        class_name="w-full",
    )

    purchase_left = rx.el.div(
        purchase_fields,
        purchase_notes,
        class_name="flex flex-col gap-4 lg:col-span-2",
    )

    purchase_supplier = rx.el.div(
        rx.el.label(
            "Proveedor",
            class_name="block text-sm font-medium text-gray-600",
        ),
        rx.el.input(
            placeholder="Buscar por nombre o RUC/CUIT",
            on_change=State.search_supplier_change,
            value=State.purchase_supplier_query,
            class_name="w-full p-2 border rounded-md",
        ),
        rx.cond(
            State.purchase_supplier_suggestions.length() > 0,
            rx.el.div(
                rx.foreach(
                    State.purchase_supplier_suggestions,
                    lambda supplier: rx.el.button(
                        rx.el.div(
                            rx.el.span(
                                supplier["name"],
                                class_name="font-medium text-gray-800",
                            ),
                            rx.el.span(
                                supplier["tax_id"],
                                class_name="text-xs text-gray-500",
                            ),
                            class_name="flex flex-col text-left",
                        ),
                        on_click=lambda _,
                        supplier=supplier: State.select_supplier(
                            supplier
                        ),
                        class_name="w-full text-left p-2 hover:bg-gray-100",
                    ),
                ),
                class_name="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-60 overflow-y-auto",
            ),
            rx.fragment(),
        ),
        rx.cond(
            State.selected_supplier != None,
            rx.el.div(
                rx.el.div(
                    rx.el.span(
                        State.selected_supplier["name"],
                        class_name="font-medium text-gray-800",
                    ),
                    rx.el.span(
                        State.selected_supplier["tax_id"],
                        class_name="text-xs text-gray-500",
                    ),
                    class_name="flex flex-col",
                ),
                rx.el.button(
                    rx.icon("x", class_name="h-4 w-4"),
                    on_click=State.clear_selected_supplier,
                    class_name="p-1 text-gray-500 hover:text-gray-800",
                ),
                class_name="flex items-center justify-between rounded-md border border-gray-200 bg-white p-2",
            ),
            rx.fragment(),
        ),
        rx.el.p(
            "Si no existe el proveedor, gestionelo en Compras > Proveedores.",
            class_name="text-xs text-gray-500",
        ),
        class_name="flex flex-col gap-2 bg-gray-50 border border-gray-200 rounded-lg p-4 relative",
    )

    purchase_grid = rx.el.div(
        purchase_left,
        purchase_supplier,
        class_name="grid grid-cols-1 lg:grid-cols-3 gap-6",
    )

    entry_item_form = rx.el.div(
        rx.el.h2(
            "Añadir Producto", class_name="text-lg font-semibold text-gray-700 mb-4"
        ),
        rx.el.div(
            rx.el.div(
                rx.el.label(
                    "Codigo de Barra",
                    class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.input(
                        id="barcode-input-entry",
                        key=State.entry_form_key.to_string(),
                        default_value=State.new_entry_item["barcode"],
                        placeholder="Ej: 7791234567890",
                        on_blur=lambda e: State.process_entry_barcode_from_input(e),
                        on_key_down=lambda k: State.handle_barcode_enter(k, "barcode-input-entry"),
                        class_name="w-full p-2 border rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500",
                        type="text",
                        auto_complete="off",
                    ),
                    class_name="w-full sm:w-48",
                ),
                rx.el.div(
                    rx.el.label(
                        "Descripción",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.input(
                        placeholder="Ej: Coca-Cola 600ml",
                        on_change=lambda val: State.handle_entry_change(
                            "description", val
                        ),
                        class_name="w-full p-2 border rounded-md",
                        value=State.new_entry_item["description"],
                    ),
                    rx.cond(
                        State.entry_autocomplete_suggestions.length() > 0,
                        rx.el.div(
                            rx.foreach(
                                State.entry_autocomplete_suggestions,
                                lambda suggestion: rx.el.button(
                                    suggestion,
                                    on_click=lambda _,
                                    suggestion=suggestion: State.select_product_for_entry(
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
                        on_change=lambda val: State.handle_entry_change(
                            "quantity", val
                        ),
                        class_name="w-full p-2 border rounded-md",
                        value=State.new_entry_item["quantity"].to_string(),
                    ),
                    class_name="w-full sm:w-24",
                ),
                rx.el.div(
                    rx.el.label(
                        "Unidad",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.select(
                        rx.foreach(
                            State.units, lambda unit: rx.el.option(unit, value=unit)
                        ),
                        value=State.new_entry_item["unit"],
                        on_change=lambda val: State.handle_entry_change("unit", val),
                        class_name="w-full p-2 border rounded-md",
                    ),
                    class_name="w-full sm:w-32",
                ),
                rx.el.div(
                    rx.el.label(
                        "Precio Compra",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.input(
                        type="number",
                        on_change=lambda val: State.handle_entry_change("price", val),
                        class_name="w-full p-2 border rounded-md",
                        value=State.new_entry_item["price"].to_string(),
                    ),
                    class_name="w-full sm:w-32",
                ),
                rx.el.div(
                    rx.el.label(
                        "Precio Venta",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.input(
                        type="number",
                        on_change=lambda val: State.handle_entry_change(
                            "sale_price", val
                        ),
                        class_name="w-full p-2 border rounded-md",
                        value=State.new_entry_item["sale_price"].to_string(),
                    ),
                    class_name="w-full sm:w-32",
                ),
                rx.el.div(
                    rx.el.label(
                        "Subtotal",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.div(
                        State.currency_symbol,
                        State.entry_subtotal.to_string(),
                        class_name="w-full p-2 font-semibold text-right",
                    ),
                    class_name="w-full sm:w-32",
                ),
                rx.el.div(
                    rx.el.button(
                        rx.icon("plus", class_name="h-5 w-5"),
                        "Añadir",
                        on_click=State.add_item_to_entry,
                        class_name="flex items-center justify-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 mt-2 min-h-[44px]",
                    ),
                    class_name="w-full sm:w-auto flex items-center",
                ),
                class_name="flex flex-wrap items-start gap-4",
            ),
        class_name="mt-3 pt-3 border-t border-gray-100",
    )

    purchase_card = rx.el.div(
        purchase_header,
        purchase_grid,
        entry_item_form,
        class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md",
    )

    content = rx.el.div(
        page_title(
            "Ingreso de Productos",
            "Registra la entrada de nuevos productos al almacen para aumentar el stock disponible.",
        ),
        purchase_card,
        rx.el.div(
            rx.el.h2(
                "Productos a Ingresar",
                class_name="text-lg font-semibold text-gray-700 mb-4",
            ),
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th(
                                "Codigo de Barra", class_name="py-2 px-4 text-left"
                            ),
                            rx.el.th("Descripción", class_name="py-2 px-4 text-left"),
                            rx.el.th("Categoría", class_name="py-2 px-4 text-left"),
                            rx.el.th("Cantidad", class_name="py-2 px-4 text-center"),
                            rx.el.th("Unidad", class_name="py-2 px-4 text-center"),
                            rx.el.th("P. Compra", class_name="py-2 px-4 text-right"),
                            rx.el.th("P. Venta", class_name="py-2 px-4 text-right"),
                            rx.el.th("Subtotal", class_name="py-2 px-4 text-right"),
                            rx.el.th("Acción", class_name="py-2 px-4 text-center"),
                        ),
                        class_name="bg-gray-100",
                    ),
                    rx.el.tbody(rx.foreach(State.new_entry_items, item_entry_row)),
                    class_name="w-full",
                ),
                class_name="overflow-x-auto",
            ),
            rx.cond(
                State.new_entry_items.length() == 0,
                rx.el.p(
                    "Aún no has añadido productos.",
                    class_name="text-gray-500 text-center py-8",
                ),
                rx.fragment(),
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.span("Total General:", class_name="text-xl font-bold"),
                    rx.el.span(
                        State.currency_symbol,
                        State.entry_total.to_string(),
                        class_name="text-xl font-bold text-indigo-700",
                    ),
                    class_name="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-4",
                ),
                rx.el.button(
                    "Confirmar Ingreso",
                    on_click=State.confirm_entry,
                    class_name="w-full sm:w-auto bg-green-600 text-white px-5 py-3 rounded-lg hover:bg-green-700 font-semibold min-h-[44px]",
                ),
                class_name="pt-4 mt-4 border-t border-gray-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4",
            ),
            class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md flex flex-col gap-4",
        ),
        class_name="p-4 sm:p-6 w-full max-w-7xl mx-auto flex flex-col gap-4",
    )
    
    return permission_guard(
        has_permission=State.can_view_ingresos,
        content=content,
        redirect_message="Acceso denegado a Ingresos",
    )
