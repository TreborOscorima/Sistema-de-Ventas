import reflex as rx

from app.state import State
from app.components.ui import (
  BADGE_STYLES,
  BUTTON_STYLES,
  CARD_STYLES,
  TYPOGRAPHY,
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
                rx.el.div(
                    rx.el.span(
                        product["description"],
                        class_name="font-medium text-slate-900 text-sm",
                    ),
                    rx.cond(
                        product["is_kit"],
                        rx.el.span(
                            "KIT",
                            class_name="text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-semibold tracking-wide",
                        ),
                        rx.fragment(),
                    ),
                    class_name="flex items-center gap-1.5 flex-wrap",
                ),
                rx.el.span(
                    product["category"],
                    class_name=TYPOGRAPHY["caption"],
                ),
                class_name="flex flex-col gap-0.5",
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
