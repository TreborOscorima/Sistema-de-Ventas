import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  card_container,
  date_range_filter,
  filter_action_buttons,
  pagination_controls,
  section_header,
  status_badge,
)


def _cashbox_log_filters() -> rx.Component:
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


def _cashbox_log_card(log: rx.Var[dict]) -> rx.Component:
  """Card de apertura/cierre para vista móvil."""
  return rx.el.div(
    # Header: evento + fecha
    rx.el.div(
      rx.cond(
        log["action"] == "apertura",
        status_badge("Apertura", status_colors={"apertura": ("bg-emerald-100", "text-emerald-700")}),
        status_badge("Cierre", status_colors={"cierre": ("bg-orange-100", "text-orange-700")}),
      ),
      rx.el.span(log["timestamp"], class_name="text-xs text-slate-400 font-mono"),
      class_name="flex items-center justify-between gap-2",
    ),
    # Body: usuario + montos
    rx.el.div(
      rx.el.div(
        rx.el.span("Usuario", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(log["user"], class_name="text-sm font-medium text-slate-800 truncate"),
        class_name="flex flex-col gap-0.5 min-w-0",
      ),
      rx.el.div(
        rx.el.span("Apertura", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(
          State.currency_symbol, " ", log["opening_amount"],
          class_name="text-sm font-semibold tabular-nums text-slate-700",
        ),
        class_name="flex flex-col gap-0.5",
      ),
      rx.el.div(
        rx.el.span("Cierre", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(
          State.currency_symbol, " ", log["closing_total"],
          class_name="text-sm font-semibold tabular-nums text-slate-900",
        ),
        class_name="flex flex-col gap-0.5",
      ),
      class_name="grid grid-cols-3 gap-3 mt-3",
    ),
    # Footer: acciones
    rx.el.div(
      rx.el.button(
        rx.icon("eye", class_name="h-4 w-4"),
        "Ver detalle",
        on_click=State.show_cashbox_log(log["id"]),
        class_name=BUTTON_STYLES["link_primary"],
      ),
      rx.cond(
        log["action"] == "cierre",
        rx.el.div(
          rx.el.button(
            rx.icon("file-text", class_name="h-4 w-4"),
            on_click=State.export_cashbox_close_pdf_for_log(log["id"]),
            title="Descargar PDF",
            class_name=BUTTON_STYLES["icon_success"],
          ),
          rx.el.button(
            rx.icon("printer", class_name="h-4 w-4"),
            on_click=State.print_cashbox_close_summary_for_log(log["id"]),
            title="Reimprimir",
            class_name=BUTTON_STYLES["icon_primary"],
          ),
          class_name="flex gap-2",
        ),
        rx.fragment(),
      ),
      class_name="flex items-center justify-between mt-3 pt-3 border-t border-slate-100",
    ),
    class_name="bg-white border border-slate-200 rounded-xl p-4 shadow-sm",
  )


def cashbox_log_row(log: rx.Var[dict]) -> rx.Component:
  return rx.el.tr(
    rx.el.td(log["timestamp"], class_name="py-3 px-4 text-sm whitespace-nowrap"),
    rx.el.td(
      rx.cond(
        log["action"] == "apertura",
        status_badge("Apertura", status_colors={"apertura": ("bg-emerald-100", "text-emerald-700")}),
        status_badge("Cierre", status_colors={"cierre": ("bg-orange-100", "text-orange-700")}),
      ),
      class_name="py-3 px-4",
    ),
    rx.el.td(log["user"], class_name="py-3 px-4 text-sm hidden md:table-cell"),
    rx.el.td(
      State.currency_symbol,
      log["opening_amount"],
      class_name="py-3 px-4 text-sm text-right font-medium hidden md:table-cell tabular-nums",
    ),
    rx.el.td(
      State.currency_symbol,
      log["closing_total"],
      class_name="py-3 px-4 text-sm text-right font-semibold tabular-nums",
    ),
    rx.el.td(
      rx.el.div(
        rx.el.button(
          rx.icon("eye", class_name="h-4 w-4"),
          on_click=lambda _, log_id=log["id"]: State.show_cashbox_log(log_id),
          title="Visualizar",
          aria_label="Visualizar",
          class_name=BUTTON_STYLES["icon_primary"],
        ),
        rx.cond(
          log["action"] == "cierre",
          rx.el.button(
            rx.icon("file-text", class_name="h-4 w-4"),
            on_click=lambda _, log_id=log["id"]: State.export_cashbox_close_pdf_for_log(log_id),
            title="Descargar PDF",
            aria_label="Descargar PDF",
            class_name=BUTTON_STYLES["icon_success"],
          ),
          rx.fragment(),
        ),
        rx.cond(
          log["action"] == "cierre",
          rx.el.button(
            rx.icon("printer", class_name="h-4 w-4"),
            on_click=lambda _, log_id=log["id"]: State.print_cashbox_close_summary_for_log(log_id),
            title="Reimprimir resumen",
            aria_label="Reimprimir resumen",
            class_name=BUTTON_STYLES["icon_primary"],
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
    _cashbox_log_filters(),
    # Vista móvil: Cards (< md)
    rx.el.div(
      rx.foreach(State.filtered_cashbox_logs, _cashbox_log_card),
      class_name="flex flex-col gap-3 md:hidden",
    ),
    # Vista desktop: Tabla (md+)
    rx.el.div(
      rx.el.table(
        rx.el.thead(
          rx.el.tr(
            rx.el.th("Fecha y Hora", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Evento", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Usuario", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
            rx.el.th(
              "Monto Apertura", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right hidden md:table-cell"
            ),
            rx.el.th(
              "Monto Cierre", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right"
            ),
            rx.el.th(
              "Acciones", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center"
            ),
            class_name=TABLE_STYLES["header"],
          )
        ),
        rx.el.tbody(rx.foreach(State.filtered_cashbox_logs, cashbox_log_row)),
        class_name="min-w-full",
      ),
      class_name="hidden md:block overflow-x-auto rounded-lg border border-slate-200",
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
