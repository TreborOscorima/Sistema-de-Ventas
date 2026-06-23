import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  CARD_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  pagination_controls,
)
from ._modals import petty_cash_modal, petty_cash_edit_modal


def _tipo_badge(movement_type: rx.Var) -> rx.Component:
  """Indicador visual de tipo (Egreso / Ingreso)."""
  return rx.cond(
    movement_type == "ingreso",
    rx.el.span(
      rx.icon("circle-arrow-up", class_name="w-3 h-3"),
      "Ingreso",
      class_name="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700",
    ),
    rx.el.span(
      rx.icon("circle-arrow-down", class_name="w-3 h-3"),
      "Egreso",
      class_name="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700",
    ),
  )


def _petty_cash_card(item: rx.Var) -> rx.Component:
  """Card de movimiento de caja chica para vista móvil."""
  return rx.el.div(
    rx.el.div(
      rx.el.span(item["timestamp"], class_name="text-xs text-slate-400 font-mono"),
      rx.el.div(
        rx.cond(
          item["movement_type"] == "ingreso",
          rx.el.span(
            "+ ", State.currency_symbol, " ", item["formatted_amount"],
            class_name="text-base font-bold text-green-600 tabular-nums",
          ),
          rx.el.span(
            "- ", State.currency_symbol, " ", item["formatted_amount"],
            class_name="text-base font-bold text-red-600 tabular-nums",
          ),
        ),
        rx.el.button(
          rx.icon("pencil", class_name="w-3.5 h-3.5"),
          on_click=State.open_petty_cash_edit_modal(item["id"]),
          class_name="p-1.5 rounded-md text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors",
          title="Editar movimiento",
        ),
        class_name="flex items-center gap-2",
      ),
      class_name="flex items-center justify-between gap-2",
    ),
    rx.el.div(
      _tipo_badge(item["movement_type"]),
      rx.cond(
        item["category"] != "",
        rx.el.span(
          item["category"],
          class_name="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600",
        ),
        rx.fragment(),
      ),
      class_name="flex items-center gap-2 mt-2",
    ),
    rx.el.p(
      item["notes"],
      class_name="text-sm text-slate-700 mt-1 leading-snug",
    ),
    rx.el.div(
      rx.el.div(
        rx.el.span("Usuario", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(item["user"], class_name="text-xs font-medium text-slate-700 truncate"),
        class_name="flex flex-col gap-0.5 min-w-0",
      ),
      rx.el.div(
        rx.el.span("Cant.", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(item["formatted_quantity"], class_name="text-xs font-medium text-slate-700"),
        class_name="flex flex-col gap-0.5",
      ),
      rx.el.div(
        rx.el.span("Unidad", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(item["unit"], class_name="text-xs font-medium text-slate-700"),
        class_name="flex flex-col gap-0.5",
      ),
      class_name="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-100",
    ),
    class_name="bg-white border border-slate-200 rounded-xl p-4 shadow-sm",
  )


def _filter_bar() -> rx.Component:
  """Barra de filtros: tipo + rango de fechas + limpiar."""
  return rx.el.div(
    # Tipo
    rx.el.div(
      rx.el.label("Tipo", class_name=TYPOGRAPHY["caption"]),
      rx.el.select(
        rx.el.option("Todos", value=""),
        rx.el.option("Egreso", value="egreso"),
        rx.el.option("Ingreso", value="ingreso"),
        value=State.petty_cash_filter_type,
        on_change=State.set_petty_cash_filter_type,
        class_name="text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300 text-slate-700 h-9",
      ),
      class_name="flex flex-col gap-1",
    ),
    # Desde
    rx.el.div(
      rx.el.label("Desde", class_name=TYPOGRAPHY["caption"]),
      rx.el.input(
        type="date",
        value=State.petty_cash_filter_date_from,
        on_change=State.set_petty_cash_filter_date_from,
        class_name="text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300 text-slate-700 h-9",
      ),
      class_name="flex flex-col gap-1",
    ),
    # Hasta
    rx.el.div(
      rx.el.label("Hasta", class_name=TYPOGRAPHY["caption"]),
      rx.el.input(
        type="date",
        value=State.petty_cash_filter_date_to,
        on_change=State.set_petty_cash_filter_date_to,
        class_name="text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300 text-slate-700 h-9",
      ),
      class_name="flex flex-col gap-1",
    ),
    # Limpiar filtros (visible solo si hay alguno activo)
    rx.cond(
      State.petty_cash_filter_active,
      rx.el.button(
        rx.icon("x", class_name="w-3.5 h-3.5"),
        "Limpiar",
        on_click=State.clear_petty_cash_filters,
        class_name="self-end inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors h-9",
      ),
      rx.fragment(),
    ),
    class_name="flex flex-wrap items-end gap-3 px-4 pb-4 pt-2 border-b border-slate-100",
  )


def petty_cash_view() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      # ── Header ────────────────────────────────────────────────────────
      rx.el.div(
        rx.el.div(
          rx.el.h2("MOVIMIENTOS DE CAJA CHICA", class_name=TYPOGRAPHY["section_title"]),
          rx.el.p("Gestión de gastos e ingresos de caja chica.", class_name=TYPOGRAPHY["body_secondary"]),
          class_name="flex flex-col mb-4 lg:mb-0",
        ),
        rx.el.div(
          rx.el.div(
            rx.el.span("Saldo Apertura", class_name=f"{TYPOGRAPHY['caption']} font-medium uppercase tracking-wider"),
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
        class_name="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 p-4",
      ),
      # ── Filtros ────────────────────────────────────────────────────────
      _filter_bar(),
      # ── Vista móvil: Cards (< md) ──────────────────────────────────────
      rx.el.div(
        rx.foreach(State.petty_cash_movements, _petty_cash_card),
        class_name="flex flex-col gap-3 md:hidden p-4",
      ),
      # ── Vista desktop: Tabla (md+) ─────────────────────────────────────
      rx.el.div(
        rx.el.table(
          rx.el.thead(
            rx.el.tr(
              rx.el.th("Fecha y Hora",  scope="col", class_name=f"{TABLE_STYLES['header_cell']} whitespace-nowrap"),
              rx.el.th("Tipo",          scope="col", class_name=f"{TABLE_STYLES['header_cell']} whitespace-nowrap hidden sm:table-cell"),
              rx.el.th("Categoría",     scope="col", class_name=f"{TABLE_STYLES['header_cell']} whitespace-nowrap hidden lg:table-cell"),
              rx.el.th("Usuario",       scope="col", class_name=f"{TABLE_STYLES['header_cell']} whitespace-nowrap hidden md:table-cell"),
              rx.el.th("Motivo",        scope="col", class_name=TABLE_STYLES["header_cell"]),
              rx.el.th("Cant.",         scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right whitespace-nowrap hidden lg:table-cell"),
              rx.el.th("Unidad",        scope="col", class_name=f"{TABLE_STYLES['header_cell']} whitespace-nowrap hidden lg:table-cell"),
              rx.el.th("Costo unit.",   scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right whitespace-nowrap hidden lg:table-cell"),
              rx.el.th("Total",         scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right whitespace-nowrap"),
              rx.el.th("",             scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-10"),
              class_name=TABLE_STYLES["header"],
            )
          ),
          rx.el.tbody(
            rx.foreach(
              State.petty_cash_movements,
              lambda item: rx.el.tr(
                rx.el.td(item["timestamp"], class_name="py-3 px-4 text-sm whitespace-nowrap text-slate-700"),
                rx.el.td(_tipo_badge(item["movement_type"]), class_name="py-3 px-4 hidden sm:table-cell"),
                rx.el.td(
                  rx.cond(
                    item["category"] != "",
                    rx.el.span(
                      item["category"],
                      class_name="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600",
                    ),
                    rx.el.span("—", class_name="text-slate-300 text-sm"),
                  ),
                  class_name="py-3 px-4 hidden lg:table-cell",
                ),
                rx.el.td(item["user"], class_name="py-3 px-4 text-sm whitespace-nowrap text-slate-600 hidden md:table-cell"),
                rx.el.td(item["notes"], class_name="py-3 px-4 text-sm text-slate-700 max-w-xs truncate"),
                rx.el.td(item["formatted_quantity"], class_name="py-3 px-4 text-sm text-right whitespace-nowrap hidden lg:table-cell"),
                rx.el.td(item["unit"], class_name="py-3 px-4 text-sm whitespace-nowrap hidden lg:table-cell text-slate-500"),
                rx.el.td(
                  State.currency_symbol, item["formatted_cost"],
                  class_name="py-3 px-4 text-sm text-right whitespace-nowrap hidden lg:table-cell tabular-nums",
                ),
                rx.el.td(
                  rx.cond(
                    item["movement_type"] == "ingreso",
                    rx.el.span(
                      "+ ", State.currency_symbol, item["formatted_amount"],
                      class_name="font-semibold text-green-600 tabular-nums",
                    ),
                    rx.el.span(
                      "- ", State.currency_symbol, item["formatted_amount"],
                      class_name="font-semibold text-red-600 tabular-nums",
                    ),
                  ),
                  class_name="py-3 px-4 text-sm text-right whitespace-nowrap",
                ),
                rx.el.td(
                  rx.el.button(
                    rx.icon("pencil", class_name="w-4 h-4"),
                    on_click=State.open_petty_cash_edit_modal(item["id"]),
                    class_name="p-1.5 rounded-md text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors",
                    title="Editar",
                  ),
                  class_name="py-2 px-3 text-center",
                ),
                class_name="border-b hover:bg-slate-50 transition-colors",
              ),
            )
          ),
          class_name="min-w-full",
        ),
        class_name="hidden md:block overflow-x-auto w-full border-t",
      ),
      rx.cond(
        State.petty_cash_movements.length() > 0,
        rx.el.div(
          pagination_controls(
            current_page=State.petty_cash_current_page,
            total_pages=State.petty_cash_total_pages,
            on_prev=State.prev_petty_cash_page,
            on_next=State.next_petty_cash_page,
          ),
          class_name="px-4 py-3 border-t border-slate-100",
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
      class_name=f"{CARD_STYLES['default']} w-full p-0 overflow-hidden",
    ),
    petty_cash_modal(),
    petty_cash_edit_modal(),
    class_name="space-y-4 w-full",
  )
