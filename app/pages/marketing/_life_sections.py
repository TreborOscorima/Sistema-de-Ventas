"""Secciones para la landing page de TUWAYKILIFE (Sistema para Clínicas)."""

import reflex as rx

from app.constants import WHATSAPP_NUMBER

from ._state import _site_href, _app_href, _life_href, _wa_link
from ._scripts import _track_event_script
from ._components import _nav_link, _faq_item, _footer_link

# ── Datos estáticos ───────────────────────────────────────────

_life_demo_link = _wa_link("Hola, me interesa conocer TUWAYKILIFE para mi clínica. Quiero coordinar una demo.")

LIFE_TRUST_BADGES = [
    ("calendar-clock", "Agenda y turnos en un solo lugar"),
    ("clipboard-list", "Historia clínica digital"),
    ("building-2", "Multi-especialidad y multi-sucursal"),
    ("smartphone", "Funciona en tablet o celular"),
]

LIFE_FEATURES = [
    (
        "calendar-clock",
        "Turnos y Agenda",
        "Agenda por profesional y sede, con estados de turno (pendiente, confirmado, atendido) y reprogramación en un clic.",
    ),
    (
        "clipboard-list",
        "Historia Clínica",
        "Registra notas clínicas por paciente y especialidad. Todo el historial de atenciones, ordenado y siempre a mano.",
    ),
    (
        "users",
        "Pacientes",
        "Ficha completa de cada paciente con datos de contacto, documento y su historial de turnos y atenciones.",
    ),
    (
        "credit-card",
        "Punto de Cobro",
        "Cobra consultas, servicios y productos con múltiples métodos de pago. Recibo en PDF al instante.",
    ),
    (
        "wallet",
        "Caja y Cuentas",
        "Caja por sede con arqueo y cierre, más cuentas corrientes para pacientes que pagan en partes.",
    ),
    (
        "package",
        "Inventario e Insumos",
        "Control de stock de insumos y productos con alertas de reposición y descuento automático al vender.",
    ),
]

LIFE_EXTRA_MODULES = [
    (
        "stethoscope",
        "Servicios por especialidad",
        "Catálogo de servicios con precios por especialidad: estética, odontología, masajes, quiropraxia y más.",
    ),
    (
        "user-check",
        "Profesionales",
        "Gestiona el equipo de profesionales, sus especialidades y su agenda propia dentro de la clínica.",
    ),
    (
        "shopping-cart",
        "Compras a proveedores",
        "Registra compras de insumos, controla proveedores y mantené el stock siempre actualizado.",
    ),
    (
        "tag",
        "Promociones",
        "Crea promociones y descuentos con vigencia. El cobro las aplica automáticamente al facturar.",
    ),
    (
        "bar-chart-2",
        "Reportes",
        "Ingresos, egresos y producción por profesional o servicio, exportables a Excel para tu contador.",
    ),
    (
        "shield-check",
        "Roles y permisos",
        "Administrador, recepción, profesional y contador. Cada usuario ve solo lo que le corresponde, por módulo.",
    ),
]

LIFE_STEPS = [
    (
        "01",
        "Carga tu clínica y tu equipo",
        "Registra tus sedes, profesionales y servicios por especialidad. Listo para agendar en minutos.",
    ),
    (
        "02",
        "Agenda los turnos",
        "Recepción asigna turnos por profesional y sede. El paciente queda vinculado a su historia clínica.",
    ),
    (
        "03",
        "Atiende y registra",
        "El profesional deja la nota clínica de la atención. Todo queda en el historial del paciente.",
    ),
    (
        "04",
        "Cobra y cierra caja",
        "Cobra la atención con recibo en PDF. Al final del turno, el arqueo de caja se hace solo.",
    ),
]

