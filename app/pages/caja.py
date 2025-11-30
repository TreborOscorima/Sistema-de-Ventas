import reflex as rx
from app.state import State


def cashbox_filters() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.label(
                "Fecha Inicio", class_name="text-sm font-medium text-gray-600"
            ),
            rx.el.input(
                type="date",
                value=State.cashbox_staged_start_date,
                on_change=State.set_cashbox_staged_start_date,
                class_name="w-full p-2 border rounded-md",
            ),
            class_name="flex flex-col gap-2",
        ),
        rx.el.div(
            rx.el.label("Fecha Fin", class_name="text-sm font-medium text-gray-600"),
            rx.el.input(
                type="date",
                value=State.cashbox_staged_end_date,
                on_change=State.set_cashbox_staged_end_date,
                class_name="w-full p-2 border rounded-md",
            ),
            class_name="flex flex-col gap-2",
        ),
        rx.el.div(
            rx.el.label("Mostrar adelantos", class_name="text-sm font-medium text-gray-600"),
            rx.el.div(
                rx.el.input(
                    type="checkbox",
                    checked=State.show_cashbox_advances,
                    on_change=lambda val: State.set_show_cashbox_advances(val),
                    class_name="h-4 w-4 text-indigo-600 border-gray-300 rounded",
                ),
                rx.el.span(
                    "Incluir adelantos en el listado",
                    class_name="text-sm text-gray-600",
                ),
                class_name="flex items-center gap-2",
            ),
            class_name="flex flex-col gap-2",
        ),
        rx.el.div(
            rx.el.button(
                rx.icon("search", class_name="h-4 w-4"),
                "Buscar",
                on_click=State.apply_cashbox_filters,
                class_name="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 min-h-[42px]",
            ),
            rx.el.button(
                "Limpiar",
                on_click=State.reset_cashbox_filters,
                class_name="w-full px-4 py-2 rounded-md border text-gray-700 hover:bg-gray-50 min-h-[42px]",
            ),
            rx.el.button(
                rx.icon("download", class_name="h-4 w-4"),
                "Exportar",
                on_click=State.export_cashbox_report,
                class_name="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-green-600 text-white hover:bg-green-700 min-h-[42px]",
            ),
            class_name="flex flex-col gap-2 sm:flex-row sm:flex-wrap",
        ),
        class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[repeat(3,minmax(0,1fr))] gap-3 sm:gap-4 items-end",
    )


def cashbox_log_filters() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.label(
                "Fecha Inicio", class_name="text-sm font-medium text-gray-600"
            ),
            rx.el.input(
                type="date",
                value=State.cashbox_log_staged_start_date,
                on_change=State.set_cashbox_log_staged_start_date,
                class_name="w-full p-2 border rounded-md",
            ),
            class_name="flex flex-col gap-2",
        ),
        rx.el.div(
            rx.el.label("Fecha Fin", class_name="text-sm font-medium text-gray-600"),
            rx.el.input(
                type="date",
                value=State.cashbox_log_staged_end_date,
                on_change=State.set_cashbox_log_staged_end_date,
                class_name="w-full p-2 border rounded-md",
            ),
            class_name="flex flex-col gap-2",
        ),
        rx.el.div(
            rx.el.button(
                rx.icon("search", class_name="h-4 w-4"),
                "Buscar",
                on_click=State.apply_cashbox_log_filters,
                class_name="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 min-h-[42px]",
            ),
            rx.el.button(
                "Limpiar",
                on_click=State.reset_cashbox_log_filters,
                class_name="w-full px-4 py-2 rounded-md border text-gray-700 hover:bg-gray-50 min-h-[42px]",
            ),
            rx.el.button(
                rx.icon("download", class_name="h-4 w-4"),
                "Exportar Excel",
                on_click=State.export_cashbox_sessions,
                class_name="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-emerald-600 text-white hover:bg-emerald-700 min-h-[42px]",
            ),
            class_name="flex flex-col gap-2 sm:flex-row sm:flex-wrap lg:flex-col",
        ),
        class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4",
    )



