import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  CARD_STYLES,
  INPUT_STYLES,
  SELECT_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  page_title,
  permission_guard,
)
from ._schedule import sport_selector, mini_calendar_sidebar, schedule_planner
from ._modals import reservation_delete_modal, reservation_modal
from ._reservations import reservations_table


def campo_tab() -> rx.Component:
  return rx.el.div(
    sport_selector(),
    rx.flex(
      rx.box(
        mini_calendar_sidebar(),
        class_name="hidden lg:block w-72 shrink-0 sticky top-4",
      ),
      rx.el.div(
        schedule_planner(),
        class_name="flex-1 w-full",
      ),
      align="start",
      class_name="flex-col lg:flex-row gap-6 items-start w-full",
    ),
    reservations_table(),
    reservation_delete_modal(),
    reservation_modal(),
    class_name="flex flex-col gap-4",
  )


def field_prices_tab() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.h3("PRECIOS DE CAMPO", class_name=TYPOGRAPHY["section_title"]),
      rx.el.p(
        "Configura las tarifas por deporte y nombre de campo para usarlas directamente al registrar reservas.",
        class_name="text-sm text-slate-600",
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.cond(
      State.can_manage_config,
      rx.el.div(
        rx.el.input(
          placeholder="Deporte (ej: Futbol, Voley)",
          default_value=State.new_field_price_sport,
          on_blur=State.set_new_field_price_sport,
          class_name=SELECT_STYLES["default"],
          debounce_timeout=600,
        ),
        rx.el.input(
          placeholder="Nombre del campo (ej: Futbol 5)",
          default_value=State.new_field_price_name,
          on_blur=State.set_new_field_price_name,
          class_name=SELECT_STYLES["default"],
          debounce_timeout=600,
        ),
        rx.el.input(
          type="number",
          step="0.01",
          placeholder="Precio por hora",
          default_value=State.new_field_price_amount,
          on_blur=State.set_new_field_price_amount,
          class_name=SELECT_STYLES["default"],
        ),
        rx.el.button(
          rx.icon("plus", class_name="h-4 w-4"),
          "Agregar",
          on_click=State.add_field_price,
          class_name=BUTTON_STYLES["primary"],
        ),
        rx.el.button(
          rx.icon("refresh-ccw", class_name="h-4 w-4"),
          "Actualizar",
          on_click=State.update_field_price,
          is_disabled=rx.cond(State.editing_field_price_id == "", True, False),
          class_name=rx.cond(
            State.editing_field_price_id == "",
            BUTTON_STYLES["disabled"],
            BUTTON_STYLES["warning"],
          ),
        ),
        class_name="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-2 sm:gap-3 items-end bg-white p-3.5 sm:p-4 rounded-xl shadow-sm border border-slate-200",
      ),
      rx.el.div(
        rx.el.p(
          "Solo usuarios con permiso de Configuracion Global pueden modificar precios.",
          class_name="text-sm text-amber-700",
        ),
        class_name="rounded-md border border-amber-200 bg-amber-50 px-3 py-2",
      ),
    ),
    rx.cond(
      State.editing_field_price_id != "",
      rx.el.div(
        "Editando un precio existente. Ajusta los campos y presiona Actualizar.",
        class_name="text-sm text-amber-700 bg-amber-50 border border-amber-100 px-3 py-2 rounded-md",
      ),
      rx.fragment(),
    ),
    # Mobile card view for field prices
    rx.el.div(
      rx.foreach(
        State.field_prices,
        lambda price: rx.el.div(
          rx.el.div(
            rx.el.span(price["sport"], class_name=TYPOGRAPHY["card_title"]),
            rx.el.span(price["name"], class_name=TYPOGRAPHY["body"]),
            class_name="flex items-center justify-between gap-2",
          ),
          rx.el.div(
            rx.el.span("Precio/hora", class_name=TYPOGRAPHY["caption"]),
            rx.el.span(
              price["price"].to_string(),
              class_name=TYPOGRAPHY["mono_value"],
            ),
            class_name="flex items-center justify-between",
          ),
          rx.cond(
            State.can_manage_config,
            rx.el.div(
              rx.el.button(
                rx.icon("pencil", class_name="h-4 w-4"),
                rx.el.span("Editar", class_name="text-sm font-semibold"),
                on_click=lambda _, pid=price["id"]: State.edit_field_price(pid),
                class_name=BUTTON_STYLES["link_primary"],
              ),
              rx.el.button(
                rx.icon("trash-2", class_name="h-4 w-4"),
                rx.el.span("Eliminar", class_name="text-sm font-semibold"),
                on_click=lambda _, pid=price["id"]: State.remove_field_price(pid),
                class_name=BUTTON_STYLES["link_danger"],
              ),
              class_name="flex flex-wrap gap-2",
            ),
            rx.el.span("Solo lectura", class_name=TYPOGRAPHY["caption"]),
          ),
          class_name=f"{CARD_STYLES['compact']} flex flex-col gap-2",
        ),
      ),
      class_name="flex flex-col gap-3 md:hidden",
    ),
    # Desktop table view for field prices
    rx.el.div(
      rx.el.table(
        rx.el.thead(
          rx.el.tr(
            rx.el.th("Deporte", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Campo", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Precio (por hora)", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th(
              "Acciones",
              scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center",
            ),
            class_name=TABLE_STYLES["header"],
          )
        ),
        rx.el.tbody(
          rx.foreach(
            State.field_prices,
            lambda price: rx.el.tr(
              rx.el.td(price["sport"], class_name="py-2 px-3"),
              rx.el.td(price["name"], class_name="py-2 px-3"),
              rx.el.td(
                rx.el.input(
                  type="number",
                  step="0.01",
                  default_value=price["price"].to_string(),
                  on_blur=lambda value, pid=price["id"]: State.update_field_price_amount(
                    pid, value
                  ),
                  disabled=~State.can_manage_config,
                  class_name=f"{INPUT_STYLES['default']} sm:w-36 disabled:bg-slate-100 disabled:text-slate-500",
                ),
                class_name="py-2 px-3",
              ),
              rx.el.td(
                rx.cond(
                  State.can_manage_config,
                  rx.el.div(
                    rx.el.button(
                      rx.icon("pencil", class_name="h-4 w-4"),
                      on_click=lambda _, pid=price["id"]: State.edit_field_price(pid),
                      title="Editar",
                      aria_label="Editar",
                      class_name=BUTTON_STYLES["icon_primary"],
                    ),
                    rx.el.button(
                      rx.icon("trash-2", class_name="h-4 w-4"),
                      on_click=lambda _, pid=price["id"]: State.remove_field_price(pid),
                      title="Eliminar",
                      aria_label="Eliminar",
                      class_name=BUTTON_STYLES["icon_danger"],
                    ),
                    class_name="flex items-center justify-center gap-2",
                  ),
                  rx.el.span("Solo lectura", class_name="text-xs text-slate-500"),
                ),
                class_name="py-2 px-3 text-center",
              ),
              class_name="border-b",
            ),
          )
        ),
        class_name="min-w-full",
      ),
      class_name=f"hidden md:block {CARD_STYLES['default']} overflow-x-auto",
    ),
    class_name="flex flex-col gap-4",
  )


def servicio_card(title: str, description: str) -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.span(title, class_name=TYPOGRAPHY["section_title"]),
      rx.el.p(description, class_name="text-sm text-slate-600"),
      class_name="flex flex-col gap-2",
    ),
    class_name=f"w-full {CARD_STYLES['default']}",
  )


def servicios_page() -> rx.Component:
  """Página principal del módulo de servicios y reservas."""
  content = rx.el.div(
    page_title(
      "SERVICIOS",
      "Gestiona reservas, precios de campo, adelantos, cancelaciones y registros administrativos.",
    ),
    rx.match(
      State.service_tab,
      ("campo", campo_tab()),
      ("precios_campo", field_prices_tab()),
      ("piscina", servicio_card("Alquiler de Piscina", "Registro y seguimiento de alquiler de piscina.")),
      campo_tab(),
    ),
    class_name="w-full flex flex-col gap-4",
  )
  return permission_guard(
    has_permission=State.can_view_servicios,
    content=content,
    redirect_message="Acceso denegado a Servicios",
  )
