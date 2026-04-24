"""Página de Listas de Precios múltiples."""
import reflex as rx
from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    INPUT_STYLES,
    SELECT_STYLES,
    TABLE_STYLES,
    TYPOGRAPHY,
    RADIUS,
    SHADOWS,
    TRANSITIONS,
    page_title,
    modal_container,
    empty_state,
)


# ─── Card de lista de precios ─────────────────────────────────────────────────

def _price_list_card(pl: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(pl["name"], class_name="font-semibold text-slate-900"),
                rx.cond(
                    pl["is_default"],
                    rx.el.span(
                        "Predeterminada",
                        class_name="text-xs font-medium bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full",
                    ),
                    rx.fragment(),
                ),
                class_name="flex items-center gap-2 flex-wrap",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("pencil", class_name="h-4 w-4"),
                    on_click=State.open_edit_price_list(pl),
                    class_name=f"{BUTTON_STYLES.get('ghost', 'p-2 rounded-lg text-slate-500 hover:bg-slate-100')} p-1.5",
                    title="Editar nombre",
                ),
                rx.el.button(
                    rx.icon("list", class_name="h-4 w-4"),
                    on_click=State.open_price_list_detail(pl["id"]),
                    class_name=f"{BUTTON_STYLES.get('ghost', 'p-2 rounded-lg text-slate-500 hover:bg-slate-100')} p-1.5",
                    title="Ver/editar precios",
                ),
                class_name="flex items-center gap-1",
            ),
            class_name="flex items-start justify-between",
        ),
        rx.el.p(pl["description"], class_name="text-sm text-slate-500 mt-1"),
        rx.el.div(
            rx.el.div(
                rx.icon("package", class_name="h-4 w-4 text-slate-400"),
                rx.el.span(
                    pl["item_count"].to_string() + " precios especiales",
                    class_name="text-xs text-slate-600",
                ),
                class_name="flex items-center gap-1.5",
            ),
            rx.el.div(
                rx.icon("users", class_name="h-4 w-4 text-slate-400"),
                rx.el.span(
                    pl["client_count"].to_string() + " clientes asignados",
                    class_name="text-xs text-slate-600",
                ),
                class_name="flex items-center gap-1.5",
            ),
            rx.el.span(pl["currency_code"], class_name="text-xs font-mono text-slate-400 ml-auto"),
            class_name="flex items-center gap-4 mt-3 flex-wrap",
        ),
        class_name=f"bg-white border border-slate-200 {RADIUS['lg']} p-4 {SHADOWS['sm']} hover:shadow-md {TRANSITIONS['fast']}",
    )


# ─── Modal: Crear/Editar lista ────────────────────────────────────────────────

