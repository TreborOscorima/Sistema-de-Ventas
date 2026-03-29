import reflex as rx
from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    INPUT_STYLES,
    TABLE_STYLES,
    action_button,
    modal_container,
    toggle_switch,
    permission_guard,
)
from app.pages.clientes import client_form_modal


def _fiscal_lookup_input() -> rx.Component:
    """Campo de consulta fiscal RUC/CUIT/DNI.

    Visible solo cuando billing está activo y el comprobante NO es nota_venta.
    Consulta la API fiscal (SUNAT/AFIP) y autocompleta datos del comprador.
    """
    return rx.cond(
        State.billing_is_active
        & (State.sale_receipt_type_selection != "nota_venta"),
        rx.el.div(
            # Input de consulta
            rx.el.div(
                rx.el.label(
                    rx.cond(
                        State.billing_country == "AR",
                        "CUIT del cliente",
                        rx.cond(
                            State.sale_receipt_type_selection == "factura",
                            "RUC del cliente",
                            "RUC / DNI del cliente",
                        ),
                    ),
                    class_name="text-xs font-medium text-slate-500",
                ),
                rx.el.div(
                    rx.el.input(
                        placeholder=rx.cond(
                            State.billing_country == "AR",
                            "Ej: 20345678901",
                            rx.cond(
                                State.sale_receipt_type_selection == "factura",
                                "Ej: 20123456789",
                                "8 o 11 dígitos",
                            ),
                        ),
                        value=State.fiscal_doc_number,
                        on_change=State.lookup_fiscal_document,
                        max_length=11,
                        class_name=(
                            "w-full text-sm px-3 py-1.5 border border-slate-200 "
                            "rounded-md focus:outline-none focus:ring-1 "
                            "focus:ring-indigo-400 focus:border-indigo-400"
                        ),
                    ),
                    # Spinner de carga
                    rx.cond(
                        State.fiscal_lookup_loading,
                        rx.el.div(
                            rx.spinner(size="1"),
                            class_name="absolute right-2 top-1/2 -translate-y-1/2",
                        ),
                        rx.fragment(),
                    ),
                    class_name="relative",
                ),
                class_name="flex flex-col gap-1",
            ),
            # Resultado exitoso
            rx.cond(
                State.fiscal_lookup_result.length() > 0,  # type: ignore[union-attr]
                rx.el.div(
                    rx.el.div(
                        rx.icon("circle-check", class_name="h-3.5 w-3.5 text-emerald-600 shrink-0 mt-0.5"),
                        rx.el.div(
                            rx.el.span(
                                State.fiscal_lookup_result["legal_name"],
                                class_name="text-xs font-semibold text-emerald-800 line-clamp-1",
                            ),
                            rx.el.span(
                                State.fiscal_lookup_result["fiscal_address"],
                                class_name="text-xs text-emerald-700 line-clamp-1",
                            ),
                            class_name="flex flex-col min-w-0",
                        ),
                        class_name="flex items-start gap-1.5",
                    ),
                    # Badge AR: tipo comprobante
                    rx.cond(
                        State.fiscal_ar_cbte_letra != "",
                        rx.el.div(
                            rx.el.span(
                                "Factura ",
                                rx.el.strong(State.fiscal_ar_cbte_letra),
                                class_name="text-xs font-medium text-indigo-700",
                            ),
                            rx.el.span(
                                " | IVA: ",
                                State.fiscal_lookup_result["iva_condition"],
                                class_name="text-xs text-indigo-600",
                            ),
                            class_name="flex items-center gap-1 mt-1 px-2 py-0.5 bg-indigo-50 rounded",
                        ),
                        rx.fragment(),
                    ),
                    # Advertencia PE (estado no ACTIVO o condición no HABIDO)
                    rx.cond(
                        State.fiscal_lookup_error != "",
                        rx.el.div(
                            rx.icon("triangle-alert", class_name="h-3 w-3 text-amber-600 shrink-0"),
                            rx.el.span(
                                State.fiscal_lookup_error,
                                class_name="text-xs text-amber-700",
                            ),
                            class_name="flex items-center gap-1 mt-1",
                        ),
                        rx.fragment(),
                    ),
                    class_name="p-2 bg-emerald-50 border border-emerald-200 rounded-md",
                ),
                rx.fragment(),
            ),
            # Error (no encontrado / error de red)
            rx.cond(
                (State.fiscal_lookup_result.length() == 0)  # type: ignore[union-attr]
                & (State.fiscal_lookup_error != ""),
                rx.el.div(
                    rx.icon("circle-x", class_name="h-3.5 w-3.5 text-red-500 shrink-0"),
                    rx.el.span(
                        State.fiscal_lookup_error,
                        class_name="text-xs text-red-600",
                    ),
                    role="alert",
                    class_name="flex items-center gap-1.5 p-2 bg-red-50 border border-red-200 rounded-md",
                ),
                rx.fragment(),
            ),
            # Botón limpiar (visible si hay datos)
            rx.cond(
                State.fiscal_doc_number != "",
                rx.el.button(
                    rx.icon("x", class_name="h-3 w-3"),
                    rx.el.span("Limpiar", class_name="text-xs"),
                    on_click=State.clear_fiscal_lookup,
                    class_name="flex items-center gap-0.5 text-slate-400 hover:text-slate-600 self-end",
                ),
                rx.fragment(),
            ),
            class_name="flex flex-col gap-1.5 px-3 py-2 bg-slate-50 rounded-lg",
        ),
        rx.fragment(),
    )


def _receipt_type_selector() -> rx.Component:
    """Selector de tipo de comprobante fiscal (boleta/factura/nota de venta).

    Solo visible si la empresa tiene billing activo.
    Detecta automáticamente factura cuando el cliente tiene RUC/CUIT.
    """
    _btn_base = (
        "flex-1 text-center text-xs font-medium py-1.5 px-2 rounded-md "
        "border transition-colors cursor-pointer"
    )
    _btn_active = _btn_base + " bg-indigo-100 border-indigo-300 text-indigo-700"
    _btn_inactive = _btn_base + " bg-white border-slate-200 text-slate-500 hover:bg-slate-50"

    return rx.cond(
        State.billing_is_active,
        rx.el.div(
            rx.el.span("Comprobante", class_name="text-xs font-medium text-slate-500"),
            rx.el.div(
                rx.el.button(
                    "Nota de Venta",
                    on_click=State.set_sale_receipt_type("nota_venta"),
                    class_name=rx.cond(
                        State.sale_receipt_type_selection == "nota_venta",
                        _btn_active,
                        _btn_inactive,
                    ),
                ),
                rx.el.button(
                    "Boleta",
                    on_click=State.set_sale_receipt_type("boleta"),
                    class_name=rx.cond(
                        State.sale_receipt_type_selection == "boleta",
                        _btn_active,
                        _btn_inactive,
                    ),
                ),
                rx.el.button(
                    "Factura",
                    on_click=State.set_sale_receipt_type("factura"),
                    class_name=rx.cond(
                        State.sale_receipt_type_selection == "factura",
                        _btn_active,
                        _btn_inactive,
                    ),
                ),
                class_name="flex gap-1",
            ),
            class_name="flex flex-col gap-1 px-3 py-2 bg-slate-50 rounded-lg",
        ),
        rx.fragment(),
    )


