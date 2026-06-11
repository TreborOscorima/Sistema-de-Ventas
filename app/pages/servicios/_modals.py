import reflex as rx

from app.state import State
from app.components.ui import (
  BADGE_STYLES,
  BUTTON_STYLES,
  INPUT_STYLES,
  TYPOGRAPHY,
)


def payment_method_selector_compact() -> rx.Component:
  """
  Selector de método de pago compacto para servicios/reservas.
  Reutiliza State.enabled_payment_methods y State.select_payment_method.
  """
  return rx.el.div(
    rx.el.label("Método de pago", class_name=TYPOGRAPHY["label"]),
    rx.el.div(
      rx.foreach(
        State.enabled_payment_methods,
        lambda method: rx.el.button(
          rx.cond(
            method["kind"] == "cash",
            rx.icon("banknote", class_name="h-3 w-3"),
            rx.cond(
              (method["kind"] == "debit") | (method["kind"] == "credit") | (method["kind"] == "card"),
              rx.icon("credit-card", class_name="h-3 w-3"),
              rx.cond(
                (method["kind"] == "yape") | (method["kind"] == "plin") | (method["kind"] == "wallet"),
                rx.icon("smartphone", class_name="h-3 w-3"),
                rx.cond(
                  method["kind"] == "transfer",
                  rx.icon("arrow-left-right", class_name="h-3 w-3"),
                  rx.icon("layers", class_name="h-3 w-3"),
                ),
              ),
            ),
          ),
          rx.el.span(method["name"], class_name="text-xs font-medium"),
          on_click=lambda _, mid=method["id"]: State.select_payment_method(mid),
          class_name=rx.cond(
            State.payment_method == method["name"],
            "flex items-center gap-1 px-2 py-1.5 rounded-md bg-indigo-600 text-white text-xs",
            "flex items-center gap-1 px-2 py-1.5 rounded-md border bg-white text-slate-700 hover:bg-slate-50 text-xs",
          ),
        ),
      ),
      class_name="flex flex-wrap gap-1.5",
    ),
    class_name="flex flex-col gap-1.5",
  )


def reservation_status_badge(reservation: rx.Var[dict]) -> rx.Component:
  return rx.cond(
    reservation["status"] == "pagado",
    rx.el.span(
      "Pagado",
      class_name=BADGE_STYLES["success"],
    ),
    rx.cond(
      reservation["status"] == "cancelado",
      rx.el.span(
        "Cancelado",
        class_name=BADGE_STYLES["danger"],
      ),
      rx.cond(
        reservation["status"] == "eliminado",
        rx.el.span(
          "Eliminado",
          class_name=BADGE_STYLES["neutral"],
        ),
        rx.el.span(
          "Pendiente",
          class_name=BADGE_STYLES["warning"],
        ),
      ),
    ),
  )


