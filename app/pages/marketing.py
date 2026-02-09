import reflex as rx


def _nav_link(label: str, href: str) -> rx.Component:
    return rx.el.a(
        label,
        href=href,
        class_name=(
            "text-sm font-medium text-slate-600 hover:text-slate-900 "
            "transition-colors duration-150"
        ),
    )


def _metric_card(value: str, label: str) -> rx.Component:
    return rx.el.div(
        rx.el.p(value, class_name="text-2xl sm:text-3xl font-extrabold text-slate-900"),
        rx.el.p(label, class_name="text-xs sm:text-sm text-slate-600"),
        class_name=(
            "rounded-2xl border border-slate-200/80 bg-white/90 backdrop-blur px-4 py-4 shadow-sm "
            "transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        ),
    )


def _module_card(icon: str, title: str, description: str, outcome: str) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            class_name="h-1 w-16 rounded-full bg-gradient-to-r from-emerald-400 to-cyan-400",
        ),
        rx.el.div(
            rx.icon(icon, class_name="h-5 w-5 text-emerald-700"),
            class_name="inline-flex items-center justify-center rounded-xl bg-emerald-100 p-2",
        ),
        rx.el.h3(title, class_name="mt-4 text-base font-bold text-slate-900"),
        rx.el.p(description, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
        rx.el.div(
            rx.icon("badge-check", class_name="h-4 w-4 text-emerald-700"),
            rx.el.p(outcome, class_name="text-sm font-medium text-slate-700"),
            class_name="mt-4 flex items-start gap-2",
        ),
        class_name=(
            "group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm "
            "transition-all duration-200 hover:-translate-y-1 hover:shadow-lg hover:border-emerald-200"
        ),
    )


def _step_card(step: str, title: str, detail: str) -> rx.Component:
    return rx.el.div(
        rx.el.span(
            step,
            class_name=(
                "inline-flex h-8 w-8 items-center justify-center rounded-full "
                "bg-slate-900 text-xs font-bold text-white"
            ),
        ),
        rx.el.div(
            rx.el.h3(title, class_name="text-base font-semibold text-slate-900"),
            rx.el.p(detail, class_name="mt-1 text-sm text-slate-600"),
            class_name="flex-1",
        ),
        class_name=(
            "flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 "
            "transition-all duration-200 hover:border-slate-300 hover:shadow-sm"
        ),
    )


def _plan_card(
    title: str,
    subtitle: str,
    points: list[str],
    cta_label: str,
    cta_href: str,
    tone: str = "standard",
    badge_text: str = "",
) -> rx.Component:
    is_enterprise = tone == "enterprise"
    is_professional = tone == "professional"

    card_class = (
        "rounded-2xl border bg-white p-6 shadow-sm transition-all duration-200 "
        "hover:-translate-y-1 hover:shadow-xl"
    )
    subtitle_class = "mt-2 text-sm text-slate-600"
    point_text_class = "text-sm text-slate-700"
    check_color = "text-emerald-700"
    cta_class = (
        "mt-6 inline-flex w-full items-center justify-center rounded-xl bg-slate-900 px-4 "
        "py-2.5 text-sm font-semibold text-white hover:bg-slate-800 transition-colors duration-150"
    )

    if is_professional:
        card_class += " ring-2 ring-emerald-400 border-emerald-200"
    else:
        card_class += " border-slate-200"

    if is_enterprise:
        card_class = (
            "rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-lg transition-all "
            "duration-200 hover:-translate-y-1 hover:shadow-2xl"
        )
        subtitle_class = "mt-2 text-sm text-slate-300"
        point_text_class = "text-sm text-slate-200"
        check_color = "text-emerald-300"
        cta_class = (
            "mt-6 inline-flex w-full items-center justify-center rounded-xl bg-emerald-500 px-4 "
            "py-2.5 text-sm font-semibold text-white hover:bg-emerald-400 transition-colors duration-150"
        )

    badge = (
        rx.el.span(
            badge_text,
            class_name=(
                "inline-flex rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700"
            ),
        )
        if badge_text
        else rx.fragment()
    )

    point_rows = [
        rx.el.li(
            rx.icon("check", class_name=f"h-4 w-4 {check_color}"),
            rx.el.span(point, class_name=point_text_class),
            class_name="flex items-start gap-2",
        )
        for point in points
    ]

    return rx.el.article(
        badge,
        rx.el.h3(
            title,
            class_name="mt-2 text-lg font-bold text-white" if is_enterprise else "mt-2 text-lg font-bold text-slate-900",
        ),
        rx.el.p(subtitle, class_name=subtitle_class),
        rx.el.ul(*point_rows, class_name="mt-5 space-y-2"),
        rx.el.a(
            cta_label,
            href=cta_href,
            target="_blank" if cta_href.startswith("https://") else None,
            rel="noopener noreferrer" if cta_href.startswith("https://") else None,
            class_name=cta_class,
        ),
        class_name=card_class,
    )