def compact_sale_item_row(item: rx.Var[dict]) -> rx.Component:
    """Fila compacta para la tabla de productos en venta (desktop)."""
    return rx.el.tr(
        rx.el.td(
            item["barcode"],
            class_name="py-2 px-3 text-xs text-slate-500 font-mono hidden md:table-cell",
        ),
        rx.el.td(
            item["description"],
            class_name="py-2 px-3 text-sm font-medium text-slate-800",
        ),
        rx.el.td(
            item["quantity"].to_string(),
            class_name="py-2 px-3 text-center text-sm",
        ),
        rx.el.td(
            rx.el.span(State.currency_symbol, item["price"].to_string()),
            class_name="py-2 px-3 text-right text-sm hidden sm:table-cell",
        ),
        rx.el.td(
            rx.el.span(
                State.currency_symbol,
                item["subtotal"].to_string(),
                class_name="font-semibold text-indigo-600",
            ),
            class_name="py-2 px-3 text-right text-sm",
        ),
        rx.el.td(
            rx.el.button(
                rx.icon("x", class_name="h-4 w-4"),
                on_click=lambda: State.remove_item_from_sale(item["temp_id"]),
                title="Quitar producto",
                aria_label="Quitar producto",
                class_name="p-1 text-red-500 hover:bg-red-50 rounded transition-colors",
            ),
            class_name="py-2 px-2 text-center",
        ),
        class_name="border-b border-slate-100 hover:bg-slate-50 transition-colors",
    )


