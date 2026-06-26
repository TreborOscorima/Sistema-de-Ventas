import reflex as rx
from app.state import State
from app.components.ui import BUTTON_STYLES, action_button, modal_container


def compact_sale_item_row(item: rx.Var[dict]) -> rx.Component:
    """Fila compacta para la tabla de productos en venta (desktop)."""
    return rx.el.tr(
        rx.el.td(
            item["barcode"],
            class_name="py-2 px-3 text-xs text-slate-500 font-mono hidden md:table-cell",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.span(
                    item["description"],
                    class_name="font-medium text-slate-800",
                ),
                # Número de lote visible si el ítem lo requiere (farmacia/alimentos).
                # Botón clickable: abre el selector manual de lote.
                rx.cond(
                    item["batch_number"] != "",
                    rx.el.button(
                        rx.icon("flask-round", class_name="h-3 w-3 inline mr-0.5"),
                        "Lote: ",
                        item["batch_number"],
                        rx.icon("chevron-down", class_name="h-3 w-3 inline ml-0.5"),
                        on_click=lambda: State.open_batch_picker(item["temp_id"]),
                        title="Cambiar lote",
                        aria_label="Cambiar lote",
                        type="button",
                        class_name="text-xs font-mono text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-1.5 py-0.5 rounded inline-flex items-center gap-0.5 transition-colors w-fit",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    item["kit_name"] != "",
                    rx.el.span(
                        rx.icon("package", class_name="h-3 w-3 inline mr-0.5"),
                        "KIT: ",
                        item["kit_name"],
                        class_name="text-xs font-mono text-violet-700 bg-violet-50 border border-violet-200 px-1.5 py-0.5 rounded inline-flex items-center gap-0.5 w-fit",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    item["promotion_name"] != "",
                    rx.el.span(
                        rx.icon("tag", class_name="h-3 w-3 inline mr-0.5"),
                        item["promotion_name"],
                        class_name="text-xs font-mono text-orange-700 bg-orange-50 border border-orange-200 px-1.5 py-0.5 rounded inline-flex items-center gap-0.5 w-fit",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    item["price_list_name"] != "",
                    rx.el.span(
                        rx.icon("tag", class_name="h-3 w-3 inline mr-0.5"),
                        item["price_list_name"],
                        class_name="text-xs font-mono text-indigo-700 bg-indigo-50 border border-indigo-200 px-1.5 py-0.5 rounded inline-flex items-center gap-0.5 w-fit",
                    ),
                    rx.fragment(),
                ),
                class_name="flex flex-col gap-0.5",
            ),
            class_name="py-2 px-3 text-sm",
        ),
        rx.el.td(
            item["quantity"].to_string(),
            class_name="py-2 px-3 text-center text-sm",
        ),
        rx.el.td(
            rx.cond(
                item["promotion_name"] != "",
                rx.el.div(
                    rx.el.span(
                        State.currency_symbol,
                        item["base_price"],
                        class_name="text-slate-400 line-through text-xs leading-none",
                    ),
                    rx.el.span(
                        State.currency_symbol,
                        item["sale_price"],
                        class_name="text-emerald-600 font-semibold",
                    ),
                    class_name="flex flex-col items-end gap-0.5",
                ),
                rx.cond(
                    item["price_list_name"] != "",
                    rx.el.div(
                        rx.el.span(
                            State.currency_symbol,
                            item["original_price"],
                            class_name="text-slate-400 line-through text-xs leading-none",
                        ),
                        rx.el.span(
                            State.currency_symbol,
                            item["sale_price"],
                            class_name="text-indigo-600 font-semibold",
                        ),
                        class_name="flex flex-col items-end gap-0.5",
                    ),
                    rx.el.span(State.currency_symbol, item["sale_price"]),
                ),
            ),
            class_name="py-2 px-3 text-right text-sm hidden sm:table-cell",
        ),
        rx.el.td(
            rx.el.span(
                State.currency_symbol,
                item["subtotal"],
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
                class_name=BUTTON_STYLES["icon_danger"],
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
                rx.cond(
                    item["batch_number"] != "",
                    rx.el.button(
                        rx.icon("flask-round", class_name="h-3 w-3 inline mr-0.5"),
                        "Lote: ",
                        item["batch_number"],
                        rx.icon("chevron-down", class_name="h-3 w-3 inline ml-0.5"),
                        on_click=lambda: State.open_batch_picker(item["temp_id"]),
                        title="Cambiar lote",
                        aria_label="Cambiar lote",
                        type="button",
                        class_name="text-xs font-mono text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-1.5 py-0.5 rounded inline-flex items-center gap-0.5 w-fit transition-colors",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    item["kit_name"] != "",
                    rx.el.span(
                        rx.icon("package", class_name="h-3 w-3 inline mr-0.5"),
                        "KIT: ",
                        item["kit_name"],
                        class_name="text-xs font-mono text-violet-700 bg-violet-50 border border-violet-200 px-1.5 py-0.5 rounded inline-flex items-center gap-0.5 w-fit",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    item["promotion_name"] != "",
                    rx.el.span(
                        rx.icon("tag", class_name="h-3 w-3 inline mr-0.5"),
                        item["promotion_name"],
                        class_name="text-xs font-mono text-orange-700 bg-orange-50 border border-orange-200 px-1.5 py-0.5 rounded inline-flex items-center gap-0.5 w-fit",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    item["price_list_name"] != "",
                    rx.el.span(
                        rx.icon("tag", class_name="h-3 w-3 inline mr-0.5"),
                        item["price_list_name"],
                        class_name="text-xs font-mono text-indigo-700 bg-indigo-50 border border-indigo-200 px-1.5 py-0.5 rounded inline-flex items-center gap-0.5 w-fit",
                    ),
                    rx.fragment(),
                ),
                class_name="flex flex-col gap-0.5",
            ),
            rx.el.button(
                rx.icon("x", class_name="h-4 w-4"),
                on_click=lambda: State.remove_item_from_sale(item["temp_id"]),
                title="Quitar producto",
                aria_label="Quitar producto",
                class_name=BUTTON_STYLES["icon_danger"],
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
                rx.cond(
                    item["promotion_name"] != "",
                    rx.el.div(
                        rx.el.span(
                            State.currency_symbol,
                            item["base_price"],
                            class_name="text-slate-400 line-through text-xs",
                        ),
                        rx.el.span(
                            State.currency_symbol,
                            item["sale_price"],
                            class_name="font-semibold text-emerald-600",
                        ),
                        class_name="flex flex-col items-start leading-tight",
                    ),
                    rx.cond(
                        item["price_list_name"] != "",
                        rx.el.div(
                            rx.el.span(
                                State.currency_symbol,
                                item["base_price"],
                                class_name="text-slate-400 line-through text-xs",
                            ),
                            rx.el.span(
                                State.currency_symbol,
                                item["sale_price"],
                                class_name="font-semibold text-indigo-600",
                            ),
                            class_name="flex flex-col items-start leading-tight",
                        ),
                        rx.el.span(State.currency_symbol, item["sale_price"], class_name="font-medium"),
                    ),
                ),
                class_name="flex items-center gap-1",
            ),
            rx.el.div(
                rx.el.span(
                    State.currency_symbol,
                    item["subtotal"],
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
                            class_name=BUTTON_STYLES["icon_primary"],
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
        class_name="min-w-full",
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
    footer = rx.el.div(
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
        class_name="flex items-center gap-2 w-full",
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
