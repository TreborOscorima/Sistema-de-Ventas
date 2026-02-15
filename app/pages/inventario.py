import reflex as rx
from app.state import State
from app.components.ui import (
  TABLE_STYLES,
  page_title,
  pagination_controls,
  permission_guard,
  toggle_switch,
)


def edit_product_modal() -> rx.Component:
  return rx.cond(
    State.is_editing_product,
    rx.el.div(
      rx.el.div(
        on_click=State.cancel_edit_product,
        class_name="fixed inset-0 bg-black/40 backdrop-blur-sm modal-overlay",
      ),
      rx.el.div(
        rx.el.div(
          rx.el.h3(
            "Editar Producto",
            class_name="text-xl font-semibold text-slate-800",
          ),
          rx.el.button(
            rx.icon("x", class_name="h-4 w-4"),
            on_click=State.cancel_edit_product,
            class_name="p-2 rounded-full hover:bg-slate-100",
          ),
          class_name="flex items-start justify-between gap-4 mb-4",
        ),
        rx.divider(color="slate-100"),
        rx.el.div(
          rx.el.div(
            rx.el.label("Código de Barra", class_name="block text-sm font-medium text-slate-700"),
            rx.el.input(
              default_value=State.editing_product["barcode"],
              on_blur=lambda v: State.handle_edit_product_change("barcode", v),
              class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
              debounce_timeout=600,
            ),
          ),
          rx.el.div(
            rx.el.label("Descripción", class_name="block text-sm font-medium text-slate-700"),
            rx.el.input(
              default_value=State.editing_product["description"],
              on_blur=lambda v: State.handle_edit_product_change("description", v),
              class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
              debounce_timeout=600,
            ),
          ),
          rx.el.div(
            rx.el.label("Categoría", class_name="block text-sm font-medium text-slate-700"),
            rx.el.select(
              rx.foreach(
                State.categories,
                lambda cat: rx.el.option(cat, value=cat)
              ),
              default_value=State.editing_product["category"],
              on_change=lambda v: State.handle_edit_product_change("category", v),
              class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            ),
          ),
          rx.el.div(
            rx.cond(
              State.show_variants,
              rx.el.div(
                rx.el.label(
                  "Stock Total (calculado)",
                  class_name="block text-sm font-medium text-slate-700",
                ),
                rx.el.input(
                  type="number",
                  value=State.variants_stock_total.to_string(),
                  is_disabled=True,
                  class_name="w-full h-10 px-3 text-sm bg-slate-100 border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                ),
              ),
              rx.el.div(
                rx.el.label(
                  "Stock",
                  class_name="block text-sm font-medium text-slate-700",
                ),
                rx.el.input(
                  type="number",
                  default_value=State.editing_product["stock"].to_string(),
                  on_blur=lambda v: State.handle_edit_product_change("stock", v),
                  class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                ),
              ),
            )
          ),
          rx.el.div(
            rx.el.label("Unidad", class_name="block text-sm font-medium text-slate-700"),
            rx.el.select(
              rx.el.option("Unidad", value="Unidad"),
              rx.el.option("Kg", value="Kg"),
              rx.el.option("Lt", value="Lt"),
              rx.el.option("Paquete", value="Paquete"),
              rx.el.option("Caja", value="Caja"),
              default_value=State.editing_product["unit"],
              on_change=lambda v: State.handle_edit_product_change("unit", v),
              class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            ),
          ),
          rx.el.div(
            rx.el.label("Precio Compra", class_name="block text-sm font-medium text-slate-700"),
            rx.el.input(
              type="number",
              default_value=State.editing_product["purchase_price"].to_string(),
              on_blur=lambda v: State.handle_edit_product_change("purchase_price", v),
              class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            ),
          ),
          rx.el.div(
            rx.el.label("Precio Venta", class_name="block text-sm font-medium text-slate-700"),
            rx.el.input(
              type="number",
              default_value=State.editing_product["sale_price"].to_string(),
              on_blur=lambda v: State.handle_edit_product_change("sale_price", v),
              class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            ),
          ),
          class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        rx.el.div(
          rx.el.div(
            rx.el.label(
              "Tiene Variantes",
              class_name="text-sm font-medium text-slate-700",
            ),
            rx.el.div(
              toggle_switch(
                checked=State.show_variants,
                on_change=State.set_show_variants,
              ),
              rx.el.span(
                "Tallas/colores con stock individual",
                class_name="text-xs text-slate-500",
              ),
              class_name="flex items-center gap-2",
            ),
            class_name="flex flex-col gap-2",
          ),
          rx.el.div(
            rx.el.label(
              "Precios Mayoristas",
              class_name="text-sm font-medium text-slate-700",
            ),
            rx.el.div(
              toggle_switch(
                checked=State.show_wholesale,
                on_change=State.set_show_wholesale,
              ),
              rx.el.span(
                "Escalas por cantidad mínima",
                class_name="text-xs text-slate-500",
              ),
              class_name="flex items-center gap-2",
            ),
            class_name="flex flex-col gap-2",
          ),
          class_name="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4",
        ),
        rx.cond(
          State.show_variants,
          rx.el.div(
            rx.el.div(
              rx.el.h4(
                "Variantes",
                class_name="text-sm font-semibold text-slate-700",
              ),
              rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                "Agregar variante",
                on_click=State.add_variant_row,
                class_name="flex items-center gap-2 px-3 py-2 text-xs rounded-md bg-indigo-600 text-white hover:bg-indigo-700",
              ),
              class_name="flex items-center justify-between",
            ),
            rx.el.div(
              rx.el.div(
                rx.el.span(
                  "SKU", class_name="text-xs text-slate-500 uppercase sm:col-span-2"
                ),
                rx.el.span("Talla", class_name="text-xs text-slate-500 uppercase"),
                rx.el.span("Color", class_name="text-xs text-slate-500 uppercase"),
                rx.el.span("Stock", class_name="text-xs text-slate-500 uppercase"),
                rx.el.span("Acción", class_name="text-xs text-slate-500 uppercase"),
                class_name="hidden sm:grid sm:grid-cols-6 gap-2",
              ),
              rx.foreach(
                State.variant_rows,
                lambda row: rx.el.div(
                  rx.el.input(
                    placeholder="SKU",
                    id=f"variant_sku_{row['index']}",
                    default_value=row["sku"],
                    on_blur=lambda v, index=row["index"]: State.update_variant_field(
                      index, "sku", v
                    ),
                    on_key_down=lambda k, index=row["index"]: State.handle_variant_sku_keydown(
                      k, index
                    ),
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 sm:col-span-2",
                  ),
                  rx.el.input(
                    placeholder="Talla",
                    default_value=row["size"],
                    on_blur=lambda v, index=row["index"]: State.update_variant_field(
                      index, "size", v
                    ),
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                  ),
                  rx.el.input(
                    placeholder="Color",
                    default_value=row["color"],
                    on_blur=lambda v, index=row["index"]: State.update_variant_field(
                      index, "color", v
                    ),
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                  ),
                  rx.el.input(
                    type="number",
                    placeholder="0",
                    default_value=row["stock"].to_string(),
                    on_blur=lambda v, index=row["index"]: State.update_variant_field(
                      index, "stock", v
                    ),
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                  ),
                  rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda _, index=row["index"]: State.remove_variant_row(
                      index
                    ),
                    class_name="p-2 text-red-600 hover:bg-red-50 rounded-md",
                  ),
                  class_name="grid grid-cols-1 sm:grid-cols-6 gap-2 items-center",
                ),
              ),
              class_name="flex flex-col gap-3",
            ),
            class_name="mt-4 space-y-3",
          ),
          rx.fragment(),
        ),
        rx.cond(
          State.show_wholesale,
          rx.el.div(
            rx.el.div(
              rx.el.h4(
                "Precios Mayoristas",
                class_name="text-sm font-semibold text-slate-700",
              ),
              rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                "Agregar regla",
                on_click=State.add_tier_row,
                class_name="flex items-center gap-2 px-3 py-2 text-xs rounded-md bg-indigo-600 text-white hover:bg-indigo-700",
              ),
              class_name="flex items-center justify-between",
            ),
            rx.el.div(
              rx.el.div(
                rx.el.span(
                  "Cantidad mínima", class_name="text-xs text-slate-500 uppercase"
                ),
                rx.el.span(
                  "Precio unitario", class_name="text-xs text-slate-500 uppercase"
                ),
                rx.el.span("Acción", class_name="text-xs text-slate-500 uppercase"),
                class_name="hidden sm:grid sm:grid-cols-3 gap-2",
              ),
              rx.foreach(
                State.price_tier_rows,
                lambda row: rx.el.div(
                  rx.el.input(
                    type="number",
                    placeholder="0",
                    default_value=row["min_qty"].to_string(),
                    on_blur=lambda v, index=row["index"]: State.update_tier_field(
                      index, "min_qty", v
                    ),
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                  ),
                  rx.el.input(
                    type="number",
                    placeholder="0.00",
                    default_value=row["price"].to_string(),
                    on_blur=lambda v, index=row["index"]: State.update_tier_field(
                      index, "price", v
                    ),
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                  ),
                  rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda _, index=row["index"]: State.remove_tier_row(
                      index
                    ),
                    class_name="p-2 text-red-600 hover:bg-red-50 rounded-md",
                  ),
                  class_name="grid grid-cols-1 sm:grid-cols-3 gap-2 items-center",
                ),
              ),
              class_name="flex flex-col gap-3",
            ),
            class_name="mt-4 space-y-3",
          ),
          rx.fragment(),
        ),
        rx.divider(color="slate-100"),
        rx.el.div(
          rx.el.button(
            "Cancelar",
            on_click=State.cancel_edit_product,
            class_name="px-4 py-2 rounded-md border text-slate-700 hover:bg-slate-50",
          ),
          rx.el.button(
            "Guardar Cambios",
            on_click=State.save_edited_product,
            disabled=State.is_loading,
            loading=State.is_loading,
            class_name="px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700",
          ),
          class_name="flex flex-col sm:flex-row sm:justify-end gap-3 mt-6",
        ),
        class_name="relative z-10 w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto",
      ),
      class_name="fixed inset-0 z-50 flex items-start sm:items-center justify-center px-4 py-6 overflow-hidden",
    ),
    rx.fragment(),
  )


