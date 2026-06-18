import reflex as rx
from app.state import State
from app.components.ui import BUTTON_STYLES, toggle_switch
from ._fiscal_section import _coupon_input, _receipt_type_selector, _fiscal_lookup_input


def _quot_action_buttons() -> rx.Component:
    """Botones de presupuesto en el footer del POS (guardar y cargar)."""
    return rx.el.div(
        rx.el.button(
            rx.icon("bookmark", class_name="h-3.5 w-3.5"),
            rx.el.span("Guardar", class_name="hidden sm:inline"),
            on_click=State.open_quot_save_modal,
            disabled=State.new_sale_items.length() == 0,
            class_name=(
                "flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium "
                "text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg "
                "hover:bg-indigo-100 disabled:opacity-40 disabled:cursor-not-allowed "
                "transition-colors"
            ),
            title="Guardar el carrito actual como presupuesto",
        ),
        rx.el.button(
            rx.icon("folder-open", class_name="h-3.5 w-3.5"),
            rx.el.span("Cargar", class_name="hidden sm:inline"),
            on_click=State.open_pos_quot_drawer,
            class_name=(
                "flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium "
                "text-slate-600 bg-slate-50 border border-slate-200 rounded-lg "
                "hover:bg-slate-100 transition-colors"
            ),
            title="Buscar y cargar un presupuesto existente",
        ),
        class_name="flex gap-2 flex-wrap justify-center",
    )


def _quot_save_modal() -> rx.Component:
    """Modal para guardar el carrito POS como presupuesto."""
    return rx.cond(
        State.show_quot_save_modal,
        rx.el.div(
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.div(
                        rx.icon("bookmark", class_name="h-5 w-5 text-indigo-600"),
                        rx.el.span(
                            "Guardar como Presupuesto",
                            class_name="font-semibold text-slate-800",
                        ),
                        class_name="flex items-center gap-2",
                    ),
                    rx.el.button(
                        rx.icon("x", class_name="h-4 w-4"),
                        on_click=State.close_quot_save_modal,
                        class_name="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100",
                    ),
                    class_name="flex items-center justify-between p-4 border-b",
                ),
                # Body
                rx.el.div(
                    rx.el.div(
                        rx.el.label(
                            "Validez (días)",
                            class_name="block text-xs font-medium text-slate-600 mb-1",
                        ),
                        rx.el.input(
                            default_value=State.quot_save_validity_days,
                            type="number",
                            min="1",
                            max="365",
                            on_blur=State.set_quot_save_validity,
                            class_name=(
                                "w-full border border-slate-200 rounded-lg px-3 py-2 "
                                "text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                            ),
                        ),
                    ),
                    rx.el.div(
                        rx.el.label(
                            "Notas (opcionales)",
                            class_name="block text-xs font-medium text-slate-600 mb-1",
                        ),
                        rx.el.textarea(
                            placeholder="Condiciones, observaciones para el cliente...",
                            default_value=State.quot_save_notes,
                            on_blur=State.set_quot_save_notes,
                            class_name=(
                                "w-full border border-slate-200 rounded-lg px-3 py-2 "
                                "text-sm resize-none h-20 placeholder-slate-400 focus:outline-none "
                                "focus:ring-2 focus:ring-indigo-300"
                            ),
                        ),
                    ),
                    rx.el.p(
                        rx.icon("info", class_name="h-3.5 w-3.5 shrink-0 text-slate-400"),
                        "El carrito continuará activo tras guardar.",
                        class_name="flex items-center gap-1.5 text-xs text-slate-400",
                    ),
                    class_name="p-4 space-y-3",
                ),
                # Footer
                rx.el.div(
                    rx.el.button(
                        rx.cond(State.is_loading, "Guardando...", "Guardar"),
                        on_click=State.save_pos_cart_as_quotation,
                        disabled=State.is_loading,
                        class_name=(
                            "px-4 py-2 text-sm font-medium text-white bg-indigo-600 "
                            "rounded-lg hover:bg-indigo-700 disabled:opacity-60 "
                            "disabled:cursor-not-allowed transition-colors"
                        ),
                    ),
                    rx.el.button(
                        "Cancelar",
                        on_click=State.close_quot_save_modal,
                        class_name=(
                            "px-4 py-2 text-sm border border-slate-200 rounded-lg "
                            "hover:bg-slate-50 transition-colors"
                        ),
                    ),
                    class_name="flex gap-2 justify-end p-4 border-t bg-slate-50",
                ),
                class_name="bg-white rounded-xl shadow-xl w-full max-w-sm mx-4",
            ),
            class_name=(
                "fixed inset-0 z-50 flex items-center justify-center "
                "bg-black/40 backdrop-blur-sm"
            ),
        ),
        rx.fragment(),
    )


