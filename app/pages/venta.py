import reflex as rx
from app.state import State
from app.components.ui import (
    page_title,
    section_header,
    card_container,
    form_field,
    text_input,
    action_button,
    data_table,
    BUTTON_STYLES,
    INPUT_STYLES,
    icon_button,
)


def sale_item_row(item: rx.Var[dict]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(item["barcode"], class_name="py-3 px-4 align-middle"),
        rx.el.td(item["description"], class_name="py-3 px-4 align-middle"),
        rx.el.td(item["quantity"].to_string(), class_name="py-3 px-4 text-center align-middle"),
        rx.el.td(item["unit"], class_name="py-3 px-4 text-center align-middle"),
        rx.el.td(
            State.currency_symbol,
            item["price"].to_string(),
            class_name="py-3 px-4 text-right align-middle",
        ),
        rx.el.td(
            State.currency_symbol,
            item["subtotal"].to_string(),
            class_name="py-3 px-4 text-right font-semibold align-middle",
        ),
        rx.el.td(
            icon_button(
                "trash-2",
                on_click=lambda: State.remove_item_from_sale(item["temp_id"]),
                variant="icon_danger",
            ),
            class_name="py-3 px-4 text-center align-middle",
        ),
        class_name="border-b hover:bg-gray-50 transition-colors",
    )


def field_rental_sale_section() -> rx.Component:
    return card_container(
        section_header(
            "Alquiler de Campo",
            "Revisa los datos de la reserva enviada desde Servicios y completa el cobro.",
        ),
        rx.cond(
            State.reservation_selected_for_payment == None,
            rx.el.div(
                rx.icon("info", class_name="h-5 w-5 text-blue-500"),
                rx.el.div(
                    rx.el.span("Sin reserva seleccionada", class_name="text-sm font-semibold text-gray-800"),
                    rx.el.span(
                        "Usa el boton Pagar en Reservas registradas para cargar los datos aqui.",
                        class_name="text-sm text-gray-600",
                    ),
                    class_name="flex flex-col",
                ),
                class_name="flex items-start gap-3 rounded-lg border border-blue-100 bg-blue-50 p-4",
            ),
            rx.el.div(
                form_field(
                    "Cliente",
                    text_input(value=State.reservation_selected_for_payment["client_name"], disabled=True),
                ),
                form_field(
                    "Telefono",
                    text_input(value=State.reservation_selected_for_payment["phone"], disabled=True),
                ),
                form_field(
                    "Campo",
                    text_input(value=State.reservation_selected_for_payment["field_name"], disabled=True),
                ),
                form_field(
                    "Deporte",
                    text_input(
                        value=State.reservation_selected_for_payment.get(
                            "sport_label", State.reservation_selected_for_payment["sport"]
                        ),
                        disabled=True,
                    ),
                ),
                form_field(
                    "Horario",
                    rx.el.div(
                        State.reservation_selected_for_payment["start_datetime"],
                        " - ",
                        State.reservation_selected_for_payment["end_datetime"],
                        class_name=INPUT_STYLES["disabled"],
                    ),
                ),
                form_field(
                    "Estado",
                    text_input(value=State.reservation_selected_for_payment["status"], disabled=True),
                ),
                form_field(
                    "Monto total",
                    rx.el.div(
                        rx.el.span(State.currency_symbol, class_name="text-gray-500"),
                        rx.el.span(
                            State.reservation_selected_for_payment["total_amount"].to_string(),
                            class_name="font-semibold",
                        ),
                        class_name=f"{INPUT_STYLES['disabled']} flex items-center gap-1",
                    ),
                ),
                form_field(
                    "Adelanto",
                    rx.el.div(
                        rx.el.span(State.currency_symbol, class_name="text-gray-500"),
                        rx.el.span(
                            State.reservation_selected_for_payment["advance_amount"].to_string(),
                            class_name="font-semibold",
                        ),
                        class_name=f"{INPUT_STYLES['disabled']} flex items-center gap-1",
                    ),
                ),
                form_field(
                    "Saldo pendiente",
                    rx.el.div(
                        rx.el.span(State.currency_symbol, class_name="text-gray-500"),
                        rx.el.span(
                            State.selected_reservation_balance.to_string(),
                            class_name="font-semibold text-indigo-600",
                        ),
                        class_name=f"{INPUT_STYLES['disabled']} flex items-center gap-1",
                    ),
                ),
                class_name="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4",
            ),
        ),
    )


