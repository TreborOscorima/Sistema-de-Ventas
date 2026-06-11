import reflex as rx

from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    CARD_STYLES,
    TRANSITIONS,
    TYPOGRAPHY,
)
from app.components.ui import RADIUS


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
