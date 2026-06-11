import reflex as rx

from app.state import State
from app.components.ui import BUTTON_STYLES, TYPOGRAPHY


def purchase_row(purchase: rx.Var[dict]) -> rx.Component:
  """Fila de compra para la tabla de listado."""
  action_buttons = rx.el.div(
    rx.el.button(
      rx.icon("eye", class_name="h-4 w-4"),
      on_click=lambda _: State.open_purchase_detail(purchase["id"]),
      title="Ver detalle",
      aria_label="Ver detalle",
      class_name=BUTTON_STYLES["primary_sm"],
    ),
    rx.cond(
      State.can_manage_compras,
      rx.el.button(
        rx.icon("pencil", class_name="h-4 w-4"),
        on_click=lambda _: State.open_purchase_edit_modal(purchase["id"]),
        class_name=BUTTON_STYLES["icon_primary"],
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
        class_name=BUTTON_STYLES["icon_danger"],
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
            class_name=TYPOGRAPHY["caption"],
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
          purchase["supplier_tax_id"], class_name=TYPOGRAPHY["caption"]
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


def _purchase_card(purchase: rx.Var) -> rx.Component:
  """Card de compra para vista móvil."""
  return rx.el.div(
    # Header: Fecha + Total
    rx.el.div(
      rx.el.div(
        rx.el.span(purchase["issue_date"], class_name="font-medium text-slate-900 text-sm"),
        rx.cond(
          purchase["registered_time"] != "",
          rx.el.span(purchase["registered_time"], class_name=TYPOGRAPHY["caption"]),
          rx.fragment(),
        ),
        class_name="flex flex-col",
      ),
      rx.el.div(
        rx.el.span(
          State.currency_symbol,
          " ",
          purchase["total_amount"].to_string(),
          class_name="font-semibold tabular-nums text-slate-900",
        ),
        rx.el.span(purchase["currency_code"], class_name=TYPOGRAPHY["caption"]),
        class_name="flex flex-col items-end",
      ),
      class_name="flex items-start justify-between gap-2",
    ),
    # Body: Proveedor + Items
    rx.el.div(
      rx.el.div(
        rx.el.span(purchase["supplier_name"], class_name="text-sm font-medium text-slate-800"),
        rx.el.span(purchase["supplier_tax_id"], class_name=TYPOGRAPHY["caption"]),
        class_name="flex flex-col",
      ),
      rx.el.div(
        rx.icon("package", class_name="h-3.5 w-3.5 text-slate-400"),
        rx.el.span(
          purchase["items_count"].to_string(),
          " productos",
          class_name=TYPOGRAPHY["caption"],
        ),
        class_name="flex items-center gap-1",
      ),
      class_name="flex flex-col gap-1.5 mt-2",
    ),
    # Footer: Acciones
    rx.el.div(
      rx.el.button(
        rx.icon("eye", class_name="h-4 w-4"),
        " Detalle",
        on_click=lambda _: State.open_purchase_detail(purchase["id"]),
        title="Ver detalle",
        aria_label="Ver detalle",
        class_name=BUTTON_STYLES["link_primary"],
      ),
      rx.el.div(
        rx.cond(
          State.can_manage_compras,
          rx.el.button(
            rx.icon("pencil", class_name="h-4 w-4"),
            on_click=lambda _: State.open_purchase_edit_modal(purchase["id"]),
            class_name=BUTTON_STYLES["icon_primary"],
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
            class_name=BUTTON_STYLES["icon_danger"],
            title="Eliminar",
            aria_label="Eliminar",
          ),
          rx.fragment(),
        ),
        class_name="flex items-center gap-2",
      ),
      class_name="flex items-center justify-between mt-3 pt-2 border-t border-slate-100",
    ),
    class_name="bg-white border border-slate-200 rounded-xl p-4 shadow-sm",
  )


def _supplier_card(supplier: rx.Var) -> rx.Component:
  """Card de proveedor para vista móvil."""
  actions = rx.el.div(
    rx.el.button(
      rx.icon("pencil", class_name="h-4 w-4"),
      on_click=lambda _: State.open_supplier_modal(supplier),
      title="Editar proveedor",
      aria_label="Editar proveedor",
      class_name=BUTTON_STYLES["icon_primary"],
    ),
    rx.el.button(
      rx.icon("trash-2", class_name="h-4 w-4"),
      on_click=lambda _: State.delete_supplier(supplier["id"]),
      title="Eliminar proveedor",
      aria_label="Eliminar proveedor",
      class_name=BUTTON_STYLES["icon_danger"],
    ),
    class_name="flex items-center gap-2",
  )
  return rx.el.div(
    # Header: Nombre + Acciones
    rx.el.div(
      rx.el.div(
        rx.el.span(supplier["name"], class_name="font-medium text-slate-900 text-sm"),
        rx.el.span(supplier["tax_id"], class_name=TYPOGRAPHY["caption"]),
        class_name="flex flex-col",
      ),
      rx.cond(
        State.can_manage_proveedores,
        actions,
        rx.el.span("Solo lectura", class_name=TYPOGRAPHY["caption"]),
      ),
      class_name="flex items-start justify-between gap-2",
    ),
    # Body: Contacto
    rx.el.div(
      rx.cond(
        supplier["phone"] != "",
        rx.el.div(
          rx.icon("phone", class_name="h-3.5 w-3.5 text-slate-400"),
          rx.el.span(supplier["phone"], class_name="text-sm text-slate-600"),
          class_name="flex items-center gap-1.5",
        ),
        rx.fragment(),
      ),
      rx.cond(
        supplier["email"] != "",
        rx.el.div(
          rx.icon("mail", class_name="h-3.5 w-3.5 text-slate-400"),
          rx.el.span(supplier["email"], class_name="text-sm text-slate-600"),
          class_name="flex items-center gap-1.5",
        ),
        rx.fragment(),
      ),
      rx.cond(
        supplier["address"] != "",
        rx.el.div(
          rx.icon("map-pin", class_name="h-3.5 w-3.5 text-slate-400"),
          rx.el.span(supplier["address"], class_name="text-sm text-slate-600"),
          class_name="flex items-center gap-1.5",
        ),
        rx.fragment(),
      ),
      class_name="flex flex-col gap-1.5 mt-2",
    ),
    class_name="bg-white border border-slate-200 rounded-xl p-4 shadow-sm",
  )


def supplier_row(supplier: rx.Var[dict]) -> rx.Component:
  actions = rx.el.div(
    rx.el.button(
      rx.icon("pencil", class_name="h-4 w-4"),
      on_click=lambda _: State.open_supplier_modal(supplier),
      title="Editar proveedor",
      aria_label="Editar proveedor",
      class_name=BUTTON_STYLES["icon_primary"],
    ),
    rx.el.button(
      rx.icon("trash-2", class_name="h-4 w-4"),
      on_click=lambda _: State.delete_supplier(supplier["id"]),
      title="Eliminar proveedor",
      aria_label="Eliminar proveedor",
      class_name=BUTTON_STYLES["icon_danger"],
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
      class_name="py-3 px-4 hidden md:table-cell",
    ),
    rx.el.td(
      rx.cond(supplier["email"] != "", supplier["email"], "-"),
      class_name="py-3 px-4 hidden md:table-cell",
    ),
    rx.el.td(
      rx.cond(supplier["address"] != "", supplier["address"], "-"),
      class_name="py-3 px-4 hidden md:table-cell",
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
