import reflex as rx
from app.state import State
from app.components.ui import (
    INPUT_STYLES,
)


def compact_sale_item_row(item: rx.Var[dict]) -> rx.Component:
    """Fila compacta para la tabla de productos en venta (desktop)."""
    return rx.el.tr(
        rx.el.td(
            item["barcode"],
            class_name="py-2 px-3 text-xs text-gray-500 font-mono hidden md:table-cell",
        ),
        rx.el.td(
            item["description"],
            class_name="py-2 px-3 text-sm font-medium text-gray-800",
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
                class_name="p-1 text-red-500 hover:bg-red-50 rounded transition-colors",
            ),
            class_name="py-2 px-2 text-center",
        ),
        class_name="border-b border-gray-100 hover:bg-gray-50 transition-colors",
    )


def mobile_sale_item_card(item: rx.Var[dict]) -> rx.Component:
    """Card de producto para móvil."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.span(item["description"], class_name="font-medium text-gray-800"),
                rx.el.span(item["barcode"], class_name="text-xs text-gray-400 font-mono"),
                class_name="flex flex-col",
            ),
            rx.el.button(
                rx.icon("x", class_name="h-4 w-4"),
                on_click=lambda: State.remove_item_from_sale(item["temp_id"]),
                class_name="p-1.5 text-red-500 hover:bg-red-50 rounded-full transition-colors",
            ),
            class_name="flex items-start justify-between gap-2",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span("Cant:", class_name="text-xs text-gray-500"),
                rx.el.span(item["quantity"].to_string(), class_name="font-medium"),
                class_name="flex items-center gap-1",
            ),
            rx.el.div(
                rx.el.span("Precio:", class_name="text-xs text-gray-500"),
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
        class_name="p-3 bg-white border-b border-gray-100",
    )


def quick_add_bar() -> rx.Component:
    """Barra de entrada rápida de productos - estilo POS responsive."""
    return rx.el.div(
        # Fila 1: Código de barra y Búsqueda (siempre visible)
        rx.el.div(
            # Código de barra
            rx.el.div(
                rx.icon("scan-barcode", class_name="h-5 w-5 text-gray-400 flex-shrink-0"),
                rx.el.input(
                    id="venta_barcode_input",
                    key=State.sale_form_key.to_string(),
                    default_value=State.new_sale_item["barcode"],
                    on_change=lambda val: State.handle_sale_change("barcode", val),
                    placeholder="Código...",
                    on_blur=lambda e: State.process_sale_barcode_from_input(e),
                    on_key_down=lambda k: State.handle_key_down(k),
                    class_name="flex-1 min-w-0 border-0 focus:ring-0 text-sm bg-transparent outline-none",
                    type="text",
                    auto_complete="off",
                ),
                class_name="flex items-center gap-2 px-3 py-2.5 border rounded-lg bg-white focus-within:ring-2 focus-within:ring-indigo-500 w-full sm:w-48 lg:w-56",
            ),
            # Búsqueda de producto
            rx.el.div(
                rx.el.div(
                    rx.icon("search", class_name="h-5 w-5 text-gray-400 flex-shrink-0"),
                    rx.el.input(
                        placeholder="Buscar producto...",
                        value=State.new_sale_item["description"],
                        on_change=lambda val: State.handle_sale_change("description", val),
                        class_name="flex-1 min-w-0 border-0 focus:ring-0 text-sm bg-transparent outline-none",
                    ),
                    class_name="flex items-center gap-2 px-3 py-2.5 border rounded-lg bg-white focus-within:ring-2 focus-within:ring-indigo-500 w-full",
                ),
                rx.cond(
                    State.autocomplete_suggestions.length() > 0,
                    rx.el.div(
                        rx.foreach(
                            State.autocomplete_suggestions,
                            lambda suggestion: rx.el.button(
                                suggestion,
                                on_click=lambda _, s=suggestion: State.select_product_for_sale(s),
                                class_name="w-full text-left px-3 py-2.5 hover:bg-indigo-50 text-sm border-b border-gray-100 last:border-0",
                            ),
                        ),
                        class_name="absolute z-20 left-0 right-0 mt-1 bg-white border rounded-lg shadow-xl max-h-60 overflow-y-auto",
                    ),
                    rx.fragment(),
                ),
                class_name="relative flex-1 min-w-0",
            ),
            class_name="flex flex-col sm:flex-row gap-2 flex-1",
        ),
        # Fila 2: Cantidad, Precio, Subtotal y Botón
        rx.el.div(
            # Cantidad
            rx.el.div(
                rx.el.label("Cant.", class_name="text-xs text-gray-500 sm:hidden"),
                rx.el.input(
                    type="number",
                    min="0.01",
                    step="0.01",
                    value=State.new_sale_item["quantity"].to_string(),
                    on_change=lambda val: State.handle_sale_change("quantity", val),
                    class_name="w-full px-3 py-2.5 border rounded-lg text-sm text-center focus:ring-2 focus:ring-indigo-500",
                    placeholder="1",
                ),
                class_name="flex flex-col gap-1 w-16 sm:w-20",
            ),
            # Precio
            rx.el.div(
                rx.el.label("Precio", class_name="text-xs text-gray-500 sm:hidden"),
                rx.el.div(
                    rx.el.span(State.currency_symbol, class_name="text-gray-400 text-sm"),
                    rx.el.input(
                        type="number",
                        min="0",
                        step="0.01",
                        value=State.new_sale_item["price"].to_string(),
                        on_change=lambda val: State.handle_sale_change("price", val),
                        class_name="flex-1 min-w-0 border-0 focus:ring-0 text-sm bg-transparent outline-none text-right",
                    ),
                    class_name="flex items-center gap-1 px-3 py-2.5 border rounded-lg bg-white focus-within:ring-2 focus-within:ring-indigo-500",
                ),
                class_name="flex flex-col gap-1 w-20 sm:w-24",
            ),
            # Subtotal
            rx.el.div(
                rx.el.label("Subtotal", class_name="text-xs text-gray-500 sm:hidden"),
                rx.el.div(
                    rx.el.span(
                        State.currency_symbol,
                        State.sale_subtotal.to_string(),
                        class_name="text-sm font-semibold text-indigo-600",
                    ),
                    class_name="px-3 py-2.5 bg-gray-100 rounded-lg text-right h-[42px] flex items-center justify-end",
                ),
                class_name="flex flex-col gap-1 w-20 sm:w-24",
            ),
            # Botón añadir
            rx.el.button(
                rx.icon("plus", class_name="h-5 w-5"),
                rx.el.span("Añadir", class_name="sm:hidden"),
                on_click=State.add_item_to_sale,
                class_name="px-4 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 h-[42px] flex-1 sm:flex-none sm:w-auto self-end",
            ),
            class_name="flex items-end gap-2",
        ),
        class_name="flex flex-col gap-3 p-3 bg-gray-50 border-b",
    )


def products_table() -> rx.Component:
    """Tabla de productos en la venta - responsive."""
    return rx.el.div(
        # Header
        rx.el.div(
            rx.el.div(
                rx.icon("shopping-cart", class_name="h-5 w-5 text-indigo-600"),
                rx.el.span("Productos", class_name="font-semibold text-gray-800 sm:hidden"),
                rx.el.span("Productos en Venta", class_name="font-semibold text-gray-800 hidden sm:inline"),
                rx.el.span(
                    "(", State.new_sale_items.length().to_string(), ")",
                    class_name="text-sm text-gray-500",
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.button(
                rx.icon("trash-2", class_name="h-4 w-4"),
                rx.el.span("Vaciar", class_name="hidden sm:inline"),
                on_click=State.clear_sale_items,
                class_name="flex items-center gap-1 px-2 sm:px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors",
            ),
            class_name="flex items-center justify-between p-3 bg-white border-b",
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
                                rx.el.th("Código", class_name="py-2 px-3 text-left text-xs font-medium text-gray-500 uppercase hidden md:table-cell"),
                                rx.el.th("Producto", class_name="py-2 px-3 text-left text-xs font-medium text-gray-500 uppercase"),
                                rx.el.th("Cant.", class_name="py-2 px-3 text-center text-xs font-medium text-gray-500 uppercase"),
                                rx.el.th("Precio", class_name="py-2 px-3 text-right text-xs font-medium text-gray-500 uppercase hidden sm:table-cell"),
                                rx.el.th("Subtotal", class_name="py-2 px-3 text-right text-xs font-medium text-gray-500 uppercase"),
                                rx.el.th("", class_name="py-2 px-3 w-10"),
                                class_name="bg-gray-50 border-b",
                            ),
                        ),
                        rx.el.tbody(
                            rx.foreach(State.new_sale_items, compact_sale_item_row),
                        ),
                        class_name="w-full hidden sm:table",
                    ),
                ),
                rx.el.div(
                    rx.icon("package-open", class_name="h-10 w-10 sm:h-12 sm:w-12 text-gray-300"),
                    rx.el.p("No hay productos", class_name="text-gray-500 font-medium"),
                    rx.el.p("Escanea un código o busca un producto", class_name="text-xs sm:text-sm text-gray-400"),
                    class_name="flex flex-col items-center justify-center py-8 sm:py-12 text-center",
                ),
            ),
            class_name="flex-1 overflow-y-auto",
        ),
        class_name="flex flex-col bg-white rounded-lg border shadow-sm flex-1 min-h-0",
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
                        rx.el.span("Cobro de Servicio", class_name="font-bold text-gray-800"),
                        rx.el.span("Alquiler de Campo", class_name="text-sm text-gray-500"),
                        class_name="flex flex-col",
                    ),
                    class_name="flex items-center gap-3",
                ),
                # Botón cerrar para limpiar la reserva pendiente
                rx.el.button(
                    rx.icon("x", class_name="h-5 w-5"),
                    on_click=State.clear_pending_reservation,
                    title="Cerrar cobro de servicio",
                    class_name="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors",
                ),
                class_name="flex items-center justify-between",
            ),
            # Datos del cliente y reserva
            rx.el.div(
                # Columna 1: Cliente
                rx.el.div(
                    rx.el.div(
                        rx.icon("user", class_name="h-4 w-4 text-gray-400"),
                        rx.el.span("Cliente", class_name="text-xs text-gray-500 uppercase"),
                        class_name="flex items-center gap-1",
                    ),
                    rx.el.span(
                        State.reservation_selected_for_payment["client_name"],
                        class_name="font-semibold text-gray-800",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                # Columna 2: Campo
                rx.el.div(
                    rx.el.div(
                        rx.icon("map-pin", class_name="h-4 w-4 text-gray-400"),
                        rx.el.span("Campo", class_name="text-xs text-gray-500 uppercase"),
                        class_name="flex items-center gap-1",
                    ),
                    rx.el.span(
                        State.reservation_selected_for_payment["field_name"],
                        class_name="font-semibold text-gray-800",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                # Columna 3: Horario
                rx.el.div(
                    rx.el.div(
                        rx.icon("clock", class_name="h-4 w-4 text-gray-400"),
                        rx.el.span("Horario", class_name="text-xs text-gray-500 uppercase"),
                        class_name="flex items-center gap-1",
                    ),
                    rx.el.span(
                        State.reservation_selected_for_payment["start_datetime"],
                        class_name="font-semibold text-gray-800 text-sm",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                # Columna 4: Teléfono
                rx.el.div(
                    rx.el.div(
                        rx.icon("phone", class_name="h-4 w-4 text-gray-400"),
                        rx.el.span("Teléfono", class_name="text-xs text-gray-500 uppercase"),
                        class_name="flex items-center gap-1",
                    ),
                    rx.el.span(
                        State.reservation_selected_for_payment["phone"],
                        class_name="font-semibold text-gray-800",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4",
            ),
            # Resumen de montos
            rx.el.div(
                rx.el.div(
                    rx.el.span("Total Reserva", class_name="text-sm text-gray-600"),
                    rx.el.span(
                        State.currency_symbol,
                        State.reservation_selected_for_payment["total_amount"].to_string(),
                        class_name="text-lg font-bold text-gray-800",
                    ),
                    class_name="flex flex-col items-center p-3 bg-gray-50 rounded-lg",
                ),
                rx.el.div(
                    rx.el.span("Adelanto Pagado", class_name="text-sm text-gray-600"),
                    rx.el.span(
                        State.currency_symbol,
                        State.reservation_selected_for_payment["advance_amount"].to_string(),
                        class_name="text-lg font-bold text-emerald-600",
                    ),
                    class_name="flex flex-col items-center p-3 bg-emerald-50 rounded-lg",
                ),
                rx.el.div(
                    rx.el.span("Saldo a Cobrar", class_name="text-sm text-gray-600"),
                    rx.el.span(
                        State.currency_symbol,
                        State.selected_reservation_balance.to_string(),
                        class_name="text-2xl font-bold text-indigo-600",
                    ),
                    class_name="flex flex-col items-center p-3 bg-indigo-50 rounded-lg border-2 border-indigo-200",
                ),
                class_name="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4",
            ),
            class_name="bg-white border-2 border-emerald-200 rounded-xl p-4 shadow-sm",
        ),
        rx.fragment(),
    )


def payment_sidebar() -> rx.Component:
    """Sidebar derecho con método de pago y total."""
    return rx.el.aside(
        # Header
        rx.el.div(
            rx.icon("wallet", class_name="h-5 w-5 text-indigo-600"),
            rx.el.span("Cobro", class_name="font-bold text-gray-800"),
            class_name="flex items-center gap-2 p-4 border-b",
        ),
        # Métodos de pago
        rx.el.div(
            rx.el.p("Método de pago", class_name="text-xs font-medium text-gray-500 uppercase mb-2"),
            rx.el.div(
                rx.foreach(
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
                        rx.el.span(method["name"], class_name="text-xs uppercase font-medium"),
                        on_click=lambda _, mid=method["id"]: State.select_payment_method(mid),
                        class_name=rx.cond(
                            State.payment_method == method["name"],
                            "flex items-center gap-2 px-3 py-2 rounded-lg bg-indigo-600 text-white w-full justify-center",
                            "flex items-center gap-2 px-3 py-2 rounded-lg border bg-white text-gray-700 hover:bg-gray-50 w-full justify-center",
                        ),
                    ),
                ),
                class_name="grid grid-cols-2 gap-2",
            ),
            class_name="p-4 border-b",
        ),
        # Opciones según método
        rx.el.div(
            rx.cond(
                State.payment_method_kind == "cash",
                rx.el.div(
                    rx.el.label("Monto recibido", class_name="text-xs font-medium text-gray-600"),
                    rx.el.div(
                        rx.el.span(State.currency_symbol, class_name="text-gray-400"),
                        rx.el.input(
                            type="number",
                            value=rx.cond(
                                State.payment_cash_amount > 0,
                                State.payment_cash_amount.to_string(),
                                "",
                            ),
                            on_change=lambda value: State.set_cash_amount(value),
                            class_name="flex-1 border-0 focus:ring-0 text-lg font-semibold bg-transparent outline-none text-right",
                            placeholder="0.00",
                        ),
                        class_name="flex items-center gap-2 px-3 py-2 border rounded-lg bg-white focus-within:ring-2 focus-within:ring-indigo-500",
                    ),
                    rx.cond(
                        State.payment_cash_message != "",
                        rx.el.p(
                            State.payment_cash_message,
                            class_name=rx.cond(
                                State.payment_cash_status == "change",
                                "text-sm font-semibold text-emerald-600 mt-2",
                                rx.cond(
                                    State.payment_cash_status == "due",
                                    "text-sm font-semibold text-red-600 mt-2",
                                    "text-sm text-gray-500 mt-2",
                                ),
                            ),
                        ),
                        rx.fragment(),
                    ),
                    class_name="flex flex-col gap-2",
                ),
                rx.fragment(),
            ),
            rx.cond(
                State.payment_method_kind == "card",
                rx.el.div(
                    rx.el.label("Tipo de tarjeta", class_name="text-xs font-medium text-gray-600"),
                    rx.el.div(
                        rx.el.button(
                            "Crédito",
                            on_click=lambda: State.set_card_type("Credito"),
                            class_name=rx.cond(
                                State.payment_card_type == "Credito",
                                "flex-1 px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium",
                                "flex-1 px-3 py-2 rounded-lg border text-gray-700 text-sm hover:bg-gray-50",
                            ),
                        ),
                        rx.el.button(
                            "Débito",
                            on_click=lambda: State.set_card_type("Debito"),
                            class_name=rx.cond(
                                State.payment_card_type == "Debito",
                                "flex-1 px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium",
                                "flex-1 px-3 py-2 rounded-lg border text-gray-700 text-sm hover:bg-gray-50",
                            ),
                        ),
                        class_name="flex gap-2",
                    ),
                    class_name="flex flex-col gap-2",
                ),
                rx.fragment(),
            ),
            rx.cond(
                State.payment_method_kind == "wallet",
                rx.el.div(
                    rx.el.label("Billetera", class_name="text-xs font-medium text-gray-600"),
                    rx.el.div(
                        rx.el.button(
                            "Yape",
                            on_click=lambda: State.choose_wallet_provider("Yape"),
                            class_name=rx.cond(
                                State.payment_wallet_choice == "Yape",
                                "flex-1 px-3 py-2 rounded-lg bg-purple-600 text-white text-sm font-medium",
                                "flex-1 px-3 py-2 rounded-lg border text-gray-700 text-sm hover:bg-gray-50",
                            ),
                        ),
                        rx.el.button(
                            "Plin",
                            on_click=lambda: State.choose_wallet_provider("Plin"),
                            class_name=rx.cond(
                                State.payment_wallet_choice == "Plin",
                                "flex-1 px-3 py-2 rounded-lg bg-teal-600 text-white text-sm font-medium",
                                "flex-1 px-3 py-2 rounded-lg border text-gray-700 text-sm hover:bg-gray-50",
                            ),
                        ),
                        class_name="flex gap-2",
                    ),
                    class_name="flex flex-col gap-2",
                ),
                rx.fragment(),
            ),
            rx.cond(
                State.payment_method_kind == "mixed",
                rx.el.div(
                    rx.el.div(
                        rx.el.label("Efectivo", class_name="text-xs font-medium text-gray-600"),
                        rx.el.input(
                            type="number",
                            value=rx.cond(
                                State.payment_mixed_cash > 0,
                                State.payment_mixed_cash.to_string(),
                                "",
                            ),
                            on_change=lambda value: State.set_mixed_cash_amount(value),
                            class_name="w-full px-3 py-2 border rounded-lg text-sm",
                            placeholder="0.00",
                        ),
                        class_name="flex flex-col gap-1",
                    ),
                rx.el.div(
                    rx.el.label("Complemento", class_name="text-xs font-medium text-gray-600"),
                    rx.el.div(
                        rx.el.button(
                            "T. Débito",
                            on_click=lambda: State.set_mixed_non_cash_kind("debit"),
                            class_name=rx.cond(
                                State.payment_mixed_non_cash_kind == "debit",
                                "flex-1 px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium",
                                "flex-1 px-3 py-2 rounded-lg border text-gray-700 text-sm hover:bg-gray-50",
                            ),
                        ),
                        rx.el.button(
                            "T. Crédito",
                            on_click=lambda: State.set_mixed_non_cash_kind("credit"),
                            class_name=rx.cond(
                                State.payment_mixed_non_cash_kind == "credit",
                                "flex-1 px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium",
                                "flex-1 px-3 py-2 rounded-lg border text-gray-700 text-sm hover:bg-gray-50",
                            ),
                        ),
                        rx.el.button(
                            "Yape",
                            on_click=lambda: State.set_mixed_non_cash_kind("yape"),
                            class_name=rx.cond(
                                State.payment_mixed_non_cash_kind == "yape",
                                "flex-1 px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium",
                                "flex-1 px-3 py-2 rounded-lg border text-gray-700 text-sm hover:bg-gray-50",
                            ),
                        ),
                        rx.el.button(
                            "Plin",
                            on_click=lambda: State.set_mixed_non_cash_kind("plin"),
                            class_name=rx.cond(
                                State.payment_mixed_non_cash_kind == "plin",
                                "flex-1 px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium",
                                "flex-1 px-3 py-2 rounded-lg border text-gray-700 text-sm hover:bg-gray-50",
                            ),
                        ),
                        rx.el.button(
                            "Transferencia",
                            on_click=lambda: State.set_mixed_non_cash_kind("transfer"),
                            class_name=rx.cond(
                                State.payment_mixed_non_cash_kind == "transfer",
                                "flex-1 px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium",
                                "flex-1 px-3 py-2 rounded-lg border text-gray-700 text-sm hover:bg-gray-50",
                            ),
                        ),
                        class_name="grid grid-cols-2 gap-2",
                    ),
                    class_name="flex flex-col gap-2",
                ),
                    rx.el.div(
                        rx.el.label("Monto complemento", class_name="text-xs font-medium text-gray-600"),
                        rx.el.div(
                            rx.el.span(State.currency_symbol, class_name="text-gray-400"),
                            rx.el.input(
                                type="number",
                                value=State.payment_mixed_complement,
                                is_disabled=True,
                                class_name="flex-1 border-0 focus:ring-0 text-sm bg-transparent outline-none text-right",
                            ),
                            class_name="flex items-center gap-2 px-3 py-2 border rounded-lg bg-gray-50",
                        ),
                        class_name="flex flex-col gap-1",
                    ),
                    rx.cond(
                        State.payment_mixed_non_cash_kind == "card",
                        rx.el.div(
                            rx.el.label("Tipo de tarjeta", class_name="text-xs font-medium text-gray-600"),
                            rx.el.div(
                                rx.el.button(
                                    "Credito",
                                    on_click=lambda: State.set_card_type("Credito"),
                                    class_name=rx.cond(
                                        State.payment_card_type == "Credito",
                                        "flex-1 px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium",
                                        "flex-1 px-3 py-2 rounded-lg border text-gray-700 text-sm hover:bg-gray-50",
                                    ),
                                ),
                                rx.el.button(
                                    "Debito",
                                    on_click=lambda: State.set_card_type("Debito"),
                                    class_name=rx.cond(
                                        State.payment_card_type == "Debito",
                                        "flex-1 px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium",
                                        "flex-1 px-3 py-2 rounded-lg border text-gray-700 text-sm hover:bg-gray-50",
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
                            rx.el.label("Billetera", class_name="text-xs font-medium text-gray-600"),
                            rx.el.div(
                                rx.el.button(
                                    "Yape",
                                    on_click=lambda: State.choose_wallet_provider("Yape"),
                                    class_name=rx.cond(
                                        State.payment_wallet_choice == "Yape",
                                        "flex-1 px-3 py-2 rounded-lg bg-purple-600 text-white text-sm font-medium",
                                        "flex-1 px-3 py-2 rounded-lg border text-gray-700 text-sm hover:bg-gray-50",
                                    ),
                                ),
                                rx.el.button(
                                    "Plin",
                                    on_click=lambda: State.choose_wallet_provider("Plin"),
                                    class_name=rx.cond(
                                        State.payment_wallet_choice == "Plin",
                                        "flex-1 px-3 py-2 rounded-lg bg-teal-600 text-white text-sm font-medium",
                                        "flex-1 px-3 py-2 rounded-lg border text-gray-700 text-sm hover:bg-gray-50",
                                    ),
                                ),
                                class_name="flex gap-2",
                            ),
                            class_name="flex flex-col gap-2",
                        ),
                        rx.fragment(),
                    ),
                    class_name="flex flex-col gap-3",
                ),
                rx.fragment(),
            ),
            class_name="p-4 border-b min-h-[80px]",
        ),
        # Total
        rx.el.div(
            rx.el.div(
                rx.el.span("TOTAL", class_name="text-xs font-medium text-gray-500"),
                rx.el.div(
                    rx.el.span(State.currency_symbol, class_name="text-xl text-indigo-600"),
                    rx.el.span(
                        State.sale_total.to_string(),
                        class_name="text-3xl font-bold text-indigo-600",
                    ),
                    class_name="flex items-baseline gap-1",
                ),
                class_name="flex flex-col items-center py-3",
            ),
            class_name="p-3 bg-gray-50",
        ),
        # Botones de acción
        rx.el.div(
            rx.el.button(
                rx.icon("circle-check", class_name="h-5 w-5"),
                "Confirmar Venta",
                on_click=State.confirm_sale,
                class_name="w-full flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700 transition-colors text-lg",
            ),
            rx.cond(
                State.sale_receipt_ready,
                rx.el.button(
                    rx.icon("printer", class_name="h-4 w-4"),
                    "Imprimir",
                    on_click=State.print_sale_receipt,
                    class_name="w-full flex items-center justify-center gap-2 px-4 py-2 border-2 border-indigo-600 text-indigo-600 rounded-lg font-medium hover:bg-indigo-50 transition-colors",
                ),
                rx.el.button(
                    rx.icon("printer", class_name="h-4 w-4"),
                    "Imprimir",
                    disabled=True,
                    class_name="w-full flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 text-gray-400 rounded-lg cursor-not-allowed",
                ),
            ),
            class_name="p-4 flex flex-col gap-2 mt-auto",
        ),
        class_name="w-80 bg-white border-l flex flex-col h-full",
    )


def payment_mobile_section() -> rx.Component:
    """Sección de pago para móvil y tablet."""
    return rx.el.div(
        # Header
        rx.el.div(
            rx.el.div(
                rx.icon("wallet", class_name="h-5 w-5 text-indigo-600"),
                rx.el.span("Cobro", class_name="font-bold text-gray-800"),
                class_name="flex items-center gap-2",
            ),
            class_name="p-3 sm:p-4 border-b",
        ),
        # Métodos de pago - grid responsive
        rx.el.div(
            rx.foreach(
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
                    rx.el.span(method["name"], class_name="uppercase text-xs sm:text-sm font-medium"),
                    on_click=lambda _, mid=method["id"]: State.select_payment_method(mid),
                    class_name=rx.cond(
                        State.payment_method == method["name"],
                        "flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-indigo-600 text-white",
                        "flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
                    ),
                ),
            ),
            class_name="grid grid-cols-2 sm:grid-cols-4 gap-2 p-3 sm:p-4",
        ),
        # Opciones según método - solo efectivo por ahora en móvil
        rx.cond(
            State.payment_method_kind == "cash",
            rx.el.div(
                rx.el.label("Monto recibido", class_name="text-sm font-medium text-gray-700"),
                rx.el.div(
                    rx.el.span(State.currency_symbol, class_name="text-gray-400 text-lg"),
                    rx.el.input(
                        type="number",
                        value=rx.cond(
                            State.payment_cash_amount > 0,
                            State.payment_cash_amount.to_string(),
                            "",
                        ),
                        on_change=lambda value: State.set_cash_amount(value),
                        class_name="flex-1 border-0 focus:ring-0 text-xl font-semibold bg-transparent outline-none text-right",
                        placeholder="0.00",
                    ),
                    class_name="flex items-center gap-2 px-3 py-3 border rounded-lg bg-white focus-within:ring-2 focus-within:ring-indigo-500",
                ),
                rx.cond(
                    State.payment_cash_message != "",
                    rx.el.p(
                        State.payment_cash_message,
                        class_name=rx.cond(
                            State.payment_cash_status == "change",
                            "text-sm font-semibold text-emerald-600 mt-1",
                            "text-sm font-semibold text-red-600 mt-1",
                        ),
                    ),
                    rx.fragment(),
                ),
                class_name="flex flex-col gap-2 px-3 sm:px-4 pb-3",
            ),
            rx.fragment(),
        ),
        rx.cond(
            State.payment_method_kind == "card",
            rx.el.div(
                rx.el.label("Tipo de tarjeta", class_name="text-sm font-medium text-gray-700"),
                rx.el.div(
                    rx.el.button(
                        "Crédito",
                        on_click=lambda: State.set_card_type("Credito"),
                        class_name=rx.cond(
                            State.payment_card_type == "Credito",
                            "flex-1 px-3 py-2.5 rounded-lg bg-indigo-600 text-white font-medium",
                            "flex-1 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
                        ),
                    ),
                    rx.el.button(
                        "Débito",
                        on_click=lambda: State.set_card_type("Debito"),
                        class_name=rx.cond(
                            State.payment_card_type == "Debito",
                            "flex-1 px-3 py-2.5 rounded-lg bg-indigo-600 text-white font-medium",
                            "flex-1 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
                        ),
                    ),
                    class_name="flex gap-2",
                ),
                class_name="flex flex-col gap-2 px-3 sm:px-4 pb-3",
            ),
            rx.fragment(),
        ),
        rx.cond(
            State.payment_method_kind == "wallet",
            rx.el.div(
                rx.el.label("Billetera digital", class_name="text-sm font-medium text-gray-700"),
                rx.el.div(
                    rx.el.button(
                        "Yape",
                        on_click=lambda: State.choose_wallet_provider("Yape"),
                        class_name=rx.cond(
                            State.payment_wallet_choice == "Yape",
                            "flex-1 px-3 py-2.5 rounded-lg bg-purple-600 text-white font-medium",
                            "flex-1 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
                        ),
                    ),
                    rx.el.button(
                        "Plin",
                        on_click=lambda: State.choose_wallet_provider("Plin"),
                        class_name=rx.cond(
                            State.payment_wallet_choice == "Plin",
                            "flex-1 px-3 py-2.5 rounded-lg bg-teal-600 text-white font-medium",
                            "flex-1 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
                        ),
                    ),
                    class_name="flex gap-2",
                ),
                class_name="flex flex-col gap-2 px-3 sm:px-4 pb-3",
            ),
            rx.fragment(),
        ),
        rx.cond(
            State.payment_method_kind == "mixed",
            rx.el.div(
                rx.el.div(
                    rx.el.label("Efectivo", class_name="text-xs font-medium text-gray-600"),
                    rx.el.input(
                        type="number",
                        value=rx.cond(
                            State.payment_mixed_cash > 0,
                            State.payment_mixed_cash.to_string(),
                            "",
                        ),
                        on_change=lambda value: State.set_mixed_cash_amount(value),
                        class_name="w-full px-3 py-2 border rounded-lg text-sm",
                        placeholder="0.00",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label("Complemento", class_name="text-xs font-medium text-gray-600"),
                    rx.el.div(
                        rx.el.button(
                            "T. Débito",
                            on_click=lambda: State.set_mixed_non_cash_kind("debit"),
                            class_name=rx.cond(
                                State.payment_mixed_non_cash_kind == "debit",
                                "flex-1 px-3 py-2.5 rounded-lg bg-indigo-600 text-white font-medium",
                                "flex-1 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
                            ),
                        ),
                        rx.el.button(
                            "T. Crédito",
                            on_click=lambda: State.set_mixed_non_cash_kind("credit"),
                            class_name=rx.cond(
                                State.payment_mixed_non_cash_kind == "credit",
                                "flex-1 px-3 py-2.5 rounded-lg bg-indigo-600 text-white font-medium",
                                "flex-1 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
                            ),
                        ),
                        rx.el.button(
                            "Yape",
                            on_click=lambda: State.set_mixed_non_cash_kind("yape"),
                            class_name=rx.cond(
                                State.payment_mixed_non_cash_kind == "yape",
                                "flex-1 px-3 py-2.5 rounded-lg bg-indigo-600 text-white font-medium",
                                "flex-1 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
                            ),
                        ),
                        rx.el.button(
                            "Plin",
                            on_click=lambda: State.set_mixed_non_cash_kind("plin"),
                            class_name=rx.cond(
                                State.payment_mixed_non_cash_kind == "plin",
                                "flex-1 px-3 py-2.5 rounded-lg bg-indigo-600 text-white font-medium",
                                "flex-1 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
                            ),
                        ),
                        rx.el.button(
                            "Transferencia",
                            on_click=lambda: State.set_mixed_non_cash_kind("transfer"),
                            class_name=rx.cond(
                                State.payment_mixed_non_cash_kind == "transfer",
                                "flex-1 px-3 py-2.5 rounded-lg bg-indigo-600 text-white font-medium",
                                "flex-1 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
                            ),
                        ),
                        class_name="grid grid-cols-2 gap-2",
                    ),
                    class_name="flex flex-col gap-2",
                ),
                rx.el.div(
                    rx.el.label("Monto complemento", class_name="text-xs font-medium text-gray-600"),
                    rx.el.div(
                        rx.el.span(State.currency_symbol, class_name="text-gray-400"),
                        rx.el.input(
                            type="number",
                            value=State.payment_mixed_complement,
                            is_disabled=True,
                            class_name="flex-1 border-0 focus:ring-0 text-sm bg-transparent outline-none text-right",
                        ),
                        class_name="flex items-center gap-2 px-3 py-2 border rounded-lg bg-gray-50",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.cond(
                    State.payment_mixed_non_cash_kind == "card",
                    rx.el.div(
                        rx.el.label("Tipo de tarjeta", class_name="text-xs font-medium text-gray-600"),
                        rx.el.div(
                            rx.el.button(
                                "Credito",
                                on_click=lambda: State.set_card_type("Credito"),
                                class_name=rx.cond(
                                    State.payment_card_type == "Credito",
                                    "flex-1 px-3 py-2.5 rounded-lg bg-indigo-600 text-white font-medium",
                                    "flex-1 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
                                ),
                            ),
                            rx.el.button(
                                "Debito",
                                on_click=lambda: State.set_card_type("Debito"),
                                class_name=rx.cond(
                                    State.payment_card_type == "Debito",
                                    "flex-1 px-3 py-2.5 rounded-lg bg-indigo-600 text-white font-medium",
                                    "flex-1 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
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
                        rx.el.label("Billetera", class_name="text-xs font-medium text-gray-600"),
                        rx.el.div(
                            rx.el.button(
                                "Yape",
                                on_click=lambda: State.choose_wallet_provider("Yape"),
                                class_name=rx.cond(
                                    State.payment_wallet_choice == "Yape",
                                    "flex-1 px-3 py-2.5 rounded-lg bg-purple-600 text-white font-medium",
                                    "flex-1 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
                                ),
                            ),
                            rx.el.button(
                                "Plin",
                                on_click=lambda: State.choose_wallet_provider("Plin"),
                                class_name=rx.cond(
                                    State.payment_wallet_choice == "Plin",
                                    "flex-1 px-3 py-2.5 rounded-lg bg-teal-600 text-white font-medium",
                                    "flex-1 px-3 py-2.5 rounded-lg border text-gray-700 hover:bg-gray-50",
                                ),
                            ),
                            class_name="flex gap-2",
                        ),
                        class_name="flex flex-col gap-2",
                    ),
                    rx.fragment(),
                ),
                class_name="flex flex-col gap-3 px-3 sm:px-4 pb-3",
            ),
            rx.fragment(),
        ),
        # Total y botones
        rx.el.div(
            rx.el.div(
                rx.el.span("TOTAL", class_name="text-sm font-medium text-gray-500"),
                rx.el.div(
                    rx.el.span(State.currency_symbol, class_name="text-xl text-indigo-600"),
                    rx.el.span(
                        State.sale_total.to_string(),
                        class_name="text-3xl sm:text-4xl font-bold text-indigo-600",
                    ),
                    class_name="flex items-baseline gap-0.5",
                ),
                class_name="flex flex-col items-center",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("circle-check", class_name="h-5 w-5"),
                    "Confirmar Venta",
                    on_click=State.confirm_sale,
                    class_name="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700",
                ),
                rx.cond(
                    State.sale_receipt_ready,
                    rx.el.button(
                        rx.icon("printer", class_name="h-4 w-4"),
                        on_click=State.print_sale_receipt,
                        class_name="px-4 py-3 border-2 border-indigo-600 text-indigo-600 rounded-lg hover:bg-indigo-50",
                    ),
                    rx.fragment(),
                ),
                class_name="flex gap-2 mt-3",
            ),
            class_name="p-3 sm:p-4 bg-gray-50 border-t",
        ),
        class_name="bg-white rounded-lg border shadow-sm lg:hidden",
    )


def venta_page() -> rx.Component:
    return rx.el.div(
        # Contenido principal
        rx.el.div(
            # Info de reserva/servicio prominente (si aplica)
            reservation_info_card(),
            # Barra de entrada rápida
            quick_add_bar(),
            # Tabla de productos
            products_table(),
            # Pago móvil/tablet
            payment_mobile_section(),
            class_name="flex flex-col flex-1 min-h-0 gap-3 sm:gap-4 p-3 sm:p-4 lg:pr-0 overflow-y-auto lg:overflow-hidden",
        ),
        # Sidebar de pago (solo desktop grande)
        rx.el.div(
            payment_sidebar(),
            class_name="hidden lg:block h-[calc(100vh-4rem)] sticky top-16",
        ),
        class_name="flex min-h-[calc(100vh-4rem)] lg:h-[calc(100vh-4rem)]",
    )
