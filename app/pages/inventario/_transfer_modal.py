import reflex as rx

from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    INPUT_STYLES,
    RADIUS,
    TABLE_STYLES,
    TRANSITIONS,
    TYPOGRAPHY,
    modal_container,
)


def _transfer_search_bar() -> rx.Component:
    return rx.el.div(
        rx.el.label(
            "Buscar productos para transferir",
            class_name="text-xs font-medium text-slate-500 uppercase tracking-wide",
        ),
        rx.el.div(
            rx.icon("search", class_name="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2"),
            rx.el.input(
                placeholder="Código de barras o descripción...",
                value=State.transfer_search_term,
                on_change=State.transfer_search_products,
                class_name=INPUT_STYLES["default"] + " pl-9",
            ),
            class_name="relative",
        ),
        rx.cond(
            State.transfer_search_results.length() > 0,
            rx.el.div(
                rx.foreach(
                    State.transfer_search_results,
                    lambda r: rx.el.div(
                        rx.el.div(
                            rx.el.span(
                                r["description"],
                                class_name="text-sm font-medium text-slate-700",
                            ),
                            rx.el.span(
                                r["barcode"],
                                class_name="text-xs text-slate-400",
                            ),
                            class_name="flex flex-col",
                        ),
                        rx.el.div(
                            rx.el.span(
                                "Stock: ", r["stock"], " ", r["unit"],
                                class_name="text-xs text-slate-500",
                            ),
                            rx.el.button(
                                rx.icon("plus", class_name="h-3.5 w-3.5"),
                                on_click=State.transfer_add_item(r["id"]),
                                class_name=f"p-1.5 text-indigo-600 hover:bg-indigo-50 {RADIUS['md']} cursor-pointer {TRANSITIONS['fast']}",
                            ),
                            class_name="flex items-center gap-2",
                        ),
                        class_name=f"flex items-center justify-between px-3 py-2 hover:bg-slate-50 {TRANSITIONS['fast']} cursor-pointer",
                    ),
                ),
                class_name=f"border border-slate-200 {RADIUS['lg']} overflow-hidden divide-y divide-slate-100 max-h-48 overflow-y-auto",
            ),
            rx.fragment(),
        ),
        class_name="flex flex-col gap-2",
    )


def _transfer_items_table() -> rx.Component:
    return rx.cond(
        State.transfer_items.length() > 0,
        rx.el.div(
            rx.el.label(
                "Productos a transferir",
                class_name="text-xs font-medium text-slate-500 uppercase tracking-wide",
            ),
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("Producto", class_name=TABLE_STYLES["header_cell"]),
                        rx.el.th("Stock disp.", class_name=TABLE_STYLES["header_cell"] + " text-center"),
                        rx.el.th("Cantidad", class_name=TABLE_STYLES["header_cell"] + " text-center"),
                        rx.el.th("", class_name=TABLE_STYLES["header_cell"] + " w-10"),
                    ),
                ),
                rx.el.tbody(
                    rx.foreach(
                        State.transfer_items,
                        lambda item: rx.el.tr(
                            rx.el.td(
                                rx.el.div(
                                    rx.el.span(item["description"], class_name="text-sm text-slate-700"),
                                    rx.el.span(item["barcode"], class_name="text-xs text-slate-400"),
                                    class_name="flex flex-col",
                                ),
                                class_name=TABLE_STYLES["cell"],
                            ),
                            rx.el.td(
                                item["available_stock"], " ", item["unit"],
                                class_name=TABLE_STYLES["cell"] + " text-center text-sm text-slate-500",
                            ),
                            rx.el.td(
                                rx.el.input(
                                    type="number",
                                    min="1",
                                    value=item["quantity"],
                                    on_change=lambda v, pid=item["product_id"]: State.transfer_update_qty(pid, v),
                                    class_name="w-20 px-2 py-1 text-sm text-center border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                                ),
                                class_name=TABLE_STYLES["cell"] + " text-center",
                            ),
                            rx.el.td(
                                rx.el.button(
                                    rx.icon("trash-2", class_name="h-3.5 w-3.5"),
                                    on_click=State.transfer_remove_item(item["product_id"]),
                                    class_name=f"p-1.5 text-red-500 hover:bg-red-50 {RADIUS['md']} cursor-pointer {TRANSITIONS['fast']}",
                                ),
                                class_name=TABLE_STYLES["cell"],
                            ),
                        ),
                    ),
                ),
                class_name="w-full",
            ),
            class_name="flex flex-col gap-2",
        ),
        rx.fragment(),
    )