def add_product_section() -> rx.Component:
    return card_container(
        section_header("Añadir Producto a la Venta"),
        rx.el.div(
            rx.el.div(
                form_field(
                    "Codigo de Barra",
                    rx.el.input(
                        id="barcode-input-sale",
                        key=State.sale_form_key.to_string(),
                        default_value=State.new_sale_item["barcode"],
                        placeholder="Ej: 7791234567890",
                        on_blur=lambda e: State.process_sale_barcode_from_input(e),
                        on_key_down=lambda k: State.handle_barcode_enter(k, "barcode-input-sale"),
                        class_name=INPUT_STYLES["default"],
                        type="text",
                        auto_complete="off",
                    ),
                ),
                class_name="w-full sm:w-48",
            ),
            rx.el.div(
                form_field(
                    "Descripción",
                    rx.el.div(
                        text_input(
                            placeholder="Buscar producto...",
                            value=State.new_sale_item["description"],
                            on_change=lambda val: State.handle_sale_change("description", val),
                        ),
                        rx.cond(
                            State.autocomplete_suggestions.length() > 0,
                            rx.el.div(
                                rx.foreach(
                                    State.autocomplete_suggestions,
                                    lambda suggestion: rx.el.button(
                                        suggestion,
                                        on_click=lambda _, s=suggestion: State.select_product_for_sale(s),
                                        class_name="w-full text-left p-2 hover:bg-gray-100 text-sm",
                                    ),
                                ),
                                class_name="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-60 overflow-y-auto",
                            ),
                            rx.fragment(),
                        ),
                        class_name="relative",
                    ),
                ),
                class_name="flex-grow min-w-[200px]",
            ),
            rx.el.div(
                form_field(
                    "Cantidad",
                    text_input(
                        input_type="number",
                        value=State.new_sale_item["quantity"].to_string(),
                        on_change=lambda val: State.handle_sale_change("quantity", val),
                    ),
                ),
                class_name="w-full sm:w-24",
            ),
            rx.el.div(
                form_field(
                    "Unidad",
                    text_input(value=State.new_sale_item["unit"], disabled=True),
                ),
                class_name="w-full sm:w-32",
            ),
            rx.el.div(
                form_field(
                    "Precio Venta",
                    text_input(
                        input_type="number",
                        value=State.new_sale_item["price"].to_string(),
                        on_change=lambda val: State.handle_sale_change("price", val),
                    ),
                ),
                class_name="w-full sm:w-32",
            ),
            rx.el.div(
                form_field(
                    "Subtotal",
                    rx.el.div(
                        State.currency_symbol,
                        State.sale_subtotal.to_string(),
                        class_name=f"{INPUT_STYLES['disabled']} font-semibold text-right",
                    ),
                ),
                class_name="w-full sm:w-32",
            ),
            rx.el.div(
                action_button(
                    "Añadir",
                    on_click=State.add_item_to_sale,
                    icon="plus",
                ),
                class_name="mt-6",
            ),
            class_name="flex flex-wrap items-start gap-4",
        ),
    )


