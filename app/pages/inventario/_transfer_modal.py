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


def _barcode_scanner() -> rx.Component:
    return rx.el.div(
        rx.el.label(
            rx.icon("scan-barcode", class_name="h-3.5 w-3.5"),
            "Escanear código de barras",
            class_name="flex items-center gap-1.5 text-xs font-medium text-slate-500 uppercase tracking-wide",
        ),
        rx.el.form(
            rx.el.div(
                rx.icon("scan-barcode", class_name="h-4 w-4 text-indigo-500 flex-shrink-0"),
                rx.el.input(
                    name="barcode",
                    key=State.transfer_barcode_key.to_string(),
                    placeholder="Escanee o escriba el código y presione Enter...",
                    auto_complete="off",
                    auto_focus=True,
                    class_name="flex-1 min-w-0 border-0 focus:ring-0 text-sm bg-transparent outline-none py-0 placeholder-slate-400",
                ),
                class_name="flex items-center gap-2 px-3 py-2.5 border-2 border-indigo-200 rounded-lg bg-indigo-50/30 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-400",
            ),
            on_submit=State.transfer_barcode_submit,
            reset_on_submit=True,
        ),
        rx.el.p(
            "Escanee un producto para agregarlo. Si ya existe, se incrementa la cantidad.",
            class_name="text-xs text-slate-400 italic",
        ),
        class_name="flex flex-col gap-1.5",
    )


def _description_search() -> rx.Component:
    return rx.el.div(
        rx.el.label(
            rx.icon("search", class_name="h-3.5 w-3.5"),
            "Buscar por descripción",
            class_name="flex items-center gap-1.5 text-xs font-medium text-slate-500 uppercase tracking-wide",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon("search", class_name="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2"),
                rx.el.input(
                    value=State.transfer_search_term,
                    on_change=State.transfer_search_products,
                    placeholder="Escriba para buscar por nombre o código...",
                    class_name=INPUT_STYLES["default"] + " pl-9",
                ),
                class_name="relative",
            ),
            rx.cond(
                State.transfer_search_results.length() > 0,
                rx.el.div(
                    rx.foreach(
                        State.transfer_search_results,
                        lambda r: rx.el.button(
                            rx.el.div(
                                rx.el.div(
                                    rx.el.span(
                                        r["description"],
                                        class_name="text-sm font-medium text-slate-700",
                                    ),
                                    rx.cond(
                                        r["variant_label"] != "",
                                        rx.el.span(
                                            r["variant_label"],
                                            class_name="text-xs font-medium text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded",
                                        ),
                                        rx.fragment(),
                                    ),
                                    class_name="flex items-center gap-1.5",
                                ),
                                rx.cond(
                                    r["barcode"] != "",
                                    rx.el.span(
                                        r["barcode"],
                                        class_name="text-xs text-slate-400 font-mono",
                                    ),
                                    rx.fragment(),
                                ),
                                class_name="flex flex-col items-start",
                            ),
                            rx.el.div(
                                rx.el.span(
                                    r["stock"], " ", r["unit"],
                                    class_name="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full",
                                ),
                                rx.icon("circle-plus", class_name="h-5 w-5 text-indigo-500"),
                                class_name="flex items-center gap-2 shrink-0",
                            ),
                            on_click=State.transfer_add_item(r["key"]),
                            type="button",
                            class_name=f"flex items-center justify-between w-full px-3 py-2.5 hover:bg-indigo-50 {TRANSITIONS['fast']} cursor-pointer text-left",
                        ),
                    ),
                    class_name=f"border border-slate-200 {RADIUS['lg']} overflow-hidden divide-y divide-slate-100 max-h-52 overflow-y-auto bg-white shadow-lg",
                ),
                rx.fragment(),
            ),
            class_name="flex flex-col gap-1",
        ),
        class_name="flex flex-col gap-1.5",
    )


