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
    ("Todos los tipos", ""),
    ("Venta", "Venta"),
    ("Re Ajuste Inventario", "Re Ajuste Inventario"),
    ("Ingreso", "Ingreso"),
    ("Compra", "Compra"),
    ("Importacion", "Importacion"),
    ("Devolucion", "Devolucion"),
]


def _type_badge(movement_type: rx.Var) -> rx.Component:
    return rx.el.span(
        movement_type,
        class_name=rx.match(
            movement_type,
            ("Venta",                "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700"),
            ("Re Ajuste Inventario", "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-700"),
            ("Ingreso",              "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700"),
            ("Compra",               "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700"),
            ("Importacion",          "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700"),
            ("Devolucion",           "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-700"),
            "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600",
        ),
    )


def _filter_field(label: str, control: rx.Component) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-xs font-medium text-slate-500 mb-1.5"),
        control,
        class_name="flex flex-col min-w-0",
    )


def movements_section() -> rx.Component:
    """Sección colapsable de historial de movimientos de stock."""
    return rx.el.div(

        # ── Header ────────────────────────────────────────────────
        rx.el.div(
            # Lado izquierdo: ícono + título + badge
            rx.el.div(
                rx.el.div(
                    rx.icon("history", class_name="h-5 w-5 text-indigo-500"),
                    class_name="flex items-center justify-center h-9 w-9 rounded-lg bg-indigo-50",
                ),
                rx.el.div(
                    rx.el.h2("Historial de Movimientos", class_name="text-base font-semibold text-slate-800"),
                    rx.el.p(
                        "Registro completo de entradas, salidas y ajustes de stock",
                        class_name="text-xs text-slate-400 hidden sm:block",
                    ),
                    class_name="flex flex-col",
                ),
                rx.cond(
                    State.movements_total_count > 0,
                    rx.el.span(
                        State.movements_total_count.to_string(),
                        " reg.",
                        class_name="hidden sm:inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-600",
                    ),
                    rx.fragment(),
                ),
                class_name="flex items-center gap-3",
            ),
            # Lado derecho: acciones
            rx.el.div(
                rx.cond(
                    State.movements_section_open,
                    rx.el.button(
                        rx.icon("download", class_name="h-4 w-4"),
                        rx.el.span("Exportar Excel", class_name="hidden sm:inline"),
                        on_click=State.export_movements_to_excel,
                        class_name=BUTTON_STYLES["success_sm"],
                    ),
                    rx.fragment(),
                ),
                rx.el.button(
                    rx.cond(
                        State.movements_section_open,
                        rx.fragment(
                            rx.icon("chevron-up", class_name="h-4 w-4"),
                            rx.el.span("Ocultar", class_name="hidden sm:inline"),
                        ),
                        rx.fragment(
                            rx.icon("chevron-down", class_name="h-4 w-4"),
                            rx.el.span("Ver historial", class_name="hidden sm:inline"),
                        ),
                    ),
                    on_click=State.toggle_movements_section,
                    class_name=BUTTON_STYLES["secondary_sm"],
                ),
                class_name="flex items-center gap-2 flex-shrink-0",
            ),
            class_name="flex items-center justify-between px-5 py-4",
        ),

        # ── Contenido colapsable ──────────────────────────────────
        rx.cond(
            State.movements_section_open,
            rx.el.div(

                # Filtros
                rx.el.div(
                    rx.el.div(
                        # Fila 1: búsqueda + tipo (2 columnas)
                        rx.el.div(
                            _filter_field(
                                "Buscar",
                                rx.debounce_input(
                                    rx.input(
                                        placeholder="Producto, código o descripción...",
                                        on_change=State.set_movements_search,
                                        class_name=INPUT_STYLES["default"],
                                    ),
                                    debounce_timeout=500,
                                ),
                            ),
                            _filter_field(
                                "Tipo de movimiento",
                                rx.el.select(
                                    rx.foreach(
                                        rx.Var.create(_TYPE_OPTIONS),
                                        lambda opt: rx.el.option(opt[0], value=opt[1]),
                                    ),
                                    value=State.movements_type_filter,
                                    on_change=State.set_movements_type_filter,
                                    class_name=INPUT_STYLES["default"],
                                ),
                            ),
                            class_name="grid grid-cols-1 sm:grid-cols-2 gap-3",
                        ),
                        # Fila 2: fechas + botón limpiar
                        rx.el.div(
                            _filter_field(
                                "Desde",
                                rx.el.input(
                                    type="date",
                                    value=State.movements_date_from,
                                    on_change=State.set_movements_date_from,
                                    class_name=INPUT_STYLES["default"],
                                ),
                            ),
                            _filter_field(
                                "Hasta",
                                rx.el.input(
                                    type="date",
                                    value=State.movements_date_to,
                                    on_change=State.set_movements_date_to,
                                    class_name=INPUT_STYLES["default"],
                                ),
                            ),
                            # Botón limpiar alineado al fondo
                            rx.el.div(
                                rx.el.label("‎", class_name="block text-xs mb-1.5"),
                                rx.el.button(
                                    rx.icon("filter-x", class_name="h-4 w-4"),
                                    "Limpiar filtros",
                                    on_click=State.clear_movements_filters,
                                    class_name=f"{BUTTON_STYLES['ghost']} w-full justify-center",
                                ),
                                class_name="flex flex-col min-w-0",
                            ),
                            class_name="grid grid-cols-1 sm:grid-cols-3 gap-3",
                        ),
                        class_name="flex flex-col gap-3",
                    ),
                    class_name="px-5 py-4 bg-slate-50/60 border-t border-b border-slate-100",
                ),

                # Tabla
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th(
                                    "Fecha",
                                    scope="col",
                                    class_name=f"{TABLE_STYLES['header_cell']} w-36",
                                ),
                                rx.el.th(
                                    "Tipo",
                                    scope="col",
                                    class_name=f"{TABLE_STYLES['header_cell']} w-40",
                                ),
                                rx.el.th(
                                    "Producto",
                                    scope="col",
                                    class_name=TABLE_STYLES["header_cell"],
                                ),
                                rx.el.th(
                                    "Cant.",
                                    scope="col",
                                    class_name=f"{TABLE_STYLES['header_cell']} text-center w-20",
                                ),
                                rx.el.th(
                                    "Usuario",
                                    scope="col",
                                    class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell w-28",
                                ),
                                rx.el.th(
                                    "Descripción / Motivo",
                                    scope="col",
                                    class_name=f"{TABLE_STYLES['header_cell']} hidden lg:table-cell",
                                ),
                                class_name=TABLE_STYLES["header"],
                            )
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                State.movements_list,
                                lambda m: rx.el.tr(
                                    # Fecha
                                    rx.el.td(
                                        rx.el.div(
                                            rx.el.span(
                                                m["timestamp_date"],
                                                class_name="text-xs font-medium text-slate-700 block",
                                            ),
                                            rx.el.span(
                                                m["timestamp_time"],
                                                class_name="text-xs text-slate-400 block",
                                            ),
                                            class_name="flex flex-col leading-tight",
                                        ),
                                        class_name="py-3 px-4 whitespace-nowrap align-middle",
                                    ),
                                    # Tipo
                                    rx.el.td(
                                        _type_badge(m["type"]),
                                        class_name="py-3 px-4 align-middle",
                                    ),
                                    # Producto
                                    rx.el.td(
                                        rx.el.div(
                                            rx.el.span(
                                                m["product_name"],
                                                class_name="text-sm font-medium text-slate-800 block leading-snug",
                                            ),
                                            rx.el.span(
                                                m["product_barcode"],
                                                class_name="text-xs text-slate-400 block font-mono mt-0.5",
                                            ),
                                            class_name="flex flex-col",
                                        ),
                                        class_name="py-3 px-4 align-middle",
                                    ),
                                    # Cantidad
                                    rx.el.td(
                                        rx.el.span(
                                            m["quantity"],
                                            class_name=rx.cond(
                                                m["quantity_positive"],
                                                "inline-flex items-center justify-center min-w-[3rem] px-2 py-0.5 rounded-md text-sm font-bold bg-emerald-50 text-emerald-700",
                                                "inline-flex items-center justify-center min-w-[3rem] px-2 py-0.5 rounded-md text-sm font-bold bg-red-50 text-red-600",
                                            ),
                                        ),
                                        class_name="py-3 px-4 text-center align-middle",
                                    ),
                                    # Usuario
                                    rx.el.td(
                                        rx.el.div(
                                            rx.icon("user", class_name="h-3 w-3 text-slate-400 flex-shrink-0"),
                                            rx.el.span(m["username"], class_name="text-xs text-slate-600"),
                                            class_name="flex items-center gap-1.5",
                                        ),
                                        class_name="py-3 px-4 hidden md:table-cell align-middle",
                                    ),
                                    # Descripción
                                    rx.el.td(
                                        rx.el.span(
                                            m["description"],
                                            class_name="text-xs text-slate-500 line-clamp-2 leading-relaxed",
                                        ),
                                        class_name="py-3 px-4 hidden lg:table-cell align-middle max-w-xs",
                                    ),
                                    class_name="border-b border-slate-50 hover:bg-slate-50/80 transition-colors",
                                ),
                            ),
                        ),
                        class_name="min-w-full divide-y divide-slate-100",
                    ),
                    class_name="overflow-x-auto",
                ),

                # Empty state
                rx.cond(
                    State.movements_list.length() == 0,
                    rx.el.div(
                        rx.icon("inbox", class_name="h-10 w-10 text-slate-300 mx-auto mb-3"),
                        rx.el.p(
                            "No hay movimientos que coincidan con los filtros.",
                            class_name="text-sm text-slate-500 text-center",
                        ),
                        class_name="flex flex-col items-center justify-center py-12",
                    ),
                    rx.fragment(),
                ),

                # Paginación
                rx.cond(
                    State.movements_total_pages > 1,
                    rx.el.div(
                        # Info de registros
                        rx.el.span(
                            "Página ",
                            State.movements_current_page.to_string(),
                            " de ",
                            State.movements_total_pages.to_string(),
                            " · ",
                            State.movements_total_count.to_string(),
                            " registros",
                            class_name="text-xs text-slate-400 hidden sm:block",
                        ),
                        pagination_controls(
                            current_page=State.movements_current_page,
                            total_pages=State.movements_total_pages,
                            on_prev=lambda: State.set_movements_page(State.movements_current_page - 1),
                            on_next=lambda: State.set_movements_page(State.movements_current_page + 1),
                        ),
                        class_name="flex items-center justify-between px-5 py-3 border-t border-slate-100",
                    ),
                    rx.fragment(),
                ),

                class_name="",
            ),
            rx.fragment(),
        ),

        class_name="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden",
    )