LIFE_FAQ_ITEMS = [
    (
        "¿Sirve para cualquier especialidad?",
        "Sí. TUWAYKILIFE está pensado para clínicas y consultorios de todas las ramas: estética, odontología, masajes, quiropraxia, nutrición, cirugía ambulatoria y más.",
    ),
    (
        "¿Puedo manejar varias sedes?",
        "Sí. Es multi-sucursal desde el inicio: cada sede tiene su agenda, su caja y su stock, con una visión central de toda la clínica.",
    ),
    (
        "¿Necesito instalar algo?",
        "No. Funciona 100% en la nube desde cualquier dispositivo con navegador: computadora, tablet o celular. Sin instalaciones ni hardware especial.",
    ),
    (
        "¿La historia clínica es segura?",
        "Los datos de cada clínica están aislados (arquitectura multi-tenant) y el acceso se controla por rol. Cada usuario ve únicamente lo que le corresponde.",
    ),
    (
        "¿Cuántos usuarios puedo crear?",
        "Sin límite de usuarios. Crea cuentas para recepción, profesionales, caja y administración, cada una con sus permisos.",
    ),
    (
        "¿Emite comprobantes?",
        "Sí. El punto de cobro genera recibos en PDF al instante y registra todo en caja, con historial de comprobantes reimprimibles.",
    ),
]


# ── Componentes ───────────────────────────────────────────────

def _life_header() -> rx.Component:
    return rx.el.header(
        rx.el.div(
            # Logo
            rx.el.a(
                rx.icon("heart-pulse", class_name="h-8 w-8 text-teal-600"),
                rx.el.span(
                    "TUWAYKILIFE",
                    class_name="text-2xl font-extrabold tracking-tight text-slate-900",
                ),
                href=_site_href("/life"),
                class_name="flex items-center gap-2.5",
            ),
            # Nav desktop
            rx.el.nav(
                _nav_link("Características", "#caracteristicas", "click_life_nav_features", "life_header_nav"),
                _nav_link("Cómo funciona", "#como-funciona", "click_life_nav_steps", "life_header_nav"),
                _nav_link("Módulos", "#modulos-extra", "click_life_nav_modulos", "life_header_nav"),
                _nav_link("FAQ", "#faq", "click_life_nav_faq", "life_header_nav"),
                rx.el.a(
                    rx.icon("layers", class_name="h-3.5 w-3.5"),
                    "Inicio",
                    href=_site_href("/"),
                    class_name="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-400 transition-colors hover:text-slate-700",
                ),
                class_name="hidden items-center gap-6 md:flex",
            ),
            # CTAs desktop
            rx.el.div(
                rx.el.a(
                    "Ingresar",
                    href=_life_href("/login"),
                    on_click=rx.call_script(_track_event_script("click_life_login", "life_header_nav")),
                    class_name="hidden items-center justify-center rounded-xl border-2 border-teal-600 bg-white px-4 py-2 text-sm font-semibold text-teal-700 transition-colors hover:bg-teal-50 md:inline-flex",
                ),
                rx.el.a(
                    "Comenzar gratis",
                    href=_app_href("/registro?producto=life"),
                    on_click=rx.call_script(_track_event_script("click_life_registro", "life_header_nav")),
                    class_name="hidden items-center justify-center rounded-xl bg-teal-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-teal-700 md:inline-flex",
                ),
                class_name="hidden items-center gap-3 md:flex",
            ),
            # Menú mobile
            rx.el.details(
                rx.el.summary(
                    rx.icon("menu", class_name="h-5 w-5 text-slate-700"),
                    class_name="inline-flex h-10 w-10 cursor-pointer items-center justify-center rounded-lg border border-slate-200 bg-white md:hidden",
                ),
                rx.el.div(
                    rx.el.div(
                        _nav_link("Características", "#caracteristicas", "click_life_nav_features_m", "life_mobile_menu"),
                        _nav_link("Cómo funciona", "#como-funciona", "click_life_nav_steps_m", "life_mobile_menu"),
                        _nav_link("Módulos", "#modulos-extra", "click_life_nav_modulos_m", "life_mobile_menu"),
                        _nav_link("FAQ", "#faq", "click_life_nav_faq_m", "life_mobile_menu"),
                        rx.el.a(
                            "← Inicio",
                            href=_site_href("/"),
                            class_name="text-sm font-semibold text-slate-400 transition-colors hover:text-slate-700",
                        ),
                        class_name="flex flex-col gap-4 py-1",
                    ),
                    rx.el.div(class_name="border-t border-slate-100"),
                    rx.el.div(
                        rx.el.a(
                            "Ingresar",
                            href=_life_href("/login"),
                            on_click=rx.call_script(_track_event_script("click_life_login_m", "life_mobile_menu")),
                            class_name="inline-flex w-full items-center justify-center rounded-xl border-2 border-teal-600 px-4 py-2 text-sm font-semibold text-teal-700 hover:bg-teal-50",
                        ),
                        rx.el.a(
                            "Comenzar gratis",
                            href=_app_href("/registro?producto=life"),
                            on_click=rx.call_script(_track_event_script("click_life_registro_m", "life_mobile_menu")),
                            class_name="inline-flex w-full items-center justify-center rounded-xl bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700",
                        ),
                        class_name="flex flex-col gap-2",
                    ),
                    class_name="absolute right-0 mt-3 w-64 rounded-xl border border-slate-200 bg-white p-4 shadow-lg md:hidden flex flex-col gap-3",
                ),
                class_name="relative md:hidden",
            ),
            class_name="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8",
        ),
        class_name="glass-nav fixed top-0 left-0 right-0 z-50 border-b border-slate-200/80",
    )