def _quot_load_drawer() -> rx.Component:
    """Drawer lateral para buscar y cargar presupuestos en el POS."""

    def _result_row(q: rx.Var) -> rx.Component:
        return rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.span(
                        "#", q["id"].to_string(),
                        class_name="font-mono text-xs font-semibold text-slate-700",
                    ),
                    rx.el.span(
                        q["status_label"],
                        class_name=rx.cond(
                            q["is_expired"],
                            "text-xs px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700",
                            "text-xs px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700",
                        ),
                    ),
                    class_name="flex items-center gap-2",
                ),
                rx.el.span(
                    q["total_amount"],
                    class_name="font-bold text-indigo-700 tabular-nums text-sm",
                ),
                class_name="flex items-center justify-between",
            ),
            rx.el.div(
                rx.el.span(
                    "Creado: ", q["created_at"],
                    class_name="text-xs text-slate-400",
                ),
                rx.el.span(
                    "Vence: ", q["expires_at"],
                    class_name="text-xs text-slate-400",
                ),
                class_name="flex gap-3 mt-0.5",
            ),
            rx.cond(
                q["notes_preview"] != "",
                rx.el.p(
                    q["notes_preview"],
                    class_name="text-xs text-slate-500 italic mt-0.5 truncate",
                ),
                rx.fragment(),
            ),
            rx.el.button(
                rx.icon("shopping-cart", class_name="h-3.5 w-3.5"),
                "Cargar al POS",
                on_click=State.convert_quotation_to_cart(q["id"]),
                disabled=q["is_expired"],
                class_name=(
                    "mt-2 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium "
                    "text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 "
                    "disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                ),
            ),
            class_name=(
                "p-3 border border-slate-200 rounded-lg bg-white hover:bg-slate-50 "
                "space-y-0.5 transition-colors"
            ),
        )

    return rx.cond(
        State.show_pos_quot_drawer,
        rx.el.div(
            # Overlay
            rx.el.div(
                on_click=State.close_pos_quot_drawer,
                class_name="absolute inset-0 bg-black/30",
            ),
            # Panel
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.div(
                        rx.icon("folder-open", class_name="h-5 w-5 text-indigo-600"),
                        rx.el.span(
                            "Cargar Presupuesto",
                            class_name="font-semibold text-slate-800",
                        ),
                        class_name="flex items-center gap-2",
                    ),
                    rx.el.button(
                        rx.icon("x", class_name="h-4 w-4"),
                        on_click=State.close_pos_quot_drawer,
                        class_name="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100",
                    ),
                    class_name="flex items-center justify-between p-4 border-b shrink-0",
                ),
                # Buscador
                rx.el.div(
                    rx.debounce_input(
                        rx.input(
                            placeholder="Buscar por #ID o texto en notas...",
                            value=State.pos_quot_search,
                            on_change=State.search_pos_quotations,
                            class_name=(
                                "w-full border border-slate-200 rounded-lg px-3 py-2 "
                                "text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                            ),
                            auto_focus=True,
                        ),
                        debounce_timeout=350,
                    ),
                    rx.cond(
                        State.pos_quot_loading,
                        rx.el.p(
                            rx.spinner(size="1"),
                            "Buscando...",
                            class_name="flex items-center gap-2 text-xs text-slate-400 mt-1",
                        ),
                        rx.fragment(),
                    ),
                    class_name="p-3 border-b shrink-0",
                ),
                # Resultados
                rx.el.div(
                    rx.cond(
                        State.pos_quot_results.length() > 0,
                        rx.foreach(State.pos_quot_results, _result_row),
                        rx.cond(
                            State.pos_quot_search != "",
                            rx.el.p(
                                "Sin resultados. Prueba con otro término.",
                                class_name="text-sm text-slate-400 text-center py-8",
                            ),
                            rx.el.div(
                                rx.icon(
                                    "folder-open",
                                    class_name="h-10 w-10 text-slate-200 mx-auto",
                                ),
                                rx.el.p(
                                    "Escribe un #ID o texto para buscar presupuestos pendientes.",
                                    class_name="text-xs text-slate-400 text-center mt-2",
                                ),
                                class_name="py-10",
                            ),
                        ),
                    ),
                    class_name="flex-1 overflow-y-auto p-3 space-y-2",
                ),
                class_name=(
                    "absolute right-0 top-0 h-full w-80 bg-slate-50 shadow-2xl "
                    "flex flex-col z-10"
                ),
            ),
            class_name="fixed inset-0 z-50",
        ),
        rx.fragment(),
    )