def _dest_branch_select() -> rx.Component:
    return rx.el.div(
        rx.el.label(
            "Sucursal destino",
            class_name="text-xs font-medium text-slate-500 uppercase tracking-wide",
        ),
        rx.el.select(
            rx.el.option("Seleccione sucursal destino...", value=""),
            rx.foreach(
                State.available_branches,
                lambda branch: rx.cond(
                    branch["id"] != State.selected_branch_id,
                    rx.el.option(branch["name"], value=branch["id"]),
                    rx.fragment(),
                ),
            ),
            value=State.transfer_dest_branch_id,
            on_change=State.transfer_set_dest_branch,
            class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
    )


def transfer_modal() -> rx.Component:
    return modal_container(
        is_open=State.transfer_modal_open,
        on_close=State.transfer_close_modal,
        title="Transferir stock entre sucursales",
        description="Seleccione los productos y la sucursal destino para la transferencia.",
        max_width="max-w-2xl",
        children=[
            rx.el.div(
                _dest_branch_select(),
                _transfer_search_bar(),
                _transfer_items_table(),
                rx.el.div(
                    rx.el.label(
                        "Notas (opcional)",
                        class_name="text-xs font-medium text-slate-500 uppercase tracking-wide",
                    ),
                    rx.el.textarea(
                        value=State.transfer_notes,
                        on_change=State.transfer_set_notes,
                        placeholder="Motivo de la transferencia...",
                        rows=2,
                        class_name=INPUT_STYLES["default"] + " resize-none",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                class_name="flex flex-col gap-4",
            ),
        ],
        footer=rx.el.div(
            rx.el.button(
                "Cancelar",
                on_click=State.transfer_close_modal,
                class_name=BUTTON_STYLES["secondary"],
            ),
            rx.el.button(
                rx.cond(
                    State.transfer_loading,
                    rx.fragment(
                        rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"),
                        "Procesando...",
                    ),
                    rx.fragment(
                        rx.icon("arrow-right-left", class_name="h-4 w-4"),
                        "Transferir",
                    ),
                ),
                on_click=State.transfer_submit,
                disabled=State.transfer_loading,
                class_name=BUTTON_STYLES["primary"],
            ),
            class_name="flex justify-end gap-2",
        ),
    )


def transfer_history_section() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.button(
                rx.icon(
                    "chevron-down",
                    class_name=rx.cond(
                        State.transfer_show_history,
                        "h-4 w-4 rotate-180 transition-transform",
                        "h-4 w-4 transition-transform",
                    ),
                ),
                rx.el.span(
                    "Historial de Transferencias",
                    class_name="text-sm font-medium text-slate-700",
                ),
                on_click=State.transfer_toggle_history,
                class_name=f"flex items-center gap-2 px-3 py-2 hover:bg-slate-50 {RADIUS['md']} cursor-pointer {TRANSITIONS['fast']}",
            ),
            class_name="mb-2",
        ),
        rx.cond(
            State.transfer_show_history,
            rx.cond(
                State.transfer_loading,
                rx.el.div(
                    rx.icon("loader-circle", class_name="h-4 w-4 text-slate-400 animate-spin"),
                    rx.el.span("Cargando...", class_name="text-sm text-slate-500"),
                    class_name="flex items-center gap-2 py-4 justify-center",
                ),
                rx.cond(
                    State.transfer_history.length() > 0,
                    rx.el.div(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    rx.el.th("#", class_name=TABLE_STYLES["header_cell"]),
                                    rx.el.th("Origen", class_name=TABLE_STYLES["header_cell"]),
                                    rx.el.th("Destino", class_name=TABLE_STYLES["header_cell"]),
                                    rx.el.th("Productos", class_name=TABLE_STYLES["header_cell"]),
                                    rx.el.th("Estado", class_name=TABLE_STYLES["header_cell"]),
                                    rx.el.th("Fecha", class_name=TABLE_STYLES["header_cell"]),
                                ),
                            ),
                            rx.el.tbody(
                                rx.foreach(
                                    State.transfer_history,
                                    lambda t: rx.el.tr(
                                        rx.el.td(t["id"], class_name=TABLE_STYLES["cell"] + " text-sm"),
                                        rx.el.td(t["origin"], class_name=TABLE_STYLES["cell"] + " text-sm"),
                                        rx.el.td(t["destination"], class_name=TABLE_STYLES["cell"] + " text-sm"),
                                        rx.el.td(
                                            t["items_summary"],
                                            class_name=TABLE_STYLES["cell"] + " text-xs text-slate-500 max-w-48 truncate",
                                        ),
                                        rx.el.td(
                                            rx.cond(
                                                t["status"] == "completed",
                                                rx.el.span("Completada", class_name="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full"),
                                                rx.cond(
                                                    t["status"] == "cancelled",
                                                    rx.el.span("Cancelada", class_name="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full"),
                                                    rx.el.span("Pendiente", class_name="text-xs font-medium text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full"),
                                                ),
                                            ),
                                            class_name=TABLE_STYLES["cell"],
                                        ),
                                        rx.el.td(t["created_at"], class_name=TABLE_STYLES["cell"] + " text-xs text-slate-500"),
                                    ),
                                ),
                            ),
                            class_name="w-full",
                        ),
                        class_name="overflow-x-auto",
                    ),
                    rx.el.p(
                        "No hay transferencias registradas.",
                        class_name="text-sm text-slate-500 py-4 text-center",
                    ),
                ),
            ),
            rx.fragment(),
        ),
    )
