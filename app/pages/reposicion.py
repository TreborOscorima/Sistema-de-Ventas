"""Página de Órdenes de Compra — POs sugeridas por stock bajo."""
import reflex as rx

from app.state import State
from app.components.ui import (
    BADGE_STYLES,
    BUTTON_STYLES,
    CARD_STYLES,
    INPUT_STYLES,
    SELECT_STYLES,
    SPACING,
    TABLE_STYLES,
    TYPOGRAPHY,
    empty_state,
    modal_container,
    page_title,
    permission_guard,
)


def _status_badge(status: rx.Var[str]) -> rx.Component:
    """Badge de estado usando tokens centralizados BADGE_STYLES."""
    return rx.match(
        status,
        ("draft",     rx.el.span("Borrador", class_name=BADGE_STYLES["warning"])),
        ("sent",      rx.el.span("Enviada",  class_name=BADGE_STYLES["info"])),
        ("received",  rx.el.span("Recibida", class_name=BADGE_STYLES["success"])),
        ("cancelled", rx.el.span("Cancelada",class_name=BADGE_STYLES["neutral"])),
        rx.el.span(status, class_name=BADGE_STYLES["neutral"]),
    )


def _reorder_item_row(item: rx.Var[dict], index: rx.Var[int]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(item["barcode"],                class_name="py-2.5 px-4 text-xs font-mono text-slate-500"),
        rx.el.td(item["description"],            class_name="py-2.5 px-4 text-sm font-medium text-slate-800"),
        rx.el.td(
            item["current_stock"].to_string(),
            class_name="py-2.5 px-4 text-right text-red-600 font-semibold tabular-nums",
        ),
        rx.el.td(
            item["min_stock_alert"].to_string(),
            class_name="py-2.5 px-4 text-right text-slate-500 tabular-nums",
        ),
        rx.el.td(
            rx.el.input(
                default_value=item["suggested_quantity"].to_string(),
                type="number",
                min="0.0001",
                step="1",
                on_blur=lambda val: State.update_confirm_item_quantity(index, val),
                class_name=INPUT_STYLES["default"] + " w-24 text-right",
            ),
            class_name="py-2.5 px-4",
        ),
        rx.el.td(
            item["unit_cost_str"],
            class_name="py-2.5 px-4 text-right text-slate-600 tabular-nums",
        ),
        class_name="border-b border-slate-100 hover:bg-slate-50 transition-colors",
    )


def _supplier_group_card(group: rx.Var[dict]) -> rx.Component:
    """Tarjeta por proveedor: blanca con acento indigo si tiene proveedor, ámbar si no."""
    no_supplier = group["supplier_id"] == 0

    return rx.el.div(
        # ── Cabecera: ícono + nombre + total ──────────────────────────────────
        rx.el.div(
            rx.el.div(
                rx.cond(
                    no_supplier,
                    rx.icon("circle-alert", class_name="h-5 w-5 text-amber-500 mt-0.5 flex-shrink-0"),
                    rx.icon("truck",        class_name="h-5 w-5 text-indigo-400 mt-0.5 flex-shrink-0"),
                ),
                rx.el.div(
                    rx.el.h3(
                        group["supplier_name"],
                        class_name=rx.cond(
                            no_supplier,
                            "text-base font-semibold text-amber-800",
                            "text-base font-semibold text-slate-800",
                        ),
                    ),
                    rx.el.span(
                        group["item_count"].to_string() + " productos bajo umbral",
                        class_name=rx.cond(
                            no_supplier,
                            BADGE_STYLES["warning"] + " mt-0.5 w-fit",
                            BADGE_STYLES["info"]    + " mt-0.5 w-fit",
                        ),
                    ),
                    class_name="flex flex-col gap-1",
                ),
                class_name="flex items-start gap-3 flex-1 min-w-0",
            ),
            rx.el.div(
                rx.el.p("Total estimado", class_name=TYPOGRAPHY["caption"]),
                rx.el.p(
                    State.currency_symbol, " ", group["total_estimated_str"].to(str),
                    class_name=rx.cond(
                        no_supplier,
                        "text-xl font-bold text-amber-700 tabular-nums",
                        "text-xl font-bold text-indigo-600 tabular-nums",
                    ),
                ),
                class_name="text-right flex-shrink-0",
            ),
            class_name="flex items-start justify-between gap-4",
        ),
        # ── Pie: mensaje de ayuda + botón de acción ───────────────────────────
        rx.el.div(
            rx.cond(
                no_supplier,
                rx.el.p(
                    "Asigne un proveedor predeterminado a cada producto desde Inventario.",
                    class_name="text-xs text-amber-700 flex-1",
                ),
                rx.fragment(),
            ),
            rx.el.button(
                rx.cond(
                    no_supplier,
                    rx.fragment(
                        rx.icon("circle-alert", class_name="h-4 w-4"),
                        "Sin proveedor asignado",
                    ),
                    rx.fragment(
                        rx.icon("file-plus", class_name="h-4 w-4"),
                        "Crear orden de compra",
                    ),
                ),
                on_click=lambda _: State.open_reorder_confirm_modal(group["supplier_id"]),
                disabled=no_supplier,
                class_name=rx.cond(
                    no_supplier,
                    "flex items-center gap-2 h-9 px-3 text-sm font-medium rounded-lg"
                    " bg-amber-100 text-amber-600 cursor-not-allowed opacity-60",
                    BUTTON_STYLES["primary_sm"],
                ),
            ),
            class_name=rx.cond(
                no_supplier,
                "flex items-center justify-between gap-3 pt-3 border-t border-amber-200",
                "flex items-center justify-end   gap-3 pt-3 border-t border-slate-100",
            ),
        ),
        class_name=rx.cond(
            no_supplier,
            "bg-amber-50 border border-amber-200 rounded-xl p-5 sm:p-6 shadow-sm flex flex-col gap-4",
            CARD_STYLES["default"] + " flex flex-col gap-4",
        ),
    )