def cashbox_opening_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(
                rx.cond(State.cashbox_is_open, "wallet-cards", "alarm-clock"),
                class_name=rx.cond(
                    State.cashbox_is_open,
                    "h-10 w-10 text-emerald-600",
                    "h-10 w-10 text-indigo-600",
                ),
            ),
            rx.el.div(
                rx.el.p(
                    rx.cond(
                        State.cashbox_is_open,
                        "Caja abierta",
                        "Apertura de caja requerida",
                    ),
                    class_name="text-lg font-semibold text-gray-900",
                ),
                rx.el.p(
                    rx.cond(
                        State.cashbox_is_open,
                        "La caja sigue abierta hasta que confirmes el cierre.",
                        "Ingresa el monto inicial para comenzar la jornada. Sin apertura no podras vender ni gestionar la caja.",
                    ),
                    class_name="text-sm text-gray-600",
                ),
                class_name="flex flex-col gap-1",
            ),
            class_name="flex items-start gap-3",
        ),
        rx.cond(
            State.cashbox_is_open,
            rx.el.div(
                rx.el.div(
                    rx.el.span(
                        "Monto inicial",
                        class_name="text-xs uppercase tracking-wide text-gray-500",
                    ),
                    rx.el.span(
                        State.currency_symbol,
                        State.cashbox_opening_amount.to_string(),
                        class_name="text-xl font-semibold text-gray-900",
                    ),
                    class_name="flex flex-col gap-1 bg-emerald-50 border border-emerald-100 rounded-lg px-4 py-3",
                ),
                rx.el.div(
                    rx.el.span(
                        "Apertura",
                        class_name="text-xs uppercase tracking-wide text-gray-500",
                    ),
                    rx.el.span(
                        rx.cond(
                            State.cashbox_opening_time == "",
                            "Sin registro",
                            State.cashbox_opening_time,
                        ),
                        class_name="text-sm font-medium text-gray-800",
                    ),
                    class_name="flex flex-col gap-1 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3",
                ),
                class_name="flex flex-col sm:flex-row gap-3",
            ),
            rx.fragment(),
        ),
        rx.el.div(
            rx.el.label("Caja inicial", class_name="font-medium text-gray-800"),
            rx.el.div(
                rx.el.input(
                    type="number",
                    step="0.01",
                    value=State.cashbox_open_amount_input,
                    on_change=State.set_cashbox_open_amount_input,
                    placeholder="Ej: 150.00",
                    disabled=State.cashbox_is_open,
                    class_name=rx.cond(
                        State.cashbox_is_open,
                        "flex-1 p-3 border rounded-lg bg-gray-100 text-gray-500 cursor-not-allowed",
                        "flex-1 p-3 border rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400",
                    ),
                ),
                rx.el.button(
                    rx.icon("play", class_name="h-4 w-4"),
                    rx.cond(State.cashbox_is_open, "Caja abierta", "Aperturar caja"),
                    on_click=State.open_cashbox_session,
                    disabled=State.cashbox_is_open,
                    class_name=rx.cond(
                        State.cashbox_is_open,
                        "flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-gray-200 text-gray-500 cursor-not-allowed min-h-[44px]",
                        "flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 shadow min-h-[44px]",
                    ),
                ),
                rx.el.button(
                    rx.icon("lock", class_name="h-4 w-4"),
                    "Cerrar Caja",
                    on_click=State.open_cashbox_close_modal,
                    disabled=~State.cashbox_is_open,
                    class_name=rx.cond(
                        State.cashbox_is_open,
                        "flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 shadow min-h-[44px]",
                        "flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-indigo-100 text-indigo-400 cursor-not-allowed min-h-[44px]",
                    ),
                ),
                class_name="flex flex-col md:flex-row md:items-center gap-3 mt-2",
            ),
            rx.el.p(
                "Consejo: registra el efectivo inicial real para un cuadre correcto al cierre.",
                class_name="text-xs text-gray-500 mt-1",
            ),
            class_name="flex flex-col gap-1",
        ),
        class_name="bg-white p-4 sm:p-5 rounded-xl shadow-md mb-4 border border-gray-100 flex flex-col gap-3",
    )


def sale_items_list(items: rx.Var[list[dict]]) -> rx.Component:
    return rx.el.div(
        rx.foreach(
            items,
            lambda item: rx.el.div(
                rx.el.span(item["description"], class_name="font-medium"),
                rx.el.span(
                    item["quantity"].to_string(),
                    class_name="text-sm text-gray-500",
                ),
                class_name="flex items-center justify-between text-sm",
            ),
        ),
        class_name="flex flex-col gap-1",
    )


