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
            rx.el.span(q["total_amount"], class_name="font-semibold text-slate-900 tabular-nums"),
            class_name="py-3 px-4 text-sm text-right",
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
                    rx.el.p(rx.el.span("Creado: ", class_name="text-slate-500"), rx.el.span(q["created_at"], class_name="text-sm")),
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
                        q["status"] == QuotationStatus.DRAFT,
                        rx.el.button(
                            "Marcar Enviado",
                            on_click=State.update_quotation_status(q["id"], QuotationStatus.SENT),
                            class_name=f"{BUTTON_STYLES.get('secondary', 'px-3 py-1.5 text-sm border border-slate-200 rounded-lg hover:bg-slate-50')}",
                        ),
                        rx.fragment(),
                    ),
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
            class_name="flex gap-3 justify-end",
        ),
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
                    class_name=INPUT_STYLES.get("default", "border rounded px-2 py-1 w-20 text-sm text-right"),
                ),
                class_name="py-2 px-3",
            ),
            rx.el.td(
                rx.el.input(
                    default_value=item["unit_price"],
                    type="number",
                    min="0",
                    step="0.01",
                    on_blur=lambda v: State.quot_update_item_price(idx, v),
                    class_name=INPUT_STYLES.get("default", "border rounded px-2 py-1 w-24 text-sm text-right"),
                ),
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
                    class_name=INPUT_STYLES.get("default", "border rounded px-2 py-1 w-16 text-sm text-right"),
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
            class_name="border-b border-slate-100",
        )

    return modal_container(
        is_open=State.show_quotation_form,
        on_close=State.close_quotation_form,
        title="Nuevo Presupuesto",
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
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                    ),
                    class_name="w-36",
                ),
                rx.el.div(
                    rx.el.label("Descuento global %", class_name=TYPOGRAPHY["label"]),
                    rx.el.input(
                        default_value=State.quot_global_discount,
                        type="text",
                        input_mode="decimal",
                        on_blur=State.set_quot_global_discount,
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                    ),
                    class_name="w-36",
                ),
                class_name="flex flex-wrap gap-4",
            ),

            # Buscador de productos
            rx.el.div(
                rx.el.label("Agregar producto", class_name=TYPOGRAPHY["label"]),
                rx.el.div(
                    rx.debounce_input(
                        rx.el.input(
                            placeholder="Buscar por nombre o código de barras...",
                            value=State.quot_search,
                            on_change=State.quot_search_products,
                            class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
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
                    class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full") + " h-20 resize-none",
                ),
            ),
        ],
        footer=rx.el.div(
            rx.el.button(
                rx.cond(State.is_loading, "Guardando...", "Guardar Presupuesto"),
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
    return rx.fragment(
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
                    rx.el.option("Convertidos", value="converted"),
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
                            rx.el.th("Total", class_name=TABLE_STYLES["header_cell"] + " text-right"),
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

        on_mount=State.page_init_presupuestos,
    )