def _reorder_confirm_modal() -> rx.Component:
    return modal_container(
        is_open=State.reorder_confirm_open,
        on_close=State.close_reorder_confirm_modal,
        title="Confirmar orden de compra",
        description=State.reorder_confirm_supplier_name,
        children=[
            rx.el.div(
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("Código",     class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Producto",   class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Stock",      class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                                rx.el.th("Mínimo",     class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("A pedir",    class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("Costo unit.",class_name=TABLE_STYLES["header_cell"] + " text-right"),
                            ),
                            class_name=TABLE_STYLES["header"],
                        ),
                        rx.el.tbody(
                            rx.foreach(State.reorder_confirm_items, _reorder_item_row),
                        ),
                        class_name="w-full text-sm min-w-[500px]",
                    ),
                    class_name="max-h-96 overflow-x-auto overflow-y-auto border border-slate-200 rounded-lg",
                ),
                rx.el.div(
                    rx.el.label("Notas (opcional)", class_name="text-sm font-medium text-slate-700"),
                    rx.el.textarea(
                        default_value=State.reorder_confirm_notes,
                        placeholder="Referencia, urgencia, condiciones de pago...",
                        on_blur=lambda val: State.set_reorder_confirm_notes(val),
                        class_name=INPUT_STYLES["default"] + " h-20",
                        max_length=500,
                    ),
                    class_name="flex flex-col gap-1 mt-4",
                ),
                rx.el.div(
                    rx.el.p("Total estimado:", class_name="text-slate-600 font-medium"),
                    rx.el.p(
                        State.currency_symbol + " " + State.reorder_confirm_total_str,
                        class_name="text-2xl font-bold text-indigo-600 tabular-nums",
                    ),
                    class_name="flex items-center justify-between mt-4 px-4 py-3 bg-indigo-50 border border-indigo-100 rounded-lg",
                ),
                class_name="flex flex-col gap-2",
            ),
        ],
        footer=rx.el.div(
            rx.el.button(
                "Cancelar",
                on_click=State.close_reorder_confirm_modal,
                class_name=BUTTON_STYLES["secondary"],
            ),
            rx.el.button(
                rx.icon("file-plus", class_name="h-4 w-4"),
                "Crear borrador",
                on_click=State.confirm_create_purchase_order,
                class_name=BUTTON_STYLES["primary"],
            ),
            class_name="flex justify-end gap-2",
        ),
        max_width="max-w-3xl",
    )


