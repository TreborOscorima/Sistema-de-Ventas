"""Página de Ofertas y Promociones."""
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
    BADGE_STYLES,
    page_title,
    modal_container,
    empty_state,
)
from app.models.promotions import PromotionType, PromotionScope


# ─── Helpers visuales ─────────────────────────────────────────────────────────

def _running_badge(is_running: rx.Var) -> rx.Component:
    return rx.cond(
        is_running,
        rx.el.span(
            "Activa",
            class_name="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700",
        ),
        rx.el.span(
            "Inactiva",
            class_name="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-500",
        ),
    )


def _type_chip(type_label: rx.Var) -> rx.Component:
    return rx.el.span(
        type_label,
        class_name="text-xs font-medium text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded",
    )


# ─── Fila de tabla ────────────────────────────────────────────────────────────

def _promo_row(p: rx.Var) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.p(p["name"], class_name="font-medium text-slate-900 text-sm"),
            rx.el.p(p["description"], class_name="text-xs text-slate-400 truncate max-w-xs"),
            class_name="py-3 px-4",
        ),
        rx.el.td(_type_chip(p["type_label"]), class_name="py-3 px-4"),
        rx.el.td(
            rx.el.span(p["scope_label"], class_name="text-sm text-slate-600"),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.el.span(
                rx.cond(
                    p["type"] == PromotionType.PERCENTAGE,
                    p["discount_value"].to_string() + "%",
                    rx.cond(
                        p["type"] == PromotionType.FIXED_AMOUNT,
                        State.currency_symbol + p["discount_value"].to_string(),
                        p["min_quantity"].to_string() + "x" + (p["min_quantity"] - p["free_quantity"]).to_string(),
                    ),
                ),
                class_name="font-semibold text-amber-700 tabular-nums text-sm",
            ),
            class_name="py-3 px-4 text-right",
        ),
        rx.el.td(
            rx.el.p(p["starts_at"], class_name="text-xs text-slate-500"),
            rx.el.p(p["ends_at"], class_name="text-xs text-slate-400"),
            class_name="py-3 px-4",
        ),
        rx.el.td(_running_badge(p["is_running"]), class_name="py-3 px-4"),
        rx.el.td(
            rx.el.div(
                rx.el.button(
                    rx.icon("pencil", class_name="h-4 w-4"),
                    on_click=State.open_edit_promotion(p),
                    class_name=f"{BUTTON_STYLES.get('ghost', 'p-2 rounded-lg text-slate-500 hover:bg-slate-100')} p-1.5",
                    title="Editar",
                ),
                rx.cond(
                    p["is_active"],
                    rx.el.button(
                        rx.icon("pause-circle", class_name="h-4 w-4"),
                        on_click=State.toggle_promotion(p["id"], False),
                        class_name="p-1.5 rounded-lg text-amber-500 hover:bg-amber-50",
                        title="Desactivar",
                    ),
                    rx.el.button(
                        rx.icon("play-circle", class_name="h-4 w-4"),
                        on_click=State.toggle_promotion(p["id"], True),
                        class_name="p-1.5 rounded-lg text-emerald-500 hover:bg-emerald-50",
                        title="Activar",
                    ),
                ),
                class_name="flex items-center gap-1 justify-end",
            ),
            class_name="py-3 px-4",
        ),
        class_name="border-b border-slate-100 hover:bg-slate-50/80 transition-colors",
    )


# ─── Card mobile ──────────────────────────────────────────────────────────────

def _promo_card(p: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                _type_chip(p["type_label"]),
                _running_badge(p["is_running"]),
                class_name="flex items-center gap-2",
            ),
            rx.el.span(
                rx.cond(
                    p["type"] == PromotionType.PERCENTAGE,
                    p["discount_value"].to_string() + "% off",
                    p["discount_value"].to_string(),
                ),
                class_name="font-bold text-amber-700 tabular-nums",
            ),
            class_name="flex items-center justify-between",
        ),
        rx.el.p(p["name"], class_name="font-medium text-slate-900 text-sm mt-1"),
        rx.el.p(p["scope_label"], class_name="text-xs text-slate-500"),
        rx.el.div(
            rx.el.span(p["starts_at"] + " → " + p["ends_at"], class_name="text-xs text-slate-400"),
            class_name="mt-1",
        ),
        rx.el.div(
            rx.el.button(
                rx.icon("pencil", class_name="h-4 w-4"),
                "Editar",
                on_click=State.open_edit_promotion(p),
                class_name="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800",
            ),
            rx.cond(
                p["is_active"],
                rx.el.button(
                    rx.icon("pause-circle", class_name="h-4 w-4"),
                    "Desactivar",
                    on_click=State.toggle_promotion(p["id"], False),
                    class_name="flex items-center gap-1 text-xs text-amber-600 hover:text-amber-800",
                ),
                rx.el.button(
                    rx.icon("play-circle", class_name="h-4 w-4"),
                    "Activar",
                    on_click=State.toggle_promotion(p["id"], True),
                    class_name="flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-800",
                ),
            ),
            class_name="flex gap-4 mt-2",
        ),
        class_name=f"bg-white border border-slate-200 {RADIUS['lg']} p-4 {SHADOWS['sm']}",
    )