def reservation_modal() -> rx.Component:
  return rx.cond(
    State.reservation_modal_open,
    rx.el.div(
      rx.el.div(
        on_click=State.close_reservation_modal,
        class_name="fixed inset-0 bg-black/40 backdrop-blur-sm modal-overlay",
      ),
      rx.el.div(
        rx.el.div(
          rx.el.h3(
            rx.cond(
              State.reservation_modal_mode == "view",
              "Detalle de reserva",
              "Nueva reserva",
            ),
            class_name=TYPOGRAPHY["section_title"],
          ),
          rx.el.p(
            rx.cond(
              State.reservation_modal_mode == "view",
              "Consulta el estado y acciones de la reserva seleccionada.",
              "Completa los datos para crear la reserva en el horario elegido.",
            ),
            class_name=TYPOGRAPHY["body_secondary"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.divider(color="slate-100"),
        rx.el.div(
          rx.el.span("Horario", class_name="text-xs uppercase text-slate-500"),
          rx.el.span(
            State.reservation_form["date"],
            " ",
            State.reservation_form["start_time"],
            " - ",
            State.reservation_form["end_time"],
            class_name="text-sm font-semibold text-slate-900",
          ),
          rx.el.span(
            rx.cond(
              State.field_rental_sport == "futbol",
              "Campos de Futbol",
              "Campos de Voley",
            ),
            class_name="text-xs text-slate-600",
          ),
          class_name="rounded-md border border-dashed border-slate-200 p-3 bg-slate-50 flex flex-col gap-1",
        ),
        rx.cond(
          State.reservation_modal_mode == "view",
          rx.cond(
            State.modal_reservation == None,
            rx.el.p("Reserva no encontrada.", class_name="text-sm text-slate-600"),
            rx.el.div(
              rx.el.div(
                rx.el.div(
                  rx.el.span("Cliente", class_name="text-xs uppercase text-slate-500"),
                  rx.el.span(
                    State.modal_reservation["client_name"],
                    class_name="text-sm font-semibold text-slate-900",
                  ),
                  class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                  rx.el.span("Telefono", class_name="text-xs uppercase text-slate-500"),
                  rx.el.span(
                    State.modal_reservation["phone"],
                    class_name="text-sm font-semibold text-slate-900",
                  ),
                  class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                  rx.el.span("Campo", class_name="text-xs uppercase text-slate-500"),
                  rx.el.span(
                    State.modal_reservation["field_name"],
                    class_name="text-sm font-semibold text-slate-900",
                  ),
                  class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                  rx.el.span("Estado", class_name="text-xs uppercase text-slate-500"),
                  reservation_status_badge(State.modal_reservation),
                  class_name="flex flex-col gap-1",
                ),
                class_name="grid grid-cols-1 sm:grid-cols-2 gap-3",
              ),
              rx.el.div(
                rx.el.div(
                  rx.el.span("Total", class_name="text-xs uppercase text-slate-500"),
                  rx.el.span(
                    State.currency_symbol,
                    State.modal_reservation["total_amount"].to_string(),
                    class_name="text-sm font-semibold text-slate-900",
                  ),
                  class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                  rx.el.span("Pagado", class_name="text-xs uppercase text-slate-500"),
                  rx.el.span(
                    State.currency_symbol,
                    State.modal_reservation["paid_amount"].to_string(),
                    class_name="text-sm font-semibold text-slate-900",
                  ),
                  class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                  rx.el.span("Saldo", class_name="text-xs uppercase text-slate-500"),
                  rx.el.span(
                    State.currency_symbol,
                    State.selected_reservation_balance.to_string(),
                    class_name="text-sm font-semibold text-slate-900",
                  ),
                  class_name="flex flex-col gap-1",
                ),
                class_name="grid grid-cols-1 sm:grid-cols-3 gap-3",
              ),
              rx.el.div(
                rx.fragment(),
                class_name="grid grid-cols-1 sm:grid-cols-3 gap-2",
              ),
              class_name="flex flex-col gap-4",
            ),
          ),
          rx.el.div(
            rx.el.div(
              rx.el.label("Cliente", class_name=TYPOGRAPHY["label"]),
              rx.el.input(
                placeholder="Nombre completo",
                default_value=State.reservation_form["client_name"],
                on_blur=lambda value: State.update_reservation_form("client_name", value),
                class_name=INPUT_STYLES["default"],
                debounce_timeout=600,
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.label("Telefono", class_name=TYPOGRAPHY["label"]),
              rx.el.input(
                placeholder="999 999 999",
                default_value=State.reservation_form["phone"],
                on_blur=lambda value: State.update_reservation_form("phone", value),
                class_name=INPUT_STYLES["default"],
                debounce_timeout=600,
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.label("Deporte", class_name=TYPOGRAPHY["label"]),
              rx.el.select(
                rx.el.option("Selecciona un deporte", value=""),
                rx.foreach(
                  State.field_prices_for_current_sport,
                  lambda price: rx.el.option(
                    price["sport"] + " - " + price["name"],
                    value=price["id"],
                  ),
                ),
                default_value=State.reservation_form["selected_price_id"],
                on_change=State.select_reservation_field_price,
                class_name=INPUT_STYLES["default"],
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.label("Campo", class_name=TYPOGRAPHY["label"]),
              rx.el.input(
                placeholder="Cancha / Campo",
                key=State.reservation_form["selected_price_id"] + "-" + State.reservation_form["field_name"],
                default_value=State.reservation_form["field_name"],
                on_blur=lambda value: State.update_reservation_form("field_name", value),
                class_name=INPUT_STYLES["default"],
                debounce_timeout=600,
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.label("Adelanto", class_name=TYPOGRAPHY["label"]),
              rx.el.input(
                type="number",
                step="0.01",
                default_value=State.reservation_form["advance_amount"],
                on_blur=lambda value: State.update_reservation_form("advance_amount", value),
                class_name=INPUT_STYLES["default"],
              ),
              class_name="flex flex-col gap-1",
            ),
            payment_method_selector_compact(),
            rx.el.div(
              rx.el.label("Monto total", class_name=TYPOGRAPHY["label"]),
              rx.el.input(
                type="number",
                step="0.01",
                key=State.reservation_form["selected_price_id"] + "-" + State.reservation_form["start_time"] + "-" + State.reservation_form["end_time"] + "-" + State.reservation_form["total_amount"],
                default_value=State.reservation_form["total_amount"],
                on_blur=lambda value: State.update_reservation_form("total_amount", value),
                class_name=INPUT_STYLES["default"],
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.label("Estado", class_name=TYPOGRAPHY["label"]),
              rx.el.select(
                rx.el.option("Pendiente", value="pendiente"),
                rx.el.option("Pagado", value="pagado"),
                default_value=State.reservation_form["status"],
                on_change=lambda value: State.update_reservation_form("status", value),
                class_name=INPUT_STYLES["default"],
              ),
              class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 gap-3",
          ),
        ),
        rx.divider(color="slate-100"),
        rx.el.div(
          rx.cond(
            State.reservation_modal_mode == "view",
            rx.el.button(
              rx.icon("printer", class_name="h-4 w-4"),
              "Imprimir Comprobante",
              on_click=lambda: State.print_reservation_receipt(State.reservation_modal_reservation_id),
              class_name=f"{BUTTON_STYLES['secondary']} min-h-[42px]",
            ),
            rx.fragment(),
          ),
          rx.el.button(
            "Cerrar",
            on_click=State.close_reservation_modal,
            class_name=f"{BUTTON_STYLES['secondary']} min-h-[42px]",
          ),
          rx.cond(
            State.reservation_modal_mode == "new",
            rx.el.button(
              rx.icon("check", class_name="h-4 w-4"),
              "Guardar reserva",
              on_click=State.create_field_reservation,
              disabled=rx.cond(
                (State.reservation_form["client_name"] == "")
                | (State.reservation_form["date"] == "")
                | (State.reservation_form["start_time"] == "")
                | (State.reservation_form["end_time"] == "")
                | (State.reservation_form["total_amount"] == "0")
                | (State.reservation_form["total_amount"] == "")
                | (State.schedule_selected_date == ""),
                True,
                False,
              ),
              class_name=rx.cond(
                (State.reservation_form["client_name"] == "")
                | (State.reservation_form["date"] == "")
                | (State.reservation_form["start_time"] == "")
                | (State.reservation_form["end_time"] == "")
                | (State.reservation_form["total_amount"] == "0")
                | (State.reservation_form["total_amount"] == "")
                | (State.schedule_selected_date == ""),
                f"{BUTTON_STYLES['disabled']} min-h-[42px]",
                f"{BUTTON_STYLES['primary']} min-h-[42px]",
              ),
            ),
            rx.fragment(),
          ),
          class_name="flex justify-end gap-3 pt-4",
        ),
        class_name="relative z-10 w-full max-w-3xl rounded-xl bg-white p-4 sm:p-6 shadow-xl max-h-[90vh] overflow-y-auto",
      ),
      class_name="fixed inset-0 z-50 flex items-center justify-center px-4",
    ),
    rx.fragment(),
  )


def reservation_form_card() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.h3("Registro de reservas", class_name=TYPOGRAPHY["section_title"]),
      rx.el.p(
        "Captura los datos del cliente, horario y adelantos opcionales.",
        class_name="text-sm text-slate-600",
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.div(
        rx.el.label("Nombre completo", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          placeholder="Ej: Juan Perez",
          default_value=State.reservation_form["client_name"],
          on_blur=lambda value: State.update_reservation_form("client_name", value),
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("DNI (opcional)", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          placeholder="Documento",
          default_value=State.reservation_form["dni"],
          on_blur=lambda value: State.update_reservation_form("dni", value),
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Telefono (opcional)", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          placeholder="999 999 999",
          default_value=State.reservation_form["phone"],
          on_blur=lambda value: State.update_reservation_form("phone", value),
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Campo", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          placeholder="Campo A / Cancha 1",
          key=State.reservation_form["selected_price_id"] + "-" + State.reservation_form["field_name"],
          default_value=State.reservation_form["field_name"],
          on_blur=lambda value: State.update_reservation_form("field_name", value),
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Fecha", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          type="date",
          default_value=State.reservation_form["date"],
          on_blur=lambda value: State.update_reservation_form("date", value),
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Hora inicio", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          type="time",
          default_value=State.reservation_form["start_time"],
          on_blur=lambda value: State.update_reservation_form("start_time", value),
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Hora fin", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          type="time",
          default_value=State.reservation_form["end_time"],
          on_blur=lambda value: State.update_reservation_form("end_time", value),
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Adelanto", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          type="number",
          step="0.01",
          default_value=State.reservation_form["advance_amount"],
          on_blur=lambda value: State.update_reservation_form("advance_amount", value),
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      payment_method_selector_compact(),
      rx.el.div(
        rx.el.label("Monto total", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          type="number",
          step="0.01",
          key=State.reservation_form["selected_price_id"] + "-" + State.reservation_form["start_time"] + "-" + State.reservation_form["end_time"] + "-" + State.reservation_form["total_amount"],
          default_value=State.reservation_form["total_amount"],
          on_blur=lambda value: State.update_reservation_form("total_amount", value),
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Estado", class_name=TYPOGRAPHY["label"]),
        rx.el.select(
          rx.el.option("Pendiente", value="pendiente"),
          rx.el.option("Pagado", value="pagado"),
          default_value=State.reservation_form["status"],
          on_change=lambda value: State.update_reservation_form("status", value),
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      class_name="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4",
    ),
    rx.el.div(
      rx.el.button(
        rx.icon("check", class_name="h-4 w-4"),
        "Guardar reserva",
        on_click=State.create_field_reservation,
        class_name=f"{BUTTON_STYLES['primary']} min-h-[44px]",
      ),
      class_name="flex justify-end",
    ),
    class_name=f"flex flex-col gap-4",
  )


def reservation_delete_modal() -> rx.Component:
  return rx.radix.primitives.dialog.root(
    rx.radix.primitives.dialog.portal(
      rx.radix.primitives.dialog.overlay(
        class_name="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 modal-overlay"
      ),
      rx.radix.primitives.dialog.content(
        rx.el.div(
          rx.el.h3("Eliminar reserva", class_name=TYPOGRAPHY["section_title"]),
          rx.el.p(
            "Esta accion marcara la reserva como Eliminada y liberara el horario. Ingresa un sustento obligatorio.",
            class_name="text-sm text-slate-600",
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.divider(color="slate-100"),
        rx.cond(
          State.reservation_selected_for_delete == None,
          rx.el.p("Reserva no encontrada.", class_name="text-sm text-slate-600"),
          rx.el.div(
            rx.el.div(
              rx.el.span("Cliente", class_name="text-xs uppercase text-slate-500"),
              rx.el.span(
                State.reservation_selected_for_delete["client_name"],
                class_name="text-sm font-semibold text-slate-900",
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.span("Horario", class_name="text-xs uppercase text-slate-500"),
              rx.el.span(
                State.reservation_selected_for_delete["start_datetime"],
                " - ",
                State.reservation_selected_for_delete["end_datetime"],
                class_name="text-sm font-semibold text-slate-900",
              ),
              class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-slate-50 border border-slate-100 rounded-md p-3",
          ),
        ),
        rx.el.div(
          rx.el.label("Sustento de eliminacion", class_name=TYPOGRAPHY["label"]),
          rx.el.textarea(
            placeholder="Ej: Registro duplicado o datos incorrectos",
            default_value=State.reservation_delete_reason,
            on_blur=State.set_reservation_delete_reason,
            auto_focus=True,
            class_name="w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-md placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 min-h-[100px]",
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.divider(color="slate-100"),
        rx.el.div(
          rx.el.button(
            "Cancelar",
            on_click=lambda _: State.close_reservation_delete_modal(),
            class_name=f"{BUTTON_STYLES['secondary']} min-h-[40px]",
          ),
          rx.el.button(
            rx.icon("trash-2", class_name="h-4 w-4"),
            "Eliminar",
            on_click=lambda _: State.confirm_reservation_delete(),
            disabled=State.reservation_delete_button_disabled,
            class_name=rx.cond(
              State.reservation_delete_button_disabled,
              f"{BUTTON_STYLES['disabled']} min-h-[40px]",
              f"{BUTTON_STYLES['danger']} min-h-[40px]",
            ),
          ),
          class_name="flex justify-end gap-3",
        ),
        class_name=(
          "bg-white rounded-xl border border-slate-200 shadow-sm p-5 w-full max-w-xl space-y-4 "
          "data-[state=open]:animate-in data-[state=closed]:animate-out "
          "data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0 "
          "data-[state=open]:zoom-in-95 data-[state=closed]:zoom-out-95 "
          "data-[state=open]:slide-in-from-top-4 data-[state=closed]:slide-out-to-top-4 "
          "fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-xl -translate-x-1/2 -translate-y-1/2 focus:outline-none"
        ),
      ),
    ),
    open=State.reservation_delete_modal_open,
    on_open_change=State.set_reservation_delete_modal_open,
  )
