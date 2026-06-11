import reflex as rx

from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    INPUT_STYLES,
    RADIUS,
    SELECT_STYLES,
    SHADOWS,
    TRANSITIONS,
    TYPOGRAPHY,
)
from ._shared import _copy_text_script


# ─── Motivos predefinidos por acción ───────────────────────

_REASON_PRESETS = {
    "change_plan": [
        "Cliente solicitó activación de cuenta",
        "Upgrade por crecimiento del negocio",
        "Downgrade solicitado por el cliente",
        "Migración de plan por promoción",
        "Ajuste por renovación de contrato",
        "Corrección de plan asignado incorrectamente",
    ],
    "change_status": [
        "Pago recibido — reactivación de cuenta",
        "Incumplimiento de pago",
        "Solicitud del cliente — suspensión temporal",
        "Reactivación tras resolución de problema",
        "Cuenta comprometida — suspensión preventiva",
        "Mantenimiento programado",
    ],
    "extend_trial": [
        "Cliente en evaluación — necesita más tiempo",
        "Problema técnico durante el periodo de prueba",
        "Solicitud comercial — extensión cortesía",
        "Demostración a decisor pendiente",
        "Cliente con proceso de implementación en curso",
        "Extensión por feriado / temporada baja",
    ],
    "adjust_limits": [
        "Crecimiento de equipo del cliente",
        "Apertura de nueva sucursal",
        "Ajuste por plan contratado",
        "Reducción por optimización de recursos",
        "Ajuste temporal por evento especial",
        "Corrección de límites configurados incorrectamente",
    ],
}


def _info_pill(label: str, value: rx.Var, color: str = "slate") -> rx.Component:
    """Pequeño pill informativo de solo lectura."""
    return rx.el.div(
        rx.el.span(label, class_name=f"text-xs text-{color}-400 uppercase tracking-wider font-semibold"),
        rx.el.span(value, class_name=f"text-sm font-medium text-{color}-700"),
        class_name=f"flex flex-col gap-0.5 bg-{color}-50 px-3 py-1.5 {RADIUS['md']}",
    )


def _reason_selector(action_key: str) -> rx.Component:
    """Selector de motivo predefinido + textarea para personalizar."""
    presets = _REASON_PRESETS.get(action_key, [])
    return rx.el.div(
        rx.el.label(
            "Motivo (obligatorio)",
            class_name=TYPOGRAPHY["label"],
        ),
        rx.el.select(
            rx.el.option("— Selecciona un motivo —", value=""),
            *[rx.el.option(r, value=r) for r in presets],
            rx.el.option("✏️ Escribir motivo personalizado", value="custom"),
            value=State.owner_form_reason_preset,
            on_change=State.owner_set_form_reason_preset,
            class_name=SELECT_STYLES["default"],
        ),
        rx.el.textarea(
            value=State.owner_form_reason,
            on_change=State.owner_set_form_reason,
            placeholder="Describe el motivo o complementa la selección...",
            rows=2,
            class_name=f"{INPUT_STYLES['default']} h-auto py-2 resize-none",
        ),
        class_name="flex flex-col gap-2",
    )


