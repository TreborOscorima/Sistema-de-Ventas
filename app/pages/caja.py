import reflex as rx
from app.state import State
from app.components.ui import (
  date_range_filter,
  filter_action_buttons,
  section_header,
  BUTTON_STYLES,
  modal_container,
  status_badge,
  pagination_controls,
  card_container,
  info_badge,
  form_textarea,
  TABLE_STYLES,
  INPUT_STYLES,
  toggle_switch,
  page_title,
  permission_guard,
)


def cashbox_filters() -> rx.Component:
  """Seccion de filtros para ventas de caja."""
  start_filter, end_filter = date_range_filter(
    start_value=State.cashbox_staged_start_date,
    end_value=State.cashbox_staged_end_date,
    on_start_change=State.set_cashbox_staged_start_date,
    on_end_change=State.set_cashbox_staged_end_date,
  )

  toggle_section = rx.el.div(
    rx.el.label("Mostrar adelantos", class_name="text-sm font-medium text-slate-600"),
    rx.el.div(
      toggle_switch(
        checked=State.show_cashbox_advances,
        on_change=State.set_show_cashbox_advances,
      ),
      rx.el.span(
        "Incluir adelantos en el listado",
        class_name="text-sm text-slate-600",
      ),
      class_name="flex items-center gap-2",
    ),
    class_name="flex flex-col gap-2 bg-white border border-slate-200 rounded-xl px-3 py-2",
  )

  return rx.el.div(
    rx.el.div(
      start_filter,
      end_filter,
      toggle_section,
      class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4",
    ),
    rx.el.div(
      filter_action_buttons(
        on_search=State.apply_cashbox_filters,
        on_clear=State.reset_cashbox_filters,
        on_export=State.export_cashbox_report,
      ),
      class_name="flex w-full lg:w-auto lg:justify-end",
    ),
    class_name="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4",
  )


def cashbox_log_filters() -> rx.Component:
  """Seccion de filtros para movimientos de caja."""
  start_filter, end_filter = date_range_filter(
    start_value=State.cashbox_log_staged_start_date,
    end_value=State.cashbox_log_staged_end_date,
    on_start_change=State.set_cashbox_log_staged_start_date,
    on_end_change=State.set_cashbox_log_staged_end_date,
  )

  return rx.el.div(
    start_filter,
    end_filter,
    filter_action_buttons(
      on_search=State.apply_cashbox_log_filters,
      on_clear=State.reset_cashbox_log_filters,
      on_export=State.export_cashbox_sessions,
      export_text="Exportar",
    ),
    class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 items-end",
  )


