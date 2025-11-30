import reflex as rx
from app.state import State


def sale_item_row(item: rx.Var[dict]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(item["barcode"], class_name="py-3 px-4"),
        rx.el.td(item["description"], class_name="py-3 px-4"),
        rx.el.td(item["quantity"].to_string(), class_name="py-3 px-4 text-center"),
        rx.el.td(item["unit"], class_name="py-3 px-4 text-center"),
        rx.el.td(
            State.currency_symbol,
            item["price"].to_string(),
            class_name="py-3 px-4 text-right",
        ),
        rx.el.td(
            State.currency_symbol,
            item["subtotal"].to_string(),
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


def field_rental_sale_section() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h2(
                "Alquiler de Campo",
                class_name="text-lg font-semibold text-gray-700",
            ),
            rx.el.p(
                "Revisa los datos de la reserva enviada desde Servicios y completa el cobro con los metodos de pago de Venta.",
                class_name="text-sm text-gray-600",
            ),
            class_name="flex flex-col gap-1",
        ),
        rx.cond(
            State.reservation_selected_for_payment == None,
            rx.el.div(
                rx.icon("info", class_name="h-4 w-4 text-gray-500"),
                rx.el.div(
                    rx.el.span("Sin reserva seleccionada", class_name="text-sm font-semibold text-gray-800"),
                    rx.el.span(
                        "Usa el boton Pagar en Reservas registradas para cargar los datos aqui.",
                        class_name="text-sm text-gray-600",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                class_name="flex items-start gap-2 rounded-md border border-dashed border-gray-300 bg-gray-50 p-3",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.label("Cliente", class_name="text-sm font-medium text-gray-700"),
                    rx.el.input(
                        value=State.reservation_selected_for_payment["client_name"],
                        is_disabled=True,
                        class_name="w-full p-2 border rounded-md bg-gray-100",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label("Telefono", class_name="text-sm font-medium text-gray-700"),
                    rx.el.input(
                        value=State.reservation_selected_for_payment["phone"],
                        is_disabled=True,
                        class_name="w-full p-2 border rounded-md bg-gray-100",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label("Campo", class_name="text-sm font-medium text-gray-700"),
                    rx.el.input(
                        value=State.reservation_selected_for_payment["field_name"],
                        is_disabled=True,
                        class_name="w-full p-2 border rounded-md bg-gray-100",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label("Deporte", class_name="text-sm font-medium text-gray-700"),
                    rx.el.input(
                        value=State.reservation_selected_for_payment.get(
                            "sport_label", State.reservation_selected_for_payment["sport"]
                        ),
                        is_disabled=True,
                        class_name="w-full p-2 border rounded-md bg-gray-100",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label("Horario", class_name="text-sm font-medium text-gray-700"),
                    rx.el.div(
                        State.reservation_selected_for_payment["start_datetime"],
                        " - ",
                        State.reservation_selected_for_payment["end_datetime"],
                        class_name="w-full p-2 border rounded-md bg-gray-100 text-sm font-semibold",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label("Estado", class_name="text-sm font-medium text-gray-700"),
                    rx.el.input(
                        value=State.reservation_selected_for_payment["status"],
                        is_disabled=True,
                        class_name="w-full p-2 border rounded-md bg-gray-100",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label("Monto total", class_name="text-sm font-medium text-gray-700"),
                    rx.el.div(
                        rx.el.span(State.currency_symbol, class_name="text-gray-500"),
                        rx.el.span(
                            State.reservation_selected_for_payment["total_amount"].to_string(),
                            class_name="font-semibold",
                        ),
                        class_name="w-full p-2 border rounded-md bg-gray-100 flex items-center gap-1",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label("Adelanto", class_name="text-sm font-medium text-gray-700"),
                    rx.el.div(
                        rx.el.span(State.currency_symbol, class_name="text-gray-500"),
                        rx.el.span(
                            State.reservation_selected_for_payment["advance_amount"].to_string(),
                            class_name="font-semibold",
                        ),
                        class_name="w-full p-2 border rounded-md bg-gray-100 flex items-center gap-1",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label("Saldo pendiente", class_name="text-sm font-medium text-gray-700"),
                    rx.el.div(
                        rx.el.span(State.currency_symbol, class_name="text-gray-500"),
                        rx.el.span(
                            State.selected_reservation_balance.to_string(),
                            class_name="font-semibold",
                        ),
                        class_name="w-full p-2 border rounded-md bg-gray-100 flex items-center gap-1",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                class_name="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4",
            ),
        ),
        class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md mb-6 flex flex-col gap-4",
    )


def venta_page() -> rx.Component:
    return rx.el.div(
        rx.el.h1(
            "Control de Ventas y Pagos",
            class_name="text-2xl font-bold text-gray-800 mb-6",
        ),
        field_rental_sale_section(),
        rx.el.div(
            rx.el.h2(
                "Añadir Producto a la Venta",
                class_name="text-lg font-semibold text-gray-700 mb-4",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.label(
                        "Codigo de Barra",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.input(
                        placeholder="Ej: 7791234567890",
                        on_change=lambda val: State.handle_sale_change("barcode", val),
                        class_name="w-full p-2 border rounded-md",
                        value=State.new_sale_item["barcode"],
                    ),
                    class_name="w-48",
                ),
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
                        value=State.new_sale_item["description"],
                    ),
                    rx.cond(
                        State.autocomplete_suggestions.length() > 0,
                        rx.el.div(
                            rx.foreach(
                                State.autocomplete_suggestions,
                                lambda suggestion: rx.el.button(
                                    suggestion,
                                    on_click=lambda _,
                                    suggestion=suggestion: State.select_product_for_sale(
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
                        value=State.new_sale_item["quantity"].to_string(),
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
                        value=State.new_sale_item["unit"],
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
                        value=State.new_sale_item["price"].to_string(),
                    ),
                    class_name="w-32",
                ),
                rx.el.div(
                    rx.el.label(
                        "Subtotal",
                        class_name="block text-sm font-medium text-gray-600 mb-1",
                    ),
                    rx.el.div(
                        State.currency_symbol,
                        State.sale_subtotal.to_string(),
                        class_name="w-full p-2 font-semibold text-right",
                    ),
                    class_name="w-32",
                ),
                rx.el.div(
                    rx.el.button(
                        rx.icon("plus", class_name="h-5 w-5"),
                        "Añadir",
                        on_click=State.add_item_to_sale,
                        class_name="flex items-center justify-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 mt-6 min-h-[44px]",
                    )
                ),
                class_name="flex flex-wrap items-start gap-4",
            ),
            class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md mb-6",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.h2(
                    "Productos en la Venta",
                    class_name="text-lg font-semibold text-gray-700",
                ),
                rx.el.button(
                    rx.icon("trash-2", class_name="h-5 w-5"),
                    "Vaciar Lista",
                    on_click=State.clear_sale_items,
                    class_name="w-full sm:w-auto flex items-center justify-center gap-2 bg-red-500 text-white px-4 py-2 rounded-md hover:bg-red-600 min-h-[44px]",
                ),
                class_name="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4",
            ),
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("Codigo de Barra", class_name="py-2 px-4 text-left"),
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
            class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md flex flex-col gap-4",
        ),

        rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.el.h3(
                                "Metodo de Pago",
                                class_name="text-base font-semibold text-gray-700",
                            ),
                            rx.el.div(
                                rx.foreach(
                                    State.enabled_payment_methods,
                                    lambda method: rx.el.button(
                                        rx.el.div(
                                            rx.cond(
                                                method["kind"] == "cash",
                                                rx.icon("banknote", class_name="h-4 w-4"),
                                                rx.cond(
                                                    method["kind"] == "card",
                                                    rx.icon("credit-card", class_name="h-4 w-4"),
                                                    rx.cond(
                                                        method["kind"] == "wallet",
                                                        rx.icon("qr-code", class_name="h-4 w-4"),
                                                        rx.icon("layers", class_name="h-4 w-4"),
                                                    ),
                                                ),
                                            ),
                                            rx.el.span(method["name"], class_name="uppercase"),
                                            class_name="flex items-center gap-2",
                                        ),
                                        on_click=lambda _,
                                        mid=method["id"]: State.select_payment_method(mid),
                                        class_name=rx.cond(
                                            State.payment_method == method["name"],
                                            "px-4 py-2 rounded-md bg-indigo-600 text-white font-semibold",
                                            "px-4 py-2 rounded-md bg-white border text-gray-700 hover:bg-gray-50",
                                        ),
                                    ),
                                ),
                                class_name="flex flex-wrap gap-3",
                            ),
                            rx.cond(
                                State.enabled_payment_methods.length() == 0,
                                rx.el.p(
                                    "No hay metodos activos, activalos desde Configuracion.",
                                    class_name="text-sm text-red-600",
                                ),
                                rx.el.p(
                                    State.payment_method_description,
                                    class_name="text-sm text-gray-500",
                                ),
                            ),
                            rx.cond(
                                State.payment_method_kind == "cash",
                                rx.el.div(
                                    rx.el.label(
                                        "Monto recibido",
                                        class_name="text-sm font-semibold text-gray-700",
                                    ),
                                    rx.el.input(
                                        type="number",
                                        step="0.01",
                                        value=State.payment_cash_amount,
                                        on_change=lambda value: State.set_cash_amount(value),
                                        class_name="w-full md:w-64 p-2 border rounded-md",
                                    ),
                                    rx.cond(
                                        State.payment_cash_message != "",
                                        rx.cond(
                                            State.payment_cash_status == "change",
                                            rx.el.span(
                                                State.payment_cash_message,
                                                class_name="text-sm font-semibold text-green-600",
                                            ),
                                            rx.cond(
                                                State.payment_cash_status == "due",
                                                rx.el.span(
                                                    State.payment_cash_message,
                                                    class_name="text-sm font-semibold text-red-600",
                                                ),
                                                rx.cond(
                                                    State.payment_cash_status == "warning",
                                                    rx.el.span(
                                                        State.payment_cash_message,
                                                        class_name="text-sm font-semibold text-red-600",
                                                    ),
                                                    rx.el.span(
                                                        State.payment_cash_message,
                                                        class_name="text-sm text-gray-600",
                                                    ),
                                                ),
                                            ),
                                        ),
                                        rx.fragment(),
                                    ),
                                    class_name="flex flex-col gap-2 max-w-sm mt-2",
                                ),
                                rx.fragment(),
                            ),
                            rx.cond(
                                State.payment_method_kind == "card",
                                rx.el.div(
                                    rx.el.span(
                                        "Seleccione el tipo de tarjeta",
                                        class_name="text-sm font-semibold text-gray-700",
                                    ),
                                    rx.el.div(
                                        rx.el.button(
                                            rx.icon("credit-card", class_name="h-4 w-4"),
                                            "Credito",
                                            on_click=lambda: State.set_card_type("Credito"),
                                            class_name=rx.cond(
                                                State.payment_card_type == "Credito",
                                                "px-4 py-2 rounded-md bg-indigo-500 text-white",
                                                "px-4 py-2 rounded-md border",
                                            ),
                                        ),
                                        rx.el.button(
                                            rx.icon("credit-card", class_name="h-4 w-4"),
                                            "Debito",
                                            on_click=lambda: State.set_card_type("Debito"),
                                            class_name=rx.cond(
                                                State.payment_card_type == "Debito",
                                                "px-4 py-2 rounded-md bg-indigo-500 text-white",
                                                "px-4 py-2 rounded-md border",
                                            ),
                                        ),
                                        class_name="flex gap-3",
                                    ),
                                    class_name="flex flex-col gap-2 mt-2",
                                ),
                                rx.fragment(),
                            ),
                            rx.cond(
                                State.payment_method_kind == "wallet",
                                rx.el.div(
                                    rx.el.span(
                                        "Seleccione la billetera digital",
                                        class_name="text-sm font-semibold text-gray-700",
                                    ),
                                    rx.el.div(
                                        rx.el.button(
                                            rx.icon("smartphone", class_name="h-4 w-4"),
                                            "Yape",
                                            on_click=lambda: State.choose_wallet_provider("Yape"),
                                            class_name=rx.cond(
                                                State.payment_wallet_choice == "Yape",
                                                "px-4 py-2 rounded-md bg-indigo-500 text-white",
                                                "px-4 py-2 rounded-md border",
                                            ),
                                        ),
                                        rx.el.button(
                                            rx.icon("qr-code", class_name="h-4 w-4"),
                                            "Plin",
                                            on_click=lambda: State.choose_wallet_provider("Plin"),
                                            class_name=rx.cond(
                                                State.payment_wallet_choice == "Plin",
                                                "px-4 py-2 rounded-md bg-indigo-500 text-white",
                                                "px-4 py-2 rounded-md border",
                                            ),
                                        ),
                                        rx.el.button(
                                            "Otro",
                                            on_click=lambda: State.choose_wallet_provider("Otro"),
                                            class_name=rx.cond(
                                                State.payment_wallet_choice == "Otro",
                                                "px-4 py-2 rounded-md bg-indigo-500 text-white",
                                                "px-4 py-2 rounded-md border",
                                            ),
                                        ),
                                        class_name="flex flex-wrap gap-3",
                                    ),
                                    rx.cond(
                                        State.payment_wallet_choice == "Otro",
                                        rx.el.input(
                                            placeholder="Nombre de la billetera",
                                            value=State.payment_wallet_provider,
                                            on_change=lambda value: State.set_wallet_provider_custom(
                                                value
                                            ),
                                            class_name="w-full md:w-72 p-2 border rounded-md",
                                        ),
                                        rx.fragment(),
                                    ),
                                    class_name="flex flex-col gap-2 mt-2",
                                ),
                                rx.fragment(),
                            ),
                            rx.cond(
                                State.payment_method_kind == "mixed",
                                rx.el.div(
                                    rx.el.div(
                                        rx.el.span(
                                            "Efectivo",
                                            class_name="text-sm font-semibold text-gray-700",
                                        ),
                                        rx.el.input(
                                            type="number",
                                            step="0.01",
                                            value=State.payment_mixed_cash,
                                            on_change=lambda value: State.set_mixed_cash_amount(value),
                                            class_name="w-full md:w-56 p-2 border rounded-md",
                                        ),
                                        class_name="flex flex-col gap-2",
                                    ),
                                    rx.el.div(
                                        rx.el.span(
                                            "Tarjeta",
                                            class_name="text-sm font-semibold text-gray-700",
                                        ),
                                        rx.el.input(
                                            type="number",
                                            step="0.01",
                                            value=State.payment_mixed_card,
                                            on_change=lambda value: State.set_mixed_card_amount(value),
                                            class_name="w-full md:w-56 p-2 border rounded-md",
                                        ),
                                        rx.el.div(
                                            rx.el.button(
                                                rx.icon("credit-card", class_name="h-4 w-4"),
                                                "Credito",
                                                on_click=lambda: State.set_card_type("Credito"),
                                                class_name=rx.cond(
                                                    State.payment_card_type == "Credito",
                                                    "px-3 py-1 rounded-md bg-indigo-500 text-white text-sm",
                                                    "px-3 py-1 rounded-md border text-sm",
                                                ),
                                            ),
                                            rx.el.button(
                                                rx.icon("credit-card", class_name="h-4 w-4"),
                                                "Debito",
                                                on_click=lambda: State.set_card_type("Debito"),
                                                class_name=rx.cond(
                                                    State.payment_card_type == "Debito",
                                                    "px-3 py-1 rounded-md bg-indigo-500 text-white text-sm",
                                                    "px-3 py-1 rounded-md border text-sm",
                                                ),
                                            ),
                                            class_name="flex gap-2",
                                        ),
                                        class_name="flex flex-col gap-2",
                                        ),
                                        rx.el.div(
                                            rx.el.span(
                                                "Billetera Digital / QR",
                                                class_name="text-sm font-semibold text-gray-700",
                                            ),
                                            rx.el.input(
                                                type="number",
                                                step="0.01",
                                            value=State.payment_mixed_wallet,
                                            on_change=lambda value: State.set_mixed_wallet_amount(value),
                                            class_name="w-full md:w-56 p-2 border rounded-md",
                                        ),
                                        rx.el.div(
                                            rx.el.button(
                                                rx.icon("smartphone", class_name="h-4 w-4"),
                                                "Yape",
                                                on_click=lambda: State.choose_wallet_provider("Yape"),
                                                class_name=rx.cond(
                                                    State.payment_wallet_choice == "Yape",
                                                    "px-3 py-1 rounded-md bg-indigo-500 text-white text-sm",
                                                    "px-3 py-1 rounded-md border text-sm",
                                                ),
                                            ),
                                            rx.el.button(
                                                rx.icon("qr-code", class_name="h-4 w-4"),
                                                "Plin",
                                                on_click=lambda: State.choose_wallet_provider("Plin"),
                                                class_name=rx.cond(
                                                    State.payment_wallet_choice == "Plin",
                                                    "px-3 py-1 rounded-md bg-indigo-500 text-white text-sm",
                                                    "px-3 py-1 rounded-md border text-sm",
                                                ),
                                            ),
                                            rx.el.button(
                                                "Otro",
                                                on_click=lambda: State.choose_wallet_provider("Otro"),
                                                class_name=rx.cond(
                                                    State.payment_wallet_choice == "Otro",
                                                    "px-3 py-1 rounded-md bg-indigo-500 text-white text-sm",
                                                    "px-3 py-1 rounded-md border text-sm",
                                                ),
                                            ),
                                            class_name="flex flex-wrap gap-2",
                                        ),
                                        rx.cond(
                                            State.payment_wallet_choice == "Otro",
                                            rx.el.input(
                                                placeholder="Nombre de la billetera",
                                                value=State.payment_wallet_provider,
                                                on_change=lambda value: State.set_wallet_provider_custom(
                                                    value
                                                ),
                                                class_name="w-full md:w-72 p-2 border rounded-md",
                                            ),
                                            rx.fragment(),
                                        ),
                                        class_name="flex flex-col gap-2",
                                    ),
                                    rx.el.div(
                                        rx.el.label(
                                            "Notas adicionales",
                                            class_name="text-sm font-semibold text-gray-700",
                                        ),
                                        rx.el.textarea(
                                            placeholder="Describe la combinacion de pagos",
                                            value=State.payment_mixed_notes,
                                            on_change=lambda value: State.set_mixed_notes(value),
                                            class_name="w-full md:w-96 p-2 border rounded-md",
                                        ),
                                        class_name="flex flex-col gap-2",
                                    ),
                                    rx.cond(
                                        State.payment_mixed_message != "",
                                        rx.cond(
                                            State.payment_mixed_status == "change",
                                            rx.el.span(
                                                State.payment_mixed_message,
                                                class_name="text-sm font-semibold text-green-600",
                                            ),
                                            rx.cond(
                                                State.payment_mixed_status == "due",
                                                rx.el.span(
                                                    State.payment_mixed_message,
                                                    class_name="text-sm font-semibold text-red-600",
                                                ),
                                                rx.cond(
                                                    State.payment_mixed_status == "warning",
                                                    rx.el.span(
                                                        State.payment_mixed_message,
                                                        class_name="text-sm font-semibold text-red-600",
                                                    ),
                                                    rx.el.span(
                                                        State.payment_mixed_message,
                                                        class_name="text-sm text-gray-600",
                                                    ),
                                                ),
                                            ),
                                        ),
                                        rx.fragment(),
                                    ),
                                    class_name="flex flex-col gap-3 mt-2",
                                ),
                                rx.fragment(),
                            ),
                            class_name="flex flex-col gap-3",
                        ),
                        class_name="flex flex-col gap-3",
                    ),
                    rx.el.div(
                        rx.el.span(
                            "Total General:",
                            class_name="text-xl font-bold text-gray-800",
                        ),
                        rx.el.span(
                            State.currency_symbol,
                            State.sale_total.to_string(),
                            class_name="text-2xl font-bold text-indigo-700",
                        ),
                        class_name="flex flex-col sm:flex-row sm:items-end gap-2 sm:gap-3",
                    ),
                    rx.el.div(
                        rx.el.button(
                            "Confirmar Pago",
                            on_click=State.confirm_sale,
                            class_name="w-full sm:w-auto bg-green-600 text-white px-5 py-3 rounded-lg hover:bg-green-700 font-semibold text-center min-h-[44px]",
                        ),
                        rx.cond(
                            State.sale_receipt_ready,
                            rx.el.button(
                                rx.icon("printer", class_name="h-4 w-4"),
                                "Imprimir Comprobante",
                                on_click=State.print_sale_receipt,
                                class_name="w-full sm:w-auto flex items-center justify-center gap-2 border border-indigo-200 text-indigo-700 px-4 py-3 rounded-lg hover:bg-indigo-50 min-h-[44px]",
                            ),
                            rx.el.button(
                                rx.icon("printer", class_name="h-4 w-4"),
                                "Imprimir Comprobante",
                                is_disabled=True,
                                class_name="w-full sm:w-auto flex items-center justify-center gap-2 border border-indigo-200 text-indigo-300 px-4 py-3 rounded-lg cursor-not-allowed min-h-[44px]",
                            ),
                        ),
                        class_name="flex flex-col sm:flex-row sm:items-center justify-end gap-3",
                    ),
                    class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md flex flex-col gap-4",
                ),
        class_name="p-4 sm:p-6 w-full max-w-7xl mx-auto flex flex-col gap-6",
    )
