import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  CARD_STYLES,
  INPUT_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  empty_state,
  modal_container,
  page_header,
  permission_guard,
)

# ── Helpers de segmento ──────────────────────────────────────────────────────

_SEGMENT_LABELS: dict[str, str] = {
  "nuevo": "Nuevo",
  "regular": "Regular",
  "vip": "VIP",
  "mayorista": "Mayorista",
}

_SEGMENT_CLASSES: dict[str, str] = {
  "nuevo":     "bg-blue-100 text-blue-700",
  "regular":   "bg-slate-100 text-slate-600",
  "vip":       "bg-amber-100 text-amber-700",
  "mayorista": "bg-purple-100 text-purple-700",
}


def _segment_badge(segment: rx.Var[str]) -> rx.Component:
  """Badge de color según segmento; oculto si está vacío."""
  def _badge(seg: str, label: str, cls: str) -> rx.Component:
    return rx.cond(
      segment == seg,
      rx.el.span(label, class_name=f"text-xs font-medium px-2 py-0.5 rounded-full {cls}"),
      rx.fragment(),
    )

  return rx.cond(
    (segment == None) | (segment == ""),
    rx.fragment(),
    rx.el.span(
      rx.cond(segment == "nuevo",     "Nuevo",     rx.cond(
      segment == "regular",  "Regular",   rx.cond(
      segment == "vip",      "VIP",        rx.cond(
      segment == "mayorista","Mayorista",  segment)))),
      class_name=rx.cond(
        segment == "nuevo",     "text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 text-blue-700",
        rx.cond(segment == "regular",  "text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600",
        rx.cond(segment == "vip",      "text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700",
        rx.cond(segment == "mayorista","text-xs font-medium px-2 py-0.5 rounded-full bg-purple-100 text-purple-700",
                                       "text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-500")))),
    ),
  )


# ── Tabla desktop ────────────────────────────────────────────────────────────

def client_row(client: rx.Var[dict]) -> rx.Component:
  return rx.el.tr(
    rx.el.td(
      rx.el.div(
        client["name"],
        _segment_badge(client["segment"]),
        class_name="flex items-center gap-2",
      ),
      class_name="py-3 px-4 font-medium text-slate-900",
    ),
    rx.el.td(client["dni"], class_name="py-3 px-4"),
    rx.el.td(
      rx.cond(
        (client["phone"] == None) | (client["phone"] == ""),
        rx.el.span("-", class_name="text-slate-400"),
        client["phone"],
      ),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      rx.cond(
        (client["address"] == None) | (client["address"] == ""),
        rx.el.span("-", class_name="text-slate-400"),
        client["address"],
      ),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      State.currency_symbol,
      client["credit_available"].to_string(),
      class_name="py-3 px-4 text-right font-semibold text-emerald-700",
    ),
    rx.el.td(
      rx.el.div(
        rx.el.button(
          rx.icon("history", class_name="h-4 w-4"),
          on_click=lambda _, c=client: State.open_historial(c),
          class_name=BUTTON_STYLES["icon_primary"],
          title="Ver historial de ventas",
          aria_label="Ver historial",
        ),
        rx.el.button(
          rx.icon("pencil", class_name="h-4 w-4"),
          on_click=lambda _, c=client: State.open_modal(c),
          class_name=BUTTON_STYLES["icon_primary"],
          title="Editar",
          aria_label="Editar",
        ),
        rx.el.button(
          rx.icon("trash-2", class_name="h-4 w-4"),
          on_click=lambda _, c_id=client["id"]: State.delete_client(c_id),
          disabled=State.is_loading,
          loading=State.is_loading,
          class_name=BUTTON_STYLES["icon_danger"],
          title="Eliminar",
          aria_label="Eliminar",
        ),
        class_name="flex items-center justify-center gap-2",
      ),
      class_name="py-3 px-4 text-center",
    ),
    class_name="border-b hover:bg-slate-50 transition-colors",
  )


