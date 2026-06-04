"""Página de Presupuestos / Cotizaciones."""
import reflex as rx
from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    INPUT_STYLES,
    SELECT_STYLES,
    CARD_STYLES,
    TABLE_STYLES,
    TYPOGRAPHY,
    RADIUS,
    SHADOWS,
    TRANSITIONS,
    BADGE_STYLES,
    page_header,
    modal_container,
    pagination_controls,
    empty_state,
    permission_guard,
)
from app.models.quotations import QuotationStatus


# ─── Colores de estado ────────────────────────────────────────────────────────

def _status_badge(status_label: rx.Var, status_color: rx.Var) -> rx.Component:
    return rx.el.span(
        status_label,
        class_name=rx.cond(
            status_color != "",
            f"{status_color} px-2 py-0.5 rounded-full text-xs font-semibold",
            "text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full text-xs font-semibold",
        ),
    )


# ─── Fila de la tabla ─────────────────────────────────────────────────────────

def _quotation_row(q: rx.Var) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.span(f"#{q['id']}", class_name="font-mono text-xs text-slate-500"),
            class_name="py-3 px-4 text-sm",
        ),
        rx.el.td(q["created_at"], class_name="py-3 px-4 text-sm text-slate-700"),
        rx.el.td(q["expires_at"], class_name="py-3 px-4 text-sm text-slate-500"),
        rx.el.td(
            _status_badge(q["status_label"], q["status_color"]),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.el.span(q["client_name"], class_name="text-sm text-slate-600 truncate max-w-[140px] block"),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.el.span(q["total_amount"], class_name="font-semibold text-slate-900 tabular-nums"),
            class_name="py-3 px-4 text-sm text-right",
        ),
        rx.el.td(
            q["created_by"],
            class_name="py-3 px-4 text-sm text-slate-700 hidden lg:table-cell",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.button(
                    rx.icon("eye", class_name="h-4 w-4"),
                    on_click=State.open_quotation_detail(q["id"]),
                    class_name=f"{BUTTON_STYLES.get('ghost', 'p-2 rounded-lg text-slate-500 hover:bg-slate-100')} p-1.5",
                    title="Ver detalle",
                ),
                rx.el.button(
                    rx.icon("download", class_name="h-4 w-4"),
                    on_click=State.download_quotation_pdf(q["id"]),
                    class_name=f"{BUTTON_STYLES.get('ghost', 'p-2 rounded-lg text-slate-500 hover:bg-slate-100')} p-1.5",
                    title="Descargar PDF",
                ),
                rx.cond(
                    q["status"] == "draft",
                    rx.el.button(
                        rx.icon("send", class_name="h-4 w-4"),
                        on_click=State.open_quot_send_modal(q["id"]),
                        class_name=f"{BUTTON_STYLES['icon_primary']} p-1.5",
                        title="Enviar al cliente",
                    ),
                    rx.fragment(),
                ),
                class_name="flex items-center gap-1 justify-end",
            ),
            class_name="py-3 px-4",
        ),
        class_name="border-b border-slate-100 hover:bg-slate-50/80 transition-colors",
    )


# ─── Card mobile ─────────────────────────────────────────────────────────────

def _quotation_card(q: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.span(f"#{q['id']}", class_name="font-mono text-xs text-slate-500"),
                _status_badge(q["status_label"], q["status_color"]),
                class_name="flex items-center gap-2",
            ),
            rx.el.span(
                q["total_amount"],
                class_name="font-bold text-lg text-indigo-700 tabular-nums",
            ),
            class_name="flex items-center justify-between",
        ),
        rx.el.div(
            rx.el.span(f"Creado: {q['created_at']}", class_name="text-xs text-slate-500"),
            rx.el.span(f"Vence: {q['expires_at']}", class_name="text-xs text-slate-400"),
            class_name="flex gap-3 mt-1",
        ),
        rx.el.p(q["client_name"], class_name="text-xs text-slate-500 mt-0.5 truncate"),
        rx.el.div(
            rx.el.button(
                rx.icon("eye", class_name="h-4 w-4"),
                "Ver",
                on_click=State.open_quotation_detail(q["id"]),
                class_name="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800",
            ),
            rx.el.button(
                rx.icon("download", class_name="h-4 w-4"),
                "PDF",
                on_click=State.download_quotation_pdf(q["id"]),
                class_name="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700",
            ),
            class_name="flex gap-4 mt-2",
        ),
        class_name=f"bg-white border border-slate-200 {RADIUS['lg']} p-4 {SHADOWS['sm']}",
    )


