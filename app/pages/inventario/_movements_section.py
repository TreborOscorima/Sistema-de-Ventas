"""Sección de historial de movimientos de stock."""
import reflex as rx

from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    INPUT_STYLES,
    TABLE_STYLES,
    TYPOGRAPHY,
    pagination_controls,
)

_TYPE_OPTIONS = [
    ("Todos", ""),
    ("Venta", "Venta"),
    ("Re Ajuste Inventario", "Re Ajuste Inventario"),
    ("Ingreso", "Ingreso"),
    ("Compra", "Compra"),
    ("Importacion", "Importacion"),
    ("Devolucion", "Devolucion"),
]

_TYPE_COLORS: dict[str, str] = {
    "Venta": "bg-red-100 text-red-800",
    "Re Ajuste Inventario": "bg-amber-100 text-amber-800",
    "Ingreso": "bg-emerald-100 text-emerald-800",
    "Compra": "bg-blue-100 text-blue-800",
    "Importacion": "bg-indigo-100 text-indigo-800",
    "Devolucion": "bg-purple-100 text-purple-800",
}
_DEFAULT_TYPE_COLOR = "bg-slate-100 text-slate-700"


def _type_badge(movement_type: rx.Var) -> rx.Component:
    """Badge con color según tipo de movimiento."""
    return rx.el.span(
        movement_type,
        class_name=rx.match(
            movement_type,
            ("Venta", "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800"),
            ("Re Ajuste Inventario", "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800"),
            ("Ingreso", "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800"),
            ("Compra", "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800"),
            ("Importacion", "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800"),
            ("Devolucion", "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800"),
            "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700",
        ),
    )