def mobile_sale_item_card(item: rx.Var[dict]) -> rx.Component:
    """Card de producto para móvil."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.span(item["description"], class_name="font-medium text-slate-800"),
                rx.el.span(item["barcode"], class_name="text-xs text-slate-400 font-mono"),
                class_name="flex flex-col",
            ),
            rx.el.button(
                rx.icon("x", class_name="h-4 w-4"),
                on_click=lambda: State.remove_item_from_sale(item["temp_id"]),
                title="Quitar producto",
                aria_label="Quitar producto",
                class_name="p-1.5 text-red-500 hover:bg-red-50 rounded-full transition-colors",
            ),
            class_name="flex items-start justify-between gap-2",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span("Cant:", class_name="text-xs text-slate-500"),
                rx.el.span(item["quantity"].to_string(), class_name="font-medium"),
                class_name="flex items-center gap-1",
            ),
            rx.el.div(
                rx.el.span("Precio:", class_name="text-xs text-slate-500"),
                rx.el.span(State.currency_symbol, item["price"].to_string(), class_name="font-medium"),
                class_name="flex items-center gap-1",
            ),
            rx.el.div(
                rx.el.span(
                    State.currency_symbol,
                    item["subtotal"].to_string(),
                    class_name="text-lg font-bold text-indigo-600",
                ),
                class_name="ml-auto",
            ),
            class_name="flex items-center gap-4 mt-2",
        ),
        class_name="p-3 bg-white border-b border-slate-100",
    )


def recent_moves_modal() -> rx.Component:
    """Modal de movimientos recientes del inventario."""
    table_header = rx.table.header(
        rx.table.row(
            rx.table.column_header_cell("Hora"),
            rx.table.column_header_cell("Detalle"),
            rx.table.column_header_cell("Cliente"),
            rx.table.column_header_cell("Total", justify="end"),
            rx.table.column_header_cell("", justify="center"),
        )
    )

    table_body = rx.table.body(
        rx.foreach(
            State.recent_transactions,
            lambda entry: rx.table.row(
                rx.table.cell(
                    entry["time_display"],
                    class_name="text-sm text-slate-600",
                ),
                rx.table.cell(
                    rx.cond(
                        State.recent_expanded_id == entry["id"],
                        rx.cond(
                            entry["detail_lines"].length() > 0,
                            rx.el.div(
                                rx.foreach(
                                    entry["detail_lines"],
                                    lambda line: rx.el.div(
                                        rx.el.span(
                                            line["left"],
                                            class_name="min-w-0 flex-1",
                                        ),
                                        rx.el.span(
                                            line["right"],
                                            class_name="whitespace-nowrap font-semibold text-slate-900",
                                        ),
                                        class_name="flex items-start justify-between gap-3",
                                    ),
                                ),
                                class_name="flex flex-col gap-1",
                            ),
                            rx.el.span(
                                entry["detail_full"],
                                class_name="whitespace-pre-line",
                            ),
                        ),
                        rx.el.span(entry["detail_short"]),
                    ),
                    on_click=State.toggle_recent_detail(entry["id"]),
                    class_name=(
                        "text-sm text-slate-800 cursor-pointer "
                        "hover:text-indigo-700"
                    ),
                ),
                rx.table.cell(
                    entry["client_display"],
                    class_name="text-sm text-slate-600",
                ),
                rx.table.cell(
                    entry["amount_display"],
                    justify="end",
                    class_name="text-sm font-semibold text-slate-900 tabular-nums",
                ),
                rx.table.cell(
                    rx.cond(
                        entry["sale_id"] != "",
                        rx.el.button(
                            rx.icon("printer", class_name="h-4 w-4"),
                            on_click=State.reprint_recent_sale(entry["sale_id"]),
                            class_name="p-2 text-indigo-600 hover:bg-indigo-50 rounded-full",
                            title="Reimprimir comprobante",
                            aria_label="Reimprimir comprobante",
                        ),
                        rx.el.span("-", class_name="text-xs text-slate-400"),
                    ),
                    justify="center",
                ),
            ),
        ),
    )

    table = rx.table.root(
        table_header,
        table_body,
        variant="surface",
        size="2",
        class_name="w-full",
    )

    content = rx.cond(
        State.recent_loading,
        rx.el.div(
            rx.spinner(size="3"),
            class_name="py-8 flex justify-center",
        ),
        rx.cond(
            State.recent_transactions.length() > 0,
            rx.el.div(
                table,
                class_name="w-full overflow-x-auto",
            ),
            rx.el.p(
                "No hay movimientos recientes.",
                class_name="text-sm text-slate-500 text-center py-6",
            ),
        ),
    )

    footer = rx.el.div(
        action_button(
            "Cerrar",
            on_click=State.toggle_recent_modal(False),
            variant="secondary",
        ),
        class_name="flex justify-end",
    )

    return modal_container(
        is_open=State.show_recent_modal,
        on_close=State.toggle_recent_modal(False),
        title="Movimientos recientes",
        description="Últimas 15 operaciones registradas en la sucursal activa.",
        children=[content],
        footer=footer,
        max_width="max-w-3xl",
    )


def sale_receipt_modal() -> rx.Component:
    """Modal del recibo/boleta de venta."""
    footer = rx.hstack(
        rx.el.button(
            rx.icon("download", class_name="h-4 w-4"),
            "Descargar PDF",
            on_click=State.download_pdf_receipt,
            class_name=f"{BUTTON_STYLES['primary']} flex-1",
        ),
        rx.el.button(
            rx.icon("printer", class_name="h-4 w-4"),
            "Imprimir Ticket",
            on_click=State.print_receipt,
            class_name=f"{BUTTON_STYLES['success']} flex-1",
        ),
        spacing="2",
        class_name="w-full",
    )

    body = rx.el.div(
        rx.el.p(
            "Selecciona la salida del comprobante para finalizar la venta.",
            class_name="text-sm text-slate-600 text-center",
        ),
        class_name="py-2",
    )

    return modal_container(
        is_open=State.show_sale_receipt_modal,
        on_close=State.close_sale_receipt_modal,
        title=rx.el.span(
            "Comprobante generado",
            class_name="block w-full text-center",
        ),
        description=rx.el.span(
            "¿Cómo deseas entregar el comprobante?",
            class_name="block w-full text-center",
        ),
        children=[body],
        footer=footer,
        max_width="max-w-md",
    )


def client_selector() -> rx.Component:
    """Selector de cliente para ventas a credito."""
    return rx.box(
        rx.cond(
            State.selected_client != None,
            rx.hstack(
                rx.hstack(
                    rx.vstack(
                        rx.el.span(
                            State.selected_client["name"],
                            class_name="text-sm font-semibold text-slate-900",
                        ),
                        rx.el.span(
                            "DNI: ",
                            State.selected_client["dni"],
                            class_name="text-xs text-slate-500 font-mono",
                        ),
                        spacing="1",
                        align="start",
                        class_name="min-w-0",
                    ),
                    rx.badge(
                        rx.el.span(
                            "Linea de Credito: ",
                            State.currency_symbol,
                            State.selected_client_credit_available.to_string(),
                        ),
                        color_scheme="green",
                        variant="soft",
                        size="2",
                        class_name="whitespace-nowrap",
                    ),
                    spacing="3",
                    align="center",
                    class_name="flex-1 min-w-0",
                ),
                rx.icon_button(
                    "trash-2",
                    on_click=State.clear_selected_client,
                    color_scheme="red",
                    variant="soft",
                    size="2",
                    title="Quitar cliente",
                    aria_label="Quitar cliente",
                ),
                align="center",
                justify="between",
                class_name="w-full",
            ),
            rx.vstack(
                rx.el.div(
                    rx.debounce_input(
                        rx.input(
                            value=State.client_search_query,
                            on_change=State.search_client_change,
                            placeholder="Buscar cliente (DNI o nombre)...",
                            class_name="flex-1 px-3 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-indigo-500",
                        ),
                        debounce_timeout=600,
                    ),
                    rx.el.button(
                        rx.icon("plus", class_name="h-4 w-4"),
                        on_click=State.open_modal_from_pos,
                        class_name="h-10 w-10 flex items-center justify-center rounded-lg border text-indigo-600 hover:bg-indigo-50",
                        title="Nuevo cliente",
                        aria_label="Nuevo cliente",
                    ),
                    class_name="flex items-center gap-1 w-full",
                ),
                rx.cond(
                    State.client_suggestions.length() > 0,
                    rx.vstack(
                        rx.foreach(
                            State.client_suggestions,
                            lambda client: rx.button(
                                rx.vstack(
                                    rx.el.span(
                                        client["name"],
                                        class_name="font-medium text-slate-900",
                                    ),
                                    rx.el.span(
                                        "DNI: ",
                                        client["dni"],
                                        class_name="text-xs text-slate-500 font-mono",
                                    ),
                                    spacing="1",
                                    align="start",
                                    class_name="w-full",
                                ),
                                on_click=lambda _, c=client: State.select_client(c),
                                variant="ghost",
                                class_name="w-full justify-start text-left",
                            ),
                        ),
                        spacing="1",
                        class_name="w-full rounded-lg border bg-white shadow-sm p-1",
                    ),
                    rx.fragment(),
                ),
                spacing="1",
                class_name="w-full",
            ),
        ),
        class_name="w-full p-2.5 bg-white rounded-xl border shadow-sm",
    )


def quick_add_bar() -> rx.Component:
    """Barra de entrada rápida de productos - estilo POS responsive."""
    return rx.el.div(
        # Fila 1: Código de barra y Búsqueda (siempre visible)
        rx.el.div(
            # Código de barra — form-based: solo dispara evento al presionar Enter
            rx.el.div(
                rx.el.form(
                    rx.el.div(
                        rx.icon("scan-barcode", class_name="h-5 w-5 text-slate-400 flex-shrink-0"),
                        rx.el.input(
                            name="barcode",
                            id="venta_barcode_input",
                            key=State.sale_form_key.to_string(),
                            default_value=State.new_sale_item["barcode"],
                            placeholder="Código...",
                            class_name="flex-1 min-w-0 border-0 focus:ring-0 text-sm bg-transparent outline-none py-0",
                            type="text",
                            auto_complete="off",
                        ),
                        class_name="flex items-center gap-1 px-3 py-2 border rounded-lg bg-white focus-within:ring-2 focus-within:ring-indigo-500 w-full",
                    ),
                    on_submit=State.handle_barcode_form_submit,
                    reset_on_submit=True,
                    class_name="w-full",
                ),
                rx.cond(
                    State.last_scanned_label != "",
                    rx.el.span(
                        State.last_scanned_label,
                        class_name="text-xs text-slate-500 truncate",
                    ),
                    rx.fragment(),
                ),
                class_name="flex flex-col gap-1 w-full sm:w-56 lg:w-64",
            ),
            # Búsqueda de producto
            rx.el.div(
                rx.el.div(
                    rx.icon("search", class_name="h-5 w-5 text-slate-400 flex-shrink-0"),
                    rx.debounce_input(
                        rx.input(
                            value=State.new_sale_item["description"],
                            on_change=lambda val: State.handle_sale_change("description", val),
                            on_key_down=State.handle_autocomplete_keydown,
                            placeholder="Buscar producto...",
                            class_name="flex-1 min-w-0 border-0 focus:ring-0 text-sm bg-transparent outline-none py-0",
                        ),
                        debounce_timeout=600,
                    ),
                    class_name="flex items-center gap-1 px-3 py-2 border rounded-lg bg-white focus-within:ring-2 focus-within:ring-indigo-500 w-full",
                ),
                rx.cond(
                    State.autocomplete_results.length() > 0,
                    rx.el.div(
                        rx.foreach(
                            State.autocomplete_rows,
                            lambda suggestion: rx.el.button(
                                suggestion["description"],
                                on_click=lambda _, s=suggestion: State.select_product_for_sale(s),
                                class_name=rx.cond(
                                    suggestion["index"]
                                    == State.autocomplete_selected_index,
                                    "w-full text-left px-3 py-2.5 bg-indigo-50 text-sm border-b border-slate-100 last:border-0",
                                    "w-full text-left px-3 py-2.5 hover:bg-indigo-50 text-sm border-b border-slate-100 last:border-0",
                                ),
                            ),
                        ),
                        custom_attrs={"data-autocomplete-dropdown": "1"},
                        class_name="absolute z-20 left-0 right-0 mt-1 bg-white border rounded-lg shadow-xl max-h-60 overflow-y-auto",
                    ),
                    rx.fragment(),
                ),
                custom_attrs={"data-product-search": "1"},
                class_name="relative flex-1 min-w-0",
            ),
            class_name="flex flex-col sm:flex-row gap-2 flex-1",
        ),
        # Fila 2: Cantidad, Precio, Subtotal y Botón
        rx.el.div(
            # Cantidad
            rx.el.div(
                rx.el.label("Cant.", class_name="text-xs text-slate-500 sm:hidden"),
                rx.el.input(
                    type="number",
                    min="0.01",
                    step="0.01",
                    key=State.sale_form_key.to_string() + "_qty",
                    default_value=State.new_sale_item["quantity"].to_string(),
                    on_blur=lambda val: State.handle_sale_change("quantity", val),
                    class_name="w-full px-3 py-2 border rounded-lg text-sm text-center focus:ring-2 focus:ring-indigo-500",
                    placeholder="1",
                ),
                class_name="flex flex-col gap-1 w-[88px] sm:w-20",
            ),
            # Precio
            rx.el.div(
                rx.el.div(
                    rx.el.label("Precio", class_name="text-xs text-slate-500 sm:hidden"),
                    rx.cond(
                        State.wholesale_price_applied,
                        rx.el.span(
                            "Mayorista",
                            class_name="text-xs font-semibold text-amber-600 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5 leading-none",
                        ),
                        rx.fragment(),
                    ),
                    class_name="flex items-center gap-1.5",
                ),
                rx.el.div(
                    rx.el.span(State.currency_symbol, class_name="text-slate-400 text-sm"),
                    rx.el.input(
                        type="number",
                        min="0",
                        step="0.01",
                        key=State.sale_form_key.to_string() + "_price",
                        default_value=State.new_sale_item["price"].to_string(),
                        on_blur=lambda val: State.handle_sale_change("price", val),
                        class_name="flex-1 min-w-0 border-0 focus:ring-0 text-sm bg-transparent outline-none text-right",
                    ),
                    class_name=rx.cond(
                        State.wholesale_price_applied,
                        "flex items-center gap-1 px-3 py-2 border border-amber-300 rounded-lg bg-amber-50/50 focus-within:ring-2 focus-within:ring-amber-500",
                        "flex items-center gap-1 px-3 py-2 border rounded-lg bg-white focus-within:ring-2 focus-within:ring-indigo-500",
                    ),
                ),
                class_name="flex flex-col gap-1 w-[122px] sm:w-28",
            ),
            # Subtotal
            rx.el.div(
                rx.el.label("Subtotal", class_name="text-xs text-slate-500 sm:hidden"),
                rx.el.div(
                    rx.el.span(
                        State.currency_symbol,
                        State.sale_subtotal.to_string(),
                        class_name="text-sm font-semibold text-indigo-600",
                    ),
                    class_name="px-3 py-2 bg-slate-100 rounded-lg text-right h-[42px] flex items-center justify-end",
                ),
                class_name="flex flex-col gap-1 w-[122px] sm:w-28",
            ),
            # Botón añadir
            rx.el.button(
                rx.icon("plus", class_name="h-5 w-5"),
                rx.el.span("Añadir", class_name="sm:hidden"),
                on_click=State.add_item_to_sale,
                custom_attrs={"data-venta-add-btn": "1"},
                class_name=(
                    "inline-flex h-[42px] min-w-[106px] items-center justify-center gap-2 rounded-lg "
                    "bg-indigo-600 px-3.5 text-sm font-medium text-white hover:bg-indigo-700 "
                    "transition-colors sm:min-w-[120px]"
                ),
            ),
            class_name="flex flex-wrap items-end gap-2",
        ),
        custom_attrs={"data-quick-add-bar": "1"},
        class_name="flex flex-col gap-2 p-2.5 bg-slate-50 border-b",
    )


def products_table(embedded: bool = False) -> rx.Component:
    """Tabla de productos en la venta - responsive."""
    content = rx.el.div(
        # Header
        rx.el.div(
            rx.el.div(
                rx.icon("shopping-cart", class_name="h-5 w-5 text-indigo-600"),
                rx.el.span("Productos", class_name="font-semibold text-slate-800 sm:hidden"),
                rx.el.span("PRODUCTOS EN VENTA", class_name="font-semibold text-slate-800 hidden sm:inline"),
                rx.el.span(
                    "(", State.new_sale_items.length().to_string(), ")",
                    class_name="text-sm text-slate-500",
                ),
                class_name="flex items-center gap-1",
            ),
            rx.el.button(
                rx.icon("trash-2", class_name="h-4 w-4"),
                rx.el.span("Vaciar", class_name="hidden sm:inline"),
                on_click=State.clear_sale_items,
                class_name="flex items-center gap-1 px-2 sm:px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors",
            ),
            class_name="flex items-center justify-between p-2.5 bg-white border-b",
        ),
        # Contenido
        rx.el.div(
            rx.cond(
                State.new_sale_items.length() > 0,
                rx.fragment(
                    # Vista móvil: cards
                    rx.el.div(
                        rx.foreach(State.new_sale_items, mobile_sale_item_card),
                        class_name="sm:hidden",
                    ),
                    # Vista desktop: tabla
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th(
                                    "Código",
                                    scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell",
                                ),
                                rx.el.th(
                                    "Producto", scope="col", class_name=TABLE_STYLES["header_cell"]
                                ),
                                rx.el.th(
                                    "Cant.",
                                    scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center",
                                ),
                                rx.el.th(
                                    "Precio",
                                    scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right hidden sm:table-cell",
                                ),
                                rx.el.th(
                                    "Subtotal",
                                    scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right",
                                ),
                                rx.el.th(
                                    "", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-10"
                                ),
                                class_name=TABLE_STYLES["header"],
                            ),
                        ),
                        rx.el.tbody(
                            rx.foreach(State.new_sale_items, compact_sale_item_row),
                        ),
                        class_name="w-full hidden sm:table",
                    ),
                ),
                rx.el.div(
                    rx.icon("package-open", class_name="h-10 w-10 sm:h-12 sm:w-12 text-slate-300"),
                    rx.el.p("No hay productos", class_name="text-slate-500 font-medium"),
                    rx.el.p("Escanea un código o busca un producto", class_name="text-xs sm:text-sm text-slate-400"),
                    class_name="flex flex-col items-center justify-center py-8 sm:py-12 text-center",
                ),
            ),
            class_name="flex-1 overflow-y-auto px-3 py-2",
        ),
        class_name="flex flex-col flex-1 min-h-[320px] sm:min-h-[360px]",
    )
    if embedded:
        return content
    return rx.el.div(
        content,
        class_name="flex flex-col bg-white rounded-xl border shadow-sm flex-1 min-h-[320px] sm:min-h-[360px]",
    )


def sale_products_card() -> rx.Component:
    """Tarjeta principal con los productos de la venta."""
    return rx.el.div(
        quick_add_bar(),
        products_table(embedded=True),
        class_name="flex flex-col bg-white rounded-xl border shadow-sm flex-1 min-h-[320px] sm:min-h-[360px]",
    )


def reservation_info_card() -> rx.Component:
    """Card prominente de reserva/servicio si existe."""
    return rx.cond(
        State.reservation_selected_for_payment != None,
        rx.el.div(
            # Header con icono, título y botón cerrar
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.icon("calendar-check", class_name="h-6 w-6 text-white"),
                        class_name="p-2 bg-emerald-600 rounded-lg",
                    ),
                    rx.el.div(
                        rx.el.span("Cobro de Servicio", class_name="font-bold text-slate-800"),
                        rx.el.span("Alquiler de Campo", class_name="text-sm text-slate-500"),
                        class_name="flex flex-col",
                    ),
                    class_name="flex items-center gap-2",
                ),
                # Botón cerrar para limpiar la reserva pendiente
                rx.el.button(
                    rx.icon("x", class_name="h-5 w-5"),
                    on_click=State.clear_pending_reservation,
                    title="Cerrar cobro de servicio",
                    aria_label="Cerrar cobro de servicio",
                    class_name="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors",
                ),
                class_name="flex items-center justify-between",
            ),
            # Datos del cliente y reserva
            rx.el.div(
                # Columna 1: Cliente
                rx.el.div(
                    rx.el.div(
                        rx.icon("user", class_name="h-4 w-4 text-slate-400"),
                        rx.el.span("Cliente", class_name="text-xs text-slate-500 uppercase"),
                        class_name="flex items-center gap-1",
                    ),
                    rx.el.span(
                        State.reservation_selected_for_payment["client_name"],
                        class_name="font-semibold text-slate-800",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                # Columna 2: Campo
                rx.el.div(
                    rx.el.div(
                        rx.icon("map-pin", class_name="h-4 w-4 text-slate-400"),
                        rx.el.span("Campo", class_name="text-xs text-slate-500 uppercase"),
                        class_name="flex items-center gap-1",
                    ),
                    rx.el.span(
                        State.reservation_selected_for_payment["field_name"],
                        class_name="font-semibold text-slate-800",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                # Columna 3: Horario
                rx.el.div(
                    rx.el.div(
                        rx.icon("clock", class_name="h-4 w-4 text-slate-400"),
                        rx.el.span("Horario", class_name="text-xs text-slate-500 uppercase"),
                        class_name="flex items-center gap-1",
                    ),
                    rx.el.span(
                        State.reservation_selected_for_payment["start_datetime"],
                        class_name="font-semibold text-slate-800 text-sm",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                # Columna 4: Teléfono
                rx.el.div(
                    rx.el.div(
                        rx.icon("phone", class_name="h-4 w-4 text-slate-400"),
                        rx.el.span("Teléfono", class_name="text-xs text-slate-500 uppercase"),
                        class_name="flex items-center gap-1",
                    ),
                    rx.el.span(
                        State.reservation_selected_for_payment["phone"],
                        class_name="font-semibold text-slate-800",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 mt-2",
            ),
            # Resumen de montos
            rx.el.div(
                rx.el.div(
                    rx.el.span("Total Reserva", class_name="text-sm text-slate-600"),
                    rx.el.span(
                        State.currency_symbol,
                        State.reservation_selected_for_payment["total_amount"].to_string(),
                        class_name="text-lg font-bold text-slate-800",
                    ),
                    class_name="flex flex-col items-center p-2 bg-slate-50 rounded-lg",
                ),
                rx.el.div(
                    rx.el.span("Adelanto Pagado", class_name="text-sm text-slate-600"),
                    rx.el.span(
                        State.currency_symbol,
                        State.reservation_selected_for_payment["advance_amount"].to_string(),
                        class_name="text-lg font-bold text-emerald-600",
                    ),
                    class_name="flex flex-col items-center p-2 bg-emerald-50 rounded-lg",
                ),
                rx.el.div(
                    rx.el.span("Saldo a Cobrar", class_name="text-sm text-slate-600"),
                    rx.el.span(
                        State.currency_symbol,
                        State.selected_reservation_balance.to_string(),
                        class_name="text-2xl font-bold text-indigo-600",
                    ),
                    class_name="flex flex-col items-center p-2 bg-indigo-50 rounded-lg border-2 border-indigo-200",
                ),
                class_name="grid grid-cols-1 sm:grid-cols-3 gap-1 mt-2",
            ),
            class_name="bg-white border-2 border-emerald-200 rounded-xl p-2 shadow-sm",
        ),
        rx.fragment(),
    )


def _payment_form_body(variant: str) -> rx.Component:
    """Shared inner form content for payment sidebar and mobile section.

    Args:
        variant: "desktop" for the sidebar, "mobile" for the mobile/tablet section.
    """
    is_desktop = variant == "desktop"

    # ── Payment method button classes ──────────────────────────────────────
    pm_btn_active = (
        "flex items-center gap-2 px-3 py-2 rounded-lg bg-indigo-600 text-white w-full justify-center"
        if is_desktop else
        "flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-indigo-600 text-white"
    )
    pm_btn_inactive = (
        "flex items-center gap-2 px-3 py-2 rounded-lg border bg-white text-slate-700 hover:bg-slate-50 w-full justify-center"
        if is_desktop else
        "flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border text-slate-700 hover:bg-slate-50"
    )
    pm_name_class = (
        "text-xs uppercase font-medium"
        if is_desktop else
        "uppercase text-xs sm:text-sm font-medium"
    )

    # ── Payment method grid wrapper ─────────────────────────────────────────
    pm_grid_class = (
        "grid grid-cols-2 gap-2"
        if is_desktop else
        "grid grid-cols-2 sm:grid-cols-4 gap-2 p-3 sm:p-4"
    )

    # ── Credit section wrapper class ────────────────────────────────────────
    credit_section_class = (
        "p-4 border-b"
        if is_desktop else
        "px-3 sm:px-4 pb-3 border-b"
    )

    # ── Cash input key suffix ───────────────────────────────────────────────
    cash_key_suffix = "_cash_amount_desktop" if is_desktop else "_cash_amount_mobile"
    mixed_cash_key_suffix = "_mixed_cash_desktop" if is_desktop else "_mixed_cash_mobile"

    # ── Cash input sizing ───────────────────────────────────────────────────
    cash_symbol_class = "text-slate-400" if is_desktop else "text-slate-400 text-lg"
    cash_input_class = (
        "flex-1 border-0 focus:ring-0 text-lg font-semibold bg-transparent outline-none text-right"
        if is_desktop else
        "flex-1 border-0 focus:ring-0 text-xl font-semibold bg-transparent outline-none text-right"
    )
    cash_row_class = (
        "flex items-center gap-2 px-3 py-2 border rounded-lg bg-white focus-within:ring-2 focus-within:ring-indigo-500"
        if is_desktop else
        "flex items-center gap-2 px-3 py-3 border rounded-lg bg-white focus-within:ring-2 focus-within:ring-indigo-500"
    )
    cash_label_class = (
        "text-xs font-medium text-slate-600"
        if is_desktop else
        "text-sm font-medium text-slate-700"
    )
    cash_section_class = (
        "flex flex-col gap-2"
        if is_desktop else
        "flex flex-col gap-2 px-3 sm:px-4 pb-3"
    )

    # ── Card/wallet label class ─────────────────────────────────────────────
    card_label_class = (
        "text-xs font-medium text-slate-600"
        if is_desktop else
        "text-sm font-medium text-slate-700"
    )
    card_section_class = (
        "flex flex-col gap-2"
        if is_desktop else
        "flex flex-col gap-2 px-3 sm:px-4 pb-3"
    )
    wallet_label = "Billetera" if is_desktop else "Billetera digital"
    wallet_section_class = (
        "flex flex-col gap-2"
        if is_desktop else
        "flex flex-col gap-2 px-3 sm:px-4 pb-3"
    )

    # ── Card/wallet button padding ──────────────────────────────────────────
    card_btn_active = (
        "flex-1 px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium"
        if is_desktop else
        "flex-1 px-3 py-2.5 rounded-lg bg-indigo-600 text-white font-medium"
    )
    card_btn_inactive = (
        "flex-1 px-3 py-2 rounded-lg border text-slate-700 text-sm hover:bg-slate-50"
        if is_desktop else
        "flex-1 px-3 py-2.5 rounded-lg border text-slate-700 hover:bg-slate-50"
    )
    yape_btn_active = (
        "flex-1 px-3 py-2 rounded-lg bg-purple-600 text-white text-sm font-medium"
        if is_desktop else
        "flex-1 px-3 py-2.5 rounded-lg bg-purple-600 text-white font-medium"
    )
    yape_btn_inactive = (
        "flex-1 px-3 py-2 rounded-lg border text-slate-700 text-sm hover:bg-slate-50"
        if is_desktop else
        "flex-1 px-3 py-2.5 rounded-lg border text-slate-700 hover:bg-slate-50"
    )
    plin_btn_active = (
        "flex-1 px-3 py-2 rounded-lg bg-teal-600 text-white text-sm font-medium"
        if is_desktop else
        "flex-1 px-3 py-2.5 rounded-lg bg-teal-600 text-white font-medium"
    )
    plin_btn_inactive = (
        "flex-1 px-3 py-2 rounded-lg border text-slate-700 text-sm hover:bg-slate-50"
        if is_desktop else
        "flex-1 px-3 py-2.5 rounded-lg border text-slate-700 hover:bg-slate-50"
    )
    mixed_btn_active = (
        "flex-1 px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium"
        if is_desktop else
        "flex-1 px-3 py-2.5 rounded-lg bg-indigo-600 text-white font-medium"
    )
    mixed_btn_inactive = (
        "flex-1 px-3 py-2 rounded-lg border text-slate-700 text-sm hover:bg-slate-50"
        if is_desktop else
        "flex-1 px-3 py-2.5 rounded-lg border text-slate-700 hover:bg-slate-50"
    )
    mixed_yape_active = (
        "flex-1 px-3 py-2 rounded-lg bg-purple-600 text-white text-sm font-medium"
        if is_desktop else
        "flex-1 px-3 py-2.5 rounded-lg bg-purple-600 text-white font-medium"
    )
    mixed_yape_inactive = (
        "flex-1 px-3 py-2 rounded-lg border text-slate-700 text-sm hover:bg-slate-50"
        if is_desktop else
        "flex-1 px-3 py-2.5 rounded-lg border text-slate-700 hover:bg-slate-50"
    )
    mixed_plin_active = (
        "flex-1 px-3 py-2 rounded-lg bg-teal-600 text-white text-sm font-medium"
        if is_desktop else
        "flex-1 px-3 py-2.5 rounded-lg bg-teal-600 text-white font-medium"
    )
    mixed_plin_inactive = (
        "flex-1 px-3 py-2 rounded-lg border text-slate-700 text-sm hover:bg-slate-50"
        if is_desktop else
        "flex-1 px-3 py-2.5 rounded-lg border text-slate-700 hover:bg-slate-50"
    )
    mixed_section_class = (
        "flex flex-col gap-3"
        if is_desktop else
        "flex flex-col gap-3 px-3 sm:px-4 pb-3"
    )

    # ── Options section wrapper class ───────────────────────────────────────
    options_section_class = (
        "p-4 border-b min-h-[80px]"
        if is_desktop else
        ""
    )

    # ── Total display ───────────────────────────────────────────────────────
    total_label_class = (
        "text-xs font-medium text-slate-500"
        if is_desktop else
        "text-sm font-medium text-slate-500"
    )
    total_amount_class = (
        "text-3xl font-bold text-indigo-600"
        if is_desktop else
        "text-3xl sm:text-4xl font-bold text-indigo-600"
    )
    total_row_class = (
        "flex items-baseline gap-1"
        if is_desktop else
        "flex items-baseline gap-0.5"
    )
    total_container_class = (
        "flex flex-col items-center py-3"
        if is_desktop else
        "flex flex-col items-center"
    )
    footer_class = (
        "shrink-0 bg-white border-t"
        if is_desktop else
        "p-3 sm:p-4 bg-slate-50 border-t"
    )

    # ── Confirm button classes ──────────────────────────────────────────────
    confirm_active_class = (
        "w-full flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700 transition-colors text-lg"
        if is_desktop else
        "flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700"
    )
    confirm_loading_class = (
        "w-full flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 text-white rounded-lg font-semibold transition-colors text-lg opacity-50 cursor-not-allowed"
        if is_desktop else
        "flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 text-white rounded-lg font-semibold opacity-50 cursor-not-allowed"
    )
    confirm_wrapper_class = (
        "p-4 flex flex-col gap-2"
        if is_desktop else
        "flex gap-2 mt-3"
    )

    # ── Cash message classes ────────────────────────────────────────────────
    if is_desktop:
        cash_message_class = rx.cond(
            State.payment_cash_status == "change",
            "text-sm font-semibold text-emerald-600 mt-2",
            rx.cond(
                State.payment_cash_status == "due",
                "text-sm font-semibold text-red-600 mt-2",
                "text-sm text-slate-500 mt-2",
            ),
        )
    else:
        cash_message_class = rx.cond(
            State.payment_cash_status == "change",
            "text-sm font-semibold text-emerald-600 mt-1",
            "text-sm font-semibold text-red-600 mt-1",
        )

    # ── Credit section header ───────────────────────────────────────────────
    if is_desktop:
        credit_header = rx.hstack(
            rx.el.div(
                rx.el.span("VENTA A CREDITO / FIADO", class_name="text-xs font-medium text-slate-600"),
                rx.el.span("Configurar cuotas y pago inicial", class_name="text-xs text-slate-400"),
                class_name="flex flex-col",
            ),
            toggle_switch(
                checked=State.is_credit_mode,
                on_change=State.toggle_credit_mode,
            ),
            class_name="flex items-center justify-between",
        )
    else:
        credit_header = rx.hstack(
            rx.el.span("Venta a Credito / Fiado", class_name="text-sm font-semibold text-slate-800"),
            toggle_switch(
                checked=State.is_credit_mode,
                on_change=State.toggle_credit_mode,
            ),
            class_name="flex items-center justify-between",
        )

    # ── Payment methods section ─────────────────────────────────────────────
    pm_buttons = rx.foreach(
        State.enabled_payment_methods,
        lambda method: rx.el.button(
            rx.cond(
                method["kind"] == "cash",
                rx.icon("banknote", class_name="h-4 w-4"),
                rx.cond(
                    (method["kind"] == "debit")
                    | (method["kind"] == "credit")
                    | (method["kind"] == "card"),
                    rx.icon("credit-card", class_name="h-4 w-4"),
                    rx.cond(
                        (method["kind"] == "yape")
                        | (method["kind"] == "plin")
                        | (method["kind"] == "wallet"),
                        rx.icon("smartphone", class_name="h-4 w-4"),
                        rx.cond(
                            method["kind"] == "transfer",
                            rx.icon("arrow-left-right", class_name="h-4 w-4"),
                            rx.icon("layers", class_name="h-4 w-4"),
                        ),
                    ),
                ),
            ),
            rx.el.span(method["name"], class_name=pm_name_class),
            on_click=lambda _, mid=method["id"]: State.select_payment_method(mid),
            class_name=rx.cond(
                State.payment_method == method["name"],
                pm_btn_active,
                pm_btn_inactive,
            ),
        ),
    )

    if is_desktop:
        pm_section = rx.el.div(
            rx.el.p("Método de pago", class_name="text-xs font-medium text-slate-500 uppercase mb-2"),
            rx.el.div(
                pm_buttons,
                class_name=pm_grid_class,
            ),
            class_name="p-4 border-b",
        )
    else:
        pm_section = rx.el.div(
            pm_buttons,
            class_name=pm_grid_class,
        )

    # ── Credit fields (shared) ──────────────────────────────────────────────
    credit_fields = rx.cond(
        State.is_credit_mode,
        rx.el.div(
            rx.el.div(
                rx.el.label("Cuotas", class_name="text-xs font-medium text-slate-600"),
                rx.el.input(
                    type="number",
                    min="1",
                    default_value=State.credit_installments.to_string(),
                    on_blur=lambda value: State.set_installments_count(value),
                    class_name="w-full px-3 py-2 border rounded-lg text-sm",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Frecuencia (Dias)", class_name="text-xs font-medium text-slate-600"),
                rx.el.input(
                    type="number",
                    min="1",
                    default_value=State.credit_interval_days.to_string(),
                    on_blur=lambda value: State.set_payment_interval_days(value),
                    class_name="w-full px-3 py-2 border rounded-lg text-sm",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Pago Inicial", class_name="text-xs font-medium text-slate-600"),
                rx.el.input(
                    type="number",
                    min="0",
                    step="0.01",
                    default_value=State.credit_initial_payment,
                    on_blur=lambda value: State.set_credit_initial_payment(value),
                    class_name="w-full px-3 py-2 border rounded-lg text-sm",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.span(
                    "Saldo a financiar: ",
                    State.currency_symbol,
                    State.credit_financed_amount.to_string(),
                    " en ",
                    State.credit_installments.to_string(),
                    " cuotas",
                    class_name="text-xs text-slate-600",
                ),
                class_name="px-3 py-2 rounded-lg bg-slate-50 border",
            ),
            class_name="flex flex-col gap-3 mt-3",
        ),
        rx.fragment(),
    )

    # ── Options by payment method ───────────────────────────────────────────
    cash_option = rx.cond(
        State.payment_method_kind == "cash",
        rx.el.div(
            rx.el.label("Monto recibido", class_name=cash_label_class),
            rx.el.div(
                rx.el.span(State.currency_symbol, class_name=cash_symbol_class),
                rx.el.input(
                    type="number",
                    key=State.sale_form_key.to_string() + cash_key_suffix,
                    default_value=rx.cond(
                        State.payment_cash_amount > 0,
                        State.payment_cash_amount.to_string(),
                        "",
                    ),
                    on_blur=lambda value: State.set_cash_amount(value),
                    class_name=cash_input_class,
                    placeholder="0.00",
                ),
                class_name=cash_row_class,
            ),
            rx.cond(
                State.is_credit_mode,
                rx.fragment(),
                rx.cond(
                    State.payment_cash_message != "",
                    rx.el.p(
                        State.payment_cash_message,
                        class_name=cash_message_class,
                    ),
                    rx.fragment(),
                ),
            ),
            class_name=cash_section_class,
        ),
        rx.fragment(),
    )

    card_option = rx.cond(
        State.payment_method_kind == "card",
        rx.el.div(
            rx.el.label("Tipo de tarjeta", class_name=card_label_class),
            rx.el.div(
                rx.el.button(
                    "Crédito",
                    on_click=lambda: State.set_card_type("Credito"),
                    class_name=rx.cond(
                        State.payment_card_type == "Credito",
                        card_btn_active,
                        card_btn_inactive,
                    ),
                ),
                rx.el.button(
                    "Débito",
                    on_click=lambda: State.set_card_type("Debito"),
                    class_name=rx.cond(
                        State.payment_card_type == "Debito",
                        card_btn_active,
                        card_btn_inactive,
                    ),
                ),
                class_name="flex gap-2",
            ),
            class_name=card_section_class,
        ),
        rx.fragment(),
    )

    wallet_option = rx.cond(
        State.payment_method_kind == "wallet",
        rx.el.div(
            rx.el.label(wallet_label, class_name=card_label_class),
            rx.el.div(
                rx.el.button(
                    "Yape",
                    on_click=lambda: State.choose_wallet_provider("Yape"),
                    class_name=rx.cond(
                        State.payment_wallet_choice == "Yape",
                        yape_btn_active,
                        yape_btn_inactive,
                    ),
                ),
                rx.el.button(
                    "Plin",
                    on_click=lambda: State.choose_wallet_provider("Plin"),
                    class_name=rx.cond(
                        State.payment_wallet_choice == "Plin",
                        plin_btn_active,
                        plin_btn_inactive,
                    ),
                ),
                class_name="flex gap-2",
            ),
            class_name=wallet_section_class,
        ),
        rx.fragment(),
    )

    mixed_option = rx.cond(
        State.payment_method_kind == "mixed",
        rx.el.div(
            rx.el.div(
                rx.el.label("Efectivo", class_name="text-xs font-medium text-slate-600"),
                rx.el.input(
                    type="number",
                    key=State.sale_form_key.to_string() + mixed_cash_key_suffix,
                    default_value=rx.cond(
                        State.payment_mixed_cash > 0,
                        State.payment_mixed_cash.to_string(),
                        "",
                    ),
                    on_blur=lambda value: State.set_mixed_cash_amount(value),
                    class_name="w-full px-3 py-2 border rounded-lg text-sm",
                    placeholder="0.00",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Complemento", class_name="text-xs font-medium text-slate-600"),
                rx.el.div(
                    rx.el.button(
                        "T. Débito",
                        on_click=lambda: State.set_mixed_non_cash_kind("debit"),
                        class_name=rx.cond(
                            State.payment_mixed_non_cash_kind == "debit",
                            mixed_btn_active,
                            mixed_btn_inactive,
                        ),
                    ),
                    rx.el.button(
                        "T. Crédito",
                        on_click=lambda: State.set_mixed_non_cash_kind("credit"),
                        class_name=rx.cond(
                            State.payment_mixed_non_cash_kind == "credit",
                            mixed_btn_active,
                            mixed_btn_inactive,
                        ),
                    ),
                    rx.el.button(
                        "Yape",
                        on_click=lambda: State.set_mixed_non_cash_kind("yape"),
                        class_name=rx.cond(
                            State.payment_mixed_non_cash_kind == "yape",
                            mixed_btn_active,
                            mixed_btn_inactive,
                        ),
                    ),
                    rx.el.button(
                        "Plin",
                        on_click=lambda: State.set_mixed_non_cash_kind("plin"),
                        class_name=rx.cond(
                            State.payment_mixed_non_cash_kind == "plin",
                            mixed_btn_active,
                            mixed_btn_inactive,
                        ),
                    ),
                    rx.el.button(
                        "Transferencia",
                        on_click=lambda: State.set_mixed_non_cash_kind("transfer"),
                        class_name=rx.cond(
                            State.payment_mixed_non_cash_kind == "transfer",
                            mixed_btn_active,
                            mixed_btn_inactive,
                        ),
                    ),
                    class_name="grid grid-cols-2 gap-2",
                ),
                class_name="flex flex-col gap-2",
            ),
            rx.el.div(
                rx.el.label("Monto complemento", class_name="text-xs font-medium text-slate-600"),
                rx.el.div(
                    rx.el.span(State.currency_symbol, class_name="text-slate-400"),
                    rx.el.input(
                        type="number",
                        value=State.payment_mixed_complement,
                        is_disabled=True,
                        class_name="flex-1 border-0 focus:ring-0 text-sm bg-transparent outline-none text-right",
                    ),
                    class_name="flex items-center gap-2 px-3 py-2 border rounded-lg bg-slate-50",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.cond(
                State.payment_mixed_non_cash_kind == "card",
                rx.el.div(
                    rx.el.label("Tipo de tarjeta", class_name="text-xs font-medium text-slate-600"),
                    rx.el.div(
                        rx.el.button(
                            "Credito",
                            on_click=lambda: State.set_card_type("Credito"),
                            class_name=rx.cond(
                                State.payment_card_type == "Credito",
                                mixed_btn_active,
                                mixed_btn_inactive,
                            ),
                        ),
                        rx.el.button(
                            "Debito",
                            on_click=lambda: State.set_card_type("Debito"),
                            class_name=rx.cond(
                                State.payment_card_type == "Debito",
                                mixed_btn_active,
                                mixed_btn_inactive,
                            ),
                        ),
                        class_name="flex gap-2",
                    ),
                    class_name="flex flex-col gap-2",
                ),
                rx.fragment(),
            ),
            rx.cond(
                State.payment_mixed_non_cash_kind == "wallet",
                rx.el.div(
                    rx.el.label("Billetera", class_name="text-xs font-medium text-slate-600"),
                    rx.el.div(
                        rx.el.button(
                            "Yape",
                            on_click=lambda: State.choose_wallet_provider("Yape"),
                            class_name=rx.cond(
                                State.payment_wallet_choice == "Yape",
                                mixed_yape_active,
                                mixed_yape_inactive,
                            ),
                        ),
                        rx.el.button(
                            "Plin",
                            on_click=lambda: State.choose_wallet_provider("Plin"),
                            class_name=rx.cond(
                                State.payment_wallet_choice == "Plin",
                                mixed_plin_active,
                                mixed_plin_inactive,
                            ),
                        ),
                        class_name="flex gap-2",
                    ),
                    class_name="flex flex-col gap-2",
                ),
                rx.fragment(),
            ),
            class_name=mixed_section_class,
        ),
        rx.fragment(),
    )

    # ── Footer: receipt selector + fiscal + total + confirm ─────────────────
    if is_desktop:
        footer = rx.el.div(
            _receipt_type_selector(),
            _fiscal_lookup_input(),
            rx.el.div(
                rx.el.div(
                    rx.el.span("TOTAL", class_name=total_label_class),
                    rx.el.div(
                        rx.el.span(State.currency_symbol, class_name="text-xl text-indigo-600"),
                        rx.el.span(
                            State.sale_total.to_string(),
                            class_name=total_amount_class,
                        ),
                        class_name=total_row_class,
                    ),
                    class_name=total_container_class,
                ),
                class_name="p-3 bg-slate-50",
            ),
            rx.el.div(
                rx.el.button(
                    rx.cond(
                        State.is_loading,
                        rx.hstack(
                            rx.spinner(size="2"),
                            rx.text("Procesando..."),
                            spacing="2",
                        ),
                        rx.hstack(
                            rx.icon("circle-check", class_name="h-5 w-5"),
                            rx.text("Confirmar Venta"),
                            spacing="2",
                        ),
                    ),
                    on_click=State.confirm_sale,
                    disabled=State.is_loading,
                    loading=State.is_loading,
                    class_name=rx.cond(
                        State.is_loading,
                        confirm_loading_class,
                        confirm_active_class,
                    ),
                ),
                rx.fragment(),
                class_name=confirm_wrapper_class,
            ),
            class_name=footer_class,
        )
    else:
        footer = rx.el.div(
            _receipt_type_selector(),
            _fiscal_lookup_input(),
            rx.el.div(
                rx.el.span("TOTAL", class_name=total_label_class),
                rx.el.div(
                    rx.el.span(State.currency_symbol, class_name="text-xl text-indigo-600"),
                    rx.el.span(
                        State.sale_total.to_string(),
                        class_name=total_amount_class,
                    ),
                    class_name=total_row_class,
                ),
                class_name=total_container_class,
            ),
            rx.el.div(
                rx.el.button(
                    rx.cond(
                        State.is_loading,
                        rx.hstack(
                            rx.spinner(size="2"),
                            rx.text("Procesando..."),
                            spacing="2",
                        ),
                        rx.hstack(
                            rx.icon("circle-check", class_name="h-5 w-5"),
                            rx.text("Confirmar Venta"),
                            spacing="2",
                        ),
                    ),
                    on_click=State.confirm_sale,
                    disabled=State.is_loading,
                    loading=State.is_loading,
                    class_name=rx.cond(
                        State.is_loading,
                        confirm_loading_class,
                        confirm_active_class,
                    ),
                ),
                rx.fragment(),
                class_name=confirm_wrapper_class,
            ),
            class_name=footer_class,
        )

    # ── Assemble scrollable body ────────────────────────────────────────────
    if is_desktop:
        scrollable = rx.el.div(
            pm_section,
            rx.divider(class_name="mx-4"),
            rx.el.div(
                credit_header,
                credit_fields,
                class_name=credit_section_class,
            ),
            rx.el.div(
                cash_option,
                card_option,
                wallet_option,
                mixed_option,
                class_name=options_section_class,
            ),
            class_name="flex-1 overflow-y-auto min-h-0",
        )
        return scrollable, footer
    else:
        return (
            pm_section,
            rx.el.div(
                credit_header,
                credit_fields,
                class_name=credit_section_class,
            ),
            cash_option,
            card_option,
            wallet_option,
            mixed_option,
            footer,
        )


def payment_sidebar() -> rx.Component:
    """Sidebar derecho con método de pago y total."""
    scrollable, footer = _payment_form_body("desktop")
    return rx.el.aside(
        # Header
        rx.el.div(
            rx.icon("wallet", class_name="h-5 w-5 text-indigo-600"),
            rx.el.span("COBRO", class_name="font-bold text-slate-800"),
            class_name="flex items-center gap-2 p-4 border-b shrink-0",
        ),
        scrollable,
        footer,
        class_name="w-full max-w-[22rem] bg-white border rounded-lg shadow-sm overflow-hidden flex flex-col h-full",
    )


def payment_mobile_section() -> rx.Component:
    """Sección de pago para móvil y tablet."""
    (
        pm_section,
        credit_section,
        cash_option,
        card_option,
        wallet_option,
        mixed_option,
        footer,
    ) = _payment_form_body("mobile")
    return rx.el.div(
        # Header
        rx.el.div(
            rx.el.div(
                rx.icon("wallet", class_name="h-5 w-5 text-indigo-600"),
                rx.el.span("Cobro", class_name="font-bold text-slate-800"),
                class_name="flex items-center gap-2",
            ),
            class_name="p-3 sm:p-4 border-b",
        ),
        pm_section,
        credit_section,
        cash_option,
        card_option,
        wallet_option,
        mixed_option,
        footer,
        class_name="bg-white rounded-xl border shadow-sm lg:hidden",
    )


def _venta_keyboard_shortcuts() -> rx.Component:
    """Atajos de teclado para Punto de Venta.

    F11         → Abrir modal Movimientos Recientes
    Enter       → Añadir producto (solo si autocomplete cerrado)
    Arrow Up/Down → Navegar sugerencias de autocomplete (preventDefault + scrollIntoView)
    """
    return rx.script(
        """
        (function(){
            if(window.__ventaKbAttached) return;
            window.__ventaKbAttached = true;
            document.addEventListener('keydown', function(e){
                // F11 → abrir modal Movimientos Recientes
                if(e.key === 'F11'){
                    e.preventDefault();
                    e.stopPropagation();
                    var btn = document.querySelector('[data-venta-recent-btn]');
                    if(btn) btn.click();
                    return;
                }

                // Arrow Up/Down → navegar sugerencias de autocomplete
                if(e.key === 'ArrowDown' || e.key === 'ArrowUp'){
                    var el = document.activeElement;
                    if(!el) return;
                    var searchDiv = el.closest('[data-product-search]');
                    if(!searchDiv) return;
                    var dropdown = searchDiv.querySelector('[data-autocomplete-dropdown]');
                    if(!dropdown || dropdown.children.length === 0) return;
                    // Prevenir que el cursor del input se mueva
                    e.preventDefault();
                    // Scroll al elemento seleccionado después del re-render de Reflex
                    setTimeout(function(){
                        if(!dropdown) return;
                        var items = dropdown.querySelectorAll('button');
                        for(var i = 0; i < items.length; i++){
                            // El item seleccionado tiene clase 'bg-indigo-50' (sin hover:)
                            var cls = ' ' + items[i].className + ' ';
                            if(cls.indexOf(' bg-indigo-50 ') > -1){
                                items[i].scrollIntoView({block:'nearest'});
                                break;
                            }
                        }
                    }, 80);
                    return;
                }

                // Enter → añadir producto o seleccionar autocomplete
                if(e.key === 'Enter'){
                    var el = document.activeElement;
                    if(!el) return;
                    var bar = el.closest('[data-quick-add-bar]');
                    if(!bar) return;
                    // No interferir con el form de barcode (tiene su propio on_submit)
                    if(el.id === 'venta_barcode_input') return;
                    // Si el autocomplete está abierto, dejar que Reflex on_key_down
                    // maneje la selección — NO hacer click en añadir
                    var searchDiv = el.closest('[data-product-search]');
                    if(searchDiv){
                        var dropdown = searchDiv.querySelector('[data-autocomplete-dropdown]');
                        if(dropdown && dropdown.children.length > 0) return;
                    }
                    e.preventDefault();
                    var addBtn = document.querySelector('[data-venta-add-btn]');
                    if(addBtn) addBtn.click();
                }
            });
        })();
        """
    )


def venta_page() -> rx.Component:
    """Página principal del punto de venta (POS)."""
    content = rx.el.div(
        _venta_keyboard_shortcuts(),
        # Contenido principal
        rx.el.div(
            rx.cond(
                State.reservation_selected_for_payment != None,
                rx.fragment(),
                rx.el.div(
                    rx.el.div(
                        rx.el.h1(
                            "PUNTO DE VENTA",
                            class_name="text-2xl font-bold text-slate-900 tracking-tight",
                        ),
                        rx.el.p(
                            "Realiza ventas directas, selecciona productos y gestiona el cobro.",
                            class_name="text-sm text-slate-500",
                        ),
                        class_name="flex flex-col gap-1",
                    ),
                    rx.el.button(
                        rx.icon("history", class_name="h-4 w-4"),
                        rx.el.span("Movimientos recientes(F11)"),
                        on_click=State.toggle_recent_modal(True),
                        custom_attrs={"data-venta-recent-btn": "1"},
                        class_name=(
                            "flex items-center gap-2 px-3 py-2 text-sm border border-slate-200 "
                            "rounded-lg text-slate-700 hover:bg-slate-50"
                        ),
                    ),
                    class_name="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4",
                ),
            ),
            # Info de reserva/servicio prominente (si aplica)
            reservation_info_card(),
            client_selector(),
            # Barra de entrada rápida
            sale_products_card(),
            # Pago móvil/tablet
            payment_mobile_section(),
            class_name="flex flex-col flex-1 min-h-0 gap-2 sm:gap-3 p-2.5 sm:p-3 lg:pr-0 overflow-y-auto lg:overflow-hidden",
        ),
        # Sidebar de pago (solo desktop grande)
        rx.el.div(
            payment_sidebar(),
            class_name="hidden lg:block h-[calc(100vh-4rem)] sticky top-16 shrink-0",
        ),
        client_form_modal(),
        recent_moves_modal(),
        sale_receipt_modal(),
        class_name="flex min-h-[calc(100vh-4rem)] lg:h-[calc(100vh-4rem)]",
    )
    return permission_guard(
        has_permission=State.can_view_ventas,
        content=content,
        redirect_message="Acceso denegado a Ventas",
    )
