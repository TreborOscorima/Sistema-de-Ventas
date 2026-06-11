import reflex as rx

from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    CARD_STYLES,
    INPUT_STYLES,
    RADIUS,
    TRANSITIONS,
    TYPOGRAPHY,
)
from ._shared import _plan_badge, _status_badge, _owner_action_icon_button, _owner_module_icon_badge


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
                class_name="w-full min-w-[1000px]",
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
