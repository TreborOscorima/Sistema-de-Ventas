"""Página dedicada al Generador Masivo de Etiquetas."""
import reflex as rx
from app.state import State
from app.components.ui import page_header

# Patrón CSS que simula barras de código de barras en la vista previa
_BARCODE_PATTERN = (
    "repeating-linear-gradient(90deg, "
    "#1e293b 0px, #1e293b 1.5px, "
    "transparent 1.5px, transparent 3px, "
    "#1e293b 3px, #1e293b 5px, "
    "transparent 5px, transparent 6.5px, "
    "#1e293b 6.5px, #1e293b 9px, "
    "transparent 9px, transparent 10.5px, "
    "#1e293b 10.5px, #1e293b 11.5px, "
    "transparent 11.5px, transparent 13px"
    ")"
)


# ─── Componente: Etiqueta de muestra ─────────────────────────────────────────

def _sample_label_card() -> rx.Component:
    """Etiqueta de ejemplo que muestra el diseño real del PDF con datos de muestra."""
    return rx.el.div(
        # Tarjeta de etiqueta ampliada
        rx.el.div(
            # ── Nombre + Precio ──
            rx.el.div(
                rx.el.span(
                    "Producto de Ejemplo",
                    class_name="text-sm font-bold text-slate-800 truncate",
                ),
                rx.el.span(
                    State.currency_symbol,
                    " 12.50",
                    class_name="text-base font-bold text-indigo-600 whitespace-nowrap shrink-0 ml-2",
                ),
                class_name="flex items-start justify-between gap-1",
            ),
            # ── Categoría (medium / large) ──
            rx.cond(
                State.label_size != "small",
                rx.el.span(
                    "Categoría Demo",
                    class_name="text-[10px] text-slate-500 leading-none",
                ),
                rx.fragment(),
            ),
            # ── Precio de costo (large + show_purchase_price) ──
            rx.cond(
                (State.label_size == "large") & State.label_show_purchase_price,
                rx.el.div(
                    rx.el.span(
                        "Costo: ",
                        State.currency_symbol,
                        " 8.00",
                        class_name="text-[9px] text-slate-400",
                    ),
                    class_name="w-full flex justify-end",
                ),
                rx.fragment(),
            ),
            # ── Código de barras visual ──
            rx.el.div(
                rx.el.div(
                    style={"height": "36px", "background": _BARCODE_PATTERN},
                    class_name="w-full rounded overflow-hidden",
                ),
                rx.el.span(
                    "1234567890123",
                    class_name="text-[9px] font-mono text-slate-500 text-center",
                ),
                class_name="flex flex-col items-center gap-1 mt-auto pt-3",
            ),
            class_name=(
                "border-2 border-dashed border-slate-300 rounded-xl p-4 bg-white "
                "flex flex-col gap-1.5 shadow-sm w-72"
            ),
        ),
        # Sub-texto con tamaño real
        rx.el.div(
            rx.el.span(
                rx.cond(
                    State.label_size == "small",
                    "50×30 mm",
                    rx.cond(State.label_size == "medium", "70×40 mm", "100×60 mm"),
                ),
                class_name="font-mono",
            ),
            rx.el.span("· ejemplo de diseño", class_name="text-slate-400"),
            class_name="flex items-center gap-1.5 text-xs text-slate-500 justify-center mt-3",
        ),
        class_name="flex flex-col items-center py-6",
    )


# ─── Componente: Fila de resultado de búsqueda ───────────────────────────────

def _search_result_row(p: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(p["description"], class_name="text-sm text-slate-700 truncate"),
            rx.el.span(p["barcode"], class_name="text-xs font-mono text-slate-400 truncate"),
            class_name="flex flex-col min-w-0",
        ),
        rx.el.button(
            rx.icon("plus", class_name="h-3.5 w-3.5"),
            on_click=State.add_label_specific_product(p["item_key"]),
            class_name=(
                "shrink-0 text-indigo-600 hover:text-indigo-800 "
                "border border-indigo-200 rounded-full p-0.5 hover:bg-indigo-50"
            ),
        ),
        class_name=(
            "flex items-center justify-between gap-2 px-3 py-1.5 "
            "hover:bg-slate-50 border-b border-slate-50 last:border-0 cursor-pointer"
        ),
        on_click=State.add_label_specific_product(p["item_key"]),
    )