# ─── Modal: Formulario de Promoción ──────────────────────────────────────────

def _promo_form_modal() -> rx.Component:
    is_edit = State.promo_editing_id > 0
    return modal_container(
        is_open=State.show_promotion_form,
        on_close=State.close_promotion_form,
        title=rx.cond(is_edit, "Editar Promoción", "Nueva Promoción"),
        max_width="max-w-2xl",
        children=[
            rx.el.div(
                # Nombre
                rx.el.div(
                    rx.el.label("Nombre *", class_name=TYPOGRAPHY["label"]),
                    rx.el.input(
                        placeholder="Ej: Black Friday 20% off",
                        default_value=State.promo_name,
                        on_blur=State.set_promo_name,
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.promo_form_key.to_string(),
                    ),
                    class_name="col-span-2",
                ),

                # Descripción
                rx.el.div(
                    rx.el.label("Descripción (opcional)", class_name=TYPOGRAPHY["label"]),
                    rx.el.input(
                        placeholder="Descripción interna...",
                        default_value=State.promo_description,
                        on_blur=State.set_promo_description,
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.promo_form_key.to_string(),
                    ),
                    class_name="col-span-2",
                ),

                # Tipo de descuento
                rx.el.div(
                    rx.el.label("Tipo de descuento", class_name=TYPOGRAPHY["label"]),
                    rx.el.select(
                        rx.el.option("Descuento porcentual (%)", value=PromotionType.PERCENTAGE),
                        rx.el.option("Monto fijo", value=PromotionType.FIXED_AMOUNT),
                        rx.el.option("Lleva X paga Y", value=PromotionType.BUY_X_GET_Y),
                        default_value=State.promo_type,
                        on_change=State.set_promo_type,
                        class_name=SELECT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.promo_form_key.to_string(),
                    ),
                ),

                # Ámbito
                rx.el.div(
                    rx.el.label("Ámbito de aplicación", class_name=TYPOGRAPHY["label"]),
                    rx.el.select(
                        rx.el.option("Todos los productos", value=PromotionScope.ALL),
                        rx.el.option("Por categoría", value=PromotionScope.CATEGORY),
                        rx.el.option("Producto específico", value=PromotionScope.PRODUCT),
                        default_value=State.promo_scope,
                        on_change=State.set_promo_scope,
                        class_name=SELECT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.promo_form_key.to_string(),
                    ),
                ),

                # Categoría (visible cuando scope == CATEGORY)
                rx.cond(
                    State.promo_scope == PromotionScope.CATEGORY,
                    rx.el.div(
                        rx.el.label("Categoría", class_name=TYPOGRAPHY["label"]),
                        rx.el.select(
                            rx.el.option("-- Seleccionar --", value=""),
                            rx.foreach(
                                State.promotion_categories,
                                lambda cat: rx.el.option(cat, value=cat),
                            ),
                            default_value=State.promo_category,
                            on_change=State.set_promo_category,
                            class_name=SELECT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                            key=State.promo_form_key.to_string(),
                        ),
                        class_name="col-span-2",
                    ),
                    rx.fragment(),
                ),

                # Valor del descuento / X e Y para BUY_X_GET_Y
                rx.cond(
                    State.promo_type == PromotionType.BUY_X_GET_Y,
                    rx.el.div(
                        rx.el.div(
                            rx.el.label("Lleva (cantidad mínima)", class_name=TYPOGRAPHY["label"]),
                            rx.el.input(
                                default_value=State.promo_min_quantity,
                                type="number",
                                min="1",
                                on_blur=State.set_promo_min_quantity,
                                class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                                key=State.promo_form_key.to_string(),
                            ),
                        ),
                        rx.el.div(
                            rx.el.label("Gratis (cantidad)", class_name=TYPOGRAPHY["label"]),
                            rx.el.input(
                                default_value=State.promo_free_quantity,
                                type="number",
                                min="0",
                                on_blur=State.set_promo_free_quantity,
                                class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                                key=State.promo_form_key.to_string(),
                            ),
                        ),
                        class_name="col-span-2 grid grid-cols-2 gap-4",
                    ),
                    rx.el.div(
                        rx.el.label(
                            rx.cond(
                                State.promo_type == PromotionType.PERCENTAGE,
                                "Descuento (%)",
                                "Monto fijo",
                            ),
                            class_name=TYPOGRAPHY["label"],
                        ),
                        rx.el.input(
                            default_value=State.promo_discount_value,
                            type="number",
                            min="0",
                            step="0.01",
                            on_blur=State.set_promo_discount_value,
                            class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                            key=State.promo_form_key.to_string(),
                        ),
                    ),
                ),

                # Fechas de vigencia
                rx.el.div(
                    rx.el.label("Fecha inicio", class_name=TYPOGRAPHY["label"]),
                    rx.el.input(
                        default_value=State.promo_starts_at,
                        type="date",
                        on_change=State.set_promo_starts_at,
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.promo_form_key.to_string(),
                    ),
                ),
                rx.el.div(
                    rx.el.label("Fecha fin", class_name=TYPOGRAPHY["label"]),
                    rx.el.input(
                        default_value=State.promo_ends_at,
                        type="date",
                        on_change=State.set_promo_ends_at,
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.promo_form_key.to_string(),
                    ),
                ),

                # Máximo de usos
                rx.el.div(
                    rx.el.label("Máx. usos (vacío = ilimitado)", class_name=TYPOGRAPHY["label"]),
                    rx.el.input(
                        default_value=State.promo_max_uses,
                        type="number",
                        min="1",
                        placeholder="Sin límite",
                        on_blur=State.set_promo_max_uses,
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.promo_form_key.to_string(),
                    ),
                ),

                # Activa
                rx.el.div(
                    rx.el.label("Estado", class_name=TYPOGRAPHY["label"]),
                    rx.el.div(
                        rx.el.input(
                            type="checkbox",
                            default_checked=State.promo_is_active,
                            on_change=State.set_promo_is_active,
                            class_name="h-4 w-4 rounded border-slate-300 text-indigo-600",
                            key=State.promo_form_key.to_string(),
                        ),
                        rx.el.span("Activa", class_name="text-sm text-slate-700"),
                        class_name="flex items-center gap-2 mt-1",
                    ),
                ),

                class_name="grid grid-cols-2 gap-4",
            ),
        ],
        footer=rx.el.div(
            rx.el.button(
                rx.cond(State.is_loading, "Guardando...", rx.cond(is_edit, "Actualizar", "Crear Promoción")),
                on_click=State.save_promotion,
                disabled=State.is_loading,
                class_name=f"flex items-center gap-2 {BUTTON_STYLES.get('primary', 'px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700')}",
            ),
            rx.el.button(
                "Cancelar",
                on_click=State.close_promotion_form,
                class_name=BUTTON_STYLES.get("secondary", "px-4 py-2 border border-slate-200 rounded-lg hover:bg-slate-50"),
            ),
            class_name="flex gap-3 justify-end",
        ),
    )