def payment_method_section() -> rx.Component:
    return card_container(
        rx.el.div(
            section_header("Metodo de Pago"),
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
                        on_click=lambda _, mid=method["id"]: State.select_payment_method(mid),
                        class_name=rx.cond(
                            State.payment_method == method["name"],
                            BUTTON_STYLES["primary"],
                            BUTTON_STYLES["secondary"],
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
                    form_field(
                        "Monto recibido",
                        text_input(
                            input_type="number",
                            value=State.payment_cash_amount,
                            on_change=lambda value: State.set_cash_amount(value),
                        ),
                    ),
                    rx.cond(
                        State.payment_cash_message != "",
                        rx.cond(
                            State.payment_cash_status == "change",
                            rx.el.span(State.payment_cash_message, class_name="text-sm font-semibold text-green-600"),
                            rx.cond(
                                State.payment_cash_status == "due",
                                rx.el.span(State.payment_cash_message, class_name="text-sm font-semibold text-red-600"),
                                rx.el.span(State.payment_cash_message, class_name="text-sm text-gray-600"),
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
                    rx.el.span("Seleccione el tipo de tarjeta", class_name="text-sm font-semibold text-gray-700"),
                    rx.el.div(
                        action_button(
                            "Credito",
                            on_click=lambda: State.set_card_type("Credito"),
                            variant=rx.cond(State.payment_card_type == "Credito", BUTTON_STYLES["primary"], BUTTON_STYLES["secondary"]),
                            icon="credit-card",
                        ),
                        action_button(
                            "Debito",
                            on_click=lambda: State.set_card_type("Debito"),
                            variant=rx.cond(State.payment_card_type == "Debito", BUTTON_STYLES["primary"], BUTTON_STYLES["secondary"]),
                            icon="credit-card",
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
                    rx.el.span("Seleccione la billetera digital", class_name="text-sm font-semibold text-gray-700"),
                    rx.el.div(
                        action_button(
                            "Yape",
                            on_click=lambda: State.choose_wallet_provider("Yape"),
                            variant=rx.cond(State.payment_wallet_choice == "Yape", BUTTON_STYLES["primary"], BUTTON_STYLES["secondary"]),
                            icon="smartphone",
                        ),
                        action_button(
                            "Plin",
                            on_click=lambda: State.choose_wallet_provider("Plin"),
                            variant=rx.cond(State.payment_wallet_choice == "Plin", BUTTON_STYLES["primary"], BUTTON_STYLES["secondary"]),
                            icon="qr-code",
                        ),
                        action_button(
                            "Otro",
                            on_click=lambda: State.choose_wallet_provider("Otro"),
                            variant=rx.cond(State.payment_wallet_choice == "Otro", BUTTON_STYLES["primary"], BUTTON_STYLES["secondary"]),
                        ),
                        class_name="flex flex-wrap gap-3",
                    ),
                    rx.cond(
                        State.payment_wallet_choice == "Otro",
                        text_input(
                            placeholder="Nombre de la billetera",
                            value=State.payment_wallet_provider,
                            on_change=lambda value: State.set_wallet_provider_custom(value),
                            style="default",
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
                        form_field(
                            "Efectivo",
                            text_input(
                                input_type="number",
                                value=State.payment_mixed_cash,
                                on_change=lambda value: State.set_mixed_cash_amount(value),
                            ),
                        ),
                        class_name="flex flex-col gap-2",
                    ),
                    rx.el.div(
                        form_field(
                            "Tarjeta",
                            text_input(
                                input_type="number",
                                value=State.payment_mixed_card,
                                on_change=lambda value: State.set_mixed_card_amount(value),
                            ),
                        ),
                        rx.el.div(
                            action_button(
                                "Credito",
                                on_click=lambda: State.set_card_type("Credito"),
                                variant=rx.cond(State.payment_card_type == "Credito", BUTTON_STYLES["primary_sm"], BUTTON_STYLES["secondary_sm"]),
                                icon="credit-card",
                            ),
                            action_button(
                                "Debito",
                                on_click=lambda: State.set_card_type("Debito"),
                                variant=rx.cond(State.payment_card_type == "Debito", BUTTON_STYLES["primary_sm"], BUTTON_STYLES["secondary_sm"]),
                                icon="credit-card",
                            ),
                            class_name="flex gap-2",
                        ),
                        class_name="flex flex-col gap-2",
                    ),
                    rx.el.div(
                        form_field(
                            "Billetera Digital / QR",
                            text_input(
                                input_type="number",
                                value=State.payment_mixed_wallet,
                                on_change=lambda value: State.set_mixed_wallet_amount(value),
                            ),
                        ),
                        rx.el.div(
                            action_button(
                                "Yape",
                                on_click=lambda: State.choose_wallet_provider("Yape"),
                                variant=rx.cond(State.payment_wallet_choice == "Yape", BUTTON_STYLES["primary_sm"], BUTTON_STYLES["secondary_sm"]),
                                icon="smartphone",
                            ),
                            action_button(
                                "Plin",
                                on_click=lambda: State.choose_wallet_provider("Plin"),
                                variant=rx.cond(State.payment_wallet_choice == "Plin", BUTTON_STYLES["primary_sm"], BUTTON_STYLES["secondary_sm"]),
                                icon="qr-code",
                            ),
                            action_button(
                                "Otro",
                                on_click=lambda: State.choose_wallet_provider("Otro"),
                                variant=rx.cond(State.payment_wallet_choice == "Otro", BUTTON_STYLES["primary_sm"], BUTTON_STYLES["secondary_sm"]),
                            ),
                            class_name="flex flex-wrap gap-2",
                        ),
                        rx.cond(
                            State.payment_wallet_choice == "Otro",
                            text_input(
                                placeholder="Nombre de la billetera",
                                value=State.payment_wallet_provider,
                                on_change=lambda value: State.set_wallet_provider_custom(value),
                            ),
                            rx.fragment(),
                        ),
                        class_name="flex flex-col gap-2",
                    ),
                    rx.el.div(
                        form_field(
                            "Notas adicionales",
                            rx.el.textarea(
                                placeholder="Describe la combinacion de pagos",
                                value=State.payment_mixed_notes,
                                on_change=lambda value: State.set_mixed_notes(value),
                                class_name=INPUT_STYLES["default"],
                            ),
                        ),
                        class_name="flex flex-col gap-2",
                    ),
                    rx.cond(
                        State.payment_mixed_message != "",
                        rx.el.span(
                            State.payment_mixed_message,
                            class_name=rx.cond(
                                State.payment_mixed_status == "change",
                                "text-sm font-semibold text-green-600",
                                "text-sm font-semibold text-red-600",
                            ),
                        ),
                        rx.fragment(),
                    ),
                    class_name="flex flex-col gap-3 mt-2",
                ),
                rx.fragment(),
            ),
            class_name="flex flex-col gap-4",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span("Total General:", class_name="text-xl font-bold text-gray-800"),
                rx.el.span(
                    State.currency_symbol,
                    State.sale_total.to_string(),
                    class_name="text-3xl font-bold text-indigo-600",
                ),
                class_name="flex flex-col sm:flex-row sm:items-end gap-2 sm:gap-3",
            ),
            rx.el.div(
                action_button(
                    "Confirmar Pago",
                    on_click=State.confirm_sale,
                    variant="success",
                    class_name="w-full sm:w-auto",
                ),
                rx.cond(
                    State.sale_receipt_ready,
                    action_button(
                        "Imprimir Comprobante",
                        on_click=State.print_sale_receipt,
                        variant="link_primary",
                        icon="printer",
                    ),
                    action_button(
                        "Imprimir Comprobante",
                        on_click=None,
                        variant="disabled",
                        icon="printer",
                        disabled=True,
                    ),
                ),
                class_name="flex flex-col sm:flex-row sm:items-center justify-end gap-3",
            ),
            class_name="flex flex-col gap-4 border-t pt-4 mt-2",
        ),
    )


def venta_page() -> rx.Component:
    return rx.el.div(
        page_title("Control de Ventas y Pagos"),
        field_rental_sale_section(),
        add_product_section(),
        card_container(
            rx.el.div(
                section_header("Productos en la Venta"),
                action_button(
                    "Vaciar Lista",
                    on_click=State.clear_sale_items,
                    variant="danger",
                    icon="trash-2",
                ),
                class_name="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4",
            ),
            data_table(
                headers=[
                    ("Codigo de Barra", "text-left"),
                    ("Descripción", "text-left"),
                    ("Cantidad", "text-center"),
                    ("Unidad", "text-center"),
                    ("P. Venta", "text-right"),
                    ("Subtotal", "text-right"),
                    ("Acción", "text-center"),
                ],
                rows=rx.foreach(State.new_sale_items, sale_item_row),
                empty_message="Aún no has añadido productos a la venta.",
                has_data=State.new_sale_items.length() > 0,
            ),
        ),
        payment_method_section(),
        class_name="flex flex-col gap-6 p-4 sm:p-6 max-w-7xl mx-auto",
    )
