import reflex as rx
from app.state import State
from app.components.ui import TABLE_STYLES, page_title, permission_guard


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
                    disabled=item.get("is_existing_product", False),
                    class_name="w-40 h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
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
        class_name="border-b border-slate-100 hover:bg-slate-50/80",
    )


def ingreso_page() -> rx.Component:
    purchase_header = rx.el.div(
        rx.el.h2(
            "DATOS DEL DOCUMENTO DE COMPRA",
            class_name="text-lg font-semibold text-slate-700",
        ),
        rx.el.p(
            "Completa la información básica del documento y selecciona el proveedor.",
            class_name="text-sm text-slate-500",
        ),
        class_name="flex flex-col gap-1 pb-4 mb-4 border-b border-slate-100",
    )

    purchase_fields = rx.el.div(
        rx.el.div(
            rx.el.label(
                "Buscar Proveedor",
                class_name="block text-sm font-medium text-slate-600 mb-1",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.input(
                        placeholder="Buscar por Nombre de Empresa o N° de Registro",
                        on_change=State.search_supplier_change,
                        value=State.purchase_supplier_query,
                        class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                        debounce_timeout=200,
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
                                            class_name="font-medium text-slate-800",
                                        ),
                                        rx.el.span(
                                            supplier["tax_id"],
                                            class_name="text-xs text-slate-500",
                                        ),
                                        class_name="flex flex-col text-left",
                                    ),
                                    on_click=lambda _,
                                    supplier=supplier: State.select_supplier(
                                        supplier
                                    ),
                                    class_name="w-full text-left p-2 hover:bg-slate-100",
                                ),
                            ),
                            class_name="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-60 overflow-y-auto",
                        ),
                        rx.fragment(),
                    ),
                    class_name="relative flex-1",
                ),
                rx.el.button(
                    "Limpiar Proveedor",
                    on_click=State.clear_supplier_search,
                    class_name="h-10 px-3 rounded-md border border-slate-200 bg-white text-slate-600 text-sm hover:bg-slate-50 w-full sm:w-auto",
                ),
                class_name="flex flex-col sm:flex-row gap-2 items-stretch sm:items-center",
            ),
            rx.el.p(
                "Si no existe el proveedor, gestionelo en Compras > Proveedores.",
                class_name="text-xs text-slate-500 mt-2",
            ),
            class_name="w-full sm:col-span-2 lg:col-span-4 relative",
        ),
        rx.el.div(
            rx.el.label(
                "Razón Social",
                class_name="block text-sm font-medium text-slate-600 mb-1",
            ),
            rx.el.input(
                value=rx.cond(
                    State.selected_supplier != None,
                    State.selected_supplier["name"],
                    "",
                ),
                placeholder="Razón Social / Nombre de Empresa",
                read_only=True,
                class_name="w-full h-10 px-3 text-sm bg-slate-50 border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            ),
            class_name="w-full",
        ),
        rx.el.div(
            rx.el.label(
                "N° Registro",
                class_name="block text-sm font-medium text-slate-600 mb-1",
            ),
            rx.el.input(
                value=rx.cond(
                    State.selected_supplier != None,
                    State.selected_supplier["tax_id"],
                    "",
                ),
                placeholder="N° de Registro de Empresa",
                read_only=True,
                class_name="w-full h-10 px-3 text-sm bg-slate-50 border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 font-mono",
            ),
            class_name="w-full",
        ),
        rx.el.div(
            rx.el.label(
                "Tipo de Documento",
                class_name="block text-sm font-medium text-slate-600 mb-1",
            ),
            rx.el.select(
                rx.el.option("Boleta", value="boleta"),
                rx.el.option("Factura", value="factura"),
                value=State.purchase_doc_type,
                on_change=State.set_purchase_doc_type,
                class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            ),
            class_name="w-full",
        ),
        rx.el.div(
            rx.el.label(
                "Serie",
                class_name="block text-sm font-medium text-slate-600 mb-1",
            ),
            rx.el.input(
                placeholder="Ej: F001",
                on_change=State.set_purchase_series,
                value=State.purchase_series,
                class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                debounce_timeout=200,
            ),
            class_name="w-full",
        ),
        rx.el.div(
            rx.el.label(
                "Numero",
                class_name="block text-sm font-medium text-slate-600 mb-1",
            ),
            rx.el.input(
                placeholder="Ej: 000123",
                on_change=State.set_purchase_number,
                value=State.purchase_number,
                class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                debounce_timeout=200,
            ),
            class_name="w-full",
        ),
        rx.el.div(
            rx.el.label(
                "Fecha de Emision",
                class_name="block text-sm font-medium text-slate-600 mb-1",
            ),
            rx.el.input(
                type="date",
                on_change=State.set_purchase_issue_date,
                value=State.purchase_issue_date,
                class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            ),
            class_name="w-full",
        ),
        class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end",
    )

    purchase_grid = rx.el.div(
        purchase_fields,
        class_name="w-full",
    )

    variant_existing_inputs = rx.el.div(
        rx.el.label(
            "Talla/Color",
            class_name="block text-sm font-medium text-slate-600 mb-1",
        ),
        rx.el.select(
            rx.el.option("Seleccionar Talla/Color", value=""),
            rx.foreach(
                State.variants_list,
                lambda variant: rx.el.option(
                    variant["label"], value=variant["id"]
                ),
            ),
            value=State.selected_variant_id,
            on_change=State.set_selected_variant,
            class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
        ),
        class_name="w-full",
    )

    variant_new_inputs = rx.el.div(
        rx.el.div(
            rx.el.label(
                "Talla",
                class_name="block text-sm font-medium text-slate-600 mb-1",
            ),
            rx.el.input(
                placeholder="Ej: 40",
                on_change=State.set_variant_size,
                value=State.variant_size,
                class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            ),
            class_name="w-full",
        ),
        rx.el.div(
            rx.el.label(
                "Color",
                class_name="block text-sm font-medium text-slate-600 mb-1",
            ),
            rx.el.input(
                placeholder="Ej: Negro",
                on_change=State.set_variant_color,
                value=State.variant_color,
                class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            ),
            class_name="w-full",
        ),
        class_name="grid grid-cols-1 sm:grid-cols-2 gap-2 items-end w-full",
    )

    batch_quantity_inputs = rx.el.div(
        rx.el.div(
            rx.el.label(
                "Nro Lote",
                class_name="block text-sm font-medium text-slate-600 mb-1",
            ),
            rx.el.input(
                placeholder="Ej: L123",
                on_change=State.set_batch_code,
                value=State.batch_code,
                class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            ),
            class_name="w-full",
        ),
        rx.el.div(
            rx.el.label(
                "Vencimiento",
                class_name="block text-sm font-medium text-slate-600 mb-1",
            ),
            rx.el.input(
                type="date",
                on_change=State.set_batch_date,
                value=State.batch_date,
                class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            ),
            class_name="w-full",
        ),
        class_name="grid grid-cols-1 sm:grid-cols-2 gap-2 items-end w-full",
    )

    quantity_field = rx.el.div(
        rx.el.label(
            "Cantidad",
            class_name="block text-sm font-medium text-slate-600 mb-1",
        ),
        rx.el.input(
            type="number",
            on_change=lambda val: State.handle_entry_change("quantity", val),
            class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            value=State.new_entry_item["quantity"].to_string(),
        ),
        class_name="w-full",
    )

    quantity_inputs = rx.cond(
        State.has_variants,
        rx.cond(State.is_existing_product, variant_existing_inputs, variant_new_inputs),
        rx.cond(State.requires_batches, batch_quantity_inputs, rx.fragment()),
    )

    entry_mode_selector = rx.cond(
        State.is_existing_product,
        rx.fragment(),
        rx.el.div(
            rx.el.label(
                "Tipo",
                class_name="block text-sm font-medium text-slate-600 mb-1",
            ),
            rx.el.select(
                rx.el.option("Estándar", value="standard"),
                rx.el.option("Variantes", value="variant"),
                rx.el.option("Lotes", value="batch"),
                value=State.entry_mode,
                on_change=State.set_entry_mode,
                class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            ),
            class_name="w-full",
        ),
    )

    entry_item_form = rx.el.div(
        rx.el.h2(
            "AÑADIR PRODUCTOS", class_name="text-lg font-semibold text-slate-700 mb-4"
        ),
        rx.el.div(
            rx.el.div(
                rx.el.label(
                    "Codigo de Barra",
                    class_name="block text-sm font-medium text-slate-600 mb-1",
                ),
                rx.el.input(
                    id="barcode-input-entry",
                    key=State.entry_form_key.to_string(),
                    default_value=State.new_entry_item["barcode"],
                    placeholder="Ej: 7791234567890",
                    on_blur=lambda e: State.process_entry_barcode_from_input(e),
                    on_key_down=lambda k: State.handle_barcode_enter(
                        k, "barcode-input-entry"
                    ),
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                    type="text",
                    auto_complete="off",
                ),
                class_name="col-span-12 sm:col-span-4 lg:col-span-3",
            ),
            rx.el.div(
                rx.el.label(
                    "Descripción",
                    class_name="block text-sm font-medium text-slate-600 mb-1",
                ),
                rx.debounce_input(
                    rx.input(
                        value=State.new_entry_item["description"],
                        on_change=lambda val: State.handle_entry_change(
                            "description", val
                        ),
                        placeholder="Descripción del producto",
                        class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                        is_read_only=State.is_existing_product,
                    ),
                    debounce_timeout=200,
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
                                class_name="w-full text-left p-2 hover:bg-slate-100",
                            ),
                        ),
                        class_name="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-60 overflow-y-auto",
                    ),
                    rx.fragment(),
                ),
                class_name="col-span-12 sm:col-span-8 lg:col-span-3 relative",
            ),
            rx.el.div(
                entry_mode_selector,
                class_name="col-span-12 sm:col-span-4 lg:col-span-2",
            ),
            rx.el.div(
                quantity_inputs,
                class_name="col-span-12 sm:col-span-8 lg:col-span-4",
            ),
            class_name="grid grid-cols-12 gap-4 items-end",
        ),
        rx.el.div(
            rx.el.div(
                quantity_field,
                class_name="col-span-6 sm:col-span-2 lg:col-span-2",
            ),
            rx.el.div(
                rx.el.label(
                    "Unidad",
                    class_name="block text-sm font-medium text-slate-600 mb-1",
                ),
                rx.el.select(
                    rx.foreach(
                        State.units, lambda unit: rx.el.option(unit, value=unit)
                    ),
                    value=State.new_entry_item["unit"],
                    on_change=lambda val: State.handle_entry_change("unit", val),
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                ),
                class_name="col-span-6 sm:col-span-2 lg:col-span-2",
            ),
            rx.el.div(
                rx.el.label(
                    "Precio Compra",
                    class_name="block text-sm font-medium text-slate-600 mb-1",
                ),
                rx.el.input(
                    type="number",
                    on_change=lambda val: State.handle_entry_change("price", val),
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                    value=State.new_entry_item["price"].to_string(),
                ),
                class_name="col-span-6 sm:col-span-2 lg:col-span-2",
            ),
            rx.el.div(
                rx.el.label(
                    "Precio Venta",
                    class_name="block text-sm font-medium text-slate-600 mb-1",
                ),
                rx.el.input(
                    type="number",
                    on_change=lambda val: State.handle_entry_change("sale_price", val),
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                    value=State.new_entry_item["sale_price"].to_string(),
                ),
                class_name="col-span-6 sm:col-span-2 lg:col-span-2",
            ),
            rx.el.div(
                rx.el.label(
                    "Subtotal",
                    class_name="block text-sm font-medium text-slate-600 mb-1",
                ),
                rx.el.div(
                    State.currency_symbol,
                    State.entry_subtotal.to_string(),
                    class_name="w-full h-10 px-3 text-sm bg-slate-50 border border-slate-200 rounded-md text-right font-semibold flex items-center justify-end",
                ),
                class_name="col-span-6 sm:col-span-2 lg:col-span-2",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("plus", class_name="h-5 w-5"),
                    "Añadir",
                    on_click=State.add_item_to_entry,
                    class_name="flex items-center justify-center gap-2 h-10 px-4 rounded-md bg-indigo-600 text-white font-medium hover:bg-indigo-700",
                ),
                class_name="col-span-12 sm:col-span-4 lg:col-span-2 flex items-end",
            ),
            class_name="grid grid-cols-12 gap-4 items-end mt-4",
        ),
        class_name="mt-3 pt-3 border-t border-slate-100",
    )

    purchase_card = rx.el.div(
        purchase_header,
        purchase_grid,
        entry_item_form,
        class_name="bg-white p-4 sm:p-6 rounded-xl border border-slate-200 shadow-sm",
    )

    content = rx.el.div(
        page_title(
            "INGRESO DE PRODUCTOS",
            "Registra la entrada de nuevos productos al almacen para aumentar el stock disponible.",
        ),
        purchase_card,
        rx.el.div(
            rx.el.h2(
                "PRODUCTOS A INGRESAR",
                class_name="text-lg font-semibold text-slate-700 mb-4",
            ),
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th(
                                "Codigo de Barra", class_name=TABLE_STYLES["header_cell"]
                            ),
                            rx.el.th(
                                "Descripción", class_name=TABLE_STYLES["header_cell"]
                            ),
                            rx.el.th(
                                "Categoría", class_name=TABLE_STYLES["header_cell"]
                            ),
                            rx.el.th(
                                "Cantidad",
                                class_name=f"{TABLE_STYLES['header_cell']} text-center",
                            ),
                            rx.el.th(
                                "Unidad",
                                class_name=f"{TABLE_STYLES['header_cell']} text-center",
                            ),
                            rx.el.th(
                                "P. Compra",
                                class_name=f"{TABLE_STYLES['header_cell']} text-right",
                            ),
                            rx.el.th(
                                "P. Venta",
                                class_name=f"{TABLE_STYLES['header_cell']} text-right",
                            ),
                            rx.el.th(
                                "Subtotal",
                                class_name=f"{TABLE_STYLES['header_cell']} text-right",
                            ),
                            rx.el.th(
                                "Acción",
                                class_name=f"{TABLE_STYLES['header_cell']} text-center",
                            ),
                        ),
                        class_name=TABLE_STYLES["header"],
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
                    class_name="text-slate-500 text-center py-8",
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
                    class_name="w-full sm:w-auto bg-green-600 text-white h-10 px-5 rounded-md hover:bg-green-700 font-medium",
                ),
                class_name="pt-4 mt-4 border-t border-slate-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4",
            ),
            class_name="bg-white p-4 sm:p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-4",
        ),
        class_name="p-4 sm:p-6 w-full flex flex-col gap-4",
    )

    return permission_guard(
        has_permission=State.can_view_ingresos,
        content=content,
        redirect_message="Acceso denegado a Ingresos",
    )