def _life_hero() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                # Badges
                rx.el.div(
                    rx.el.span(
                        rx.icon("heart-pulse", class_name="h-3.5 w-3.5 text-teal-600"),
                        "Sistema para clínicas y consultorios",
                        class_name="inline-flex items-center gap-1.5 rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-700 shadow-sm",
                    ),
                    rx.el.a(
                        rx.icon("layers", class_name="h-3.5 w-3.5"),
                        "Ver todos los productos",
                        href=_site_href("/"),
                        class_name="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-500 shadow-sm transition-colors hover:text-slate-700",
                    ),
                    class_name="flex flex-wrap items-center gap-2",
                ),
                # H1
                rx.el.h1(
                    "Del turno a la historia clínica — toda tu clínica en un solo sistema.",
                    class_name="mt-5 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl sm:leading-tight",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                # Descripción
                rx.el.p(
                    "TUWAYKILIFE reemplaza los cuadernos de turnos y las planillas sueltas. "
                    "Agenda, historia clínica, pacientes, cobro y caja integrados — "
                    "para clínicas de todas las especialidades, en una o varias sedes.",
                    class_name="mt-5 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg",
                ),
                # Trust pills
                rx.el.div(
                    *[
                        rx.el.div(
                            rx.icon(icon, class_name="h-4 w-4 text-teal-600 flex-shrink-0"),
                            rx.el.span(label, class_name="text-sm font-medium text-slate-700"),
                            class_name="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-sm",
                        )
                        for icon, label in LIFE_TRUST_BADGES
                    ],
                    class_name="mt-7 grid grid-cols-1 gap-2 sm:grid-cols-2",
                ),
                # CTAs
                rx.el.div(
                    rx.el.a(
                        "Comenzar gratis — 15 días",
                        href=_app_href("/registro?producto=life"),
                        on_click=rx.call_script(_track_event_script("click_life_registro", "life_hero_primary_cta")),
                        class_name="inline-flex items-center justify-center rounded-xl bg-teal-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-teal-700 shadow-sm",
                    ),
                    rx.el.a(
                        rx.icon("message-circle", class_name="h-4 w-4"),
                        "Agendar demo",
                        href=_life_demo_link,
                        target="_blank",
                        rel="noopener noreferrer",
                        on_click=rx.call_script(_track_event_script("click_life_demo", "life_hero_secondary_cta")),
                        class_name="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white/80 px-5 py-3 text-sm font-semibold text-slate-700 transition-colors hover:bg-white",
                    ),
                    class_name="mt-8 flex flex-col gap-3 sm:flex-row",
                ),
                rx.el.p(
                    "Sin tarjeta de crédito · Sin compromiso · Cancela cuando quieras",
                    class_name="mt-3 text-xs text-slate-400",
                ),
                class_name="reveal max-w-2xl",
            ),
            # Panel decorativo — vista de agenda del día
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.el.div(
                                rx.icon("calendar-clock", class_name="h-5 w-5 text-teal-600"),
                                rx.el.span("Agenda de hoy — Dra. Vargas", class_name="text-xs font-semibold text-slate-700"),
                                class_name="flex items-center gap-2",
                            ),
                            rx.el.div(
                                rx.el.div(
                                    rx.el.span("09:00", class_name="text-xs font-bold text-slate-500"),
                                    rx.el.span("Ana Flores — Limpieza facial", class_name="text-xs text-slate-600"),
                                    rx.el.span("Atendido", class_name="ml-auto rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700"),
                                    class_name="flex items-center gap-2",
                                ),
                                rx.el.div(
                                    rx.el.span("10:30", class_name="text-xs font-bold text-slate-500"),
                                    rx.el.span("Roberto Silva — Consulta", class_name="text-xs text-slate-600"),
                                    rx.el.span("Confirmado", class_name="ml-auto rounded-full bg-teal-100 px-2 py-0.5 text-[10px] font-semibold text-teal-700"),
                                    class_name="flex items-center gap-2",
                                ),
                                rx.el.div(
                                    rx.el.span("11:15", class_name="text-xs font-bold text-slate-500"),
                                    rx.el.span("Carmen Quispe — Masaje", class_name="text-xs text-slate-600"),
                                    rx.el.span("Pendiente", class_name="ml-auto rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700"),
                                    class_name="flex items-center gap-2",
                                ),
                                class_name="mt-3 space-y-2",
                            ),
                            class_name="rounded-xl border border-slate-200 bg-white p-4 shadow-sm",
                        ),
                        rx.el.div(
                            rx.el.div(
                                rx.icon("clipboard-list", class_name="h-4 w-4 text-teal-600"),
                                rx.el.span("Nota clínica guardada", class_name="text-xs font-semibold text-teal-700"),
                                class_name="flex items-center gap-2",
                            ),
                            rx.el.p(
                                "Ana Flores · hace 3 min",
                                class_name="mt-1 text-xs text-slate-400",
                            ),
                            class_name="mt-3 rounded-xl border border-teal-100 bg-teal-50 p-4",
                        ),
                        rx.el.div(
                            rx.el.div(
                                rx.icon("credit-card", class_name="h-4 w-4 text-slate-500"),
                                rx.el.span("Cobro registrado", class_name="text-xs font-semibold text-slate-700"),
                                class_name="flex items-center gap-2",
                            ),
                            rx.el.div(
                                rx.el.span("Recibo #0142", class_name="text-xs text-slate-500"),
                                rx.el.span("S/ 120.00", class_name="ml-auto text-sm font-bold text-slate-800"),
                                class_name="mt-2 flex items-center",
                            ),
                            class_name="mt-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm",
                        ),
                        class_name="space-y-3",
                    ),
                    class_name="w-full max-w-sm p-4",
                ),
                class_name="reveal hidden lg:flex lg:items-center lg:justify-center",
            ),
            class_name="grid grid-cols-1 items-start gap-10 lg:grid-cols-2 mx-auto w-full max-w-7xl px-4 pt-24 pb-16 sm:px-6 lg:px-8 lg:pt-28",
        ),
        class_name="hero-section w-full",
    )


