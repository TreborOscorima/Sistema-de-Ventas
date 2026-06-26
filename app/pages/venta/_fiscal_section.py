import reflex as rx
from app.state import State


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
                            "rounded-md placeholder-slate-400 focus:outline-none focus:ring-1 "
                            "focus:ring-indigo-500/20 focus:border-indigo-500"
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


def _coupon_input() -> rx.Component:
    """Input para ingresar/aplicar un cupón de descuento al carrito."""
    return rx.el.div(
        rx.el.span(
            rx.icon("ticket", class_name="h-3.5 w-3.5 inline mr-1 text-violet-500"),
            "Cupón",
            class_name="text-xs font-medium text-slate-500",
        ),
        rx.el.div(
            rx.el.input(
                placeholder="Código",
                default_value=State.cart_coupon_code,
                on_change=State.set_cart_coupon_input,
                disabled=State.cart_coupon_status == "applied",
                key=State.last_sale_id,
                class_name=(
                    "flex-1 border border-slate-200 rounded-lg px-3 py-1.5 text-sm uppercase "
                    "placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 "
                    "disabled:bg-emerald-50 disabled:text-emerald-700 disabled:font-semibold"
                ),
            ),
            rx.cond(
                State.cart_coupon_status == "applied",
                rx.el.button(
                    rx.icon("x", class_name="h-4 w-4"),
                    on_click=State.clear_cart_coupon,
                    title="Quitar cupón",
                    class_name="px-2 py-1.5 rounded-lg text-red-500 hover:bg-red-50 transition-colors",
                ),
                rx.el.button(
                    "Aplicar",
                    on_click=State.apply_cart_coupon,
                    class_name="px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors",
                ),
            ),
            class_name="flex items-center gap-1.5 mt-1",
        ),
        rx.cond(
            State.cart_coupon_status == "invalid",
            rx.el.p(State.cart_coupon_message, class_name="text-xs text-red-600 mt-1"),
            rx.cond(
                State.cart_coupon_status == "applied",
                rx.el.p(State.cart_coupon_message, class_name="text-xs text-emerald-600 mt-1"),
                rx.fragment(),
            ),
        ),
        class_name="flex flex-col px-3 py-2 border-b border-slate-100",
    )


def _receipt_type_selector() -> rx.Component:
    """Selector de tipo de comprobante fiscal (boleta/factura/nota de venta).

    Solo visible si la empresa tiene billing activo.
    Detecta automáticamente factura cuando el cliente tiene RUC/CUIT.
    """
    from app.components.ui import BUTTON_STYLES
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
                        BUTTON_STYLES["tab_active"],
                        BUTTON_STYLES["tab_inactive"],
                    ),
                ),
                rx.el.button(
                    "Boleta",
                    on_click=State.set_sale_receipt_type("boleta"),
                    class_name=rx.cond(
                        State.sale_receipt_type_selection == "boleta",
                        BUTTON_STYLES["tab_active"],
                        BUTTON_STYLES["tab_inactive"],
                    ),
                ),
                rx.el.button(
                    "Factura",
                    on_click=State.set_sale_receipt_type("factura"),
                    class_name=rx.cond(
                        State.sale_receipt_type_selection == "factura",
                        BUTTON_STYLES["tab_active"],
                        BUTTON_STYLES["tab_inactive"],
                    ),
                ),
                class_name="flex gap-1 w-full items-stretch min-h-[44px]",
            ),
            class_name="flex flex-col gap-1 px-3 py-2 bg-slate-50 rounded-lg",
        ),
        rx.fragment(),
    )
