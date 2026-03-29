import reflex as rx
from app.state import State
from app.components.ui import (
  pagination_controls,
  empty_state,
  select_filter,
  date_range_filter,
  payment_method_badge,
  BUTTON_STYLES,
  CARD_STYLES,
  INPUT_STYLES,
  SELECT_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  page_title,
  permission_guard,
)


def history_filters() -> rx.Component:
  """Seccion de filtros para la pagina de historial."""
  def _build_filters() -> list[rx.Component]:
    start_filter, end_filter = date_range_filter(
      start_value=State.staged_history_filter_start_date,
      end_value=State.staged_history_filter_end_date,
      on_start_change=State.set_staged_history_filter_start_date,
      on_end_change=State.set_staged_history_filter_end_date,
    )
    filters = [
      select_filter(
        "Filtrar por tipo",
        [("Todos", "Todos"), ("Venta", "Venta")],
        State.staged_history_filter_type,
        State.set_staged_history_filter_type,
      ),
      rx.el.div(
        rx.el.label(
          "Categoria",
          class_name=TYPOGRAPHY["label_secondary"],
        ),
        rx.el.select(
          rx.foreach(
            State.available_category_options,
            lambda option: rx.el.option(
              option[0], value=option[1]
            ),
          ),
          value=State.staged_history_filter_category,
          on_change=State.set_staged_history_filter_category,
          class_name=SELECT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label(
          "Buscar por producto",
          class_name=TYPOGRAPHY["label_secondary"],
        ),
        rx.el.input(
          placeholder="Descripción del producto",
          on_blur=lambda v: State.set_staged_history_filter_product(v),
          class_name=INPUT_STYLES["default"],
          default_value=State.staged_history_filter_product,
        ),
        class_name="flex flex-col gap-1",
      ),
      start_filter,
      end_filter,
    ]
    return [
      rx.el.div(filter_item, class_name="min-w-[160px] flex-1")
      for filter_item in filters
    ]

  def _build_actions() -> list[rx.Component]:
    return [
      rx.el.button(
        rx.icon("search", class_name="h-4 w-4"),
        "Buscar",
        on_click=State.apply_history_filters,
        class_name=BUTTON_STYLES["primary"],
      ),
      rx.el.button(
        "Limpiar",
        on_click=State.reset_history_filters,
        class_name=BUTTON_STYLES["secondary"],
      ),
      rx.el.button(
        rx.icon("download", class_name="h-4 w-4"),
        "Exportar",
        on_click=State.export_to_excel,
        class_name=BUTTON_STYLES["success"],
      ),
    ]

  return rx.el.div(
    rx.el.div(
      *_build_filters(),
      class_name="flex flex-wrap lg:flex-nowrap gap-3 items-end",
    ),
    rx.el.div(
      *_build_actions(),
      class_name="flex flex-wrap gap-2 justify-end",
    ),
    class_name="flex flex-col gap-3 pb-4 border-b border-slate-200",
  )


def history_table_row(movement: rx.Var[dict]) -> rx.Component:
  """Renderiza una fila del listado de historial (clickeable → abre detalle)."""
  return rx.el.tr(
    rx.el.td(movement["timestamp"], class_name="py-3 px-4 text-sm text-slate-700 whitespace-nowrap"),
    rx.el.td(
      movement["client_name"],
      class_name="py-3 px-4 text-sm text-slate-700",
    ),
    rx.el.td(
      payment_method_badge(movement.get("payment_method")),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      movement.get("payment_details", ""),
      class_name="py-3 px-4 text-sm text-slate-500 hidden lg:table-cell max-w-[200px] truncate",
      title=movement.get("payment_details", ""),
    ),
    rx.el.td(
      State.currency_symbol,
      " ",
      movement["total"].to_string(),
      class_name="py-3 px-4 text-right font-semibold tabular-nums text-slate-900 whitespace-nowrap",
    ),
    rx.el.td(
      movement.get("user", "Desconocido"),
      class_name="py-3 px-4 text-sm text-slate-500 hidden xl:table-cell",
    ),
    on_click=State.open_sale_detail(movement["sale_id"]),
    class_name="border-b border-slate-100 hover:bg-indigo-50/60 cursor-pointer transition-colors duration-150",
  )

# ════════════════════════════════════════════════════════════
# CARD MOVIL (vista responsiva para pantallas pequenas)
# ════════════════════════════════════════════════════════════

def _sale_card(sale: rx.Var) -> rx.Component:
  """Card de venta para vista móvil (clickeable → abre detalle)."""
  return rx.el.div(
    # Header: Fecha + Total
    rx.el.div(
      rx.el.span(
        sale["timestamp"],
        class_name="font-mono font-medium text-slate-900 text-sm",
      ),
      rx.el.span(
        State.currency_symbol,
        " ",
        sale["total"].to_string(),
        class_name="text-base font-bold text-slate-900 tabular-nums",
      ),
      class_name="flex items-center justify-between gap-2",
    ),
    # Body: Cliente + Método de pago (2 columnas)
    rx.el.div(
      rx.el.div(
        rx.el.span("Cliente", class_name=TYPOGRAPHY["caption"]),
        rx.el.span(
          sale["client_name"],
          class_name="text-sm font-medium text-slate-800 truncate",
        ),
        class_name="flex flex-col gap-0.5 min-w-0",
      ),
      rx.el.div(
        rx.el.span("Pago", class_name=TYPOGRAPHY["caption"]),
        payment_method_badge(sale.get("payment_method")),
        class_name="flex flex-col gap-0.5",
      ),
      class_name="grid grid-cols-2 gap-3 mt-2",
    ),
    on_click=State.open_sale_detail(sale["sale_id"]),
    class_name=(
      "bg-white border border-slate-200 rounded-xl p-4 shadow-sm "
      "cursor-pointer hover:border-indigo-300 hover:shadow-md active:bg-indigo-50/40 "
      "transition-all duration-150"
    ),
  )


def sale_detail_modal() -> rx.Component:
  """Modal de detalle de una venta del historial."""
  return rx.radix.primitives.dialog.root(
    rx.radix.primitives.dialog.portal(
      rx.radix.primitives.dialog.overlay(
        class_name="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 modal-overlay"
      ),
      rx.radix.primitives.dialog.content(
        rx.el.div(
          rx.el.h3("Detalle de venta", class_name=TYPOGRAPHY["section_title"]),
          rx.el.p(
            "Productos y resumen del comprobante seleccionado.",
            class_name=TYPOGRAPHY["body_secondary"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.divider(color="slate-100"),
        rx.cond(
          State.selected_sale_id == "",
          rx.el.p("Venta no disponible.", class_name=TYPOGRAPHY["body_secondary"]),
          rx.el.div(
            rx.el.div(
              rx.el.div(
                rx.el.span("Fecha", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
                rx.el.span(
                  State.selected_sale_summary["timestamp"],
                  class_name="text-sm font-semibold text-slate-900",
                ),
                class_name="flex flex-col gap-1",
              ),
              rx.el.div(
                rx.el.span("Cliente", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
                rx.el.span(
                  State.selected_sale_summary["client_name"],
                  class_name="text-sm font-semibold text-slate-900",
                ),
                class_name="flex flex-col gap-1",
              ),
              rx.el.div(
                rx.el.span("Usuario", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
                rx.el.span(
                  State.selected_sale_summary["user"],
                  class_name="text-sm font-semibold text-slate-900",
                ),
                class_name="flex flex-col gap-1",
              ),
            class_name="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50 border border-slate-200 rounded-xl p-3",
          ),
            rx.el.div(
              rx.el.div(
                rx.el.span("Metodo de pago", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
                payment_method_badge(State.selected_sale_summary["payment_method"]),
                class_name="flex flex-col gap-1",
              ),
              rx.el.div(
                rx.el.span("Total", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
                rx.el.span(
                  State.currency_symbol,
                  State.selected_sale_summary["total"].to_string(),
                  class_name="text-lg font-semibold text-slate-900",
                ),
                class_name="flex flex-col gap-1",
              ),
            class_name="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-slate-50 border border-slate-200 rounded-xl p-3",
          ),
            rx.el.div(
              rx.el.h4("Productos", class_name=TYPOGRAPHY["label"]),
              rx.cond(
                State.selected_sale_items_view.length() == 0,
                rx.el.p(
                  "Sin productos registrados.",
                  class_name=TYPOGRAPHY["body_secondary"],
                ),
                rx.el.div(
                  rx.el.table(
                    rx.el.thead(
                      rx.el.tr(
                        rx.el.th("Producto", scope="col", class_name=TABLE_STYLES["header_cell"]),
                        rx.el.th(
                          "Cantidad",
                          scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right",
                        ),
                        rx.el.th(
                          "Precio",
                          scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right",
                        ),
                        rx.el.th(
                          "Subtotal",
                          scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right",
                        ),
                        class_name=TABLE_STYLES["header"],
                      )
                    ),
                    rx.el.tbody(
                      rx.foreach(
                        State.selected_sale_items_view,
                        lambda item: rx.el.tr(
                          rx.el.td(item["description"], class_name="py-2 px-3 text-sm"),
                          rx.el.td(item["quantity"].to_string(), class_name="py-2 px-3 text-right text-sm"),
                          rx.el.td(
                            State.currency_symbol,
                            item["unit_price"].to_string(),
                            class_name="py-2 px-3 text-right text-sm",
                          ),
                          rx.el.td(
                            State.currency_symbol,
                            item["subtotal"].to_string(),
                            class_name="py-2 px-3 text-right text-sm font-semibold",
                          ),
                          class_name="border-b border-slate-100",
                        ),
                      )
                    ),
                    class_name="min-w-full text-sm",
                  ),
                class_name="max-h-64 overflow-y-auto overflow-x-auto border border-slate-200 rounded-xl",
              ),
            ),
            class_name="flex flex-col gap-2",
          ),
          class_name="flex flex-col gap-4",
        ),
      ),
      rx.divider(color="slate-100"),
      rx.el.div(
        rx.el.button(
          "Cerrar",
          on_click=State.close_sale_detail,
          class_name=BUTTON_STYLES["secondary"],
        ),
        class_name="flex justify-end gap-3",
      ),
      class_name=(
        "bg-white rounded-xl border border-slate-200 shadow-sm p-6 w-full max-w-3xl space-y-4 "
        "data-[state=open]:animate-in data-[state=closed]:animate-out "
        "data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0 "
        "data-[state=open]:zoom-in-95 data-[state=closed]:zoom-out-95 "
        "data-[state=open]:slide-in-from-top-4 data-[state=closed]:slide-out-to-top-4 "
        "fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-3xl -translate-x-1/2 -translate-y-1/2 focus:outline-none"
      ),
    ),
  ),
  open=State.sale_detail_modal_open,
  on_open_change=State.set_sale_detail_modal_open,
)


def credit_sales_card() -> rx.Component:
  return rx.card(
    rx.el.div(
      rx.el.div(
        rx.icon("credit-card", class_name="h-6 w-6 text-amber-600"),
        class_name="p-3 rounded-lg bg-amber-100",
      ),
      rx.el.div(
        rx.el.p(
          "Saldo por cobrar (Credito)",
          class_name=TYPOGRAPHY["body_secondary"],
        ),
        rx.el.p(
          rx.el.span(
            State.currency_symbol, State.credit_outstanding.to_string()
          ),
          class_name="text-2xl font-bold text-slate-800",
        ),
        class_name="flex-1",
      ),
      class_name="flex items-center gap-4",
    ),
    class_name=CARD_STYLES["compact"],
  )


def render_dynamic_card(card: rx.Var[dict]) -> rx.Component:
  icon_class = rx.match(
    card["color"],
    ("blue", "h-6 w-6 text-indigo-600"),
    ("indigo", "h-6 w-6 text-indigo-600"),
    ("violet", "h-6 w-6 text-violet-600"),
    ("pink", "h-6 w-6 text-pink-600"),
    ("cyan", "h-6 w-6 text-cyan-600"),
    ("orange", "h-6 w-6 text-orange-600"),
    ("amber", "h-6 w-6 text-amber-600"),
    ("gray", "h-6 w-6 text-slate-600"),
    "h-6 w-6 text-slate-600",
  )
  icon_wrapper = rx.match(
    card["color"],
    ("blue", "p-3 rounded-lg bg-indigo-100"),
    ("indigo", "p-3 rounded-lg bg-indigo-100"),
    ("violet", "p-3 rounded-lg bg-violet-100"),
    ("pink", "p-3 rounded-lg bg-pink-100"),
    ("cyan", "p-3 rounded-lg bg-cyan-100"),
    ("orange", "p-3 rounded-lg bg-orange-100"),
    ("amber", "p-3 rounded-lg bg-amber-100"),
    ("gray", "p-3 rounded-lg bg-slate-100"),
    "p-3 rounded-lg bg-slate-100",
  )
  icon_component = rx.match(
    card["icon"],
    ("coins", rx.icon("coins", class_name=icon_class)),
    ("credit-card", rx.icon("credit-card", class_name=icon_class)),
    ("qr-code", rx.icon("qr-code", class_name=icon_class)),
    ("landmark", rx.icon("landmark", class_name=icon_class)),
    ("layers", rx.icon("layers", class_name=icon_class)),
    ("circle-help", rx.icon("circle-help", class_name=icon_class)),
    rx.icon("circle-help", class_name=icon_class),
  )
  return rx.card(
    rx.el.div(
      rx.el.div(
        icon_component,
        class_name=icon_wrapper,
      ),
      rx.el.div(
        rx.el.p(card["name"], class_name=TYPOGRAPHY["body_secondary"]),
        rx.el.p(
          rx.el.span(
            State.currency_symbol, card["amount"].to_string()
          ),
          class_name="text-2xl font-bold text-slate-800",
        ),
        class_name="flex-1",
      ),
      class_name="flex items-center gap-4",
    ),
    class_name=CARD_STYLES["compact"],
  )


def historial_page() -> rx.Component:
  """Página principal del historial de ventas y movimientos."""
  content = rx.fragment(
    rx.el.div(
      page_title(
        "HISTORIAL DE VENTAS",
        "Consulta y exporta el registro de todas las ventas realizadas.",
      ),
      rx.el.div(
        credit_sales_card(),
        rx.foreach(State.dynamic_payment_cards, render_dynamic_card),
        class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-6",
      ),
      rx.el.div(
        history_filters(),
        # Vista movil: Cards (visible en < md)
        rx.el.div(
          rx.foreach(State.filtered_history, _sale_card),
          class_name="flex flex-col gap-3 md:hidden",
        ),
        # Vista desktop: Tabla (oculta en < md)
        rx.el.div(
          rx.el.table(
            rx.el.thead(
              rx.el.tr(
                rx.el.th("Fecha y Hora", scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Cliente", scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Método de Pago", scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Detalle Pago", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden lg:table-cell"),
                rx.el.th(
                  "Total", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right"
                ),
                rx.el.th("Usuario", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden xl:table-cell"),
                class_name=TABLE_STYLES["header"],
              )
            ),
            rx.el.tbody(rx.foreach(State.filtered_history, history_table_row)),
            class_name="min-w-full",
          ),
          class_name="hidden md:block overflow-x-auto",
        ),
        rx.cond(
          State.filtered_history.length() == 0,
          empty_state("No hay movimientos que coincidan con los filtros."),
          rx.fragment(),
        ),
        class_name=f"{CARD_STYLES['default']} flex flex-col gap-4",
      ),
      pagination_controls(
        current_page=State.current_page_history,
        total_pages=State.total_pages,
        on_prev=lambda: State.set_history_page(State.current_page_history - 1),
        on_next=lambda: State.set_history_page(State.current_page_history + 1),
      ),
      # Nota: Los reportes financieros ahora se generan desde el módulo Reportes
      # para mantener un único punto de verdad para datos contables
    rx.el.div(
      rx.el.div(
        rx.icon("info", class_name="w-5 h-5 text-indigo-500"),
        rx.el.div(
          rx.el.p("¿Necesitas reportes financieros?", class_name="font-medium text-slate-800"),
          rx.el.p(
            "Los reportes de ingresos por método de pago, detalle de cobros y cierres de caja ahora se generan desde el módulo ",
            rx.link("Reportes", href="/reportes", class_name="text-indigo-600 hover:underline font-medium"),
            " para garantizar datos 100% exactos y consolidados.",
            class_name=TYPOGRAPHY["body_secondary"],
          ),
          class_name="flex-1",
        ),
        class_name="flex items-start gap-3",
      ),
      class_name="bg-indigo-50 border border-indigo-100 rounded-xl p-4",
    ),
      class_name="p-4 sm:p-6 w-full flex flex-col gap-6",
    ),
    sale_detail_modal(),
    on_mount=State.reload_history_background,
  )
  return permission_guard(
    has_permission=State.can_view_historial,
    content=content,
    redirect_message="Acceso denegado a Historial",
  )
