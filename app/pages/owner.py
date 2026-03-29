"""
Backoffice de Owners — Mini-sistema independiente de gestión de la plataforma SaaS.

Completamente separado del Sistema de Ventas:
- Layout propio (sin sidebar del sistema de ventas)
- Header administrativo independiente
- Accesible solo para propietarios de plataforma
- Invisible para usuarios regulares del sistema
"""
import os

import reflex as rx

from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    CARD_STYLES,
    INPUT_STYLES,
    RADIUS,
    SELECT_STYLES,
    SHADOWS,
    TRANSITIONS,
    TYPOGRAPHY,
)

APP_SURFACE: str = (os.getenv("APP_SURFACE") or "all").strip().lower()
if APP_SURFACE not in {"all", "landing", "app", "owner"}:
    APP_SURFACE = "all"

PUBLIC_APP_URL = (os.getenv("PUBLIC_APP_URL") or "").strip().rstrip("/")
OWNER_LOGIN_PATH = "/login" if APP_SURFACE == "owner" else "/owner/login"


def _app_href(path: str = "/") -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    if PUBLIC_APP_URL:
        return f"{PUBLIC_APP_URL}{normalized}"
    return normalized


def _copy_text_script(target_id: str) -> str:
    """Copia texto desde un nodo del DOM con fallback para HTTP/IP."""
    return (
        "(function(){"
        f"const el=document.getElementById('{target_id}');"
        "const text=(el?.textContent||'').trim();"
        "if(!text){return;}"
        "const fallback=()=>{"
        "const ta=document.createElement('textarea');"
        "ta.value=text;"
        "ta.setAttribute('readonly','');"
        "ta.style.position='fixed';"
        "ta.style.opacity='0';"
        "ta.style.left='-9999px';"
        "document.body.appendChild(ta);"
        "ta.focus();"
        "ta.select();"
        "ta.setSelectionRange(0, ta.value.length);"
        "let copied=false;"
        "try{copied=document.execCommand('copy');}catch(_err){copied=false;}"
        "document.body.removeChild(ta);"
        "if(!copied){window.prompt('Copia manualmente la contraseña temporal:', text);}"
        "};"
        "if(window.isSecureContext && navigator.clipboard && navigator.clipboard.writeText){"
        "navigator.clipboard.writeText(text).catch(()=>fallback());"
        "}else{"
        "fallback();"
        "}"
        "})();"
    )


# ─── Helpers de estilo ──────────────────────────────────

_BADGE_PLAN = {
    "trial": "bg-amber-100 text-amber-700",
    "standard": "bg-indigo-100 text-indigo-700",
    "professional": "bg-purple-100 text-purple-700",
    "enterprise": "bg-emerald-100 text-emerald-700",
}

_BADGE_STATUS = {
    "active": "bg-emerald-100 text-emerald-700",
    "warning": "bg-amber-100 text-amber-700",
    "past_due": "bg-red-100 text-red-700",
    "suspended": "bg-slate-200 text-slate-600",
    "trial_expired": "bg-orange-100 text-orange-700",
}

_ACTION_LABELS = {
    "change_plan": "Cambiar Plan",
    "change_status": "Cambiar Estado",
    "extend_trial": "Extender Prueba",
    "adjust_limits": "Ajustar Límites",
}


def _plan_badge(plan: rx.Var) -> rx.Component:
    return rx.el.span(
        plan,
        class_name=rx.match(
            plan,
            ("trial", f"px-2 py-0.5 text-xs font-medium {RADIUS['sm']} {_BADGE_PLAN['trial']}"),
            ("standard", f"px-2 py-0.5 text-xs font-medium {RADIUS['sm']} {_BADGE_PLAN['standard']}"),
            ("professional", f"px-2 py-0.5 text-xs font-medium {RADIUS['sm']} {_BADGE_PLAN['professional']}"),
            ("enterprise", f"px-2 py-0.5 text-xs font-medium {RADIUS['sm']} {_BADGE_PLAN['enterprise']}"),
            f"px-2 py-0.5 text-xs font-medium {RADIUS['sm']} bg-slate-100 text-slate-600",
        ),
    )


def _status_badge(status: rx.Var) -> rx.Component:
    return rx.el.span(
        rx.cond(
            status == "trial_expired",
            "Trial Vencido",
            status,
        ),
        class_name=rx.match(
            status,
            ("active", f"px-2 py-0.5 text-xs font-medium {RADIUS['sm']} {_BADGE_STATUS['active']}"),
            ("warning", f"px-2 py-0.5 text-xs font-medium {RADIUS['sm']} {_BADGE_STATUS['warning']}"),
            ("past_due", f"px-2 py-0.5 text-xs font-medium {RADIUS['sm']} {_BADGE_STATUS['past_due']}"),
            ("suspended", f"px-2 py-0.5 text-xs font-medium {RADIUS['sm']} {_BADGE_STATUS['suspended']}"),
            ("trial_expired", f"px-2 py-0.5 text-xs font-medium {RADIUS['sm']} {_BADGE_STATUS['trial_expired']}"),
            f"px-2 py-0.5 text-xs font-medium {RADIUS['sm']} bg-slate-100 text-slate-600",
        ),
    )


def _owner_action_icon_button(
    icon_name: str,
    label: str,
    on_click,
    tone: str = "indigo",
) -> rx.Component:
    """Botón de acción del backoffice con tooltip visible al hover."""
    tone_class = {
        "indigo": "text-indigo-600 hover:bg-indigo-100 active:bg-indigo-200",
        "slate": "text-slate-600 hover:bg-slate-100 active:bg-slate-200",
    }.get(tone, "text-indigo-600 hover:bg-indigo-100 active:bg-indigo-200")

    return rx.el.div(
        rx.el.button(
            rx.icon(icon_name, class_name="h-5 w-5"),
            title=label,
            aria_label=label,
            on_click=on_click,
            class_name=(
                f"p-2.5 {tone_class} {RADIUS['full']} {TRANSITIONS['fast']} "
                "hover:scale-105 focus:outline-none focus:ring-2 focus:ring-indigo-500/25"
            ),
        ),
        rx.el.span(
            label,
            class_name=(
                "pointer-events-none absolute left-1/2 top-0 z-20 -translate-x-1/2 "
                "-translate-y-[125%] whitespace-nowrap rounded-md bg-slate-900 px-2.5 "
                "py-1 text-xs font-semibold text-white shadow-lg opacity-0 scale-95 "
                "transition-all duration-150 group-hover:opacity-100 group-hover:scale-100"
            ),
        ),
        class_name="relative group",
    )