def _payment_form_body(variant: str) -> tuple:
    """Shared inner form content for payment sidebar and mobile section.

    Args:
        variant: "desktop" for the sidebar, "mobile" for the mobile/tablet section.
    """
    is_desktop = variant == "desktop"

    # ── Payment method button classes ──────────────────────────────────────
    pm_btn_active = (
        "flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-600 text-white w-full justify-center"
        if is_desktop else
        "flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-indigo-600 text-white"
    )
    pm_btn_inactive = (
        "flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-white text-slate-700 hover:bg-slate-50 w-full justify-center"
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
        "grid grid-cols-2 gap-1.5"
        if is_desktop else
        "grid grid-cols-2 sm:grid-cols-4 gap-2 p-3 sm:p-4"
    )

    # ── Credit section wrapper class ────────────────────────────────────────
    credit_section_class = (
        "px-3 py-2 border-b"
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
        "flex flex-col gap-2 px-3 py-2 border-b border-slate-100"
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
        "px-3 py-2 border-b min-h-[64px]"
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
        "text-2xl font-bold text-indigo-600"
        if is_desktop else
        "text-3xl sm:text-4xl font-bold text-indigo-600"
    )
    total_row_class = (
        "flex items-baseline gap-1"
        if is_desktop else
        "flex items-baseline gap-0.5"
    )
    total_container_class = (
        "flex items-baseline justify-between mb-2"
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
        "px-3 py-2 flex flex-col gap-2"
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
        credit_header = rx.el.div(
            rx.el.span("CREDITO / FIADO", class_name="text-xs font-medium text-slate-600"),
            toggle_switch(
                checked=State.is_credit_mode,
                on_change=State.toggle_credit_mode,
            ),
            class_name="flex items-center justify-between",
        )
    else:
        credit_header = rx.el.div(
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
            rx.el.div(
                pm_buttons,
                class_name=pm_grid_class,
            ),
            class_name="p-2 border-b",
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
                    class_name="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm placeholder-slate-400",
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
                        disabled=True,
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
            _coupon_input(),
            cash_option,
            _receipt_type_selector(),
            _fiscal_lookup_input(),
            rx.el.div(
                rx.el.div(
                    rx.el.span("TOTAL", class_name=total_label_class),
                    rx.el.div(
                        rx.el.span(State.currency_symbol, class_name="text-base text-indigo-600"),
                        rx.el.span(
                            State.sale_total.to_string(),
                            class_name=total_amount_class,
                        ),
                        class_name=total_row_class,
                    ),
                    class_name=total_container_class,
                ),
                rx.el.button(
                    rx.cond(
                        State.is_loading,
                        rx.el.div(
                            rx.spinner(size="2"),
                            rx.el.span("Procesando..."),
                            class_name="flex items-center gap-2",
                        ),
                        rx.el.div(
                            rx.icon("circle-check", class_name="h-5 w-5"),
                            rx.el.span("Confirmar Venta"),
                            class_name="flex items-center gap-2",
                        ),
                    ),
                    on_click=State.confirm_sale,
                    disabled=State.is_loading,
                    loading=State.is_loading,
                    data_venta_confirm_btn=True,
                    class_name=rx.cond(
                        State.is_loading,
                        confirm_loading_class,
                        confirm_active_class,
                    ),
                ),
                _quot_action_buttons(),
                class_name=confirm_wrapper_class,
            ),
            class_name=footer_class,
        )
    else:
        footer = rx.el.div(
            _coupon_input(),
            cash_option,
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
                        rx.el.div(
                            rx.spinner(size="2"),
                            rx.el.span("Procesando..."),
                            class_name="flex items-center gap-2",
                        ),
                        rx.el.div(
                            rx.icon("circle-check", class_name="h-5 w-5"),
                            rx.el.span("Confirmar Venta"),
                            class_name="flex items-center gap-2",
                        ),
                    ),
                    on_click=State.confirm_sale,
                    disabled=State.is_loading,
                    loading=State.is_loading,
                    data_venta_confirm_btn=True,
                    class_name=rx.cond(
                        State.is_loading,
                        confirm_loading_class,
                        confirm_active_class,
                    ),
                ),
                _quot_action_buttons(),
                class_name=confirm_wrapper_class,
            ),
            class_name=footer_class,
        )

    # ── Assemble scrollable body ────────────────────────────────────────────
    if is_desktop:
        scrollable = rx.el.div(
            pm_section,
            rx.divider(class_name="mx-4"),
            rx.cond(
                State.company_has_credits,
                rx.el.div(
                    credit_header,
                    credit_fields,
                    class_name=credit_section_class,
                ),
                rx.fragment(),
            ),
            rx.el.div(
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
            rx.cond(
                State.company_has_credits,
                rx.el.div(
                    credit_header,
                    credit_fields,
                    class_name=credit_section_class,
                ),
                rx.fragment(),
            ),
            card_option,
            wallet_option,
            mixed_option,
            footer,
        )


def payment_sidebar() -> rx.Component:
    """Sidebar derecho con método de pago y total."""
    scrollable, footer = _payment_form_body("desktop")
    return rx.el.aside(
        scrollable,
        footer,
        class_name="w-full max-w-[22rem] bg-white border rounded-lg shadow-sm overflow-hidden flex flex-col h-full",
    )


def payment_mobile_section() -> rx.Component:
    """Sección de pago para móvil y tablet."""
    (
        pm_section,
        credit_section,
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
        card_option,
        wallet_option,
        mixed_option,
        footer,
        class_name="bg-white rounded-xl border shadow-sm lg:hidden",
    )