def _date_and_notes_section() -> rx.Component:
    """Fecha efectiva (auto) + notas opcionales."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.label("Fecha de aplicación", class_name=TYPOGRAPHY["label"]),
                rx.el.div(
                    rx.icon("calendar", class_name="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2"),
                    rx.el.input(
                        value=State.owner_form_effective_date,
                        read_only=True,
                        class_name=f"{INPUT_STYLES['default']} pl-10 bg-slate-50 text-slate-500 cursor-default",
                    ),
                    class_name="relative",
                ),
                class_name="flex flex-col gap-1.5",
            ),
            class_name="w-full",
        ),
        rx.el.div(
            rx.el.label("Notas adicionales (opcional)", class_name=TYPOGRAPHY["label"]),
            rx.debounce_input(
                rx.input(
                    value=State.owner_form_notes,
                    on_change=State.owner_set_form_notes,
                    placeholder="Ej: Contacto: Juan Pérez, Tel: 987654321",
                    class_name=INPUT_STYLES["default"],
                ),
                debounce_timeout=300,
            ),
            class_name="flex flex-col gap-1.5",
        ),
        class_name="flex flex-col gap-3",
    )


# ─── Formularios condicionales del modal ──────────────────

def _form_change_plan() -> rx.Component:
    return rx.el.div(
        # Info actual
        rx.el.div(
            _info_pill("Plan actual", State.owner_form_current_plan, "blue"),
            _info_pill("Estado", State.owner_form_current_status, "slate"),
            class_name="flex gap-2 flex-wrap",
        ),
        # Separator
        rx.el.div(class_name="border-t border-slate-100"),
        # Nuevo plan
        rx.el.div(
            rx.el.label("Nuevo Plan", class_name=TYPOGRAPHY["label"]),
            rx.el.select(
                rx.el.option("Prueba", value="trial"),
                rx.el.option("Estándar", value="standard"),
                rx.el.option("Profesional", value="professional"),
                rx.el.option("Empresarial", value="enterprise"),
                value=State.owner_form_plan,
                on_change=State.owner_set_form_plan,
                class_name=SELECT_STYLES["default"],
            ),
            class_name="flex flex-col gap-1.5",
        ),
        # Duración de suscripción (solo si no es trial)
        rx.cond(
            State.owner_form_plan != "trial",
            rx.el.div(
                rx.el.label("Duración de suscripción", class_name=TYPOGRAPHY["label"]),
                rx.el.div(
                    *[
                        rx.el.button(
                            label,
                            on_click=State.owner_set_form_subscription_months(val),
                            class_name=rx.cond(
                                State.owner_form_subscription_months == val,
                                f"px-3 py-1.5 text-xs font-medium {RADIUS['md']} bg-indigo-100 text-indigo-700 border border-indigo-300",
                                f"px-3 py-1.5 text-xs font-medium {RADIUS['md']} bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100 cursor-pointer",
                            ),
                        )
                        for label, val in [
                            ("1 mes", "1"),
                            ("3 meses", "3"),
                            ("6 meses", "6"),
                            ("12 meses", "12"),
                            ("24 meses", "24"),
                        ]
                    ],
                    class_name="flex gap-2 flex-wrap",
                ),
                rx.el.p(
                    "La suscripción vencerá después del periodo seleccionado.",
                    class_name="text-xs text-slate-400",
                ),
                class_name="flex flex-col gap-2",
            ),
            rx.fragment(),
        ),
        # Nota informativa (la activación siempre es inmediata al cambiar plan)
        rx.el.div(
            rx.icon("circle-check", class_name="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5"),
            rx.el.p(
                "La empresa quedará activa inmediatamente tras el cambio de plan.",
                class_name="text-xs text-slate-500",
            ),
            class_name="flex items-start gap-1.5",
        ),
        # Fecha + Notas
        _date_and_notes_section(),
        # Separator
        rx.el.div(class_name="border-t border-slate-100"),
        # Motivos
        _reason_selector("change_plan"),
        class_name="flex flex-col gap-4",
    )


def _form_change_status() -> rx.Component:
    return rx.el.div(
        # Info actual
        rx.el.div(
            _info_pill("Estado actual", State.owner_form_current_status, "amber"),
            _info_pill("Plan", State.owner_form_current_plan, "blue"),
            rx.cond(
                State.owner_form_trial_ends_at != "",
                _info_pill("Prueba vence", State.owner_form_trial_ends_at, "red"),
                rx.fragment(),
            ),
            class_name="flex gap-2 flex-wrap",
        ),
        # Separator
        rx.el.div(class_name="border-t border-slate-100"),
        # Nuevo estado
        rx.el.div(
            rx.el.label("Nuevo Estado", class_name=TYPOGRAPHY["label"]),
            rx.el.select(
                rx.el.option("Activo", value="active"),
                rx.el.option("Advertencia", value="warning"),
                rx.el.option("Vencido", value="past_due"),
                rx.el.option("Suspendido", value="suspended"),
                value=State.owner_form_status,
                on_change=State.owner_set_form_status,
                class_name=SELECT_STYLES["default"],
            ),
            class_name="flex flex-col gap-1.5",
        ),
        # Fecha + Notas
        _date_and_notes_section(),
        # Separator
        rx.el.div(class_name="border-t border-slate-100"),
        # Motivos
        _reason_selector("change_status"),
        class_name="flex flex-col gap-4",
    )


def _form_extend_trial() -> rx.Component:
    return rx.el.div(
        # Info actual
        rx.el.div(
            _info_pill("Plan", State.owner_form_current_plan, "amber"),
            _info_pill("Estado", State.owner_form_current_status, "slate"),
            rx.cond(
                State.owner_form_trial_ends_at != "",
                _info_pill("Vence", State.owner_form_trial_ends_at, "red"),
                rx.fragment(),
            ),
            class_name="flex gap-2 flex-wrap",
        ),
        # Separator
        rx.el.div(class_name="border-t border-slate-100"),
        # Presets rápidos de días
        rx.el.div(
            rx.el.label("Extensión rápida", class_name=TYPOGRAPHY["label"]),
            rx.el.div(
                *[
                    rx.el.button(
                        f"{d} días",
                        on_click=State.owner_set_form_extra_days_preset(str(d)),
                        class_name=rx.cond(
                            State.owner_form_extra_days == str(d),
                            f"px-3 py-1.5 text-xs font-medium {RADIUS['md']} bg-indigo-100 text-indigo-700 border border-indigo-300",
                            f"px-3 py-1.5 text-xs font-medium {RADIUS['md']} bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100 cursor-pointer",
                        ),
                    )
                    for d in [7, 14, 30, 60, 90]
                ],
                class_name="flex gap-2 flex-wrap",
            ),
            class_name="flex flex-col gap-2",
        ),
        # Input manual de días
        rx.el.div(
            rx.el.label("Días a extender (personalizado)", class_name=TYPOGRAPHY["label"]),
            rx.debounce_input(
                rx.input(
                    type="number",
                    min="1",
                    max="365",
                    value=State.owner_form_extra_days,
                    on_change=State.owner_set_form_extra_days,
                    class_name=INPUT_STYLES["default"],
                ),
                debounce_timeout=250,
            ),
            class_name="flex flex-col gap-1.5",
        ),
        # Fecha + Notas
        _date_and_notes_section(),
        # Separator
        rx.el.div(class_name="border-t border-slate-100"),
        # Motivos
        _reason_selector("extend_trial"),
        class_name="flex flex-col gap-4",
    )


def _module_card(
    icon_name: str,
    title: str,
    description: str,
    checked: rx.Var,
    on_change,
    included_by_plan: rx.Var,
) -> rx.Component:
    """Tarjeta de módulo con toggle y badge de inclusión por plan."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon(icon_name, class_name="h-6 w-6 text-indigo-600"),
                class_name=f"p-2.5 bg-indigo-50 {RADIUS['lg']} flex-shrink-0",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.span(title, class_name="text-sm font-semibold text-slate-800"),
                    rx.cond(
                        included_by_plan,
                        rx.el.span(
                            "Incluido en plan",
                            class_name=f"text-xs font-medium text-emerald-700 bg-emerald-50 px-1.5 py-0.5 {RADIUS['sm']}",
                        ),
                        rx.el.span(
                            "Extra",
                            class_name=f"text-xs font-medium text-amber-700 bg-amber-50 px-1.5 py-0.5 {RADIUS['sm']}",
                        ),
                    ),
                    class_name="flex items-center gap-2",
                ),
                rx.el.p(description, class_name=f"{TYPOGRAPHY['caption']} mt-0.5"),
                class_name="flex flex-col flex-1",
            ),
            # Toggle switch
            rx.el.label(
                rx.el.input(
                    type="checkbox",
                    checked=checked,
                    on_change=on_change,
                    class_name="sr-only peer",
                ),
                rx.el.div(
                    class_name=(
                        "relative w-9 h-5 bg-slate-200 peer-focus:outline-none "
                        f"peer-focus:ring-2 peer-focus:ring-indigo-300 {RADIUS['full']} peer "
                        "peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full "
                        "peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] "
                        f"after:start-[2px] after:bg-white after:border-slate-300 after:border after:{RADIUS['full']} "
                        f"after:h-4 after:w-4 after:{TRANSITIONS['fast']} peer-checked:bg-indigo-600"
                    ),
                ),
                class_name="inline-flex items-center cursor-pointer flex-shrink-0",
            ),
            class_name="flex items-start gap-3",
        ),
        class_name=rx.cond(
            checked,
            f"p-3 border border-indigo-200 bg-indigo-50/30 {RADIUS['lg']} {TRANSITIONS['fast']}",
            f"p-3 border border-slate-200 bg-white {RADIUS['lg']} {TRANSITIONS['fast']}",
        ),
    )