def sale_row(sale: rx.Var[dict]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(sale["timestamp"], class_name="py-3 px-4"),
        rx.el.td(sale["user"], class_name="py-3 px-4"),
        rx.el.td(
            rx.el.p(sale["payment_method"], class_name="font-medium"),
            rx.el.p(
                sale["payment_details"],
                class_name="text-xs text-gray-500 mt-1",
            ),
            rx.cond(
                sale["is_deleted"],
                rx.el.div(
                    rx.el.span(
                        "Venta eliminada",
                        class_name="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-700",
                    ),
                    rx.el.p(
                        sale["delete_reason"],
                        class_name="text-xs text-red-600 mt-1",
                    ),
                    class_name="mt-2 space-y-1",
                ),
                rx.fragment(),
            ),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.el.span(
                State.currency_symbol,
                sale["service_total"].to_string(),
                class_name="font-semibold",
            ),
            class_name="py-3 px-4 text-right",
        ),
        rx.el.td(sale_items_list(sale["items"]), class_name="py-3 px-4"),
        rx.el.td(
            rx.el.div(
                rx.cond(
                    sale["is_deleted"],
                    rx.el.button(
                        rx.icon("printer", class_name="h-4 w-4"),
                        "Reimprimir",
                        disabled=True,
                        class_name="flex items-center justify-center gap-2 px-3 py-2 rounded-md border text-gray-400 cursor-not-allowed min-h-[40px]",
                    ),
                    rx.el.button(
                        rx.icon("printer", class_name="h-4 w-4"),
                        "Reimprimir",
                        on_click=lambda _,
                        sale_id=sale["sale_id"]: State.reprint_sale_receipt(sale_id),
                        class_name="flex items-center justify-center gap-2 px-3 py-2 rounded-md border text-blue-600 hover:bg-blue-50 min-h-[40px]",
                    ),
                ),
                rx.cond(
                    sale["is_deleted"],
                    rx.el.button(
                        rx.icon("trash-2", class_name="h-4 w-4"),
                        "Eliminada",
                        disabled=True,
                        class_name="flex items-center justify-center gap-2 px-3 py-2 rounded-md border text-gray-400 cursor-not-allowed min-h-[40px]",
                    ),
                    rx.el.button(
                        rx.icon("trash-2", class_name="h-4 w-4"),
                        "Eliminar",
                        on_click=lambda _,
                        sale_id=sale["sale_id"]: State.open_sale_delete_modal(
                            sale_id
                        ),
                        class_name="flex items-center justify-center gap-2 px-3 py-2 rounded-md border text-red-600 hover:bg-red-50 min-h-[40px]",
                    ),
                ),
                class_name="flex flex-col gap-2 md:flex-row md:justify-center",
            ),
            class_name="py-3 px-4",
        ),
        class_name="border-b",
    )


def cashbox_log_row(log: rx.Var[dict]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(log["timestamp"], class_name="py-3 px-4"),
        rx.el.td(
            rx.cond(
                log["action"] == "apertura",
                rx.el.span(
                    "Apertura",
                    class_name="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-700",
                ),
                rx.el.span(
                    "Cierre",
                    class_name="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-orange-100 text-orange-700",
                ),
            ),
            class_name="py-3 px-4",
        ),
        rx.el.td(log["user"], class_name="py-3 px-4"),
        rx.el.td(
            State.currency_symbol,
            log["opening_amount"].to_string(),
            class_name="py-3 px-4 text-right font-medium",
        ),
        rx.el.td(
            State.currency_symbol,
            log["closing_total"].to_string(),
            class_name="py-3 px-4 text-right font-medium",
        ),
        rx.el.td(
            rx.el.button(
                rx.icon("eye", class_name="h-4 w-4"),
                "Visualizar",
                on_click=lambda _, log_id=log["id"]: State.show_cashbox_log(log_id),
                class_name="flex items-center justify-center gap-2 px-3 py-2 rounded-md border text-indigo-600 hover:bg-indigo-50 min-h-[40px]",
            ),
            class_name="py-3 px-4 text-center",
        ),
        class_name="border-b",
    )