# ─── Modal: Detalle ───────────────────────────────────────────────────────────

def _quotation_detail_modal() -> rx.Component:
    q = State.selected_quotation
    items = State.selected_quotation_items

    def _item_row(item: rx.Var) -> rx.Component:
        return rx.el.tr(
            rx.el.td(item["description"], class_name="py-2 px-3 text-sm"),
            rx.el.td(item["quantity"], class_name="py-2 px-3 text-sm text-right tabular-nums"),
            rx.el.td(item["unit_price"], class_name="py-2 px-3 text-sm text-right tabular-nums"),
            rx.el.td(
                rx.cond(
                    item["discount_percentage"].to(float) > 0,
                    rx.el.span(f"{item['discount_percentage']}%", class_name="text-amber-600 text-xs"),
                    rx.el.span("—", class_name="text-slate-300 text-xs"),
                ),
                class_name="py-2 px-3 text-sm text-center",
            ),
            rx.el.td(item["subtotal"], class_name="py-2 px-3 text-sm text-right font-semibold tabular-nums"),
            class_name="border-b border-slate-100",
        )

    return modal_container(
        is_open=State.show_quotation_detail,
        on_close=State.close_quotation_detail,
        title="Detalle del Presupuesto",
        max_width="max-w-3xl",
        children=[
            # Info de cabecera
            rx.el.div(
                rx.el.div(
                    rx.el.p(rx.el.span("Nro: ", class_name="text-slate-500"), rx.el.span(f"#{q['id']}", class_name="font-mono font-semibold"), class_name="text-sm"),
                    rx.el.p(rx.el.span("Estado: ", class_name="text-slate-500"), _status_badge(q["status_label"], q["status_color"]), class_name="text-sm flex items-center gap-1"),
                    rx.el.p(rx.el.span("Cliente: ", class_name="text-slate-500"), rx.el.span(q["client_name"], class_name="text-sm font-medium"), class_name="text-sm"),
                    rx.el.p(rx.el.span("Creado: ", class_name="text-slate-500"), rx.el.span(q["created_at"], class_name="text-sm")),
                    rx.el.p(rx.el.span("Usuario: ", class_name="text-slate-500"), rx.el.span(q["created_by"], class_name="text-sm font-medium")),
                    rx.el.p(rx.el.span("Válido hasta: ", class_name="text-slate-500"), rx.el.span(q["expires_at"], class_name="text-sm font-medium text-amber-700")),
                    class_name="space-y-1",
                ),
                rx.el.div(
                    rx.el.p("Total", class_name="text-xs text-slate-500 uppercase tracking-wide"),
                    rx.el.p(q["total_amount"], class_name="text-2xl font-bold text-indigo-700 tabular-nums"),
                    rx.cond(
                        q["discount_percentage"].to(float) > 0,
                        rx.el.p(f"Desc. global: {q['discount_percentage']}%", class_name="text-xs text-amber-600"),
                        rx.fragment(),
                    ),
                    class_name="text-right",
                ),
                class_name="flex justify-between items-start",
            ),
            rx.divider(color="slate-100"),

            # Tabla de ítems
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("Descripción", class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Cant.", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                            rx.el.th("P. Unit.", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                            rx.el.th("Desc.%", class_name=TABLE_STYLES["header_cell"] + " text-center"),
                            rx.el.th("Subtotal", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                            class_name=TABLE_STYLES["header"],
                        ),
                    ),
                    rx.el.tbody(rx.foreach(items, _item_row)),
                    class_name="w-full",
                ),
                class_name="overflow-x-auto",
            ),

            # Notas
            rx.cond(
                q["notes"] != "",
                rx.el.div(
                    rx.el.p("Notas:", class_name="text-xs text-slate-500 font-medium uppercase tracking-wide"),
                    rx.el.p(q["notes"], class_name="text-sm text-slate-600 italic"),
                    class_name="bg-slate-50 rounded-lg p-3",
                ),
                rx.fragment(),
            ),

            # Acciones de estado
            rx.el.div(
                rx.el.p("Cambiar estado:", class_name="text-xs text-slate-500 font-medium"),
                rx.el.div(
                    rx.cond(
                        (q["status"] == QuotationStatus.SENT) | (q["status"] == QuotationStatus.DRAFT),
                        rx.el.button(
                            "Aceptado",
                            on_click=State.update_quotation_status(q["id"], QuotationStatus.ACCEPTED),
                            class_name=f"px-3 py-1.5 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        (q["status"] == QuotationStatus.SENT) | (q["status"] == QuotationStatus.DRAFT),
                        rx.el.button(
                            "Rechazado",
                            on_click=State.update_quotation_status(q["id"], QuotationStatus.REJECTED),
                            class_name=f"px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700",
                        ),
                        rx.fragment(),
                    ),
                    class_name="flex flex-wrap gap-2",
                ),
                class_name="space-y-2",
            ),
        ],
        footer=rx.el.div(
            rx.cond(
                (q["status"] == QuotationStatus.ACCEPTED) | (q["status"] == QuotationStatus.SENT),
                rx.el.button(
                    rx.icon("shopping-cart", class_name="h-4 w-4"),
                    "Convertir a Venta",
                    on_click=State.convert_quotation_to_cart(q["id"]),
                    class_name="flex items-center gap-2 px-3 py-1.5 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium",
                ),
                rx.fragment(),
            ),
            rx.cond(
                (q["status"] == QuotationStatus.DRAFT)
                | (q["status"] == QuotationStatus.SENT)
                | (q["status"] == QuotationStatus.ACCEPTED),
                rx.el.button(
                    rx.icon("pencil", class_name="h-4 w-4"),
                    "Editar",
                    on_click=State.open_quotation_edit(q["id"]),
                    class_name="flex items-center gap-2 px-3 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600 font-medium",
                ),
                rx.fragment(),
            ),
            rx.cond(
                (q["status"] == QuotationStatus.SENT) | (q["status"] == QuotationStatus.ACCEPTED),
                rx.el.button(
                    rx.icon("send", class_name="h-4 w-4"),
                    "Reenviar",
                    on_click=State.open_quot_send_modal(q["id"]),
                    class_name=f"flex items-center gap-2 {BUTTON_STYLES.get('secondary', 'px-3 py-1.5 text-sm border border-slate-200 rounded-lg hover:bg-slate-50')}",
                ),
                rx.fragment(),
            ),
            rx.el.button(
                rx.icon("download", class_name="h-4 w-4"),
                "Descargar PDF",
                on_click=State.download_quotation_pdf(q["id"]),
                class_name=f"flex items-center gap-2 {BUTTON_STYLES.get('primary', 'px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700')}",
            ),
            rx.el.button(
                "Cerrar",
                on_click=State.close_quotation_detail,
                class_name=f"{BUTTON_STYLES.get('secondary', 'px-4 py-2 border border-slate-200 rounded-lg hover:bg-slate-50')}",
            ),
            class_name="flex gap-3 justify-end flex-wrap",
        ),
    )


