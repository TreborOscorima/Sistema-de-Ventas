import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  TYPOGRAPHY,
  info_badge,
  payment_method_badge,
)


def sale_items_list(
  items: rx.Var[list[dict]],
  preview_items: rx.Var[list[dict]],
  hidden_count: rx.Var[int],
  sale_id: rx.Var[str],
) -> rx.Component:
  expanded = State.expanded_cashbox_sale_id == sale_id
  def _item_row(item: rx.Var[dict]) -> rx.Component:
    return rx.el.div(
      rx.el.div(
        rx.el.span(
          item["description"],
          title=item["description"],
          class_name="block text-sm font-medium text-slate-900 truncate",
        ),
      ),
      rx.el.div(
        rx.el.span(
          item["quantity"].to_string(),
          " x ",
          item["sale_price"].to_string(),
          class_name=TYPOGRAPHY["caption"],
        ),
        rx.el.span(
          State.currency_symbol,
          item["subtotal"].to_string(),
          class_name="text-xs font-semibold text-slate-700",
        ),
        class_name="flex justify-between items-center",
      ),
      class_name="flex flex-col gap-0.5 border-b border-dashed border-slate-100 last:border-0 pb-1 last:pb-0",
    )

  list_content = rx.cond(
    expanded,
    rx.foreach(items, _item_row),
    rx.foreach(preview_items, _item_row),
  )

  return rx.el.div(
    list_content,
    rx.cond(
      expanded | (hidden_count <= 0),
      rx.fragment(),
      rx.el.div(
        rx.el.span(
          "Ver ",
          hidden_count.to_string(),
          " item(s) más",
          class_name="text-xs text-indigo-600 font-medium",
        ),
        class_name="pt-1",
      ),
    ),
    class_name=rx.cond(
      expanded,
      "flex flex-col gap-1",
      "flex flex-col gap-1 h-24 overflow-hidden",
    ),
  )


def render_payment_details(details: rx.Var[str]) -> rx.Component:
  return rx.cond(
    details.length() > 50,
    rx.tooltip(
      rx.el.span(
        rx.icon("info", class_name="h-3 w-3"),
        "Detalle",
        class_name="inline-flex items-center gap-1 rounded-full bg-slate-100/80 px-2 py-0.5 text-xs font-semibold text-slate-600 hover:bg-slate-200 cursor-help",
      ),
      content=details,
      side="bottom",
      align="start",
      side_offset=6,
    ),
    rx.el.p(details, class_name=TYPOGRAPHY["caption"]),
  )


def _cashbox_sale_card(sale: rx.Var[dict]) -> rx.Component:
  """Card de venta de caja para vista móvil."""
  return rx.el.div(
    # Header: Hora + Método de pago
    rx.el.div(
      rx.el.span(
        sale["timestamp"],
        class_name="font-mono text-xs text-slate-500",
      ),
      payment_method_badge(sale["payment_method"]),
      class_name="flex items-center justify-between gap-2",
    ),
    # Body: Usuario + Detalle de pago
    rx.el.div(
      rx.el.div(
        rx.el.span(sale["user"], class_name="text-sm font-medium text-slate-800"),
        render_payment_details(sale["payment_details"]),
        class_name="flex flex-col gap-0.5",
      ),
      rx.cond(
        sale["is_deleted"],
        rx.el.div(
          info_badge("Venta eliminada", variant="danger"),
          rx.el.p(
            sale["delete_reason"],
            class_name="text-xs text-red-600 mt-1",
          ),
          class_name="mt-1",
        ),
        rx.fragment(),
      ),
      class_name="flex flex-col gap-1 mt-2",
    ),
    # Items preview
    rx.el.div(
      sale_items_list(
        sale["items"],
        sale["items_preview"],
        sale["items_hidden_count"],
        sale["sale_id"],
      ),
      on_click=lambda _, sale_id=sale["sale_id"]: State.toggle_cashbox_sale_detail(sale_id),
      class_name="mt-2 cursor-pointer",
    ),
    # Footer: Monto + Acciones
    rx.el.div(
      rx.el.span(
        State.currency_symbol,
        sale["amount"].to_string(),
        class_name="text-base font-semibold tabular-nums text-slate-900 whitespace-nowrap",
      ),
      rx.el.div(
        rx.el.button(
          rx.icon("printer", class_name="h-4 w-4"),
          " Reimprimir",
          on_click=lambda _, sale_id=sale["sale_id"]: State.reprint_sale_receipt(sale_id),
          disabled=sale["is_deleted"],
          title="Reimprimir",
          aria_label="Reimprimir",
          class_name=rx.cond(
            sale["is_deleted"],
            "inline-flex items-center gap-1 text-xs text-slate-300 cursor-not-allowed",
            BUTTON_STYLES["link_primary"],
          ),
        ),
        rx.el.button(
          rx.icon("trash-2", class_name="h-4 w-4"),
          " Eliminar",
          on_click=lambda _, sale_id=sale["sale_id"]: State.open_sale_delete_modal(sale_id),
          disabled=sale["is_deleted"] | ~State.current_user["privileges"]["delete_sales"],
          title="Eliminar",
          aria_label="Eliminar",
          class_name=rx.cond(
            sale["is_deleted"] | ~State.current_user["privileges"]["delete_sales"],
            "inline-flex items-center gap-1 text-xs text-slate-300 cursor-not-allowed",
            BUTTON_STYLES["link_danger"],
          ),
        ),
        class_name="flex items-center gap-3",
      ),
      class_name="flex flex-col gap-2 mt-3 pt-2 border-t border-slate-100",
    ),
    class_name="bg-white border border-slate-200 rounded-xl p-4 shadow-sm",
  )