def _price_list_form_modal() -> rx.Component:
    is_edit = State.pl_editing_id > 0
    return modal_container(
        is_open=State.show_price_list_form,
        on_close=State.close_price_list_form,
        title=rx.cond(is_edit, "Editar Lista de Precios", "Nueva Lista de Precios"),
        max_width="max-w-lg",
        children=[
            rx.el.div(
                # Nombre
                rx.el.div(
                    rx.el.label("Nombre *", class_name=TYPOGRAPHY["label"]),
                    rx.el.input(
                        placeholder="Ej: Mayorista, VIP, Distribuidores",
                        default_value=State.pl_name,
                        on_blur=State.set_pl_name,
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.pl_form_key.to_string(),
                    ),
                ),

                # Descripción
                rx.el.div(
                    rx.el.label("Descripción (opcional)", class_name=TYPOGRAPHY["label"]),
                    rx.el.input(
                        placeholder="Descripción para referencia interna...",
                        default_value=State.pl_description,
                        on_blur=State.set_pl_description,
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.pl_form_key.to_string(),
                    ),
                ),

                # Moneda
                rx.el.div(
                    rx.el.label("Moneda", class_name=TYPOGRAPHY["label"]),
                    rx.el.select(
                        rx.el.option("PEN — Sol Peruano", value="PEN"),
                        rx.el.option("ARS — Peso Argentino", value="ARS"),
                        rx.el.option("USD — Dólar", value="USD"),
                        default_value=State.pl_currency_code,
                        on_change=State.set_pl_currency_code,
                        class_name=SELECT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.pl_form_key.to_string(),
                    ),
                ),

                # Default
                rx.el.div(
                    rx.el.div(
                        rx.el.input(
                            type="checkbox",
                            default_checked=State.pl_is_default,
                            on_change=State.set_pl_is_default,
                            class_name="h-4 w-4 rounded border-slate-300 text-indigo-600",
                            key=State.pl_form_key.to_string(),
                        ),
                        rx.el.div(
                            rx.el.span("Lista predeterminada", class_name="text-sm font-medium text-slate-700"),
                            rx.el.span(
                                "Se aplica cuando el cliente no tiene lista asignada",
                                class_name="text-xs text-slate-500",
                            ),
                            class_name="flex flex-col",
                        ),
                        class_name="flex items-start gap-2",
                    ),
                    class_name="pt-1",
                ),

                class_name="flex flex-col gap-4",
            ),
        ],
        footer=rx.el.div(
            rx.el.button(
                rx.cond(State.is_loading, "Guardando...", rx.cond(is_edit, "Actualizar", "Crear Lista")),
                on_click=State.save_price_list,
                disabled=State.is_loading,
                class_name=f"flex items-center gap-2 {BUTTON_STYLES.get('primary', 'px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700')}",
            ),
            rx.el.button(
                "Cancelar",
                on_click=State.close_price_list_form,
                class_name=BUTTON_STYLES.get("secondary", "px-4 py-2 border border-slate-200 rounded-lg hover:bg-slate-50"),
            ),
            class_name="flex gap-3 justify-end",
        ),
    )


# ─── Modal: Detalle / ítems de la lista ──────────────────────────────────────

def _item_row(item: rx.Var) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.p(item["product_name"], class_name="text-sm font-medium text-slate-900"),
            rx.el.p(item["barcode"], class_name="text-xs text-slate-400 font-mono"),
            class_name="py-2 px-3",
        ),
        rx.el.td(
            rx.cond(
                item["variant_desc"] != "",
                rx.el.span(item["variant_desc"], class_name="text-xs text-slate-500"),
                rx.el.span("—", class_name="text-slate-300 text-xs"),
            ),
            class_name="py-2 px-3 text-sm",
        ),
        rx.el.td(
            rx.el.span(item["unit_price_display"], class_name="font-semibold text-indigo-700 tabular-nums text-sm"),
            class_name="py-2 px-3 text-right",
        ),
        rx.el.td(
            rx.el.button(
                rx.icon("trash-2", class_name="h-4 w-4"),
                on_click=State.remove_price_list_item(item["id"]),
                class_name="p-1 text-red-400 hover:bg-red-50 rounded",
                title="Eliminar",
            ),
            class_name="py-2 px-3 text-center",
        ),
        class_name="border-b border-slate-100 hover:bg-slate-50/80",
    )


