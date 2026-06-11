import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  CARD_STYLES,
  INPUT_STYLES,
  SELECT_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  pagination_controls,
)
from ._modals import reservation_status_badge, payment_method_selector_compact


def reservation_mobile_card(reservation: rx.Var[dict]) -> rx.Component:
  """Tarjeta compacta de reserva para vista movil."""
  return rx.el.div(
    # Header: cliente + estado
    rx.el.div(
      rx.el.span(reservation["client_name"], class_name=TYPOGRAPHY["card_title"]),
      reservation_status_badge(reservation),
      class_name="flex items-center justify-between gap-2",
    ),
    # Campo + Horario
    rx.el.div(
      rx.el.div(
        rx.el.span("Campo", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(reservation["field_name"], class_name=TYPOGRAPHY["body"]),
        class_name="flex flex-col",
      ),
      rx.el.div(
        rx.el.span("Horario", class_name=TYPOGRAPHY["caption"]),
        rx.el.div(
          rx.el.span(reservation["start_datetime"], class_name=TYPOGRAPHY["mono_value"]),
          rx.el.span(reservation["end_datetime"], class_name=TYPOGRAPHY["caption"]),
          class_name="flex flex-col",
        ),
        class_name="flex flex-col",
      ),
      class_name="grid grid-cols-2 gap-3",
    ),
    # Montos
    rx.el.div(
      rx.el.div(
        rx.el.span("Total", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(
          State.currency_symbol, reservation["total_amount"].to_string(),
          class_name=TYPOGRAPHY["mono_value"],
        ),
        class_name="flex flex-col",
      ),
      rx.el.div(
        rx.el.span("Pagado", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(
          State.currency_symbol, reservation["paid_amount"].to_string(),
          class_name=TYPOGRAPHY["mono_value"],
        ),
        class_name="flex flex-col",
      ),
      rx.el.div(
        rx.el.span("Saldo", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(
          State.currency_symbol,
          (reservation["total_amount"] - reservation["advance_amount"]).to_string(),
          class_name=TYPOGRAPHY["mono_value"],
        ),
        class_name="flex flex-col",
      ),
      class_name="grid grid-cols-3 gap-3",
    ),
    # Sustento de eliminacion (si aplica)
    rx.cond(
      reservation["status"] == "eliminado",
      rx.el.span(
        "Sustento: ",
        reservation.get("delete_reason", ""),
        class_name=TYPOGRAPHY["caption"],
      ),
      rx.fragment(),
    ),
    # Acciones
    rx.el.div(
      rx.el.button(
        rx.icon("trash-2", class_name="h-4 w-4"),
        on_click=lambda _, rid=reservation["id"]: State.start_reservation_delete(rid),
        disabled=reservation["status"] != "pendiente",
        title="Eliminar reserva",
        aria_label="Eliminar reserva",
        class_name=rx.cond(
          reservation["status"] != "pendiente",
          "p-2 rounded-full bg-slate-200 text-slate-500 cursor-not-allowed",
          BUTTON_STYLES["icon_danger"],
        ),
      ),
      rx.el.button(
        rx.icon("eye", class_name="h-4 w-4"),
        rx.el.span("Ver", class_name="text-sm font-semibold"),
        on_click=lambda _, rid=reservation["id"]: State.view_reservation_details(rid),
        class_name=BUTTON_STYLES["link_primary"],
      ),
      rx.el.button(
        rx.icon("printer", class_name="h-4 w-4"),
        rx.el.span("Imprimir", class_name="text-sm font-semibold"),
        on_click=lambda _, rid=reservation["id"]: State.print_reservation_receipt(rid),
        class_name=BUTTON_STYLES["secondary_sm"],
      ),
      rx.el.button(
        rx.icon("credit-card", class_name="h-4 w-4"),
        rx.el.span("Pagar", class_name="text-sm font-semibold"),
        on_click=lambda _, rid=reservation["id"]: State.go_to_sale_for_reservation(rid),
        disabled=rx.cond(
          reservation["status"] == "eliminado",
          True,
          rx.cond(
            reservation["status"] == "cancelado",
            True,
            rx.cond(reservation["status"] == "pagado", True, False),
          ),
        ),
        class_name=rx.cond(
          reservation["status"] == "eliminado",
          BUTTON_STYLES["disabled_sm"],
          rx.cond(
            reservation["status"] == "cancelado",
            BUTTON_STYLES["disabled_sm"],
            rx.cond(
              reservation["status"] == "pagado",
              BUTTON_STYLES["disabled_sm"],
              BUTTON_STYLES["success_sm"],
            ),
          ),
        ),
      ),
      class_name="flex flex-wrap gap-2",
    ),
    class_name=f"{CARD_STYLES['compact']} flex flex-col gap-3",
  )


def reservation_row(reservation: rx.Var[dict]) -> rx.Component:
  return rx.el.tr(
    rx.el.td(reservation["client_name"], class_name="py-3 px-4"),
    rx.el.td(reservation["field_name"], class_name="py-3 px-4 hidden md:table-cell"),
    rx.el.td(
      rx.el.div(
        rx.el.span(reservation["start_datetime"], class_name="text-sm font-medium"),
        rx.el.span(reservation["end_datetime"], class_name="text-xs text-slate-500"),
        class_name="flex flex-col",
      ),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      rx.el.div(
        rx.el.span(State.currency_symbol, reservation["total_amount"].to_string(), class_name="font-semibold"),
        rx.el.span(
          "Pagado ",
          State.currency_symbol,
          reservation["paid_amount"].to_string(),
          class_name="text-xs text-slate-600",
        ),
        class_name="flex flex-col gap-1",
      ),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      rx.el.div(
        reservation_status_badge(reservation),
        rx.cond(
          reservation["status"] == "eliminado",
          rx.el.span(
            "Sustento: ",
            reservation.get("delete_reason", ""),
            class_name="text-xs text-slate-500",
          ),
          rx.fragment(),
        ),
        class_name="flex flex-col gap-1",
      ),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      reservation["created_by"],
      class_name="py-3 px-4 text-sm text-slate-700 hidden lg:table-cell",
    ),
    rx.el.td(
      rx.el.div(
        rx.el.button(
          rx.icon("trash-2", class_name="h-4 w-4"),
          on_click=lambda _, rid=reservation["id"]: State.start_reservation_delete(rid),
          disabled=reservation["status"] != "pendiente",
          title="Eliminar reserva",
          aria_label="Eliminar reserva",
          class_name=rx.cond(
            reservation["status"] != "pendiente",
            "p-2 rounded-full bg-slate-200 text-slate-500 cursor-not-allowed",
            BUTTON_STYLES["icon_danger"],
          ),
        ),
        rx.el.button(
          rx.icon("eye", class_name="h-4 w-4"),
          rx.el.span("Ver", class_name="text-sm font-semibold"),
          on_click=lambda _, rid=reservation["id"]: State.view_reservation_details(rid),
          class_name=BUTTON_STYLES["link_primary"],
        ),
        rx.el.button(
          rx.icon("printer", class_name="h-4 w-4"),
          rx.el.span("Imprimir", class_name="text-sm font-semibold"),
          on_click=lambda _, rid=reservation["id"]: State.print_reservation_receipt(rid),
          class_name=BUTTON_STYLES["secondary_sm"],
        ),
        rx.el.button(
          rx.icon("credit-card", class_name="h-4 w-4"),
          rx.el.span("Pagar", class_name="text-sm font-semibold"),
          on_click=lambda _, rid=reservation["id"]: State.go_to_sale_for_reservation(rid),
          disabled=rx.cond(
            reservation["status"] == "eliminado",
            True,
            rx.cond(
              reservation["status"] == "cancelado",
              True,
              rx.cond(reservation["status"] == "pagado", True, False),
            ),
          ),
          class_name=rx.cond(
            reservation["status"] == "eliminado",
            BUTTON_STYLES["disabled_sm"],
            rx.cond(
              reservation["status"] == "cancelado",
              BUTTON_STYLES["disabled_sm"],
              rx.cond(
                reservation["status"] == "pagado",
                BUTTON_STYLES["disabled_sm"],
                BUTTON_STYLES["success_sm"],
              ),
            ),
          ),
        ),
        class_name="flex flex-col sm:flex-row sm:flex-wrap gap-2",
      ),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      rx.el.span(
        State.currency_symbol,
        (reservation["total_amount"] - reservation["advance_amount"]).to_string(),
        class_name="font-semibold",
      ),
      class_name="py-3 px-4 text-right hidden md:table-cell",
    ),
    class_name="border-b",
  )


def reservations_table() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.h3("RESERVAS REGISTRADAS", class_name=TYPOGRAPHY["section_title"]),
      rx.el.p(
        "Revisa el estado de cada reserva por deporte.",
        class_name="text-sm text-slate-600",
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.div(
        rx.debounce_input(
          rx.input(
            placeholder="Buscar por cliente, campo o horario...",
            default_value=State.reservation_staged_search,
            on_change=State.set_reservation_staged_search,
            class_name=INPUT_STYLES["default"],
          ),
          debounce_timeout=600,
        ),
        rx.el.select(
          rx.el.option("Todos", value="todos"),
          rx.el.option("Pendiente", value="pendiente"),
          rx.el.option("Pagado", value="pagado"),
          rx.el.option("Cancelado", value="cancelado"),
          rx.el.option("Eliminado", value="eliminado"),
          default_value=State.reservation_staged_status,
          on_change=State.set_reservation_staged_status,
          class_name=SELECT_STYLES["default"],
        ),
        rx.el.input(
          type="date",
          default_value=State.reservation_staged_start_date,
          on_blur=State.set_reservation_staged_start_date,
          class_name=SELECT_STYLES["default"],
        ),
        rx.el.input(
          type="date",
          default_value=State.reservation_staged_end_date,
          on_blur=State.set_reservation_staged_end_date,
          class_name=SELECT_STYLES["default"],
        ),
        class_name="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2",
      ),
      rx.el.div(
        rx.el.button(
          rx.icon("search", class_name="h-4 w-4"),
          "Buscar",
          on_click=State.apply_reservation_filters,
          class_name=BUTTON_STYLES["primary"],
        ),
        rx.el.button(
          rx.icon("rotate-ccw", class_name="h-4 w-4"),
          "Limpiar",
          on_click=State.reset_reservation_filters,
          class_name=BUTTON_STYLES["secondary"],
        ),
        rx.el.button(
          rx.icon("download", class_name="h-4 w-4"),
          "Exportar",
          on_click=State.export_reservations_excel,
          class_name=BUTTON_STYLES["success"],
        ),
        class_name="flex flex-col sm:flex-row sm:flex-wrap gap-2 xl:justify-end",
      ),
      class_name="flex flex-col gap-2",
    ),
    # Mobile card view
    rx.el.div(
      rx.foreach(State.paginated_reservations, reservation_mobile_card),
      class_name="flex flex-col gap-3 md:hidden",
    ),
    # Desktop table view
    rx.el.div(
      rx.el.table(
        rx.el.thead(
          rx.el.tr(
            rx.el.th("Cliente", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-[13%]"),
            rx.el.th("Campo", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-[12%] hidden md:table-cell"),
            rx.el.th("Horario", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-[16%]"),
            rx.el.th("Monto", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-[10%]"),
            rx.el.th("Estado", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-[9%]"),
            rx.el.th("Usuario", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-[8%] hidden lg:table-cell"),
            rx.el.th("Acciones", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-[32%]"),
            rx.el.th(
              "Saldo", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-[8%] text-right hidden md:table-cell"
            ),
            class_name=TABLE_STYLES["header"],
          )
        ),
        rx.el.tbody(rx.foreach(State.paginated_reservations, reservation_row)),
        class_name="w-full min-w-[800px]",
      ),
      class_name="hidden md:block w-full overflow-x-auto rounded-lg border border-slate-200",
    ),
    rx.cond(
      State.service_reservations_for_sport.length() == 0,
      rx.el.p(
        "Aun no hay reservas en este deporte.",
        class_name="text-center text-slate-500 py-4",
      ),
      pagination_controls(
        current_page=State.reservation_current_page,
        total_pages=State.reservation_total_pages,
        on_prev=State.prev_reservation_page,
        on_next=State.next_reservation_page,
      ),
    ),
    class_name=f"{CARD_STYLES['default']} flex flex-col gap-3",
  )


def payments_card() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.h3("Pagos y adelantos", class_name=TYPOGRAPHY["section_title"]),
      rx.el.p(
        "Registra pagos parciales, saldo pendiente y genera comprobante.",
        class_name="text-sm text-slate-600",
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.div(
        rx.el.label("Reserva", class_name=TYPOGRAPHY["label"]),
        rx.el.select(
          rx.el.option("Selecciona una reserva", value=""),
          rx.foreach(
            State.active_reservation_options,
            lambda option: rx.el.option(option["label"], value=option["id"]),
          ),
          default_value=State.reservation_payment_id,
          on_change=State.select_reservation_for_payment,
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Monto a registrar", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          type="number",
          step="0.01",
          placeholder="Ej: 80.00",
          default_value=State.reservation_payment_amount,
          on_blur=State.set_reservation_payment_amount,
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      class_name="grid grid-cols-1 lg:grid-cols-2 gap-4",
    ),
    # Selector de método de pago para pagos de reservas
    rx.cond(
      State.reservation_payment_id != "",
      payment_method_selector_compact(),
      rx.fragment(),
    ),
    rx.el.div(
      rx.el.button(
        rx.icon("wallet", class_name="h-4 w-4"),
        "Registrar pago",
        on_click=State.apply_reservation_payment,
        class_name=f"{BUTTON_STYLES['success']} min-h-[44px]",
      ),
      rx.el.button(
        rx.icon("badge-check", class_name="h-4 w-4"),
        "Pagar saldo",
        on_click=State.pay_reservation_balance,
        class_name=f"{BUTTON_STYLES['link_primary']} min-h-[44px]",
      ),
      class_name="flex flex-col sm:flex-row gap-3",
    ),
    rx.cond(
      State.reservation_selected_for_payment == None,
      rx.el.div(
        rx.el.p("Selecciona una reserva para ver el saldo pendiente.", class_name="text-sm text-slate-600"),
        class_name="rounded-lg border border-dashed border-slate-200 p-3",
      ),
      rx.el.div(
        rx.el.div(
          rx.el.span("Estado", class_name="text-xs uppercase text-slate-500"),
          reservation_status_badge(State.reservation_selected_for_payment),
          class_name="flex items-center gap-2",
        ),
        rx.el.div(
          rx.el.span("Saldo pendiente", class_name="text-xs uppercase text-slate-500"),
          rx.el.span(
            State.currency_symbol,
            State.selected_reservation_balance.to_string(),
            class_name="text-lg font-semibold text-slate-900",
          ),
          class_name="flex items-center justify-between",
        ),
        rx.el.div(
          rx.el.span("Horario", class_name="text-xs uppercase text-slate-500"),
          rx.el.span(
            State.reservation_selected_for_payment["start_datetime"],
            " - ",
            State.reservation_selected_for_payment["end_datetime"],
            class_name="text-sm font-medium text-slate-800",
          ),
          class_name="flex items-center justify-between",
        ),
        class_name="rounded-lg border border-emerald-100 bg-emerald-50 p-3 flex flex-col gap-2",
      ),
    ),
    class_name=f"{CARD_STYLES['default']} flex flex-col gap-4",
  )


def cancellation_card() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.h3("Cancelacion de reservas", class_name=TYPOGRAPHY["section_title"]),
      rx.el.p(
        "Selecciona la reserva, registra el motivo y marca el estado como cancelado.",
        class_name="text-sm text-slate-600",
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.label("Reserva a cancelar", class_name=TYPOGRAPHY["label"]),
      rx.el.select(
        rx.el.option("Selecciona una reserva", value=""),
        rx.foreach(
          State.active_reservation_options,
          lambda option: rx.el.option(option["label"], value=option["id"]),
        ),
        default_value=State.reservation_cancel_selection,
        on_change=State.select_reservation_to_cancel,
        class_name=INPUT_STYLES["default"],
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.label("Motivo de cancelacion", class_name=TYPOGRAPHY["label"]),
      rx.el.textarea(
        placeholder="Describe el motivo",
        default_value=State.reservation_cancel_reason,
        on_blur=State.set_reservation_cancel_reason,
        class_name="w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-md placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 min-h-[100px]",
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.button(
      rx.icon("ban", class_name="h-4 w-4"),
      "Cancelar reserva",
      on_click=State.cancel_reservation,
      class_name=f"{BUTTON_STYLES['danger']} min-h-[44px]",
    ),
    class_name=f"{CARD_STYLES['default']} flex flex-col gap-3",
  )