def _po_detail_item_row(item: rx.Var[dict]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(item["barcode"],           class_name="py-2.5 px-4 text-xs font-mono text-slate-500"),
        rx.el.td(item["description"],       class_name="py-2.5 px-4 text-sm font-medium text-slate-800"),
        rx.el.td(item["current_stock"],     class_name="py-2.5 px-4 text-right text-red-600 tabular-nums text-sm"),
        rx.el.td(item["min_stock_alert"],   class_name="py-2.5 px-4 text-right text-slate-500 tabular-nums text-sm"),
        rx.el.td(item["suggested_quantity"],class_name="py-2.5 px-4 text-right font-semibold tabular-nums text-sm"),
        rx.el.td(item["unit"],              class_name="py-2.5 px-4 text-slate-500 text-sm"),
        rx.el.td(item["unit_cost"],         class_name="py-2.5 px-4 text-right tabular-nums text-sm"),
        rx.el.td(item["subtotal"],          class_name="py-2.5 px-4 text-right font-semibold tabular-nums text-sm text-indigo-700"),
        class_name="border-b border-slate-100 hover:bg-slate-50 transition-colors",
    )


def _po_detail_modal() -> rx.Component:
    return modal_container(
        is_open=State.po_detail_open,
        on_close=State.close_po_detail,
        title="Detalle de Orden de Compra",
        description=State.po_detail_supplier,
        children=[
            rx.el.div(
                # Metadata row
                rx.el.div(
                    _status_badge(State.po_detail_status),
                    rx.cond(
                        State.po_detail_auto_generated,
                        rx.el.span("Auto-generada", class_name=BADGE_STYLES["info"]),
                        rx.el.span("Manual", class_name=BADGE_STYLES["neutral"]),
                    ),
                    rx.el.span(
                        "# " + State.po_detail_id.to_string() + " · " + State.po_detail_created_at,
                        class_name=TYPOGRAPHY["caption"],
                    ),
                    class_name="flex items-center gap-2 flex-wrap",
                ),
                # Items table
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("Código",  class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Producto",class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Stock",   class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("Mínimo",  class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("Pedido",  class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("Unidad",  class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Costo",   class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("Subtotal",class_name=TABLE_STYLES["header_cell"] + " text-right"),
                            ),
                            class_name=TABLE_STYLES["header"],
                        ),
                        rx.el.tbody(
                            rx.foreach(State.po_detail_items, _po_detail_item_row),
                        ),
                        class_name="w-full text-sm min-w-[640px]",
                    ),
                    class_name="max-h-80 overflow-x-auto overflow-y-auto border border-slate-200 rounded-lg",
                ),
                # Notes
                rx.cond(
                    State.po_detail_notes != "",
                    rx.el.div(
                        rx.el.p("Notas:", class_name="text-sm font-medium text-slate-700"),
                        rx.el.p(State.po_detail_notes, class_name="text-sm text-slate-600 italic"),
                        class_name="flex flex-col gap-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg",
                    ),
                    rx.fragment(),
                ),
                # Total
                rx.el.div(
                    rx.el.p("Total de la orden:", class_name="text-slate-600 font-medium"),
                    rx.el.p(
                        State.currency_symbol + " " + State.po_detail_total_str,
                        class_name="text-2xl font-bold text-indigo-600 tabular-nums",
                    ),
                    class_name="flex items-center justify-between px-4 py-3 bg-indigo-50 border border-indigo-100 rounded-lg",
                ),
                class_name="flex flex-col gap-4",
            ),
        ],
        footer=rx.el.div(
            rx.el.button(
                "Cerrar",
                on_click=State.close_po_detail,
                class_name=BUTTON_STYLES["secondary"],
            ),
            rx.cond(
                State.po_detail_status == "sent",
                rx.el.button(
                    rx.icon("package-check", class_name="h-4 w-4"),
                    "Marcar como recibida",
                    on_click=lambda _: State.mark_po_received(State.po_detail_id),
                    class_name=BUTTON_STYLES["primary"],
                ),
                rx.fragment(),
            ),
            class_name="flex justify-end gap-2",
        ),
        max_width="max-w-4xl",
    )