def _form_adjust_limits() -> rx.Component:
    return rx.el.div(
        # Info actual
        rx.el.div(
            _info_pill("Plan", State.owner_form_current_plan, "blue"),
            _info_pill("Estado", State.owner_form_current_status, "slate"),
            class_name="flex gap-2 flex-wrap",
        ),
        # Separator
        rx.el.div(class_name="border-t border-slate-100"),
        # Usuarios y Sucursales en grid
        rx.el.div(
            rx.el.div(
                rx.el.label("Máx. Usuarios", class_name=TYPOGRAPHY["label"]),
                rx.debounce_input(
                    rx.input(
                        type="number",
                        min="1",
                        value=State.owner_form_max_users,
                        on_change=State.owner_set_form_max_users,
                        class_name=INPUT_STYLES["default"],
                    ),
                    debounce_timeout=250,
                ),
                class_name="flex flex-col gap-1.5",
            ),
            rx.el.div(
                rx.el.label("Máx. Sucursales", class_name=TYPOGRAPHY["label"]),
                rx.debounce_input(
                    rx.input(
                        type="number",
                        min="1",
                        value=State.owner_form_max_branches,
                        on_change=State.owner_set_form_max_branches,
                        class_name=INPUT_STYLES["default"],
                    ),
                    debounce_timeout=250,
                ),
                class_name="flex flex-col gap-1.5",
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 gap-4",
        ),
        # Separator
        rx.el.div(class_name="border-t border-slate-100"),
        # Módulos habilitados
        rx.el.div(
            rx.el.div(
                rx.icon("puzzle", class_name="h-4 w-4 text-indigo-600"),
                rx.el.span("Módulos", class_name="text-sm font-semibold text-slate-800"),
                class_name="flex items-center gap-1.5",
            ),
            rx.el.p(
                "Activa o desactiva módulos para esta empresa. Los módulos marcados como \"Incluido en plan\" vienen habilitados por defecto según el plan contratado.",
                class_name="text-xs text-slate-400 mt-0.5",
            ),
            rx.el.div(
                _module_card(
                    icon_name="calendar-days",
                    title="Servicios y Reservas",
                    description="Gestión de servicios, reservas de canchas, agenda y citas.",
                    checked=State.owner_form_has_reservations,
                    on_change=State.owner_set_form_has_reservations,
                    included_by_plan=rx.cond(
                        (State.owner_form_current_plan == "standard"),
                        rx.Var.create(False),
                        rx.Var.create(True),
                    ),
                ),
                _module_card(
                    icon_name="users",
                    title="Clientes",
                    description="Directorio de clientes, proveedores y gestión de contactos.",
                    checked=State.owner_form_has_clients,
                    on_change=State.owner_set_form_has_clients,
                    included_by_plan=rx.cond(
                        (State.owner_form_current_plan == "standard"),
                        rx.Var.create(False),
                        rx.Var.create(True),
                    ),
                ),
                _module_card(
                    icon_name="credit-card",
                    title="Cuentas Corrientes",
                    description="Créditos, cobranzas, cuotas y seguimiento de deudas de clientes.",
                    checked=State.owner_form_has_credits,
                    on_change=State.owner_set_form_has_credits,
                    included_by_plan=rx.cond(
                        (State.owner_form_current_plan == "standard"),
                        rx.Var.create(False),
                        rx.Var.create(True),
                    ),
                ),
                _module_card(
                    icon_name="file-text",
                    title="Facturación Electrónica",
                    description="Emisión de comprobantes electrónicos (boletas, facturas) a SUNAT.",
                    checked=State.owner_form_has_billing,
                    on_change=State.owner_set_form_has_billing,
                    included_by_plan=rx.cond(
                        (State.owner_form_current_plan == "enterprise"),
                        rx.Var.create(True),
                        rx.Var.create(False),
                    ),
                ),
                _module_card(
                    icon_name="calculator",
                    title="Presupuestos",
                    description="Creación y gestión de presupuestos y cotizaciones para clientes.",
                    checked=State.owner_form_has_presupuestos,
                    on_change=State.owner_set_form_has_presupuestos,
                    included_by_plan=rx.cond(
                        (State.owner_form_current_plan == "standard"),
                        rx.Var.create(False),
                        rx.Var.create(True),
                    ),
                ),
                _module_card(
                    icon_name="badge-percent",
                    title="Promociones",
                    description="Gestión de descuentos, ofertas y campañas promocionales.",
                    checked=State.owner_form_has_promociones,
                    on_change=State.owner_set_form_has_promociones,
                    included_by_plan=rx.cond(
                        (State.owner_form_current_plan == "standard"),
                        rx.Var.create(False),
                        rx.Var.create(True),
                    ),
                ),
                _module_card(
                    icon_name="dollar-sign",
                    title="Listas de Precios",
                    description="Configuración de listas de precios diferenciadas por cliente o canal.",
                    checked=State.owner_form_has_listas_precios,
                    on_change=State.owner_set_form_has_listas_precios,
                    included_by_plan=rx.cond(
                        (State.owner_form_current_plan == "standard"),
                        rx.Var.create(False),
                        rx.Var.create(True),
                    ),
                ),
                _module_card(
                    icon_name="tag",
                    title="Etiquetas",
                    description="Impresión y gestión de etiquetas de productos con código de barras.",
                    checked=State.owner_form_has_etiquetas,
                    on_change=State.owner_set_form_has_etiquetas,
                    included_by_plan=rx.cond(
                        (State.owner_form_current_plan == "standard"),
                        rx.Var.create(False),
                        rx.Var.create(True),
                    ),
                ),
                class_name="flex flex-col gap-2 mt-2",
            ),
            class_name="flex flex-col gap-1",
        ),
        # Fecha + Notas
        _date_and_notes_section(),
        # Separator
        rx.el.div(class_name="border-t border-slate-100"),
        # Motivos
        _reason_selector("adjust_limits"),
        class_name="flex flex-col gap-4",
    )


# ─── Modal de reset de contraseña ─────────────────────────

def _reset_user_row(user: rx.Var[dict[str, str]]) -> rx.Component:
    """Fila de usuario en el modal de reset de contraseña."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("user", class_name="h-4 w-4 text-indigo-600"),
                class_name=(
                    "h-8 w-8 rounded-full bg-indigo-100 flex items-center "
                    "justify-center flex-shrink-0"
                ),
            ),
            rx.el.div(
                rx.el.p(
                    user["username"],
                    class_name="text-sm font-medium text-slate-800",
                ),
                rx.el.p(
                    rx.cond(
                        user["email"] != "",
                        user["email"],
                        "Sin correo",
                    ),
                    class_name=f"{TYPOGRAPHY['caption']} break-all",
                ),
                class_name="flex flex-col min-w-0",
            ),
            class_name="flex items-center gap-2.5 min-w-0 flex-1",
        ),
        rx.el.div(
            rx.el.span(
                user["role_name"],
                class_name="text-xs text-slate-500 bg-slate-50 px-2 py-0.5 rounded-full",
            ),
            rx.cond(
                user["is_active"] == "true",
                rx.el.span(
                    "Activo",
                    class_name="text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full",
                ),
                rx.el.span(
                    "Inactivo",
                    class_name="text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full",
                ),
            ),
            rx.el.button(
                rx.icon("rotate-ccw", class_name="h-3.5 w-3.5"),
                "Resetear",
                on_click=State.owner_reset_password(user["id"], user["username"]),
                disabled=State.owner_reset_loading,
                type="button",
                class_name=(
                    "ml-1 flex items-center gap-1 px-2.5 py-1 text-xs font-medium "
                    "text-amber-700 bg-amber-50 hover:bg-amber-100 rounded-md "
                    f"{TRANSITIONS['fast']} disabled:opacity-50 disabled:cursor-not-allowed"
                ),
            ),
            class_name="flex flex-wrap items-center gap-2 sm:justify-end flex-shrink-0",
        ),
        class_name=(
            "flex flex-col gap-3 px-3 py-2.5 hover:bg-slate-50 rounded-lg "
            "sm:flex-row sm:items-center sm:justify-between"
        ),
    )


def _reset_password_modal() -> rx.Component:
    """Modal de reseteo de contraseña con listado de usuarios."""
    return rx.cond(
        State.owner_reset_modal_open,
        rx.el.div(
            # Overlay
            rx.el.div(
                on_click=State.owner_close_reset_modal,
                class_name="fixed inset-0 bg-black/40 z-[70] modal-overlay",
            ),
            # Panel
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.icon("key-round", class_name="h-5 w-5 text-amber-600"),
                            class_name=f"p-2 bg-amber-50 {RADIUS['lg']}",
                        ),
                        rx.el.div(
                            rx.el.h2(
                                "Resetear Contraseña",
                                class_name=TYPOGRAPHY["section_title"],
                            ),
                            rx.el.p(
                                State.owner_reset_company_name,
                                class_name=TYPOGRAPHY["body_secondary"],
                            ),
                            class_name="flex flex-col",
                        ),
                        class_name="flex items-center gap-3",
                    ),
                    rx.el.button(
                        rx.icon("x", class_name="h-5 w-5"),
                        on_click=State.owner_close_reset_modal,
                        type="button",
                        title="Cerrar",
                        aria_label="Cerrar",
                        class_name=BUTTON_STYLES["icon_ghost"],
                    ),
                    class_name="flex items-start justify-between gap-4 mb-4 pb-4 border-b border-slate-100",
                ),
                # Contraseña temporal generada (solo visible después de resetear)
                rx.cond(
                    State.owner_reset_result_visible,
                    rx.el.div(
                        rx.el.div(
                            rx.icon("shield-check", class_name="h-5 w-5 text-emerald-600"),
                            rx.el.div(
                                rx.el.p(
                                    "Contraseña temporal para ",
                                    rx.el.span(
                                        State.owner_reset_target_username,
                                        class_name="font-semibold",
                                    ),
                                    class_name="text-sm text-emerald-800",
                                ),
                                rx.el.p(
                                    "El usuario deberá cambiarla al iniciar sesión.",
                                    class_name="text-xs text-emerald-600 mt-0.5",
                                ),
                                class_name="flex flex-col",
                            ),
                            class_name="flex items-start gap-2",
                        ),
                        rx.el.div(
                            rx.el.code(
                                State.owner_reset_temp_password,
                                id="owner-temp-password-value",
                                class_name=(
                                    "block w-full min-w-0 overflow-x-auto text-center sm:text-left "
                                    "text-lg font-mono font-bold text-emerald-900 bg-emerald-100 "
                                    "px-4 py-2 rounded-lg tracking-wider select-all"
                                ),
                            ),
                            rx.el.button(
                                rx.icon("copy", class_name="h-4 w-4"),
                                "Copiar",
                                on_click=rx.call_script(
                                    _copy_text_script("owner-temp-password-value")
                                ),
                                type="button",
                                class_name=(
                                    f"flex items-center gap-1.5 px-3 py-2 text-sm font-medium "
                                    f"text-emerald-700 bg-emerald-100 hover:bg-emerald-200 "
                                    f"{RADIUS['lg']} {TRANSITIONS['fast']}"
                                ),
                            ),
                            class_name=(
                                "mt-3 flex flex-col gap-2 sm:flex-row sm:items-center "
                                "sm:justify-between"
                            ),
                        ),
                        rx.el.p(
                            rx.icon("triangle-alert", class_name="h-3.5 w-3.5 inline mr-1"),
                            "Copia esta contraseña ahora. No se mostrará de nuevo.",
                            class_name="text-xs text-amber-700 mt-2 text-center",
                        ),
                        class_name=(
                            "bg-emerald-50 border border-emerald-200 rounded-xl "
                            "p-4 mb-4"
                        ),
                    ),
                    rx.fragment(),
                ),
                # Loading
                rx.cond(
                    State.owner_reset_loading,
                    rx.el.div(
                        rx.icon("loader-circle", class_name="h-5 w-5 text-slate-400 animate-spin"),
                        rx.el.span("Cargando...", class_name=TYPOGRAPHY["body_secondary"]),
                        class_name="flex items-center gap-2 justify-center py-6",
                    ),
                    rx.fragment(),
                ),
                # Lista de usuarios
                rx.cond(
                    State.owner_reset_users.length() > 0,  # type: ignore
                    rx.el.div(
                        rx.el.p(
                            "Selecciona el usuario a resetear:",
                            class_name=f"{TYPOGRAPHY['label_secondary']} mb-2",
                        ),
                        rx.el.div(
                            rx.foreach(State.owner_reset_users, _reset_user_row),
                            class_name="flex flex-col gap-0.5 max-h-[320px] overflow-y-auto",
                        ),
                        class_name="flex flex-col",
                    ),
                    rx.cond(
                        ~State.owner_reset_loading,
                        rx.el.p(
                            "No se encontraron usuarios en esta empresa.",
                            class_name=f"{TYPOGRAPHY['body_secondary']} text-center py-6",
                        ),
                        rx.fragment(),
                    ),
                ),
                # Footer
                rx.el.div(
                    rx.el.button(
                        "Cerrar",
                        on_click=State.owner_close_reset_modal,
                        type="button",
                        class_name=BUTTON_STYLES["secondary"] + " w-full sm:w-auto",
                    ),
                    class_name="flex justify-end mt-5 pt-4 border-t border-slate-100",
                ),
                class_name=(
                    f"fixed z-[80] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 "
                    f"w-[calc(100%-1.5rem)] sm:w-full max-w-2xl bg-white {RADIUS['xl']} "
                    f"{SHADOWS['xl']} p-4 sm:p-6 max-h-[92vh] overflow-y-auto"
                ),
            ),
        ),
        rx.fragment(),
    )


# ─── Modal de acción ──────────────────────────────────────

def _action_modal() -> rx.Component:
    return rx.cond(
        State.owner_modal_open,
        rx.el.div(
            # Overlay
            rx.el.div(
                on_click=State.owner_close_modal,
                class_name="fixed inset-0 bg-black/40 z-[70] modal-overlay",
            ),
            # Panel
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.match(
                                State.owner_modal_action,
                                ("change_plan", rx.icon("repeat", class_name="h-5 w-5 text-indigo-600")),
                                ("change_status", rx.icon("toggle-right", class_name="h-5 w-5 text-indigo-600")),
                                ("extend_trial", rx.icon("calendar-plus", class_name="h-5 w-5 text-amber-600")),
                                ("adjust_limits", rx.icon("sliders-horizontal", class_name="h-5 w-5 text-emerald-600")),
                                rx.icon("settings", class_name="h-5 w-5 text-slate-600"),
                            ),
                            class_name=f"p-2 bg-slate-50 {RADIUS['lg']}",
                        ),
                        rx.el.div(
                            rx.el.h2(
                                rx.match(
                                    State.owner_modal_action,
                                    ("change_plan", "Cambiar Plan"),
                                    ("change_status", "Cambiar Estado"),
                                    ("extend_trial", "Extender Prueba"),
                                    ("adjust_limits", "Ajustar Límites"),
                                    "Acción",
                                ),
                                class_name=TYPOGRAPHY["section_title"],
                            ),
                            rx.el.p(
                                State.owner_modal_company_name,
                                class_name=TYPOGRAPHY["body_secondary"],
                            ),
                            class_name="flex flex-col",
                        ),
                        class_name="flex items-center gap-3",
                    ),
                    rx.el.button(
                        rx.icon("x", class_name="h-5 w-5"),
                        on_click=State.owner_close_modal,
                        title="Cerrar",
                        aria_label="Cerrar",
                        class_name=BUTTON_STYLES["icon_ghost"],
                    ),
                    class_name="flex items-start justify-between gap-4 mb-5 pb-4 border-b border-slate-100",
                ),
                # Formulario condicional (incluye motivos y fecha)
                rx.match(
                    State.owner_modal_action,
                    ("change_plan", _form_change_plan()),
                    ("change_status", _form_change_status()),
                    ("extend_trial", _form_extend_trial()),
                    ("adjust_limits", _form_adjust_limits()),
                    rx.fragment(),
                ),
                # Footer
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=State.owner_close_modal,
                        class_name=BUTTON_STYLES["secondary"] + " w-full sm:w-auto",
                    ),
                    rx.el.button(
                        rx.cond(
                            State.owner_loading,
                            rx.el.span(
                                rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"),
                                "Procesando...",
                                class_name="flex items-center gap-2",
                            ),
                            "Confirmar",
                        ),
                        on_click=State.owner_execute_action,
                        disabled=State.owner_loading,
                        class_name=rx.cond(
                            State.owner_loading,
                            BUTTON_STYLES["disabled"] + " w-full sm:w-auto",
                            BUTTON_STYLES["primary"] + " w-full sm:w-auto",
                        ),
                    ),
                    class_name="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-end gap-3 mt-6 pt-4 border-t border-slate-100",
                ),
                class_name=f"fixed z-[80] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100%-1.5rem)] sm:w-full max-w-lg bg-white {RADIUS['xl']} {SHADOWS['xl']} p-4 sm:p-6 max-h-[92vh] overflow-y-auto",
            ),
        ),
        rx.fragment(),
    )
