"""Reusable UI primitive components for the marketing landing page."""

import reflex as rx

from ._scripts import _track_event_script


def _nav_link(label: str, href: str, event_name: str = "", source: str = "") -> rx.Component:
    props = {}
    if event_name:
        props["on_click"] = rx.call_script(_track_event_script(event_name, source))
    return rx.el.a(
        label,
        href=href,
        class_name="text-sm font-semibold text-slate-600 transition-colors hover:text-slate-900",
        **props,
    )


def _metric_card(value: str, label: str, detail: str) -> rx.Component:
    return rx.el.div(
        rx.el.p(value, class_name="text-2xl font-extrabold text-slate-900 sm:text-3xl"),
        rx.el.p(label, class_name="mt-1 text-sm font-semibold text-slate-700"),
        rx.el.p(detail, class_name="mt-1 text-xs text-slate-500"),
        class_name="rounded-2xl border border-slate-200 bg-white px-5 py-5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
    )


def _trust_pill(icon: str, label: str) -> rx.Component:
    return rx.el.div(
        rx.icon(icon, class_name="h-4 w-4 text-emerald-700"),
        rx.el.span(label, class_name="text-xs font-semibold text-slate-700 sm:text-sm"),
        class_name="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 shadow-sm",
    )


def _industry_chip(icon: str, name: str, detail: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, class_name="h-5 w-5 text-slate-700"),
            class_name="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100",
        ),
        rx.el.div(
            rx.el.p(name, class_name="text-sm font-semibold text-slate-800"),
            rx.el.p(detail, class_name="text-xs text-slate-500"),
            class_name="leading-tight",
        ),
        class_name="inline-flex min-w-[200px] items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm",
    )