# ─── Componente: Fila de producto específico seleccionado ────────────────────

def _specific_item_row(item: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(item["description"], class_name="text-sm text-slate-700 truncate"),
            rx.el.span(item["barcode"], class_name="text-xs font-mono text-slate-400 truncate"),
            class_name="flex flex-col min-w-0 flex-1",
        ),
        # Controles de cantidad
        rx.el.div(
            rx.el.button(
                "−",
                on_click=State.decrement_label_specific_qty(item["item_key"]),
                class_name=(
                    "w-6 h-6 flex items-center justify-center "
                    "border border-slate-200 rounded text-sm hover:bg-slate-100 select-none"
                ),
            ),
            rx.el.span(
                item["qty"].to_string(),
                class_name="w-7 text-center text-sm font-medium tabular-nums",
            ),
            rx.el.button(
                "+",
                on_click=State.increment_label_specific_qty(item["item_key"]),
                class_name=(
                    "w-6 h-6 flex items-center justify-center "
                    "border border-slate-200 rounded text-sm hover:bg-slate-100 select-none"
                ),
            ),
            rx.el.button(
                rx.icon("x", class_name="h-3 w-3 text-red-400"),
                on_click=State.remove_label_specific_product(item["item_key"]),
                class_name="ml-1.5 p-0.5 hover:text-red-600 rounded",
            ),
            class_name="flex items-center gap-1 shrink-0",
        ),
        class_name="flex items-center gap-2 py-1.5 border-b border-slate-50 last:border-0",
    )


# ─── Sección: Productos específicos ──────────────────────────────────────────

def _specific_products_section() -> rx.Component:
    return rx.el.div(
        # Input de búsqueda
        rx.el.div(
            rx.el.label(
                "Buscar productos",
                class_name="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1",
            ),
            rx.el.input(
                placeholder="Nombre o código de barras…",
                value=State.label_search_query,
                on_change=State.set_label_search_query,
                class_name=(
                    "w-full border border-slate-200 rounded-lg px-3 py-2 text-sm "
                    "focus:outline-none focus:ring-2 focus:ring-indigo-300"
                ),
            ),
            class_name="flex flex-col gap-1",
        ),
        # Resultados de búsqueda (dropdown-like)
        rx.cond(
            State.label_search_results.length() > 0,
            rx.el.div(
                rx.foreach(State.label_search_results, _search_result_row),
                class_name=(
                    "border border-indigo-100 rounded-lg overflow-hidden "
                    "max-h-44 overflow-y-auto bg-white shadow-sm"
                ),
            ),
            rx.fragment(),
        ),
        # Productos seleccionados
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Seleccionados",
                    class_name="text-xs font-semibold text-slate-600 uppercase tracking-wide",
                ),
                rx.cond(
                    State.label_specific_items.length() > 0,
                    rx.el.span(
                        State.label_specific_items.length().to_string() + " productos",
                        class_name="text-xs text-indigo-600 font-medium",
                    ),
                    rx.fragment(),
                ),
                class_name="flex items-center justify-between mb-1",
            ),
            rx.cond(
                State.label_specific_items.length() > 0,
                rx.el.div(
                    rx.foreach(State.label_specific_items, _specific_item_row),
                    class_name="max-h-56 overflow-y-auto",
                ),
                rx.el.p(
                    "Busca productos arriba y presiona + para agregarlos.",
                    class_name="text-xs text-slate-400 py-2",
                ),
            ),
        ),
        class_name="flex flex-col gap-3",
    )


# ─── Sección: Configuración ───────────────────────────────────────────────────

