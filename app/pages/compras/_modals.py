import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  INPUT_STYLES,
  SELECT_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  modal_container,
)


def purchase_detail_modal() -> rx.Component:
  """Modal unificado: detalle visual + edición de metadatos del documento."""

  # ── Encabezado visual ───────────────────────────────────────────────────────
  doc_badge = rx.el.div(
    rx.el.span(
      State.purchase_detail["doc_type"],
      class_name=(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold "
        "bg-indigo-100 text-indigo-700 uppercase tracking-widest"
      ),
    ),
    rx.el.span(
      State.purchase_detail["series"],
      " — ",
      State.purchase_detail["number"],
      class_name="text-base font-bold text-slate-700 font-mono tracking-tight",
    ),
    class_name="flex items-center gap-2.5",
  )

  # ── Tarjetas de resumen (solo lectura) ──────────────────────────────────────
  info_cards = rx.el.div(
    # Proveedor
    rx.el.div(
      rx.el.div(
        rx.icon("building-2", class_name="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0"),
        rx.el.div(
          rx.el.p("Proveedor", class_name=TYPOGRAPHY["caption"]),
          rx.el.p(
            State.purchase_detail["supplier_name"],
            class_name="text-sm font-semibold text-slate-800 leading-tight",
          ),
          rx.el.p(
            State.purchase_detail["supplier_tax_id"],
            class_name="text-xs text-slate-400 font-mono",
          ),
          class_name="flex flex-col gap-0.5 min-w-0",
        ),
        class_name="flex items-start gap-2",
      ),
      class_name="flex-1 min-w-0 bg-slate-50 rounded-xl p-3 border border-slate-100",
    ),
    # Fecha de emisión + registrado
    rx.el.div(
      rx.el.div(
        rx.icon("calendar", class_name="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0"),
        rx.el.div(
          rx.el.p("Emisión", class_name=TYPOGRAPHY["caption"]),
          rx.el.p(
            State.purchase_detail["issue_date"],
            class_name="text-sm font-semibold text-slate-800",
          ),
          rx.el.p(
            "Registrado a las ",
            State.purchase_detail["registered_time"],
            class_name="text-xs text-slate-400",
          ),
          class_name="flex flex-col gap-0.5",
        ),
        class_name="flex items-start gap-2",
      ),
      class_name="flex-shrink-0 bg-slate-50 rounded-xl p-3 border border-slate-100",
    ),
    # Usuario
    rx.el.div(
      rx.el.div(
        rx.icon("user", class_name="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0"),
        rx.el.div(
          rx.el.p("Usuario", class_name=TYPOGRAPHY["caption"]),
          rx.el.p(
            State.purchase_detail["user"],
            class_name="text-sm font-semibold text-slate-800",
          ),
          rx.el.p(
            State.purchase_detail["items_count"].to_string(),
            " producto(s)",
            class_name="text-xs text-slate-400",
          ),
          class_name="flex flex-col gap-0.5",
        ),
        class_name="flex items-start gap-2",
      ),
      class_name="flex-shrink-0 bg-slate-50 rounded-xl p-3 border border-slate-100",
    ),
    # Total (destacado)
    rx.el.div(
      rx.el.div(
        rx.icon("receipt", class_name="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0"),
        rx.el.div(
          rx.el.p("Total", class_name="text-xs font-medium text-indigo-500 uppercase tracking-wide"),
          rx.el.p(
            State.currency_symbol,
            " ",
            State.purchase_detail["total_amount"],
            class_name="text-xl font-bold text-indigo-700 tabular-nums leading-tight",
          ),
          rx.el.p(
            State.purchase_detail["currency_code"],
            class_name="text-xs font-mono text-indigo-400",
          ),
          class_name="flex flex-col gap-0.5",
        ),
        class_name="flex items-start gap-2",
      ),
      class_name="flex-shrink-0 bg-indigo-50 rounded-xl p-3 border border-indigo-100",
    ),
    class_name="flex flex-wrap gap-3",
  )

  # ── Sección editable (doc_type, serie, número, fecha, notas) ───────────────
  # key= en el wrapper fuerza remount de React al abrir distinto documento
  edit_section = rx.el.div(
    rx.el.div(
      rx.icon("pencil-line", class_name="w-3.5 h-3.5 text-slate-400"),
      rx.el.span(
        "Datos del documento",
        class_name="text-xs font-semibold text-slate-500 uppercase tracking-wider",
      ),
      class_name="flex items-center gap-1.5 mb-3",
    ),
    rx.el.div(
      # Tipo
      rx.el.div(
        rx.el.label("Tipo", class_name=TYPOGRAPHY["label"]),
        rx.el.select(
          rx.el.option("Boleta", value="boleta"),
          rx.el.option("Factura", value="factura"),
          default_value=State.purchase_edit_form["doc_type"],
          on_change=lambda v: State.update_purchase_edit_field("doc_type", v),
          class_name=SELECT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      # Serie
      rx.el.div(
        rx.el.label("Serie", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          placeholder="Ej: B001",
          default_value=State.purchase_edit_form["series"],
          on_blur=lambda v: State.update_purchase_edit_field("series", v),
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      # Número
      rx.el.div(
        rx.el.label("Número", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          placeholder="Ej: 000001",
          default_value=State.purchase_edit_form["number"],
          on_blur=lambda v: State.update_purchase_edit_field("number", v),
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      # Fecha
      rx.el.div(
        rx.el.label("Fecha de emisión", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          type="date",
          default_value=State.purchase_edit_form["issue_date"],
          on_change=lambda v: State.update_purchase_edit_field("issue_date", v),
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3",
    ),
    key=State.purchase_edit_form["id"].to_string(),
    class_name="border-t border-slate-100 pt-4",
  )

  # ── Tabla de productos (solo lectura) ───────────────────────────────────────
  items_table = rx.el.div(
    rx.el.div(
      rx.icon("package", class_name="w-3.5 h-3.5 text-slate-400"),
      rx.el.span(
        "Productos ingresados",
        class_name="text-xs font-semibold text-slate-500 uppercase tracking-wider",
      ),
      class_name="flex items-center gap-1.5 mb-3",
    ),
    rx.el.div(
      rx.el.table(
        rx.el.thead(
          rx.el.tr(
            rx.el.th("Producto", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th(
              "Cant.", scope="col",
              class_name=f"{TABLE_STYLES['header_cell']} text-center w-20",
            ),
            rx.el.th(
              "Unidad", scope="col",
              class_name=f"{TABLE_STYLES['header_cell']} hidden sm:table-cell w-20",
            ),
            rx.el.th(
              "Costo Unit.", scope="col",
              class_name=f"{TABLE_STYLES['header_cell']} text-right",
            ),
            rx.el.th(
              "Subtotal", scope="col",
              class_name=f"{TABLE_STYLES['header_cell']} text-right",
            ),
            class_name=TABLE_STYLES["header"],
          )
        ),
        rx.el.tbody(
          rx.foreach(
            State.purchase_detail_items,
            lambda item: rx.el.tr(
              rx.el.td(
                rx.el.div(
                  rx.el.span(item["description"], class_name="text-sm font-medium text-slate-800"),
                  rx.el.span(item["barcode"], class_name="text-xs text-slate-400 font-mono"),
                  class_name="flex flex-col gap-0.5",
                ),
                class_name="py-3 px-4",
              ),
              rx.el.td(
                item["quantity"],
                class_name="py-3 px-4 text-center text-sm tabular-nums",
              ),
              rx.el.td(
                item["unit"],
                class_name="py-3 px-4 text-sm text-slate-500 hidden sm:table-cell",
              ),
              rx.el.td(
                State.currency_symbol, " ", item["unit_cost"],
                class_name="py-3 px-4 text-right text-sm tabular-nums text-slate-600",
              ),
              rx.el.td(
                State.currency_symbol, " ", item["subtotal"],
                class_name="py-3 px-4 text-right text-sm font-semibold tabular-nums",
              ),
              class_name="border-b border-slate-50 hover:bg-slate-50 transition-colors",
            ),
          )
        ),
        class_name="w-full text-sm",
      ),
      class_name="overflow-x-auto rounded-xl border border-slate-100",
    ),
    class_name="border-t border-slate-100 pt-4",
  )

  detail_body = rx.el.div(
    doc_badge,
    info_cards,
    edit_section,
    items_table,
    class_name="flex flex-col gap-4",
  )

  return modal_container(
    is_open=State.purchase_detail_modal_open,
    on_close=State.close_purchase_detail,
    title="Detalle de Compra",
    description="Revisa y corrige los datos del documento.",
    children=[
      rx.cond(
        State.purchase_detail != None,
        detail_body,
        rx.fragment(),
      )
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cerrar",
        on_click=State.close_purchase_detail,
        class_name=BUTTON_STYLES["secondary"],
      ),
      rx.cond(
        State.can_manage_compras,
        rx.el.button(
          rx.icon("save", class_name="w-4 h-4"),
          "Guardar cambios",
          on_click=State.save_purchase_edit,
          class_name=BUTTON_STYLES["primary"],
        ),
        rx.fragment(),
      ),
      class_name="flex justify-end gap-2",
    ),
    max_width="max-w-4xl",
  )


def purchase_edit_modal() -> rx.Component:
  supplier_suggestions = rx.cond(
    State.purchase_edit_supplier_suggestions.length() > 0,
    rx.el.div(
      rx.foreach(
        State.purchase_edit_supplier_suggestions,
        lambda supplier: rx.el.button(
          rx.el.div(
            rx.el.span(
              supplier["name"],
              class_name="font-medium text-slate-800",
            ),
            rx.el.span(
              supplier["tax_id"],
              class_name=TYPOGRAPHY["caption"],
            ),
            class_name="flex flex-col text-left",
          ),
          on_click=lambda _,
          supplier=supplier: State.select_purchase_edit_supplier(
            supplier
          ),
          class_name="w-full text-left p-2 hover:bg-slate-100",
        ),
      ),
      class_name="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-60 overflow-y-auto",
    ),
    rx.fragment(),
  )

  selected_supplier = rx.cond(
    State.purchase_edit_form["supplier_id"] != None,
    rx.el.div(
      rx.el.div(
        rx.el.span(
          State.purchase_edit_form["supplier_name"],
          class_name="font-medium text-slate-800",
        ),
        rx.el.span(
          State.purchase_edit_form["supplier_tax_id"],
          class_name=TYPOGRAPHY["caption"],
        ),
        class_name="flex flex-col",
      ),
      rx.el.button(
        rx.icon("x", class_name="h-4 w-4"),
        on_click=State.clear_purchase_edit_supplier,
        title="Quitar proveedor seleccionado",
        aria_label="Quitar proveedor seleccionado",
        class_name="p-1 text-slate-500 hover:text-slate-800",
      ),
      class_name="flex items-center justify-between rounded-md border border-slate-200 bg-white p-2",
    ),
    rx.fragment(),
  )

  return modal_container(
    is_open=State.purchase_edit_modal_open,
    on_close=State.close_purchase_edit_modal,
    title="Editar compra",
    description="Actualiza la información del documento y proveedor.",
    children=[
      rx.el.div(
        rx.el.div(
          rx.el.label(
            "Tipo de Documento",
            class_name=f"{TYPOGRAPHY['label_secondary']} block mb-1",
          ),
          rx.el.select(
            rx.el.option("Boleta", value="boleta"),
            rx.el.option("Factura", value="factura"),
            default_value=State.purchase_edit_form["doc_type"],
            on_change=lambda value: State.update_purchase_edit_field(
              "doc_type", value
            ),
            class_name=SELECT_STYLES["default"],
          ),
          class_name="w-full",
        ),
        rx.el.div(
          rx.el.label(
            "Serie",
            class_name=f"{TYPOGRAPHY['label_secondary']} block mb-1",
          ),
          rx.el.input(
            placeholder="Ej: F001",
            default_value=State.purchase_edit_form["series"],
            on_blur=lambda value: State.update_purchase_edit_field(
              "series", value
            ),
            class_name=INPUT_STYLES["default"],
            debounce_timeout=600,
          ),
          class_name="w-full",
        ),
        rx.el.div(
          rx.el.label(
            "Numero",
            class_name=f"{TYPOGRAPHY['label_secondary']} block mb-1",
          ),
          rx.el.input(
            placeholder="Ej: 000123",
            default_value=State.purchase_edit_form["number"],
            on_blur=lambda value: State.update_purchase_edit_field(
              "number", value
            ),
            class_name=INPUT_STYLES["default"],
            debounce_timeout=600,
          ),
          class_name="w-full",
        ),
        rx.el.div(
          rx.el.label(
            "Fecha de Emision",
            class_name=f"{TYPOGRAPHY['label_secondary']} block mb-1",
          ),
          rx.el.input(
            type="date",
            default_value=State.purchase_edit_form["issue_date"],
            on_blur=lambda value: State.update_purchase_edit_field(
              "issue_date", value
            ),
            class_name=INPUT_STYLES["default"],
          ),
          class_name="w-full",
        ),
        class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
      ),
      rx.el.div(
        rx.el.label(
          "Notas",
          class_name=f"{TYPOGRAPHY['label_secondary']} block mb-1",
        ),
        rx.el.textarea(
          placeholder="Observaciones del documento o compra",
          default_value=State.purchase_edit_form["notes"],
          on_blur=lambda value: State.update_purchase_edit_field(
            "notes", value
          ),
          class_name=f"{INPUT_STYLES['default']} min-h-[80px] h-auto py-2",
        ),
        class_name="w-full",
      ),
      rx.el.div(
        rx.el.label(
          "Proveedor",
          class_name="block text-sm font-medium text-slate-600",
        ),
        rx.debounce_input(
          rx.input(
            placeholder="Buscar por nombre o N° de Registro de Empresa",
            value=State.purchase_edit_supplier_query,
            on_change=State.search_purchase_edit_supplier,
            class_name=INPUT_STYLES["default"],
          ),
          debounce_timeout=600,
        ),
        supplier_suggestions,
        selected_supplier,
        class_name="flex flex-col gap-2 bg-slate-50 border border-slate-200 rounded-lg p-4 relative",
      ),
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_purchase_edit_modal,
        class_name=BUTTON_STYLES["secondary"],
      ),
      rx.el.button(
        "Guardar cambios",
        on_click=State.save_purchase_edit,
        class_name=BUTTON_STYLES["primary"],
      ),
      class_name="flex justify-end gap-2",
    ),
    max_width="max-w-4xl",
  )


def purchase_delete_modal() -> rx.Component:
  return modal_container(
    is_open=State.purchase_delete_modal_open,
    on_close=State.close_purchase_delete_modal,
    title="Eliminar compra",
    description=(
      "Esta acción revierte el stock ingresado y elimina el documento."
    ),
    children=[
      rx.cond(
        State.purchase_delete_target != None,
        rx.el.div(
          rx.el.div(
            rx.el.p("Documento", class_name=TYPOGRAPHY["caption"]),
            rx.el.p(
              State.purchase_delete_target["doc_type"],
              class_name="font-semibold",
            ),
            class_name="flex flex-col gap-1",
          ),
          rx.el.div(
            rx.el.p("Serie", class_name=TYPOGRAPHY["caption"]),
            rx.el.p(
              State.purchase_delete_target["series"],
              class_name="font-semibold",
            ),
            class_name="flex flex-col gap-1",
          ),
          rx.el.div(
            rx.el.p("Numero", class_name=TYPOGRAPHY["caption"]),
            rx.el.p(
              State.purchase_delete_target["number"],
              class_name="font-semibold",
            ),
            class_name="flex flex-col gap-1",
          ),
          rx.el.div(
            rx.el.p("Proveedor", class_name=TYPOGRAPHY["caption"]),
            rx.el.p(
              State.purchase_delete_target["supplier_name"],
              class_name="font-semibold",
            ),
            rx.el.p(
              State.purchase_delete_target["supplier_tax_id"],
              class_name=TYPOGRAPHY["caption"],
            ),
            class_name="flex flex-col gap-1",
          ),
          class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
        ),
        rx.fragment(),
      )
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_purchase_delete_modal,
        class_name=BUTTON_STYLES["secondary"],
      ),
      rx.el.button(
        rx.icon("trash-2", class_name="h-4 w-4"),
        "Eliminar",
        on_click=State.delete_purchase,
        class_name=BUTTON_STYLES["danger"],
      ),
      class_name="flex justify-end gap-2",
    ),
    max_width="max-w-3xl",
  )


def supplier_modal() -> rx.Component:
  return modal_container(
    is_open=State.supplier_modal_open,
    on_close=State.close_supplier_modal,
    title="Proveedor",
    description="Registrar o editar proveedor.",
    children=[
      rx.el.div(
        rx.el.label("Razón Social / Nombre de Empresa", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          default_value=State.current_supplier["name"],
          on_blur=lambda val: State.update_current_supplier("name", val),
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("N° de Registro de Empresa", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          default_value=State.current_supplier["tax_id"],
          on_blur=lambda val: State.update_current_supplier("tax_id", val),
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Telefono", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          default_value=State.current_supplier["phone"],
          on_blur=lambda val: State.update_current_supplier("phone", val),
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Email", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          default_value=State.current_supplier["email"],
          on_blur=lambda val: State.update_current_supplier("email", val),
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Direccion", class_name=TYPOGRAPHY["label"]),
        rx.el.textarea(
          default_value=State.current_supplier["address"],
          on_blur=lambda val: State.update_current_supplier("address", val),
          class_name=f"{INPUT_STYLES['default']} min-h-[80px] h-auto py-2",
        ),
        class_name="flex flex-col gap-1",
      ),
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_supplier_modal,
        class_name=BUTTON_STYLES["secondary"],
      ),
      rx.el.button(
        "Guardar",
        on_click=State.save_supplier,
        class_name=BUTTON_STYLES["primary"],
      ),
      class_name="flex justify-end gap-2",
    ),
    max_width="max-w-lg",
  )