def _browser_frame(src: str, alt: str) -> rx.Component:
    """Tarjeta con barra de navegador simulada que envuelve una captura."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.span(class_name="h-2.5 w-2.5 rounded-full bg-slate-300"),
                rx.el.span(class_name="h-2.5 w-2.5 rounded-full bg-slate-300"),
                rx.el.span(class_name="h-2.5 w-2.5 rounded-full bg-slate-300"),
                class_name="flex items-center gap-1.5",
            ),
            class_name="flex items-center border-b border-slate-100 bg-slate-50/60 px-4 py-3",
        ),
        rx.el.div(
            rx.el.img(
                src=src,
                alt=alt,
                class_name="h-auto w-full object-cover",
            ),
            class_name="bg-white p-1",
        ),
        class_name="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-200/40 ring-1 ring-slate-900/5",
    )


def _hero_annotation_badge(icon: str, label: str, pos_cls: str, color_cls: str) -> rx.Component:
    return rx.el.div(
        rx.icon(icon, class_name="h-3.5 w-3.5 shrink-0"),
        rx.el.span(label, class_name="text-xs font-semibold whitespace-nowrap"),
        class_name=f"absolute {pos_cls} hidden lg:inline-flex items-center gap-1.5 {color_cls} rounded-full px-3 py-1.5 shadow-lg ring-1 ring-white/20 pointer-events-none",
    )


def _hero_preview_card() -> rx.Component:
    return rx.el.aside(
        rx.el.div(
            _browser_frame("/dashboard-screenshot.webp", "Dashboard de TUWAYKIAPP"),
            _hero_annotation_badge(
                "trending-up", "Ventas del día",
                "top-[12%] -left-[12%]",
                "bg-emerald-500 text-white",
            ),
            _hero_annotation_badge(
                "triangle-alert", "Alerta de stock",
                "top-[38%] -right-[14%]",
                "bg-amber-500 text-white",
            ),
            _hero_annotation_badge(
                "wallet", "Caja abierta",
                "bottom-[30%] -left-[12%]",
                "bg-indigo-500 text-white",
            ),
            _hero_annotation_badge(
                "bar-chart-3", "Reportes live",
                "bottom-[10%] -right-[12%]",
                "bg-violet-500 text-white",
            ),
            class_name="reveal relative",
        ),
        class_name="w-full",
    )


def _comparison_card(title: str, icon: str, points: list[str], tone: str = "negative") -> rx.Component:
    icon_bg = "bg-rose-50 text-rose-600" if tone == "negative" else "bg-emerald-50 text-emerald-700"
    border = "border-rose-100" if tone == "negative" else "border-emerald-100"
    bullet_icon = "x" if tone == "negative" else "check"
    bullet_color = "text-rose-500" if tone == "negative" else "text-emerald-600"
    rows = [
        rx.el.li(
            rx.icon(bullet_icon, class_name=f"h-4 w-4 {bullet_color} mt-0.5"),
            rx.el.span(point, class_name="text-sm text-slate-700"),
            class_name="flex items-start gap-2",
        )
        for point in points
    ]
    return rx.el.article(
        rx.el.div(rx.icon(icon, class_name="h-5 w-5"), class_name=f"inline-flex rounded-xl p-2.5 {icon_bg}"),
        rx.el.h3(title, class_name="mt-4 text-lg font-bold text-slate-900"),
        rx.el.ul(*rows, class_name="mt-4 space-y-2.5"),
        class_name=f"rounded-2xl border {border} bg-white p-7",
    )


def _module_card(icon: str, title: str, description: str, bullets: list[str]) -> rx.Component:
    rows = [
        rx.el.li(
            rx.icon("check", class_name="h-4 w-4 text-emerald-700 mt-0.5"),
            rx.el.span(item, class_name="text-sm text-slate-700"),
            class_name="flex items-start gap-2",
        )
        for item in bullets
    ]
    return rx.el.article(
        rx.el.div(rx.icon(icon, class_name="h-5 w-5 text-slate-700"), class_name="inline-flex items-center justify-center rounded-xl bg-slate-100 p-2.5"),
        rx.el.h3(title, class_name="mt-4 text-base font-bold text-slate-900"),
        rx.el.p(description, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
        rx.el.ul(*rows, class_name="mt-4 space-y-2"),
        class_name="rounded-2xl border border-slate-200 bg-white p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
    )


def _timeline_step(step: str, title: str, detail: str) -> rx.Component:
    return rx.el.article(
        rx.el.span(step, class_name="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white"),
        rx.el.div(
            rx.el.h3(title, class_name="text-base font-semibold text-slate-900"),
            rx.el.p(detail, class_name="mt-1 text-sm text-slate-600"),
            class_name="flex-1",
        ),
        class_name="flex items-start gap-4 rounded-2xl border border-slate-200 bg-white p-5",
    )


def _use_case_card(icon: str, title: str, description: str, features: list[str], accent: str = "indigo") -> rx.Component:
    accent_icon_cls = {
        "indigo": "bg-indigo-50 text-indigo-600",
        "emerald": "bg-emerald-50 text-emerald-600",
        "amber": "bg-amber-50 text-amber-600",
        "violet": "bg-violet-50 text-violet-600",
    }.get(accent, "bg-indigo-50 text-indigo-600")
    accent_bullet_cls = {
        "indigo": "text-indigo-600",
        "emerald": "text-emerald-600",
        "amber": "text-amber-600",
        "violet": "text-violet-600",
    }.get(accent, "text-indigo-600")
    accent_border_hover = {
        "indigo": "hover:border-indigo-200",
        "emerald": "hover:border-emerald-200",
        "amber": "hover:border-amber-200",
        "violet": "hover:border-violet-200",
    }.get(accent, "hover:border-indigo-200")
    rows = [
        rx.el.li(
            rx.icon("check", class_name=f"h-3.5 w-3.5 mt-0.5 shrink-0 {accent_bullet_cls}"),
            rx.el.span(feat, class_name="text-xs text-slate-600"),
            class_name="flex items-start gap-2",
        )
        for feat in features
    ]
    return rx.el.article(
        rx.el.div(
            rx.icon(icon, class_name="h-6 w-6"),
            class_name=f"inline-flex items-center justify-center rounded-xl p-3 {accent_icon_cls}",
        ),
        rx.el.h3(title, class_name="mt-4 text-base font-bold text-slate-900"),
        rx.el.p(description, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
        rx.el.ul(*rows, class_name="mt-4 space-y-1.5"),
        class_name=f"rounded-2xl border border-slate-200 bg-white p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md {accent_border_hover}",
    )


def _extra_capability_chip(icon: str, title: str, description: str) -> rx.Component:
    return rx.el.div(
        rx.icon(icon, class_name="h-4 w-4 text-slate-500 shrink-0"),
        rx.el.div(
            rx.el.p(title, class_name="text-sm font-semibold text-slate-800"),
            rx.el.p(description, class_name="text-xs text-slate-500 leading-relaxed"),
            class_name="flex flex-col gap-0.5",
        ),
        class_name="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 transition-all duration-200 hover:border-slate-300 hover:shadow-sm",
    )


def _strength_card(icon: str, title: str, detail: str) -> rx.Component:
    return rx.el.article(
        rx.el.div(rx.icon(icon, class_name="h-6 w-6 text-slate-900"), class_name="inline-flex items-center justify-center rounded-xl bg-slate-100 p-3"),
        rx.el.h3(title, class_name="mt-4 text-base font-bold text-slate-900"),
        rx.el.p(detail, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
        class_name="rounded-2xl border border-slate-200 bg-white p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
    )


def _plan_card(
    title: str, subtitle: str, price_label: str, points: list[str],
    cta_label: str, cta_href: str, event_name: str,
    tone: str = "standard", badge_text: str = "",
) -> rx.Component:
    is_enterprise = tone == "enterprise"
    is_professional = tone == "professional"

    card_cls = "rounded-2xl border bg-white p-7 transition-all duration-200 hover:-translate-y-1 hover:shadow-md"
    t_cls = "mt-3 text-lg font-bold text-slate-900"
    s_cls = "mt-2 text-sm text-slate-600"
    p_cls = "text-sm text-slate-700"
    chk = "text-emerald-600"
    pr_cls = "mt-6 text-4xl font-extrabold tracking-tight text-slate-900"
    per_cls = "text-xs font-semibold uppercase tracking-wide text-slate-500"
    cta_cls = "mt-8 inline-flex w-full items-center justify-center rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-800"

    if is_professional:
        card_cls += " border-slate-300 ring-1 ring-slate-900/5"
    else:
        card_cls += " border-slate-200"

    if is_enterprise:
        card_cls = "rounded-2xl border border-slate-800 bg-slate-900 p-7 transition-all duration-200 hover:-translate-y-1 hover:shadow-lg"
        t_cls = "mt-3 text-lg font-bold text-white"
        s_cls = "mt-2 text-sm text-slate-400"
        p_cls = "text-sm text-slate-300"
        chk = "text-emerald-400"
        pr_cls = "mt-6 text-4xl font-extrabold tracking-tight text-white"
        per_cls = "text-xs font-semibold uppercase tracking-wide text-slate-400"
        cta_cls = "mt-8 inline-flex w-full items-center justify-center rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition-colors hover:bg-slate-50"

    badge_cls = (
        "inline-flex rounded-full bg-slate-700 px-3 py-1 text-xs font-semibold text-slate-200"
        if is_enterprise
        else "inline-flex rounded-full bg-emerald-500 px-3 py-1 text-xs font-semibold text-white"
    )
    badge = rx.el.span(badge_text, class_name=badge_cls) if badge_text else rx.fragment()

    rows = [
        rx.el.li(
            rx.icon("check", class_name=f"h-4 w-4 {chk} mt-0.5"),
            rx.el.span(pt, class_name=p_cls),
            class_name="flex items-start gap-3",
        )
        for pt in points
    ]
    return rx.el.article(
        badge,
        rx.el.h3(title, class_name=t_cls),
        rx.el.p(subtitle, class_name=s_cls),
        rx.el.div(
            rx.el.p(price_label, class_name=pr_cls),
            rx.el.p("USD / mes", class_name=per_cls),
        ),
        rx.el.ul(*rows, class_name="mt-8 space-y-3"),
        rx.el.a(
            cta_label, href=cta_href, target="_blank", rel="noopener noreferrer",
            on_click=rx.call_script(_track_event_script(event_name, f"plan_{title.lower()}")),
            class_name=cta_cls,
        ),
        class_name=card_cls,
    )


def _faq_item(question: str, answer: str, open_by_default: bool = False) -> rx.Component:
    open_props = {"open": True} if open_by_default else {}
    return rx.el.details(
        rx.el.summary(
            rx.el.div(
                rx.icon("circle-help", class_name="h-4 w-4 text-slate-400"),
                rx.el.p(question, class_name="text-sm font-semibold text-slate-900"),
                class_name="flex items-center gap-2.5",
            ),
            rx.icon("chevron-right", class_name="faq-chevron h-4 w-4 text-slate-400"),
            class_name="flex cursor-pointer list-none items-center justify-between gap-3",
        ),
        rx.el.p(answer, class_name="mt-3 text-sm leading-relaxed text-slate-600"),
        class_name="faq-item rounded-2xl border border-slate-200 bg-white p-5 transition-all duration-200 open:border-slate-300 open:shadow-sm",
        **open_props,
    )


def _footer_link(label: str, href: str, event_name: str, source: str, external: bool = False) -> rx.Component:
    return rx.el.a(
        label, href=href,
        target="_blank" if external else None,
        rel="noopener noreferrer" if external else None,
        on_click=rx.call_script(_track_event_script(event_name, source)),
        class_name="text-sm text-slate-600 transition-colors hover:text-slate-900",
    )