def cashbox_payments_header() -> rx.Component:
  date_range = rx.cond(
    (State.cashbox_filter_start_date != "") | (State.cashbox_filter_end_date != ""),
    rx.el.span(
      rx.cond(
        State.cashbox_filter_start_date != "",
        State.cashbox_filter_start_date,
        "Inicio",
      ),
      " → ",
      rx.cond(
        State.cashbox_filter_end_date != "",
        State.cashbox_filter_end_date,
        "Hoy",
      ),
    ),
    rx.el.span("Todo el periodo"),
  )

  return rx.el.div(
    rx.el.div(
      rx.el.h2("LISTADO DE PAGOS", class_name="text-lg font-semibold text-slate-900"),
      rx.el.p(
        "Ventas registradas según el rango seleccionado.",
        class_name="text-sm text-slate-500",
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.span(
        rx.icon("calendar", class_name="h-3.5 w-3.5 text-slate-400"),
        date_range,
        class_name="inline-flex items-center gap-1.5 rounded-full bg-slate-100/70 px-3 py-1 text-[11px] font-semibold text-slate-600",
      ),
      rx.el.span(
        rx.cond(
          State.show_cashbox_advances,
          "Adelantos incluidos",
          "Adelantos ocultos",
        ),
        class_name=rx.cond(
          State.show_cashbox_advances,
          "inline-flex items-center rounded-full bg-emerald-100 px-3 py-1 text-[11px] font-semibold text-emerald-700",
          "inline-flex items-center rounded-full bg-amber-100 px-3 py-1 text-[11px] font-semibold text-amber-700",
        ),
      ),
      rx.el.span(
        "Página ",
        State.cashbox_current_page.to_string(),
        " de ",
        State.cashbox_total_pages.to_string(),
        class_name="inline-flex items-center rounded-full bg-slate-100/70 px-3 py-1 text-[11px] font-semibold text-slate-600",
      ),
      class_name="flex flex-wrap items-center gap-2",
    ),
    class_name="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between",
  )


def cashbox_opening_card() -> rx.Component:
  return card_container(
    rx.el.div(
      rx.el.div(
        rx.icon(
          rx.cond(State.cashbox_is_open, "wallet-cards", "alarm-clock"),
          class_name=rx.cond(
            State.cashbox_is_open,
            "h-7 w-7 text-emerald-600",
            "h-7 w-7 text-indigo-600",
          ),
        ),
        rx.el.div(
          rx.el.p(
            rx.cond(
              State.cashbox_is_open,
              "CAJA ABIERTA",
              "APERTURA DE CAJA REQUIRIDA",
            ),
            class_name="text-sm font-semibold text-slate-900",
          ),
          rx.el.p(
            rx.cond(
              State.cashbox_is_open,
              "La caja sigue abierta hasta que confirmes el cierre.",
              "Ingresa el monto inicial para comenzar la jornada.",
            ),
            class_name="text-[11px] text-slate-600",
          ),
          class_name="flex flex-col",
        ),
        class_name="flex items-start gap-2.5",
      ),
      rx.cond(
        State.cashbox_is_open,
        rx.el.div(
          rx.el.div(
            rx.el.span(
              "Monto inicial",
              class_name="text-xs uppercase tracking-wide text-slate-500",
            ),
            rx.el.span(
              State.currency_symbol,
              State.cashbox_opening_amount_display,
              class_name="text-base font-semibold text-slate-900",
            ),
            class_name="flex flex-col gap-0.5 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-1.5",
          ),
          rx.el.div(
            rx.el.span(
              "Apertura",
              class_name="text-xs uppercase tracking-wide text-slate-500",
            ),
            rx.el.span(
              rx.cond(
                State.cashbox_opening_time == "",
                "Sin registro",
                State.cashbox_opening_time,
              ),
              class_name="text-sm font-medium text-slate-800",
            ),
            class_name="flex flex-col gap-0.5 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5",
          ),
          class_name="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full md:w-auto",
        ),
        rx.fragment(),
      ),
      class_name="flex flex-col md:flex-row justify-between gap-2",
    ),
    rx.el.div(
      rx.el.label("Caja inicial", class_name="text-sm font-medium text-slate-800"),
      rx.el.form(
        rx.el.div(
          rx.el.input(
            name="amount",
            type="number",
            step="0.01",
            default_value=State.cashbox_open_amount_input,
            placeholder="Ej: 150.00",
            disabled=State.cashbox_is_open,
            class_name=rx.cond(
              State.cashbox_is_open,
              f"{INPUT_STYLES['disabled']} py-2 text-sm",
              f"{INPUT_STYLES['default']} py-2 text-sm",
            ),
          ),
          rx.el.button(
            rx.icon("play", class_name="h-4 w-4"),
            rx.cond(State.cashbox_is_open, "Caja abierta", "Aperturar caja"),
            type="submit",
            disabled=State.cashbox_is_open | ~State.current_user["privileges"]["manage_cashbox"],
            class_name=rx.cond(
              State.cashbox_is_open | ~State.current_user["privileges"]["manage_cashbox"],
              f"{BUTTON_STYLES['disabled']} w-full sm:w-auto sm:min-w-[152px]",
              f"{BUTTON_STYLES['primary']} w-full sm:w-auto sm:min-w-[152px]",
            ),
          ),
          rx.el.button(
            rx.icon("lock", class_name="h-4 w-4"),
            "Cerrar Caja",
            type="button",
            on_click=State.open_cashbox_close_modal,
            disabled=~State.cashbox_is_open | ~State.current_user["privileges"]["manage_cashbox"],
            class_name=rx.cond(
              State.cashbox_is_open & State.current_user["privileges"]["manage_cashbox"],
              f"{BUTTON_STYLES['primary']} w-full sm:w-auto sm:min-w-[136px]",
              f"{BUTTON_STYLES['disabled']} w-full sm:w-auto sm:min-w-[136px]",
            ),
          ),
          class_name="flex flex-col sm:flex-row gap-2",
        ),
        on_submit=State.handle_cashbox_form_submit,
      ),
      rx.el.p(
        "Consejo: registra el efectivo inicial real para un cuadre correcto al cierre.",
        class_name="text-[11px] text-slate-500",
      ),
      class_name="flex flex-col gap-1",
    ),
    style="compact",
    gap="gap-1.5",
  )


def sale_items_list(
  items: rx.Var[list[dict]],
  preview_items: rx.Var[list[dict]],
  hidden_count: rx.Var[int],
  sale_id: rx.Var[str],
) -> rx.Component:
  expanded = State.expanded_cashbox_sale_id == sale_id
  def _item_row(item: rx.Var[dict]) -> rx.Component:
    return rx.el.div(
      rx.el.div(
        rx.el.span(
          item["description"],
          title=item["description"],
          class_name="block text-sm font-medium text-slate-900 truncate",
        ),
      ),
      rx.el.div(
        rx.el.span(
          item["quantity"].to_string(),
          " x ",
          item["sale_price"].to_string(),
          class_name="text-[11px] text-slate-500",
        ),
        rx.el.span(
          State.currency_symbol,
          item["subtotal"].to_string(),
          class_name="text-[11px] font-semibold text-slate-700",
        ),
        class_name="flex justify-between items-center",
      ),
      class_name="flex flex-col gap-0.5 border-b border-dashed border-slate-100 last:border-0 pb-1 last:pb-0",
    )

  list_content = rx.cond(
    expanded,
    rx.foreach(items, _item_row),
    rx.foreach(preview_items, _item_row),
  )

  return rx.el.div(
    list_content,
    rx.cond(
      expanded | (hidden_count <= 0),
      rx.fragment(),
      rx.el.div(
        rx.el.span(
          "Ver ",
          hidden_count.to_string(),
          " item(s) más",
          class_name="text-[11px] text-indigo-600 font-medium",
        ),
        class_name="pt-1",
      ),
    ),
    class_name=rx.cond(
      expanded,
      "flex flex-col gap-1",
      "flex flex-col gap-1 h-24 overflow-hidden",
    ),
  )


def render_payment_details(details: rx.Var[str]) -> rx.Component:
  return rx.cond(
    details.length() > 50,
    rx.tooltip(
      rx.el.span(
        rx.icon("info", class_name="h-3 w-3"),
        "Detalle",
        class_name="inline-flex items-center gap-1 rounded-full bg-slate-100/80 px-2 py-0.5 text-[11px] font-semibold text-slate-600 hover:bg-slate-200 cursor-help",
      ),
      content=details,
      side="bottom",
      align="start",
      side_offset=6,
    ),
    rx.el.p(details, class_name="text-[11px] text-slate-500"),
  )


def method_chip(label: rx.Var | str, color_classes: str) -> rx.Component:
  return rx.el.span(
    label,
    class_name=(
      "inline-flex items-center rounded-full px-2 py-0.5 "
      f"text-[11px] font-semibold tracking-wide {color_classes}"
    ),
  )


def payment_method_badge(method: rx.Var[str]) -> rx.Component:
  is_credit_sale = (method == None) | (method == "") | (method == "-")
  return rx.cond(
    is_credit_sale,
    method_chip("Crédito / Fiado", "bg-amber-100 text-amber-700"),
    rx.match(
      method,
      ("Efectivo", method_chip("Efectivo", "bg-emerald-100 text-emerald-700")),
      ("Yape", method_chip("Yape", "bg-violet-100 text-violet-700")),
      ("Plin", method_chip("Plin", "bg-violet-100 text-violet-700")),
      (
        "Billetera Digital (Yape)",
        method_chip("Yape", "bg-violet-100 text-violet-700"),
      ),
      (
        "Billetera Digital (Plin)",
        method_chip("Plin", "bg-violet-100 text-violet-700"),
      ),
      ("Transferencia", method_chip("Transferencia", "bg-sky-100 text-sky-700")),
      ("Transferencia Bancaria", method_chip("Transferencia", "bg-sky-100 text-sky-700")),
      ("Tarjeta", method_chip(method, "bg-blue-100 text-blue-700")),
      ("T. Debito", method_chip(method, "bg-blue-100 text-blue-700")),
      ("T. Credito", method_chip(method, "bg-blue-100 text-blue-700")),
      ("Tarjeta de Débito", method_chip("Tarjeta Débito", "bg-blue-100 text-blue-700")),
      ("Tarjeta de Crédito", method_chip("Tarjeta Crédito", "bg-blue-100 text-blue-700")),
      ("Pago Mixto", method_chip("Mixto", "bg-amber-100 text-amber-700")),
      rx.el.span(
        method,
        class_name="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600",
      ),
    ),
  )


def sale_row(sale: rx.Var[dict]) -> rx.Component:
  return rx.el.tr(
    rx.el.td(
      sale["timestamp"],
      class_name="py-3.5 px-4 align-top text-[13px] text-slate-500 whitespace-nowrap",
    ),
    rx.el.td(
      sale["user"],
      class_name="py-3.5 px-4 align-top text-sm font-medium text-slate-700",
    ),
    rx.el.td(
      payment_method_badge(sale["payment_method"]),
      rx.el.div(
        render_payment_details(sale["payment_details"]),
        class_name="mt-1",
      ),
      rx.cond(
        sale["is_deleted"],
        rx.el.div(
          info_badge("Venta eliminada", variant="danger"),
          rx.el.p(
            sale["delete_reason"],
            class_name="text-xs text-red-600 mt-1",
          ),
          class_name="mt-2",
        ),
        rx.fragment(),
      ),
      class_name="py-3.5 px-4 align-top text-sm text-slate-700",
    ),
    rx.el.td(
      rx.el.span(
        State.currency_symbol,
        sale["amount"].to_string(),
        class_name="text-base font-semibold text-slate-900 tabular-nums tracking-tight",
      ),
      class_name="py-3.5 px-4 text-right align-top",
    ),
    rx.el.td(
      sale_items_list(
        sale["items"],
        sale["items_preview"],
        sale["items_hidden_count"],
        sale["sale_id"],
      ),
      on_click=lambda _, sale_id=sale["sale_id"]: State.toggle_cashbox_sale_detail(sale_id),
      class_name="py-3.5 px-4 align-top min-w-[220px] cursor-pointer",
    ),
    rx.el.td(
      rx.el.div(
        rx.el.button(
          rx.icon("printer", class_name="h-4 w-4"),
          on_click=lambda _, sale_id=sale["sale_id"]: State.reprint_sale_receipt(sale_id),
          disabled=sale["is_deleted"],
          title="Reimprimir",
          aria_label="Reimprimir",
          class_name=rx.cond(
            sale["is_deleted"],
            "p-2 rounded-md text-slate-300 bg-transparent cursor-not-allowed",
            "p-2 rounded-md text-indigo-600 hover:bg-indigo-50 active:bg-indigo-100 transition-colors",
          ),
        ),
        rx.el.button(
          rx.icon("trash-2", class_name="h-4 w-4"),
          on_click=lambda _, sale_id=sale["sale_id"]: State.open_sale_delete_modal(sale_id),
          disabled=sale["is_deleted"] | ~State.current_user["privileges"]["delete_sales"],
          title="Eliminar",
          aria_label="Eliminar",
          class_name=rx.cond(
            sale["is_deleted"] | ~State.current_user["privileges"]["delete_sales"],
            "p-2 rounded-md text-slate-300 bg-transparent cursor-not-allowed",
            "p-2 rounded-md text-red-600 hover:bg-red-50 active:bg-red-100 transition-colors",
          ),
        ),
        class_name=(
          "flex flex-col gap-2 sm:flex-row sm:justify-center "
          "rounded-full border border-slate-200/80 bg-white/80 px-2 py-1 shadow-sm"
        ),
      ),
      class_name="py-3.5 px-4 align-top",
    ),
    class_name=(
      "border-b border-slate-100 transition-colors hover:bg-indigo-50/30 "
      "odd:bg-white even:bg-slate-50/30"
    ),
  )


def cashbox_log_row(log: rx.Var[dict]) -> rx.Component:
  return rx.el.tr(
    rx.el.td(log["timestamp"], class_name="py-3 px-4"),
    rx.el.td(
      rx.cond(
        log["action"] == "apertura",
        status_badge("Apertura", status_colors={"apertura": ("bg-emerald-100", "text-emerald-700")}),
        status_badge("Cierre", status_colors={"cierre": ("bg-orange-100", "text-orange-700")}),
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
      rx.el.div(
        rx.el.button(
          rx.icon("eye", class_name="h-4 w-4"),
          on_click=lambda _, log_id=log["id"]: State.show_cashbox_log(log_id),
          title="Visualizar",
          aria_label="Visualizar",
          class_name="p-2 rounded-md text-indigo-600 hover:bg-indigo-50 transition-colors",
        ),
        rx.cond(
          log["action"] == "cierre",
          rx.el.button(
            rx.icon("file-text", class_name="h-4 w-4"),
            on_click=lambda _, log_id=log["id"]: State.export_cashbox_close_pdf_for_log(
              log_id
            ),
            title="Descargar PDF",
            aria_label="Descargar PDF",
            class_name="p-2 rounded-md text-red-600 hover:bg-red-50 transition-colors",
          ),
          rx.fragment(),
        ),
        rx.cond(
          log["action"] == "cierre",
          rx.el.button(
            rx.icon("printer", class_name="h-4 w-4"),
            on_click=lambda _, log_id=log["id"]: State.print_cashbox_close_summary_for_log(
              log_id
            ),
            title="Reimprimir resumen",
            aria_label="Reimprimir resumen",
            class_name="p-2 rounded-md text-indigo-600 hover:bg-indigo-50 transition-colors",
          ),
          rx.fragment(),
        ),
        class_name="flex flex-row gap-2 justify-center",
      ),
      class_name="py-3 px-4 text-center",
    ),
    class_name="border-b hover:bg-slate-50 transition-colors",
  )


def cashbox_logs_section() -> rx.Component:
  return card_container(
    section_header(
      "APERTURAS Y CIERRES DE CAJA",
      "Consulta quien abrio o cerro la caja y cuando lo hizo.",
    ),
    cashbox_log_filters(),
    rx.el.div(
      rx.el.table(
        rx.el.thead(
          rx.el.tr(
            rx.el.th("Fecha y Hora", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Evento", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Usuario", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th(
              "Monto Apertura", class_name=f"{TABLE_STYLES['header_cell']} text-right"
            ),
            rx.el.th(
              "Monto Cierre", class_name=f"{TABLE_STYLES['header_cell']} text-right"
            ),
            rx.el.th(
              "Acciones", class_name=f"{TABLE_STYLES['header_cell']} text-center"
            ),
            class_name=TABLE_STYLES["header"],
          )
        ),
        rx.el.tbody(rx.foreach(State.filtered_cashbox_logs, cashbox_log_row)),
        class_name="min-w-full",
      ),
      class_name="overflow-x-auto rounded-lg border border-slate-200",
    ),
    rx.cond(
      State.filtered_cashbox_logs.length() > 0,
      pagination_controls(
        current_page=State.cashbox_log_current_page,
        total_pages=State.cashbox_log_total_pages,
        on_prev=State.prev_cashbox_log_page,
        on_next=State.next_cashbox_log_page,
      ),
      rx.fragment(),
    ),
    rx.cond(
      State.filtered_cashbox_logs.length() == 0,
      rx.el.p(
        "Aun no hay aperturas o cierres registrados.",
        class_name="text-center text-slate-500 py-6",
      ),
      rx.fragment(),
    ),
  )


def delete_sale_modal() -> rx.Component:
  return modal_container(
    is_open=State.sale_delete_modal_open,
    on_close=State.close_sale_delete_modal,
    title="Eliminar venta",
    description="Ingrese el motivo para eliminar la venta seleccionada. Esta acción no se puede deshacer.",
    children=[
      form_textarea(
        label="Motivo de eliminación",
        default_value=State.sale_delete_reason,
        on_blur=State.set_sale_delete_reason,
        placeholder="Detalle aquí el motivo...",
      )
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_sale_delete_modal,
        class_name=BUTTON_STYLES["secondary"],
      ),
      rx.el.button(
        rx.icon("trash-2", class_name="h-4 w-4"),
        "Eliminar",
        on_click=State.delete_sale,
        class_name=BUTTON_STYLES["danger"],
      ),
      class_name="flex justify-end gap-3 mt-4",
    ),
  )


def close_cashbox_modal() -> rx.Component:
  return modal_container(
    is_open=State.cashbox_close_modal_open,
    on_close=State.close_cashbox_close_modal,
    title="Resumen de Caja",
    description=f"Cierre de caja para {State.current_user['username']}",
    max_width="max-w-4xl",
    children=[
      rx.el.div(
        rx.el.h4(
          "Resumen de caja",
          class_name="text-sm font-semibold text-slate-700 mb-2",
        ),
        rx.el.table(
          rx.el.tbody(
            rx.el.tr(
              rx.el.td("Apertura", class_name="py-2 px-3 text-left text-sm"),
              rx.el.td(
                State.cashbox_close_opening_amount_display,
                class_name="py-2 px-3 text-right text-sm font-semibold",
              ),
              class_name="border-b",
            ),
            rx.el.tr(
              rx.el.td("Ingresos reales", class_name="py-2 px-3 text-left text-sm"),
              rx.el.td(
                State.cashbox_close_income_total_display,
                class_name="py-2 px-3 text-right text-sm font-semibold",
              ),
              class_name="border-b",
            ),
            rx.el.tr(
              rx.el.td("Egresos caja chica", class_name="py-2 px-3 text-left text-sm"),
              rx.el.td(
                State.cashbox_close_expense_total_display,
                class_name="py-2 px-3 text-right text-sm font-semibold",
              ),
              class_name="border-b",
            ),
            rx.el.tr(
              rx.el.td(
                rx.el.span("Saldo esperado", class_name="font-semibold"),
                class_name="py-2 px-3 text-left text-sm",
              ),
              rx.el.td(
                State.cashbox_close_expected_total_display,
                class_name="py-2 px-3 text-right text-sm font-bold",
              ),
              class_name="border-t border-slate-200 bg-slate-50",
            ),
          ),
          class_name="w-full text-sm border rounded-lg",
        ),
        class_name="mb-6",
      ),
      rx.el.div(
        rx.el.h4(
          "Ingresos por metodo",
          class_name="text-sm font-semibold text-slate-700 mb-2",
        ),
        rx.el.table(
          rx.el.thead(
            rx.el.tr(
              rx.el.th("Metodo", class_name=TABLE_STYLES["header_cell"]),
              rx.el.th(
                "Movimientos", class_name=f"{TABLE_STYLES['header_cell']} text-center"
              ),
              rx.el.th("Total", class_name=f"{TABLE_STYLES['header_cell']} text-right"),
              class_name=TABLE_STYLES["header"],
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
                  item["count"],
                  class_name="py-2 px-3 text-center text-sm font-semibold",
                ),
                rx.el.td(
                  item["total"],
                  class_name="py-2 px-3 text-right text-sm font-semibold",
                ),
                class_name="border-b",
              ),
            ),
            rx.el.tr(
              rx.el.td(
                rx.el.span("Total ingresos", class_name="font-semibold"),
                class_name="py-2 px-3 text-left text-sm",
              ),
              rx.el.td(
                rx.el.span("-", class_name="text-slate-400"),
                class_name="py-2 px-3 text-center text-sm",
              ),
              rx.el.td(
                State.cashbox_close_income_total_display,
                class_name="py-2 px-3 text-right text-sm font-bold",
              ),
              class_name="border-t border-slate-200 bg-slate-50",
            )
          ),
          class_name="w-full text-sm border rounded-lg",
        ),
        class_name="mb-6",
      ),
      rx.el.div(
        rx.el.h4(
          "Detalle de ingresos",
          class_name="text-sm font-semibold text-slate-700 mb-2",
        ),
        rx.el.div(
          rx.el.table(
            rx.el.thead(
              rx.el.tr(
                rx.el.th("Hora", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Concepto", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th(
                  "Monto", class_name=f"{TABLE_STYLES['header_cell']} text-right"
                ),
                class_name=TABLE_STYLES["header"],
              )
            ),
            rx.el.tbody(
              rx.foreach(
                State.cashbox_close_sales,
                lambda sale: rx.el.tr(
                  rx.el.td(
                    sale["time"],
                    class_name="py-2 px-3 text-sm text-slate-500 font-mono whitespace-nowrap",
                  ),
                  rx.el.td(
                    rx.el.p(
                      sale["concept"],
                      class_name="text-sm font-medium text-slate-900 max-w-md truncate",
                      title=sale["concept"],
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
          class_name="max-h-64 overflow-y-auto overflow-x-auto border rounded-lg",
        ),
      ),
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_cashbox_close_modal,
        class_name=BUTTON_STYLES["secondary"],
      ),
      rx.cond(
        (State.cashbox_close_sales.length() > 0)
        | (State.cashbox_close_totals.length() > 0),
        rx.el.button(
          rx.icon("file-text", class_name="h-4 w-4"),
          "Descargar PDF",
          on_click=State.export_cashbox_close_pdf,
          class_name=(
            "flex items-center gap-2 bg-red-600 text-white px-4 py-2 "
            "rounded-md hover:bg-red-700 transition-colors"
          ),
        ),
        rx.fragment(),
      ),
      rx.el.button(
        rx.icon("lock", class_name="h-4 w-4"),
        "Confirmar Cierre",
        on_click=State.close_cashbox_day,
        class_name="flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 min-h-[42px]",
      ),
      class_name="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 sm:gap-3 mt-4",
    ),
  )


def cashbox_log_modal() -> rx.Component:
  return modal_container(
    is_open=State.cashbox_log_modal_open,
    on_close=State.close_cashbox_log_modal,
    title="Detalle de apertura/cierre",
    description="Resumen del movimiento de caja seleccionado.",
    max_width="max-w-2xl",
    children=[
      rx.cond(
        State.cashbox_log_selected == None,
        rx.el.p("Registro no disponible.", class_name="text-sm text-slate-600"),
        rx.el.div(
          rx.el.div(
            rx.el.div(
              rx.el.span("Fecha y hora", class_name="text-xs uppercase tracking-wide text-slate-500"),
              rx.el.p(State.cashbox_log_selected["timestamp"], class_name="text-sm font-semibold text-slate-900"),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.span("Evento", class_name="text-xs uppercase tracking-wide text-slate-500"),
              rx.cond(
                State.cashbox_log_selected["action"] == "apertura",
                status_badge("Apertura", status_colors={"apertura": ("bg-emerald-100", "text-emerald-700")}),
                status_badge("Cierre", status_colors={"cierre": ("bg-orange-100", "text-orange-700")}),
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.span("Usuario", class_name="text-xs uppercase tracking-wide text-slate-500"),
              rx.el.p(State.cashbox_log_selected["user"], class_name="text-sm font-semibold text-slate-900"),
              class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-1 sm:grid-cols-3 gap-3",
          ),
          rx.el.div(
            rx.el.div(
              rx.el.span("Monto apertura", class_name="text-xs uppercase tracking-wide text-slate-500"),
              rx.el.p(State.currency_symbol, State.cashbox_log_selected["opening_amount"].to_string(), class_name="text-lg font-semibold text-slate-900"),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.span("Monto cierre", class_name="text-xs uppercase tracking-wide text-slate-500"),
              rx.el.p(State.currency_symbol, State.cashbox_log_selected["closing_total"].to_string(), class_name="text-lg font-semibold text-slate-900"),
              class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 gap-3",
          ),
          rx.cond(
            State.cashbox_log_selected["totals_by_method"].length() == 0,
            rx.el.div(
              rx.el.h4("Totales por metodo", class_name="text-sm font-semibold text-slate-700"),
              rx.el.p("Sin totales registrados para este evento.", class_name="text-sm text-slate-600"),
              class_name="bg-slate-50 border border-slate-200 rounded-lg p-3",
            ),
            rx.el.div(
              rx.el.h4("Totales por metodo", class_name="text-sm font-semibold text-slate-700"),
              rx.el.ul(
                rx.foreach(
                  State.cashbox_log_selected["totals_by_method"],
                  lambda item: rx.el.li(
                    rx.el.span(item["method"], class_name="text-sm text-slate-700"),
                    rx.el.span(State.currency_symbol, item["amount"].to_string(), class_name="text-sm font-semibold text-slate-900"),
                    class_name="flex items-center justify-between",
                  ),
                ),
                class_name="flex flex-col gap-2",
              ),
              class_name="bg-slate-50 border border-slate-200 rounded-lg p-3",
            ),
          ),
          rx.el.div(
            rx.el.span("Notas", class_name="text-xs uppercase tracking-wide text-slate-500"),
            rx.el.p(
              rx.cond(
                State.cashbox_log_selected["notes"] == "",
                "Sin notas adicionales.",
                State.cashbox_log_selected["notes"],
              ),
              class_name="text-sm text-slate-700",
            ),
            class_name="flex flex-col gap-1",
          ),
          class_name="flex flex-col gap-4",
        ),
      ),
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cerrar",
        on_click=State.close_cashbox_log_modal,
        class_name=BUTTON_STYLES["secondary"],
      ),
      class_name="flex justify-end pt-2",
    ),
  )


def petty_cash_modal() -> rx.Component:
  return modal_container(
    is_open=State.petty_cash_modal_open,
    on_close=State.close_petty_cash_modal,
    title="Registrar Movimiento",
    description="Ingrese los detalles del gasto o salida de dinero.",
    children=[
      rx.el.div(
        form_textarea(
          label="Motivo / Descripción",
          default_value=State.petty_cash_reason,
          on_blur=State.set_petty_cash_reason,
          placeholder="Ej: Compra de útiles de limpieza",
        ),
        rx.el.div(
          rx.el.div(
            rx.el.label("Cantidad", class_name="text-sm font-medium text-slate-700"),
            rx.el.input(
              type="number",
              step="0.01",
              default_value=State.petty_cash_quantity,
              on_blur=State.set_petty_cash_quantity,
              class_name=INPUT_STYLES,
            ),
            class_name="flex flex-col gap-2"
          ),
          rx.el.div(
            rx.el.label("Unidad", class_name="text-sm font-medium text-slate-700"),
            rx.el.select(
              rx.el.option("Unidad", value="Unidad"),
              rx.el.option("Kg", value="Kg"),
              rx.el.option("Lt", value="Lt"),
              rx.el.option("Paquete", value="Paquete"),
              rx.el.option("Caja", value="Caja"),
              rx.el.option("Otro", value="Otro"),
              default_value=State.petty_cash_unit,
              on_change=State.set_petty_cash_unit,
              class_name=INPUT_STYLES,
            ),
            class_name="flex flex-col gap-2"
          ),
          class_name="grid grid-cols-1 sm:grid-cols-2 gap-4"
        ),
        rx.el.div(
          rx.el.div(
            rx.el.label("Costo Unitario", class_name="text-sm font-medium text-slate-700"),
            rx.el.div(
              rx.el.span(State.currency_symbol, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 font-medium"),
              rx.el.input(
                type="number",
                step="0.01",
                default_value=State.petty_cash_cost,
                on_blur=State.set_petty_cash_cost,
                placeholder="0.00",
                class_name="w-full h-10 pl-8 pr-4 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all",
              ),
              class_name="relative"
            ),
            class_name="flex flex-col gap-2"
          ),
          rx.el.div(
            rx.el.label("Total", class_name="text-sm font-medium text-slate-700"),
            rx.el.div(
              rx.el.span(State.currency_symbol, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 font-medium"),
              rx.el.input(
                type="number",
                step="0.01",
                value=State.petty_cash_amount,
                read_only=True,
                placeholder="0.00",
                class_name="w-full h-10 pl-8 pr-4 text-sm bg-slate-50 border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all",
              ),
              class_name="relative"
            ),
            class_name="flex flex-col gap-2"
          ),
          class_name="grid grid-cols-1 sm:grid-cols-2 gap-4"
        ),
        class_name="flex flex-col gap-4 py-4"
      )
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_petty_cash_modal,
        class_name=BUTTON_STYLES["secondary"],
      ),
      rx.el.button(
        rx.icon("plus", class_name="h-4 w-4"),
        "Registrar",
        on_click=State.add_petty_cash_movement,
        class_name=BUTTON_STYLES["primary"],
      ),
      class_name="flex justify-end gap-3 pt-2",
    )
  )


def petty_cash_view() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.div(
        rx.el.div(
          rx.el.h2("MOVIMIENTOS DE CAJA CHICA", class_name="text-xl font-semibold text-slate-800"),
          rx.el.p("Gestión de gastos y salidas de efectivo.", class_name="text-sm text-slate-500"),
          class_name="flex flex-col mb-4 lg:mb-0",
        ),
        rx.el.div(
          rx.el.div(
            rx.el.span("Saldo Actual", class_name="text-xs font-medium text-slate-500 uppercase tracking-wider"),
            rx.el.span(
              State.currency_symbol + " " + State.cashbox_opening_amount_display,
              class_name="text-2xl font-bold text-indigo-600"
            ),
            class_name="flex flex-col items-start justify-center bg-indigo-50 px-4 py-2 rounded-xl border border-indigo-100 shadow-sm w-full sm:w-auto sm:min-w-[144px]"
          ),
          rx.el.div(
            rx.el.button(
              rx.icon("download", class_name="w-4 h-4 mr-2"),
              "Exportar",
              on_click=State.export_petty_cash_report,
              class_name=f"{BUTTON_STYLES['success']} w-full sm:w-auto sm:min-w-[148px]",
            ),
            rx.el.button(
              rx.icon("plus", class_name="w-4 h-4 mr-2"),
              "Registrar Movimiento",
              on_click=State.open_petty_cash_modal,
              class_name=f"{BUTTON_STYLES['primary']} w-full sm:w-auto sm:min-w-[176px]",
            ),
            class_name="flex flex-col sm:flex-row gap-3 w-full sm:w-auto",
          ),
          class_name="flex flex-col md:flex-row items-stretch md:items-center gap-4 w-full md:w-auto",
        ),
        class_name="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-6",
      ),
      rx.el.div(
        rx.el.table(
          rx.el.thead(
            rx.el.tr(
              rx.el.th(
                "Fecha y Hora",
                class_name=f"{TABLE_STYLES['header_cell']} whitespace-nowrap",
              ),
              rx.el.th(
                "Usuario", class_name=f"{TABLE_STYLES['header_cell']} whitespace-nowrap"
              ),
              rx.el.th(
                "Motivo", class_name=f"{TABLE_STYLES['header_cell']} min-w-[180px]"
              ),
              rx.el.th(
                "Cant.", class_name=f"{TABLE_STYLES['header_cell']} text-right whitespace-nowrap"
              ),
              rx.el.th(
                "Unidad", class_name=f"{TABLE_STYLES['header_cell']} whitespace-nowrap"
              ),
              rx.el.th(
                "Costo", class_name=f"{TABLE_STYLES['header_cell']} text-right whitespace-nowrap"
              ),
              rx.el.th(
                "Total", class_name=f"{TABLE_STYLES['header_cell']} text-right whitespace-nowrap"
              ),
              class_name=TABLE_STYLES["header"],
            )
          ),
          rx.el.tbody(
            rx.foreach(
              State.petty_cash_movements,
              lambda item: rx.el.tr(
                rx.el.td(item["timestamp"], class_name="py-3 px-4 whitespace-nowrap"),
                rx.el.td(item["user"], class_name="py-3 px-4 whitespace-nowrap"),
                rx.el.td(item["notes"], class_name="py-3 px-4"),
                rx.el.td(item["formatted_quantity"], class_name="py-3 px-4 text-right whitespace-nowrap"),
                rx.el.td(item["unit"], class_name="py-3 px-4 whitespace-nowrap"),
                rx.el.td(
                  State.currency_symbol,
                  item["formatted_cost"],
                  class_name="py-3 px-4 text-right whitespace-nowrap",
                ),
                rx.el.td(
                  State.currency_symbol,
                  item["formatted_amount"],
                  class_name="py-3 px-4 text-right font-semibold text-red-600 whitespace-nowrap",
                ),
                class_name="border-b hover:bg-slate-50",
              ),
            )
          ),
          class_name="min-w-full",
        ),
        class_name="overflow-x-auto w-full border rounded-lg",
      ),
      rx.cond(
        State.petty_cash_movements.length() > 0,
        pagination_controls(
          current_page=State.petty_cash_current_page,
          total_pages=State.petty_cash_total_pages,
          on_prev=State.prev_petty_cash_page,
          on_next=State.next_petty_cash_page,
        ),
        rx.fragment(),
      ),
      rx.cond(
        State.petty_cash_movements.length() == 0,
        rx.el.p(
          "No hay movimientos registrados.",
          class_name="text-center text-slate-500 py-8",
        ),
        rx.fragment(),
      ),
      class_name="bg-white p-4 sm:p-6 rounded-xl border border-slate-200 shadow-sm w-full",
    ),
    petty_cash_modal(),
    class_name="space-y-4 w-full",
  )

def cashbox_page() -> rx.Component:
  content = rx.el.div(
    page_title(
      "GESTION DE CAJA",
      "Controla la apertura, cierre y movimientos de dinero en caja.",
    ),
    rx.cond(
      State.router.page.params["tab"] == "movimientos",
      petty_cash_view(),
      rx.el.div(
        cashbox_opening_card(),
        card_container(
          cashbox_payments_header(),
          rx.el.div(
            cashbox_filters(),
            class_name="bg-slate-50/80 border border-slate-200/80 rounded-xl p-4 sm:p-5",
          ),
          rx.el.div(
            rx.el.table(
              rx.el.thead(
                rx.el.tr(
                  rx.el.th("Fecha y Hora", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th("Usuario", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th("Metodo", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th(
                    "Total", class_name=f"{TABLE_STYLES['header_cell']} text-right"
                  ),
                  rx.el.th("Detalle", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th(
                    "Acciones", class_name=f"{TABLE_STYLES['header_cell']} text-center"
                  ),
                  class_name=TABLE_STYLES["header"],
                )
              ),
              rx.el.tbody(
                rx.foreach(State.filtered_cashbox_sales, sale_row),
              ),
              class_name="min-w-full",
            ),
            class_name="overflow-x-auto rounded-xl border border-slate-200 bg-white",
          ),
          rx.cond(
            State.filtered_cashbox_sales.length() == 0,
            rx.el.p(
              "Aun no hay ventas registradas.",
              class_name="text-center text-slate-500 py-8",
            ),
            pagination_controls(
              current_page=State.cashbox_current_page,
              total_pages=State.cashbox_total_pages,
              on_prev=State.prev_cashbox_page,
              on_next=State.next_cashbox_page,
            ),
          ),
          style="highlight",
          gap="gap-5",
        ),
        cashbox_logs_section(),
        delete_sale_modal(),
        close_cashbox_modal(),
        cashbox_log_modal(),
        class_name="flex flex-col gap-6",
      ),
    ),
    on_mount=State.refresh_cashbox_data,
    class_name="flex flex-col gap-6 p-4 sm:p-6 w-full",
  )
  return permission_guard(
    has_permission=State.can_view_cashbox,
    content=content,
    redirect_message="Acceso denegado a Gestión de Caja",
  )