def _faq_item(question: str, answer: str, open_by_default: bool = False) -> rx.Component:
    open_props = {"open": True} if open_by_default else {}
    return rx.el.details(
        rx.el.summary(
            rx.el.div(
                rx.icon("circle-help", class_name="h-4 w-4 text-emerald-700"),
                rx.el.p(question, class_name="text-sm font-semibold text-slate-900"),
                class_name="flex items-center gap-2",
            ),
            rx.icon("chevron-right", class_name="h-4 w-4 text-slate-500"),
            class_name="flex cursor-pointer list-none items-center justify-between gap-3",
        ),
        rx.el.p(answer, class_name="mt-3 text-sm leading-relaxed text-slate-600"),
        class_name=(
            "rounded-xl border border-slate-200 bg-white p-4 transition-all duration-200 "
            "open:border-emerald-200 open:shadow-sm"
        ),
        **open_props,
    )


def marketing_page() -> rx.Component:
    demo_link = (
        "https://wa.me/5491168376517?text="
        "Hola,%20quiero%20una%20demo%20en%20vivo%20de%20TUWAYKIAPP."
    )
    sales_link = (
        "https://wa.me/5491168376517?text="
        "Hola,%20quiero%20informacion%20comercial%20de%20TUWAYKIAPP."
    )
    enterprise_link = (
        "https://wa.me/5491168376517?text="
        "Hola,%20quiero%20una%20propuesta%20del%20Plan%20Enterprise%20de%20TUWAYKIAPP."
    )

    return rx.el.div(
        rx.el.style(
            "@import url('https://fonts.googleapis.com/css2?"
            "family=Sora:wght@400;600;700;800&family=Public+Sans:wght@400;500;600&display=swap');"
            "@keyframes floatY{0%,100%{transform:translateY(0px);}50%{transform:translateY(-16px);}}"
            "@keyframes pulseSoft{0%,100%{opacity:.35;}50%{opacity:.7;}}"
            ".orb-a{animation:floatY 10s ease-in-out infinite;}"
            ".orb-b{animation:floatY 13s ease-in-out infinite reverse;}"
            ".orb-c{animation:pulseSoft 8s ease-in-out infinite;}"
        ),
        rx.el.div(
            rx.el.div(
                class_name=(
                    "orb-a absolute -top-32 -left-24 h-80 w-80 rounded-full bg-emerald-300/30 blur-3xl"
                ),
            ),
            rx.el.div(
                class_name=(
                    "orb-b absolute top-40 -right-24 h-80 w-80 rounded-full bg-sky-300/30 blur-3xl"
                ),
            ),
            rx.el.div(
                class_name=(
                    "orb-c absolute bottom-0 left-1/3 h-72 w-72 rounded-full bg-cyan-300/20 blur-3xl"
                ),
            ),
            class_name="pointer-events-none absolute inset-0 overflow-hidden",
        ),
        rx.el.header(
            rx.el.div(
                rx.el.a(
                    rx.icon("box", class_name="h-5 w-5 text-slate-900"),
                    rx.el.span("TUWAYKIAPP", class_name="font-bold text-slate-900"),
                    href="/sitio",
                    class_name="flex items-center gap-2",
                ),
                rx.el.nav(
                    _nav_link("Modulos", "#modulos"),
                    _nav_link("Planes", "#planes"),
                    _nav_link("FAQ", "#faq"),
                    _nav_link("Ingresar", "/"),
                    class_name="hidden items-center gap-6 md:flex",
                ),
                rx.el.a(
                    "Demo + Trial",
                    href="/registro",
                    class_name=(
                        "inline-flex items-center justify-center rounded-xl bg-emerald-600 "
                        "px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 "
                        "transition-colors duration-150"
                    ),
                ),
                class_name=(
                    "mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8"
                ),
            ),
            class_name=(
                "sticky top-0 z-50 border-b border-slate-200/70 bg-white/85 backdrop-blur supports-[backdrop-filter]:bg-white/75"
            ),
        ),
        rx.el.main(
            rx.el.section(
                rx.el.div(
                    rx.el.span(
                        "SaaS para tiendas, servicios y reservas",
                        class_name=(
                            "inline-flex rounded-full border border-emerald-200 bg-emerald-50 "
                            "px-3 py-1 text-xs font-semibold text-emerald-700"
                        ),
                    ),
                    rx.el.h1(
                        "Controla ventas, caja, inventario y servicios en una sola plataforma.",
                        class_name=(
                            "mt-4 text-3xl font-extrabold tracking-tight text-slate-900 "
                            "sm:text-5xl"
                        ),
                    ),
                    rx.el.p(
                        "TUWAYKIAPP ayuda a negocios multiempresa a cobrar mas rapido, "
                        "reducir errores operativos y tomar decisiones con reportes claros.",
                        class_name="mt-4 max-w-2xl text-base leading-relaxed text-slate-600 sm:text-lg",
                    ),
                    rx.el.div(
                        rx.el.span(
                            "Activa demo trial de 15 dias y valida el sistema en tu operacion real.",
                            class_name=(
                                "inline-flex rounded-full border border-sky-200 bg-sky-50 px-3 py-1 "
                                "text-xs font-semibold text-sky-700"
                            ),
                        ),
                        class_name="mt-4",
                    ),
                    rx.el.div(
                        rx.el.a(
                            "Comenzar trial de 15 dias",
                            href="/registro",
                            class_name=(
                                "inline-flex items-center justify-center rounded-xl bg-slate-900 "
                                "px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800 "
                                "transition-colors duration-150"
                            ),
                        ),
                        rx.el.a(
                            rx.icon("message-circle", class_name="h-4 w-4"),
                            "Agendar demo guiada",
                            href=demo_link,
                            target="_blank",
                            rel="noopener noreferrer",
                            class_name=(
                                "inline-flex items-center gap-2 rounded-xl border border-slate-300 "
                                "bg-white px-5 py-3 text-sm font-semibold text-slate-700 "
                                "hover:bg-slate-50 transition-colors duration-150"
                            ),
                        ),
                        class_name="mt-7 flex flex-col gap-3 sm:flex-row",
                    ),
                    rx.el.div(
                        _metric_card("+35%", "mejor control de caja diaria"),
                        _metric_card("-60%", "menos diferencias de stock"),
                        _metric_card("15 dias", "trial gratis sin tarjeta"),
                        class_name="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3",
                    ),
                    class_name="max-w-3xl",
                ),
                class_name="mx-auto w-full max-w-6xl px-4 pb-14 pt-14 sm:px-6 lg:px-8 lg:pt-20",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.p(
                        "Pensado para operaciones reales:",
                        class_name="text-xs font-semibold uppercase tracking-wide text-slate-500",
                    ),
                    rx.el.div(
                        rx.el.div(
                            rx.icon("building-2", class_name="h-4 w-4 text-slate-700"),
                            rx.el.span("Tiendas con ventas rapidas", class_name="text-sm text-slate-700"),
                            class_name="flex items-center gap-2",
                        ),
                        rx.el.div(
                            rx.icon("calendar-check", class_name="h-4 w-4 text-slate-700"),
                            rx.el.span("Negocios con reservas", class_name="text-sm text-slate-700"),
                            class_name="flex items-center gap-2",
                        ),
                        rx.el.div(
                            rx.icon("users", class_name="h-4 w-4 text-slate-700"),
                            rx.el.span("Equipos multiusuario y sucursales", class_name="text-sm text-slate-700"),
                            class_name="flex items-center gap-2",
                        ),
                        class_name="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3",
                    ),
                    class_name="mx-auto w-full max-w-6xl rounded-2xl border border-slate-200 bg-white p-5 sm:p-6",
                ),
                class_name="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Todo lo que necesitas para operar con orden",
                        class_name="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.p(
                        "Cada modulo esta conectado para evitar doble carga de datos y darte trazabilidad completa.",
                        class_name="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                    ),
                    rx.el.div(
                        _module_card(
                            "shopping-cart",
                            "Ventas de producto",
                            "Cobros rapidos con multiples metodos de pago, tickets y control por usuario.",
                            "Menos tiempo en caja y menos errores en el cierre.",
                        ),
                        _module_card(
                            "package",
                            "Inventario inteligente",
                            "Stock por sucursal, categorias, unidades y movimientos con historial detallado.",
                            "Reposicion mas precisa y menos quiebres de stock.",
                        ),
                        _module_card(
                            "calendar-plus",
                            "Reservas y servicios",
                            "Agenda de campos/servicios con adelantos, cobro final y comprobantes.",
                            "Mayor ocupacion y flujo de caja mas predecible.",
                        ),
                        _module_card(
                            "wallet",
                            "Caja y arqueo",
                            "Apertura, cierre, movimientos y auditoria de ingresos/egresos.",
                            "Visibilidad diaria del efectivo real.",
                        ),
                        _module_card(
                            "users",
                            "Usuarios y roles por tenant",
                            "Permisos por empresa y sucursal con aislamiento multi-tenant.",
                            "Mas seguridad y control operativo.",
                        ),
                        _module_card(
                            "pie-chart",
                            "Reportes ejecutivos",
                            "Metricas por periodo, sucursal y categoria para decisiones comerciales.",
                            "Detecta oportunidades y corrige desvíos a tiempo.",
                        ),
                        class_name="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3",
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:px-8",
                    id="modulos",
                ),
                class_name="mx-auto w-full max-w-6xl",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Flujos clave que puedes ejecutar hoy",
                        class_name="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.p(
                        "Desde el primer dia puedes operar punta a punta sin depender de hojas de calculo.",
                        class_name="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                    ),
                    rx.el.div(
                        _step_card(
                            "01",
                            "Alta de empresa y sucursal",
                            "Registro rapido con usuario admin, empresa inicial y configuracion base.",
                        ),
                        _step_card(
                            "02",
                            "Roles por tenant",
                            "Crea perfiles por empresa para separar funciones y accesos.",
                        ),
                        _step_card(
                            "03",
                            "Venta de producto",
                            "Genera ticket, descuenta stock y registra el movimiento de caja.",
                        ),
                        _step_card(
                            "04",
                            "Reserva y cobro de servicio",
                            "Agenda, cobra adelanto, confirma pago final y deja trazabilidad completa.",
                        ),
                        _step_card(
                            "05",
                            "Cierre y reporte",
                            "Valida caja diaria y consulta reportes para ajustar decisiones comerciales.",
                        ),
                        class_name="mt-8 grid grid-cols-1 gap-3 md:grid-cols-2",
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:px-8",
                ),
                class_name="mx-auto w-full max-w-6xl bg-slate-50",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Planes para crecer sin friccion",
                        class_name="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.p(
                        "El trial/demo se activa al registrarte. Aqui eliges el plan de crecimiento comercial.",
                        class_name="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base",
                    ),
                    rx.el.div(
                        _plan_card(
                            "Standard",
                            "Para negocios en crecimiento con operacion diaria estable.",
                            [
                                "Mas sucursales y usuarios",
                                "Reportes mas profundos",
                                "Acompanamiento de implementacion",
                                "Soporte comercial continuo",
                            ],
                            "Hablar con ventas",
                            sales_link,
                            tone="standard",
                        ),
                        _plan_card(
                            "Professional",
                            "Para operaciones multi-sucursal con mayor exigencia de control.",
                            [
                                "Configuracion avanzada",
                                "Prioridad de soporte",
                                "Gobernanza operativa",
                                "Escalabilidad para alto volumen",
                            ],
                            "Solicitar propuesta",
                            sales_link,
                            tone="professional",
                            badge_text="Mas elegido",
                        ),
                        _plan_card(
                            "Enterprise",
                            "Para companias que requieren maxima escala, control y personalizacion.",
                            [
                                "Arquitectura y onboarding dedicado",
                                "Soporte prioritario y SLA",
                                "Integraciones y flujos a medida",
                                "Estrategia de escalamiento enterprise",
                            ],
                            "Solicitar Enterprise",
                            enterprise_link,
                            tone="enterprise",
                            badge_text="Escala total",
                        ),
                        class_name="mt-8 grid grid-cols-1 gap-4 lg:grid-cols-3",
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:px-8",
                    id="planes",
                ),
                class_name="mx-auto w-full max-w-6xl",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.h2(
                        "Preguntas frecuentes",
                        class_name="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl",
                    ),
                    rx.el.div(
                        _faq_item(
                            "Cuanto tarda implementarlo?",
                            "Puedes comenzar el mismo dia. El onboarding base toma minutos.",
                            open_by_default=True,
                        ),
                        _faq_item(
                            "Necesito tarjeta para el trial?",
                            "No. Puedes activar la prueba de 15 dias sin tarjeta.",
                        ),
                        _faq_item(
                            "Sirve para varias empresas o sucursales?",
                            "Si. El sistema es multi-tenant y maneja aislamiento por empresa.",
                        ),
                        _faq_item(
                            "Puedo cobrar productos y servicios en el mismo sistema?",
                            "Si. Incluye flujo de ventas, reservas, adelantos y cobro final.",
                        ),
                        _faq_item(
                            "Que pasa cuando termino el trial?",
                            "Si te interesa continuar, eliges Standard, Professional o Enterprise sin perder continuidad operativa.",
                        ),
                        class_name="mt-7 grid grid-cols-1 gap-3 md:grid-cols-2",
                    ),
                    class_name="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:px-8",
                    id="faq",
                ),
                class_name="mx-auto w-full max-w-6xl bg-slate-50",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.div(
                        rx.el.h2(
                            "Listo para operar con mas control desde esta semana?",
                            class_name="text-2xl font-extrabold tracking-tight text-white sm:text-3xl",
                        ),
                        rx.el.p(
                            "Activa tu prueba gratis, crea tu empresa y empieza a vender con trazabilidad completa.",
                            class_name="mt-3 max-w-2xl text-sm leading-relaxed text-slate-200 sm:text-base",
                        ),
                        rx.el.div(
                            rx.el.a(
                                "Crear cuenta ahora",
                                href="/registro",
                                class_name=(
                                    "inline-flex items-center justify-center rounded-xl bg-emerald-500 "
                                    "px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-400 "
                                    "transition-colors duration-150"
                                ),
                            ),
                            rx.el.a(
                                "Ver login del sistema",
                                href="/",
                                class_name=(
                                    "inline-flex items-center justify-center rounded-xl border border-slate-500 "
                                    "px-5 py-3 text-sm font-semibold text-slate-100 hover:bg-slate-800 "
                                    "transition-colors duration-150"
                                ),
                            ),
                            class_name="mt-6 flex flex-col gap-3 sm:flex-row",
                        ),
                        class_name="max-w-3xl",
                    ),
                    class_name=(
                        "mx-auto w-full max-w-6xl rounded-3xl bg-slate-900 px-6 py-10 sm:px-10"
                    ),
                ),
                class_name="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6 lg:px-8",
            ),
            class_name="relative mx-auto w-full",
        ),
        rx.el.footer(
            rx.el.div(
                rx.el.p(
                    "TUWAYKIAPP | Sistema de Ventas SaaS para negocios multi-sucursal.",
                    class_name="text-sm text-slate-500",
                ),
                rx.el.div(
                    rx.el.a(
                        "Prueba gratis",
                        href="/registro",
                        class_name="text-sm text-slate-600 hover:text-slate-900",
                    ),
                    rx.el.a(
                        "Demo",
                        href=demo_link,
                        target="_blank",
                        rel="noopener noreferrer",
                        class_name="text-sm text-slate-600 hover:text-slate-900",
                    ),
                    rx.el.a(
                        "Ingresar",
                        href="/",
                        class_name="text-sm text-slate-600 hover:text-slate-900",
                    ),
                    class_name="flex items-center gap-4",
                ),
                class_name=(
                    "mx-auto flex w-full max-w-6xl flex-col items-start justify-between "
                    "gap-3 px-4 py-8 sm:flex-row sm:items-center sm:px-6 lg:px-8"
                ),
            ),
            class_name="border-t border-slate-200 bg-white",
        ),
        class_name="relative min-h-screen bg-gradient-to-b from-slate-100 via-white to-slate-100",
        style={"fontFamily": "'Sora', 'Public Sans', sans-serif"},
    )