def sale_row(sale: rx.Var[dict]) -> rx.Component:
  return rx.el.tr(
    rx.el.td(
      sale["timestamp"],
      class_name="py-3.5 px-4 align-top text-[13px] text-slate-500 whitespace-nowrap",
    ),
    rx.el.td(
      sale["user"],
      class_name="py-3.5 px-4 align-top text-sm font-medium text-slate-700",
    ),
    rx.el.td(
      payment_method_badge(sale["payment_method"]),
      rx.el.div(
        render_payment_details(sale["payment_details"]),
        class_name="mt-1",
      ),
      rx.cond(
        sale["is_deleted"],
        rx.el.div(
          info_badge("Venta eliminada", variant="danger"),
          rx.el.p(
            sale["delete_reason"],
            class_name="text-xs text-red-600 mt-1",
          ),
          class_name="mt-2",
        ),
        rx.fragment(),
      ),
      class_name="py-3.5 px-4 align-top text-sm text-slate-700",
    ),
    rx.el.td(
      rx.el.span(
        State.currency_symbol,
        sale["amount"].to_string(),
        class_name="text-base font-semibold text-slate-900 tabular-nums tracking-tight",
      ),
      class_name="py-3.5 px-4 text-right align-top",
    ),
    rx.el.td(
      sale_items_list(
        sale["items"],
        sale["items_preview"],
        sale["items_hidden_count"],
        sale["sale_id"],
      ),
      on_click=lambda _, sale_id=sale["sale_id"]: State.toggle_cashbox_sale_detail(sale_id),
      class_name="py-3.5 px-4 align-top min-w-[220px] cursor-pointer",
    ),
    rx.el.td(
      rx.el.div(
        rx.el.button(
          rx.icon("printer", class_name="h-4 w-4"),
          on_click=lambda _, sale_id=sale["sale_id"]: State.reprint_sale_receipt(sale_id),
          disabled=sale["is_deleted"],
          title="Reimprimir",
          aria_label="Reimprimir",
          class_name=rx.cond(
            sale["is_deleted"],
            "p-2 rounded-md text-slate-300 bg-transparent cursor-not-allowed",
            BUTTON_STYLES["icon_primary"],
          ),
        ),
        rx.el.button(
          rx.icon("trash-2", class_name="h-4 w-4"),
          on_click=lambda _, sale_id=sale["sale_id"]: State.open_sale_delete_modal(sale_id),
          disabled=sale["is_deleted"] | ~State.current_user["privileges"]["delete_sales"],
          title="Eliminar",
          aria_label="Eliminar",
          class_name=rx.cond(
            sale["is_deleted"] | ~State.current_user["privileges"]["delete_sales"],
            "p-2 rounded-md text-slate-300 bg-transparent cursor-not-allowed",
            BUTTON_STYLES["icon_danger"],
          ),
        ),
        class_name=(
          "flex flex-col gap-2 sm:flex-row sm:justify-center "
          "rounded-full border border-slate-200/80 bg-white/80 px-2 py-1 shadow-sm"
        ),
      ),
      class_name="py-3.5 px-4 align-top",
    ),
    class_name=(
      "border-b border-slate-100 transition-colors hover:bg-indigo-50/30 "
      "odd:bg-white even:bg-slate-50/30"
    ),
  )
