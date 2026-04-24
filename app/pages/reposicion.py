"""Página de Reposición Automática — POs sugeridas por stock bajo."""
import reflex as rx

from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    CARD_STYLES,
    INPUT_STYLES,
    SELECT_STYLES,
    SPACING,
    TABLE_STYLES,
    TYPOGRAPHY,
    modal_container,
    page_title,
    permission_guard,
)


def _status_badge(status: rx.Var[str]) -> rx.Component:
    """Badge de color por estado."""
    return rx.match(
        status,
        ("draft", rx.el.span("Borrador", class_name="px-2 py-1 rounded-full text-xs bg-amber-100 text-amber-800")),
        ("sent", rx.el.span("Enviada", class_name="px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800")),
        ("received", rx.el.span("Recibida", class_name="px-2 py-1 rounded-full text-xs bg-emerald-100 text-emerald-800")),
        ("cancelled", rx.el.span("Cancelada", class_name="px-2 py-1 rounded-full text-xs bg-slate-200 text-slate-600")),
        rx.el.span(status, class_name="px-2 py-1 rounded-full text-xs bg-slate-100 text-slate-700"),
    )


def _reorder_item_row(item: rx.Var[dict], index: rx.Var[int]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(item["barcode"], class_name="py-2 px-3 text-xs text-slate-500"),
        rx.el.td(item["description"], class_name="py-2 px-3 font-medium"),
        rx.el.td(
            item["current_stock"].to_string(),
            class_name="py-2 px-3 text-right text-rose-600 font-semibold",
        ),
        rx.el.td(
            item["min_stock_alert"].to_string(),
            class_name="py-2 px-3 text-right text-slate-500",
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
            class_name="py-2 px-3",
        ),
        rx.el.td(
            item["unit_cost"].to_string(),
            class_name="py-2 px-3 text-right text-slate-600",
        ),
        class_name="border-b border-slate-100",
    )


