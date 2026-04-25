"""Página dedicada al Generador Masivo de Etiquetas."""
import reflex as rx
from app.state import State
from app.components.ui import page_header


# ─── Sección: Configuración ───────────────────────────────────────────────────

def _config_card() -> rx.Component:
    return rx.el.div(
        rx.el.h3(
            "Configuración de impresión",
            class_name="text-sm font-semibold text-slate-700 mb-4",
        ),

        # Tamaño de etiqueta
        rx.el.div(
            rx.el.label(
                "Tamaño de etiqueta",
                class_name="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1",
            ),
            rx.el.select(
                rx.el.option("Pequeña — 50×30 mm (4 columnas)", value="small"),
                rx.el.option("Mediana — 70×40 mm (3 columnas)", value="medium"),
                rx.el.option("Grande — 100×60 mm (2 columnas)", value="large"),
                value=State.label_size,
                on_change=State.set_label_size,
                class_name="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white",
            ),
            class_name="flex flex-col gap-1",
        ),

        # Filtro de productos
        rx.el.div(
            rx.el.label(
                "Productos a etiquetar",
                class_name="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1",
            ),
            rx.el.select(
                rx.el.option("Todos los productos activos", value="all"),
                rx.el.option("Precio cambiado en los últimos N días", value="price_changed"),
                rx.el.option("Sin código de barras asignado", value="no_barcode"),
                value=State.label_filter,
                on_change=State.set_label_filter,
                class_name="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white",
            ),
            class_name="flex flex-col gap-1",
        ),

        # Días (visible solo cuando filtro == price_changed)
        rx.cond(
            State.label_filter == "price_changed",
            rx.el.div(
                rx.el.label(
                    "Últimos N días con cambio de precio",
                    class_name="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1",
                ),
                rx.el.input(
                    default_value=State.label_price_changed_days.to_string(),
                    type="text",
                    input_mode="numeric",
                    on_blur=State.set_label_price_changed_days,
                    class_name="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.fragment(),
        ),

        # Copias por etiqueta
        rx.el.div(
            rx.el.label(
                "Copias por etiqueta",
                class_name="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1",
            ),
            rx.el.input(
                default_value=State.label_copies.to_string(),
                type="text",
                input_mode="numeric",
                on_blur=State.set_label_copies,
                class_name="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm",
            ),
            class_name="flex flex-col gap-1",
        ),

        # Mostrar precio de compra (checkbox)
        rx.el.div(
            rx.el.label(
                rx.el.input(
                    type="checkbox",
                    default_checked=State.label_show_purchase_price,
                    on_change=State.set_label_show_purchase_price,
                    class_name="h-4 w-4 rounded border-slate-300 text-indigo-600",
                ),
                rx.el.span(
                    "Incluir precio de compra en etiqueta",
                    class_name="text-sm text-slate-700",
                ),
                class_name="flex items-center gap-2 cursor-pointer",
            ),
        ),

        # Separador
        rx.el.hr(class_name="border-slate-100"),

        # Botones de acción
        rx.el.div(
            rx.el.button(
                rx.icon("search", class_name="h-4 w-4"),
                "Vista previa",
                on_click=State.load_label_preview,
                disabled=State.is_loading,
                class_name=(
                    "flex items-center gap-2 px-4 py-2 border border-slate-200 "
                    "rounded-lg hover:bg-slate-50 text-sm font-medium disabled:opacity-50"
                ),
            ),
            rx.el.button(
                rx.cond(
                    State.is_loading,
                    rx.el.div(
                        rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"),
                        "Generando…",
                        class_name="flex items-center gap-2",
                    ),
                    rx.el.div(
                        rx.icon("download", class_name="h-4 w-4"),
                        "Descargar PDF",
                        class_name="flex items-center gap-2",
                    ),
                ),
                on_click=State.download_label_pdf,
                disabled=State.is_loading,
                class_name=(
                    "flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white "
                    "rounded-lg hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
                ),
            ),
            class_name="flex gap-3 flex-wrap",
        ),

        class_name="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col gap-4",
    )


# ─── Sección: Preview ─────────────────────────────────────────────────────────

def _size_badge(size: rx.Var) -> rx.Component:
    return rx.cond(
        size == "small",
        rx.el.span("50×30 mm", class_name="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded font-mono"),
        rx.cond(
            size == "medium",
            rx.el.span("70×40 mm", class_name="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded font-mono"),
            rx.el.span("100×60 mm", class_name="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded font-mono"),
        ),
    )


def _preview_product_row(p: rx.Var) -> rx.Component:
    return rx.el.li(
        rx.el.div(
            rx.el.span(p["description"], class_name="text-sm text-slate-700 truncate"),
            rx.el.span(p["barcode"], class_name="text-xs font-mono text-slate-400"),
            class_name="flex flex-col gap-0.5 min-w-0",
        ),
        rx.el.span(
            State.currency_symbol + p["sale_price"].to_string(),
            class_name="text-sm font-semibold text-indigo-600 tabular-nums shrink-0",
        ),
        class_name="flex items-center justify-between gap-3 py-1.5 px-3 hover:bg-slate-50 rounded",
    )


def _preview_card() -> rx.Component:
    return rx.el.div(
        # Header del card de preview
        rx.el.div(
            rx.el.h3(
                "Vista previa de productos",
                class_name="text-sm font-semibold text-slate-700",
            ),
            rx.cond(
                State.label_preview_loaded,
                rx.el.div(
                    rx.el.span(
                        State.label_preview_count.to_string() + " productos",
                        class_name="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full",
                    ),
                    _size_badge(State.label_size),
                    class_name="flex items-center gap-2",
                ),
                rx.fragment(),
            ),
            class_name="flex items-center justify-between",
        ),

        # Estado vacío antes del primer preview
        rx.cond(
            ~State.label_preview_loaded,
            rx.el.div(
                rx.icon("printer", class_name="h-10 w-10 text-slate-300 mx-auto mb-3"),
                rx.el.p(
                    "Haz clic en «Vista previa» para ver los productos que se incluirán en el PDF.",
                    class_name="text-sm text-slate-400 text-center",
                ),
                class_name="flex flex-col items-center justify-center py-12",
            ),
            # Lista de productos
            rx.el.div(
                rx.cond(
                    State.label_preview_products.length() > 0,
                    rx.el.ul(
                        rx.foreach(State.label_preview_products, _preview_product_row),
                        class_name="divide-y divide-slate-50",
                    ),
                    rx.el.p(
                        "No hay productos con los filtros seleccionados.",
                        class_name="text-sm text-slate-400 text-center py-8",
                    ),
                ),
                rx.cond(
                    State.label_preview_count > 20,
                    rx.el.p(
                        "…y " + (State.label_preview_count - 20).to_string() + " más",
                        class_name="text-xs text-slate-400 text-center pt-2",
                    ),
                    rx.fragment(),
                ),
                class_name="max-h-96 overflow-y-auto",
            ),
        ),

        class_name="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col gap-4",
    )


# ─── Página principal ─────────────────────────────────────────────────────────

def etiquetas_page() -> rx.Component:
    """Página dedicada al generador masivo de etiquetas con código de barras."""
    return rx.el.div(
        page_header(
            "ETIQUETAS",
            "Genera PDFs de etiquetas con código de barras listos para imprimir.",
        ),

        # Indicador de tamaño en el encabezado
        rx.el.div(
            rx.el.div(
                rx.icon("info", class_name="h-4 w-4 text-indigo-500 shrink-0"),
                rx.el.p(
                    "Configura el tamaño, filtro y copias, luego haz clic en «Vista previa» para ver qué productos se incluirán y descarga el PDF.",
                    class_name="text-sm text-slate-600",
                ),
                class_name="flex items-start gap-2",
            ),
            class_name="bg-indigo-50 border border-indigo-100 rounded-xl px-4 py-3",
        ),

        # Layout en 2 columnas: configuración | preview
        rx.el.div(
            _config_card(),
            _preview_card(),
            class_name="grid grid-cols-1 lg:grid-cols-2 gap-6",
        ),

        class_name="flex flex-col gap-6",
    )
