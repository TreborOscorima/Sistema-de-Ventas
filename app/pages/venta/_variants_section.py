import reflex as rx
from app.state import State
from app.components.ui import BUTTON_STYLES, modal_container


def _batch_picker_row(option: rx.Var[dict]) -> rx.Component:
    """Fila del selector manual de lote en el POS."""
    return rx.el.button(
        rx.el.div(
            rx.el.div(
                rx.icon("flask-round", class_name="h-4 w-4 text-emerald-600 shrink-0"),
                rx.el.span(
                    option["batch_number"],
                    class_name="font-mono font-semibold text-slate-800",
                ),
                rx.cond(
                    option["is_current"],
                    rx.el.span(
                        "Actual",
                        class_name="text-[10px] font-semibold uppercase tracking-wide text-emerald-700 bg-emerald-100 border border-emerald-200 rounded-full px-1.5 py-0.5",
                    ),
                    rx.fragment(),
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.div(
                rx.el.span(
                    rx.icon("calendar", class_name="h-3 w-3 inline mr-1"),
                    rx.cond(
                        option["expiration_date"] != "",
                        option["expiration_date"],
                        rx.el.span("Sin vencimiento", class_name="italic text-slate-400"),
                    ),
                    class_name="text-xs text-slate-600",
                ),
                rx.el.span(
                    rx.icon("package", class_name="h-3 w-3 inline mr-1"),
                    "Stock: ",
                    option["stock"].to_string(),
                    class_name="text-xs text-slate-600",
                ),
                class_name="flex items-center gap-3 mt-1",
            ),
            class_name="flex flex-col items-start text-left",
        ),
        on_click=lambda: State.select_batch_for_item(option["id"]),
        type="button",
        class_name=(
            "w-full px-3 py-2 border border-slate-200 rounded-lg "
            "hover:bg-emerald-50 hover:border-emerald-300 transition-colors"
        ),
    )


def _variant_picker_cell(cell: rx.Var[dict]) -> rx.Component:
    """Celda de la grilla talla×color del selector visual de variante."""
    return rx.cond(
        cell["is_placeholder"],
        # Combinación inexistente: celda vacía
        rx.el.div(
            rx.el.span("—", class_name="text-slate-300"),
            class_name=(
                "h-16 flex items-center justify-center border border-dashed "
                "border-slate-200 rounded-lg bg-slate-50/50"
            ),
        ),
        # Celda real: botón con stock + SKU
        rx.el.button(
            rx.el.div(
                rx.el.span(
                    cell["stock"].to_string(),
                    class_name=rx.cond(
                        cell["available"],
                        "text-base font-bold text-slate-800",
                        "text-base font-bold text-red-500",
                    ),
                ),
                rx.el.span(
                    rx.cond(
                        cell["available"], "disp.", "agotado"
                    ),
                    class_name="text-[10px] text-slate-500",
                ),
                class_name="flex flex-col items-center leading-none",
            ),
            on_click=lambda: State.select_variant_for_sale(cell["variant_id"]),
            disabled=~cell["available"],
            type="button",
            title=cell["sku"],
            aria_label=cell["sku"],
            class_name=rx.cond(
                cell["available"],
                (
                    "h-16 flex items-center justify-center border-2 border-indigo-200 "
                    "rounded-lg bg-white hover:bg-indigo-50 hover:border-indigo-400 "
                    "active:bg-indigo-100 transition-colors cursor-pointer"
                ),
                (
                    "h-16 flex items-center justify-center border border-slate-200 "
                    "rounded-lg bg-slate-100 cursor-not-allowed opacity-60"
                ),
            ),
        ),
    )


def _variant_picker_row(row: rx.Var[dict]) -> rx.Component:
    """Fila de la grilla talla×color: encabezado de talla + celdas por color."""
    return rx.el.div(
        rx.el.div(
            row["size"],
            class_name=(
                "h-16 flex items-center justify-center text-sm font-semibold "
                "text-slate-700 bg-slate-100 rounded-lg px-2 min-w-[3rem]"
            ),
        ),
        rx.el.div(
            rx.foreach(row["cells"], _variant_picker_cell),
            class_name="grid gap-1.5 flex-1",
            style={
                "gridTemplateColumns": "repeat(auto-fit, minmax(2.75rem, 1fr))",
            },
        ),
        class_name="flex items-stretch gap-1.5",
    )


def variant_picker_modal() -> rx.Component:
    """Modal selector visual de variante (grilla talla × color).

    Aparece automáticamente cuando el cajero elige un producto con variantes
    desde el grid visual. Cada celda muestra stock disponible y al hacer click
    agrega esa variante específica al carrito (vía SKU).
    """
    body = rx.el.div(
        rx.cond(
            State.variant_picker_loading,
            rx.el.div(
                rx.spinner(size="2"),
                rx.el.span(
                    "Cargando variantes…", class_name="text-sm text-slate-500"
                ),
                class_name="flex items-center justify-center gap-2 py-8",
            ),
            rx.cond(
                State.variant_picker_rows.length() > 0,  # type: ignore[union-attr]
                rx.el.div(
                    # Header de colores
                    rx.el.div(
                        rx.el.div(
                            "",
                            class_name="min-w-[3rem]",
                        ),
                        rx.el.div(
                            rx.foreach(
                                State.variant_picker_colors,
                                lambda c: rx.el.div(
                                    c,
                                    class_name=(
                                        "h-8 flex items-center justify-center text-xs "
                                        "font-semibold text-slate-600 bg-slate-50 "
                                        "rounded-md px-1 truncate"
                                    ),
                                    title=c,
                                ),
                            ),
                            class_name="grid gap-1.5 flex-1",
                            style={
                                "gridTemplateColumns": "repeat(auto-fit, minmax(2.75rem, 1fr))",
                            },
                        ),
                        class_name="flex items-stretch gap-1.5 mb-1",
                    ),
                    # Filas (talla)
                    rx.el.div(
                        rx.foreach(
                            State.variant_picker_rows, _variant_picker_row
                        ),
                        class_name="flex flex-col gap-1.5",
                    ),
                    class_name="max-h-[60vh] overflow-y-auto",
                ),
                rx.el.div(
                    rx.icon(
                        "triangle-alert",
                        class_name="h-8 w-8 text-amber-500 mx-auto",
                    ),
                    rx.el.p(
                        "Este producto no tiene variantes registradas.",
                        class_name="text-sm text-slate-600 text-center mt-2",
                    ),
                    class_name="py-6",
                ),
            ),
        ),
        class_name="py-2",
    )

    footer = rx.el.button(
        "Cancelar",
        on_click=State.close_variant_picker,
        type="button",
        class_name=f"{BUTTON_STYLES['secondary']} w-full",
    )

    return modal_container(
        is_open=State.variant_picker_open,
        on_close=State.close_variant_picker,
        title=rx.el.span(
            rx.icon(
                "shirt", class_name="h-4 w-4 inline mr-1.5 text-violet-600"
            ),
            "Seleccionar variante",
        ),
        description=State.variant_picker_description,
        children=[body],
        footer=footer,
        max_width="max-w-2xl",
    )


def batch_picker_modal() -> rx.Component:
    """Modal selector manual de lote para un ítem del carrito.

    Permite al cajero cambiar el lote auto-asignado por FEFO.
    Útil cuando el cliente pide un lote específico (farmacias).
    """
    body = rx.el.div(
        rx.cond(
            State.batch_picker_loading,
            rx.el.div(
                rx.spinner(size="2"),
                rx.el.span("Cargando lotes…", class_name="text-sm text-slate-500"),
                class_name="flex items-center justify-center gap-2 py-8",
            ),
            rx.cond(
                State.batch_picker_options.length() > 0,  # type: ignore[union-attr]
                rx.el.div(
                    rx.foreach(State.batch_picker_options, _batch_picker_row),
                    class_name="flex flex-col gap-2 max-h-[60vh] overflow-y-auto",
                ),
                rx.el.div(
                    rx.icon("triangle-alert", class_name="h-8 w-8 text-amber-500 mx-auto"),
                    rx.el.p(
                        "No hay lotes con stock disponible para este producto.",
                        class_name="text-sm text-slate-600 text-center mt-2",
                    ),
                    class_name="py-6",
                ),
            ),
        ),
        class_name="py-2",
    )

    footer = rx.el.button(
        "Cancelar",
        on_click=State.close_batch_picker,
        type="button",
        class_name=f"{BUTTON_STYLES['secondary']} w-full",
    )

    return modal_container(
        is_open=State.batch_picker_open,
        on_close=State.close_batch_picker,
        title=rx.el.span(
            rx.icon("flask-round", class_name="h-4 w-4 inline mr-1.5 text-emerald-600"),
            "Seleccionar lote",
        ),
        description=State.batch_picker_description,
        children=[body],
        footer=footer,
        max_width="max-w-md",
    )
