import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  INPUT_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  card_container,
  page_title,
  pagination_controls,
  permission_guard,
)
from ._filters import cashbox_filters, cashbox_payments_header
from ._sales import _cashbox_sale_card, sale_row
from ._logs import cashbox_logs_section
from ._modals import delete_sale_modal, close_cashbox_modal, cashbox_log_modal
from ._petty_cash import petty_cash_view


def cashbox_opening_card() -> rx.Component:
  """Tarjeta de apertura de caja."""
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
            class_name=TYPOGRAPHY["label"],
          ),
          rx.el.p(
            rx.cond(
              State.cashbox_is_open,
              "La caja sigue abierta hasta que confirmes el cierre.",
              "Ingresa el monto inicial para comenzar la jornada.",
            ),
            class_name=TYPOGRAPHY["caption"],
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
              class_name=f"{TYPOGRAPHY['caption']} uppercase tracking-wide",
            ),
            rx.el.span(
              State.currency_symbol,
              State.cashbox_opening_amount_display,
              class_name=TYPOGRAPHY["mono_value"],
            ),
            class_name="flex flex-col gap-0.5 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-1.5",
          ),
          rx.el.div(
            rx.el.span(
              "Apertura",
              class_name=f"{TYPOGRAPHY['caption']} uppercase tracking-wide",
            ),
            rx.el.span(
              rx.cond(
                State.cashbox_opening_time == "",
                "Sin registro",
                State.cashbox_opening_time,
              ),
              class_name=TYPOGRAPHY["label"],
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
      rx.el.label("Caja inicial", class_name=TYPOGRAPHY["label"]),
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
        class_name=TYPOGRAPHY["caption"],
      ),
      class_name="flex flex-col gap-1",
    ),
    style="compact",
    gap="gap-1.5",
  )


def cashbox_page() -> rx.Component:
  content = rx.el.div(
    page_title(
      "GESTION DE CAJA",
      "Controla la apertura, cierre y movimientos de dinero en caja.",
    ),
    rx.cond(
      State.cash_tab == "movimientos",
      petty_cash_view(),
      rx.el.div(
        cashbox_opening_card(),
        card_container(
          cashbox_payments_header(),
          rx.el.div(
            cashbox_filters(),
            class_name="bg-slate-50/80 border border-slate-200/80 rounded-xl p-4 sm:p-5",
          ),
          # Vista móvil: Cards (visible en < md)
          rx.el.div(
            rx.foreach(State.filtered_cashbox_sales, _cashbox_sale_card),
            class_name="flex flex-col gap-3 md:hidden",
          ),
          # Vista desktop: Tabla (oculta en < md)
          rx.el.div(
            rx.el.table(
              rx.el.thead(
                rx.el.tr(
                  rx.el.th("Fecha y Hora", scope="col", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th("Usuario", scope="col", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th("Metodo", scope="col", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th(
                    "Total", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right"
                  ),
                  rx.el.th("Detalle", scope="col", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th(
                    "Acciones", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center"
                  ),
                  class_name=TABLE_STYLES["header"],
                )
              ),
              rx.el.tbody(
                rx.foreach(State.filtered_cashbox_sales, sale_row),
              ),
              class_name="min-w-full",
            ),
            class_name="hidden md:block overflow-x-auto rounded-xl border border-slate-200 bg-white",
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
    class_name="flex flex-col gap-6 p-4 sm:p-6 w-full",
  )
  return permission_guard(
    has_permission=State.can_view_cashbox,
    content=content,
    redirect_message="Acceso denegado a Gestión de Caja",
  )
