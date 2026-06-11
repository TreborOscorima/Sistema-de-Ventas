import reflex as rx

from app.state import State
from app.components.ui import (
  BADGE_STYLES,
  BUTTON_STYLES,
  CARD_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  date_range_filter,
  section_header,
  select_filter,
)


def log_type_badge(entry: rx.Var[dict]) -> rx.Component:
  return rx.el.span(
    rx.cond(
      entry["type"] == "reserva",
      "Reserva creada",
      rx.cond(
        entry["type"] == "cancelacion",
        "Cancelacion",
        rx.cond(
          entry["type"] == "eliminacion",
          "Eliminacion",
          rx.cond(entry["type"] == "adelanto", "Adelanto", "Pago"),
        ),
      ),
    ),
    class_name=BADGE_STYLES["neutral"],
  )


def admin_log_mobile_card(entry: rx.Var[dict]) -> rx.Component:
  """Tarjeta compacta de log administrativo para vista movil."""
  return rx.el.div(
    # Header: tipo + estado
    rx.el.div(
      log_type_badge(entry),
      rx.el.span(entry["status"].capitalize(), class_name=TYPOGRAPHY["body"]),
      class_name="flex items-center justify-between gap-2",
    ),
    # Fecha + Cliente
    rx.el.div(
      rx.el.div(
        rx.el.span("Fecha", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(entry["timestamp"], class_name=TYPOGRAPHY["mono_value"]),
        class_name="flex flex-col",
      ),
      rx.el.div(
        rx.el.span("Cliente", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(entry["client_name"], class_name=TYPOGRAPHY["body"]),
        class_name="flex flex-col",
      ),
      class_name="grid grid-cols-2 gap-3",
    ),
    # Campo + Monto
    rx.el.div(
      rx.el.div(
        rx.el.span("Campo", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(entry["field_name"], class_name=TYPOGRAPHY["body"]),
        class_name="flex flex-col",
      ),
      rx.el.div(
        rx.el.span("Monto", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(
          State.currency_symbol, entry["amount"].to_string(),
          class_name=TYPOGRAPHY["mono_value"],
        ),
        class_name="flex flex-col",
      ),
      class_name="grid grid-cols-2 gap-3",
    ),
    # Notas (si existen)
    rx.cond(
      entry["notes"] != "",
      rx.el.div(
        rx.el.span("Notas", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(entry["notes"], class_name=TYPOGRAPHY["body"]),
        class_name="flex flex-col",
      ),
      rx.fragment(),
    ),
    class_name=f"{CARD_STYLES['compact']} flex flex-col gap-2",
  )


def admin_log_row(entry: rx.Var[dict]) -> rx.Component:
  return rx.el.tr(
    rx.el.td(entry["timestamp"], class_name="py-3 px-4"),
    rx.el.td(log_type_badge(entry), class_name="py-3 px-4"),
    rx.el.td(entry["client_name"], class_name="py-3 px-4"),
    rx.el.td(entry["field_name"], class_name="py-3 px-4 hidden md:table-cell"),
    rx.el.td(
      rx.el.span(
        State.currency_symbol,
        entry["amount"].to_string(),
        class_name="font-semibold",
      ),
      class_name="py-3 px-4 text-right",
    ),
    rx.el.td(
      rx.el.span(entry["status"].capitalize(), class_name="text-sm font-medium"),
      class_name="py-3 px-4",
    ),
    rx.el.td(entry["notes"], class_name="py-3 px-4 text-sm text-slate-600 hidden md:table-cell"),
    class_name="border-b",
  )


def admin_log_filters() -> rx.Component:
  """Seccion de filtros para el log administrativo."""
  start_filter, end_filter = date_range_filter(
    start_value=State.service_log_filter_start_date,
    end_value=State.service_log_filter_end_date,
    on_start_change=State.set_service_log_filter_start_date,
    on_end_change=State.set_service_log_filter_end_date,
    start_label="Fecha inicio",
    end_label="Fecha fin",
  )

  return rx.el.div(
    start_filter,
    end_filter,
    select_filter(
      "Deporte",
      [("Todos", "todos"), ("Futbol", "futbol"), ("Voley", "voley")],
      State.service_log_filter_sport,
      State.set_service_log_filter_sport,
    ),
    select_filter(
      "Estado",
      [
        ("Todos", "todos"),
        ("Pendiente", "pendiente"),
        ("Pagado", "pagado"),
        ("Cancelado", "cancelado"),
        ("Eliminado", "eliminado"),
      ],
      State.service_log_filter_status,
      State.set_service_log_filter_status,
    ),
    rx.el.button(
      rx.icon("eraser", class_name="h-4 w-4"),
      "Limpiar filtros",
      on_click=State.reset_service_log_filters,
      class_name=BUTTON_STYLES["secondary"],
    ),
    class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end",
  )


def admin_log_table() -> rx.Component:
  """Tabla con entradas del log administrativo."""
  return rx.el.div(
    section_header(
      "Registro administrativo",
      "Movimientos de reservas, cancelaciones y pagos con filtros por fecha, deporte y estado.",
    ),
    admin_log_filters(),
    # Mobile card view
    rx.el.div(
      rx.foreach(State.filtered_service_admin_log, admin_log_mobile_card),
      class_name="flex flex-col gap-3 md:hidden",
    ),
    # Desktop table view
    rx.el.table(
      rx.el.thead(
        rx.el.tr(
          rx.el.th("Fecha y hora", scope="col", class_name=TABLE_STYLES["header_cell"]),
          rx.el.th("Movimiento", scope="col", class_name=TABLE_STYLES["header_cell"]),
          rx.el.th("Cliente", scope="col", class_name=TABLE_STYLES["header_cell"]),
          rx.el.th("Campo", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
          rx.el.th(
            "Monto", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right"
          ),
          rx.el.th("Estado", scope="col", class_name=TABLE_STYLES["header_cell"]),
          rx.el.th("Notas", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
          class_name=TABLE_STYLES["header"],
        )
      ),
      rx.el.tbody(rx.foreach(State.filtered_service_admin_log, admin_log_row)),
      class_name="hidden md:table min-w-full",
    ),
    rx.cond(
      State.filtered_service_admin_log.length() == 0,
      rx.el.p(
        "No hay movimientos para los filtros seleccionados.",
        class_name="text-center text-slate-500 py-4",
      ),
      rx.fragment(),
    ),
    class_name=f"{CARD_STYLES['default']} overflow-x-auto flex flex-col gap-4",
  )