def _owner_module_icon_badge(
    icon_name: str,
    label: str,
    tone_classes: str,
) -> rx.Component:
    """Badge de módulo con tooltip visual notorio al hover."""
    return rx.el.div(
        rx.el.span(
            rx.icon(icon_name, class_name="h-4 w-4"),
            aria_label=label,
            class_name=(
                f"inline-flex items-center justify-center p-1.5 {tone_classes} "
                f"{RADIUS['sm']} {TRANSITIONS['fast']} group-hover:scale-105"
            ),
        ),
        rx.el.span(
            label,
            class_name=(
                "pointer-events-none absolute left-1/2 top-0 z-20 -translate-x-1/2 "
                "-translate-y-[125%] whitespace-nowrap rounded-md bg-slate-900 px-2.5 "
                "py-1 text-xs font-semibold text-white shadow-lg opacity-0 scale-95 "
                "transition-all duration-150 group-hover:opacity-100 group-hover:scale-100"
            ),
        ),
        class_name="relative group",
    )


# ─── Barra de búsqueda ──────────────────────────────────

def _search_bar() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("search", class_name="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"),
            rx.debounce_input(
                rx.input(
                    placeholder="Buscar por nombre o RUC...",
                    value=State.owner_search,
                    on_change=State.owner_search_companies,
                    class_name=INPUT_STYLES["search"],
                ),
                debounce_timeout=350,
            ),
            class_name="relative w-full sm:w-80",
        ),
        rx.el.div(
            rx.el.button(
                rx.cond(
                    State.owner_loading,
                    rx.icon("loader-circle", class_name="h-4 w-4 mr-1.5 animate-spin"),
                    rx.icon("refresh-cw", class_name="h-4 w-4 mr-1.5"),
                ),
                "Sincronizar Expirados",
                on_click=State.owner_sync_expired,
                disabled=State.owner_loading,
                class_name=rx.cond(
                    State.owner_loading,
                    (
                        "inline-flex items-center justify-center w-full sm:w-auto px-3 py-1.5 text-xs font-medium "
                        f"{RADIUS['md']} bg-orange-50/70 text-orange-500 border border-orange-200 "
                        "cursor-not-allowed opacity-80"
                    ),
                    (
                        "inline-flex items-center justify-center w-full sm:w-auto px-3 py-1.5 text-xs font-medium "
                        f"{RADIUS['md']} bg-orange-50 text-orange-700 border border-orange-200 "
                        "hover:bg-orange-100 transition-colors cursor-pointer"
                    ),
                ),
            ),
            rx.el.span(
                State.owner_companies_total,
                " empresas",
                class_name=TYPOGRAPHY["body_secondary"],
            ),
            class_name="flex flex-col-reverse sm:flex-row items-start sm:items-center gap-2 sm:gap-3 w-full sm:w-auto",
        ),
        class_name="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4",
    )


# ─── Tabla de empresas ──────────────────────────────────

def _company_due_value(company: rx.Var) -> rx.Component:
    return rx.cond(
        company["plan_type"] == "trial",
        rx.cond(
            company["trial_ends_at"],
            rx.el.span(
                company["trial_ends_at"],
                class_name="text-xs text-amber-600",
            ),
            rx.el.span("Sin fecha", class_name="text-xs text-slate-400 italic"),
        ),
        rx.cond(
            company["subscription_ends_at"],
            rx.el.span(
                company["subscription_ends_at"],
                class_name="text-xs text-slate-600",
            ),
            rx.el.span("Sin fecha", class_name="text-xs text-slate-400 italic"),
        ),
    )


def _company_modules(company: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.cond(
            company["has_reservations_module"],
            _owner_module_icon_badge(
                "calendar-days",
                "Servicios y Reservas",
                "bg-violet-50 text-violet-600",
            ),
            rx.fragment(),
        ),
        rx.cond(
            company["has_clients_module"],
            _owner_module_icon_badge(
                "users",
                "Clientes",
                "bg-sky-50 text-sky-600",
            ),
            rx.fragment(),
        ),
        rx.cond(
            company["has_credits_module"],
            _owner_module_icon_badge(
                "credit-card",
                "Cuentas Corrientes",
                "bg-amber-50 text-amber-600",
            ),
            rx.fragment(),
        ),
        rx.cond(
            company["has_electronic_billing"],
            _owner_module_icon_badge(
                "file-text",
                "Facturación Electrónica",
                "bg-indigo-50 text-indigo-600",
            ),
            rx.fragment(),
        ),
        class_name="flex items-center gap-1.5 flex-wrap",
    )


def _company_actions(company: rx.Var) -> rx.Component:
    return rx.el.div(
        _owner_action_icon_button(
            "repeat",
            "Cambiar Plan",
            on_click=State.owner_open_modal(
                "change_plan", company["id"], company["name"]
            ),
            tone="indigo",
        ),
        _owner_action_icon_button(
            "toggle-right",
            "Cambiar Estado",
            on_click=State.owner_open_modal(
                "change_status", company["id"], company["name"]
            ),
            tone="indigo",
        ),
        _owner_action_icon_button(
            "calendar-plus",
            "Extender Prueba",
            on_click=State.owner_open_modal(
                "extend_trial", company["id"], company["name"]
            ),
            tone="slate",
        ),
        _owner_action_icon_button(
            "sliders-horizontal",
            "Ajustar Límites",
            on_click=State.owner_open_modal(
                "adjust_limits", company["id"], company["name"]
            ),
            tone="slate",
        ),
        _owner_action_icon_button(
            "key-round",
            "Resetear Contraseña",
            on_click=State.owner_open_reset_modal(
                company["id"], company["name"]
            ),
            tone="slate",
        ),
        _owner_action_icon_button(
            "file-text",
            "Billing / Facturación",
            on_click=State.owner_open_billing_modal(
                company["id"], company["name"]
            ),
            tone="indigo",
        ),
        class_name="flex items-center gap-2 flex-wrap",
    )


