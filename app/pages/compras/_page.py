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
from ._rows import purchase_row, _purchase_card, _supplier_card, supplier_row
from ._modals import (
  purchase_detail_modal,
  purchase_edit_modal,
  purchase_delete_modal,
  supplier_modal,
)


def compras_page() -> rx.Component:
  """Página principal de gestión de compras y proveedores."""
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
        rx.el.h3("Filtros de búsqueda", class_name=TYPOGRAPHY["card_title"]),
        rx.el.p(
          "Filtra por documento, proveedor o rango de fechas.",
          class_name=TYPOGRAPHY["body_secondary"],
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.button(
        "Limpiar",
        on_click=State.reset_purchase_filters,
        class_name=BUTTON_STYLES["secondary"],
      ),
      class_name="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3",
    ),
    rx.el.div(
      rx.el.div(
        rx.el.label("Buscar", class_name=f"{TYPOGRAPHY['label_secondary']} mb-1"),
        rx.debounce_input(
          rx.input(
            placeholder="Documento, Proveedor, N° de Registro de Empresa",
            value=State.purchase_search_term,
            on_change=State.set_purchase_search_term,
            class_name=INPUT_STYLES["default"],
          ),
          debounce_timeout=600,
        ),
        class_name="w-full",
      ),
      rx.el.div(
        rx.el.label("Fecha inicio", class_name=f"{TYPOGRAPHY['label_secondary']} mb-1"),
        rx.el.input(
          type="date",
          value=State.purchase_start_date,
          on_change=State.set_purchase_start_date,
          class_name=INPUT_STYLES["default"],
        ),
        class_name="w-full",
      ),
      rx.el.div(
        rx.el.label("Fecha fin", class_name=f"{TYPOGRAPHY['label_secondary']} mb-1"),
        rx.el.input(
          type="date",
          value=State.purchase_end_date,
          on_change=State.set_purchase_end_date,
          class_name=INPUT_STYLES["default"],
        ),
        class_name="w-full",
      ),
      class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-4",
    ),
    class_name=CARD_STYLES["default"],
  )

  table_card = rx.el.div(
    rx.el.div(
      rx.el.div(
        rx.el.h3("COMPRAS REGISTRADAS", class_name=TYPOGRAPHY["card_title"]),
        rx.el.p(
          "Historial de documentos ingresados.",
          class_name=TYPOGRAPHY["body_secondary"],
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.span("Resultados:", class_name=TYPOGRAPHY["body_secondary"]),
        rx.el.span(
          State.purchase_records.length().to_string(),
          class_name="text-sm font-semibold text-slate-700",
        ),
        class_name="flex items-center gap-2",
      ),
      class_name="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3",
    ),
    # Vista móvil: Cards (visible en < md)
    rx.el.div(
      rx.foreach(State.purchase_records, _purchase_card),
      class_name="flex flex-col gap-3 md:hidden",
    ),
    # Vista desktop: Tabla (oculta en < md)
    rx.el.div(
      rx.el.table(
        rx.el.thead(
          rx.el.tr(
            rx.el.th("Fecha", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Proveedor", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Documento", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
            rx.el.th("Serie", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
            rx.el.th("Numero", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
            rx.el.th("Total", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right"),
            rx.el.th("Usuario", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
            rx.el.th("Items", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center"),
            rx.el.th("Accion", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center"),
          ),
          class_name=TABLE_STYLES["header"],
        ),
        rx.el.tbody(rx.foreach(State.purchase_records, purchase_row)),
        class_name="w-full text-sm",
      ),
      class_name="hidden md:block overflow-x-auto border border-slate-100 rounded-lg",
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
    class_name=f"{CARD_STYLES['default']} flex flex-col {SPACING['card_gap']}",
  )

  registro_content = rx.el.div(
    filters_card,
    table_card,
    class_name="flex flex-col gap-4",
  )

  proveedores_content = rx.el.div(
    rx.el.div(
      rx.el.div(
        rx.el.label("Buscar proveedor", class_name=f"{TYPOGRAPHY['label_secondary']} mb-1"),
        rx.debounce_input(
          rx.input(
            placeholder="Razón Social, N° de Registro de Empresa, telefono",
            value=State.supplier_search_query,
            on_change=State.set_supplier_search_query,
            class_name=INPUT_STYLES["default"],
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
          class_name=BUTTON_STYLES["primary"],
        ),
        rx.el.span(
          "Solo lectura",
          class_name="text-xs text-slate-400",
        ),
      ),
      class_name="flex flex-wrap items-end justify-between gap-4",
    ),
    # Vista móvil: Cards (visible en < md)
    rx.el.div(
      rx.foreach(State.suppliers_view, _supplier_card),
      class_name="flex flex-col gap-3 md:hidden",
    ),
    # Vista desktop: Tabla (oculta en < md)
    rx.el.div(
      rx.el.table(
        rx.el.thead(
          rx.el.tr(
            rx.el.th("Proveedor", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("N° de Registro de Empresa", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Telefono", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
            rx.el.th("Email", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
            rx.el.th("Direccion", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
            rx.el.th("Accion", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center"),
          ),
          class_name=TABLE_STYLES["header"],
        ),
        rx.el.tbody(rx.foreach(State.suppliers_view, supplier_row)),
        class_name="w-full text-sm",
      ),
      class_name="hidden md:block overflow-x-auto border border-slate-100 rounded-lg",
    ),
    rx.cond(
      State.suppliers_view.length() == 0,
      rx.el.p(
        "No hay proveedores registrados.",
        class_name="text-slate-500 text-center py-8",
      ),
      rx.fragment(),
    ),
    class_name=f"{CARD_STYLES['default']} flex flex-col {SPACING['card_gap']}",
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