def _po_row(po: rx.Var[dict]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            "#" + po["id"].to_string(),
            class_name="py-3 px-4 font-mono text-xs text-slate-500",
        ),
        rx.el.td(
            rx.el.div(
                po["supplier_name"],
                rx.cond(
                    po["auto_generated"],
                    rx.el.span("Auto", class_name=BADGE_STYLES["info"]),
                    rx.el.span("Manual", class_name=BADGE_STYLES["neutral"]),
                ),
                class_name="flex items-center gap-2",
            ),
            class_name="py-3 px-4 font-medium text-slate-800",
        ),
        rx.el.td(_status_badge(po["status"]), class_name="py-3 px-4"),
        rx.el.td(
            po["item_count"].to_string() + " ítem(s)",
            class_name="py-3 px-4 text-center text-sm text-slate-600 tabular-nums",
        ),
        rx.el.td(
            State.currency_symbol, " ", po["total_amount_str"].to(str),
            class_name="py-3 px-4 text-right font-semibold tabular-nums text-slate-800",
        ),
        rx.el.td(
            po["created_at"],
            class_name="py-3 px-4 text-xs text-slate-400 hidden md:table-cell",
        ),
        rx.el.td(
            po["created_by"],
            class_name="py-3 px-4 text-sm text-slate-700 hidden lg:table-cell",
        ),
        rx.el.td(
            rx.el.div(
                # Imprimir PDF (siempre)
                rx.el.button(
                    rx.icon("printer", class_name="h-4 w-4"),
                    on_click=lambda _: State.download_po_pdf(po["id"]),
                    title="Descargar PDF",
                    class_name=BUTTON_STYLES["icon_primary"],
                ),
                # Ver detalle (siempre)
                rx.el.button(
                    rx.icon("eye", class_name="h-4 w-4"),
                    on_click=lambda _: State.open_po_detail(po["id"]),
                    title="Ver detalle",
                    class_name=BUTTON_STYLES["icon_primary"],
                ),
                # Editar borrador (solo draft)
                rx.cond(
                    po["status"] == "draft",
                    rx.el.button(
                        rx.icon("pencil", class_name="h-4 w-4"),
                        on_click=lambda _: State.open_po_edit(po["id"]),
                        title="Editar borrador",
                        class_name="p-1.5 rounded-lg text-amber-600 hover:bg-amber-50 transition-colors",
                    ),
                    rx.fragment(),
                ),
                # Enviar al proveedor (solo draft) → abre modal de envío
                rx.cond(
                    po["status"] == "draft",
                    rx.el.button(
                        rx.icon("send", class_name="h-4 w-4"),
                        on_click=lambda _: State.open_po_send_modal(po["id"]),
                        title="Enviar al proveedor",
                        class_name=BUTTON_STYLES["icon_primary"],
                    ),
                    rx.fragment(),
                ),
                # Marcar recibida (solo sent)
                rx.cond(
                    po["status"] == "sent",
                    rx.el.button(
                        rx.icon("package-check", class_name="h-4 w-4"),
                        on_click=lambda _: State.mark_po_received(po["id"]),
                        title="Marcar como recibida",
                        class_name="p-1.5 rounded-lg text-emerald-600 hover:bg-emerald-50 transition-colors",
                    ),
                    rx.fragment(),
                ),
                # Cancelar (draft o sent)
                rx.cond(
                    (po["status"] != "received") & (po["status"] != "cancelled"),
                    rx.el.button(
                        rx.icon("x", class_name="h-4 w-4"),
                        on_click=lambda _: State.cancel_po(po["id"]),
                        title="Cancelar orden",
                        class_name=BUTTON_STYLES["icon_danger"],
                    ),
                    rx.fragment(),
                ),
                class_name="flex items-center justify-center gap-1",
            ),
            class_name="py-3 px-4 text-center",
        ),
        class_name="border-b border-slate-100 hover:bg-slate-50 transition-colors",
    )