def _company_row(company: rx.Var) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.div(
                rx.el.p(company["name"], class_name="font-medium text-slate-800 text-sm"),
                rx.el.p(
                    "RUC: ", company["ruc"],
                    class_name=TYPOGRAPHY["caption"],
                ),
                rx.el.div(
                    rx.icon("mail", class_name="h-3 w-3 text-slate-400"),
                    rx.el.span(company["admin_email"], class_name=TYPOGRAPHY["caption"]),
                    class_name="flex items-center gap-1 mt-1",
                ),
                rx.el.div(
                    rx.icon("phone", class_name="h-3 w-3 text-slate-400"),
                    rx.el.span(company["company_phone"], class_name=TYPOGRAPHY["caption"]),
                    class_name="flex items-center gap-1",
                ),
                class_name="flex flex-col gap-0.5",
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(_plan_badge(company["plan_type"]), class_name="px-4 py-3"),
        rx.el.td(_status_badge(company["effective_status"]), class_name="px-4 py-3"),
        rx.el.td(
            rx.el.span(
                company["current_users"],
                "/",
                company["max_users"],
                class_name="text-sm text-slate-700 tabular-nums",
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.span(
                company["current_branches"],
                "/",
                company["max_branches"],
                class_name="text-sm text-slate-700 tabular-nums",
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(_company_due_value(company), class_name="px-4 py-3"),
        rx.el.td(_company_modules(company), class_name="px-4 py-3"),
        rx.el.td(_company_actions(company), class_name="px-4 py-3"),
        class_name=f"border-b border-slate-100 hover:bg-slate-50 {TRANSITIONS['fast']}",
    )


def _company_mobile_card(company: rx.Var) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    company["name"],
                    class_name="font-semibold text-slate-800 text-sm leading-tight",
                ),
                rx.el.p(
                    "RUC: ", company["ruc"],
                    class_name=f"{TYPOGRAPHY['caption']} mt-0.5",
                ),
                class_name="flex flex-col min-w-0",
            ),
            _status_badge(company["effective_status"]),
            class_name="flex items-start justify-between gap-2",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon("mail", class_name="h-3 w-3 text-slate-400"),
                rx.el.span(company["admin_email"], class_name=TYPOGRAPHY["caption"]),
                class_name="flex items-center gap-1",
            ),
            rx.el.div(
                rx.icon("phone", class_name="h-3 w-3 text-slate-400"),
                rx.el.span(company["company_phone"], class_name=TYPOGRAPHY["caption"]),
                class_name="flex items-center gap-1",
            ),
            class_name="flex flex-col gap-1 mt-2 min-w-0",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span("Plan", class_name="text-xs text-slate-400 uppercase tracking-wide"),
                _plan_badge(company["plan_type"]),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.span("Usuarios", class_name="text-xs text-slate-400 uppercase tracking-wide"),
                rx.el.span(
                    company["current_users"],
                    "/",
                    company["max_users"],
                    class_name="text-sm text-slate-700 tabular-nums",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.span("Sucursales", class_name="text-xs text-slate-400 uppercase tracking-wide"),
                rx.el.span(
                    company["current_branches"],
                    "/",
                    company["max_branches"],
                    class_name="text-sm text-slate-700 tabular-nums",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.span("Vence", class_name="text-xs text-slate-400 uppercase tracking-wide"),
                _company_due_value(company),
                class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-2 gap-3 mt-3",
        ),
        rx.el.div(
            rx.el.span(
                "Módulos",
                class_name="text-xs text-slate-400 uppercase tracking-wide mt-0.5",
            ),
            _company_modules(company),
            class_name="flex flex-col gap-2 mt-3",
        ),
        rx.el.div(
            rx.el.span(
                "Acciones",
                class_name="text-xs text-slate-400 uppercase tracking-wide mt-0.5",
            ),
            _company_actions(company),
            class_name="flex flex-col gap-2 mt-3",
        ),
        class_name=f"bg-white border border-slate-200 {RADIUS['lg']} p-4",
    )


def _companies_table() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.foreach(State.owner_companies, _company_mobile_card),
            class_name="grid grid-cols-1 gap-3 md:grid-cols-2 xl:hidden",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("Empresa", scope="col", class_name="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider"),
                        rx.el.th("Plan", scope="col", class_name="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider"),
                        rx.el.th("Estado", scope="col", class_name="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider"),
                        rx.el.th("Usuarios", scope="col", class_name="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider"),
                        rx.el.th("Sucursales", scope="col", class_name="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider"),
                        rx.el.th("Vence", scope="col", class_name="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider"),
                        rx.el.th("Módulos", scope="col", class_name="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider"),
                        rx.el.th("Acciones", scope="col", class_name="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider"),
                        class_name="bg-slate-50 border-b border-slate-200",
                    ),
                ),
                rx.el.tbody(
                    rx.foreach(State.owner_companies, _company_row),
                ),
                class_name="w-full table-auto min-w-full",
            ),
            class_name="hidden xl:block overflow-x-auto",
        ),
        class_name=f"{CARD_STYLES['default']} p-3 sm:p-4",
    )


# ─── Paginación ──────────────────────────────────────────