def _bulk_actions() -> rx.Component:
    """Acciones rápidas: cargar todo el stock de la sucursal / vaciar el carrito."""
    return rx.el.div(
        rx.el.button(
            rx.icon("layers", class_name="h-4 w-4"),
            "Agregar todo el stock",
            on_click=State.transfer_add_all,
            type="button",
            class_name="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50 transition-colors",
        ),
        rx.cond(
            State.transfer_items.length() > 0,
            rx.el.button(
                rx.icon("eraser", class_name="h-4 w-4"),
                "Quitar todos",
                on_click=State.transfer_clear_all,
                type="button",
                class_name="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",
            ),
            rx.fragment(),
        ),
        rx.el.span(
            "Carga todos los productos con stock de esta sucursal (podés ajustar antes de confirmar).",
            class_name="text-xs text-slate-400 italic w-full sm:w-auto sm:ml-auto sm:text-right",
        ),
        class_name="flex items-center gap-2 flex-wrap",
    )


def _qty_stepper(item: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.button(
            rx.icon("minus", class_name="h-3.5 w-3.5"),
            on_click=State.transfer_decrement_qty(item["key"]),
            type="button",
            class_name=f"p-1 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 {RADIUS['md']} {TRANSITIONS['fast']} disabled:opacity-30",
            disabled=item["quantity"] == "1",
        ),
        rx.el.input(
            type="number",
            min="1",
            value=item["quantity"],
            on_change=lambda v, k=item["key"]: State.transfer_update_qty(k, v),
            class_name="w-14 px-1 py-0.5 text-sm text-center font-medium border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
        ),
        rx.el.button(
            rx.icon("plus", class_name="h-3.5 w-3.5"),
            on_click=State.transfer_increment_qty(item["key"]),
            type="button",
            class_name=f"p-1 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 {RADIUS['md']} {TRANSITIONS['fast']}",
        ),
        class_name="flex items-center gap-0.5",
    )


def _transfer_items_list() -> rx.Component:
    return rx.cond(
        State.transfer_items.length() > 0,
        rx.el.div(
            rx.el.div(
                rx.el.label(
                    rx.icon("package", class_name="h-3.5 w-3.5"),
                    "Productos a transferir",
                    class_name="flex items-center gap-1.5 text-xs font-medium text-slate-500 uppercase tracking-wide",
                ),
                rx.el.span(
                    State.transfer_items.length().to_string(),
                    rx.cond(
                        State.transfer_items.length() == 1,
                        " producto",
                        " productos",
                    ),
                    class_name="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full",
                ),
                class_name="flex items-center justify-between",
            ),
            rx.el.div(
                rx.foreach(
                    State.transfer_items,
                    lambda item: rx.el.div(
                        rx.el.div(
                            rx.el.div(
                                rx.el.div(
                                    rx.el.span(
                                        item["description"],
                                        class_name="text-sm font-medium text-slate-700 line-clamp-1",
                                    ),
                                    rx.cond(
                                        item["variant_label"] != "",
                                        rx.el.span(
                                            item["variant_label"],
                                            class_name="text-xs font-medium text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded",
                                        ),
                                        rx.fragment(),
                                    ),
                                    class_name="flex items-center gap-1.5 min-w-0",
                                ),
                                rx.cond(
                                    item["barcode"] != "",
                                    rx.el.span(
                                        item["barcode"],
                                        class_name="text-xs text-slate-400 font-mono",
                                    ),
                                    rx.fragment(),
                                ),
                                class_name="flex flex-col min-w-0",
                            ),
                            rx.el.span(
                                "Disp: ", item["available_stock"], " ", item["unit"],
                                class_name="text-xs text-slate-400 shrink-0",
                            ),
                            class_name="flex items-center justify-between gap-2 flex-1 min-w-0",
                        ),
                        rx.el.div(
                            _qty_stepper(item),
                            rx.el.button(
                                rx.icon("trash-2", class_name="h-3.5 w-3.5"),
                                on_click=State.transfer_remove_item(item["key"]),
                                type="button",
                                class_name=f"p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 {RADIUS['md']} {TRANSITIONS['fast']}",
                            ),
                            class_name="flex items-center gap-2",
                        ),
                        class_name="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-3 py-2.5",
                    ),
                ),
                class_name=f"border border-slate-200 {RADIUS['lg']} divide-y divide-slate-100 overflow-hidden max-h-64 overflow-y-auto",
            ),
            class_name="flex flex-col gap-2",
        ),
        rx.el.div(
            rx.icon("package-open", class_name="h-8 w-8 text-slate-300"),
            rx.el.p(
                "Escanee un código de barras o busque productos para agregarlos",
                class_name="text-sm text-slate-400 text-center",
            ),
            class_name="flex flex-col items-center gap-2 py-6 border-2 border-dashed border-slate-200 rounded-xl",
        ),
    )