# ─── Modal: Enviar Presupuesto ───────────────────────────────────────────────

def _quotation_send_modal() -> rx.Component:
    """Modal para enviar un presupuesto al cliente via email o WhatsApp."""
    return modal_container(
        is_open=State.quot_send_open,
        on_close=State.close_quot_send_modal,
        title="Enviar Presupuesto",
        description=State.quot_send_client_name,
        children=[
            rx.el.div(
                # Resumen
                rx.el.div(
                    rx.el.p(
                        "Total: ",
                        rx.el.span(
                            State.currency_symbol, " ", State.quot_send_total_str,
                            class_name="font-bold text-indigo-600",
                        ),
                        "  ·  Válido hasta: ",
                        rx.el.span(State.quot_send_expires_at, class_name="font-medium text-amber-700"),
                        class_name="text-sm text-slate-600",
                    ),
                    class_name="px-4 py-2.5 bg-indigo-50 border border-indigo-100 rounded-lg",
                ),

                # ── Email ─────────────────────────────────────────────────────
                rx.el.div(
                    rx.el.div(
                        rx.icon("mail", class_name="h-4 w-4 text-indigo-500"),
                        rx.el.span("Enviar por Email", class_name="font-semibold text-slate-800 text-sm"),
                        class_name="flex items-center gap-2",
                    ),
                    rx.el.p(
                        "Se adjuntará el PDF completo del presupuesto.",
                        class_name="text-xs text-slate-500 mt-0.5",
                    ),
                    rx.el.div(
                        rx.el.input(
                            default_value=State.quot_send_recipient_email,
                            placeholder="email@cliente.com",
                            type="email",
                            on_change=State.set_quot_send_recipient,
                            class_name=INPUT_STYLES["default"] + " flex-1",
                        ),
                        rx.el.button(
                            rx.cond(
                                State.quot_send_loading,
                                rx.fragment(
                                    rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"),
                                    "Enviando...",
                                ),
                                rx.fragment(
                                    rx.icon("send", class_name="h-4 w-4"),
                                    "Enviar",
                                ),
                            ),
                            on_click=State.send_quotation_by_email,
                            disabled=State.quot_send_loading,
                            class_name=BUTTON_STYLES["primary_sm"],
                        ),
                        class_name="flex gap-2 mt-2",
                    ),
                    rx.cond(
                        State.quot_send_error != "",
                        rx.el.p(State.quot_send_error, class_name="text-xs text-red-600 mt-1"),
                        rx.fragment(),
                    ),
                    class_name="flex flex-col gap-1 p-4 border border-slate-200 rounded-xl bg-white",
                ),

                # ── WhatsApp ──────────────────────────────────────────────────
                rx.el.div(
                    rx.el.div(
                        rx.icon("message-circle", class_name="h-4 w-4 text-emerald-500"),
                        rx.el.span("Enviar por WhatsApp", class_name="font-semibold text-slate-800 text-sm"),
                        class_name="flex items-center gap-2",
                    ),
                    rx.el.p(
                        "Abre WhatsApp con el resumen del presupuesto listo para enviar al cliente.",
                        class_name="text-xs text-slate-500 mt-0.5",
                    ),
                    rx.el.button(
                        rx.icon("message-circle", class_name="h-4 w-4"),
                        "Abrir en WhatsApp",
                        on_click=State.send_quotation_whatsapp,
                        class_name="mt-2 flex items-center gap-2 h-9 px-4 text-sm font-medium rounded-lg"
                                   " bg-emerald-500 hover:bg-emerald-600 text-white transition-colors",
                    ),
                    class_name="flex flex-col gap-1 p-4 border border-slate-200 rounded-xl bg-white",
                ),

                # ── Solo marcar ───────────────────────────────────────────────
                rx.el.div(
                    rx.el.p(
                        "¿Ya contactaste al cliente por otro medio?",
                        class_name="text-xs text-slate-500",
                    ),
                    rx.el.button(
                        "Solo marcar como enviado",
                        on_click=lambda _: State.mark_quotation_sent_only(State.quot_send_quot_id),
                        class_name=BUTTON_STYLES["secondary_sm"],
                    ),
                    class_name="flex items-center justify-between gap-4 px-4 py-3"
                               " border border-dashed border-slate-200 rounded-xl",
                ),

                class_name="flex flex-col gap-3",
            ),
        ],
        footer=rx.el.button(
            "Cancelar",
            on_click=State.close_quot_send_modal,
            class_name=BUTTON_STYLES.get("secondary", "px-4 py-2 border border-slate-200 rounded-lg hover:bg-slate-50"),
        ),
        max_width="max-w-lg",
    )