def _life_how_it_works() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("zap", class_name="h-4 w-4 text-teal-600"),
                    rx.el.span("Cómo funciona", class_name="text-xs font-bold text-teal-600 uppercase tracking-widest"),
                    class_name="inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-4 py-1.5",
                ),
                rx.el.h2(
                    "Del turno al cierre de caja en cuatro pasos",
                    class_name="mt-6 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                class_name="flex flex-col items-center text-center",
            ),
            rx.el.div(
                *[
                    rx.el.div(
                        rx.el.div(
                            rx.el.span(
                                num,
                                class_name="text-sm font-extrabold text-teal-600",
                            ),
                            class_name="inline-flex h-10 w-10 items-center justify-center rounded-full border-2 border-teal-200 bg-teal-50",
                        ),
                        rx.el.div(
                            rx.el.h3(title, class_name="mt-4 text-base font-bold text-slate-900"),
                            rx.el.p(desc, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
                            class_name="mt-2",
                        ),
                        class_name="reveal rounded-2xl border border-slate-200 bg-white p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
                    )
                    for num, title, desc in LIFE_STEPS
                ],
                class_name="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8",
        ),
        id="como-funciona",
        class_name="py-20 sm:py-24 bg-slate-50",
    )


def _life_features() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("heart-pulse", class_name="h-4 w-4 text-teal-600"),
                    rx.el.span("Características", class_name="text-xs font-bold text-teal-600 uppercase tracking-widest"),
                    class_name="inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-4 py-1.5",
                ),
                rx.el.h2(
                    "Todo lo que tu clínica necesita",
                    class_name="mt-6 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                rx.el.p(
                    "Desde la agenda hasta el cierre de caja — cada módulo está pensado para el día a día real de una clínica.",
                    class_name="mt-4 max-w-2xl text-base leading-relaxed text-slate-600",
                ),
                class_name="flex flex-col items-center text-center",
            ),
            rx.el.div(
                *[
                    rx.el.article(
                        rx.el.div(
                            rx.icon(icon, class_name="h-5 w-5 text-teal-600"),
                            class_name="inline-flex items-center justify-center rounded-xl bg-teal-50 p-2.5",
                        ),
                        rx.el.h3(title, class_name="mt-4 text-base font-bold text-slate-900"),
                        rx.el.p(desc, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
                        class_name="reveal rounded-2xl border border-slate-200 bg-white p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
                    )
                    for icon, title, desc in LIFE_FEATURES
                ],
                class_name="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8",
        ),
        id="caracteristicas",
        class_name="py-20 sm:py-24 bg-white",
    )


