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
    page_header,
    modal_container,
    empty_state,
)
from app.models.promotions import PromotionType, PromotionScope


# ─── Helpers visuales ─────────────────────────────────────────────────────────

_STATUS_BADGE_BASE = "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold"

_STATUS_BADGE_CLASSES = {
    "active": f"{_STATUS_BADGE_BASE} bg-emerald-100 text-emerald-700",
    "paused": f"{_STATUS_BADGE_BASE} bg-slate-100 text-slate-500",
    "scheduled": f"{_STATUS_BADGE_BASE} bg-blue-100 text-blue-700",
    "expired": f"{_STATUS_BADGE_BASE} bg-red-100 text-red-700",
    "exhausted": f"{_STATUS_BADGE_BASE} bg-amber-100 text-amber-700",
}


def _status_badge(status: rx.Var, label: rx.Var) -> rx.Component:
    return rx.el.span(
        label,
        class_name=rx.match(
            status,
            ("active", _STATUS_BADGE_CLASSES["active"]),
            ("paused", _STATUS_BADGE_CLASSES["paused"]),
            ("scheduled", _STATUS_BADGE_CLASSES["scheduled"]),
            ("expired", _STATUS_BADGE_CLASSES["expired"]),
            ("exhausted", _STATUS_BADGE_CLASSES["exhausted"]),
            _STATUS_BADGE_CLASSES["paused"],
        ),
    )


def _type_chip(type_label: rx.Var) -> rx.Component:
    return rx.el.span(
        type_label,
        class_name="text-xs font-medium text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded",
    )


def _day_checkbox(label: str, checked, on_change) -> rx.Component:
    """Checkbox compacto para selección de día (L M X J V S D)."""
    return rx.el.label(
        rx.el.input(
            type="checkbox",
            default_checked=checked,
            on_change=on_change,
            class_name="peer sr-only",
        ),
        rx.el.span(
            label,
            class_name=(
                "inline-flex items-center justify-center w-9 h-9 rounded-full "
                "border border-slate-300 text-sm font-medium text-slate-600 "
                "cursor-pointer select-none transition-colors "
                "peer-checked:bg-indigo-600 peer-checked:text-white peer-checked:border-indigo-600 "
                "hover:bg-slate-50"
            ),
        ),
        class_name="cursor-pointer",
        key=State.promo_form_key.to_string() + label,
    )


# ─── Fila de tabla ────────────────────────────────────────────────────────────