# ─── Modal: Nuevo Presupuesto ─────────────────────────────────────────────────

def _new_quotation_modal() -> rx.Component:
    def _cart_item_row(item: rx.Var, idx: int) -> rx.Component:
        return rx.el.tr(
            rx.el.td(
                rx.el.p(item["description"], class_name="text-sm font-medium text-slate-900"),
                rx.el.p(item["barcode"], class_name="text-xs text-slate-400 font-mono"),
                class_name="py-2 px-3",
            ),
            rx.el.td(
                rx.el.input(
                    default_value=item["quantity"],
                    type="number",
                    min="0.01",
                    step="0.01",
                    on_blur=lambda v: State.quot_update_item_qty(idx, v),
                    class_name=INPUT_STYLES["default"],
                ),
                class_name="py-2 px-3",
            ),
            rx.el.td(
                rx.el.span(item["unit_price"], class_name="tabular-nums text-sm text-right block w-24"),
                class_name="py-2 px-3",
            ),
            rx.el.td(
                rx.el.input(
                    default_value=item["discount_percentage"],
                    type="number",
                    min="0",
                    max="100",
                    step="0.5",
                    on_blur=lambda v: State.quot_update_item_discount(idx, v),
                    class_name=INPUT_STYLES["default"],
                ),
                class_name="py-2 px-3",
            ),
            rx.el.td(
                rx.el.span(item["subtotal"], class_name="font-semibold tabular-nums text-sm"),
                class_name="py-2 px-3 text-right",
            ),
            rx.el.td(
                rx.el.button(
                    rx.icon("x", class_name="h-4 w-4"),
                    on_click=State.quot_remove_item(idx),
                    class_name="p-1 text-red-500 hover:bg-red-50 rounded",
                ),
                class_name="py-2 px-3 text-center",
            ),
            key=item["product_id"],
            class_name="border-b border-slate-100",
        )

    return modal_container(
        is_open=State.show_quotation_form,
        on_close=State.close_quotation_form,
        title=rx.cond(State.quot_edit_id > 0, "Editar Presupuesto", "Nuevo Presupuesto"),
        max_width="max-w-4xl",
        children=[
            # Datos del cliente y validez
            rx.el.div(
                rx.el.div(
                    rx.el.label("Cliente (opcional)", class_name=TYPOGRAPHY["label"]),
                    rx.el.select(
                        rx.el.option("Público en general", value=""),
                        rx.foreach(
                            State.quotation_clients,
                            lambda c: rx.el.option(c["name"], value=c["id"]),
                        ),
                        default_value=State.quot_client_id,
                        on_change=State.set_quot_client,
                        class_name=SELECT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                    ),
                    class_name="flex-1",
                ),
                rx.el.div(
                    rx.el.label("Validez (días)", class_name=TYPOGRAPHY["label"]),
                    rx.el.input(
                        default_value=State.quot_validity_days,
                        type="text",
                        input_mode="numeric",
                        on_blur=State.set_quot_validity,
                        class_name=INPUT_STYLES["default"],
                    ),
                    class_name="w-full sm:w-36",
                ),
                rx.el.div(
                    rx.el.label("Descuento global %", class_name=TYPOGRAPHY["label"]),
                    rx.el.input(
                        default_value=State.quot_global_discount,
                        type="text",
                        input_mode="decimal",
                        on_blur=State.set_quot_global_discount,
                        class_name=INPUT_STYLES["default"],
                    ),
                    class_name="w-full sm:w-36",
                ),
                class_name="flex flex-wrap gap-4",
            ),

            # Buscador de productos
            rx.el.div(
                rx.el.label("Agregar producto", class_name=TYPOGRAPHY["label"]),
                rx.el.div(
                    rx.debounce_input(
                        rx.input(
                            placeholder="Buscar por nombre o código de barras...",
                            value=State.quot_search,
                            on_change=State.quot_search_products,
                            class_name=INPUT_STYLES["default"],
                        ),
                        debounce_timeout=400,
                    ),
                    rx.cond(
                        State.quot_search_results.length() > 0,
                        rx.el.div(
                            rx.foreach(
                                State.quot_search_results,
                                lambda p: rx.el.div(
                                    rx.el.p(p["description"], class_name="text-sm font-medium"),
                                    rx.el.p(p["barcode"], class_name="text-xs text-slate-400 font-mono"),
                                    on_click=lambda: State.quot_add_product(p),
                                    class_name="px-3 py-2 hover:bg-indigo-50 cursor-pointer border-b border-slate-100",
                                ),
                            ),
                            class_name="absolute z-50 w-full bg-white border border-slate-200 rounded-xl shadow-lg max-h-60 overflow-y-auto",
                        ),
                        rx.fragment(),
                    ),
                    class_name="relative",
                ),
                class_name="space-y-1",
            ),

            # Tabla del carrito
            rx.cond(
                State.quot_cart.length() > 0,
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("Producto", class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Cant.", class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("P. Unit.", class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Desc.%", class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Subtotal", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("", class_name=TABLE_STYLES["header_cell"]),
                                class_name=TABLE_STYLES["header"],
                            ),
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                State.quot_cart,
                                lambda item, idx: _cart_item_row(item, idx),
                            )
                        ),
                        class_name="w-full",
                    ),
                    rx.el.div(
                        rx.el.span("Total del Presupuesto:", class_name="text-sm text-slate-500 font-medium"),
                        rx.el.span(
                            State.currency_symbol + State.quot_cart_total.to_string(),
                            class_name="text-xl font-bold text-indigo-700 tabular-nums",
                        ),
                        class_name="flex justify-end items-center gap-3 mt-3",
                    ),
                    class_name="overflow-x-auto",
                ),
                rx.el.div(
                    rx.icon("file-text", class_name="h-10 w-10 text-slate-300 mx-auto"),
                    rx.el.p("Busca y agrega productos al presupuesto.", class_name="text-sm text-slate-400 mt-2"),
                    class_name="text-center py-8",
                ),
            ),

            # Notas
            rx.el.div(
                rx.el.label("Notas (opcionales)", class_name=TYPOGRAPHY["label"]),
                rx.el.textarea(
                    placeholder="Condiciones, observaciones, etc.",
                    default_value=State.quot_notes,
                    on_blur=State.set_quot_notes,
                    class_name=INPUT_STYLES["default"] + " h-20 resize-none",
                ),
            ),
        ],
        footer=rx.el.div(
            rx.el.button(
                rx.cond(
                    State.is_loading,
                    "Guardando...",
                    rx.cond(State.quot_edit_id > 0, "Actualizar Presupuesto", "Guardar Presupuesto"),
                ),
                on_click=State.save_quotation,
                disabled=State.is_loading,
                class_name=f"flex items-center gap-2 {BUTTON_STYLES.get('primary', 'px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700')}",
            ),
            rx.el.button(
                "Cancelar",
                on_click=State.close_quotation_form,
                class_name=BUTTON_STYLES.get("secondary", "px-4 py-2 border border-slate-200 rounded-lg hover:bg-slate-50"),
            ),
            class_name="flex gap-3 justify-end",
        ),
    )