def _dest_branch_select() -> rx.Component:
    return rx.el.div(
        rx.el.label(
            rx.icon("building-2", class_name="h-3.5 w-3.5"),
            "Sucursal destino",
            class_name="flex items-center gap-1.5 text-xs font-medium text-slate-500 uppercase tracking-wide",
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
        description="Escanee o busque los productos y seleccione la sucursal destino.",
        max_width="max-w-2xl",
        children=[
            rx.el.div(
                _dest_branch_select(),
                rx.el.div(
                    class_name="border-t border-slate-100",
                ),
                _barcode_scanner(),
                _description_search(),
                _bulk_actions(),
                rx.el.div(
                    class_name="border-t border-slate-100",
                ),
                _transfer_items_list(),
                rx.el.div(
                    rx.el.label(
                        rx.icon("message-square", class_name="h-3.5 w-3.5"),
                        "Notas (opcional)",
                        class_name="flex items-center gap-1.5 text-xs font-medium text-slate-500 uppercase tracking-wide",
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
            rx.cond(
                State.transfer_items.length() > 0,
                rx.el.span(
                    State.transfer_items.length().to_string(),
                    rx.cond(
                        State.transfer_items.length() == 1,
                        " producto seleccionado",
                        " productos seleccionados",
                    ),
                    class_name="text-xs text-slate-500 mr-auto",
                ),
                rx.fragment(),
            ),
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
            class_name="flex items-center justify-end gap-2",
        ),
    )


def _detail_status_badge(status: rx.Var) -> rx.Component:
    return rx.cond(
        status == "completed",
        rx.el.span("Completada", class_name="text-xs font-medium text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full"),
        rx.cond(
            status == "cancelled",
            rx.el.span("Cancelada", class_name="text-xs font-medium text-red-600 bg-red-50 px-2.5 py-1 rounded-full"),
            rx.el.span("Pendiente", class_name="text-xs font-medium text-amber-600 bg-amber-50 px-2.5 py-1 rounded-full"),
        ),
    )


def transfer_detail_modal() -> rx.Component:
    d = State.transfer_detail
    return modal_container(
        is_open=State.transfer_detail_open,
        on_close=State.transfer_close_detail,
        title="Detalle de transferencia",
        description="Resumen completo de los productos movidos en esta transferencia.",
        max_width="max-w-lg",
        children=[
            rx.el.div(
                # Encabezado: #id + estado
                rx.el.div(
                    rx.el.span(
                        "#", d["id"].to_string(),
                        class_name="text-lg font-bold text-slate-800",
                    ),
                    _detail_status_badge(d["status"]),
                    class_name="flex items-center justify-between",
                ),
                # Origen → Destino
                rx.el.div(
                    rx.el.div(
                        rx.el.span("Origen", class_name="text-xs text-slate-400 uppercase tracking-wide"),
                        rx.el.span(d["origin"], class_name="text-sm font-semibold text-slate-700"),
                        class_name="flex flex-col gap-0.5",
                    ),
                    rx.icon("arrow-right", class_name="h-5 w-5 text-indigo-400 shrink-0"),
                    rx.el.div(
                        rx.el.span("Destino", class_name="text-xs text-slate-400 uppercase tracking-wide"),
                        rx.el.span(d["destination"], class_name="text-sm font-semibold text-slate-700"),
                        class_name="flex flex-col gap-0.5",
                    ),
                    class_name="flex items-center justify-between gap-3 px-4 py-3 bg-slate-50 rounded-lg",
                ),
                # Fecha + usuario
                rx.el.div(
                    rx.el.div(
                        rx.icon("calendar", class_name="h-3.5 w-3.5 text-slate-400"),
                        rx.el.span(d["created_at"], class_name="text-xs text-slate-600"),
                        class_name="flex items-center gap-1.5",
                    ),
                    rx.cond(
                        d["created_by"] != "",
                        rx.el.div(
                            rx.icon("user", class_name="h-3.5 w-3.5 text-slate-400"),
                            rx.el.span(d["created_by"], class_name="text-xs text-slate-600"),
                            class_name="flex items-center gap-1.5",
                        ),
                        rx.fragment(),
                    ),
                    class_name="flex items-center gap-4",
                ),
                # Notas (si hay)
                rx.cond(
                    d["notes"] != "",
                    rx.el.div(
                        rx.el.span("Notas", class_name="text-xs text-slate-400 uppercase tracking-wide"),
                        rx.el.p(d["notes"], class_name="text-sm text-slate-600"),
                        class_name="flex flex-col gap-0.5 px-3 py-2 border-l-2 border-indigo-200 bg-indigo-50/40 rounded",
                    ),
                    rx.fragment(),
                ),
                # Lista de ítems
                rx.el.div(
                    rx.el.div(
                        rx.icon("package", class_name="h-3.5 w-3.5"),
                        rx.el.span(
                            "Productos transferidos (",
                            d["items_count"].to_string(),
                            ")",
                            class_name="text-xs font-medium",
                        ),
                        class_name="flex items-center gap-1.5 text-slate-500",
                    ),
                    rx.el.div(
                        rx.foreach(
                            State.transfer_detail_items,
                            lambda it: rx.el.div(
                                rx.el.span(it["name"], class_name="text-sm text-slate-700 line-clamp-1"),
                                rx.el.span(
                                    "×", it["quantity"],
                                    class_name="text-sm font-semibold text-slate-800 shrink-0 bg-slate-100 px-2 py-0.5 rounded",
                                ),
                                class_name="flex items-center justify-between gap-2 px-3 py-2",
                            ),
                        ),
                        class_name=f"border border-slate-200 {RADIUS['lg']} divide-y divide-slate-100 overflow-hidden max-h-64 overflow-y-auto",
                    ),
                    class_name="flex flex-col gap-1.5",
                ),
                class_name="flex flex-col gap-4",
            ),
        ],
        footer=rx.el.button(
            "Cerrar",
            on_click=State.transfer_close_detail,
            class_name=BUTTON_STYLES["secondary"],
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
                                    rx.el.th("", class_name=TABLE_STYLES["header_cell"]),
                                ),
                            ),
                            rx.el.tbody(
                                rx.foreach(
                                    State.transfer_history,
                                    lambda t: rx.el.tr(
                                        rx.el.td("#", t["id"], class_name=TABLE_STYLES["cell"] + " text-sm font-medium"),
                                        rx.el.td(t["origin"], class_name=TABLE_STYLES["cell"] + " text-sm"),
                                        rx.el.td(t["destination"], class_name=TABLE_STYLES["cell"] + " text-sm"),
                                        rx.el.td(
                                            rx.el.span(
                                                t["items_count"].to_string(),
                                                rx.cond(t["items_count"] == 1, " producto", " productos"),
                                                class_name="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full",
                                            ),
                                            class_name=TABLE_STYLES["cell"],
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
                                        rx.el.td(
                                            rx.el.div(
                                                rx.el.span("Ver detalle", class_name="text-xs font-medium text-indigo-600 hidden sm:inline"),
                                                rx.icon("chevron-right", class_name="h-4 w-4 text-indigo-400"),
                                                class_name="flex items-center gap-1 justify-end",
                                            ),
                                            class_name=TABLE_STYLES["cell"],
                                        ),
                                        on_click=State.transfer_open_detail(t["id"]),
                                        class_name="cursor-pointer hover:bg-indigo-50/60 transition-colors",
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