def pagination_controls() -> rx.Component:
    return rx.el.div(
        rx.cond(
            State.cashbox_current_page <= 1,
            rx.el.button(
                "Anterior",
                class_name="px-3 py-2 rounded-md bg-gray-200 text-gray-500 cursor-not-allowed min-h-[40px]",
            ),
            rx.el.button(
                "Anterior",
                on_click=State.prev_cashbox_page,
                class_name="px-3 py-2 rounded-md border bg-white hover:bg-gray-50 min-h-[40px]",
            ),
        ),
        rx.el.span(
            rx.el.span("Página "),
            State.cashbox_current_page,
            rx.el.span(" de "),
            State.cashbox_total_pages,
            class_name="text-sm text-gray-600",
        ),
        rx.cond(
            State.cashbox_current_page >= State.cashbox_total_pages,
            rx.el.button(
                "Siguiente",
                class_name="px-3 py-2 rounded-md bg-gray-200 text-gray-500 cursor-not-allowed min-h-[40px]",
            ),
            rx.el.button(
                "Siguiente",
                on_click=State.next_cashbox_page,
                class_name="px-3 py-2 rounded-md border bg-white hover:bg-gray-50 min-h-[40px]",
            ),
        ),
        class_name="flex flex-col gap-3 items-center sm:flex-row sm:justify-between",
    )


def cashbox_logs_section() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h2(
                "Aperturas y cierres de caja",
                class_name="text-xl font-semibold text-gray-800",
            ),
            rx.el.p(
                "Consulta quien abrio o cerro la caja y cuando lo hizo.",
                class_name="text-sm text-gray-600",
            ),
            class_name="flex flex-col gap-1",
        ),
        cashbox_log_filters(),
        rx.el.table(
            rx.el.thead(
                rx.el.tr(
                    rx.el.th("Fecha y Hora", class_name="py-3 px-4 text-left"),
                    rx.el.th("Evento", class_name="py-3 px-4 text-left"),
                    rx.el.th("Usuario", class_name="py-3 px-4 text-left"),
                    rx.el.th(
                        "Monto Apertura", class_name="py-3 px-4 text-right"
                    ),
                    rx.el.th(
                        "Monto Cierre", class_name="py-3 px-4 text-right"
                    ),
                    rx.el.th("Acciones", class_name="py-3 px-4 text-center"),
                    class_name="bg-gray-100",
                )
            ),
            rx.el.tbody(rx.foreach(State.filtered_cashbox_logs, cashbox_log_row)),
            class_name="min-w-full",
        ),
        rx.cond(
            State.filtered_cashbox_logs.length() == 0,
            rx.el.p(
                "Aun no hay aperturas o cierres registrados.",
                class_name="text-center text-gray-500 py-6",
            ),
            rx.fragment(),
        ),
        class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md overflow-x-auto flex flex-col gap-4",
    )


def delete_sale_modal() -> rx.Component:
    return rx.cond(
        State.sale_delete_modal_open,
        rx.el.div(
            rx.el.div(
                on_click=State.close_sale_delete_modal,
                class_name="fixed inset-0 bg-black/40",
            ),
            rx.el.div(
                rx.el.h3(
                    "Eliminar venta",
                    class_name="text-lg font-semibold text-gray-800",
                ),
                rx.el.p(
                    "Ingrese el motivo para eliminar la venta seleccionada. Esta acción no se puede deshacer.",
                    class_name="text-sm text-gray-600",
                ),
                rx.el.textarea(
                    placeholder="Detalle aquí el motivo...",
                    value=State.sale_delete_reason,
                    on_change=lambda value: State.set_sale_delete_reason(value),
                    class_name="w-full mt-4 p-3 border rounded-lg min-h-[120px]",
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=State.close_sale_delete_modal,
                        class_name="px-4 py-2 rounded-md border text-gray-700 hover:bg-gray-50 min-h-[42px]",
                    ),
                    rx.el.button(
                        rx.icon("trash-2", class_name="h-4 w-4"),
                        "Eliminar",
                        on_click=State.delete_sale,
                        class_name="flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-red-600 text-white hover:bg-red-700 min-h-[42px]",
                    ),
                    class_name="flex justify-end gap-3 mt-4",
                ),
                class_name="relative z-10 w-full max-w-lg rounded-xl bg-white p-6 shadow-xl",
            ),
            class_name="fixed inset-0 z-50 flex items-center justify-center px-4",
        ),
        rx.fragment(),
    )