# ─── Página principal ─────────────────────────────────────────────────────────

def presupuestos_page() -> rx.Component:
    return permission_guard(
        has_permission=State.can_view_presupuestos,
        content=rx.fragment(
        page_header(
            "PRESUPUESTOS",
            "Crea y gestiona cotizaciones para tus clientes",
            actions=[
                rx.el.select(
                    rx.el.option("Todos los estados", value=""),
                    rx.el.option("Borradores", value="draft"),
                    rx.el.option("Enviados", value="sent"),
                    rx.el.option("Aceptados", value="accepted"),
                    rx.el.option("Rechazados", value="rejected"),
                    rx.el.option("Vencidos", value="expired"),
                    rx.el.option("Procesados", value="converted"),
                    default_value=State.quotations_filter_status,
                    on_change=State.set_quotations_filter_status,
                    class_name=SELECT_STYLES.get("default", "border rounded px-3 py-2 text-sm"),
                ),
                rx.el.button(
                    rx.icon("plus", class_name="h-4 w-4"),
                    "Nuevo Presupuesto",
                    on_click=State.open_quotation_form,
                    class_name=f"flex items-center gap-2 {BUTTON_STYLES['primary']} text-sm",
                ),
            ],
        ),

        # Tabla desktop
        rx.el.div(
            rx.cond(
                State.quotations.length() > 0,
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("Nro.", class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Creado", class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Vence", class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Estado", class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Cliente", class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Total", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                            rx.el.th("Usuario", class_name=TABLE_STYLES["header_cell"] + " hidden lg:table-cell"),
                            rx.el.th("Acciones", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                            class_name=TABLE_STYLES["header"],
                        ),
                    ),
                    rx.el.tbody(rx.foreach(State.quotations, _quotation_row)),
                    class_name="w-full",
                ),
                empty_state("No hay presupuestos. Crea el primero con el botón de arriba.", "file-text"),
            ),
            class_name="hidden md:block overflow-x-auto bg-white border border-slate-200 rounded-xl shadow-sm",
        ),

        # Cards mobile
        rx.el.div(
            rx.cond(
                State.quotations.length() > 0,
                rx.foreach(State.quotations, _quotation_card),
                empty_state("No hay presupuestos aún.", "file-text"),
            ),
            class_name="flex flex-col gap-3 md:hidden",
        ),

        # Paginación
        pagination_controls(
            current_page=State.quotations_page,
            total_pages=State.quotations_total_pages,
            on_prev=State.quotations_prev_page,
            on_next=State.quotations_next_page,
        ),

        # Modales
        _new_quotation_modal(),
        _quotation_detail_modal(),
        _quotation_send_modal(),
        # rx.fragment no soporta on_mount; la carga inicial la dispara
        # `app.add_page(on_load=State.page_init_presupuestos)` en app/app.py.
        ),
        redirect_message="Acceso denegado a Presupuestos",
    )
