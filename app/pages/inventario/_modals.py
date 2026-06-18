import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  INPUT_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  modal_container,
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
        rx.el.div(
          rx.upload(
            rx.el.div(
              rx.icon("cloud-upload", class_name="h-10 w-10 text-slate-400 mx-auto mb-2"),
              rx.el.p(
                "Arrastre un archivo aquí",
                class_name="text-sm text-slate-500 text-center",
              ),
              rx.el.p(
                "Formatos: .csv, .xlsx",
                class_name="text-xs text-slate-400 text-center mt-1",
              ),
              class_name="flex flex-col items-center justify-center py-8",
            ),
            id="import_upload",
            accept={
              ".csv": ["text/csv", "text/plain", "application/csv"],
              ".xlsx": [
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel",
              ],
            },
            max_files=1,
            border="2px dashed #cbd5e1",
            border_radius="0.75rem",
            class_name="cursor-pointer hover:border-indigo-400 transition-colors",
            on_drop=State.handle_import_upload(rx.upload_files(upload_id="import_upload")),  # type: ignore
          ),
          # Fallback para browsers sin soporte de drag & drop (mobile/Firefox/Safari)
          rx.el.div(
            rx.el.button(
              rx.icon("folder-open", class_name="h-4 w-4"),
              "Seleccionar archivo",
              on_click=rx.call_script("document.getElementById('import_upload').click()"),
              class_name=BUTTON_STYLES["ghost"],
            ),
            class_name="flex justify-center mt-2",
          ),
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
              rx.el.span(State.import_stats["updated"].to_string(), class_name="text-lg font-bold text-indigo-600"),
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
                          "text-xs px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-medium",
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
                  disabled=True,
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
                  disabled=True,
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
                  disabled=True,
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
                  disabled=True,
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
                class_name="w-full mt-2 p-3 border border-slate-200 rounded-lg h-32 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
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