def _life_extra_modules() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("grid-3x3", class_name="h-4 w-4 text-teal-600"),
                    rx.el.span("Módulos adicionales", class_name="text-xs font-bold text-teal-600 uppercase tracking-widest"),
                    class_name="inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-4 py-1.5",
                ),
                rx.el.h2(
                    "Más herramientas para tu operación",
                    class_name="mt-6 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                class_name="flex flex-col items-center text-center",
            ),
            rx.el.div(
                *[
                    rx.el.div(
                        rx.el.div(
                            rx.icon(icon, class_name="h-5 w-5 text-teal-600 flex-shrink-0"),
                            class_name="inline-flex items-center justify-center rounded-xl bg-teal-50 p-2.5 flex-shrink-0",
                        ),
                        rx.el.div(
                            rx.el.h3(title, class_name="text-sm font-bold text-slate-900"),
                            rx.el.p(desc, class_name="mt-1 text-xs leading-relaxed text-slate-600"),
                        ),
                        class_name="reveal flex items-start gap-4 rounded-2xl border border-slate-200 bg-white p-5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
                    )
                    for icon, title, desc in LIFE_EXTRA_MODULES
                ],
                class_name="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8",
        ),
        id="modulos-extra",
        class_name="py-20 sm:py-24 bg-slate-50",
    )


