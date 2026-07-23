import reflex as rx

from app.state import State
from app.components.ui import CARD_STYLES, RADIUS, TRANSITIONS, TYPOGRAPHY


def _metric_card(
    icon: str,
    label: str,
    value: rx.Var,
    suffix: str = "",
    tone: str = "slate",
) -> rx.Component:
    tone_map = {
        "emerald": ("bg-emerald-50", "text-emerald-600"),
        "indigo": ("bg-indigo-50", "text-indigo-600"),
        "amber": ("bg-amber-50", "text-amber-600"),
        "violet": ("bg-violet-50", "text-violet-600"),
        "red": ("bg-red-50", "text-red-500"),
        "sky": ("bg-sky-50", "text-sky-600"),
        "slate": ("bg-slate-100", "text-slate-600"),
    }
    bg, fg = tone_map.get(tone, tone_map["slate"])

    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon(icon, class_name=f"h-5 w-5 {fg}"),
                class_name=f"p-2.5 {bg} {RADIUS['lg']}",
            ),
            rx.el.div(
                rx.el.p(label, class_name="text-xs font-medium text-slate-500 uppercase tracking-wide"),
                rx.el.p(
                    value,
                    suffix,
                    class_name="text-2xl font-bold text-slate-800 tabular-nums mt-1",
                ),
                class_name="flex flex-col min-w-0",
            ),
            class_name="flex items-start gap-3",
        ),
        class_name=f"bg-white border border-slate-200 {RADIUS['xl']} p-4 {TRANSITIONS['fast']} hover:shadow-sm",
    )


def _plan_distribution_bar() -> rx.Component:
    """Barra visual de distribución por plan."""
    m = State.owner_metrics
    total = m["total_companies"].to(int)

    def _segment(plan_key: str, label: str, color: str) -> rx.Component:
        count = m[plan_key].to(int)
        pct = rx.cond(total > 0, (count * 100 / total), 0)
        return rx.cond(
            count > 0,
            rx.el.div(
                title=label + ": " + count.to(str),
                class_name=f"h-full {color} {TRANSITIONS['fast']}",
                style={"width": pct.to(str) + "%", "minWidth": "4px"},
            ),
            rx.fragment(),
        )

    return rx.el.div(
        rx.el.div(
            rx.el.span("Distribución por Plan", class_name="text-xs font-medium text-slate-500 uppercase tracking-wide"),
            class_name="mb-2",
        ),
        rx.el.div(
            _segment("plan_trial", "Trial", "bg-amber-400 rounded-l"),
            _segment("plan_standard", "Standard", "bg-indigo-500"),
            _segment("plan_professional", "Professional", "bg-purple-500"),
            _segment("plan_enterprise", "Enterprise", "bg-emerald-500 rounded-r"),
            class_name=f"flex h-3 {RADIUS['full']} overflow-hidden bg-slate-100",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(class_name="inline-block w-2.5 h-2.5 rounded-sm bg-amber-400"),
                rx.el.span("Trial ", m["plan_trial"].to(int), class_name="text-xs text-slate-600"),
                class_name="flex items-center gap-1.5",
            ),
            rx.el.div(
                rx.el.span(class_name="inline-block w-2.5 h-2.5 rounded-sm bg-indigo-500"),
                rx.el.span("Standard ", m["plan_standard"].to(int), class_name="text-xs text-slate-600"),
                class_name="flex items-center gap-1.5",
            ),
            rx.el.div(
                rx.el.span(class_name="inline-block w-2.5 h-2.5 rounded-sm bg-purple-500"),
                rx.el.span("Professional ", m["plan_professional"].to(int), class_name="text-xs text-slate-600"),
                class_name="flex items-center gap-1.5",
            ),
            rx.el.div(
                rx.el.span(class_name="inline-block w-2.5 h-2.5 rounded-sm bg-emerald-500"),
                rx.el.span("Enterprise ", m["plan_enterprise"].to(int), class_name="text-xs text-slate-600"),
                class_name="flex items-center gap-1.5",
            ),
            class_name="flex flex-wrap items-center gap-4 mt-2",
        ),
        class_name=f"bg-white border border-slate-200 {RADIUS['xl']} p-4",
    )


def _metrics_section() -> rx.Component:
    """Sección de métricas MRR/churn/distribución del Owner dashboard."""
    m = State.owner_metrics

    return rx.cond(
        State.owner_metrics_loading,
        rx.el.div(
            rx.icon("loader-circle", class_name="h-5 w-5 text-slate-400 animate-spin"),
            rx.el.span("Cargando métricas...", class_name=TYPOGRAPHY["body_secondary"]),
            class_name="flex items-center gap-2 py-4 justify-center",
        ),
        rx.cond(
            m.contains("total_companies"),
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.icon("bar-chart-3", class_name="h-5 w-5 text-indigo-600"),
                        rx.el.h2(
                            "Métricas de Plataforma",
                            class_name="text-base font-semibold text-slate-700",
                        ),
                        class_name="flex items-center gap-2",
                    ),
                    rx.el.button(
                        rx.icon("refresh-cw", class_name="h-3.5 w-3.5"),
                        "Actualizar",
                        on_click=State.owner_load_metrics,
                        class_name=f"flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 px-2 py-1 {RADIUS['md']} hover:bg-slate-100 {TRANSITIONS['fast']} cursor-pointer",
                    ),
                    class_name="flex items-center justify-between mb-4",
                ),
                rx.el.div(
                    _metric_card(
                        "dollar-sign", "MRR",
                        "$" + m["mrr"].to(float).to(str),
                        " USD",
                        tone="emerald",
                    ),
                    _metric_card(
                        "trending-up", "ARR",
                        "$" + m["arr"].to(float).to(str),
                        " USD",
                        tone="indigo",
                    ),
                    _metric_card(
                        "building-2", "Empresas",
                        m["total_companies"].to(int).to(str),
                        "",
                        tone="sky",
                    ),
                    _metric_card(
                        "credit-card", "Pagantes",
                        m["total_paying"].to(int).to(str),
                        "",
                        tone="violet",
                    ),
                    _metric_card(
                        "user-minus", "Churn (30d)",
                        m["churn_rate"].to(float).to(str),
                        "%",
                        tone="red",
                    ),
                    _metric_card(
                        "arrow-right-left", "Conversión Trial (30d)",
                        m["trial_conversion"].to(float).to(str),
                        "%",
                        tone="amber",
                    ),
                    _metric_card(
                        "calendar-plus", "Nuevas (7d)",
                        m["new_7d"].to(int).to(str),
                        "",
                        tone="sky",
                    ),
                    _metric_card(
                        "calendar-range", "Nuevas (30d)",
                        m["new_30d"].to(int).to(str),
                        "",
                        tone="slate",
                    ),
                    class_name="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4",
                ),
                _plan_distribution_bar(),
                class_name=CARD_STYLES["default"] + " mb-6",
            ),
            rx.fragment(),
        ),
    )
