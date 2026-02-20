import reflex as rx
from app.state import State
from app.components.ui import (
  TABLE_STYLES,
  modal_container,
  page_title,
  pagination_controls,
  permission_guard,
)


def purchase_row(purchase: rx.Var[dict]) -> rx.Component:
  action_buttons = rx.el.div(
    rx.el.button(
      rx.icon("eye", class_name="h-4 w-4"),
      on_click=lambda _: State.open_purchase_detail(purchase["id"]),
      class_name="px-3 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700",
    ),
    rx.cond(
      State.can_manage_compras,
      rx.el.button(
        rx.icon("pencil", class_name="h-4 w-4"),
        on_click=lambda _: State.open_purchase_edit_modal(purchase["id"]),
        class_name="p-2 text-blue-500 hover:bg-blue-100 rounded-full",
        title="Editar",
        aria_label="Editar",
      ),
      rx.fragment(),
    ),
    rx.cond(
      State.can_manage_compras,
      rx.el.button(
        rx.icon("trash-2", class_name="h-4 w-4"),
        on_click=lambda _: State.open_purchase_delete_modal(purchase["id"]),
        class_name="p-2 text-red-500 hover:bg-red-100 rounded-full",
        title="Eliminar",
        aria_label="Eliminar",
      ),
      rx.fragment(),
    ),
    class_name="flex flex-wrap items-center justify-center gap-2",
  )
  return rx.el.tr(
    rx.el.td(
      rx.el.div(
        rx.el.span(purchase["issue_date"], class_name="font-medium"),
        rx.cond(
          purchase["registered_time"] != "",
          rx.el.span(
            purchase["registered_time"],
            class_name="text-xs text-slate-500",
          ),
          rx.fragment(),
        ),
        class_name="flex flex-col",
      ),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      rx.el.div(
        rx.el.span(purchase["supplier_name"], class_name="font-medium"),
        rx.el.span(
          purchase["supplier_tax_id"], class_name="text-xs text-slate-500"
        ),
        class_name="flex flex-col",
      ),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      purchase["doc_type"],
      class_name="py-3 px-4 text-left font-medium hidden md:table-cell",
    ),
    rx.el.td(purchase["series"], class_name="py-3 px-4 text-left hidden md:table-cell"),
    rx.el.td(purchase["number"], class_name="py-3 px-4 text-left hidden md:table-cell"),
    rx.el.td(
      rx.el.div(
        State.currency_symbol,
        purchase["total_amount"].to_string(),
        class_name="text-right font-semibold",
      ),
      rx.el.div(
        purchase["currency_code"],
        class_name="text-xs text-slate-400 text-right",
      ),
      class_name="py-3 px-4 text-right",
    ),
    rx.el.td(purchase["user"], class_name="py-3 px-4 text-left hidden md:table-cell"),
    rx.el.td(
      purchase["items_count"].to_string(),
      class_name="py-3 px-4 text-center",
    ),
    rx.el.td(
      action_buttons,
      class_name="py-3 px-4 text-center",
    ),
    class_name="border-b hover:bg-slate-50 transition-colors",
  )


def supplier_row(supplier: rx.Var[dict]) -> rx.Component:
  actions = rx.el.div(
    rx.el.button(
      rx.icon("pencil", class_name="h-4 w-4"),
      on_click=lambda _: State.open_supplier_modal(supplier),
      class_name="p-2 text-blue-500 hover:bg-blue-100 rounded-full",
    ),
    rx.el.button(
      rx.icon("trash-2", class_name="h-4 w-4"),
      on_click=lambda _: State.delete_supplier(supplier["id"]),
      class_name="p-2 text-red-500 hover:bg-red-100 rounded-full",
    ),
    class_name="flex items-center justify-center gap-2",
  )
  readonly = rx.el.span(
    "Solo lectura",
    class_name="text-xs text-slate-400",
  )
  return rx.el.tr(
    rx.el.td(supplier["name"], class_name="py-3 px-4"),
    rx.el.td(supplier["tax_id"], class_name="py-3 px-4"),
    rx.el.td(
      rx.cond(supplier["phone"] != "", supplier["phone"], "-"),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      rx.cond(supplier["email"] != "", supplier["email"], "-"),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      rx.cond(supplier["address"] != "", supplier["address"], "-"),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      rx.cond(
        State.can_manage_proveedores,
        actions,
        readonly,
      ),
      class_name="py-3 px-4 text-center",
    ),
    class_name="border-b hover:bg-slate-50 transition-colors",
  )