def _supplier_group_card(group: rx.Var[dict]) -> rx.Component:
    """Tarjeta de sugerencia agrupada por proveedor."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.h3(
                    group["supplier_name"],
                    class_name="text-lg font-semibold text-slate-800",
                ),
                rx.el.p(
                    group["item_count"].to_string() + " productos a reponer",
                    class_name=TYPOGRAPHY["caption"],
                ),
                class_name="flex-1",
            ),
            rx.el.div(
                rx.el.p(
                    "Total estimado",
                    class_name=TYPOGRAPHY["caption"],
                ),
                rx.el.p(
                    State.currency_symbol + " " + group["total_estimated"].to_string(),
                    class_name="text-xl font-bold text-indigo-600",
                ),
                class_name="text-right",
            ),
            class_name="flex items-center justify-between gap-4 mb-3",
        ),
        rx.el.button(
            rx.cond(
                group["supplier_id"],
                rx.fragment(
                    rx.icon("file-text", class_name="h-4 w-4"),
                    "Crear orden de compra",
                ),
                rx.fragment(
                    rx.icon("circle-alert", class_name="h-4 w-4"),
                    "Asignar proveedor en inventario",
                ),
            ),
            on_click=lambda _: State.open_reorder_confirm_modal(group["supplier_id"]),
            disabled=group["supplier_id"] == 0,
            class_name=BUTTON_STYLES["primary"] + " flex items-center gap-2",
        ),
        class_name=CARD_STYLES["default"] + " flex flex-col gap-2",
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
                                rx.el.th("Código", class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Producto", class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Stock", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("Mínimo", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("A pedir", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("Costo unit.", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                            ),
                            class_name=TABLE_STYLES["header"],
                        ),
                        rx.el.tbody(
                            rx.foreach(State.reorder_confirm_items, _reorder_item_row),
                        ),
                        class_name="w-full text-sm",
                    ),
                    class_name="max-h-96 overflow-auto border border-slate-200 rounded-lg",
                ),
                rx.el.div(
                    rx.el.label(
                        "Notas (opcional)",
                        class_name="text-sm font-medium text-slate-700",
                    ),
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
                    rx.el.p("Total estimado:", class_name="text-slate-600"),
                    rx.el.p(
                        State.currency_symbol + " " + State.reorder_confirm_total.to_string(),
                        class_name="text-2xl font-bold text-indigo-600",
                    ),
                    class_name="flex items-center justify-between mt-4 px-4 py-3 bg-slate-50 rounded-lg",
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
                "Crear borrador",
                on_click=State.confirm_create_purchase_order,
                class_name=BUTTON_STYLES["primary"],
            ),
            class_name="flex justify-end gap-2",
        ),
        max_width="max-w-3xl",
    )


def _po_row(po: rx.Var[dict]) -> rx.Component:
    return rx.el.tr(
        rx.el.td("#" + po["id"].to_string(), class_name="py-3 px-4 font-mono text-xs"),
        rx.el.td(po["supplier_name"], class_name="py-3 px-4 font-medium"),
        rx.el.td(_status_badge(po["status"]), class_name="py-3 px-4"),
        rx.el.td(
            po["item_count"].to_string(),
            class_name="py-3 px-4 text-center",
        ),
        rx.el.td(
            State.currency_symbol + " " + po["total_amount"].to_string(),
            class_name="py-3 px-4 text-right font-semibold",
        ),
        rx.el.td(
            po["created_at"],
            class_name="py-3 px-4 text-xs text-slate-500 hidden md:table-cell",
        ),
        rx.el.td(
            rx.el.div(
                rx.cond(
                    po["status"] == "draft",
                    rx.el.button(
                        rx.icon("send", class_name="h-4 w-4"),
                        on_click=lambda _: State.mark_po_sent(po["id"]),
                        title="Marcar como enviada",
                        class_name=BUTTON_STYLES["icon_primary"],
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    po["status"] != "received",
                    rx.el.button(
                        rx.icon("x", class_name="h-4 w-4"),
                        on_click=lambda _: State.cancel_po(po["id"]),
                        title="Cancelar",
                        class_name=BUTTON_STYLES["icon_danger"],
                    ),
                    rx.fragment(),
                ),
                class_name="flex items-center justify-center gap-2",
            ),
            class_name="py-3 px-4 text-center",
        ),
        class_name="border-b border-slate-100 hover:bg-slate-50",
    )


def reposicion_page() -> rx.Component:
    """Página de reposición automática."""

    suggestions_section = rx.el.div(
        rx.el.div(
            rx.el.h2(
                "Sugerencias de reposición",
                class_name="text-xl font-bold text-slate-800",
            ),
            rx.el.button(
                rx.icon("refresh-cw", class_name="h-4 w-4"),
                "Escanear stock bajo",
                on_click=State.load_reorder_suggestions,
                class_name=BUTTON_STYLES["primary"] + " flex items-center gap-2",
            ),
            class_name="flex items-center justify-between mb-4",
        ),
        rx.cond(
            State.has_reorder_suggestions,
            rx.el.div(
                rx.foreach(State.reorder_groups, _supplier_group_card),
                class_name="flex flex-col gap-4",
            ),
            rx.el.p(
                "No hay sugerencias. Presione 'Escanear stock bajo' para buscar productos bajo umbral.",
                class_name="text-slate-500 text-center py-12",
            ),
        ),
        class_name=CARD_STYLES["default"],
    )

    orders_section = rx.el.div(
        rx.el.div(
            rx.el.h2(
                "Órdenes de compra",
                class_name="text-xl font-bold text-slate-800",
            ),
            rx.el.select(
                rx.el.option("Todas", value="all"),
                rx.el.option("Borradores", value="draft"),
                rx.el.option("Enviadas", value="sent"),
                rx.el.option("Recibidas", value="received"),
                rx.el.option("Canceladas", value="cancelled"),
                default_value=State.po_status_filter,
                on_change=State.set_po_status_filter,
                class_name=SELECT_STYLES["default"],
            ),
            class_name="flex items-center justify-between mb-4",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("ID", class_name=TABLE_STYLES["header_cell"]),
                        rx.el.th("Proveedor", class_name=TABLE_STYLES["header_cell"]),
                        rx.el.th("Estado", class_name=TABLE_STYLES["header_cell"]),
                        rx.el.th("Ítems", class_name=TABLE_STYLES["header_cell"] + " text-center"),
                        rx.el.th("Total", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                        rx.el.th("Creada", class_name=TABLE_STYLES["header_cell"] + " hidden md:table-cell"),
                        rx.el.th("Acciones", class_name=TABLE_STYLES["header_cell"] + " text-center"),
                    ),
                    class_name=TABLE_STYLES["header"],
                ),
                rx.el.tbody(rx.foreach(State.purchase_orders_list, _po_row)),
                class_name="w-full text-sm",
            ),
            class_name="overflow-x-auto border border-slate-100 rounded-lg",
        ),
        rx.cond(
            State.purchase_orders_list.length() == 0,
            rx.el.p(
                "No hay órdenes en este filtro.",
                class_name="text-slate-500 text-center py-8",
            ),
            rx.fragment(),
        ),
        class_name=CARD_STYLES["default"] + " mt-6",
    )

    content = rx.el.div(
        page_title(
            "REPOSICIÓN AUTOMÁTICA",
            "Genera órdenes de compra sugeridas desde productos bajo umbral de stock.",
        ),
        suggestions_section,
        orders_section,
        _reorder_confirm_modal(),
        class_name="p-4 sm:p-6 w-full flex flex-col gap-4",
        on_mount=State.load_purchase_orders,
    )

    return permission_guard(
        has_permission=State.can_view_compras,
        content=content,
        redirect_message="Acceso denegado a Reposición",
    )