def _pagination() -> rx.Component:
    return rx.el.div(
        rx.el.button(
            rx.icon("chevron-left", class_name="h-4 w-4"),
            "Anterior",
            on_click=State.owner_prev_page,
            disabled=State.owner_page <= 1,
            class_name=rx.cond(
                State.owner_page <= 1,
                BUTTON_STYLES["disabled_sm"],
                BUTTON_STYLES["secondary_sm"],
            ),
        ),
        rx.el.span(
            "Página ",
            State.owner_page,
            " de ",
            State.owner_total_pages,
            class_name="text-xs sm:text-sm text-slate-500",
        ),
        rx.el.button(
            "Siguiente",
            rx.icon("chevron-right", class_name="h-4 w-4"),
            on_click=State.owner_next_page,
            disabled=State.owner_page >= State.owner_total_pages,
            class_name=rx.cond(
                State.owner_page >= State.owner_total_pages,
                BUTTON_STYLES["disabled_sm"],
                BUTTON_STYLES["secondary_sm"],
            ),
        ),
        class_name="flex flex-wrap items-center justify-center gap-3 sm:gap-4 mt-4",
    )


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
        # Activar inmediatamente
        rx.el.div(
            rx.el.label(
                rx.el.input(
                    type="checkbox",
                    checked=State.owner_form_activate_now,
                    on_change=State.owner_set_form_activate_now,
                    class_name="mr-2 accent-emerald-600",
                ),
                "Activar cuenta inmediatamente",
                class_name="text-sm text-slate-700 flex items-center cursor-pointer",
            ),
            rx.el.p(
                "La empresa quedará activa tras el cambio de plan.",
                class_name="text-xs text-slate-400 ml-5",
            ),
            class_name="flex flex-col gap-0.5",
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
                        (State.owner_form_current_plan == "professional")
                        | (State.owner_form_current_plan == "enterprise"),
                        rx.Var.create(True),
                        rx.Var.create(False),
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


# ─── Tabla de auditoría ──────────────────────────────────

def _audit_log_card(log: rx.Var) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            rx.el.div(
                rx.el.span("Fecha", class_name="text-xs text-slate-400 uppercase tracking-wide"),
                rx.el.p(log["created_at"], class_name=TYPOGRAPHY["caption"]),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.span("Acción", class_name="text-xs text-slate-400 uppercase tracking-wide"),
                rx.el.p(log["action"], class_name=f"{TYPOGRAPHY['label']} break-words"),
                class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-1 gap-3 sm:grid-cols-2",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span("Actor", class_name="text-xs text-slate-400 uppercase tracking-wide"),
                rx.el.p(log["actor_email"], class_name=f"{TYPOGRAPHY['body']} break-all"),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.span("Empresa", class_name="text-xs text-slate-400 uppercase tracking-wide"),
                rx.el.p(log["target_company_name"], class_name=f"{TYPOGRAPHY['body']} break-words"),
                class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-1 gap-3 sm:grid-cols-2",
        ),
        rx.el.div(
            rx.el.span("Motivo", class_name="text-xs text-slate-400 uppercase tracking-wide"),
            rx.el.p(log["reason"], class_name=f"{TYPOGRAPHY['body_secondary']} break-words"),
            class_name="flex flex-col gap-1",
        ),
        class_name=f"flex flex-col gap-4 border border-slate-200 bg-white p-4 {RADIUS['lg']}",
    )

def _audit_section() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h3(
                rx.icon("shield-check", class_name="h-5 w-5 text-indigo-600"),
                "Registro de Auditoría",
                class_name=f"flex items-center gap-2 {TYPOGRAPHY['section_title']}",
            ),
            rx.el.button(
                rx.icon("refresh-cw", class_name="h-4 w-4"),
                "Recargar",
                on_click=State.owner_load_audit_logs(0),
                class_name=BUTTON_STYLES["secondary_sm"],
            ),
            class_name="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4",
        ),
        rx.cond(
            State.owner_audit_logs.length() > 0,
            rx.el.div(
                rx.el.div(
                    rx.foreach(State.owner_audit_logs, _audit_log_card),
                    class_name="flex flex-col gap-3 xl:hidden",
                ),
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("Fecha", scope="col", class_name="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase"),
                                rx.el.th("Actor", scope="col", class_name="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase"),
                                rx.el.th("Empresa", scope="col", class_name="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase"),
                                rx.el.th("Acción", scope="col", class_name="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase"),
                                rx.el.th("Motivo", scope="col", class_name="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase"),
                                class_name="bg-slate-50 border-b border-slate-200",
                            ),
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                State.owner_audit_logs,
                                lambda log: rx.el.tr(
                                    rx.el.td(
                                        log["created_at"],
                                        class_name="px-3 py-2 text-xs text-slate-500 whitespace-nowrap",
                                    ),
                                    rx.el.td(
                                        log["actor_email"],
                                        class_name="px-3 py-2 text-sm text-slate-700",
                                    ),
                                    rx.el.td(
                                        log["target_company_name"],
                                        class_name="px-3 py-2 text-sm text-slate-700",
                                    ),
                                    rx.el.td(
                                        log["action"],
                                        class_name="px-3 py-2 text-sm text-slate-700 font-medium",
                                    ),
                                    rx.el.td(
                                        log["reason"],
                                        class_name="px-3 py-2 text-sm text-slate-500 max-w-xs truncate",
                                    ),
                                    class_name=f"border-b border-slate-100 hover:bg-slate-50 {TRANSITIONS['fast']}",
                                ),
                            ),
                        ),
                        class_name="w-full table-auto min-w-full",
                    ),
                    class_name="hidden xl:block overflow-x-auto",
                ),
                class_name="flex flex-col gap-3",
            ),
            rx.el.div(
                rx.icon("inbox", class_name="h-8 w-8 text-slate-300"),
                rx.el.p("Sin registros de auditoría aún.", class_name="text-sm text-slate-400"),
                class_name="flex flex-col items-center gap-2 py-8",
            ),
        ),
        # Paginación de auditoría
        rx.cond(
            State.owner_audit_total > 20,
            rx.el.div(
                rx.el.button(
                    rx.icon("chevron-left", class_name="h-4 w-4"),
                    "Anterior",
                    on_click=State.owner_audit_prev_page,
                    disabled=State.owner_audit_page <= 1,
                    class_name=rx.cond(
                        State.owner_audit_page <= 1,
                        BUTTON_STYLES["disabled_sm"],
                        BUTTON_STYLES["secondary_sm"],
                    ),
                ),
                rx.el.span(
                    "Página ",
                    State.owner_audit_page,
                    " de ",
                    State.owner_audit_total_pages,
                    class_name=TYPOGRAPHY["body_secondary"],
                ),
                rx.el.button(
                    "Siguiente",
                    rx.icon("chevron-right", class_name="h-4 w-4"),
                    on_click=State.owner_audit_next_page,
                    disabled=State.owner_audit_page >= State.owner_audit_total_pages,
                    class_name=rx.cond(
                        State.owner_audit_page >= State.owner_audit_total_pages,
                        BUTTON_STYLES["disabled_sm"],
                        BUTTON_STYLES["secondary_sm"],
                    ),
                ),
                class_name="flex flex-wrap items-center justify-center gap-3 sm:gap-4 mt-4",
            ),
            rx.fragment(),
        ),
        class_name=f"{CARD_STYLES['default']} mt-6",
    )


# ─── Vista de acceso denegado ─────────────────────────────