def _life_faq() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("help-circle", class_name="h-4 w-4 text-teal-600"),
                    rx.el.span("Preguntas frecuentes", class_name="text-xs font-bold text-teal-600 uppercase tracking-widest"),
                    class_name="inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-4 py-1.5",
                ),
                rx.el.h2(
                    "Lo que nos preguntan antes de empezar",
                    class_name="mt-6 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                class_name="flex flex-col items-center text-center",
            ),
            rx.el.div(
                *[_faq_item(q, a) for q, a in LIFE_FAQ_ITEMS],
                class_name="mt-12 mx-auto max-w-3xl space-y-3",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8",
        ),
        id="faq",
        class_name="py-20 sm:py-24 bg-white",
    )


def _life_cta() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.h2(
                    "Tu clínica merece más que cuadernos de turnos y planillas sueltas",
                    class_name="text-2xl font-extrabold tracking-tight text-white sm:text-3xl text-center",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                rx.el.p(
                    "Activa tu prueba de 15 días sin tarjeta. Agenda, historia clínica, cobro y caja desde el primer día.",
                    class_name="mt-4 max-w-2xl text-sm leading-relaxed text-slate-300 sm:text-base text-center",
                ),
                rx.el.div(
                    rx.el.a(
                        "Crear cuenta ahora",
                        href=_app_href("/registro?producto=life"),
                        on_click=rx.call_script(_track_event_script("click_life_registro", "life_bottom_cta_primary")),
                        class_name="inline-flex items-center justify-center rounded-xl bg-teal-500 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-teal-400",
                    ),
                    rx.el.a(
                        "Agendar demo",
                        href=_life_demo_link,
                        target="_blank",
                        rel="noopener noreferrer",
                        on_click=rx.call_script(_track_event_script("click_life_demo", "life_bottom_cta_secondary")),
                        class_name="inline-flex items-center justify-center rounded-xl border border-slate-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-slate-800",
                    ),
                    class_name="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center",
                ),
                class_name="reveal mx-auto w-full max-w-7xl overflow-hidden rounded-3xl bg-slate-900 border border-slate-800 px-8 py-14 sm:px-12 sm:py-16 shadow-2xl flex flex-col items-center",
            ),
        ),
        class_name="mx-auto w-full max-w-7xl px-4 pb-16 sm:px-6 lg:px-8",
    )


