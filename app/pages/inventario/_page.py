import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  CARD_STYLES,
  INPUT_STYLES,
  SPACING,
  TABLE_STYLES,
  TYPOGRAPHY,
  page_title,
  pagination_controls,
  permission_guard,
)
from ._edit_product import edit_product_modal
from ._modals import import_modal, stock_details_modal, inventory_adjustment_modal
from ._product_table import inventory_stat_card, _product_card


def inventario_page() -> rx.Component:
  """Página principal de gestión de inventario."""
  content = rx.el.div(
    page_title(
      "INVENTARIO ACTUAL",
      "Gestiona el stock de productos, realiza ajustes y visualiza el valor total del inventario.",
    ),
    rx.el.div(
      inventory_stat_card(
        "Total Productos",
        State.inventory_total_products.to_string(),
        "text-slate-900",
      ),
      inventory_stat_card(
        "Con Stock",
        State.inventory_in_stock_count.to_string(),
        "text-emerald-600",
      ),
      inventory_stat_card(
        "Stock Bajo",
        State.inventory_low_stock_count.to_string(),
        "text-amber-600",
      ),
      inventory_stat_card(
        "Agotados",
        State.inventory_out_of_stock_count.to_string(),
        "text-red-600",
      ),
      class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
    ),
    rx.el.div(
      rx.el.div(
        rx.el.div(
          rx.el.h2(
            "CATEGORIAS DE PRODUCTOS",
            class_name=TYPOGRAPHY["section_title"],
          ),
          rx.el.span(
            State.categories.length().to_string(),
            " categorías",
            class_name="text-xs text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full",
          ),
          class_name="flex items-center gap-3",
        ),
        rx.cond(
          State.categories.length() > 6,
          rx.el.button(
            rx.cond(
              State.categories_panel_expanded,
              "Vista compacta",
              "Ver todas",
            ),
            on_click=State.toggle_categories_panel,
            class_name=(
              "text-xs font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 "
              "px-3 py-1.5 rounded-md hover:bg-indigo-100"
            ),
          ),
          rx.fragment(),
        ),
        class_name="flex items-center justify-between gap-2 mb-4",
      ),
      rx.el.div(
        rx.el.input(
          key=State.new_category_input_key.to_string(),
          placeholder="Nombre de la categoría",
          default_value=State.new_category_name,
          on_blur=lambda v: State.update_new_category_name(v),
          class_name=f"{INPUT_STYLES['default']} flex-1",
        ),
        rx.el.button(
          rx.icon("plus", class_name="h-4 w-4"),
          "Agregar",
          on_click=State.add_category,
          class_name=BUTTON_STYLES["primary"],
        ),
        class_name="flex flex-col sm:flex-row gap-3 mb-3",
      ),
      rx.el.div(
        rx.foreach(
          State.categories,
          lambda category: rx.el.div(
            rx.el.span(category, class_name="font-medium"),
            rx.cond(
              category == "General",
              rx.fragment(),
              rx.el.button(
                rx.icon("x", class_name="h-3 w-3"),
                on_click=lambda category=category: State.remove_category(
                  category
                ),
                title="Eliminar categoria",
                aria_label="Eliminar categoria",
                class_name="text-red-500 hover:text-red-700",
              ),
            ),
            class_name=(
              "inline-flex items-center gap-2 bg-slate-100 px-3 py-1 rounded-full "
              "shrink-0 border border-slate-200"
            ),
          ),
        ),
        class_name=rx.cond(
          State.categories_panel_expanded,
          "flex flex-wrap gap-2 max-h-44 overflow-y-auto pr-1",
          "flex flex-nowrap gap-2 overflow-x-auto whitespace-nowrap pb-1",
        ),
      ),
      rx.cond(
        State.categories.length() > 6,
        rx.el.p(
          rx.cond(
            State.categories_panel_expanded,
            "Vista expandida de categorías.",
            "Vista compacta: desliza horizontalmente para ver más.",
          ),
          class_name=f"{TYPOGRAPHY['caption']} mt-2",
        ),
        rx.fragment(),
      ),
      class_name=f"{CARD_STYLES['default']} mb-6",
    ),
    rx.el.div(
      rx.el.div(
        rx.debounce_input(
          rx.input(
            placeholder="Buscar producto...",
            on_change=State.set_inventory_search_term,
            class_name=INPUT_STYLES["default"],
          ),
          debounce_timeout=600,
        ),
        rx.el.div(
          rx.el.button(
            rx.icon("plus", class_name="h-4 w-4"),
            "Nuevo Producto",
            on_click=State.open_create_product_modal,
            class_name=BUTTON_STYLES["primary_sm"],
          ),
          rx.el.button(
            rx.icon("upload", class_name="h-4 w-4"),
            "Importar",
            on_click=State.open_import_modal,
            class_name=BUTTON_STYLES["ghost"],
          ),
          rx.el.button(
            rx.icon("download", class_name="h-4 w-4"),
            "Exportar Inventario",
            on_click=State.export_inventory_to_excel,
            class_name=BUTTON_STYLES["success_sm"],
          ),
          rx.el.button(
            rx.icon("clipboard-check", class_name="h-4 w-4"),
            "Registrar Fisico",
            on_click=State.open_inventory_check_modal,
            class_name=BUTTON_STYLES["warning"],
          ),
          rx.el.button(
            rx.icon("tag", class_name="h-4 w-4"),
            "Etiquetas",
            on_click=lambda: rx.redirect("/etiquetas"),
            class_name=BUTTON_STYLES["ghost"],
            title="Abrir el generador de etiquetas",
          ),
          class_name="flex w-full flex-wrap items-center gap-2 md:w-auto md:justify-end",
        ),
        class_name="flex flex-col gap-4 md:flex-row md:items-center md:justify-between pb-4 border-b border-slate-200",
      ),
      # Toggle mostrar inactivos
      rx.el.div(
        rx.el.label(
          rx.el.input(
            type="checkbox",
            checked=State.show_inactive_products,
            on_change=State.toggle_show_inactive_products,
            class_name="rounded border-slate-300 text-indigo-600 mr-2",
          ),
          rx.el.span("Mostrar productos inactivos", class_name="text-sm text-slate-600"),
          class_name="flex items-center cursor-pointer",
        ),
        class_name="pb-2",
      ),
      # Vista móvil: Cards (visible en < md)
      rx.el.div(
        rx.foreach(State.inventory_list, _product_card),
        class_name="flex flex-col gap-3 md:hidden",
      ),
      # Vista desktop: Tabla (oculta en < md)
      rx.el.div(
        rx.el.table(
          rx.el.thead(
            rx.el.tr(
              rx.el.th("Codigo de Barra", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden lg:table-cell"),
              rx.el.th("Descripción", scope="col", class_name=TABLE_STYLES["header_cell"]),
              rx.el.th("Categoría", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
              rx.el.th(
                "Stock", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center"
              ),
              rx.el.th(
                "Unidad", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center hidden md:table-cell"
              ),
              rx.el.th(
                "Precio Compra", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right hidden lg:table-cell"
              ),
              rx.el.th(
                "Precio Venta", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right"
              ),
              rx.el.th(
                "Valor Total Stock", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right hidden lg:table-cell"
              ),
              rx.el.th(
                "Acciones", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center"
              ),
              class_name=TABLE_STYLES["header"],
            )
          ),
          rx.el.tbody(
            rx.foreach(
              State.inventory_list,
              lambda product: rx.el.tr(
                rx.el.td(
                  product["barcode"],
                  class_name="py-3 px-4 hidden lg:table-cell",
                ),
                rx.el.td(
                  rx.el.div(
                    product["description"],
                    rx.cond(
                      product["is_kit"],
                      rx.el.span(
                        "KIT",
                        class_name="ml-1.5 text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-semibold tracking-wide",
                      ),
                      rx.fragment(),
                    ),
                    rx.cond(
                      product["is_active"],
                      rx.fragment(),
                      rx.el.span(
                        "Inactivo",
                        class_name="ml-2 text-xs px-2 py-0.5 rounded-full bg-slate-200 text-slate-600",
                      ),
                    ),
                    class_name="flex items-center gap-1",
                  ),
                  class_name=rx.cond(
                    product["is_active"],
                    "py-3 px-4 font-medium",
                    "py-3 px-4 font-medium text-slate-400",
                  ),
                ),
                rx.el.td(
                  product["category"],
                  class_name="py-3 px-4 text-left hidden md:table-cell",
                ),
                rx.el.td(
                  rx.el.div(
                    product["stock"].to_string(),
                    rx.cond(
                      product["stock_is_low"],
                      rx.el.span(
                        "Bajo",
                        class_name="ml-2 text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-800",
                      ),
                      rx.cond(
                        product["stock_is_medium"],
                        rx.el.span(
                          "Moderado",
                          class_name="ml-2 text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800",
                        ),
                        rx.fragment(),
                      ),
                    ),
                    class_name=rx.cond(
                      product["stock_is_low"],
                      "flex items-center justify-center font-bold text-red-600",
                      "flex items-center justify-center",
                    ),
                  )
                ),
                rx.el.td(
                  product["unit"], class_name="py-3 px-4 text-center hidden md:table-cell"
                ),
                rx.el.td(
                  State.currency_symbol,
                  product["purchase_price"].to_string(),
                  class_name="py-3 px-4 text-right hidden lg:table-cell",
                ),
                rx.el.td(
                  State.currency_symbol,
                  product["sale_price"].to_string(),
                  class_name="py-3 px-4 text-right text-green-600",
                ),
                rx.el.td(
                  State.currency_symbol,
                  product["stock_total_display"],
                  class_name="py-3 px-4 text-right font-bold hidden lg:table-cell",
                ),
                rx.el.td(
                  rx.el.div(
                    rx.el.button(
                      rx.icon("pencil", class_name="h-4 w-4"),
                      on_click=lambda: State.open_edit_product(product),
                      class_name=BUTTON_STYLES["icon_warning"],
                      title="Editar",
                      aria_label="Editar",
                    ),
                    rx.el.button(
                      rx.icon("eye", class_name="h-4 w-4"),
                      on_click=lambda: State.open_stock_details(product),
                      class_name=BUTTON_STYLES["icon_ghost"],
                      title="Ver Desglose",
                      aria_label="Ver desglose",
                    ),
                    rx.cond(
                      product["is_variant"],
                      rx.fragment(),
                      rx.el.div(
                        rx.el.button(
                          rx.cond(
                            product["is_active"],
                            rx.icon("eye-off", class_name="h-4 w-4"),
                            rx.icon("eye", class_name="h-4 w-4"),
                          ),
                          on_click=lambda: State.toggle_product_active(product["id"]),
                          disabled=State.is_loading,
                          class_name=rx.cond(
                            product["is_active"],
                            BUTTON_STYLES["icon_ghost"],
                            BUTTON_STYLES["icon_success"],
                          ),
                          title=rx.cond(product["is_active"], "Desactivar", "Activar"),
                          aria_label=rx.cond(product["is_active"], "Desactivar", "Activar"),
                        ),
                        rx.el.button(
                          rx.icon("trash-2", class_name="h-4 w-4"),
                          on_click=lambda: State.delete_product(product["id"]),
                          disabled=State.is_loading,
                          loading=State.is_loading,
                          class_name=BUTTON_STYLES["icon_danger"],
                          title="Eliminar",
                          aria_label="Eliminar",
                        ),
                        class_name="flex items-center gap-1",
                      ),
                    ),
                    class_name="flex items-center justify-center gap-2",
                  ),
                  class_name="py-3 px-4",
                ),
                class_name="border-b",
              ),
            )
          ),
          class_name="min-w-full",
        ),
        class_name="hidden md:block w-full overflow-x-auto",
      ),
      rx.cond(
        State.inventory_list.length() == 0,
        rx.el.p(
          "El inventario está vacío.",
          class_name="text-slate-500 text-center py-8",
        ),
        rx.fragment(),
      ),
      rx.cond(
        State.inventory_total_pages > 1,
        pagination_controls(
          current_page=State.inventory_display_page,
          total_pages=State.inventory_total_pages,
          on_prev=lambda: State.set_inventory_page(State.inventory_display_page - 1),
          on_next=lambda: State.set_inventory_page(State.inventory_display_page + 1),
        ),
        rx.fragment(),
      ),
      class_name=f"{CARD_STYLES['default']} flex flex-col {SPACING['card_gap']}",
    ),
    inventory_adjustment_modal(),
    edit_product_modal(),
    stock_details_modal(),
    import_modal(),
    on_mount=State.refresh_inventory_cache,
    class_name=f"w-full flex flex-col {SPACING['page_gap']}",
  )
  return permission_guard(
    has_permission=State.can_view_inventario,
    content=content,
    redirect_message="Acceso denegado a Inventario",
  )
