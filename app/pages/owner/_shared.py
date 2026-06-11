import os

import reflex as rx

from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    RADIUS,
    TRANSITIONS,
)
from app.utils.env import APP_SURFACE

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
