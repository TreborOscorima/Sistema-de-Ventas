import reflex as rx
from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  CARD_STYLES,
  INPUT_STYLES,
  TYPOGRAPHY,
  BADGE_STYLES,
  SPACING,
  SELECT_STYLES,
  RADIUS,
  SHADOWS,
  TRANSITIONS,
  FOCUS_RING,
  TABLE_STYLES,
  page_title,
  pagination_controls,
  permission_guard,
  select_filter,
  modal_container,
  toggle_switch,
)


def import_modal() -> rx.Component:
  """Modal de importación masiva de productos desde CSV/Excel."""
  return modal_container(
    is_open=State.import_modal_open,
    on_close=State.close_import_modal,
    title="Importar productos",
    description="Suba un archivo CSV o Excel (.xlsx) con los productos a importar.",
    max_width="max-w-3xl",
    children=[
      # Zona de upload
      rx.cond(
        State.import_file_name == "",
        rx.upload(
          rx.el.div(
            rx.icon("cloud-upload", class_name="h-10 w-10 text-slate-400 mx-auto mb-2"),
            rx.el.p(
              "Arrastre un archivo aquí o haga clic para seleccionar",
              class_name="text-sm text-slate-500 text-center",
            ),
            rx.el.p(
              "Formatos: .csv, .xlsx",
              class_name="text-xs text-slate-400 text-center mt-1",
            ),
            class_name="flex flex-col items-center justify-center py-8",
          ),
          id="import_upload",
          accept={".csv": ["text/csv"], ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]},
          max_files=1,
          border="2px dashed #cbd5e1",
          border_radius="0.75rem",
          class_name="cursor-pointer hover:border-indigo-400 transition-colors",
          on_drop=State.handle_import_upload(rx.upload_files(upload_id="import_upload")),  # type: ignore
        ),
        # Archivo seleccionado - mostrar nombre
        rx.el.div(
          rx.el.div(
            rx.icon("file-check", class_name="h-5 w-5 text-emerald-600"),
            rx.el.span(State.import_file_name, class_name="text-sm font-medium text-slate-700"),
            rx.el.button(
              rx.icon("x", class_name="h-4 w-4"),
              on_click=[State.close_import_modal, State.open_import_modal],
              class_name="ml-auto text-slate-400 hover:text-red-500",
              title="Cambiar archivo",
            ),
            class_name="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg",
          ),
        ),
      ),
      # Errores
      rx.cond(
        State.import_errors.length() > 0,
        rx.el.div(
          rx.el.div(
            rx.icon("triangle-alert", class_name="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5"),
            rx.el.div(
              rx.foreach(
                State.import_errors,
                lambda err: rx.el.p(err, class_name="text-xs text-amber-700"),
              ),
            ),
            class_name="flex gap-2",
          ),
          class_name="bg-amber-50 border border-amber-200 rounded-lg p-3 max-h-24 overflow-y-auto",
        ),
        rx.fragment(),
      ),
      # Estadísticas de preview
      rx.cond(
        State.import_preview_rows.length() > 0,
        rx.el.div(
          rx.el.div(
            rx.el.div(
              rx.el.span(State.import_stats["total"].to_string(), class_name="text-lg font-bold text-slate-800"),
              rx.el.span("Total filas", class_name="text-xs text-slate-500"),
              class_name="flex flex-col items-center",
            ),
            rx.el.div(
              rx.el.span(State.import_stats["new"].to_string(), class_name="text-lg font-bold text-emerald-600"),
              rx.el.span("Nuevos", class_name="text-xs text-slate-500"),
              class_name="flex flex-col items-center",
            ),
            rx.el.div(
              rx.el.span(State.import_stats["updated"].to_string(), class_name="text-lg font-bold text-blue-600"),
              rx.el.span("Actualizar", class_name="text-xs text-slate-500"),
              class_name="flex flex-col items-center",
            ),
            rx.el.div(
              rx.el.span(State.import_stats["errors"].to_string(), class_name="text-lg font-bold text-red-600"),
              rx.el.span("Errores", class_name="text-xs text-slate-500"),
              class_name="flex flex-col items-center",
            ),
            class_name="grid grid-cols-4 gap-4 text-center",
          ),
          class_name="bg-slate-50 border border-slate-200 rounded-lg p-3",
        ),
        rx.fragment(),
      ),
      # Tabla preview
      rx.cond(
        State.import_preview_rows.length() > 0,
        rx.el.div(
          rx.el.h4("Vista previa", class_name=TYPOGRAPHY["card_title"] + " mb-2"),
          rx.el.div(
            rx.el.table(
              rx.el.thead(
                rx.el.tr(
                  rx.el.th("Estado", scope="col", class_name=TABLE_STYLES["header_cell"] + " w-20"),
                  rx.el.th("Código", scope="col", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th("Descripción", scope="col", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th("Cat.", scope="col", class_name=TABLE_STYLES["header_cell"] + " hidden sm:table-cell"),
                  rx.el.th("Stock", scope="col", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                  rx.el.th("P.Venta", scope="col", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                  class_name=TABLE_STYLES["header"],
                ),
              ),
              rx.el.tbody(
                rx.foreach(
                  State.import_preview_rows,
                  lambda row: rx.el.tr(
                    rx.el.td(
                      rx.el.span(
                        row["status"],
                        class_name=rx.cond(
                          row["status"] == "Nuevo",
                          "text-xs px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-medium",
                          "text-xs px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium",
                        ),
                      ),
                      class_name="py-2 px-3",
                    ),
                    rx.el.td(row["barcode"], class_name="py-2 px-3 text-xs font-mono text-slate-600"),
                    rx.el.td(row["description"], class_name="py-2 px-3 text-sm truncate max-w-[200px]"),
                    rx.el.td(row["category"], class_name="py-2 px-3 text-xs text-slate-500 hidden sm:table-cell"),
                    rx.el.td(row["stock"].to_string(), class_name="py-2 px-3 text-sm text-right"),
                    rx.el.td(row["sale_price"].to_string(), class_name="py-2 px-3 text-sm text-right font-mono"),
                    class_name="border-b border-slate-100",
                  ),
                ),
              ),
              class_name="min-w-full text-sm",
            ),
            class_name="max-h-52 overflow-y-auto border rounded-lg",
          ),
        ),
        rx.fragment(),
      ),
      # Columnas requeridas info
      rx.cond(
        State.import_file_name == "",
        rx.el.div(
          rx.el.h4("Columnas esperadas", class_name="text-xs font-semibold text-slate-600 mb-1"),
          rx.el.p(
            "codigo/barcode, descripcion, categoria, stock, unidad, costo/precio compra, precio/precio venta",
            class_name="text-xs text-slate-500",
          ),
          class_name="bg-slate-50 border border-slate-200 rounded-lg p-3",
        ),
        rx.fragment(),
      ),
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_import_modal,
        class_name=BUTTON_STYLES["ghost"],
      ),
      rx.el.button(
        rx.cond(
          State.import_processing,
          rx.fragment(rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"), "Importando..."),
          rx.fragment(rx.icon("check", class_name="h-4 w-4"), "Confirmar importación"),
        ),
        on_click=State.confirm_import,
        disabled=rx.cond(State.import_preview_rows.length() == 0, True, State.import_processing),
        class_name=BUTTON_STYLES["primary_sm"],
      ),
      class_name="flex items-center justify-end gap-3",
    ),
  )


def edit_product_modal() -> rx.Component:
  """Modal de edición de producto."""
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
            class_name=TYPOGRAPHY["section_title"],
          ),
          rx.el.button(
            rx.icon("x", class_name="h-4 w-4"),
            on_click=State.cancel_edit_product,
            title="Cerrar",
            aria_label="Cerrar",
            class_name=BUTTON_STYLES["icon_ghost"],
          ),
          class_name="flex items-start justify-between gap-4 mb-4",
        ),
        rx.divider(color="slate-100"),
        rx.el.div(
          rx.el.div(
            rx.el.label("Código de Barra", class_name=f"block {TYPOGRAPHY['label']}"),
            rx.el.input(
              default_value=State.editing_product["barcode"],
              on_blur=lambda v: State.handle_edit_product_change("barcode", v),
              class_name=INPUT_STYLES["default"],
              debounce_timeout=600,
            ),
          ),
          rx.el.div(
            rx.el.label("Descripción", class_name=f"block {TYPOGRAPHY['label']}"),
            rx.el.input(
              default_value=State.editing_product["description"],
              on_blur=lambda v: State.handle_edit_product_change("description", v),
              class_name=INPUT_STYLES["default"],
              debounce_timeout=600,
            ),
          ),
          rx.el.div(
            rx.el.label("Categoría", class_name=f"block {TYPOGRAPHY['label']}"),
            rx.el.select(
              rx.foreach(
                State.categories,
                lambda cat: rx.el.option(cat, value=cat)
              ),
              default_value=State.editing_product["category"],
              on_change=lambda v: State.handle_edit_product_change("category", v),
              class_name=SELECT_STYLES["default"],
            ),
          ),
          rx.el.div(
            rx.cond(
              State.show_variants,
              rx.el.div(
                rx.el.label(
                  "Stock Total (calculado)",
                  class_name=f"block {TYPOGRAPHY['label']}",
                ),
                rx.el.input(
                  type="number",
                  value=State.variants_stock_total.to_string(),
                  is_disabled=True,
                  class_name=INPUT_STYLES["disabled"],
                ),
              ),
              rx.el.div(
                rx.el.label(
                  "Stock",
                  class_name=f"block {TYPOGRAPHY['label']}",
                ),
                rx.el.input(
                  type="number",
                  default_value=State.editing_product["stock"].to_string(),
                  on_blur=lambda v: State.handle_edit_product_change("stock", v),
                  class_name=INPUT_STYLES["default"],
                ),
              ),
            )
          ),
          rx.el.div(
            rx.el.label("Unidad", class_name=f"block {TYPOGRAPHY['label']}"),
            rx.el.select(
              rx.el.option("Unidad", value="Unidad"),
              rx.el.option("Kg", value="Kg"),
              rx.el.option("Lt", value="Lt"),
              rx.el.option("Paquete", value="Paquete"),
              rx.el.option("Caja", value="Caja"),
              default_value=State.editing_product["unit"],
              on_change=lambda v: State.handle_edit_product_change("unit", v),
              class_name=SELECT_STYLES["default"],
            ),
          ),
          rx.el.div(
            rx.el.label("Precio Compra", class_name=f"block {TYPOGRAPHY['label']}"),
            rx.el.input(
              type="number",
              default_value=State.editing_product["purchase_price"].to_string(),
              on_blur=lambda v: State.handle_edit_product_change("purchase_price", v),
              class_name=INPUT_STYLES["default"],
            ),
          ),
          rx.el.div(
            rx.el.label("Precio Venta", class_name=f"block {TYPOGRAPHY['label']}"),
            rx.el.input(
              type="number",
              default_value=State.editing_product["sale_price"].to_string(),
              on_blur=lambda v: State.handle_edit_product_change("sale_price", v),
              class_name=INPUT_STYLES["default"],
            ),
          ),
          class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        rx.el.div(
          rx.el.div(
            rx.el.label(
              "Tiene Variantes",
              class_name=TYPOGRAPHY["label"],
            ),
            rx.el.div(
              toggle_switch(
                checked=State.show_variants,
                on_change=State.set_show_variants,
              ),
              rx.el.span(
                "Tallas/colores con stock individual",
                class_name=TYPOGRAPHY["caption"],
              ),
              class_name="flex items-center gap-2",
            ),
            class_name="flex flex-col gap-2",
          ),
          rx.el.div(
            rx.el.label(
              "Precios Mayoristas",
              class_name=TYPOGRAPHY["label"],
            ),
            rx.el.div(
              toggle_switch(
                checked=State.show_wholesale,
                on_change=State.set_show_wholesale,
              ),
              rx.el.span(
                "Escalas por cantidad mínima",
                class_name=TYPOGRAPHY["caption"],
              ),
              class_name="flex items-center gap-2",
            ),
            class_name="flex flex-col gap-2",
          ),
          rx.el.div(
            rx.el.label(
              "Lotes con Vencimiento",
              class_name=TYPOGRAPHY["label"],
            ),
            rx.el.div(
              toggle_switch(
                checked=State.show_batches,
                on_change=State.set_show_batches,
              ),
              rx.el.span(
                "Farmacia / Alimentos (FEFO)",
                class_name=TYPOGRAPHY["caption"],
              ),
              class_name="flex items-center gap-2",
            ),
            class_name="flex flex-col gap-2",
          ),
          rx.el.div(
            rx.el.label(
              "Atributos Dinámicos",
              class_name=TYPOGRAPHY["label"],
            ),
            rx.el.div(
              toggle_switch(
                checked=State.show_attributes,
                on_change=State.set_show_attributes,
              ),
              rx.el.span(
                "Material, calibre, principio activo, etc.",
                class_name=TYPOGRAPHY["caption"],
              ),
              class_name="flex items-center gap-2",
            ),
            class_name="flex flex-col gap-2",
          ),
          rx.el.div(
            rx.el.label(
              "Kit / Combo",
              class_name=TYPOGRAPHY["label"],
            ),
            rx.el.div(
              toggle_switch(
                checked=State.show_kit_components,
                on_change=State.set_show_kit_components,
              ),
              rx.el.span(
                "Producto compuesto por otros productos",
                class_name=TYPOGRAPHY["caption"],
              ),
              class_name="flex items-center gap-2",
            ),
            class_name="flex flex-col gap-2",
          ),
          class_name="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4",
        ),
        # Modal de confirmación para desactivar mayoreo
        rx.cond(
          State.confirm_disable_wholesale,
          rx.el.div(
            rx.el.div(
              rx.el.div(
                rx.icon("triangle-alert", class_name="h-5 w-5 text-amber-500"),
                rx.el.h4(
                  "¿Desactivar precios mayoristas?",
                  class_name="text-sm font-semibold text-slate-800",
                ),
                class_name="flex items-center gap-2",
              ),
              rx.el.p(
                "Se eliminarán todas las escalas de precio configuradas para este producto. Esta acción no se puede deshacer.",
                class_name=f"{TYPOGRAPHY['caption']} mt-2",
              ),
              rx.el.div(
                rx.el.button(
                  "Cancelar",
                  on_click=State.confirm_disable_wholesale_no,
                  class_name=BUTTON_STYLES["secondary_sm"],
                ),
                rx.el.button(
                  "Sí, desactivar",
                  on_click=State.confirm_disable_wholesale_yes,
                  class_name=BUTTON_STYLES["danger_sm"],
                ),
                class_name="flex justify-end gap-2 mt-3",
              ),
              class_name="p-4 bg-amber-50 border border-amber-200 rounded-lg",
            ),
            class_name="mt-3",
          ),
          rx.fragment(),
        ),
        rx.cond(
          State.show_variants,
          rx.el.div(
            rx.el.div(
              rx.el.h4(
                "Variantes",
                class_name=TYPOGRAPHY["label"],
              ),
              rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                "Agregar variante",
                on_click=State.add_variant_row,
                class_name=BUTTON_STYLES["primary_sm"],
              ),
              class_name="flex items-center justify-between",
            ),
            rx.el.div(
              rx.el.div(
                rx.el.span(
                  "SKU", class_name=f"{TYPOGRAPHY['caption']} uppercase sm:col-span-2"
                ),
                rx.el.span("Talla", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
                rx.el.span("Color", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
                rx.el.span("Stock", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
                rx.el.span("Acción", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
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
                    class_name=f"{INPUT_STYLES['default']} sm:col-span-2",
                  ),
                  rx.el.input(
                    placeholder="Talla",
                    default_value=row["size"],
                    on_blur=lambda v, index=row["index"]: State.update_variant_field(
                      index, "size", v
                    ),
                    class_name=INPUT_STYLES["default"],
                  ),
                  rx.el.input(
                    placeholder="Color",
                    default_value=row["color"],
                    on_blur=lambda v, index=row["index"]: State.update_variant_field(
                      index, "color", v
                    ),
                    class_name=INPUT_STYLES["default"],
                  ),
                  rx.el.input(
                    type="number",
                    placeholder="0",
                    default_value=row["stock"].to_string(),
                    on_blur=lambda v, index=row["index"]: State.update_variant_field(
                      index, "stock", v
                    ),
                    class_name=INPUT_STYLES["default"],
                  ),
                  rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda _, index=row["index"]: State.remove_variant_row(
                      index
                    ),
                    title="Eliminar variante",
                    aria_label="Eliminar variante",
                    class_name=BUTTON_STYLES["icon_danger"],
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
                class_name=TYPOGRAPHY["label"],
              ),
              rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                "Agregar regla",
                on_click=State.add_tier_row,
                class_name=BUTTON_STYLES["primary_sm"],
              ),
              class_name="flex items-center justify-between",
            ),
            rx.el.div(
              rx.el.div(
                rx.el.span(
                  "Cantidad mínima", class_name=f"{TYPOGRAPHY['caption']} uppercase"
                ),
                rx.el.span(
                  "Precio unitario", class_name=f"{TYPOGRAPHY['caption']} uppercase"
                ),
                rx.el.span("Acción", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
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
                    class_name=INPUT_STYLES["default"],
                  ),
                  rx.el.input(
                    type="number",
                    placeholder="0.00",
                    default_value=row["price"].to_string(),
                    on_blur=lambda v, index=row["index"]: State.update_tier_field(
                      index, "price", v
                    ),
                    class_name=INPUT_STYLES["default"],
                  ),
                  rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda _, index=row["index"]: State.remove_tier_row(
                      index
                    ),
                    title="Eliminar regla",
                    aria_label="Eliminar regla",
                    class_name=BUTTON_STYLES["icon_danger"],
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
        # ─── Sección de lotes (batches) ───
        rx.cond(
          State.show_batches,
          rx.el.div(
            rx.el.div(
              rx.el.h4(
                "Lotes con vencimiento",
                class_name=TYPOGRAPHY["label"],
              ),
              rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                "Agregar lote",
                on_click=State.add_batch_row,
                class_name=BUTTON_STYLES["primary_sm"],
              ),
              class_name="flex items-center justify-between",
            ),
            rx.el.div(
              rx.el.div(
                rx.el.span(
                  "N° Lote", class_name=f"{TYPOGRAPHY['caption']} uppercase sm:col-span-2"
                ),
                rx.el.span(
                  "Vencimiento", class_name=f"{TYPOGRAPHY['caption']} uppercase sm:col-span-2"
                ),
                rx.el.span("Stock", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
                rx.el.span("Acción", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
                class_name="hidden sm:grid sm:grid-cols-6 gap-2",
              ),
              rx.foreach(
                State.batch_rows,
                lambda row: rx.el.div(
                  rx.el.input(
                    placeholder="LOT-2026-001",
                    default_value=row["batch_number"],
                    on_blur=lambda v, index=row["index"]: State.update_batch_field(
                      index, "batch_number", v
                    ),
                    class_name=f"{INPUT_STYLES['default']} sm:col-span-2",
                  ),
                  rx.el.input(
                    type="date",
                    default_value=row["expiration_date"],
                    on_blur=lambda v, index=row["index"]: State.update_batch_field(
                      index, "expiration_date", v
                    ),
                    class_name=f"{INPUT_STYLES['default']} sm:col-span-2",
                  ),
                  rx.el.input(
                    type="number",
                    placeholder="0",
                    default_value=row["stock"].to_string(),
                    on_blur=lambda v, index=row["index"]: State.update_batch_field(
                      index, "stock", v
                    ),
                    class_name=INPUT_STYLES["default"],
                  ),
                  rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda _, index=row["index"]: State.remove_batch_row(
                      index
                    ),
                    title="Eliminar lote",
                    aria_label="Eliminar lote",
                    class_name=BUTTON_STYLES["icon_danger"],
                  ),
                  class_name="grid grid-cols-1 sm:grid-cols-6 gap-2 items-center",
                ),
              ),
              class_name="flex flex-col gap-3",
            ),
            rx.el.p(
              "El sistema consume lotes con FEFO (First Expire First Out) automáticamente.",
              class_name=f"{TYPOGRAPHY['caption']} mt-2",
            ),
            class_name="mt-4 space-y-3",
          ),
          rx.fragment(),
        ),
        # ─── Sección de atributos dinámicos (EAV) ───
        rx.cond(
          State.show_attributes,
          rx.el.div(
            rx.el.div(
              rx.el.h4(
                "Atributos dinámicos",
                class_name=TYPOGRAPHY["label"],
              ),
              rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                "Agregar atributo",
                on_click=State.add_attribute_row,
                class_name=BUTTON_STYLES["primary_sm"],
              ),
              class_name="flex items-center justify-between",
            ),
            rx.el.div(
              rx.el.div(
                rx.el.span(
                  "Nombre", class_name=f"{TYPOGRAPHY['caption']} uppercase sm:col-span-2"
                ),
                rx.el.span(
                  "Valor", class_name=f"{TYPOGRAPHY['caption']} uppercase sm:col-span-3"
                ),
                rx.el.span("Acción", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
                class_name="hidden sm:grid sm:grid-cols-6 gap-2",
              ),
              rx.foreach(
                State.attribute_rows,
                lambda row: rx.el.div(
                  rx.el.input(
                    placeholder="material",
                    default_value=row["name"],
                    on_blur=lambda v, index=row["index"]: State.update_attribute_field(
                      index, "name", v
                    ),
                    class_name=f"{INPUT_STYLES['default']} sm:col-span-2",
                  ),
                  rx.el.input(
                    placeholder="acero inoxidable",
                    default_value=row["value"],
                    on_blur=lambda v, index=row["index"]: State.update_attribute_field(
                      index, "value", v
                    ),
                    class_name=f"{INPUT_STYLES['default']} sm:col-span-3",
                  ),
                  rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda _, index=row["index"]: State.remove_attribute_row(
                      index
                    ),
                    title="Eliminar atributo",
                    aria_label="Eliminar atributo",
                    class_name=BUTTON_STYLES["icon_danger"],
                  ),
                  class_name="grid grid-cols-1 sm:grid-cols-6 gap-2 items-center",
                ),
              ),
              class_name="flex flex-col gap-3",
            ),
            rx.el.p(
              "Ej: ferretería (material, calibre), farmacia (principio_activo, dosaje), juguetería (edad_minima).",
              class_name=f"{TYPOGRAPHY['caption']} mt-2",
            ),
            class_name="mt-4 space-y-3",
          ),
          rx.fragment(),
        ),
        # ─── Sección de componentes de kit ───
        rx.cond(
          State.show_kit_components,
          rx.el.div(
            rx.el.div(
              rx.el.h4(
                "Componentes del kit",
                class_name=TYPOGRAPHY["label"],
              ),
              rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                "Agregar componente",
                on_click=State.add_kit_component_row,
                class_name=BUTTON_STYLES["primary_sm"],
              ),
              class_name="flex items-center justify-between",
            ),
            rx.el.div(
              rx.el.div(
                rx.el.span(
                  "Código", class_name=f"{TYPOGRAPHY['caption']} uppercase sm:col-span-2"
                ),
                rx.el.span(
                  "Producto", class_name=f"{TYPOGRAPHY['caption']} uppercase sm:col-span-2"
                ),
                rx.el.span(
                  "Cantidad", class_name=f"{TYPOGRAPHY['caption']} uppercase"
                ),
                rx.el.span("Acción", class_name=f"{TYPOGRAPHY['caption']} uppercase"),
                class_name="hidden sm:grid sm:grid-cols-6 gap-2",
              ),
              rx.foreach(
                State.kit_component_rows,
                lambda row: rx.el.div(
                  rx.el.input(
                    placeholder="Código de barras",
                    default_value=row["component_barcode"],
                    on_blur=lambda v, index=row["index"]: State.resolve_kit_component(
                      index, v
                    ),
                    class_name=f"{INPUT_STYLES['default']} sm:col-span-2",
                  ),
                  rx.el.span(
                    rx.cond(
                      row["component_name"] != "",
                      row["component_name"],
                      "Sin asignar",
                    ),
                    class_name="text-sm text-slate-600 sm:col-span-2 truncate py-2",
                  ),
                  rx.el.input(
                    type="number",
                    placeholder="1",
                    min="0.0001",
                    step="1",
                    default_value=row["quantity"].to_string(),
                    on_blur=lambda v, index=row["index"]: State.update_kit_component_field(
                      index, "quantity", v
                    ),
                    class_name=INPUT_STYLES["default"],
                  ),
                  rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda _, index=row["index"]: State.remove_kit_component_row(
                      index
                    ),
                    title="Eliminar componente",
                    aria_label="Eliminar componente",
                    class_name=BUTTON_STYLES["icon_danger"],
                  ),
                  class_name="grid grid-cols-1 sm:grid-cols-6 gap-2 items-center",
                ),
              ),
              class_name="flex flex-col gap-3",
            ),
            rx.el.p(
              "Al vender este kit, se descuenta stock de cada componente individual.",
              class_name=f"{TYPOGRAPHY['caption']} mt-2",
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
            class_name=BUTTON_STYLES["secondary"],
          ),
          rx.el.button(
            "Guardar Cambios",
            on_click=State.save_edited_product,
            disabled=State.is_loading,
            loading=State.is_loading,
            class_name=BUTTON_STYLES["primary"],
          ),
          class_name="flex flex-col sm:flex-row sm:justify-end gap-3 mt-6",
        ),
        class_name="relative z-10 w-full max-w-2xl rounded-xl bg-white p-4 sm:p-6 shadow-xl max-h-[90vh] overflow-y-auto",
      ),
      class_name="fixed inset-0 z-50 flex items-start sm:items-center justify-center px-4 py-6 overflow-hidden",
    ),
    rx.fragment(),
  )


def stock_details_modal() -> rx.Component:
  """Modal de detalles de stock (variantes, lotes, precios)."""
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
            title="Cerrar",
            aria_label="Cerrar",
            class_name=BUTTON_STYLES["icon_ghost"],
          ),
          class_name="flex items-start justify-between gap-4 mb-4",
        ),
        rx.divider(color="slate-100"),
        rx.cond(
          State.stock_details_mode == "variant",
          rx.el.table(
            rx.el.thead(
              rx.el.tr(
                rx.el.th("SKU", scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Talla", scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Color", scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th(
                  "Stock", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center"
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
                  rx.el.th("Lote", scope="col", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th("Vencimiento", scope="col", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th(
                    "Stock",
                    scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center",
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
              class_name=TYPOGRAPHY["body_secondary"],
            ),
          ),
        ),
        rx.el.div(
          rx.el.button(
            "Cerrar",
            on_click=State.close_stock_details,
            class_name=BUTTON_STYLES["secondary"],
          ),
          class_name="flex justify-end mt-6",
        ),
        class_name="relative z-10 w-full max-w-2xl rounded-xl bg-white p-4 sm:p-6 shadow-xl max-h-[90vh] overflow-y-auto",
      ),
      class_name="fixed inset-0 z-50 flex items-start sm:items-center justify-center px-4 py-6 overflow-hidden",
    ),
    rx.fragment(),
  )


def inventory_adjustment_modal() -> rx.Component:
  """Modal de ajuste manual de inventario."""
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
            title="Cerrar",
            aria_label="Cerrar",
            class_name=BUTTON_STYLES["icon_ghost"],
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
            rx.icon("circle-check", class_name="h-4 w-4"),
            "Inventario Perfecto",
            on_click=lambda: State.set_inventory_check_status("perfecto"),
                        class_name=rx.cond(
                            State.inventory_check_status == "perfecto",
                            "h-10 px-4 rounded-md bg-indigo-600 text-white font-medium flex items-center justify-center gap-2",
                            "h-10 px-4 rounded-md border text-slate-700 hover:bg-slate-50 font-medium flex items-center justify-center gap-2",
                        ),
                    ),
                    rx.el.button(
                        rx.icon("triangle-alert", class_name="h-4 w-4"),
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
              class_name=TYPOGRAPHY["label"],
            ),
            rx.el.div(
              rx.el.label(
                "Buscar producto",
                class_name=TYPOGRAPHY["label_secondary"],
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
                    class_name=INPUT_STYLES["default"],
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
                  class_name=f"{TYPOGRAPHY['caption']} uppercase",
                ),
                rx.el.input(
                  value=State.inventory_adjustment_item["barcode"],
                  is_disabled=True,
                  class_name=INPUT_STYLES["disabled"],
                ),
              ),
              rx.el.div(
                rx.el.label(
                  "Categoria",
                  class_name=f"{TYPOGRAPHY['caption']} uppercase",
                ),
                rx.el.input(
                  value=State.inventory_adjustment_item["category"],
                  is_disabled=True,
                  class_name=INPUT_STYLES["disabled"],
                ),
              ),
              rx.el.div(
                rx.el.label(
                  "Unidad",
                  class_name=f"{TYPOGRAPHY['caption']} uppercase",
                ),
                rx.el.input(
                  value=State.inventory_adjustment_item["unit"],
                  is_disabled=True,
                  class_name=INPUT_STYLES["disabled"],
                ),
              ),
              rx.el.div(
                rx.el.label(
                  "Stock disponible",
                  class_name=f"{TYPOGRAPHY['caption']} uppercase",
                ),
                rx.el.input(
                  value=State.inventory_adjustment_item[
                    "current_stock"
                  ].to_string(),
                  is_disabled=True,
                  class_name=INPUT_STYLES["disabled"],
                ),
              ),
              class_name="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4",
            ),
            rx.el.div(
              rx.el.div(
                rx.el.label(
                  "Cantidad a ajustar",
                  class_name=TYPOGRAPHY["label"],
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
                  class_name=INPUT_STYLES["default"],
                ),
              ),
              rx.el.div(
                rx.el.label(
                  "Motivo del ajuste",
                  class_name=TYPOGRAPHY["label"],
                ),
                rx.el.textarea(
                  placeholder="Ej: Producto dañado, consumo interno, vencido, etc.",
                  default_value=State.inventory_adjustment_item["reason"],
                  on_blur=lambda value: State.handle_inventory_adjustment_change(
                    "reason", value
                  ),
                  class_name=f"{INPUT_STYLES['default']} h-24",
                ),
              ),
              class_name="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4",
            ),
            rx.el.button(
              rx.icon("plus", class_name="h-4 w-4"),
              "Agregar producto al ajuste",
              on_click=State.add_inventory_adjustment_item,
              class_name=f"{BUTTON_STYLES['primary']} mt-4 w-full",
            ),
            rx.cond(
              State.inventory_adjustment_items.length() > 0,
              rx.el.div(
                rx.el.table(
                  rx.el.thead(
                    rx.el.tr(
                      rx.el.th(
                        "Producto",
                        scope="col", class_name=TABLE_STYLES["header_cell"],
                      ),
                      rx.el.th(
                        "Unidad",
                        scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center",
                      ),
                      rx.el.th(
                        "Stock",
                        scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center",
                      ),
                      rx.el.th(
                        "Cantidad Ajuste",
                        scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center",
                      ),
                      rx.el.th(
                        "Motivo",
                        scope="col", class_name=TABLE_STYLES["header_cell"],
                      ),
                      rx.el.th(
                        "Accion",
                        scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center",
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
                            title="Eliminar",
                            aria_label="Eliminar",
                            class_name=BUTTON_STYLES["icon_danger"],
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
                class_name=f"mt-4 {TYPOGRAPHY['body_secondary']}",
              ),
            ),
            rx.el.div(
              rx.el.label(
                "Notas generales del ajuste",
                class_name=f"{TYPOGRAPHY['label']} mt-4",
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
            class_name=BUTTON_STYLES["secondary"],
          ),
          rx.el.button(
            rx.icon("save", class_name="h-4 w-4"),
            "Guardar Registro",
            on_click=State.submit_inventory_check,
            disabled=State.is_loading,
            loading=State.is_loading,
            class_name=BUTTON_STYLES["primary"],
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
    rx.el.p(title, class_name=TYPOGRAPHY["body_secondary"]),
    rx.el.p(
      value,
      class_name=f"text-3xl font-semibold tracking-tight {value_class}",
    ),
    class_name=CARD_STYLES["compact"],
  )


# ════════════════════════════════════════════════════════════
# CARD MÓVIL (vista responsiva para pantallas pequeñas)
# ════════════════════════════════════════════════════════════

def _product_card(product: rx.Var) -> rx.Component:
    """Card de producto para vista móvil."""
    return rx.el.div(
        # Header: Nombre + Estado activo/inactivo
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    product["description"],
                    class_name="font-medium text-slate-900 text-sm",
                ),
                rx.el.span(
                    product["category"],
                    class_name=TYPOGRAPHY["caption"],
                ),
                class_name="flex flex-col",
            ),
            rx.cond(
                product["is_active"],
                rx.el.span(
                    "Activo",
                    class_name=BADGE_STYLES["success"],
                ),
                rx.el.span(
                    "Inactivo",
                    class_name=BADGE_STYLES["danger"],
                ),
            ),
            class_name="flex items-start justify-between gap-2",
        ),
        # Body: Stock + Precio
        rx.el.div(
            rx.el.div(
                rx.el.span("Stock", class_name=TYPOGRAPHY["caption"]),
                rx.el.div(
                    rx.el.span(
                        product["stock"].to_string(),
                        class_name=rx.cond(
                            product["stock_is_low"],
                            "font-bold text-red-600",
                            rx.cond(
                                product["stock_is_medium"],
                                "font-semibold text-amber-600",
                                "font-semibold text-green-600",
                            ),
                        ),
                    ),
                    rx.cond(
                        product["stock_is_low"],
                        rx.el.span(
                            "Bajo",
                            class_name="ml-1.5 text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-800",
                        ),
                        rx.cond(
                            product["stock_is_medium"],
                            rx.el.span(
                                "Moderado",
                                class_name="ml-1.5 text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800",
                            ),
                            rx.fragment(),
                        ),
                    ),
                    class_name="flex items-center",
                ),
                class_name="flex flex-col gap-0.5",
            ),
            rx.el.div(
                rx.el.span("Precio Venta", class_name=TYPOGRAPHY["caption"]),
                rx.el.span(
                    State.currency_symbol, " ", product["sale_price"].to_string(),
                    class_name="font-semibold tabular-nums text-green-600",
                ),
                class_name="flex flex-col gap-0.5 text-right",
            ),
            class_name="flex items-end justify-between mt-2",
        ),
        # Footer: Acciones
        rx.el.div(
            rx.el.button(
                rx.icon("pencil", class_name="h-4 w-4"),
                " Editar",
                on_click=lambda: State.open_edit_product(product),
                title="Editar producto",
                aria_label="Editar producto",
                class_name=BUTTON_STYLES["link_primary"],
            ),
            rx.el.button(
                rx.icon("eye", class_name="h-4 w-4"),
                " Desglose",
                on_click=lambda: State.open_stock_details(product),
                title="Ver desglose de stock",
                aria_label="Ver desglose de stock",
                class_name=BUTTON_STYLES["link_primary"],
            ),
            class_name="flex items-center justify-end gap-3 mt-3 pt-2 border-t border-slate-100",
        ),
        class_name="bg-white border border-slate-200 rounded-xl p-4 shadow-sm",
    )


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
                      class_name=BUTTON_STYLES["icon_primary"],
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
                            "inline-flex items-center justify-center rounded-lg p-2 text-emerald-600 hover:bg-emerald-50 transition-colors",
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
