import reflex as rx
from app.state import State
from app.components.ui import BUTTON_STYLES, TABLE_STYLES
from ._cart_section import compact_sale_item_row, mobile_sale_item_card


def client_selector() -> rx.Component:
    """Selector de cliente para ventas a credito."""
    return rx.box(
        rx.cond(
            State.has_selected_client,
            # Vista compacta inline cuando hay cliente seleccionado
            rx.el.div(
                rx.icon("user", class_name="h-3.5 w-3.5 text-slate-400 shrink-0"),
                rx.el.span(
                    State.selected_client["name"],
                    class_name="text-sm font-semibold text-slate-700",
                ),
                rx.cond(
                    State.selected_client_has_dni,
                    rx.el.span(
                        rx.el.span(class_name="w-px h-3.5 bg-slate-200 inline-block"),
                        rx.el.span("DNI:", class_name="text-xs text-slate-400"),
                        rx.el.span(
                            State.selected_client["dni"],
                            class_name="text-xs font-mono text-slate-600",
                        ),
                        class_name="inline-flex items-center gap-1",
                    ),
                    rx.el.span(""),
                ),
                rx.el.div(class_name="w-px h-3.5 bg-slate-200 mx-0.5"),
                rx.badge(
                    "Crédito: ",
                    State.currency_symbol,
                    State.credit_available_display,
                    color_scheme="green",
                    variant="soft",
                    size="1",
                    class_name="whitespace-nowrap",
                ),
                rx.cond(
                    State.active_price_list_name != "",
                    rx.el.span(
                        rx.el.span(class_name="w-px h-3.5 bg-slate-200 inline-block"),
                        rx.el.span(
                            State.active_price_list_name,
                            class_name="text-xs font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 px-1.5 py-0.5 rounded-full leading-none",
                        ),
                        class_name="inline-flex items-center gap-1",
                    ),
                    rx.el.span(""),
                ),
                rx.el.button(
                    rx.icon("x", class_name="h-3.5 w-3.5"),
                    on_click=State.clear_selected_client,
                    title="Quitar cliente",
                    aria_label="Quitar cliente",
                    class_name="ml-auto p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors shrink-0",
                ),
                class_name="flex items-center gap-1.5 w-full flex-wrap",
            ),
            rx.vstack(
                rx.el.div(
                    rx.debounce_input(
                        rx.input(
                            value=State.client_search_query,
                            on_change=State.search_client_change,
                            placeholder="Buscar cliente (DNI o nombre)...",
                            class_name="flex-1 px-3 py-2.5 border border-slate-200 rounded-lg text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                        ),
                        debounce_timeout=600,
                    ),
                    rx.el.button(
                        rx.icon("plus", class_name="h-4 w-4"),
                        on_click=State.open_modal_from_pos,
                        class_name="h-10 w-10 flex items-center justify-center rounded-lg border text-indigo-600 hover:bg-indigo-50",
                        title="Nuevo cliente",
                        aria_label="Nuevo cliente",
                    ),
                    class_name="flex items-center gap-1 w-full",
                ),
                rx.cond(
                    State.client_suggestions.length() > 0,
                    rx.vstack(
                        rx.foreach(
                            State.client_suggestions,
                            lambda client: rx.button(
                                rx.vstack(
                                    rx.el.span(
                                        client["name"],
                                        class_name="font-medium text-slate-900",
                                    ),
                                    rx.el.span(
                                        "DNI: ",
                                        client["dni"],
                                        class_name="text-xs text-slate-500 font-mono",
                                    ),
                                    spacing="1",
                                    align="start",
                                    class_name="w-full",
                                ),
                                on_click=lambda _, c=client: State.select_client(c),
                                variant="ghost",
                                class_name="w-full justify-start text-left",
                            ),
                        ),
                        spacing="1",
                        class_name="w-full rounded-lg border bg-white shadow-sm p-1",
                    ),
                    rx.fragment(),
                ),
                spacing="1",
                class_name="w-full",
            ),
        ),
        class_name="w-full p-2.5 bg-white rounded-xl border shadow-sm",
    )


def quick_add_bar() -> rx.Component:
    """Barra de entrada rápida de productos - estilo POS responsive."""
    return rx.el.div(
        # Fila 1: Código de barra y Búsqueda (siempre visible)
        rx.el.div(
            # Código de barra — form-based: solo dispara evento al presionar Enter
            rx.el.div(
                rx.el.form(
                    rx.el.div(
                        rx.icon("scan-barcode", class_name="h-5 w-5 text-slate-400 flex-shrink-0"),
                        rx.el.input(
                            name="barcode",
                            id="venta_barcode_input",
                            key=State.sale_form_key.to_string(),
                            default_value=State.new_sale_item["barcode"],
                            placeholder="Código...",
                            class_name="flex-1 min-w-0 border-0 focus:ring-0 text-sm bg-transparent outline-none py-0 placeholder-slate-400",
                            type="text",
                            auto_complete="off",
                        ),
                        class_name="flex items-center gap-1 px-3 py-2 border rounded-lg bg-white focus-within:ring-2 focus-within:ring-indigo-500 w-full",
                    ),
                    on_submit=State.handle_barcode_form_submit,
                    reset_on_submit=True,
                    class_name="w-full",
                ),
                rx.cond(
                    State.last_scanned_label != "",
                    rx.el.span(
                        State.last_scanned_label,
                        class_name="text-xs text-slate-500 truncate",
                    ),
                    rx.fragment(),
                ),
                class_name="flex flex-col gap-1 w-full sm:w-56 lg:w-64",
            ),
            # Búsqueda de producto
            rx.el.div(
                rx.el.div(
                    rx.icon("search", class_name="h-5 w-5 text-slate-400 flex-shrink-0"),
                    rx.debounce_input(
                        rx.input(
                            value=State.new_sale_item["description"],
                            on_change=lambda val: State.handle_sale_change("description", val),
                            on_key_down=State.handle_autocomplete_keydown,
                            placeholder="Buscar producto...",
                            class_name="flex-1 min-w-0 border-0 focus:ring-0 text-sm bg-transparent outline-none py-0 placeholder-slate-400",
                        ),
                        debounce_timeout=600,
                    ),
                    class_name="flex items-center gap-1 px-3 py-2 border rounded-lg bg-white focus-within:ring-2 focus-within:ring-indigo-500 w-full",
                ),
                rx.cond(
                    State.autocomplete_results.length() > 0,
                    rx.el.div(
                        rx.foreach(
                            State.autocomplete_rows,
                            lambda suggestion: rx.el.button(
                                suggestion["description"],
                                on_click=lambda _, s=suggestion: State.select_product_for_sale(s),
                                class_name=rx.cond(
                                    suggestion["index"]
                                    == State.autocomplete_selected_index,
                                    "w-full text-left px-3 py-2.5 bg-indigo-50 text-sm border-b border-slate-100 last:border-0",
                                    "w-full text-left px-3 py-2.5 hover:bg-indigo-50 text-sm border-b border-slate-100 last:border-0",
                                ),
                            ),
                        ),
                        custom_attrs={"data-autocomplete-dropdown": "1"},
                        class_name="absolute z-20 left-0 right-0 mt-1 bg-white border rounded-lg shadow-xl max-h-60 overflow-y-auto",
                    ),
                    rx.fragment(),
                ),
                custom_attrs={"data-product-search": "1"},
                class_name="relative flex-1 min-w-0",
            ),
            class_name="flex flex-col sm:flex-row gap-2 flex-1",
        ),
        # Fila 2: Cantidad, Precio, Subtotal y Botón
        rx.el.div(
            # Cantidad
            rx.el.div(
                rx.el.label("Cant.", class_name="text-xs text-slate-500 sm:hidden"),
                rx.el.input(
                    type="number",
                    min="0.01",
                    step="0.01",
                    key=State.sale_form_key.to_string() + "_qty",
                    default_value=State.new_sale_item["quantity"].to_string(),
                    on_blur=lambda val: State.handle_sale_change("quantity", val),
                    class_name="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm text-center placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                    placeholder="1",
                ),
                class_name="flex flex-col gap-1 w-[88px] sm:w-20",
            ),
            # Precio
            rx.el.div(
                rx.el.div(
                    rx.el.label("Precio", class_name="text-xs text-slate-500 sm:hidden"),
                    rx.cond(
                        State.price_list_price_applied,
                        rx.el.span(
                            "Lista",
                            class_name="text-xs font-semibold text-indigo-600 bg-indigo-50 border border-indigo-200 rounded px-1.5 py-0.5 leading-none",
                        ),
                        rx.cond(
                            State.wholesale_price_applied,
                            rx.el.span(
                                "Mayorista",
                                class_name="text-xs font-semibold text-amber-600 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5 leading-none",
                            ),
                            rx.fragment(),
                        ),
                    ),
                    rx.cond(
                        State.promotion_applied,
                        rx.el.span(
                            State.promotion_name,
                            class_name="text-xs font-semibold text-emerald-600 bg-emerald-50 border border-emerald-200 rounded px-1.5 py-0.5 leading-none",
                        ),
                        rx.fragment(),
                    ),
                    class_name="flex items-center gap-1.5",
                ),
                rx.el.div(
                    rx.el.span(State.currency_symbol, class_name="text-slate-400 text-sm"),
                    rx.el.input(
                        type="number",
                        min="0",
                        step="0.01",
                        key=State.sale_form_key.to_string() + "_price",
                        default_value=State.sale_price_form_display,
                        on_blur=lambda val: State.handle_sale_change("price", val),
                        class_name="flex-1 min-w-0 border-0 focus:ring-0 text-sm bg-transparent outline-none text-right",
                    ),
                    class_name=rx.cond(
                        State.price_list_price_applied,
                        "flex items-center gap-1 px-3 py-2 border border-indigo-300 rounded-lg bg-indigo-50/50 focus-within:ring-2 focus-within:ring-indigo-500",
                        rx.cond(
                            State.wholesale_price_applied,
                            "flex items-center gap-1 px-3 py-2 border border-amber-300 rounded-lg bg-amber-50/50 focus-within:ring-2 focus-within:ring-amber-500",
                            rx.cond(
                                State.promotion_applied,
                                "flex items-center gap-1 px-3 py-2 border border-emerald-300 rounded-lg bg-emerald-50/50 focus-within:ring-2 focus-within:ring-emerald-500",
                                "flex items-center gap-1 px-3 py-2 border rounded-lg bg-white focus-within:ring-2 focus-within:ring-indigo-500",
                            ),
                        ),
                    ),
                ),
                class_name="flex flex-col gap-1 flex-1 min-w-[100px] sm:flex-none sm:w-28",
            ),
            # Subtotal
            rx.el.div(
                rx.el.label("Subtotal", class_name="text-xs text-slate-500 sm:hidden"),
                rx.el.div(
                    rx.el.span(
                        State.currency_symbol,
                        State.sale_subtotal_display,
                        class_name="text-sm font-semibold text-indigo-600",
                    ),
                    class_name="px-3 py-2 bg-slate-100 rounded-lg text-right h-[42px] flex items-center justify-end",
                ),
                class_name="flex flex-col gap-1 flex-1 min-w-[100px] sm:flex-none sm:w-28",
            ),
            # Botón añadir
            rx.el.button(
                rx.icon("plus", class_name="h-5 w-5"),
                rx.el.span("Añadir", class_name="sm:hidden"),
                on_click=State.add_item_to_sale,
                custom_attrs={"data-venta-add-btn": "1"},
                class_name=(
                    "inline-flex h-[42px] min-w-[106px] items-center justify-center gap-2 rounded-lg "
                    "bg-indigo-600 px-3.5 text-sm font-medium text-white hover:bg-indigo-700 "
                    "transition-colors sm:min-w-[120px]"
                ),
            ),
            class_name="flex flex-wrap items-end gap-2",
        ),
        custom_attrs={"data-quick-add-bar": "1"},
        class_name="flex flex-col gap-2 p-2.5 bg-slate-50 border-b",
    )


def products_table(embedded: bool = False) -> rx.Component:
    """Tabla de productos en la venta - responsive."""
    content = rx.el.div(
        # Header
        rx.el.div(
            rx.el.div(
                rx.icon("shopping-cart", class_name="h-5 w-5 text-indigo-600"),
                rx.el.span("Productos", class_name="font-semibold text-slate-800 sm:hidden"),
                rx.el.span("PRODUCTOS EN VENTA", class_name="font-semibold text-slate-800 hidden sm:inline"),
                rx.el.span(
                    "(", State.new_sale_items.length().to_string(), ")",
                    class_name="text-sm text-slate-500",
                ),
                class_name="flex items-center gap-1",
            ),
            rx.el.button(
                rx.icon("trash-2", class_name="h-4 w-4"),
                rx.el.span("Vaciar", class_name="hidden sm:inline"),
                on_click=State.clear_sale_items,
                class_name="flex items-center gap-1 px-2 sm:px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors",
            ),
            class_name="flex items-center justify-between p-2.5 bg-white border-b",
        ),
        # Contenido
        rx.el.div(
            rx.cond(
                State.new_sale_items.length() > 0,
                rx.el.div(
                    # Vista móvil: cards
                    rx.el.div(
                        rx.foreach(State.new_sale_items, mobile_sale_item_card),
                        class_name="sm:hidden",
                    ),
                    # Vista desktop: tabla
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th(
                                    "Código",
                                    scope="col", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell",
                                ),
                                rx.el.th(
                                    "Producto", scope="col", class_name=TABLE_STYLES["header_cell"]
                                ),
                                rx.el.th(
                                    "Cant.",
                                    scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center",
                                ),
                                rx.el.th(
                                    "Precio",
                                    scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right hidden sm:table-cell",
                                ),
                                rx.el.th(
                                    "Subtotal",
                                    scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right",
                                ),
                                rx.el.th(
                                    "", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-10"
                                ),
                                class_name=TABLE_STYLES["header"],
                            ),
                        ),
                        rx.el.tbody(
                            rx.foreach(State.new_sale_items, compact_sale_item_row),
                        ),
                        class_name="w-full hidden sm:table",
                    ),
                    class_name="contents",
                ),
                rx.el.div(
                    rx.icon("package-open", class_name="h-10 w-10 sm:h-12 sm:w-12 text-slate-300"),
                    rx.el.p("No hay productos", class_name="text-slate-500 font-medium"),
                    rx.el.p("Escanea un código o busca un producto", class_name="text-xs sm:text-sm text-slate-400"),
                    class_name="flex flex-col items-center justify-center py-8 sm:py-12 text-center",
                ),
            ),
            # En mobile: altura auto (crece con el contenido, la página scrollea).
            # En desktop (lg+): flex-1 + overflow-y-auto para scroll interno del panel.
            class_name="lg:flex-1 lg:overflow-y-auto px-3 py-2",
        ),
        class_name="flex flex-col lg:flex-1",
    )
    if embedded:
        return content
    return rx.el.div(
        content,
        class_name="flex flex-col bg-white rounded-xl border shadow-sm flex-1 min-h-[320px] sm:min-h-[360px]",
    )


