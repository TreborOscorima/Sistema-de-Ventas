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


_SPORTS_OPTIONS = [
  ("futbol",   "Fútbol"),
  ("voley",    "Vóley"),
  ("basquet",  "Básquet"),
  ("tenis",    "Tenis"),
  ("paddle",   "Paddle"),
  ("rugby",    "Rugby"),
  ("hockey",   "Hockey"),
  ("natacion", "Natación"),
]


def _sport_label(sport_var: rx.Var) -> rx.Component:
  return rx.match(
    sport_var,
    ("futbol",   "Fútbol"),
    ("voley",    "Vóley"),
    ("basquet",  "Básquet"),
    ("tenis",    "Tenis"),
    ("paddle",   "Paddle"),
    ("rugby",    "Rugby"),
    ("hockey",   "Hockey"),
    ("natacion", "Natación"),
    sport_var,
  )


def _price_form() -> rx.Component:
  """Formulario add/edit con contexto condicional."""
  is_edit = State.editing_field_price_id != ""
  select_sport = rx.el.select(
    *[
      rx.el.option(label, value=val)
      for val, label in _SPORTS_OPTIONS
    ],
    value=State.new_field_price_sport,
    on_change=State.set_new_field_price_sport,
    class_name=SELECT_STYLES["default"],
  )
  input_name = rx.el.input(
    placeholder="Nombre del campo (ej: Cancha 1)",
    default_value=State.new_field_price_name,
    on_blur=State.set_new_field_price_name,
    class_name=INPUT_STYLES["default"],
    debounce_timeout=400,
    key="fpname_" + State.editing_field_price_id,
  )
  input_price = rx.el.input(
    type="number",
    step="0.01",
    placeholder="Precio por hora",
    default_value=State.new_field_price_amount,
    on_blur=State.set_new_field_price_amount,
    class_name=INPUT_STYLES["default"],
    key="fpamt_" + State.editing_field_price_id,
  )
  btn_add = rx.el.button(
    rx.icon("plus", class_name="h-4 w-4"),
    "Agregar",
    on_click=State.add_field_price,
    class_name=BUTTON_STYLES["primary"],
  )
  btns_edit = rx.el.div(
    rx.el.button(
      rx.icon("refresh-ccw", class_name="h-4 w-4"),
      "Actualizar",
      on_click=State.update_field_price,
      class_name=BUTTON_STYLES["warning"],
    ),
    rx.el.button(
      rx.icon("x", class_name="h-4 w-4"),
      "Cancelar",
      on_click=State.cancel_edit_field_price,
      class_name=BUTTON_STYLES["secondary"],
    ),
    class_name="flex gap-2",
  )
  return rx.el.div(
    rx.el.div(
      rx.cond(
        is_edit,
        rx.el.span(
          rx.icon("pencil", class_name="h-3.5 w-3.5"),
          "Editando campo existente",
          class_name="flex items-center gap-1 text-xs font-semibold text-amber-700",
        ),
        rx.el.span(
          rx.icon("circle-plus", class_name="h-3.5 w-3.5"),
          "Nuevo precio de campo",
          class_name="flex items-center gap-1 text-xs font-semibold text-slate-500",
        ),
      ),
    ),
    rx.el.div(
      select_sport,
      input_name,
      input_price,
      rx.cond(is_edit, btns_edit, btn_add),
      class_name="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2 sm:gap-3 items-end",
    ),
    class_name=rx.cond(
      is_edit,
      "flex flex-col gap-3 bg-amber-50 border border-amber-200 p-4 rounded-xl shadow-sm",
      "flex flex-col gap-3 bg-white border border-slate-200 p-4 rounded-xl shadow-sm",
    ),
  )


def _price_group_card(group: rx.Var) -> rx.Component:
  """Card por deporte con tabla interna de campos."""
  def _price_row(price: rx.Var) -> rx.Component:
    return rx.el.tr(
      rx.el.td(price["name"], class_name="py-2 px-3 text-sm text-slate-800"),
      rx.el.td(
        rx.el.input(
          type="number",
          step="0.01",
          default_value=price["price"],
          key=price["id"] + "_" + price["price"],
          on_blur=lambda value, pid=price["id"]: State.update_field_price_amount(pid, value),
          disabled=~State.can_manage_config,
          class_name=f"{INPUT_STYLES['default']} w-28 disabled:bg-slate-100 disabled:text-slate-500",
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
              class_name=BUTTON_STYLES["icon_warning"],
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
          rx.el.span("Solo lectura", class_name="text-xs text-slate-400"),
        ),
        class_name="py-2 px-3 text-center",
      ),
      class_name="border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors",
    )

  return rx.el.div(
    rx.el.div(
      rx.icon("calendar-check", class_name="h-4 w-4 text-indigo-500"),
      rx.el.span(
        _sport_label(group["sport"]),
        class_name="text-sm font-bold text-slate-700 uppercase tracking-wide",
      ),
      class_name="flex items-center gap-2 px-4 py-3 border-b border-slate-200 bg-slate-50",
    ),
    rx.el.table(
      rx.el.thead(
        rx.el.tr(
          rx.el.th("Campo", scope="col", class_name=TABLE_STYLES["header_cell"]),
          rx.el.th("Precio (por hora)", scope="col", class_name=TABLE_STYLES["header_cell"]),
          rx.el.th("Acciones", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center"),
          class_name=TABLE_STYLES["header"],
        )
      ),
      rx.el.tbody(
        rx.foreach(group["items"], _price_row),
      ),
      class_name="min-w-full",
    ),
    class_name=f"{CARD_STYLES['default']} overflow-x-auto p-0",
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
      _price_form(),
      rx.el.div(
        rx.el.p(
          "Solo usuarios con permiso de Configuración Global pueden modificar precios.",
          class_name="text-sm text-amber-700",
        ),
        class_name="rounded-md border border-amber-200 bg-amber-50 px-3 py-2",
      ),
    ),
    rx.cond(
      State.field_prices_by_sport.length() > 0,
      rx.el.div(
        rx.foreach(State.field_prices_by_sport, _price_group_card),
        class_name="flex flex-col gap-4",
      ),
      rx.el.p(
        "No hay precios configurados. Agrega uno con el formulario de arriba.",
        class_name="text-sm text-slate-400 text-center py-6",
      ),
    ),
    class_name="flex flex-col gap-4",
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
      campo_tab(),
    ),
    class_name="w-full flex flex-col gap-4",
  )
  return permission_guard(
    has_permission=State.can_view_servicios,
    content=content,
    redirect_message="Acceso denegado a Servicios",
  )
