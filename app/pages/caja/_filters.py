import reflex as rx

from app.state import State
from app.components.ui import (
  BADGE_STYLES,
  CARD_STYLES,
  TYPOGRAPHY,
  date_range_filter,
  filter_action_buttons,
  toggle_switch,
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
    rx.el.label("Mostrar adelantos", class_name=TYPOGRAPHY["label_secondary"]),
    rx.el.div(
      toggle_switch(
        checked=State.show_cashbox_advances,
        on_change=State.set_show_cashbox_advances,
      ),
      rx.el.span(
        "Incluir adelantos en el listado",
        class_name=TYPOGRAPHY["body_secondary"],
      ),
      class_name="flex items-center gap-2",
    ),
    class_name=f"{CARD_STYLES['compact']} flex flex-col gap-2",
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


def cashbox_payments_header() -> rx.Component:
  """Encabezado con resumen de pagos de caja."""
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
      rx.el.h2("LISTADO DE PAGOS", class_name=TYPOGRAPHY["section_title"]),
      rx.el.p(
        "Ventas registradas según el rango seleccionado.",
        class_name=TYPOGRAPHY["body_secondary"],
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.span(
        rx.icon("calendar", class_name="h-3.5 w-3.5 text-slate-400"),
        date_range,
        class_name="inline-flex items-center gap-1.5 rounded-full bg-slate-100/70 px-3 py-1 text-xs font-semibold text-slate-600",
      ),
      rx.el.span(
        rx.cond(
          State.show_cashbox_advances,
          "Adelantos incluidos",
          "Adelantos ocultos",
        ),
        class_name=rx.cond(
          State.show_cashbox_advances,
          BADGE_STYLES["success"],
          BADGE_STYLES["warning"],
        ),
      ),
      rx.el.span(
        "Página ",
        State.cashbox_current_page.to_string(),
        " de ",
        State.cashbox_total_pages.to_string(),
        class_name="inline-flex items-center rounded-full bg-slate-100/70 px-3 py-1 text-xs font-semibold text-slate-600",
      ),
      class_name="flex flex-wrap items-center gap-2",
    ),
    class_name="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between",
  )
