import reflex as rx
from app.state import State
from app.components.ui import page_title, permission_guard, modal_container, pagination_controls


def purchase_row(purchase: rx.Var[dict]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(purchase["issue_date"], class_name="py-3 px-4"),
        rx.el.td(purchase["doc_label"], class_name="py-3 px-4"),
        rx.el.td(
            rx.el.div(
                rx.el.span(purchase["supplier_name"], class_name="font-medium"),
                rx.el.span(purchase["supplier_tax_id"], class_name="text-xs text-gray-500"),
                class_name="flex flex-col",
            ),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.el.div(
                State.currency_symbol,
                purchase["total_amount"].to_string(),
                class_name="text-right font-semibold",
            ),
            rx.el.div(
                purchase["currency_code"],
                class_name="text-xs text-gray-400 text-right",
            ),
            class_name="py-3 px-4 text-right",
        ),
        rx.el.td(purchase["user"], class_name="py-3 px-4"),
        rx.el.td(purchase["items_count"].to_string(), class_name="py-3 px-4 text-center"),
        rx.el.td(
            rx.el.button(
                rx.icon("eye", class_name="h-4 w-4"),
                "Detalle",
                on_click=lambda _: State.open_purchase_detail(purchase["id"]),
                class_name="px-3 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700",
            ),
            class_name="py-3 px-4 text-center",
        ),
        class_name="border-b",
    )


def supplier_row(supplier: rx.Var[dict]) -> rx.Component:
    actions = rx.el.div(
        rx.el.button(
            rx.icon("pencil", class_name="h-4 w-4"),
            on_click=lambda _: State.open_supplier_modal(supplier),
            class_name="p-2 text-blue-500 hover:bg-blue-100 rounded-full",
        ),
        rx.el.button(
            rx.icon("trash-2", class_name="h-4 w-4"),
            on_click=lambda _: State.delete_supplier(supplier["id"]),
            class_name="p-2 text-red-500 hover:bg-red-100 rounded-full",
        ),
        class_name="flex items-center justify-center gap-2",
    )
    readonly = rx.el.span(
        "Solo lectura",
        class_name="text-xs text-gray-400",
    )
    return rx.el.tr(
        rx.el.td(supplier["name"], class_name="py-3 px-4"),
        rx.el.td(supplier["tax_id"], class_name="py-3 px-4"),
        rx.el.td(
            rx.cond(supplier["phone"] != "", supplier["phone"], "-"),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.cond(supplier["email"] != "", supplier["email"], "-"),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.cond(supplier["address"] != "", supplier["address"], "-"),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.cond(
                State.can_manage_proveedores,
                actions,
                readonly,
            ),
            class_name="py-3 px-4 text-center",
        ),
        class_name="border-b",
    )