def _promo_row(p: rx.Var) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.div(
                rx.el.p(p["name"], class_name="font-medium text-slate-900 text-sm"),
                rx.cond(
                    p["coupon_code"] != "",
                    rx.el.span(
                        rx.icon("ticket", class_name="h-3 w-3 mr-1"),
                        p["coupon_code"],
                        class_name="inline-flex items-center text-xs font-mono font-semibold text-fuchsia-700 bg-fuchsia-50 px-1.5 py-0.5 rounded",
                    ),
                    rx.fragment(),
                ),
                class_name="flex items-center gap-2",
            ),
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
                        p["min_quantity"].to_string() + "x" + (p["min_quantity"].to(int) - p["free_quantity"].to(int)).to_string(),
                    ),
                ),
                class_name="font-semibold text-amber-700 tabular-nums text-sm",
            ),
            class_name="py-3 px-4 text-right",
        ),
        rx.el.td(
            rx.el.p(p["starts_at"], class_name="text-xs text-slate-500"),
            rx.el.p(p["ends_at"], class_name="text-xs text-slate-400"),
            rx.cond(
                p["weekdays_label"] != "Todos los días",
                rx.el.p(p["weekdays_label"], class_name="text-xs text-indigo-500 mt-0.5"),
                rx.fragment(),
            ),
            rx.cond(
                p["time_window_label"] != "",
                rx.el.p(p["time_window_label"], class_name="text-xs text-indigo-500"),
                rx.fragment(),
            ),
            rx.cond(
                p["min_cart_amount_label"] != "",
                rx.el.p(
                    p["min_cart_amount_label"],
                    class_name="text-xs text-emerald-600 mt-0.5 font-medium",
                ),
                rx.fragment(),
            ),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.el.div(
                _status_badge(p["status"], p["status_label"]),
                rx.el.p(p["usage_label"], class_name="text-xs text-slate-400 mt-1"),
                class_name="flex flex-col items-start",
            ),
            class_name="py-3 px-4",
        ),
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
                        rx.icon("circle-pause", class_name="h-4 w-4"),
                        on_click=State.toggle_promotion(p["id"], False),
                        class_name="p-1.5 rounded-lg text-amber-500 hover:bg-amber-50",
                        title="Pausar",
                    ),
                    rx.el.button(
                        rx.icon("circle-play", class_name="h-4 w-4"),
                        on_click=State.toggle_promotion(p["id"], True),
                        class_name="p-1.5 rounded-lg text-emerald-500 hover:bg-emerald-50",
                        title="Encender",
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
                _status_badge(p["status"], p["status_label"]),
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
            rx.el.span(f"{p['starts_at']} → {p['ends_at']}", class_name="text-xs text-slate-400"),
            rx.el.span(" · ", class_name="text-xs text-slate-300"),
            rx.el.span(p["usage_label"], class_name="text-xs text-slate-400"),
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
                    rx.icon("circle-pause", class_name="h-4 w-4"),
                    "Pausar",
                    on_click=State.toggle_promotion(p["id"], False),
                    class_name="flex items-center gap-1 text-xs text-amber-600 hover:text-amber-800",
                ),
                rx.el.button(
                    rx.icon("circle-play", class_name="h-4 w-4"),
                    "Encender",
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
    # Reflex 0.8: NO precomputar comparaciones Var como locals; el bundler
    # las inlinea como identifiers no definidos en el JSX final.
    return modal_container(
        is_open=State.show_promotion_form,
        on_close=State.close_promotion_form,
        title=rx.cond(
            State.promo_editing_id > 0,
            "Editar Promoción",
            "Nueva Promoción",
        ),
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

                # Productos (visible cuando scope == PRODUCT) — multi-selección
                rx.cond(
                    State.promo_scope == PromotionScope.PRODUCT,
                    rx.el.div(
                        rx.el.label(
                            "Productos",
                            rx.el.span(
                                " (" + State.promo_product_ids.length().to_string() + " seleccionados)",
                                class_name="font-normal text-slate-400",
                            ),
                            class_name=TYPOGRAPHY["label"],
                        ),
                        # Buscador
                        rx.el.input(
                            placeholder="Buscar producto...",
                            on_change=State.set_promo_product_search,
                            class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full") + " mb-1",
                            key=State.promo_form_key.to_string(),
                        ),
                        # Lista scrollable de checkboxes
                        rx.el.div(
                            rx.cond(
                                State.promotion_products.length() == 0,
                                rx.el.p(
                                    "No hay productos activos en esta sucursal.",
                                    class_name="text-xs text-amber-600 p-2",
                                ),
                                rx.foreach(
                                    State.filtered_promotion_products,
                                    lambda prod: rx.el.div(
                                        rx.cond(
                                            State.promo_product_ids.contains(prod["id"].to_string()),
                                            rx.icon("square-check", class_name="h-4 w-4 text-indigo-600 shrink-0"),
                                            rx.icon("square", class_name="h-4 w-4 text-slate-300 shrink-0"),
                                        ),
                                        rx.el.span(
                                            prod["label"],
                                            class_name="text-sm text-slate-700 truncate",
                                        ),
                                        on_click=State.toggle_promo_product_id(prod["id"].to_string()),
                                        class_name=(
                                            "flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer "
                                            "hover:bg-indigo-50 select-none"
                                        ),
                                    ),
                                ),
                            ),
                            class_name="border border-slate-200 rounded-lg max-h-44 overflow-y-auto",
                        ),
                        rx.cond(
                            State.promo_product_ids.length() == 0,
                            rx.el.p(
                                "Seleccioná al menos un producto.",
                                class_name="text-xs text-rose-500 mt-1",
                            ),
                            rx.fragment(),
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
                                type="text",
                                input_mode="numeric",
                                on_blur=State.set_promo_min_quantity,
                                class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                                key=State.promo_form_key.to_string(),
                            ),
                        ),
                        rx.el.div(
                            rx.el.label("Gratis (cantidad)", class_name=TYPOGRAPHY["label"]),
                            rx.el.input(
                                default_value=State.promo_free_quantity,
                                type="text",
                                input_mode="numeric",
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
                            type="text",
                            input_mode="decimal",
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
                        type="text",
                        input_mode="numeric",
                        placeholder="Sin límite",
                        on_blur=State.set_promo_max_uses,
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.promo_form_key.to_string(),
                    ),
                ),

                # Días aplicables
                rx.el.div(
                    rx.el.label("Días aplicables", class_name=TYPOGRAPHY["label"]),
                    rx.el.div(
                        _day_checkbox("L", State.promo_day_mon, State.set_promo_day_mon),
                        _day_checkbox("M", State.promo_day_tue, State.set_promo_day_tue),
                        _day_checkbox("X", State.promo_day_wed, State.set_promo_day_wed),
                        _day_checkbox("J", State.promo_day_thu, State.set_promo_day_thu),
                        _day_checkbox("V", State.promo_day_fri, State.set_promo_day_fri),
                        _day_checkbox("S", State.promo_day_sat, State.set_promo_day_sat),
                        _day_checkbox("D", State.promo_day_sun, State.set_promo_day_sun),
                        class_name="flex flex-wrap gap-2 mt-1",
                    ),
                    class_name="col-span-2",
                ),

                # Banda horaria
                rx.el.div(
                    rx.el.label("Hora desde (opcional)", class_name=TYPOGRAPHY["label"]),
                    rx.el.input(
                        default_value=State.promo_time_from,
                        type="time",
                        on_change=State.set_promo_time_from,
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.promo_form_key.to_string(),
                    ),
                ),
                rx.el.div(
                    rx.el.label("Hora hasta (opcional)", class_name=TYPOGRAPHY["label"]),
                    rx.el.input(
                        default_value=State.promo_time_to,
                        type="time",
                        on_change=State.set_promo_time_to,
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.promo_form_key.to_string(),
                    ),
                ),
                rx.el.p(
                    "Dejá ambas horas vacías para aplicar todo el día. Si la hora 'desde' es mayor que 'hasta', el rango cruza medianoche (ej: 22:00 → 02:00).",
                    class_name="col-span-2 text-xs text-slate-400 -mt-2",
                ),

                # Cupón
                rx.el.div(
                    rx.el.label(
                        "Código de cupón (opcional)",
                        class_name=TYPOGRAPHY["label"],
                    ),
                    rx.el.input(
                        placeholder="Ej: VERANO20 — vacío = promoción automática",
                        default_value=State.promo_coupon_code,
                        on_blur=State.set_promo_coupon_code,
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full") + " uppercase",
                        key=State.promo_form_key.to_string(),
                    ),
                    rx.el.p(
                        "Si tiene código, sólo se aplica cuando el cliente lo ingresa en el POS. Sin código, se aplica automáticamente.",
                        class_name="text-xs text-slate-400 mt-1",
                    ),
                    class_name="col-span-2",
                ),

                # Umbral de carrito
                rx.el.div(
                    rx.el.label(
                        "Monto mínimo de carrito (opcional)",
                        class_name=TYPOGRAPHY["label"],
                    ),
                    rx.el.input(
                        placeholder="Ej: 1000 — vacío o 0 = sin umbral",
                        default_value=State.promo_min_cart_amount,
                        on_blur=State.set_promo_min_cart_amount,
                        type="number",
                        min="0",
                        step="0.01",
                        class_name=INPUT_STYLES.get("default", "border rounded px-3 py-2 text-sm w-full"),
                        key=State.promo_form_key.to_string(),
                    ),
                    rx.el.p(
                        "La promo solo se aplica cuando el subtotal del carrito (antes de descuentos) alcanza este monto.",
                        class_name="text-xs text-slate-400 mt-1",
                    ),
                    class_name="col-span-2",
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
                rx.cond(
                    State.is_loading,
                    "Guardando...",
                    rx.cond(
                        State.promo_editing_id > 0,
                        "Actualizar",
                        "Crear Promoción",
                    ),
                ),
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
        page_header(
            "OFERTAS Y PROMOCIONES",
            "Configura descuentos automáticos para el punto de venta",
            actions=[
                rx.el.select(
                    rx.el.option("Todas", value="all"),
                    rx.el.option("Encendidas", value="active"),
                    rx.el.option("Pausadas", value="inactive"),
                    default_value=State.promotions_filter_active,
                    on_change=State.set_promotions_filter,
                    class_name=SELECT_STYLES.get("default", "border rounded px-3 py-2 text-sm"),
                ),
                rx.el.button(
                    rx.icon("plus", class_name="h-4 w-4"),
                    "Nueva Promoción",
                    on_click=State.open_new_promotion,
                    class_name=f"flex items-center gap-2 {BUTTON_STYLES['primary']} text-sm",
                ),
            ],
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
        # rx.fragment no soporta on_mount; la carga inicial la dispara
        # `app.add_page(on_load=State.page_init_promociones)` en app/app.py.
    )