def _access_denied() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("shield-x", class_name="h-16 w-16 text-red-400"),
            rx.el.h2(
                "Acceso Restringido",
                class_name="text-2xl font-bold text-slate-800 mt-4",
            ),
            rx.el.p(
                "Este panel es de uso exclusivo para administradores de la plataforma.",
                class_name=f"{TYPOGRAPHY['body_secondary']} mt-2 text-center max-w-md",
            ),
            rx.el.p(
                "Si llegaste aquí por error, regresa al sistema principal.",
                class_name="text-slate-400 text-sm mt-1 text-center max-w-md",
            ),
            rx.el.a(
                rx.el.button(
                    rx.icon("arrow-left", class_name="h-4 w-4"),
                    "Ir al Sistema de Ventas",
                    class_name=BUTTON_STYLES["primary"],
                ),
                href=_app_href("/"),
                class_name="mt-6",
            ),
            class_name="flex flex-col items-center justify-center py-20",
        ),
        class_name="w-full min-h-screen bg-slate-50 flex items-center justify-center",
        style={"fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif"},
    )


# ═══════════════════════════════════════════════════════════
# LAYOUT INDEPENDIENTE DEL BACKOFFICE
# ═══════════════════════════════════════════════════════════

def _owner_header() -> rx.Component:
    """Header propio del backoffice — completamente independiente del sistema de ventas."""
    return rx.el.header(
        rx.el.div(
            # Logo / Marca del backoffice
            rx.el.div(
                rx.el.div(
                    rx.icon("shield-check", class_name="h-5 w-5 text-white"),
                    class_name=f"p-2 bg-slate-800 {RADIUS['lg']}",
                ),
                rx.el.div(
                    rx.el.span(
                        "TUWAYKIAPP",
                        class_name="text-sm sm:text-base font-bold text-slate-800 tracking-tight",
                    ),
                    rx.el.span(
                        "Admin Plataforma",
                        class_name="text-xs text-slate-400 uppercase tracking-widest",
                    ),
                    class_name="flex flex-col leading-tight",
                ),
                class_name="flex items-center justify-center sm:justify-start gap-3",
            ),
            # Acciones del header — info de usuario + logout + link al sistema
            rx.el.div(
                # Link al sistema de ventas
                rx.el.a(
                    rx.el.button(
                        rx.icon("layout-dashboard", class_name="h-4 w-4"),
                        "Sistema de Ventas",
                        class_name=f"flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 px-3 py-2 {RADIUS['md']} hover:bg-slate-100 {TRANSITIONS['fast']}",
                    ),
                    href=_app_href("/"),
                ),
                # Separador
                rx.el.div(class_name="hidden sm:block w-px h-8 bg-slate-200"),
                # Usuario actual (sesión propia del owner, no del sistema de ventas)
                rx.el.div(
                    rx.image(
                        src=f"https://api.dicebear.com/9.x/initials/svg?seed={State.owner_session_email}&backgroundColor=1e293b&textColor=ffffff",
                        class_name=f"h-8 w-8 {RADIUS['full']} ring-2 ring-slate-200",
                    ),
                    rx.el.div(
                        rx.el.p(
                            State.owner_session_email,
                            class_name="text-sm font-semibold text-slate-800 truncate max-w-[180px] sm:max-w-none",
                        ),
                        rx.el.p(
                            "Propietario",
                            class_name=f"text-xs text-slate-500 bg-slate-100 px-1.5 py-0.5 {RADIUS['full']} inline-block",
                        ),
                        class_name="flex flex-col",
                    ),
                    class_name="flex items-center gap-2",
                ),
                # Logout del backoffice (no afecta sesión de ventas)
                rx.el.button(
                    rx.icon("log-out", class_name="h-4 w-4"),
                    on_click=State.owner_logout,
                    title="Cerrar sesión del backoffice",
                    aria_label="Cerrar sesión del backoffice",
                    class_name=f"p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 {RADIUS['md']} {TRANSITIONS['fast']}",
                ),
                class_name="flex items-center gap-2 sm:gap-3 flex-wrap justify-center sm:justify-end w-full sm:w-auto",
            ),
            class_name="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-0 w-full",
        ),
        class_name=f"sticky top-0 z-40 bg-white/95 backdrop-blur-sm border-b border-slate-200 {SHADOWS['sm']}",
    )