# ─── Página principal ─────────────────────────────────────────────────────────

def promociones_page() -> rx.Component:
    return rx.fragment(
        page_title("Ofertas y Promociones", "Configura descuentos automáticos para el punto de venta"),

        # Barra de filtros y acción
        rx.el.div(
            rx.el.div(
                rx.el.select(
                    rx.el.option("Todas", value="all"),
                    rx.el.option("Activas ahora", value="active"),
                    rx.el.option("Inactivas", value="inactive"),
                    default_value=State.promotions_filter_active,
                    on_change=State.set_promotions_filter,
                    class_name=SELECT_STYLES.get("default", "border rounded px-3 py-2 text-sm"),
                ),
                class_name="flex items-center gap-3",
            ),
            rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                "Nueva Promoción",
                on_click=State.open_new_promotion,
                class_name=f"flex items-center gap-2 {BUTTON_STYLES.get('primary', 'px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700')} text-sm",
            ),
            class_name="flex items-center justify-between",
        ),

        # Tabla desktop
        rx.el.div(
            rx.cond(
                State.promotions.length() > 0,
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("Nombre / Descripción", class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Tipo", class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Ámbito", class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Valor", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                            rx.el.th("Vigencia", class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Estado", class_name=TABLE_STYLES["header_cell"]),
                            rx.el.th("Acciones", class_name=TABLE_STYLES["header_cell"] + " text-right"),
                            class_name=TABLE_STYLES["header"],
                        ),
                    ),
                    rx.el.tbody(rx.foreach(State.promotions, _promo_row)),
                    class_name="w-full",
                ),
                empty_state("No hay promociones. Crea la primera con el botón de arriba.", "tag"),
            ),
            class_name="hidden md:block overflow-x-auto bg-white border border-slate-200 rounded-xl shadow-sm",
        ),

        # Cards mobile
        rx.el.div(
            rx.cond(
                State.promotions.length() > 0,
                rx.foreach(State.promotions, _promo_card),
                empty_state("No hay promociones aún.", "tag"),
            ),
            class_name="flex flex-col gap-3 md:hidden",
        ),

        # Modal
        _promo_form_modal(),

        on_mount=State.page_init_promociones,
    )