def visual_product_grid() -> rx.Component:
    """Grid de tarjetas de producto para ropa/juguetería.

    Muestra productos como tarjetas visuales con categoría, precio y stock.
    Incluye barra de búsqueda propia para filtrar dentro del grid.
    """
    return rx.el.div(
        # Barra de búsqueda del grid
        rx.el.div(
            rx.debounce_input(
                rx.el.input(
                    placeholder="Buscar producto en catálogo...",
                    value=State.product_grid_search,
                    on_change=State.search_product_grid,
                    class_name=(
                        "w-full text-sm px-3 py-2 border border-slate-200 "
                        "rounded-lg placeholder-slate-400 focus:outline-none focus:ring-2 "
                        "focus:ring-indigo-500/20 focus:border-indigo-500"
                    ),
                ),
                debounce_timeout=300,
            ),
            class_name="px-3 pt-3 pb-1",
        ),
        # Grid de productos
        rx.cond(
            State.product_grid_items.length() > 0,
            rx.el.div(
                rx.foreach(
                    State.product_grid_items,
                    lambda p: rx.el.div(
                        # Placeholder de imagen / icono
                        rx.el.div(
                            rx.icon("package", class_name="h-8 w-8 text-slate-300"),
                            class_name="w-full h-24 bg-gradient-to-br from-slate-50 to-slate-100 rounded-t-lg flex items-center justify-center",
                        ),
                        # Info
                        rx.el.div(
                            rx.el.span(
                                p["description"],
                                class_name="text-xs font-medium text-slate-800 line-clamp-2 leading-tight",
                            ),
                            rx.el.div(
                                rx.el.span(
                                    State.currency_symbol,
                                    p["sale_price"],
                                    class_name="text-sm font-bold text-indigo-600",
                                ),
                                rx.el.span(
                                    p["stock"].to_string(),
                                    " disp.",
                                    class_name=rx.cond(
                                        p["sin_stock"],
                                        "text-xs text-red-500",
                                        "text-xs text-slate-400",
                                    ),
                                ),
                                class_name="flex items-baseline justify-between gap-1 mt-1",
                            ),
                            class_name="flex flex-col gap-0.5 p-2",
                        ),
                        # Botón agregar
                        rx.el.button(
                            rx.icon("plus", class_name="h-3.5 w-3.5"),
                            "Agregar",
                            on_click=State.add_product_to_sale_by_id(p["product_id"]),
                            disabled=p["sin_stock"],
                            class_name=(
                                "w-full py-1.5 text-xs font-medium bg-indigo-600 text-white "
                                "rounded-b-lg hover:bg-indigo-700 disabled:opacity-40 "
                                "disabled:cursor-not-allowed transition-colors "
                                "flex items-center justify-center gap-1"
                            ),
                        ),
                        class_name="border border-slate-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow bg-white",
                    ),
                ),
                class_name="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5 p-3 overflow-y-auto max-h-[50vh]",
            ),
            rx.el.div(
                rx.icon("package-search", class_name="h-8 w-8 text-slate-300"),
                rx.el.span(
                    "Cargue el catálogo o busque un producto.",
                    class_name="text-sm text-slate-400",
                ),
                rx.el.button(
                    rx.icon("refresh-cw", class_name="h-3.5 w-3.5"),
                    "Cargar catálogo",
                    on_click=State.load_product_grid(""),
                    class_name=(
                        "mt-2 px-4 py-1.5 text-xs font-medium bg-indigo-100 text-indigo-700 "
                        "rounded-lg hover:bg-indigo-200 transition-colors flex items-center gap-1"
                    ),
                ),
                class_name="flex flex-col items-center justify-center gap-2 py-12",
            ),
        ),
        class_name="flex flex-col",
    )