def _send_modal() -> rx.Component:
    """Modal para enviar una PO al proveedor via email o WhatsApp."""
    return modal_container(
        is_open=State.po_send_open,
        on_close=State.close_po_send_modal,
        title="Enviar Orden de Compra",
        description=State.po_send_supplier_name,
        children=[
            rx.el.div(
                # Resumen rápido
                rx.el.div(
                    rx.el.p(
                        "Total: ",
                        rx.el.span(
                            State.currency_symbol, " ", State.po_send_total_str,
                            class_name="font-bold text-indigo-600",
                        ),
                        class_name="text-sm text-slate-600",
                    ),
                    class_name="px-4 py-2.5 bg-indigo-50 border border-indigo-100 rounded-lg",
                ),

                # ── Opción 1: Email ──────────────────────────────────────────
                rx.el.div(
                    rx.el.div(
                        rx.icon("mail", class_name="h-4 w-4 text-indigo-500"),
                        rx.el.span("Enviar por Email", class_name="font-semibold text-slate-800 text-sm"),
                        class_name="flex items-center gap-2",
                    ),
                    rx.el.p(
                        "Se adjuntará el PDF completo de la orden.",
                        class_name="text-xs text-slate-500 mt-0.5",
                    ),
                    rx.el.div(
                        rx.el.input(
                            default_value=State.po_send_recipient_email,
                            placeholder="email@proveedor.com",
                            type="email",
                            on_change=State.set_po_send_recipient,
                            class_name=INPUT_STYLES["default"] + " flex-1",
                        ),
                        rx.el.button(
                            rx.cond(
                                State.po_send_loading,
                                rx.fragment(
                                    rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"),
                                    "Enviando...",
                                ),
                                rx.fragment(
                                    rx.icon("send", class_name="h-4 w-4"),
                                    "Enviar",
                                ),
                            ),
                            on_click=State.send_po_by_email,
                            disabled=State.po_send_loading,
                            class_name=BUTTON_STYLES["primary_sm"],
                        ),
                        class_name="flex gap-2 mt-2",
                    ),
                    rx.cond(
                        State.po_send_error != "",
                        rx.el.p(State.po_send_error, class_name="text-xs text-red-600 mt-1"),
                        rx.fragment(),
                    ),
                    class_name="flex flex-col gap-1 p-4 border border-slate-200 rounded-xl bg-white",
                ),

                # ── Opción 2: WhatsApp ───────────────────────────────────────
                rx.el.div(
                    rx.el.div(
                        rx.icon("message-circle", class_name="h-4 w-4 text-emerald-500"),
                        rx.el.span("Enviar por WhatsApp", class_name="font-semibold text-slate-800 text-sm"),
                        class_name="flex items-center gap-2",
                    ),
                    rx.el.p(
                        "Abre WhatsApp con el resumen de la orden listo para enviar al proveedor.",
                        class_name="text-xs text-slate-500 mt-0.5",
                    ),
                    rx.el.button(
                        rx.icon("message-circle", class_name="h-4 w-4"),
                        "Abrir en WhatsApp",
                        on_click=State.send_po_whatsapp,
                        class_name="mt-2 flex items-center gap-2 h-9 px-4 text-sm font-medium rounded-lg"
                                   " bg-emerald-500 hover:bg-emerald-600 text-white transition-colors",
                    ),
                    class_name="flex flex-col gap-1 p-4 border border-slate-200 rounded-xl bg-white",
                ),

                # ── Opción 3: Solo marcar ────────────────────────────────────
                rx.el.div(
                    rx.el.p(
                        "¿Ya contactaste al proveedor por otro medio?",
                        class_name="text-xs text-slate-500",
                    ),
                    rx.el.button(
                        "Solo marcar como enviada",
                        on_click=lambda _: State.mark_po_sent_only(State.po_send_po_id),
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
            on_click=State.close_po_send_modal,
            class_name=BUTTON_STYLES["secondary"],
        ),
        max_width="max-w-lg",
    )


def _edit_item_row(item: rx.Var[dict], index: rx.Var[int]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(item["barcode"],        class_name="py-2 px-3 text-xs font-mono text-slate-500"),
        rx.el.td(item["description"],    class_name="py-2 px-3 text-sm font-medium text-slate-800"),
        rx.el.td(item["current_stock"],  class_name="py-2 px-3 text-right text-red-600 tabular-nums text-sm"),
        rx.el.td(item["min_stock_alert"],class_name="py-2 px-3 text-right text-slate-500 tabular-nums text-sm"),
        rx.el.td(
            rx.el.input(
                default_value=item["suggested_quantity"].to_string(),
                type="number",
                min="0.0001",
                step="1",
                on_blur=lambda val: State.update_po_edit_item_qty(index, val),
                class_name=INPUT_STYLES["default"] + " w-24 text-right py-1",
            ),
            class_name="py-2 px-3",
        ),
        rx.el.td(item["unit_cost_str"],  class_name="py-2 px-3 text-right text-slate-600 tabular-nums text-sm"),
        rx.el.td(item["subtotal_str"],   class_name="py-2 px-3 text-right font-semibold tabular-nums text-sm text-indigo-700"),
        rx.el.td(
            rx.el.button(
                rx.icon("trash-2", class_name="h-3.5 w-3.5"),
                on_click=lambda _: State.delete_po_edit_item(index),
                title="Quitar ítem",
                class_name=BUTTON_STYLES["icon_danger"],
            ),
            class_name="py-2 px-3 text-center",
        ),
        class_name="border-b border-slate-100 hover:bg-slate-50 transition-colors",
    )


def _edit_po_modal() -> rx.Component:
    """Modal de edición completa de una PO borrador."""
    return modal_container(
        is_open=State.po_edit_open,
        on_close=State.close_po_edit,
        title="Editar Borrador",
        description="Solo borradores pueden editarse. Los cambios reemplazan los ítems actuales.",
        children=[
            rx.el.div(
                # ── Proveedor ────────────────────────────────────────────────
                rx.el.div(
                    rx.el.label("Proveedor", class_name="text-sm font-medium text-slate-700"),
                    rx.el.select(
                        rx.foreach(
                            State.po_edit_suppliers,
                            lambda s: rx.el.option(s["name"], value=s["id"].to(str)),
                        ),
                        value=State.po_edit_supplier_id.to_string(),
                        on_change=State.set_po_edit_supplier,
                        class_name=SELECT_STYLES["default"],
                    ),
                    class_name="flex flex-col gap-1",
                ),

                # ── Tabla de ítems ───────────────────────────────────────────
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("Código",    class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Producto",  class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Stock",     class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("Mínimo",    class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("Cantidad",  class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("Costo",     class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("Subtotal",  class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("",          class_name=TABLE_STYLES["header_cell"]),
                            ),
                            class_name=TABLE_STYLES["header"],
                        ),
                        rx.el.tbody(
                            rx.foreach(State.po_edit_items, _edit_item_row),
                        ),
                        class_name="w-full text-sm",
                    ),
                    class_name="max-h-72 overflow-auto border border-slate-200 rounded-lg",
                ),

                # ── Notas ────────────────────────────────────────────────────
                rx.el.div(
                    rx.el.label("Notas (opcional)", class_name="text-sm font-medium text-slate-700"),
                    rx.el.textarea(
                        default_value=State.po_edit_notes,
                        placeholder="Referencia, condiciones, urgencia...",
                        on_blur=lambda val: State.set_po_edit_notes(val),
                        class_name=INPUT_STYLES["default"] + " h-16",
                        max_length=500,
                    ),
                    class_name="flex flex-col gap-1",
                ),

                # ── Total ────────────────────────────────────────────────────
                rx.el.div(
                    rx.el.p("Total estimado:", class_name="text-slate-600 font-medium text-sm"),
                    rx.el.p(
                        State.currency_symbol, " ", State.po_edit_total_str,
                        class_name="text-xl font-bold text-indigo-600 tabular-nums",
                    ),
                    class_name="flex items-center justify-between px-4 py-3"
                               " bg-indigo-50 border border-indigo-100 rounded-lg",
                ),

                class_name="flex flex-col gap-4",
            ),
        ],
        footer=rx.el.div(
            rx.el.button(
                "Cancelar",
                on_click=State.close_po_edit,
                class_name=BUTTON_STYLES["secondary"],
            ),
            rx.el.button(
                rx.icon("save", class_name="h-4 w-4"),
                "Guardar cambios",
                on_click=State.save_po_edit,
                class_name=BUTTON_STYLES["primary"],
            ),
            class_name="flex justify-end gap-2",
        ),
        max_width="max-w-5xl",
    )


def reposicion_page() -> rx.Component:
    """Página de reposición automática."""

    # ── Sección de sugerencias ────────────────────────────────────────────────
    suggestions_section = rx.el.div(
        # Encabezado
        rx.el.div(
            rx.el.div(
                rx.icon("package-search", class_name="h-5 w-5 text-indigo-500"),
                rx.el.h2("Sugerencias de compra", class_name=TYPOGRAPHY["section_title"]),
                class_name="flex items-center gap-2",
            ),
            rx.el.button(
                rx.cond(
                    State.reorder_loading,
                    rx.fragment(
                        rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"),
                        "Escaneando...",
                    ),
                    rx.fragment(
                        rx.icon("refresh-cw", class_name="h-4 w-4"),
                        "Escanear stock bajo",
                    ),
                ),
                on_click=State.load_reorder_suggestions,
                disabled=State.reorder_loading,
                class_name=BUTTON_STYLES["secondary_sm"],
            ),
            class_name="flex items-center justify-between",
        ),
        # Resumen cuando hay resultados
        rx.cond(
            State.has_reorder_suggestions,
            rx.el.div(
                rx.icon("triangle-alert", class_name="h-4 w-4 text-amber-500 flex-shrink-0"),
                rx.el.p(
                    State.reorder_total_items.to_string()
                    + " productos bajo umbral en "
                    + State.reorder_groups.length().to_string()
                    + " proveedor(es). Revise y confirme las órdenes.",
                    class_name="text-sm text-amber-800",
                ),
                class_name="flex items-center gap-2 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg",
            ),
            rx.fragment(),
        ),
        # Tarjetas de grupos o estado vacío
        rx.cond(
            State.has_reorder_suggestions,
            rx.el.div(
                rx.foreach(State.reorder_groups, _supplier_group_card),
                class_name="flex flex-col gap-3",
            ),
            empty_state(
                title="Sin productos bajo umbral",
                message="Presione 'Escanear stock bajo' para detectar productos que requieren reposición.",
                icon="package-check",
            ),
        ),
        class_name=CARD_STYLES["default"] + " flex flex-col gap-4",
    )

    # ── Sección de órdenes de compra ──────────────────────────────────────────
    orders_section = rx.el.div(
        # Encabezado
        rx.el.div(
            rx.el.div(
                rx.icon("clipboard-list", class_name="h-5 w-5 text-slate-400"),
                rx.el.h2("Órdenes de compra", class_name=TYPOGRAPHY["section_title"]),
                class_name="flex items-center gap-2",
            ),
            rx.el.div(
                rx.el.label(
                    "Filtrar por estado:",
                    class_name="text-sm text-slate-500 whitespace-nowrap shrink-0",
                ),
                rx.el.select(
                    rx.el.option("Todas",     value="all"),
                    rx.el.option("Borradores",value="draft"),
                    rx.el.option("Enviadas",  value="sent"),
                    rx.el.option("Recibidas", value="received"),
                    rx.el.option("Canceladas",value="cancelled"),
                    default_value=State.po_status_filter,
                    on_change=State.set_po_status_filter,
                    class_name=SELECT_STYLES["default"],
                ),
                class_name="flex flex-wrap items-center gap-2",
            ),
            class_name="flex flex-wrap items-center justify-between gap-2",
        ),
        # Tabla de POs
        rx.cond(
            State.purchase_orders_list.length() > 0,
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("ID",         class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Proveedor",  class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Estado",     class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Ítems",      class_name=TABLE_STYLES["header_cell"] + " text-center"),
                            rx.el.th("Total",      class_name=TABLE_STYLES["header_cell"] + " text-right"),
                            rx.el.th("Creada",     class_name=TABLE_STYLES["header_cell"] + " hidden md:table-cell"),
                            rx.el.th("Usuario", class_name=TABLE_STYLES["header_cell"] + " hidden lg:table-cell"),
                            rx.el.th("Acciones",   class_name=TABLE_STYLES["header_cell"] + " text-center"),
                        ),
                        class_name=TABLE_STYLES["header"],
                    ),
                    rx.el.tbody(rx.foreach(State.purchase_orders_list, _po_row)),
                    class_name="w-full text-sm",
                ),
                class_name="overflow-x-auto rounded-xl border border-slate-200",
            ),
            empty_state(
                title="Sin órdenes",
                message="No hay órdenes de compra en este filtro.",
                icon="inbox",
            ),
        ),
        class_name=CARD_STYLES["default"] + " flex flex-col gap-4",
    )

    content = rx.el.div(
        page_title(
            "Órdenes de Compra",
            "Detecta productos con stock bajo y genera órdenes de compra sugeridas por proveedor.",
        ),
        suggestions_section,
        orders_section,
        _reorder_confirm_modal(),
        _po_detail_modal(),
        _send_modal(),
        _edit_po_modal(),
        class_name="p-4 sm:p-6 w-full flex flex-col gap-4",
        on_mount=State.load_purchase_orders,
    )

    return permission_guard(
        has_permission=State.can_view_compras,
        content=content,
        redirect_message="Acceso denegado a Órdenes de Compra",
    )