def _life_footer() -> rx.Component:
    return rx.el.footer(
        rx.el.div(
            rx.el.div(
                # Columna marca
                rx.el.div(
                    rx.el.a(
                        rx.icon("heart-pulse", class_name="h-7 w-7 text-teal-600"),
                        rx.el.span("TUWAYKILIFE", class_name="text-lg font-extrabold tracking-tight text-slate-900"),
                        href=_site_href("/life"),
                        class_name="inline-flex items-center gap-2.5",
                    ),
                    rx.el.p(
                        "Sistema de gestión para clínicas y consultorios. Agenda, historia clínica, cobro y caja integrados.",
                        class_name="mt-3 max-w-xs text-sm text-slate-600",
                    ),
                    rx.el.a(
                        "WhatsApp +5491168376517",
                        href=f"https://wa.me/{WHATSAPP_NUMBER}",
                        target="_blank",
                        rel="noopener noreferrer",
                        on_click=rx.call_script(_track_event_script("click_whatsapp_cta", "life_footer_contact")),
                        class_name="mt-3 inline-flex text-sm font-semibold text-emerald-700 hover:text-emerald-800",
                    ),
                ),
                # Columna producto
                rx.el.div(
                    rx.el.h4("Producto", class_name="text-sm font-bold text-slate-900"),
                    _footer_link("Características", "#caracteristicas", "click_life_footer_features", "life_footer_producto"),
                    _footer_link("Cómo funciona", "#como-funciona", "click_life_footer_steps", "life_footer_producto"),
                    _footer_link("Módulos", "#modulos-extra", "click_life_footer_modulos", "life_footer_producto"),
                    _footer_link("FAQ", "#faq", "click_life_footer_faq", "life_footer_producto"),
                    class_name="flex flex-col gap-2",
                ),
                # Columna empresa
                rx.el.div(
                    rx.el.h4("Empresa", class_name="text-sm font-bold text-slate-900"),
                    _footer_link("Agendar demo", _life_demo_link, "click_life_footer_demo", "life_footer_empresa", external=True),
                    _footer_link("Hablar con ventas", _life_demo_link, "click_life_footer_sales", "life_footer_empresa", external=True),
                    _footer_link("← Ver todos los productos", _site_href("/"), "click_life_footer_home", "life_footer_empresa"),
                    class_name="flex flex-col gap-2",
                ),
                # Columna accesos
                rx.el.div(
                    rx.el.h4("Accesos", class_name="text-sm font-bold text-slate-900"),
                    _footer_link("Ingresar a TUWAYKILIFE", _life_href("/login"), "click_life_footer_login", "life_footer_accesos"),
                    _footer_link("Crear cuenta", _app_href("/registro?producto=life"), "click_life_footer_signup", "life_footer_accesos"),
                    _footer_link("WhatsApp directo", f"https://wa.me/{WHATSAPP_NUMBER}", "click_life_footer_whatsapp", "life_footer_accesos", external=True),
                    class_name="flex flex-col gap-2",
                ),
                # Columna legal
                rx.el.div(
                    rx.el.h4("Legal", class_name="text-sm font-bold text-slate-900"),
                    _footer_link("Términos y condiciones", _site_href("/terminos"), "click_life_footer_terms", "life_footer_legal"),
                    _footer_link("Política de privacidad", _site_href("/privacidad"), "click_life_footer_privacy", "life_footer_legal"),
                    _footer_link("Política de cookies", _site_href("/cookies"), "click_life_footer_cookies", "life_footer_legal"),
                    class_name="flex flex-col gap-2",
                ),
                class_name="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-5",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.p("TUWAYKIAPP © 2026. Todos los derechos reservados.", class_name="text-sm leading-relaxed text-slate-500"),
                    rx.el.p("Hecho con foco en la operación real de clínicas.", class_name="text-sm leading-relaxed text-slate-500"),
                    class_name="space-y-1",
                ),
                rx.el.div(
                    rx.el.p("Creado por", class_name="text-xs text-slate-400 uppercase tracking-wider"),
                    rx.el.a(
                        "Trebor Oscorima",
                        href="https://www.facebook.com/trebor.oscorima/?locale=es_LA",
                        target="_blank",
                        rel="noopener noreferrer",
                        class_name="text-sm font-semibold text-slate-700 hover:text-teal-600 transition-colors",
                    ),
                    class_name="mt-1 flex flex-col gap-0.5 items-start sm:mt-0 sm:items-end sm:text-right",
                ),
                class_name="mt-8 flex flex-col items-start justify-between gap-4 border-t border-slate-200 pt-4 sm:flex-row sm:items-center",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8",
        ),
        class_name="border-t border-slate-200 bg-white",
    )


def _life_floating_whatsapp() -> rx.Component:
    return rx.el.a(
        rx.icon("message-circle", class_name="h-5 w-5"),
        rx.el.span("WhatsApp", class_name="hidden text-sm font-semibold sm:inline"),
        href=_life_demo_link,
        target="_blank",
        rel="noopener noreferrer",
        on_click=rx.call_script(_track_event_script("click_whatsapp_cta", "life_floating_button")),
        class_name="fixed bottom-5 right-5 z-[60] inline-flex items-center gap-2 rounded-full bg-emerald-600 px-4 py-3 text-white shadow-lg transition-all hover:-translate-y-0.5 hover:bg-emerald-700",
        aria_label="Contactar por WhatsApp",
    )