def _price_list_detail_modal() -> rx.Component:
    pl = State.selected_price_list
    return modal_container(
        is_open=State.show_price_list_detail,
        on_close=State.close_price_list_detail,
        title=rx.el.div(
            rx.el.span("Precios especiales: ", class_name="text-slate-500 font-normal"),
            rx.el.span(pl["name"], class_name="font-bold"),
            class_name="flex items-center gap-1 flex-wrap",
        ),
        max_width="max-w-2xl",
        children=[
            # Buscador para agregar producto
            rx.el.div(
                rx.el.p("Agregar precio especial", class_name="text-sm font-semibold text-slate-700"),
                rx.el.div(
                    rx.el.div(
                        rx.debounce_input(
                            rx.el.input(
                                placeholder="Buscar producto por nombre o código...",
                                value=State.pl_item_product_search,
                                on_change=State.pl_search_products,
                                class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                            ),
                            debounce_timeout=400,
                        ),
                        rx.cond(
                            State.pl_item_product_results.length() > 0,
                            rx.el.div(
                                rx.foreach(
                                    State.pl_item_product_results,
                                    lambda p: rx.el.div(
                                        rx.el.p(p["description"], class_name="text-sm font-medium"),
                                        rx.el.p(p["barcode"], class_name="text-xs text-slate-400 font-mono"),
                                        on_click=lambda: State.pl_select_product(p),
                                        class_name="px-3 py-2 hover:bg-indigo-50 cursor-pointer border-b border-slate-100",
                                    ),
                                ),
                                class_name="absolute z-50 w-full bg-white border border-slate-200 rounded-xl shadow-lg max-h-48 overflow-y-auto",
                            ),
                            rx.fragment(),
                        ),
                        class_name="relative flex-1",
                    ),
                    rx.el.input(
                        placeholder="Precio especial",
                        value=State.pl_item_unit_price,
                        on_change=State.set_pl_item_price,
                        type="text",
                        input_mode="decimal",
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-32"),
                    ),
                    rx.el.button(
                        rx.icon("plus", class_name="h-4 w-4"),
                        "Agregar",
                        on_click=State.add_price_list_item,
                        class_name=f"flex items-center gap-1 {BUTTON_STYLES.get('primary', 'px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700')} text-sm whitespace-nowrap",
                    ),
                    class_name="flex items-start gap-2",
                ),
                class_name="space-y-2 bg-slate-50 rounded-xl p-3",
            ),

            rx.divider(color="slate-100"),

            # Tabla de ítems existentes
            rx.cond(
                State.price_list_items.length() > 0,
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("Producto", class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Variante", class_name=TABLE_STYLES["header_cell"]),
                                rx.el.th("Precio especial", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                                rx.el.th("", class_name=TABLE_STYLES["header_cell"]),
                                class_name=TABLE_STYLES["header"],
                            ),
                        ),
                        rx.el.tbody(rx.foreach(State.price_list_items, _item_row)),
                        class_name="w-full",
                    ),
                    class_name="overflow-x-auto",
                ),
                rx.el.div(
                    rx.icon("tag", class_name="h-8 w-8 text-slate-300 mx-auto"),
                    rx.el.p(
                        "Sin precios especiales aún. Busca un producto arriba para agregar uno.",
                        class_name="text-sm text-slate-400 mt-2 text-center",
                    ),
                    class_name="py-8",
                ),
            ),
        ],
        footer=rx.el.div(
            rx.el.button(
                "Cerrar",
                on_click=State.close_price_list_detail,
                class_name=BUTTON_STYLES.get("secondary", "px-4 py-2 border border-slate-200 rounded-lg hover:bg-slate-50"),
            ),
            class_name="flex justify-end",
        ),
    )


# ─── Página principal ─────────────────────────────────────────────────────────

def listas_precios_page() -> rx.Component:
    return rx.fragment(
        page_title(
            "Listas de Precios",
            "Define precios especiales por canal, cliente mayorista o grupo",
        ),

        # Acción principal
        rx.el.div(
            rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                "Nueva Lista",
                on_click=State.open_new_price_list,
                class_name=f"flex items-center gap-2 {BUTTON_STYLES.get('primary', 'px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700')} text-sm",
            ),
            class_name="flex justify-end",
        ),

        # Grid de listas
        rx.cond(
            State.price_lists.length() > 0,
            rx.el.div(
                rx.foreach(State.price_lists, _price_list_card),
                class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4",
            ),
            empty_state("No hay listas de precios. Crea la primera con el botón de arriba.", "tag"),
        ),

        # Nota informativa
        rx.el.div(
            rx.icon("info", class_name="h-4 w-4 text-blue-500 flex-shrink-0"),
            rx.el.p(
                "Las listas de precios se asignan a clientes en el módulo de Clientes. "
                "Al registrar una venta, si el cliente tiene una lista asignada, "
                "sus precios especiales se aplican automáticamente.",
                class_name="text-xs text-slate-500 leading-relaxed",
            ),
            class_name="flex gap-2 bg-blue-50 border border-blue-100 rounded-xl p-3 mt-2",
        ),

        # Modales
        _price_list_form_modal(),
        _price_list_detail_modal(),

        on_mount=State.page_init_listas_precios,
    )