# ── Card móvil ───────────────────────────────────────────────────────────────

def _client_card(client: rx.Var) -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.div(
        rx.el.span(client["name"], class_name="font-medium text-slate-900 text-sm"),
        _segment_badge(client["segment"]),
        class_name="flex items-center gap-2 flex-wrap",
      ),
      class_name="flex items-center justify-between gap-2",
    ),
    rx.el.div(
      rx.el.div(
        rx.el.span(State.personal_id_label, class_name=TYPOGRAPHY["caption"]),
        rx.el.span(": "),
        rx.el.span(client["dni"], class_name="text-sm text-slate-800"),
        class_name="flex items-center gap-0.5",
      ),
      rx.el.div(
        rx.el.span("Tel: ", class_name=TYPOGRAPHY["caption"]),
        rx.cond(
          (client["phone"] == None) | (client["phone"] == ""),
          rx.el.span("-", class_name="text-slate-400 text-sm"),
          rx.el.span(client["phone"], class_name="text-sm text-slate-800"),
        ),
        class_name="flex items-center gap-0.5",
      ),
      rx.el.div(
        rx.el.span("Dir: ", class_name=TYPOGRAPHY["caption"]),
        rx.cond(
          (client["address"] == None) | (client["address"] == ""),
          rx.el.span("-", class_name="text-slate-400 text-sm"),
          rx.el.span(client["address"], class_name="text-sm text-slate-800"),
        ),
        class_name="flex items-center gap-0.5",
      ),
      class_name="flex flex-col gap-1.5 mt-2",
    ),
    rx.el.div(
      rx.el.span(
        State.currency_symbol, " ", client["credit_available"].to_string(),
        class_name="font-semibold tabular-nums text-emerald-700",
      ),
      rx.el.div(
        rx.el.button(
          rx.icon("history", class_name="h-4 w-4"),
          on_click=lambda _, c=client: State.open_historial(c),
          class_name=BUTTON_STYLES["icon_primary"],
          title="Ver historial",
          aria_label="Ver historial de ventas",
        ),
        rx.el.button(
          rx.icon("pencil", class_name="h-4 w-4"),
          on_click=lambda _, c=client: State.open_modal(c),
          class_name=BUTTON_STYLES["icon_primary"],
          title="Editar",
          aria_label="Editar cliente",
        ),
        rx.el.button(
          rx.icon("trash-2", class_name="h-4 w-4"),
          on_click=lambda _, c_id=client["id"]: State.delete_client(c_id),
          disabled=State.is_loading,
          loading=State.is_loading,
          class_name=BUTTON_STYLES["icon_danger"],
          title="Eliminar",
          aria_label="Eliminar cliente",
        ),
        class_name="flex items-center gap-2",
      ),
      class_name="flex items-center justify-between mt-3 pt-2 border-t border-slate-100",
    ),
    class_name="bg-white border border-slate-200 rounded-xl p-4 shadow-sm",
  )


# ── Modal crear/editar cliente ───────────────────────────────────────────────

