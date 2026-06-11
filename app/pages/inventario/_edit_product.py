import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  INPUT_STYLES,
  SELECT_STYLES,
  TYPOGRAPHY,
  toggle_switch,
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
            rx.el.label(
              "% Ganancia",
              class_name=f"block {TYPOGRAPHY['label']}",
            ),
            rx.el.div(
              rx.el.input(
                type="number",
                placeholder=State.effective_profit_margin + " (global)",
                default_value=State.editing_product["custom_profit_margin"].to_string(),
                on_blur=lambda v: State.handle_edit_product_change("profit_margin", v),
                min="0",
                max="9999",
                step="0.01",
                class_name=INPUT_STYLES["default"],
              ),
              rx.el.span(
                "%",
                class_name="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm pointer-events-none",
              ),
              class_name="relative",
            ),
            rx.el.p(
              "Vacío = usa margen global. Al cambiar recalcula Precio Venta.",
              class_name=TYPOGRAPHY["caption"],
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
          rx.el.div(
            rx.el.label("Proveedor predeterminado", class_name=f"block {TYPOGRAPHY['label']}"),
            rx.el.select(
              rx.el.option("Sin proveedor", value=""),
              rx.foreach(
                State.inventory_suppliers,
                lambda s: rx.el.option(s["name"], value=s["id"].to_string()),
              ),
              value=rx.cond(
                State.editing_product["default_supplier_id"],
                State.editing_product["default_supplier_id"].to_string(),
                "",
              ),
              on_change=lambda v: State.handle_edit_product_change("default_supplier_id", v),
              class_name=SELECT_STYLES["default"],
            ),
            rx.el.p(
              "Agrupa este producto en Reposición Automática.",
              class_name=TYPOGRAPHY["caption"],
            ),
            class_name="md:col-span-2",
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
