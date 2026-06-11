import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  CARD_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  pagination_controls,
)
from ._modals import petty_cash_modal


def _petty_cash_card(item: rx.Var) -> rx.Component:
  """Card de movimiento de caja chica para vista móvil."""
  return rx.el.div(
    # Header: fecha + total (rojo = gasto)
    rx.el.div(
      rx.el.span(item["timestamp"], class_name="text-xs text-slate-400 font-mono"),
      rx.el.span(
        "- ", State.currency_symbol, " ", item["formatted_amount"],
        class_name="text-base font-bold text-red-600 tabular-nums",
      ),
      class_name="flex items-center justify-between gap-2",
    ),
    # Body: motivo (principal)
    rx.el.p(
      item["notes"],
      class_name="text-sm text-slate-700 mt-2 leading-snug",
    ),
    # Footer: usuario + cantidad + unidad
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


def petty_cash_view() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.div(
        rx.el.div(
          rx.el.h2("MOVIMIENTOS DE CAJA CHICA", class_name=TYPOGRAPHY["section_title"]),
          rx.el.p("Gestión de gastos y salidas de efectivo.", class_name=TYPOGRAPHY["body_secondary"]),
          class_name="flex flex-col mb-4 lg:mb-0",
        ),
        rx.el.div(
          rx.el.div(
            rx.el.span("Saldo Actual", class_name=f"{TYPOGRAPHY['caption']} font-medium uppercase tracking-wider"),
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
      # Vista móvil: Cards (< md)
      rx.el.div(
        rx.foreach(State.petty_cash_movements, _petty_cash_card),
        class_name="flex flex-col gap-3 md:hidden",
      ),
      # Vista desktop: Tabla (md+)
      rx.el.div(
        rx.el.table(
          rx.el.thead(
            rx.el.tr(
              rx.el.th(
                "Fecha y Hora",
                scope="col", class_name=f"{TABLE_STYLES['header_cell']} whitespace-nowrap",
              ),
              rx.el.th(
                "Usuario", scope="col", class_name=f"{TABLE_STYLES['header_cell']} whitespace-nowrap hidden md:table-cell"
              ),
              rx.el.th(
                "Motivo", scope="col", class_name=TABLE_STYLES["header_cell"]
              ),
              rx.el.th(
                "Cant.", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right whitespace-nowrap hidden lg:table-cell"
              ),
              rx.el.th(
                "Unidad", scope="col", class_name=f"{TABLE_STYLES['header_cell']} whitespace-nowrap hidden lg:table-cell"
              ),
              rx.el.th(
                "Costo unit.", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right whitespace-nowrap hidden lg:table-cell"
              ),
              rx.el.th(
                "Total", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right whitespace-nowrap"
              ),
              class_name=TABLE_STYLES["header"],
            )
          ),
          rx.el.tbody(
            rx.foreach(
              State.petty_cash_movements,
              lambda item: rx.el.tr(
                rx.el.td(item["timestamp"], class_name="py-3 px-4 text-sm whitespace-nowrap text-slate-700"),
                rx.el.td(item["user"], class_name="py-3 px-4 text-sm whitespace-nowrap text-slate-600 hidden md:table-cell"),
                rx.el.td(item["notes"], class_name="py-3 px-4 text-sm text-slate-700"),
                rx.el.td(item["formatted_quantity"], class_name="py-3 px-4 text-sm text-right whitespace-nowrap hidden lg:table-cell"),
                rx.el.td(item["unit"], class_name="py-3 px-4 text-sm whitespace-nowrap hidden lg:table-cell text-slate-500"),
                rx.el.td(
                  State.currency_symbol,
                  item["formatted_cost"],
                  class_name="py-3 px-4 text-sm text-right whitespace-nowrap hidden lg:table-cell tabular-nums",
                ),
                rx.el.td(
                  State.currency_symbol,
                  item["formatted_amount"],
                  class_name="py-3 px-4 text-sm text-right font-semibold text-red-600 whitespace-nowrap tabular-nums",
                ),
                class_name="border-b hover:bg-slate-50 transition-colors",
              ),
            )
          ),
          class_name="min-w-full",
        ),
        class_name="hidden md:block overflow-x-auto w-full border rounded-lg",
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
      class_name=f"{CARD_STYLES['default']} w-full",
    ),
    petty_cash_modal(),
    class_name="space-y-4 w-full",
  )