def client_form_modal() -> rx.Component:
  return modal_container(
    is_open=State.show_modal,
    on_close=State.close_modal,
    title=rx.cond(
      State.current_client["id"] == None,
      "Nuevo Cliente",
      "Editar Cliente",
    ),
    description="Completa los datos del cliente.",
    children=[
      rx.el.div(
        rx.el.div(
          rx.el.label("Nombre", class_name=TYPOGRAPHY["label"]),
          rx.el.input(
            default_value=State.current_client["name"],
            on_blur=lambda v: State.update_current_client("name", v),
            placeholder="Nombre completo",
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label(State.personal_id_label, class_name=TYPOGRAPHY["label"]),
          rx.el.input(
            default_value=State.current_client["dni"],
            on_blur=lambda v: State.update_current_client("dni", v),
            placeholder=State.personal_id_placeholder,
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label("Telefono", class_name=TYPOGRAPHY["label"]),
          rx.el.input(
            default_value=State.current_client["phone"],
            on_blur=lambda v: State.update_current_client("phone", v),
            placeholder="Numero de contacto",
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label("Direccion", class_name=TYPOGRAPHY["label"]),
          rx.el.input(
            default_value=State.current_client["address"],
            on_blur=lambda v: State.update_current_client("address", v),
            placeholder="Direccion del cliente",
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label("Email", class_name=TYPOGRAPHY["label"]),
          rx.el.input(
            type="email",
            default_value=State.current_client["email"],
            on_blur=lambda v: State.update_current_client("email", v),
            placeholder="correo@ejemplo.com",
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label("Segmento", class_name=TYPOGRAPHY["label"]),
          rx.el.select(
            rx.el.option("Sin segmento", value=""),
            rx.el.option("Nuevo",     value="nuevo"),
            rx.el.option("Regular",   value="regular"),
            rx.el.option("VIP",       value="vip"),
            rx.el.option("Mayorista", value="mayorista"),
            value=State.current_client["segment"],
            on_change=lambda v: State.update_current_client("segment", v),
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label("Limite de credito", class_name=TYPOGRAPHY["label"]),
          rx.el.input(
            type="number",
            step="0.01",
            min="0",
            default_value=State.current_client["credit_limit"],
            on_blur=lambda v: State.update_current_client("credit_limit", v),
            placeholder="0.00",
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label("Lista de precios", class_name=TYPOGRAPHY["label"]),
          rx.el.select(
            rx.el.option("Sin lista (precio base + tiers)", value=""),
            rx.foreach(
              State.available_price_lists,
              lambda pl: rx.el.option(pl["display_name"], value=pl["id"]),
            ),
            value=State.current_client["price_list_id"],
            on_change=lambda v: State.update_current_client("price_list_id", v),
            class_name=INPUT_STYLES["default"],
          ),
          rx.el.p(
            "Determina los precios al vender a este cliente.",
            class_name="text-xs text-slate-500",
          ),
          class_name="flex flex-col gap-1 md:col-span-2",
        ),
        class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
      )
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_modal,
        class_name=BUTTON_STYLES["secondary"],
      ),
      rx.el.button(
        rx.icon("save", class_name="h-4 w-4"),
        "Guardar",
        on_click=State.save_client,
        disabled=State.is_loading,
        loading=State.is_loading,
        class_name=BUTTON_STYLES["primary"],
      ),
      class_name="flex justify-end gap-3 pt-2",
    ),
    max_width="max-w-2xl",
  )


# ── Modal historial de ventas ────────────────────────────────────────────────

def _sale_row(sale: rx.Var[dict]) -> rx.Component:
  return rx.el.tr(
    rx.el.td(sale["fecha"],    class_name="py-2 px-3 text-sm tabular-nums"),
    rx.el.td(sale["condicion"], class_name="py-2 px-3 text-sm"),
    rx.el.td(
      rx.el.span(
        State.currency_symbol, " ", sale["total"],
        class_name=rx.cond(
          sale["anulada"],
          "tabular-nums text-slate-400 line-through",
          "tabular-nums font-medium text-slate-800",
        ),
      ),
      class_name="py-2 px-3 text-right",
    ),
    rx.el.td(
      rx.el.span(
        sale["estado"],
        class_name=rx.cond(
          sale["anulada"],
          "text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-600",
          "text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700",
        ),
      ),
      class_name="py-2 px-3",
    ),
    class_name="border-b hover:bg-slate-50 transition-colors",
  )


def historial_modal() -> rx.Component:
  return modal_container(
    is_open=State.show_historial,
    on_close=State.close_historial,
    title=rx.el.span(
      "Historial — ",
      State.historial_client["name"],
    ),
    description="Ventas registradas para este cliente.",
    children=[
      # Resumen
      rx.el.div(
        rx.el.div(
          rx.el.p(
            State.historial_sale_count.to_string(),
            class_name="text-2xl font-bold text-slate-800",
          ),
          rx.el.p("Ventas totales", class_name="text-xs text-slate-500 mt-0.5"),
          class_name="flex flex-col items-center p-4 bg-slate-50 rounded-xl",
        ),
        rx.el.div(
          rx.el.p(
            State.currency_symbol, " ", State.historial_total_spent,
            class_name="text-2xl font-bold text-emerald-700",
          ),
          rx.el.p("Total facturado", class_name="text-xs text-slate-500 mt-0.5"),
          class_name="flex flex-col items-center p-4 bg-emerald-50 rounded-xl",
        ),
        class_name="grid grid-cols-2 gap-3 mb-4",
      ),
      # Tabla de ventas
      rx.cond(
        State.client_sales.length() == 0,
        empty_state("Este cliente no tiene ventas registradas."),
        rx.el.div(
          rx.el.table(
            rx.el.thead(
              rx.el.tr(
                rx.el.th("Fecha",     scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Condición", scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Total",     scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right"),
                rx.el.th("Estado",    scope="col", class_name=TABLE_STYLES["header_cell"]),
                class_name=TABLE_STYLES["header"],
              )
            ),
            rx.el.tbody(rx.foreach(State.client_sales, _sale_row)),
            class_name="min-w-full text-sm",
          ),
          class_name="overflow-x-auto max-h-80 overflow-y-auto border border-slate-200 rounded-xl",
        ),
      ),
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cerrar",
        on_click=State.close_historial,
        class_name=BUTTON_STYLES["secondary"],
      ),
      class_name="flex justify-end pt-2",
    ),
    max_width="max-w-2xl",
  )


# ── Página principal ─────────────────────────────────────────────────────────

def clientes_page() -> rx.Component:
  content = rx.fragment(
    rx.el.div(
      page_header(
        "CLIENTES",
        "Administra clientes para ventas, crédito y presupuestos.",
        actions=[
          rx.el.button(
            rx.icon("plus", class_name="h-4 w-4"),
            "Nuevo Cliente",
            on_click=lambda: State.open_modal(None),
            class_name=BUTTON_STYLES["primary"],
          )
        ],
      ),
      rx.el.div(
        rx.debounce_input(
          rx.input(
            placeholder=rx.cond(
              State.personal_id_label == "DNI",
              "Buscar por nombre, DNI o teléfono...",
              "Buscar por nombre, documento o teléfono..."
            ),
            value=State.search_query,
            on_change=State.set_search_query,
            class_name=INPUT_STYLES["search"],
          ),
          debounce_timeout=600,
        ),
        class_name=CARD_STYLES["default"],
      ),
      rx.el.div(
        # Vista móvil
        rx.el.div(
          rx.foreach(State.clients_view, _client_card),
          class_name="flex flex-col gap-3 md:hidden",
        ),
        # Vista desktop
        rx.el.div(
          rx.el.table(
            rx.el.thead(
              rx.el.tr(
                rx.el.th("Nombre",  scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th(State.personal_id_label, scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Teléfono", scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Direccion", scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th(
                  "Credito Disp.",
                  scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right",
                ),
                rx.el.th(
                  "Acciones",
                  scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center",
                ),
                class_name=TABLE_STYLES["header"],
              )
            ),
            rx.el.tbody(rx.foreach(State.clients_view, client_row)),
            class_name="min-w-full text-sm",
          ),
          class_name="hidden md:block overflow-x-auto",
        ),
        rx.cond(
          State.clients_view.length() == 0,
          empty_state("No hay clientes registrados."),
          rx.fragment(),
        ),
        class_name=f"{CARD_STYLES['default']} flex flex-col gap-4",
      ),
      class_name="flex flex-col gap-6 p-4 sm:p-6 w-full",
    ),
    client_form_modal(),
    historial_modal(),
    on_mount=State.load_clients,
  )
  return permission_guard(
    has_permission=State.can_view_clientes,
    content=content,
    redirect_message="Acceso denegado a Clientes",
  )