def close_cashbox_modal() -> rx.Component:
    return rx.cond(
        State.cashbox_close_modal_open,
        rx.el.div(
            rx.el.div(
                on_click=State.close_cashbox_close_modal,
                class_name="fixed inset-0 bg-black/40",
            ),
            rx.el.div(
                rx.el.h3(
                    "Resumen de Caja",
                    class_name="text-xl font-semibold text-gray-800",
                ),
                rx.el.p(
                    rx.el.span("Fecha: "),
                    rx.cond(
                        State.cashbox_close_summary_date == "",
                        "Hoy",
                        State.cashbox_close_summary_date,
                    ),
                    class_name="text-sm text-gray-600",
                ),
                rx.el.p(
                    rx.el.span("Responsable: "),
                    State.current_user["username"],
                    class_name="text-sm text-gray-600 mb-4",
                ),
                rx.el.div(
                    rx.el.h4(
                        "Totales por método",
                        class_name="text-sm font-semibold text-gray-700 mb-2",
                    ),
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("Método", class_name="py-2 px-3 text-left"),
                                rx.el.th("Monto", class_name="py-2 px-3 text-right"),
                                class_name="bg-gray-100 text-sm",
                            )
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                State.cashbox_close_totals,
                                lambda item: rx.el.tr(
                                    rx.el.td(
                                        item["method"],
                                        class_name="py-2 px-3 text-left text-sm",
                                    ),
                                    rx.el.td(
                                        item["amount"],
                                        class_name="py-2 px-3 text-right text-sm font-semibold",
                                    ),
                                    class_name="border-b",
                                ),
                            ),
                            rx.el.tr(
                                rx.el.td(
                                    rx.el.span("Total cierre", class_name="font-semibold"),
                                    class_name="py-2 px-3 text-left text-sm",
                                ),
                                rx.el.td(
                                    State.cashbox_close_total_amount,
                                    class_name="py-2 px-3 text-right text-sm font-bold",
                                ),
                                class_name="border-t border-gray-200 bg-gray-50",
                            )
                        ),
                        class_name="w-full text-sm",
                    ),
                    class_name="mb-6",
                ),
                rx.el.div(
                    rx.el.h4(
                        "Detalle de ventas",
                        class_name="text-sm font-semibold text-gray-700 mb-2",
                    ),
                    rx.el.div(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    rx.el.th(
                                        "Fecha y Hora", class_name="py-2 px-3 text-left"
                                    ),
                                    rx.el.th(
                                        "Usuario", class_name="py-2 px-3 text-left"
                                    ),
                                    rx.el.th(
                                        "Método", class_name="py-2 px-3 text-left"
                                    ),
                                    rx.el.th(
                                        "Total", class_name="py-2 px-3 text-right"
                                    ),
                                    class_name="bg-gray-100 text-sm",
                                )
                            ),
                            rx.el.tbody(
                                rx.foreach(
                                    State.cashbox_close_sales,
                                    lambda sale: rx.el.tr(
                                        rx.el.td(
                                            sale["timestamp"],
                                            class_name="py-2 px-3 text-sm",
                                        ),
                                        rx.el.td(
                                            sale["user"],
                                            class_name="py-2 px-3 text-sm",
                                        ),
                                        rx.el.td(
                                            rx.el.div(
                                                rx.el.p(
                                                    rx.cond(
                                                        sale["payment_label"] == "",
                                                        sale["payment_method"],
                                                        sale["payment_label"],
                                                    ),
                                                    class_name="text-sm font-medium text-gray-800",
                                                ),
                                                rx.cond(
                                                    sale["payment_breakdown"].length()
                                                    > 1,
                                                    rx.el.ul(
                                                        rx.foreach(
                                                            sale["payment_breakdown"],
                                                            lambda item: rx.el.li(
                                                                rx.el.span(
                                                                    item["label"],
                                                                    class_name="text-xs text-gray-600",
                                                                ),
                                                                rx.el.span(
                                                                    State.currency_symbol,
                                                                    item["amount"].to_string(),
                                                                    class_name="text-xs font-semibold text-gray-900",
                                                                ),
                                                                class_name="flex justify-between gap-2",
                                                            ),
                                                        ),
                                                        class_name="flex flex-col gap-1",
                                                    ),
                                                    rx.fragment(),
                                                ),
                                                class_name="flex flex-col gap-1",
                                            ),
                                            class_name="py-2 px-3 text-sm",
                                        ),
                                        rx.el.td(
                                            State.currency_symbol,
                                            sale["total"].to_string(),
                                            class_name="py-2 px-3 text-right text-sm font-semibold",
                                        ),
                                        class_name="border-b",
                                    ),
                                )
                            ),
                            class_name="min-w-full text-sm",
                        ),
                        class_name="max-h-64 overflow-y-auto",
                    ),
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=State.close_cashbox_close_modal,
                        class_name="px-4 py-2 rounded-md border text-gray-700 hover:bg-gray-50 min-h-[42px]",
                    ),
                    rx.el.button(
                        rx.icon("lock", class_name="h-4 w-4"),
                        "Confirmar Cierre",
                        on_click=State.close_cashbox_day,
                        class_name="flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 min-h-[42px]",
                    ),
                    class_name="flex justify-end gap-3 mt-6",
                ),
                class_name="relative z-10 w-full max-w-4xl rounded-xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto",
            ),
            class_name="fixed inset-0 z-50 flex items-center justify-center px-4",
        ),
        rx.fragment(),
    )