def sale_products_card() -> rx.Component:
    """Tarjeta principal con los productos de la venta.

    Layout adaptativo por vertical de negocio:
    - ropa/juguetería: grid visual de productos + tabla de items del carrito
    - farmacia: tabla con banner de lote obligatorio
    - resto: tabla estándar (bodega, ferretería, general)
    """
    return rx.el.div(
        quick_add_bar(),
        # Pharmacy mode: batch required reminder
        rx.cond(
            State.selected_business_vertical == "farmacia",
            rx.el.div(
                rx.icon("shield-alert", class_name="w-4 h-4 text-emerald-600 shrink-0"),
                rx.el.span(
                    "Modo Farmacia — lotes FEFO auto-asignados. El número de lote aparece en cada ítem.",
                    class_name="text-xs text-emerald-700",
                ),
                class_name="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 border-b border-emerald-100",
            ),
            rx.fragment(),
        ),
        # Grid visual para ropa / juguetería
        rx.cond(
            (State.selected_business_vertical == "ropa")
            | (State.selected_business_vertical == "jugueteria"),
            rx.el.div(
                visual_product_grid(),
                # Tabla de carrito debajo del grid
                rx.cond(
                    State.new_sale_items.length() > 0,
                    rx.el.div(
                        rx.el.div(
                            rx.icon("shopping-cart", class_name="h-4 w-4 text-indigo-600"),
                            rx.el.span(
                                "Carrito (",
                                State.new_sale_items.length().to_string(),
                                ")",
                                class_name="text-sm font-semibold text-slate-700",
                            ),
                            class_name="flex items-center gap-1.5 px-3 py-2 border-t border-slate-200 bg-slate-50",
                        ),
                        products_table(embedded=True),
                    ),
                    rx.fragment(),
                ),
                class_name="flex flex-col",
            ),
            # Tabla estándar para todos los demás rubros
            products_table(embedded=True),
        ),
        # lg:flex-1 solo en desktop (altura fija). En mobile flex-1 comprime la card
        # a min-h y deja ~40px para items — el layout scrollea, no necesita flex-grow.
        class_name="flex flex-col bg-white rounded-xl border shadow-sm lg:flex-1",
    )