def purchase_detail_modal() -> rx.Component:
  summary_grid = rx.el.div(
    rx.el.div(
      rx.el.p("Tipo de documento", class_name="text-xs text-slate-500"),
      rx.el.p(
        State.purchase_detail["doc_type"],
        class_name="font-semibold",
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.p("Proveedor", class_name="text-xs text-slate-500"),
      rx.el.p(
        State.purchase_detail["supplier_name"],
        class_name="font-semibold",
      ),
      rx.el.p(
        State.purchase_detail["supplier_tax_id"],
        class_name="text-xs text-slate-500",
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.p("Fecha", class_name="text-xs text-slate-500"),
      rx.el.p(
        State.purchase_detail["issue_date"],
        class_name="font-semibold",
      ),
      rx.cond(
        State.purchase_detail["registered_time"] != "",
        rx.el.p(
          State.purchase_detail["registered_time"],
          class_name="text-xs text-slate-500",
        ),
        rx.fragment(),
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.p("Total", class_name="text-xs text-slate-500"),
      rx.el.p(
        State.currency_symbol,
        State.purchase_detail["total_amount"].to_string(),
        class_name="font-semibold",
      ),
      rx.el.p(
        State.purchase_detail["currency_code"],
        class_name="text-xs text-slate-500",
      ),
      class_name="flex flex-col gap-1",
    ),
    class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
  )

  secondary_grid = rx.el.div(
    rx.el.div(
      rx.el.p("Serie", class_name="text-xs text-slate-500"),
      rx.el.p(
        State.purchase_detail["series"],
        class_name="font-semibold",
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.p("Numero", class_name="text-xs text-slate-500"),
      rx.el.p(
        State.purchase_detail["number"],
        class_name="font-semibold",
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.p("Usuario", class_name="text-xs text-slate-500"),
      rx.el.p(
        State.purchase_detail["user"],
        class_name="font-semibold",
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.p("Items", class_name="text-xs text-slate-500"),
      rx.el.p(
        State.purchase_detail["items_count"].to_string(),
        class_name="font-semibold",
      ),
      class_name="flex flex-col gap-1",
    ),
    class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
  )

  notes_block = rx.el.div(
    rx.el.p("Notas", class_name="text-xs text-slate-500"),
    rx.cond(
      State.purchase_detail["notes"] != "",
      rx.el.p(
        State.purchase_detail["notes"],
        class_name="text-sm text-slate-700",
      ),
      rx.el.p(
        "Sin observaciones",
        class_name="text-sm text-slate-700",
      ),
    ),
    class_name="flex flex-col gap-1",
  )

  detail_section = rx.el.div(
    secondary_grid,
    notes_block,
    class_name="flex flex-col gap-4 pt-4 mt-1 border-t border-slate-100",
  )

  items_table = rx.el.div(
    rx.el.table(
      rx.el.thead(
        rx.el.tr(
          rx.el.th("Producto", class_name=TABLE_STYLES["header_cell"]),
          rx.el.th(
            "Cantidad", class_name=f"{TABLE_STYLES['header_cell']} text-center"
          ),
          rx.el.th(
            "Costo Unit.", class_name=f"{TABLE_STYLES['header_cell']} text-right"
          ),
          rx.el.th(
            "Subtotal", class_name=f"{TABLE_STYLES['header_cell']} text-right"
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
                rx.el.span(item["description"], class_name="font-medium"),
                rx.el.span(
                  item["barcode"],
                  class_name="text-xs text-slate-500",
                ),
                class_name="flex flex-col",
              ),
              class_name="py-3 px-4",
            ),
            rx.el.td(
              item["quantity"].to_string(),
              class_name="py-3 px-4 text-center",
            ),
            rx.el.td(
              State.currency_symbol,
              item["unit_cost"].to_string(),
              class_name="py-3 px-4 text-right",
            ),
            rx.el.td(
              State.currency_symbol,
              item["subtotal"].to_string(),
              class_name="py-3 px-4 text-right font-semibold",
            ),
            class_name="border-b",
          ),
        )
      ),
      class_name="w-full text-sm",
    ),
    class_name="overflow-x-auto border rounded-lg",
  )

  detail_body = rx.el.div(
    summary_grid,
    detail_section,
    items_table,
    class_name="flex flex-col gap-4",
  )

  return modal_container(
    is_open=State.purchase_detail_modal_open,
    on_close=State.close_purchase_detail,
    title="Detalle de Compra",
    description="Resumen del documento y productos ingresados.",
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
        class_name="px-4 py-2 border rounded-md text-slate-600 hover:bg-slate-100",
      ),
      class_name="flex justify-end",
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
              class_name="text-xs text-slate-500",
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
          class_name="text-xs text-slate-500",
        ),
        class_name="flex flex-col",
      ),
      rx.el.button(
        rx.icon("x", class_name="h-4 w-4"),
        on_click=State.clear_purchase_edit_supplier,
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
            class_name="block text-sm font-medium text-slate-600 mb-1",
          ),
          rx.el.select(
            rx.el.option("Boleta", value="boleta"),
            rx.el.option("Factura", value="factura"),
            default_value=State.purchase_edit_form["doc_type"],
            on_change=lambda value: State.update_purchase_edit_field(
              "doc_type", value
            ),
            class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
          ),
          class_name="w-full",
        ),
        rx.el.div(
          rx.el.label(
            "Serie",
            class_name="block text-sm font-medium text-slate-600 mb-1",
          ),
          rx.el.input(
            placeholder="Ej: F001",
            default_value=State.purchase_edit_form["series"],
            on_blur=lambda value: State.update_purchase_edit_field(
              "series", value
            ),
            class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            debounce_timeout=600,
          ),
          class_name="w-full",
        ),
        rx.el.div(
          rx.el.label(
            "Numero",
            class_name="block text-sm font-medium text-slate-600 mb-1",
          ),
          rx.el.input(
            placeholder="Ej: 000123",
            default_value=State.purchase_edit_form["number"],
            on_blur=lambda value: State.update_purchase_edit_field(
              "number", value
            ),
            class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
            debounce_timeout=600,
          ),
          class_name="w-full",
        ),
        rx.el.div(
          rx.el.label(
            "Fecha de Emision",
            class_name="block text-sm font-medium text-slate-600 mb-1",
          ),
          rx.el.input(
            type="date",
            default_value=State.purchase_edit_form["issue_date"],
            on_blur=lambda value: State.update_purchase_edit_field(
              "issue_date", value
            ),
            class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
          ),
          class_name="w-full",
        ),
        class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
      ),
      rx.el.div(
        rx.el.label(
          "Notas",
          class_name="block text-sm font-medium text-slate-600 mb-1",
        ),
        rx.el.textarea(
          placeholder="Observaciones del documento o compra",
          default_value=State.purchase_edit_form["notes"],
          on_blur=lambda value: State.update_purchase_edit_field(
            "notes", value
          ),
          class_name="w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 min-h-[80px]",
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
            class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
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
        class_name="px-4 py-2 border rounded-md text-slate-600 hover:bg-slate-100",
      ),
      rx.el.button(
        "Guardar cambios",
        on_click=State.save_purchase_edit,
        class_name="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700",
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
            rx.el.p("Documento", class_name="text-xs text-slate-500"),
            rx.el.p(
              State.purchase_delete_target["doc_type"],
              class_name="font-semibold",
            ),
            class_name="flex flex-col gap-1",
          ),
          rx.el.div(
            rx.el.p("Serie", class_name="text-xs text-slate-500"),
            rx.el.p(
              State.purchase_delete_target["series"],
              class_name="font-semibold",
            ),
            class_name="flex flex-col gap-1",
          ),
          rx.el.div(
            rx.el.p("Numero", class_name="text-xs text-slate-500"),
            rx.el.p(
              State.purchase_delete_target["number"],
              class_name="font-semibold",
            ),
            class_name="flex flex-col gap-1",
          ),
          rx.el.div(
            rx.el.p("Proveedor", class_name="text-xs text-slate-500"),
            rx.el.p(
              State.purchase_delete_target["supplier_name"],
              class_name="font-semibold",
            ),
            rx.el.p(
              State.purchase_delete_target["supplier_tax_id"],
              class_name="text-xs text-slate-500",
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
        class_name="px-4 py-2 border rounded-md text-slate-600 hover:bg-slate-100",
      ),
      rx.el.button(
        rx.icon("trash-2", class_name="h-4 w-4"),
        "Eliminar",
        on_click=State.delete_purchase,
        class_name="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700",
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
        rx.el.label("Razón Social / Nombre de Empresa", class_name="text-sm font-medium text-slate-700"),
        rx.el.input(
          default_value=State.current_supplier["name"],
          on_blur=lambda val: State.update_current_supplier("name", val),
          class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("N° de Registro de Empresa", class_name="text-sm font-medium text-slate-700"),
        rx.el.input(
          default_value=State.current_supplier["tax_id"],
          on_blur=lambda val: State.update_current_supplier("tax_id", val),
          class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Telefono", class_name="text-sm font-medium text-slate-700"),
        rx.el.input(
          default_value=State.current_supplier["phone"],
          on_blur=lambda val: State.update_current_supplier("phone", val),
          class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Email", class_name="text-sm font-medium text-slate-700"),
        rx.el.input(
          default_value=State.current_supplier["email"],
          on_blur=lambda val: State.update_current_supplier("email", val),
          class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Direccion", class_name="text-sm font-medium text-slate-700"),
        rx.el.textarea(
          default_value=State.current_supplier["address"],
          on_blur=lambda val: State.update_current_supplier("address", val),
          class_name="w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 min-h-[80px]",
        ),
        class_name="flex flex-col gap-1",
      ),
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_supplier_modal,
        class_name="px-4 py-2 border rounded-md text-slate-600 hover:bg-slate-100",
      ),
      rx.el.button(
        "Guardar",
        on_click=State.save_supplier,
        class_name="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700",
      ),
      class_name="flex justify-end gap-2",
    ),
    max_width="max-w-lg",
  )


def compras_page() -> rx.Component:
  tab_button = "px-4 py-2 rounded-md text-sm font-semibold transition"
  registro_button = rx.el.button(
    "REGISTRO DE COMPRAS",
    on_click=lambda _: State.set_purchases_tab("registro"),
    class_name=rx.cond(
      State.purchases_active_tab == "registro",
      f"{tab_button} bg-indigo-600 text-white",
      f"{tab_button} bg-white text-slate-600 border",
    ),
  )
  proveedores_button = rx.el.button(
    "PROVEEDORES",
    on_click=lambda _: State.set_purchases_tab("proveedores"),
    class_name=rx.cond(
      State.purchases_active_tab == "proveedores",
      f"{tab_button} bg-indigo-600 text-white",
      f"{tab_button} bg-white text-slate-600 border",
    ),
  )

  filters_card = rx.el.div(
    rx.el.div(
      rx.el.div(
        rx.el.h3("Filtros de búsqueda", class_name="text-base font-semibold text-slate-700"),
        rx.el.p(
          "Filtra por documento, proveedor o rango de fechas.",
          class_name="text-sm text-slate-500",
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.button(
        "Limpiar",
        on_click=State.reset_purchase_filters,
        class_name="px-4 py-2 border rounded-md text-slate-600 hover:bg-slate-100",
      ),
      class_name="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3",
    ),
    rx.el.div(
      rx.el.div(
        rx.el.label("Buscar", class_name="text-sm font-medium text-slate-600 mb-1"),
        rx.debounce_input(
          rx.input(
            placeholder="Documento, Proveedor, N° de Registro de Empresa",
            value=State.purchase_search_term,
            on_change=State.set_purchase_search_term,
            class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
          ),
          debounce_timeout=600,
        ),
        class_name="w-full",
      ),
      rx.el.div(
        rx.el.label("Fecha inicio", class_name="text-sm font-medium text-slate-600 mb-1"),
        rx.el.input(
          type="date",
          value=State.purchase_start_date,
          on_change=State.set_purchase_start_date,
          class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
        ),
        class_name="w-full",
      ),
      rx.el.div(
        rx.el.label("Fecha fin", class_name="text-sm font-medium text-slate-600 mb-1"),
        rx.el.input(
          type="date",
          value=State.purchase_end_date,
          on_change=State.set_purchase_end_date,
          class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
        ),
        class_name="w-full",
      ),
      class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-4",
    ),
    class_name="bg-white p-4 sm:p-6 rounded-xl border border-slate-200 shadow-sm",
  )

  table_card = rx.el.div(
    rx.el.div(
      rx.el.div(
        rx.el.h3("COMPRAS REGISTRADAS", class_name="text-base font-semibold text-slate-700"),
        rx.el.p(
          "Historial de documentos ingresados.",
          class_name="text-sm text-slate-500",
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.span("Resultados:", class_name="text-sm text-slate-500"),
        rx.el.span(
          State.purchase_records.length().to_string(),
          class_name="text-sm font-semibold text-slate-700",
        ),
        class_name="flex items-center gap-2",
      ),
      class_name="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3",
    ),
    rx.el.div(
      rx.el.table(
        rx.el.thead(
          rx.el.tr(
            rx.el.th("Fecha", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Proveedor", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Documento", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
            rx.el.th("Serie", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
            rx.el.th("Numero", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
            rx.el.th("Total", class_name=f"{TABLE_STYLES['header_cell']} text-right"),
            rx.el.th("Usuario", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
            rx.el.th("Items", class_name=f"{TABLE_STYLES['header_cell']} text-center"),
            rx.el.th("Accion", class_name=f"{TABLE_STYLES['header_cell']} text-center"),
          ),
          class_name=TABLE_STYLES["header"],
        ),
        rx.el.tbody(rx.foreach(State.purchase_records, purchase_row)),
        class_name="w-full text-sm",
      ),
      class_name="overflow-x-auto border border-slate-100 rounded-lg",
    ),
    rx.cond(
      State.purchase_records.length() == 0,
      rx.el.p(
        "No hay compras registradas.",
        class_name="text-slate-500 text-center py-8",
      ),
      rx.fragment(),
    ),
    pagination_controls(
      current_page=State.purchase_current_page,
      total_pages=State.purchase_total_pages,
      on_prev=State.prev_purchase_page,
      on_next=State.next_purchase_page,
    ),
    class_name="bg-white p-4 sm:p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-4",
  )

  registro_content = rx.el.div(
    filters_card,
    table_card,
    class_name="flex flex-col gap-4",
  )

  proveedores_content = rx.el.div(
    rx.el.div(
      rx.el.div(
        rx.el.label("Buscar proveedor", class_name="text-sm font-medium text-slate-600 mb-1"),
        rx.debounce_input(
          rx.input(
            placeholder="Razón Social, N° de Registro de Empresa, telefono",
            value=State.supplier_search_query,
            on_change=State.set_supplier_search_query,
            class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
          ),
          debounce_timeout=600,
        ),
        class_name="w-full sm:w-64",
      ),
      rx.cond(
        State.can_manage_proveedores,
        rx.el.button(
          rx.icon("plus", class_name="h-4 w-4"),
          "Nuevo proveedor",
          on_click=lambda _: State.open_supplier_modal(None),
          class_name="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700",
        ),
        rx.el.span(
          "Solo lectura",
          class_name="text-xs text-slate-400",
        ),
      ),
      class_name="flex flex-wrap items-end justify-between gap-4",
    ),
    rx.el.div(
      rx.el.table(
        rx.el.thead(
          rx.el.tr(
            rx.el.th("Proveedor", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("N° de Registro de Empresa", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Telefono", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Email", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Direccion", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Accion", class_name=f"{TABLE_STYLES['header_cell']} text-center"),
          ),
          class_name=TABLE_STYLES["header"],
        ),
        rx.el.tbody(rx.foreach(State.suppliers_view, supplier_row)),
        class_name="w-full text-sm",
      ),
      class_name="overflow-x-auto border border-slate-100 rounded-lg",
    ),
    rx.cond(
      State.suppliers_view.length() == 0,
      rx.el.p(
        "No hay proveedores registrados.",
        class_name="text-slate-500 text-center py-8",
      ),
      rx.fragment(),
    ),
    class_name="bg-white p-4 sm:p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-4",
  )

  content = rx.el.div(
    page_title(
      "REGISTRO DE COMPRAS",
      "Consulta documentos de compra y gestiona proveedores.",
    ),
    rx.el.div(
      registro_button,
      proveedores_button,
      class_name="flex flex-wrap gap-2 mb-4",
    ),
    rx.cond(
      State.purchases_active_tab == "registro",
      registro_content,
      proveedores_content,
    ),
    purchase_detail_modal(),
    purchase_edit_modal(),
    purchase_delete_modal(),
    supplier_modal(),
    class_name="p-4 sm:p-6 w-full flex flex-col gap-6",
    on_mount=State.refresh_purchase_cache,
  )

  return permission_guard(
    has_permission=State.can_view_compras,
    content=content,
    redirect_message="Acceso denegado a Compras",
  )