def stock_details_modal() -> rx.Component:
  return rx.cond(
    State.stock_details_open,
    rx.el.div(
      rx.el.div(
        on_click=State.close_stock_details,
        class_name="fixed inset-0 bg-black/40 backdrop-blur-sm modal-overlay",
      ),
      rx.el.div(
        rx.el.div(
          rx.el.h3(
            State.stock_details_title,
            class_name="text-xl font-semibold text-slate-800",
          ),
          rx.el.button(
            rx.icon("x", class_name="h-4 w-4"),
            on_click=State.close_stock_details,
            class_name="p-2 rounded-full hover:bg-slate-100",
          ),
          class_name="flex items-start justify-between gap-4 mb-4",
        ),
        rx.divider(color="slate-100"),
        rx.cond(
          State.stock_details_mode == "variant",
          rx.el.table(
            rx.el.thead(
              rx.el.tr(
                rx.el.th("SKU", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Talla", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Color", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th(
                  "Stock", class_name=f"{TABLE_STYLES['header_cell']} text-center"
                ),
                class_name=TABLE_STYLES["header"],
              )
            ),
            rx.el.tbody(
              rx.foreach(
                State.selected_product_details,
                lambda row: rx.el.tr(
                  rx.el.td(row["sku"], class_name="py-2 px-3"),
                  rx.el.td(row["size"], class_name="py-2 px-3"),
                  rx.el.td(row["color"], class_name="py-2 px-3"),
                  rx.el.td(
                    row["stock"].to_string(),
                    class_name="py-2 px-3 text-center",
                  ),
                  class_name="border-b",
                ),
              )
            ),
            class_name="w-full text-sm",
          ),
          rx.cond(
            State.stock_details_mode == "batch",
            rx.el.table(
              rx.el.thead(
                rx.el.tr(
                  rx.el.th("Lote", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th("Vencimiento", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th(
                    "Stock",
                    class_name=f"{TABLE_STYLES['header_cell']} text-center",
                  ),
                  class_name=TABLE_STYLES["header"],
                )
              ),
              rx.el.tbody(
                rx.foreach(
                  State.selected_product_details,
                  lambda row: rx.el.tr(
                    rx.el.td(row["batch_number"], class_name="py-2 px-3"),
                    rx.el.td(row["expiration_date"], class_name="py-2 px-3"),
                    rx.el.td(
                      row["stock"].to_string(),
                      class_name="py-2 px-3 text-center",
                    ),
                    class_name="border-b",
                  ),
                )
              ),
              class_name="w-full text-sm",
            ),
            rx.el.p(
              "Producto único sin variantes.",
              class_name="text-sm text-slate-500",
            ),
          ),
        ),
        rx.el.div(
          rx.el.button(
            "Cerrar",
            on_click=State.close_stock_details,
            class_name="px-4 py-2 rounded-md border text-slate-700 hover:bg-slate-50",
          ),
          class_name="flex justify-end mt-6",
        ),
        class_name="relative z-10 w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto",
      ),
      class_name="fixed inset-0 z-50 flex items-start sm:items-center justify-center px-4 py-6 overflow-hidden",
    ),
    rx.fragment(),
  )


def inventory_adjustment_modal() -> rx.Component:
  return rx.cond(
    State.inventory_check_modal_open,
    rx.el.div(
      rx.el.div(
        on_click=State.close_inventory_check_modal,
        class_name="fixed inset-0 bg-black/40 backdrop-blur-sm modal-overlay",
      ),
      rx.el.div(
        rx.el.div(
          rx.el.h3(
            "Registro de Inventario Fisico",
            class_name="text-xl font-semibold text-slate-800",
          ),
          rx.el.button(
            rx.icon("x", class_name="h-4 w-4"),
            on_click=State.close_inventory_check_modal,
            class_name="p-2 rounded-full hover:bg-slate-100",
          ),
          class_name="flex items-start justify-between gap-4",
        ),
        rx.el.p(
          "Indique el resultado del inventario fisico y registre notas para sustentar cualquier re ajuste.",
          class_name="text-sm text-slate-600 mt-2",
        ),
        rx.divider(color="slate-100"),
        rx.el.div(
          rx.el.button(
            rx.icon("circle_check", class_name="h-4 w-4"),
            "Inventario Perfecto",
            on_click=lambda: State.set_inventory_check_status("perfecto"),
                        class_name=rx.cond(
                            State.inventory_check_status == "perfecto",
                            "h-10 px-4 rounded-md bg-indigo-600 text-white font-medium flex items-center justify-center gap-2",
                            "h-10 px-4 rounded-md border text-slate-700 hover:bg-slate-50 font-medium flex items-center justify-center gap-2",
                        ),
                    ),
                    rx.el.button(
                        rx.icon("triangle_alert", class_name="h-4 w-4"),
                        "Re Ajuste de Inventario",
                        on_click=lambda: State.set_inventory_check_status("ajuste"),
                        class_name=rx.cond(
                            State.inventory_check_status == "ajuste",
                            "h-10 px-4 rounded-md bg-amber-600 text-white font-medium flex items-center justify-center gap-2",
                            "h-10 px-4 rounded-md border text-slate-700 hover:bg-slate-50 font-medium flex items-center justify-center gap-2",
                        ),
                    ),
          class_name="grid grid-cols-1 md:grid-cols-2 gap-3",
        ),
        rx.cond(
          State.inventory_check_status == "ajuste",
          rx.el.div(
            rx.el.h4(
              "Productos con diferencias",
              class_name="text-sm font-semibold text-slate-700",
            ),
            rx.el.div(
              rx.el.label(
                "Buscar producto",
                class_name="text-sm font-medium text-slate-600",
              ),
              rx.el.div(
                rx.debounce_input(
                  rx.input(
                    id="inventory-adjustment-search",
                    placeholder="Ej: Gaseosa 500ml o código",
                    default_value=State.inventory_adjustment_item["description"],
                    on_change=lambda value: State.handle_inventory_adjustment_change(
                      "description", value
                    ),
                    on_blur=lambda e: State.process_inventory_adjustment_search_blur(e),
                    on_key_down=lambda k: State.handle_inventory_adjustment_search_enter(
                      k, "inventory-adjustment-search"
                    ),
                    auto_complete=False,
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                  ),
                  debounce_timeout=600,
                ),
                rx.cond(
                  State.inventory_adjustment_suggestions.length()
                  > 0,
                  rx.el.div(
                    rx.foreach(
                      State.inventory_adjustment_suggestions,
                      lambda suggestion: rx.el.button(
                        suggestion["label"],
                        on_click=lambda _,
                        suggestion=suggestion: State.select_inventory_adjustment_product(
                          suggestion
                        ),
                        class_name="w-full text-left px-3 py-2 hover:bg-slate-100",
                      ),
                    ),
                    class_name="absolute z-20 w-full mt-1 border rounded-md bg-white shadow-lg max-h-48 overflow-y-auto",
                  ),
                  rx.fragment(),
                ),
                class_name="relative",
              ),
              class_name="mt-3",
            ),
            rx.el.div(
              rx.el.div(
                rx.el.label(
                  "Codigo de barra",
                  class_name="text-xs text-slate-500 uppercase",
                ),
                rx.el.input(
                  value=State.inventory_adjustment_item["barcode"],
                  is_disabled=True,
                  class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-slate-100",
                ),
              ),
              rx.el.div(
                rx.el.label(
                  "Categoria",
                  class_name="text-xs text-slate-500 uppercase",
                ),
                rx.el.input(
                  value=State.inventory_adjustment_item["category"],
                  is_disabled=True,
                  class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-slate-100",
                ),
              ),
              rx.el.div(
                rx.el.label(
                  "Unidad",
                  class_name="text-xs text-slate-500 uppercase",
                ),
                rx.el.input(
                  value=State.inventory_adjustment_item["unit"],
                  is_disabled=True,
                  class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-slate-100",
                ),
              ),
              rx.el.div(
                rx.el.label(
                  "Stock disponible",
                  class_name="text-xs text-slate-500 uppercase",
                ),
                rx.el.input(
                  value=State.inventory_adjustment_item[
                    "current_stock"
                  ].to_string(),
                  is_disabled=True,
                  class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-slate-100",
                ),
              ),
              class_name="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4",
            ),
            rx.el.div(
              rx.el.div(
                rx.el.label(
                  "Cantidad a ajustar",
                  class_name="text-sm font-medium text-slate-700",
                ),
                rx.el.input(
                  type="number",
                  min="0",
                  step="0.01",
                  default_value=State.inventory_adjustment_item[
                    "adjust_quantity"
                  ].to_string(),
                  on_blur=lambda value: State.handle_inventory_adjustment_change(
                    "adjust_quantity", value
                  ),
                  class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                ),
              ),
              rx.el.div(
                rx.el.label(
                  "Motivo del ajuste",
                  class_name="text-sm font-medium text-slate-700",
                ),
                rx.el.textarea(
                  placeholder="Ej: Producto dañado, consumo interno, vencido, etc.",
                  default_value=State.inventory_adjustment_item["reason"],
                  on_blur=lambda value: State.handle_inventory_adjustment_change(
                    "reason", value
                  ),
                  class_name="w-full h-24 h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                ),
              ),
              class_name="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4",
            ),
            rx.el.button(
              rx.icon("plus", class_name="h-4 w-4"),
              "Agregar producto al ajuste",
              on_click=State.add_inventory_adjustment_item,
              class_name="mt-4 flex items-center justify-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 min-h-[42px]",
            ),
            rx.cond(
              State.inventory_adjustment_items.length() > 0,
              rx.el.div(
                rx.el.table(
                  rx.el.thead(
                    rx.el.tr(
                      rx.el.th(
                        "Producto",
                        class_name=TABLE_STYLES["header_cell"],
                      ),
                      rx.el.th(
                        "Unidad",
                        class_name=f"{TABLE_STYLES['header_cell']} text-center",
                      ),
                      rx.el.th(
                        "Stock",
                        class_name=f"{TABLE_STYLES['header_cell']} text-center",
                      ),
                      rx.el.th(
                        "Cantidad Ajuste",
                        class_name=f"{TABLE_STYLES['header_cell']} text-center",
                      ),
                      rx.el.th(
                        "Motivo",
                        class_name=TABLE_STYLES["header_cell"],
                      ),
                      rx.el.th(
                        "Accion",
                        class_name=f"{TABLE_STYLES['header_cell']} text-center",
                      ),
                      class_name=TABLE_STYLES["header"],
                    )
                  ),
                  rx.el.tbody(
                    rx.foreach(
                      State.inventory_adjustment_items,
                      lambda item: rx.el.tr(
                        rx.el.td(
                          item["description"],
                          class_name="py-2 px-3 font-medium",
                        ),
                        rx.el.td(
                          item["unit"],
                          class_name="py-2 px-3 text-center",
                        ),
                        rx.el.td(
                          item["current_stock"].to_string(),
                          class_name="py-2 px-3 text-center text-slate-500",
                        ),
                        rx.el.td(
                          item["adjust_quantity"].to_string(),
                          class_name="py-2 px-3 text-center text-red-600 font-semibold",
                        ),
                        rx.el.td(
                          rx.cond(
                            item["reason"] == "",
                            "-",
                            item["reason"],
                          ),
                          class_name="py-2 px-3 text-sm text-slate-600",
                        ),
                        rx.el.td(
                          rx.el.button(
                            rx.icon(
                              "trash-2",
                              class_name="h-4 w-4",
                            ),
                            on_click=lambda _,
                            temp_id=item[
                              "temp_id"
                            ]: State.remove_inventory_adjustment_item(
                              temp_id
                            ),
                            class_name="p-2 text-red-500 hover:bg-red-100 rounded-full",
                          ),
                          class_name="py-2 px-3 text-center",
                        ),
                        class_name="border-b",
                      ),
                    )
                  ),
                  class_name="w-full text-sm",
                ),
                class_name="mt-6 rounded-lg border overflow-x-auto",
              ),
              rx.el.p(
                "Aun no hay productos seleccionados para el ajuste.",
                class_name="mt-4 text-sm text-slate-500",
              ),
            ),
            rx.el.div(
              rx.el.label(
                "Notas generales del ajuste",
                class_name="text-sm font-semibold text-slate-700 mt-4",
              ),
              rx.el.textarea(
                placeholder="Detalles adicionales que respalden el ajuste realizado.",
                default_value=State.inventory_adjustment_notes,
                on_blur=lambda value: State.set_inventory_adjustment_notes(
                  value
                ),
                class_name="w-full mt-2 p-3 border rounded-lg h-32",
              ),
            ),
            class_name="mt-4 space-y-4",
          ),
          rx.fragment(),
        ),
        rx.el.div(
          rx.el.button(
            "Cancelar",
            on_click=State.close_inventory_check_modal,
            class_name="px-4 py-2 rounded-md border text-slate-700 hover:bg-slate-50",
          ),
          rx.el.button(
            rx.icon("save", class_name="h-4 w-4"),
            "Guardar Registro",
            on_click=State.submit_inventory_check,
            disabled=State.is_loading,
            loading=State.is_loading,
            class_name="flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700",
          ),
          class_name="flex flex-col gap-3 sm:flex-row sm:justify-end",
        ),
        class_name="relative z-10 w-full max-w-3xl rounded-xl bg-white p-4 sm:p-6 shadow-xl max-h-[90vh] overflow-y-auto space-y-4",
      ),
      class_name="fixed inset-0 z-50 flex items-start md:items-center justify-center px-4 py-6 overflow-hidden",
    ),
    rx.fragment(),
  )


def inventory_stat_card(title: str, value: rx.Var, value_class: str) -> rx.Component:
  return rx.el.div(
    rx.el.p(title, class_name="text-sm text-slate-500"),
    rx.el.p(
      value,
      class_name=f"text-3xl font-semibold tracking-tight {value_class}",
    ),
    class_name="bg-white rounded-xl border border-slate-100 shadow-sm p-4 sm:p-5",
  )


def inventario_page() -> rx.Component:
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
            class_name="text-lg font-semibold text-slate-700",
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
          on_change=State.update_new_category_name,
          class_name="flex-1 h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
        ),
        rx.el.button(
          rx.icon("plus", class_name="h-4 w-4"),
          "Agregar",
          on_click=State.add_category,
          class_name=(
            "inline-flex h-10 items-center justify-center gap-2 rounded-md "
            "bg-indigo-600 px-3.5 text-sm font-medium text-white hover:bg-indigo-700"
          ),
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
          class_name="text-xs text-slate-500 mt-2",
        ),
        rx.fragment(),
      ),
      class_name="bg-white p-4 sm:p-6 rounded-xl border border-slate-200 shadow-sm mb-6",
    ),
    rx.el.div(
      rx.el.div(
        rx.debounce_input(
          rx.input(
            placeholder="Buscar producto...",
            on_change=State.set_inventory_search_term,
            class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
          ),
          debounce_timeout=600,
        ),
        rx.el.div(
          rx.el.button(
            rx.icon("plus", class_name="h-4 w-4"),
            "Nuevo Producto",
            on_click=State.open_create_product_modal,
            class_name=(
              "inline-flex h-9 items-center justify-center gap-1.5 rounded-md "
              "bg-indigo-600 px-3.5 text-sm font-medium text-white shadow-sm "
              "transition-colors duration-150 hover:bg-indigo-700"
            ),
          ),
          rx.el.button(
            rx.icon("download", class_name="h-4 w-4"),
            "Exportar Inventario",
            on_click=State.export_inventory_to_excel,
            class_name=(
              "inline-flex h-9 items-center justify-center gap-1.5 rounded-md "
              "bg-emerald-600 px-3.5 text-sm font-medium text-white shadow-sm "
              "transition-colors duration-150 hover:bg-emerald-700"
            ),
          ),
          rx.el.button(
            rx.icon("clipboard_check", class_name="h-4 w-4"),
            "Registrar Fisico",
            on_click=State.open_inventory_check_modal,
            class_name=(
              "inline-flex h-9 items-center justify-center gap-1.5 rounded-md "
              "bg-amber-600 px-3.5 text-sm font-medium text-white shadow-sm "
              "transition-colors duration-150 hover:bg-amber-700"
            ),
          ),
          class_name="flex w-full flex-wrap items-center gap-2 md:w-auto md:justify-end",
        ),
        class_name="flex flex-col gap-4 md:flex-row md:items-center md:justify-between pb-4 border-b border-slate-200",
      ),
      rx.el.div(
        rx.el.table(
          rx.el.thead(
            rx.el.tr(
              rx.el.th("Codigo de Barra", class_name=TABLE_STYLES["header_cell"]),
              rx.el.th("Descripción", class_name=TABLE_STYLES["header_cell"]),
              rx.el.th("Categoría", class_name=TABLE_STYLES["header_cell"]),
              rx.el.th(
                "Stock", class_name=f"{TABLE_STYLES['header_cell']} text-center"
              ),
              rx.el.th(
                "Unidad", class_name=f"{TABLE_STYLES['header_cell']} text-center"
              ),
              rx.el.th(
                "Precio Compra", class_name=f"{TABLE_STYLES['header_cell']} text-right"
              ),
              rx.el.th(
                "Precio Venta", class_name=f"{TABLE_STYLES['header_cell']} text-right"
              ),
              rx.el.th(
                "Valor Total Stock", class_name=f"{TABLE_STYLES['header_cell']} text-right"
              ),
              rx.el.th(
                "Acciones", class_name=f"{TABLE_STYLES['header_cell']} text-center"
              ),
              class_name=TABLE_STYLES["header"],
            )
          ),
          rx.el.tbody(
            rx.foreach(
              State.inventory_paginated_list,
              lambda product: rx.el.tr(
                rx.el.td(
                  product["barcode"],
                  class_name="py-3 px-4",
                ),
                rx.el.td(
                  product["description"],
                  class_name="py-3 px-4 font-medium",
                ),
                rx.el.td(
                  product["category"],
                  class_name="py-3 px-4 text-left",
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
                  product["unit"], class_name="py-3 px-4 text-center"
                ),
                rx.el.td(
                  State.currency_symbol,
                  product["purchase_price"].to_string(),
                  class_name="py-3 px-4 text-right",
                ),
                rx.el.td(
                  State.currency_symbol,
                  product["sale_price"].to_string(),
                  class_name="py-3 px-4 text-right text-green-600",
                ),
                rx.el.td(
                  State.currency_symbol,
                  product["stock_total_display"],
                  class_name="py-3 px-4 text-right font-bold",
                ),
                rx.el.td(
                  rx.el.div(
                    rx.el.button(
                      rx.icon("pencil", class_name="h-4 w-4"),
                      on_click=lambda: State.open_edit_product(product),
                      class_name="p-2 text-blue-600 hover:bg-blue-50 rounded-full",
                      title="Editar",
                    ),
                    rx.el.button(
                      rx.icon("eye", class_name="h-4 w-4"),
                      on_click=lambda: State.open_stock_details(product),
                      class_name="p-2 text-slate-600 hover:bg-slate-100 rounded-full",
                      title="Ver Desglose",
                    ),
                    rx.cond(
                      product["is_variant"],
                      rx.fragment(),
                      rx.el.button(
                        rx.icon("trash-2", class_name="h-4 w-4"),
                        on_click=lambda: State.delete_product(product["id"]),
                        disabled=State.is_loading,
                        loading=State.is_loading,
                        class_name="p-2 text-red-600 hover:bg-red-50 rounded-full",
                        title="Eliminar",
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
          class_name="min-w-[980px]",
        ),
        class_name="w-full overflow-x-auto",
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
      class_name="bg-white p-4 sm:p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-4",
    ),
    inventory_adjustment_modal(),
    edit_product_modal(),
    stock_details_modal(),
    on_mount=State.refresh_inventory_cache,
    class_name="w-full flex flex-col gap-6",
  )
  return permission_guard(
    has_permission=State.can_view_inventario,
    content=content,
    redirect_message="Acceso denegado a Inventario",
  )