def purchase_detail_modal() -> rx.Component:
    return modal_container(
        is_open=State.purchase_detail_modal_open,
        on_close=State.close_purchase_detail,
        title="Detalle de Compra",
        description="Resumen del documento y productos ingresados.",
        children=[
            rx.cond(
                State.purchase_detail != None,
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.el.p("Documento", class_name="text-xs text-gray-500"),
                            rx.el.p(
                                State.purchase_detail["doc_label"],
                                class_name="font-semibold",
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                        rx.el.div(
                            rx.el.p("Fecha", class_name="text-xs text-gray-500"),
                            rx.el.p(State.purchase_detail["issue_date"], class_name="font-semibold"),
                            class_name="flex flex-col gap-1",
                        ),
                        rx.el.div(
                            rx.el.p("Proveedor", class_name="text-xs text-gray-500"),
                            rx.el.p(
                                State.purchase_detail["supplier_name"],
                                class_name="font-semibold",
                            ),
                            rx.el.p(
                                State.purchase_detail["supplier_tax_id"],
                                class_name="text-xs text-gray-500",
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                        rx.el.div(
                            rx.el.p("Total", class_name="text-xs text-gray-500"),
                            rx.el.p(
                                State.currency_symbol,
                                State.purchase_detail["total_amount"].to_string(),
                                class_name="font-semibold",
                            ),
                            rx.el.p(
                                State.purchase_detail["currency_code"],
                                class_name="text-xs text-gray-500",
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                        class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
                    ),
                        rx.el.div(
                            rx.el.p("Notas", class_name="text-xs text-gray-500"),
                            rx.cond(
                                State.purchase_detail["notes"] != "",
                                rx.el.p(
                                    State.purchase_detail["notes"],
                                    class_name="text-sm text-gray-700",
                                ),
                                rx.el.p(
                                    "Sin observaciones",
                                    class_name="text-sm text-gray-700",
                                ),
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                    rx.el.div(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    rx.el.th("Producto", class_name="py-2 px-4 text-left"),
                                    rx.el.th("Cantidad", class_name="py-2 px-4 text-center"),
                                    rx.el.th("Costo Unit.", class_name="py-2 px-4 text-right"),
                                    rx.el.th("Subtotal", class_name="py-2 px-4 text-right"),
                                    class_name="bg-gray-100",
                                )
                            ),
                            rx.el.tbody(
                                rx.foreach(
                                    State.purchase_detail_items,
                                    lambda item: rx.el.tr(
                                        rx.el.td(
                                            rx.el.div(
                                                rx.el.span(item["description"], class_name="font-medium"),
                                                rx.el.span(
                                                    item["barcode"],
                                                    class_name="text-xs text-gray-500",
                                                ),
                                                class_name="flex flex-col",
                                            ),
                                            class_name="py-3 px-4",
                                        ),
                                        rx.el.td(
                                            item["quantity"].to_string(),
                                            class_name="py-3 px-4 text-center",
                                        ),
                                        rx.el.td(
                                            State.currency_symbol,
                                            item["unit_cost"].to_string(),
                                            class_name="py-3 px-4 text-right",
                                        ),
                                        rx.el.td(
                                            State.currency_symbol,
                                            item["subtotal"].to_string(),
                                            class_name="py-3 px-4 text-right font-semibold",
                                        ),
                                        class_name="border-b",
                                    ),
                                )
                            ),
                        ),
                        class_name="overflow-x-auto border rounded-lg",
                    ),
                    class_name="flex flex-col gap-4",
                ),
                rx.fragment(),
            )
        ],
        footer=rx.el.div(
            rx.el.button(
                "Cerrar",
                on_click=State.close_purchase_detail,
                class_name="px-4 py-2 border rounded-md text-gray-600 hover:bg-gray-100",
            ),
            class_name="flex justify-end",
        ),
        max_width="max-w-4xl",
    )


def supplier_modal() -> rx.Component:
    return modal_container(
        is_open=State.supplier_modal_open,
        on_close=State.close_supplier_modal,
        title="Proveedor",
        description="Registrar o editar proveedor.",
        children=[
            rx.el.div(
                rx.el.label("Nombre", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    value=State.current_supplier["name"],
                    on_change=lambda val: State.update_current_supplier("name", val),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("RUC/CUIT", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    value=State.current_supplier["tax_id"],
                    on_change=lambda val: State.update_current_supplier("tax_id", val),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Telefono", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    value=State.current_supplier["phone"],
                    on_change=lambda val: State.update_current_supplier("phone", val),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Email", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    value=State.current_supplier["email"],
                    on_change=lambda val: State.update_current_supplier("email", val),
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Direccion", class_name="text-sm font-medium text-gray-700"),
                rx.el.textarea(
                    value=State.current_supplier["address"],
                    on_change=lambda val: State.update_current_supplier("address", val),
                    class_name="w-full p-2 border rounded-md min-h-[80px]",
                ),
                class_name="flex flex-col gap-1",
            ),
        ],
        footer=rx.el.div(
            rx.el.button(
                "Cancelar",
                on_click=State.close_supplier_modal,
                class_name="px-4 py-2 border rounded-md text-gray-600 hover:bg-gray-100",
            ),
            rx.el.button(
                "Guardar",
                on_click=State.save_supplier,
                class_name="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700",
            ),
            class_name="flex justify-end gap-2",
        ),
        max_width="max-w-lg",
    )


def compras_page() -> rx.Component:
    tab_button = "px-4 py-2 rounded-md text-sm font-semibold transition"
    registro_button = rx.el.button(
        "Registro de Compras",
        on_click=lambda _: State.set_purchases_tab("registro"),
        class_name=rx.cond(
            State.purchases_active_tab == "registro",
            f"{tab_button} bg-indigo-600 text-white",
            f"{tab_button} bg-white text-gray-600 border",
        ),
    )
    proveedores_button = rx.el.button(
        "Proveedores",
        on_click=lambda _: State.set_purchases_tab("proveedores"),
        class_name=rx.cond(
            State.purchases_active_tab == "proveedores",
            f"{tab_button} bg-indigo-600 text-white",
            f"{tab_button} bg-white text-gray-600 border",
        ),
    )

    registro_content = rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.label("Buscar", class_name="text-sm font-medium text-gray-600 mb-1"),
                rx.el.input(
                    placeholder="Documento, proveedor, RUC/CUIT",
                    value=State.purchase_search_term,
                    on_change=State.set_purchase_search_term,
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="w-full sm:w-64",
            ),
            rx.el.div(
                rx.el.label("Fecha inicio", class_name="text-sm font-medium text-gray-600 mb-1"),
                rx.el.input(
                    type="date",
                    value=State.purchase_start_date,
                    on_change=State.set_purchase_start_date,
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="w-full sm:w-48",
            ),
            rx.el.div(
                rx.el.label("Fecha fin", class_name="text-sm font-medium text-gray-600 mb-1"),
                rx.el.input(
                    type="date",
                    value=State.purchase_end_date,
                    on_change=State.set_purchase_end_date,
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="w-full sm:w-48",
            ),
            rx.el.button(
                "Limpiar",
                on_click=State.reset_purchase_filters,
                class_name="px-4 py-2 border rounded-md text-gray-600 hover:bg-gray-100 mt-6",
            ),
            class_name="flex flex-wrap items-end gap-4",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("Fecha", class_name="py-2 px-4 text-left"),
                        rx.el.th("Documento", class_name="py-2 px-4 text-left"),
                        rx.el.th("Proveedor", class_name="py-2 px-4 text-left"),
                        rx.el.th("Total", class_name="py-2 px-4 text-right"),
                        rx.el.th("Usuario", class_name="py-2 px-4 text-left"),
                        rx.el.th("Items", class_name="py-2 px-4 text-center"),
                        rx.el.th("Accion", class_name="py-2 px-4 text-center"),
                    ),
                    class_name="bg-gray-100",
                ),
                rx.el.tbody(rx.foreach(State.purchase_records, purchase_row)),
            ),
            class_name="overflow-x-auto",
        ),
        rx.cond(
            State.purchase_records.length() == 0,
            rx.el.p(
                "No hay compras registradas.",
                class_name="text-gray-500 text-center py-8",
            ),
            rx.fragment(),
        ),
        pagination_controls(
            current_page=State.purchase_current_page,
            total_pages=State.purchase_total_pages,
            on_prev=State.prev_purchase_page,
            on_next=State.next_purchase_page,
        ),
        class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md flex flex-col gap-4",
    )

    proveedores_content = rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.label("Buscar proveedor", class_name="text-sm font-medium text-gray-600 mb-1"),
                rx.el.input(
                    placeholder="Nombre, RUC/CUIT, telefono",
                    value=State.supplier_search_query,
                    on_change=State.set_supplier_search_query,
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="w-full sm:w-64",
            ),
            rx.cond(
                State.can_manage_proveedores,
                rx.el.button(
                    rx.icon("plus", class_name="h-4 w-4"),
                    "Nuevo proveedor",
                    on_click=lambda _: State.open_supplier_modal(None),
                    class_name="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700",
                ),
                rx.el.span(
                    "Solo lectura",
                    class_name="text-xs text-gray-400",
                ),
            ),
            class_name="flex flex-wrap items-end justify-between gap-4",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("Proveedor", class_name="py-2 px-4 text-left"),
                        rx.el.th("RUC/CUIT", class_name="py-2 px-4 text-left"),
                        rx.el.th("Telefono", class_name="py-2 px-4 text-left"),
                        rx.el.th("Email", class_name="py-2 px-4 text-left"),
                        rx.el.th("Direccion", class_name="py-2 px-4 text-left"),
                        rx.el.th("Accion", class_name="py-2 px-4 text-center"),
                    ),
                    class_name="bg-gray-100",
                ),
                rx.el.tbody(rx.foreach(State.suppliers_view, supplier_row)),
            ),
            class_name="overflow-x-auto",
        ),
        rx.cond(
            State.suppliers_view.length() == 0,
            rx.el.p(
                "No hay proveedores registrados.",
                class_name="text-gray-500 text-center py-8",
            ),
            rx.fragment(),
        ),
        class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md flex flex-col gap-4",
    )

    content = rx.el.div(
        page_title(
            "Registro de Compras",
            "Consulta documentos de compra y gestiona proveedores.",
        ),
        rx.el.div(
            registro_button,
            proveedores_button,
            class_name="flex flex-wrap gap-2 mb-4",
        ),
        rx.cond(
            State.purchases_active_tab == "registro",
            registro_content,
            proveedores_content,
        ),
        purchase_detail_modal(),
        supplier_modal(),
        class_name="p-4 sm:p-6 w-full max-w-7xl mx-auto flex flex-col gap-6",
    )

    return permission_guard(
        has_permission=State.can_view_compras,
        content=content,
        redirect_message="Acceso denegado a Compras",
    )