def _config_card() -> rx.Component:
    return rx.el.div(
        rx.el.h3(
            "Configuración de impresión",
            class_name="text-sm font-semibold text-slate-700 mb-4",
        ),

        # Formato de página
        rx.el.div(
            rx.el.label(
                "Formato de impresión",
                class_name="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1",
            ),
            rx.el.select(
                rx.el.option("A4 — Impresora normal (stickers troquelados)", value="a4"),
                rx.el.option("Rollo térmico 58 mm (cajera / portable)", value="thermal_58"),
                rx.el.option("Rollo térmico 80 mm (Zebra / industrial)", value="thermal_80"),
                value=State.label_page_format,
                on_change=State.set_label_page_format,
                class_name="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white",
            ),
            class_name="flex flex-col gap-1",
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
                rx.el.option("Productos específicos", value="specific"),
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

        # Filtro por categoría (no aplica en modo específico)
        rx.cond(
            State.label_filter != "specific",
            rx.el.div(
                rx.el.label(
                    "Categoría",
                    class_name="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1",
                ),
                rx.el.select(
                    rx.el.option("Todas las categorías", value=""),
                    rx.foreach(
                        State.label_available_categories,
                        lambda cat: rx.el.option(cat, value=cat),
                    ),
                    value=State.label_category,
                    on_change=State.set_label_category,
                    class_name="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.fragment(),
        ),

        # Sección de búsqueda/selección (solo en modo específico)
        rx.cond(
            State.label_filter == "specific",
            _specific_products_section(),
            rx.fragment(),
        ),

        # Copias por etiqueta (oculto en modo específico; usa qty por producto)
        rx.cond(
            State.label_filter != "specific",
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
            rx.fragment(),
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


def _preview_card() -> rx.Component:
    return rx.el.div(
        # Header
        rx.el.div(
            rx.el.h3(
                "Vista previa de etiqueta",
                class_name="text-sm font-semibold text-slate-700",
            ),
            _size_badge(State.label_size),
            class_name="flex items-center justify-between",
        ),

        # Etiqueta de muestra única (siempre visible)
        _sample_label_card(),

        # Badge de conteo (aparece después de "Vista previa")
        rx.cond(
            State.label_preview_loaded,
            rx.cond(
                State.label_preview_count > 0,
                rx.el.div(
                    rx.icon("circle_check", class_name="h-4 w-4 text-emerald-500 shrink-0"),
                    rx.el.span(
                        State.label_preview_count.to_string(),
                        " productos listos para imprimir",
                        class_name="text-sm text-slate-700",
                    ),
                    class_name=(
                        "flex items-center gap-2 justify-center "
                        "bg-emerald-50 border border-emerald-100 rounded-lg py-2 px-4"
                    ),
                ),
                rx.el.div(
                    rx.icon("triangle_alert", class_name="h-4 w-4 text-amber-500 shrink-0"),
                    rx.el.span(
                        "No hay productos con los filtros seleccionados.",
                        class_name="text-sm text-slate-600",
                    ),
                    class_name=(
                        "flex items-center gap-2 justify-center "
                        "bg-amber-50 border border-amber-100 rounded-lg py-2 px-4"
                    ),
                ),
            ),
            rx.el.p(
                "Haz clic en «Vista previa» para contar los productos que se imprimirán.",
                class_name="text-xs text-slate-400 text-center",
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

        rx.el.div(
            rx.el.div(
                rx.icon("info", class_name="h-4 w-4 text-indigo-500 shrink-0"),
                rx.el.p(
                    "Configura el tamaño y filtro, luego haz clic en «Vista previa» para ver cómo quedarán las etiquetas antes de descargar el PDF.",
                    class_name="text-sm text-slate-600",
                ),
                class_name="flex items-start gap-2",
            ),
            class_name="bg-indigo-50 border border-indigo-100 rounded-xl px-4 py-3",
        ),

        # Layout en 2 columnas: configuración | preview visual
        rx.el.div(
            _config_card(),
            _preview_card(),
            class_name="grid grid-cols-1 lg:grid-cols-2 gap-6",
        ),

        class_name="flex flex-col gap-6",
        on_mount=State.load_label_categories,
    )