def cashbox_log_modal() -> rx.Component:
    return rx.cond(
        State.cashbox_log_modal_open,
        rx.el.div(
            rx.el.div(
                on_click=State.close_cashbox_log_modal,
                class_name="fixed inset-0 bg-black/40",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.h3(
                        "Detalle de apertura/cierre",
                        class_name="text-lg font-semibold text-gray-800",
                    ),
                    rx.el.p(
                        "Resumen del movimiento de caja seleccionado.",
                        class_name="text-sm text-gray-600",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.cond(
                    State.cashbox_log_selected == None,
                    rx.el.p(
                        "Registro no disponible.",
                        class_name="text-sm text-gray-600",
                    ),
                    rx.el.div(
                        rx.el.div(
                            rx.el.div(
                                rx.el.span(
                                    "Fecha y hora",
                                    class_name="text-xs uppercase tracking-wide text-gray-500",
                                ),
                                rx.el.p(
                                    State.cashbox_log_selected["timestamp"],
                                    class_name="text-sm font-semibold text-gray-900",
                                ),
                                class_name="flex flex-col gap-1",
                            ),
                            rx.el.div(
                                rx.el.span(
                                    "Evento",
                                    class_name="text-xs uppercase tracking-wide text-gray-500",
                                ),
                                rx.cond(
                                    State.cashbox_log_selected["action"] == "apertura",
                                    rx.el.span(
                                        "Apertura",
                                        class_name="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-700",
                                    ),
                                    rx.el.span(
                                        "Cierre",
                                        class_name="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-orange-100 text-orange-700",
                                    ),
                                ),
                                class_name="flex flex-col gap-1",
                            ),
                            rx.el.div(
                                rx.el.span(
                                    "Usuario",
                                    class_name="text-xs uppercase tracking-wide text-gray-500",
                                ),
                                rx.el.p(
                                    State.cashbox_log_selected["user"],
                                    class_name="text-sm font-semibold text-gray-900",
                                ),
                                class_name="flex flex-col gap-1",
                            ),
                            class_name="grid grid-cols-1 sm:grid-cols-3 gap-3",
                        ),
                        rx.el.div(
                            rx.el.div(
                                rx.el.span(
                                    "Monto apertura",
                                    class_name="text-xs uppercase tracking-wide text-gray-500",
                                ),
                                rx.el.p(
                                    State.currency_symbol,
                                    State.cashbox_log_selected[
                                        "opening_amount"
                                    ].to_string(),
                                    class_name="text-lg font-semibold text-gray-900",
                                ),
                                class_name="flex flex-col gap-1",
                            ),
                            rx.el.div(
                                rx.el.span(
                                    "Monto cierre",
                                    class_name="text-xs uppercase tracking-wide text-gray-500",
                                ),
                                rx.el.p(
                                    State.currency_symbol,
                                    State.cashbox_log_selected[
                                        "closing_total"
                                    ].to_string(),
                                    class_name="text-lg font-semibold text-gray-900",
                                ),
                                class_name="flex flex-col gap-1",
                            ),
                            class_name="grid grid-cols-1 sm:grid-cols-2 gap-3",
                        ),
                        rx.cond(
                            State.cashbox_log_selected["totals_by_method"].length()
                            == 0,
                            rx.el.div(
                                rx.el.h4(
                                    "Totales por metodo",
                                    class_name="text-sm font-semibold text-gray-700",
                                ),
                                rx.el.p(
                                    "Sin totales registrados para este evento.",
                                    class_name="text-sm text-gray-600",
                                ),
                                class_name="bg-gray-50 border border-gray-200 rounded-lg p-3",
                            ),
                            rx.el.div(
                                rx.el.h4(
                                    "Totales por metodo",
                                    class_name="text-sm font-semibold text-gray-700",
                                ),
                                rx.el.ul(
                                    rx.foreach(
                                        State.cashbox_log_selected["totals_by_method"],
                                        lambda item: rx.el.li(
                                            rx.el.span(
                                                item["method"],
                                                class_name="text-sm text-gray-700",
                                            ),
                                            rx.el.span(
                                                State.currency_symbol,
                                                item["amount"].to_string(),
                                                class_name="text-sm font-semibold text-gray-900",
                                            ),
                                            class_name="flex items-center justify-between",
                                        ),
                                    ),
                                    class_name="flex flex-col gap-2",
                                ),
                                class_name="bg-gray-50 border border-gray-200 rounded-lg p-3",
                            ),
                        ),
                        rx.el.div(
                            rx.el.span(
                                "Notas",
                                class_name="text-xs uppercase tracking-wide text-gray-500",
                            ),
                            rx.el.p(
                                rx.cond(
                                    State.cashbox_log_selected["notes"] == "",
                                    "Sin notas adicionales.",
                                    State.cashbox_log_selected["notes"],
                                ),
                                class_name="text-sm text-gray-700",
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                        class_name="flex flex-col gap-4",
                    ),
                ),
                rx.el.div(
                    rx.el.button(
                        "Cerrar",
                        on_click=State.close_cashbox_log_modal,
                        class_name="px-4 py-2 rounded-md border text-gray-700 hover:bg-gray-50 min-h-[42px]",
                    ),
                    class_name="flex justify-end pt-2",
                ),
                class_name="relative z-10 w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto",
            ),
            class_name="fixed inset-0 z-50 flex items-center justify-center px-4",
        ),
        rx.fragment(),
    )


def cashbox_page() -> rx.Component:
    return rx.cond(
        State.current_user["privileges"]["view_cashbox"],
        rx.el.div(
            rx.el.h1(
                "Gestion de Caja",
                class_name="text-2xl font-bold text-gray-800 mb-6",
            ),
            cashbox_opening_card(),
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.h2(
                            "Listado de Pagos",
                            class_name="text-lg font-semibold text-gray-800",
                        ),
                        rx.el.div(
                            cashbox_filters(),
                            class_name="bg-gray-50 border border-gray-200 rounded-lg p-3 sm:p-4",
                        ),
                        class_name="flex flex-col gap-4",
                    ),
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("Fecha y Hora", class_name="py-3 px-4 text-left"),
                                rx.el.th("Usuario", class_name="py-3 px-4 text-left"),
                                rx.el.th("Pago", class_name="py-3 px-4 text-left"),
                                rx.el.th("Total", class_name="py-3 px-4 text-right"),
                                rx.el.th("Detalle", class_name="py-3 px-4 text-left"),
                                rx.el.th("Acciones", class_name="py-3 px-4 text-center"),
                                class_name="bg-gray-100",
                            )
                        ),
                        rx.el.tbody(
                            rx.foreach(State.paginated_cashbox_sales, sale_row),
                        ),
                        class_name="min-w-full",
                    ),
                    rx.cond(
                        State.filtered_cashbox_sales.length() == 0,
                        rx.el.p(
                            "Aun no hay ventas registradas.",
                            class_name="text-center text-gray-500 py-8",
                        ),
                        pagination_controls(),
                    ),
                    class_name="flex flex-col gap-4",
                ),
                class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md overflow-x-auto flex flex-col gap-4",
            ),
            cashbox_logs_section(),
            delete_sale_modal(),
            close_cashbox_modal(),
            cashbox_log_modal(),
            class_name="p-4 sm:p-6 flex flex-col gap-6 w-full max-w-7xl mx-auto",
        ),
        rx.el.div(
            rx.el.h1("Acceso Denegado", class_name="text-2xl font-bold text-red-600"),
            rx.el.p(
                "No tienes privilegios para ver la gestion de caja.",
                class_name="text-gray-600 mt-2",
            ),
            class_name="flex flex-col items-center justify-center h-full p-6",
        ),
    )