def movements_section() -> rx.Component:
    """Sección colapsable de historial de movimientos de stock."""
    return rx.el.div(
        # ── Header colapsable ──────────────────────────────────────
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("history", class_name="h-5 w-5 text-indigo-600"),
                    rx.el.h2(
                        "HISTORIAL DE MOVIMIENTOS",
                        class_name=TYPOGRAPHY["section_title"],
                    ),
                    rx.cond(
                        State.movements_total_count > 0,
                        rx.el.span(
                            State.movements_total_count.to_string(),
                            " registros",
                            class_name="text-xs text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full",
                        ),
                        rx.fragment(),
                    ),
                    class_name="flex items-center gap-3",
                ),
                rx.el.div(
                    rx.cond(
                        State.movements_section_open,
                        rx.el.button(
                            rx.icon("download", class_name="h-4 w-4"),
                            "Exportar",
                            on_click=State.export_movements_to_excel,
                            class_name=BUTTON_STYLES["success_sm"],
                        ),
                        rx.fragment(),
                    ),
                    rx.el.button(
                        rx.cond(
                            State.movements_section_open,
                            rx.icon("chevron-up", class_name="h-4 w-4"),
                            rx.icon("chevron-down", class_name="h-4 w-4"),
                        ),
                        rx.cond(
                            State.movements_section_open,
                            "Ocultar",
                            "Ver historial",
                        ),
                        on_click=State.toggle_movements_section,
                        class_name=BUTTON_STYLES["ghost"],
                    ),
                    class_name="flex items-center gap-2",
                ),
                class_name="flex items-center justify-between",
            ),
            class_name="p-4 cursor-pointer",
            on_click=State.toggle_movements_section,
        ),

        # ── Contenido (visible sólo cuando está abierto) ──────────
        rx.cond(
            State.movements_section_open,
            rx.el.div(
                # Filtros
                rx.el.div(
                    rx.el.div(
                        rx.debounce_input(
                            rx.input(
                                placeholder="Buscar producto o descripción...",
                                on_change=State.set_movements_search,
                                class_name=INPUT_STYLES["default"],
                            ),
                            debounce_timeout=500,
                        ),
                        rx.el.select(
                            rx.foreach(
                                rx.Var.create(_TYPE_OPTIONS),
                                lambda opt: rx.el.option(opt[0], value=opt[1]),
                            ),
                            value=State.movements_type_filter,
                            on_change=State.set_movements_type_filter,
                            class_name=f"{INPUT_STYLES['default']} min-w-[180px]",
                        ),
                        rx.el.input(
                            type="date",
                            value=State.movements_date_from,
                            on_change=State.set_movements_date_from,
                            class_name=INPUT_STYLES["default"],
                            title="Desde",
                        ),
                        rx.el.input(
                            type="date",
                            value=State.movements_date_to,
                            on_change=State.set_movements_date_to,
                            class_name=INPUT_STYLES["default"],
                            title="Hasta",
                        ),
                        rx.el.button(
                            rx.icon("x", class_name="h-4 w-4"),
                            "Limpiar",
                            on_click=State.clear_movements_filters,
                            class_name=BUTTON_STYLES["ghost"],
                            title="Limpiar filtros",
                        ),
                        class_name="flex flex-wrap items-center gap-3",
                    ),
                    class_name="px-4 pb-3 border-b border-slate-100",
                ),

                # Tabla desktop
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("Fecha", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden sm:table-cell"),
                                rx.el.th("Tipo", scope="col", class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Producto", scope="col", class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Cant.", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center"),
                                rx.el.th("Usuario", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"),
                                rx.el.th("Descripción / Motivo", scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden lg:table-cell"),
                                class_name=TABLE_STYLES["header"],
                            )
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                State.movements_list,
                                lambda m: rx.el.tr(
                                    rx.el.td(
                                        m["timestamp"],
                                        class_name="py-3 px-4 text-xs text-slate-500 whitespace-nowrap hidden sm:table-cell",
                                    ),
                                    rx.el.td(
                                        _type_badge(m["type"]),
                                        class_name="py-3 px-4",
                                    ),
                                    rx.el.td(
                                        rx.el.div(
                                            rx.el.span(m["product_name"], class_name="font-medium text-sm"),
                                            rx.el.span(m["product_barcode"], class_name="text-xs text-slate-400 block"),
                                            class_name="flex flex-col",
                                        ),
                                        class_name="py-3 px-4",
                                    ),
                                    rx.el.td(
                                        rx.el.span(
                                            m["quantity"],
                                            class_name=rx.cond(
                                                m["quantity_positive"],
                                                "font-bold text-emerald-600",
                                                "font-bold text-red-600",
                                            ),
                                        ),
                                        class_name="py-3 px-4 text-center",
                                    ),
                                    rx.el.td(
                                        m["username"],
                                        class_name="py-3 px-4 text-sm text-slate-600 hidden md:table-cell",
                                    ),
                                    rx.el.td(
                                        rx.el.span(
                                            m["description"],
                                            class_name="text-xs text-slate-500 line-clamp-2",
                                        ),
                                        class_name="py-3 px-4 hidden lg:table-cell max-w-xs",
                                    ),
                                    class_name="border-b hover:bg-slate-50",
                                ),
                            ),
                        ),
                        class_name="min-w-full",
                    ),
                    class_name="overflow-x-auto",
                ),

                # Empty state
                rx.cond(
                    State.movements_list.length() == 0,
                    rx.el.p(
                        "No hay movimientos que coincidan con los filtros.",
                        class_name="text-slate-500 text-center py-8 text-sm",
                    ),
                    rx.fragment(),
                ),

                # Paginación
                rx.cond(
                    State.movements_total_pages > 1,
                    rx.el.div(
                        pagination_controls(
                            current_page=State.movements_current_page,
                            total_pages=State.movements_total_pages,
                            on_prev=lambda: State.set_movements_page(State.movements_current_page - 1),
                            on_next=lambda: State.set_movements_page(State.movements_current_page + 1),
                        ),
                        class_name="px-4 py-3 border-t border-slate-100",
                    ),
                    rx.fragment(),
                ),

                class_name="border-t border-slate-100",
            ),
            rx.fragment(),
        ),

        class_name="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden",
    )