def _billing_modal() -> rx.Component:
    """Modal de gestión de billing técnico para una empresa."""
    _input = INPUT_STYLES["default"]
    _select = SELECT_STYLES["default"]
    _label = TYPOGRAPHY["label"]
    _help = TYPOGRAPHY["caption"]

    return rx.cond(
        State.owner_billing_modal_open,
        rx.el.div(
            # Overlay
            rx.el.div(
                on_click=State.owner_close_billing_modal,
                class_name="fixed inset-0 bg-black/40 z-[70] modal-overlay",
            ),
            # Panel
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.icon("file-text", class_name="h-5 w-5 text-indigo-600"),
                            class_name=f"p-2 bg-indigo-50 {RADIUS['lg']}",
                        ),
                        rx.el.div(
                            rx.el.h2(
                                "Configuración de Billing",
                                class_name=TYPOGRAPHY["section_title"],
                            ),
                            rx.el.p(
                                State.owner_billing_company_name,
                                class_name=TYPOGRAPHY["body_secondary"],
                            ),
                        ),
                        class_name="flex items-center gap-3",
                    ),
                    rx.el.button(
                        rx.icon("x", class_name="h-5 w-5"),
                        on_click=State.owner_close_billing_modal,
                        title="Cerrar",
                        aria_label="Cerrar",
                        class_name=BUTTON_STYLES["icon_ghost"],
                    ),
                    class_name="flex items-center justify-between p-4 border-b border-slate-200",
                ),
                # Body
                rx.cond(
                    State.owner_billing_loading,
                    rx.el.div(
                        rx.icon("loader-circle", class_name="h-6 w-6 text-slate-400 animate-spin"),
                        class_name="flex items-center justify-center py-12",
                    ),
                    rx.el.div(
                        # Context info (read-only)
                        rx.el.div(
                            rx.el.span(
                                "País: ", State.owner_billing_country,
                                class_name=TYPOGRAPHY["caption"],
                            ),
                            rx.el.span(" | ", class_name="text-xs text-slate-300"),
                            rx.el.span(
                                "RUC/CUIT: ", State.owner_billing_tax_id,
                                class_name=TYPOGRAPHY["caption"],
                            ),
                            rx.el.span(" | ", class_name="text-xs text-slate-300"),
                            rx.el.span(
                                State.owner_billing_business_name,
                                class_name="text-xs text-slate-600 font-medium",
                            ),
                            class_name="flex flex-wrap items-center gap-1 p-2 bg-slate-50 rounded-md",
                        ),
                        # Toggle activo
                        rx.el.div(
                            rx.el.label(
                                rx.el.input(
                                    type="checkbox",
                                    checked=State.owner_billing_is_active,
                                    on_change=State.owner_set_billing_is_active,
                                    class_name="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500",
                                ),
                                " Billing Activo",
                                class_name="flex items-center gap-2 text-sm font-medium text-slate-700 cursor-pointer",
                            ),
                            class_name="mt-1",
                        ),
                        # Ambiente
                        rx.el.div(
                            rx.el.label("Ambiente", class_name=_label),
                            rx.el.select(
                                rx.el.option("Sandbox (pruebas)", value="sandbox"),
                                rx.el.option("Producción", value="production"),
                                value=State.owner_billing_environment,
                                on_change=State.owner_set_billing_environment,
                                class_name=_select,
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                        # Nubefact URL (PE)
                        rx.cond(
                            State.owner_billing_country == "PE",
                            rx.el.div(
                                rx.el.div(
                                    rx.el.label("URL Nubefact", class_name=_label),
                                    rx.el.input(
                                        value=State.owner_billing_nubefact_url,
                                        on_change=State.owner_set_billing_nubefact_url,
                                        placeholder="https://api.nubefact.com/api/v1/...",
                                        class_name=_input,
                                    ),
                                    rx.el.p(
                                        "URL completa del endpoint Nubefact de esta empresa.",
                                        class_name=_help,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.label("Token Nubefact", class_name=_label),
                                    rx.el.input(
                                        type="password",
                                        placeholder=rx.cond(
                                            State.owner_billing_nubefact_token_display != "",
                                            State.owner_billing_nubefact_token_display,
                                            "Ingrese el token de API...",
                                        ),
                                        on_blur=State.owner_save_billing_nubefact_token,
                                        class_name=_input,
                                    ),
                                    rx.el.p(
                                        "Se guarda encriptado al salir del campo.",
                                        class_name=_help,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                class_name="grid grid-cols-1 md:grid-cols-2 gap-3",
                            ),
                            rx.fragment(),
                        ),
                        # AFIP (AR)
                        rx.cond(
                            State.owner_billing_country == "AR",
                            rx.el.div(
                                rx.el.div(
                                    rx.el.label("Punto de Venta AFIP", class_name=_label),
                                    rx.el.input(
                                        type="number",
                                        value=State.owner_billing_afip_punto_venta,
                                        on_change=State.owner_set_billing_afip_punto_venta,
                                        min="1",
                                        class_name=_input,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.label("Condición IVA Emisor", class_name=_label),
                                    rx.el.select(
                                        rx.el.option("Resp. Inscripto", value="RI"),
                                        rx.el.option("Monotributista", value="monotributo"),
                                        rx.el.option("Exento", value="exento"),
                                        value=State.owner_billing_emisor_iva,
                                        on_change=State.owner_set_billing_emisor_iva,
                                        class_name=_select,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.label("Concepto AFIP", class_name=_label),
                                    rx.el.select(
                                        rx.el.option("Productos", value="1"),
                                        rx.el.option("Servicios", value="2"),
                                        rx.el.option("Productos y Servicios", value="3"),
                                        value=State.owner_billing_afip_concepto,
                                        on_change=State.owner_set_billing_afip_concepto,
                                        class_name=_select,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.label("Umbral Identificación Factura B (ARS)", class_name=_label),
                                    rx.el.input(
                                        type="number",
                                        value=State.owner_billing_ar_threshold,
                                        on_change=State.owner_set_billing_ar_threshold,
                                        class_name=_input,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                class_name="grid grid-cols-1 md:grid-cols-4 gap-3",
                            ),
                            rx.fragment(),
                        ),
                        # Certificados AFIP (AR)
                        rx.cond(
                            State.owner_billing_country == "AR",
                            rx.el.div(
                                rx.el.h4(
                                    "Certificados AFIP",
                                    class_name="text-sm font-semibold text-slate-600",
                                ),
                                rx.el.p(
                                    "Pegue el contenido PEM completo (incluyendo BEGIN/END). "
                                    "Se guardan encriptados al salir del campo.",
                                    class_name=_help,
                                ),
                                rx.el.div(
                                    rx.el.div(
                                        rx.el.label("Certificado X.509 (.pem)", class_name=_label),
                                        rx.el.textarea(
                                            placeholder=rx.cond(
                                                State.owner_billing_cert_display != "",
                                                "****certificado configurado**** — pegue uno nuevo para reemplazar",
                                                "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
                                            ),
                                            on_blur=State.owner_save_afip_certificate,
                                            rows="4",
                                            class_name=_input + " font-mono text-xs resize-y min-h-[80px]",
                                        ),
                                        rx.cond(
                                            State.owner_billing_cert_display != "",
                                            rx.el.span(
                                                "✓ Certificado configurado",
                                                class_name="text-xs text-emerald-600 font-medium",
                                            ),
                                            rx.el.span(
                                                "⚠ Sin certificado",
                                                class_name="text-xs text-amber-600 font-medium",
                                            ),
                                        ),
                                        class_name="flex flex-col gap-1",
                                    ),
                                    rx.el.div(
                                        rx.el.label("Clave Privada RSA (.key)", class_name=_label),
                                        rx.el.textarea(
                                            placeholder=rx.cond(
                                                State.owner_billing_key_display != "",
                                                "****clave configurada**** — pegue una nueva para reemplazar",
                                                "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
                                            ),
                                            on_blur=State.owner_save_afip_private_key,
                                            rows="4",
                                            class_name=_input + " font-mono text-xs resize-y min-h-[80px]",
                                        ),
                                        rx.cond(
                                            State.owner_billing_key_display != "",
                                            rx.el.span(
                                                "✓ Clave privada configurada",
                                                class_name="text-xs text-emerald-600 font-medium",
                                            ),
                                            rx.el.span(
                                                "⚠ Sin clave privada",
                                                class_name="text-xs text-amber-600 font-medium",
                                            ),
                                        ),
                                        class_name="flex flex-col gap-1",
                                    ),
                                    class_name="grid grid-cols-1 md:grid-cols-2 gap-3",
                                ),
                                class_name="space-y-2 p-3 bg-amber-50/50 rounded-lg border border-amber-200/50",
                            ),
                            rx.fragment(),
                        ),
                        # Series / Numeración
                        rx.el.div(
                            rx.el.h4("Series y Numeración", class_name="text-sm font-semibold text-slate-600"),
                            rx.el.div(
                                rx.el.div(
                                    rx.el.label("Serie Factura", class_name=_label),
                                    rx.el.input(
                                        value=State.owner_billing_serie_factura,
                                        on_change=State.owner_set_billing_serie_factura,
                                        placeholder="F001",
                                        class_name=_input,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.label("Serie Boleta", class_name=_label),
                                    rx.el.input(
                                        value=State.owner_billing_serie_boleta,
                                        on_change=State.owner_set_billing_serie_boleta,
                                        placeholder="B001",
                                        class_name=_input,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                class_name="grid grid-cols-2 gap-3",
                            ),
                            class_name="space-y-2",
                        ),
                        # Cuota mensual
                        rx.el.div(
                            rx.el.label("Límite Mensual de Documentos", class_name=_label),
                            rx.el.input(
                                type="number",
                                value=State.owner_billing_max_limit,
                                on_change=State.owner_set_billing_max_limit,
                                min="0",
                                class_name=_input,
                            ),
                            rx.el.p(
                                "Standard=500, Professional=1000, Enterprise=2000",
                                class_name=_help,
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                        class_name="space-y-4 p-4 max-h-[60vh] overflow-y-auto",
                    ),
                ),
                # Footer
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=State.owner_close_billing_modal,
                        class_name=BUTTON_STYLES["secondary"],
                    ),
                    rx.el.button(
                        rx.cond(
                            State.owner_billing_loading,
                            rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"),
                            rx.icon("save", class_name="h-4 w-4"),
                        ),
                        " Guardar Configuración",
                        on_click=State.owner_save_billing_config,
                        disabled=State.owner_billing_loading,
                        class_name=rx.cond(
                            State.owner_billing_loading,
                            BUTTON_STYLES["disabled"],
                            BUTTON_STYLES["primary"],
                        ),
                    ),
                    class_name="flex items-center justify-end gap-3 p-4 border-t border-slate-200",
                ),
                class_name=(
                    "fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 "
                    "z-[71] w-[95vw] max-w-2xl bg-white rounded-xl shadow-2xl "
                    "border border-slate-200 modal-content"
                ),
            ),
        ),
        rx.fragment(),
    )


def _owner_content() -> rx.Component:
    """Contenido principal: tabla de empresas + auditoría."""
    return rx.el.div(
        # Header de la página
        rx.el.div(
            rx.el.div(
                rx.el.h1(
                    "Gestión de la Plataforma",
                    class_name="text-xl sm:text-2xl font-bold text-slate-800",
                ),
                rx.el.p(
                    "Administra empresas, planes, suscripciones y activaciones",
                    class_name=f"{TYPOGRAPHY['body_secondary']} mt-1",
                ),
                class_name="flex flex-col text-center sm:text-left",
            ),
            class_name="mb-5 sm:mb-6",
        ),
        _search_bar(),
        rx.cond(
            State.owner_loading,
            rx.el.div(
                rx.icon("loader-circle", class_name="h-6 w-6 text-slate-500 animate-spin"),
                rx.el.p("Cargando empresas...", class_name=TYPOGRAPHY["body_secondary"]),
                class_name="flex items-center gap-3 py-8 justify-center",
            ),
            rx.fragment(),
        ),
        _companies_table(),
        _pagination(),
        _audit_section(),
        _action_modal(),
        _reset_password_modal(),
        _billing_modal(),
        class_name="w-full max-w-7xl mx-auto px-3 sm:px-6 py-4 sm:py-6 fade-in-up",
    )


# ─── Página principal ─────────────────────────────────────

def owner_page() -> rx.Component:
    """Mini-sistema independiente del backoffice de owners.

    Layout completamente separado del Sistema de Ventas:
    - Sin sidebar del sistema de ventas
    - Header propio con marca "Admin Plataforma"
    - Fondo y estilo visual diferenciado
    - Login propio e independiente del sistema principal
    - Accesible SOLO para propietarios de plataforma autenticados
    """
    return rx.el.main(
        # Barra superior distintiva (gris oscuro para diferenciarse del sistema)
        rx.el.div(
            class_name="fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-slate-600 via-slate-800 to-slate-600 z-[60]",
        ),
        rx.cond(
            State.is_hydrated,
            rx.cond(
                State.is_owner_authenticated,
                # ───── BACKOFFICE: Layout propio ─────
                rx.el.div(
                    _owner_header(),
                    _owner_content(),
                    class_name="min-h-screen bg-slate-50",
                ),
                # ───── No autenticado en owner → redirigir a login owner ─────
                rx.el.div(
                    rx.el.div(
                        rx.icon("shield-alert", class_name="h-12 w-12 text-slate-400"),
                        rx.el.h2(
                            "Autenticación requerida",
                            class_name="text-xl font-bold text-slate-800 mt-4",
                        ),
                        rx.el.p(
                            "Debes iniciar sesión en el panel de administración.",
                            class_name=f"{TYPOGRAPHY['body_secondary']} mt-2",
                        ),
                        rx.el.a(
                            rx.el.button(
                                rx.icon("log-in", class_name="h-4 w-4"),
                                "Iniciar Sesión",
                                class_name=BUTTON_STYLES["primary"],
                            ),
                            href=OWNER_LOGIN_PATH,
                            class_name="mt-6",
                        ),
                        class_name="flex flex-col items-center justify-center py-20",
                    ),
                    class_name="w-full min-h-screen bg-slate-50 flex items-center justify-center",
                ),
            ),
            # ───── Skeleton loading ─────
            rx.el.div(
                rx.el.div(
                    rx.el.div(class_name="h-16 bg-white border-b border-slate-200"),
                    rx.el.div(
                        rx.el.div(class_name="h-8 w-64 rounded bg-slate-200 animate-pulse"),
                        rx.el.div(class_name="h-4 w-48 rounded bg-slate-200/60 animate-pulse mt-2"),
                        rx.el.div(class_name="h-64 rounded-xl bg-slate-200/30 animate-pulse mt-6"),
                        class_name="max-w-7xl mx-auto px-6 py-6",
                    ),
                    class_name="min-h-screen bg-slate-50",
                ),
            ),
        ),
        class_name="text-slate-900 w-full min-h-screen",
        style={"fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif"},
    )


# ═══════════════════════════════════════════════════════════
# PÁGINA DE LOGIN DEL OWNER BACKOFFICE
# ═══════════════════════════════════════════════════════════

def owner_login_page() -> rx.Component:
    """Página de login exclusiva del Owner Backoffice.

    Completamente independiente del login del Sistema de Ventas (/ingreso).
    Solo usuarios con is_platform_owner=True pueden acceder.
    """
    return rx.el.main(
        # Barra superior
        rx.el.div(
            class_name="fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-slate-600 via-slate-800 to-slate-600 z-[60]",
        ),
        rx.cond(
            State.is_hydrated,
            rx.cond(
                # Si ya está autenticado como owner, redirigir al backoffice
                State.is_owner_authenticated,
                rx.el.div(
                    rx.el.div(
                        rx.icon("loader-circle", class_name="h-8 w-8 text-slate-400 animate-spin"),
                        rx.el.p(
                            "Redirigiendo al panel...",
                            class_name="text-slate-500 mt-4",
                        ),
                        class_name="flex flex-col items-center justify-center py-20",
                    ),
                    class_name="w-full min-h-screen bg-slate-50 flex items-center justify-center",
                ),
                # Formulario de login
                rx.el.div(
                    rx.el.div(
                        # Logo
                        rx.el.div(
                            rx.el.div(
                                rx.icon("shield-check", class_name="h-7 w-7 sm:h-8 sm:w-8 text-white"),
                                class_name=f"p-3 bg-slate-800 {RADIUS['xl']}",
                            ),
                            rx.el.div(
                                rx.el.span(
                                    "TUWAYKIAPP",
                                    class_name="text-lg sm:text-xl font-bold text-slate-800 tracking-tight",
                                ),
                                rx.el.span(
                                    "Admin Plataforma",
                                    class_name="text-xs text-slate-400 uppercase tracking-widest",
                                ),
                                class_name="flex flex-col leading-tight",
                            ),
                            class_name="flex items-center justify-center gap-3 mb-8 w-full",
                        ),
                        # Título
                        rx.el.h1(
                            "Panel de Administración",
                            class_name="text-xl sm:text-2xl font-bold text-slate-800 text-center",
                        ),
                        rx.el.p(
                            "Ingrese sus credenciales de administrador de plataforma.",
                            class_name=f"{TYPOGRAPHY['body_secondary']} mt-1 mb-6 text-center",
                        ),
                        # Error message
                        rx.cond(
                            State.owner_login_error != "",
                            rx.el.div(
                                rx.el.div(
                                    rx.icon("circle-alert", class_name="h-4 w-4 text-red-500 flex-shrink-0"),
                                    rx.el.p(
                                        State.owner_login_error,
                                        class_name="text-sm text-red-600",
                                    ),
                                    class_name="flex items-center gap-2",
                                ),
                                role="alert",
                                class_name=f"p-3 bg-red-50 border border-red-200 {RADIUS['lg']} mb-4",
                            ),
                        ),
                        # Formulario
                        rx.el.form(
                            rx.el.div(
                                rx.el.label(
                                    "Email o Usuario",
                                    html_for="owner_email",
                                    class_name=f"block {TYPOGRAPHY['label']} mb-1.5",
                                ),
                                rx.el.input(
                                    name="owner_email",
                                    type="text",
                                    placeholder="admin@tuwaykiapp.local",
                                    auto_complete="username",
                                    required=True,
                                    class_name=INPUT_STYLES["default"] + " w-full",
                                ),
                                class_name="mb-4",
                            ),
                            rx.el.div(
                                rx.el.label(
                                    "Contraseña",
                                    html_for="owner_password",
                                    class_name=f"block {TYPOGRAPHY['label']} mb-1.5",
                                ),
                                rx.el.input(
                                    name="owner_password",
                                    type="password",
                                    placeholder="••••••••",
                                    auto_complete="current-password",
                                    required=True,
                                    class_name=INPUT_STYLES["default"] + " w-full",
                                ),
                                class_name="mb-6",
                            ),
                            rx.el.button(
                                rx.cond(
                                    State.owner_login_loading,
                                    rx.fragment(
                                        rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"),
                                        "Verificando...",
                                    ),
                                    rx.fragment(
                                        rx.icon("log-in", class_name="h-4 w-4"),
                                        "Iniciar Sesión",
                                    ),
                                ),
                                type="submit",
                                disabled=State.owner_login_loading,
                                class_name=f"w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-800 text-white font-medium {RADIUS['lg']} hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed {TRANSITIONS['fast']}",
                            ),
                            on_submit=State.owner_login,
                            reset_on_submit=False,
                        ),
                        # Separador
                        rx.el.div(
                            rx.el.div(class_name="flex-1 h-px bg-slate-200"),
                            rx.el.span(
                                "Acceso restringido",
                                class_name="px-3 text-xs text-slate-400 uppercase tracking-wide",
                            ),
                            rx.el.div(class_name="flex-1 h-px bg-slate-200"),
                            class_name="flex items-center mt-6 mb-4",
                        ),
                        rx.el.p(
                            "Este panel es de uso exclusivo para administradores de la plataforma TUWAYKIAPP. "
                            "El acceso no autorizado será registrado.",
                            class_name="text-xs text-slate-400 text-center leading-relaxed",
                        ),
                        class_name=f"w-full max-w-md bg-white {RADIUS['xl']} {SHADOWS['lg']} p-5 sm:p-8 border border-slate-200",
                    ),
                    class_name="w-full min-h-screen bg-slate-50 flex items-center justify-center px-3 sm:px-4",
                ),
            ),
            # Skeleton loading
            rx.el.div(
                rx.el.div(
                    rx.icon("loader-circle", class_name="h-8 w-8 text-slate-300 animate-spin"),
                    class_name="flex items-center justify-center py-20",
                ),
                class_name="w-full min-h-screen bg-slate-50 flex items-center justify-center",
            ),
        ),
        class_name="text-slate-900 w-full min-h-screen",
        style={"fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif"},
    )
