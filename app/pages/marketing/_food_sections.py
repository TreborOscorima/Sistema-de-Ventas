"""Secciones para la landing page de TUWAYKIFOOD."""

import reflex as rx

from app.constants import WHATSAPP_NUMBER

from ._state import _site_href, _app_href, _food_href, _wa_link
from ._scripts import _track_event_script
from ._components import _nav_link, _faq_item, _footer_link

# ── Datos estáticos ───────────────────────────────────────────

_food_demo_link = _wa_link("Hola, me interesa conocer TUWAYKIFOOD para mi restaurante. Quiero coordinar una demo.")

FOOD_TRUST_BADGES = [
    ("file-x", "Sin comandas en papel"),
    ("wifi", "Cocina conectada en tiempo real"),
    ("wallet", "Caja integrada por turno"),
    ("smartphone", "Funciona en tablet o celular"),
]

FOOD_FEATURES = [
    (
        "utensils",
        "Carta Digital",
        "Administra categorías, platos y precios desde el panel. Activa o desactiva platos en tiempo real sin recargar la página.",
    ),
    (
        "qr-code",
        "QR para clientes",
        "Cada mesa tiene su código QR. Los clientes escanean y ven la carta actualizada desde su celular — sin app ni descarga.",
    ),
    (
        "layout-grid",
        "Gestión de Mesas",
        "Mapa visual de tu salón con sectores configurables. Cada mesa muestra su estado: libre, ocupada o cuenta pedida.",
    ),
    (
        "clipboard-list",
        "Pedidos por Tablet",
        "El mozo toma el pedido en tablet o celular, mesa por mesa. El pedido llega directo a cocina sin intermediarios.",
    ),
    (
        "printer",
        "Comanda Automática",
        "Al confirmar el pedido, la comanda se imprime en cocina automáticamente. Sin papeles escritos a mano, sin confusiones.",
    ),
    (
        "wallet",
        "Caja Integrada",
        "Los pedidos cerrados se registran en caja con diferenciador por método de pago. Arqueo automático al cierre del turno.",
    ),
]

FOOD_EXTRA_MODULES = [
    (
        "store",
        "Mostrador / Para llevar",
        "Flujo independiente para pedidos de mostrador y para llevar, con cobro directo sin asignar mesa.",
    ),
    (
        "monitor",
        "KDS — Pantalla de cocina",
        "Vista en pantalla grande para el equipo de cocina. Los tickets aparecen en tiempo real y se marcan al completarse.",
    ),
    (
        "package",
        "Inventario de insumos",
        "Control de stock de ingredientes con Kardex auditable, alertas de reposición y valorización por costo.",
    ),
    (
        "credit-card",
        "Cuentas corrientes (fiado)",
        "Registra deudas de clientes habituales. El cajero las cobra parcial o totalmente desde Caja.",
    ),
    (
        "percent",
        "Descuentos y cupones",
        "Crea cupones por código con porcentaje o monto fijo. El cajero los aplica al cobrar con validación automática.",
    ),
    (
        "users",
        "Roles por función",
        "Admin, Mozo, Caja y Cocina. Cada empleado accede solo a lo que necesita, con su PIN desde cualquier dispositivo.",
    ),
]

FOOD_STEPS = [
    (
        "01",
        "Configura tu carta",
        "Crea categorías, agrega platos con precios y activa la carta QR vinculada a cada mesa.",
    ),
    (
        "02",
        "El mozo toma el pedido",
        "Desde tablet o celular, mesa por mesa. El pedido se confirma y llega directo a cocina.",
    ),
    (
        "03",
        "Cocina recibe la comanda",
        "Impresión automática o KDS en pantalla. Sin papeles escritos a mano, sin llamadas a la barra.",
    ),
    (
        "04",
        "Cierra caja al final del turno",
        "Los pedidos cobrados se registran automáticamente. El arqueo muestra diferencias al instante.",
    ),
]

FOOD_FAQ_ITEMS = [
    (
        "¿Necesito tablets para los mozos?",
        "Funciona en cualquier dispositivo con navegador: tablet, celular o laptop. No requiere hardware especial ni instalación.",
    ),
    (
        "¿Funciona sin internet?",
        "Requiere conexión para sincronizar pedidos entre dispositivos. Con señal baja puede verse afectado el envío a cocina.",
    ),
    (
        "¿Puedo gestionar varias zonas (salón, terraza)?",
        "Sí. Puedes crear sectores y asignar mesas a cada uno. El mapa de salón se adapta a la distribución de tu local.",
    ),
    (
        "¿Incluye KDS para cocina?",
        "Sí. La pantalla de cocina muestra los tickets en tiempo real y permite marcarlos como completados desde la misma vista.",
    ),
    (
        "¿Cuántos usuarios o mozos puedo crear?",
        "Sin límite de usuarios. Cada uno ingresa con su PIN y tiene acceso únicamente a su módulo asignado.",
    ),
    (
        "¿Qué pasa si se agota un plato?",
        "El Admin puede desactivar el plato desde la carta en tiempo real. Deja de aparecer para los mozos y en la carta QR de los clientes.",
    ),
]


# ── Componentes ───────────────────────────────────────────────

def _food_header() -> rx.Component:
    return rx.el.header(
        rx.el.div(
            # Logo
            rx.el.a(
                rx.icon("utensils", class_name="h-8 w-8 text-orange-500"),
                rx.el.span(
                    "TUWAYKIFOOD",
                    class_name="text-2xl font-extrabold tracking-tight text-slate-900",
                ),
                href=_site_href("/food"),
                class_name="flex items-center gap-2.5",
            ),
            # Nav desktop
            rx.el.nav(
                _nav_link("Características", "#caracteristicas", "click_food_nav_features", "food_header_nav"),
                _nav_link("Cómo funciona", "#como-funciona", "click_food_nav_steps", "food_header_nav"),
                _nav_link("Módulos", "#modulos-extra", "click_food_nav_modulos", "food_header_nav"),
                _nav_link("FAQ", "#faq", "click_food_nav_faq", "food_header_nav"),
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
                    href=_food_href("/login"),
                    on_click=rx.call_script(_track_event_script("click_food_login", "food_header_nav")),
                    class_name="hidden items-center justify-center rounded-xl border-2 border-orange-500 bg-white px-4 py-2 text-sm font-semibold text-orange-600 transition-colors hover:bg-orange-50 md:inline-flex",
                ),
                rx.el.a(
                    "Comenzar gratis",
                    href=_app_href("/registro?producto=food"),
                    on_click=rx.call_script(_track_event_script("click_food_registro", "food_header_nav")),
                    class_name="hidden items-center justify-center rounded-xl bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-orange-600 md:inline-flex",
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
                        _nav_link("Características", "#caracteristicas", "click_food_nav_features_m", "food_mobile_menu"),
                        _nav_link("Cómo funciona", "#como-funciona", "click_food_nav_steps_m", "food_mobile_menu"),
                        _nav_link("Módulos", "#modulos-extra", "click_food_nav_modulos_m", "food_mobile_menu"),
                        _nav_link("FAQ", "#faq", "click_food_nav_faq_m", "food_mobile_menu"),
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
                            href=_food_href("/login"),
                            on_click=rx.call_script(_track_event_script("click_food_login_m", "food_mobile_menu")),
                            class_name="inline-flex w-full items-center justify-center rounded-xl border-2 border-orange-500 px-4 py-2 text-sm font-semibold text-orange-600 hover:bg-orange-50",
                        ),
                        rx.el.a(
                            "Comenzar gratis",
                            href=_app_href("/registro?producto=food"),
                            on_click=rx.call_script(_track_event_script("click_food_registro_m", "food_mobile_menu")),
                            class_name="inline-flex w-full items-center justify-center rounded-xl bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600",
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


def _food_hero() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                # Badges
                rx.el.div(
                    rx.el.span(
                        rx.icon("utensils", class_name="h-3.5 w-3.5 text-orange-600"),
                        "Sistema para restaurantes y restobares",
                        class_name="inline-flex items-center gap-1.5 rounded-full border border-orange-200 bg-orange-50 px-3 py-1 text-xs font-semibold text-orange-700 shadow-sm",
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
                    "De la comanda a la caja — todo conectado en tiempo real.",
                    class_name="mt-5 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl sm:leading-tight",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                # Descripción
                rx.el.p(
                    "TUWAYKIFOOD reemplaza las comandas en papel, las pizarras y los sistemas desconectados. "
                    "Carta digital, mesas, pedidos por tablet y cocina integrados — "
                    "con la caja cerrando sola al final del turno.",
                    class_name="mt-5 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg",
                ),
                # Trust pills
                rx.el.div(
                    *[
                        rx.el.div(
                            rx.icon(icon, class_name="h-4 w-4 text-orange-600 flex-shrink-0"),
                            rx.el.span(label, class_name="text-sm font-medium text-slate-700"),
                            class_name="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-sm",
                        )
                        for icon, label in FOOD_TRUST_BADGES
                    ],
                    class_name="mt-7 grid grid-cols-1 gap-2 sm:grid-cols-2",
                ),
                # CTAs
                rx.el.div(
                    rx.el.a(
                        "Comenzar gratis — 15 días",
                        href=_app_href("/registro?producto=food"),
                        on_click=rx.call_script(_track_event_script("click_food_registro", "food_hero_primary_cta")),
                        class_name="inline-flex items-center justify-center rounded-xl bg-orange-500 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-orange-600 shadow-sm",
                    ),
                    rx.el.a(
                        rx.icon("message-circle", class_name="h-4 w-4"),
                        "Agendar demo",
                        href=_food_demo_link,
                        target="_blank",
                        rel="noopener noreferrer",
                        on_click=rx.call_script(_track_event_script("click_food_demo", "food_hero_secondary_cta")),
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
            # Panel decorativo
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.el.div(
                                rx.icon("utensils", class_name="h-5 w-5 text-orange-500"),
                                rx.el.span("Mesa 4 — Mozo: Carlos", class_name="text-xs font-semibold text-slate-700"),
                                class_name="flex items-center gap-2",
                            ),
                            rx.el.div(
                                rx.el.p("2× Milanesa con papas", class_name="text-xs text-slate-600"),
                                rx.el.p("1× Limonada", class_name="text-xs text-slate-600"),
                                rx.el.p("1× Agua mineral", class_name="text-xs text-slate-600"),
                                class_name="mt-2 space-y-1",
                            ),
                            rx.el.div(
                                rx.el.span(
                                    "Enviado a cocina",
                                    class_name="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700",
                                ),
                                class_name="mt-3",
                            ),
                            class_name="rounded-xl border border-slate-200 bg-white p-4 shadow-sm",
                        ),
                        rx.el.div(
                            rx.el.div(
                                rx.icon("printer", class_name="h-4 w-4 text-orange-500"),
                                rx.el.span("Comanda impresa en cocina", class_name="text-xs font-semibold text-orange-700"),
                                class_name="flex items-center gap-2",
                            ),
                            rx.el.p(
                                "KDS · hace 12 seg",
                                class_name="mt-1 text-xs text-slate-400",
                            ),
                            class_name="mt-3 rounded-xl border border-orange-100 bg-orange-50 p-4",
                        ),
                        rx.el.div(
                            rx.el.div(
                                rx.icon("layout-grid", class_name="h-4 w-4 text-slate-500"),
                                rx.el.span("Mapa del salón", class_name="text-xs font-semibold text-slate-700"),
                                class_name="flex items-center gap-2",
                            ),
                            rx.el.div(
                                *[
                                    rx.el.div(
                                        rx.el.span(f"M{i}", class_name="text-xs font-bold text-slate-700"),
                                        class_name=f"flex h-9 w-9 items-center justify-center rounded-lg border-2 text-xs font-bold {'border-orange-400 bg-orange-50' if i in (2, 4, 7) else 'border-slate-200 bg-white'}",
                                    )
                                    for i in range(1, 10)
                                ],
                                class_name="mt-2 grid grid-cols-4 gap-1.5",
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


def _food_how_it_works() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("zap", class_name="h-4 w-4 text-orange-600"),
                    rx.el.span("Cómo funciona", class_name="text-xs font-bold text-orange-600 uppercase tracking-widest"),
                    class_name="inline-flex items-center gap-2 rounded-full border border-orange-200 bg-orange-50 px-4 py-1.5",
                ),
                rx.el.h2(
                    "Del pedido al arqueo en cuatro pasos",
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
                                class_name="text-sm font-extrabold text-orange-600",
                            ),
                            class_name="inline-flex h-10 w-10 items-center justify-center rounded-full border-2 border-orange-200 bg-orange-50",
                        ),
                        rx.el.div(
                            rx.el.h3(title, class_name="mt-4 text-base font-bold text-slate-900"),
                            rx.el.p(desc, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
                            class_name="mt-2",
                        ),
                        class_name="reveal rounded-2xl border border-slate-200 bg-white p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
                    )
                    for num, title, desc in FOOD_STEPS
                ],
                class_name="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8",
        ),
        id="como-funciona",
        class_name="py-20 sm:py-24 bg-slate-50",
    )


def _food_features() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("utensils", class_name="h-4 w-4 text-orange-600"),
                    rx.el.span("Características", class_name="text-xs font-bold text-orange-600 uppercase tracking-widest"),
                    class_name="inline-flex items-center gap-2 rounded-full border border-orange-200 bg-orange-50 px-4 py-1.5",
                ),
                rx.el.h2(
                    "Todo lo que necesita tu restobar",
                    class_name="mt-6 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                rx.el.p(
                    "Desde la carta digital hasta el cierre de caja — cada módulo está pensado para el ritmo real de un restaurante.",
                    class_name="mt-4 max-w-2xl text-base leading-relaxed text-slate-600",
                ),
                class_name="flex flex-col items-center text-center",
            ),
            rx.el.div(
                *[
                    rx.el.article(
                        rx.el.div(
                            rx.icon(icon, class_name="h-5 w-5 text-orange-600"),
                            class_name="inline-flex items-center justify-center rounded-xl bg-orange-50 p-2.5",
                        ),
                        rx.el.h3(title, class_name="mt-4 text-base font-bold text-slate-900"),
                        rx.el.p(desc, class_name="mt-2 text-sm leading-relaxed text-slate-600"),
                        class_name="reveal rounded-2xl border border-slate-200 bg-white p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
                    )
                    for icon, title, desc in FOOD_FEATURES
                ],
                class_name="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8",
        ),
        id="caracteristicas",
        class_name="py-20 sm:py-24 bg-white",
    )


def _food_extra_modules() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("grid-3x3", class_name="h-4 w-4 text-orange-600"),
                    rx.el.span("Módulos adicionales", class_name="text-xs font-bold text-orange-600 uppercase tracking-widest"),
                    class_name="inline-flex items-center gap-2 rounded-full border border-orange-200 bg-orange-50 px-4 py-1.5",
                ),
                rx.el.h2(
                    "Más herramientas para operar mejor",
                    class_name="mt-6 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                class_name="flex flex-col items-center text-center",
            ),
            rx.el.div(
                *[
                    rx.el.div(
                        rx.el.div(
                            rx.icon(icon, class_name="h-5 w-5 text-orange-600 flex-shrink-0"),
                            class_name="inline-flex items-center justify-center rounded-xl bg-orange-50 p-2.5 flex-shrink-0",
                        ),
                        rx.el.div(
                            rx.el.h3(title, class_name="text-sm font-bold text-slate-900"),
                            rx.el.p(desc, class_name="mt-1 text-xs leading-relaxed text-slate-600"),
                        ),
                        class_name="reveal flex items-start gap-4 rounded-2xl border border-slate-200 bg-white p-5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
                    )
                    for icon, title, desc in FOOD_EXTRA_MODULES
                ],
                class_name="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8",
        ),
        id="modulos-extra",
        class_name="py-20 sm:py-24 bg-slate-50",
    )


def _food_faq() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("help-circle", class_name="h-4 w-4 text-orange-600"),
                    rx.el.span("Preguntas frecuentes", class_name="text-xs font-bold text-orange-600 uppercase tracking-widest"),
                    class_name="inline-flex items-center gap-2 rounded-full border border-orange-200 bg-orange-50 px-4 py-1.5",
                ),
                rx.el.h2(
                    "Lo que nos preguntan antes de empezar",
                    class_name="mt-6 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                class_name="flex flex-col items-center text-center",
            ),
            rx.el.div(
                *[_faq_item(q, a) for q, a in FOOD_FAQ_ITEMS],
                class_name="mt-12 mx-auto max-w-3xl space-y-3",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8",
        ),
        id="faq",
        class_name="py-20 sm:py-24 bg-white",
    )


def _food_cta() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.h2(
                    "Tu restaurante merece más que comandas en papel y sistemas desconectados",
                    class_name="text-2xl font-extrabold tracking-tight text-white sm:text-3xl text-center",
                    style={"fontFamily": "'Space Grotesk', sans-serif"},
                ),
                rx.el.p(
                    "Activa tu prueba de 15 días sin tarjeta. Carta digital, mesas, cocina y caja desde el primer día.",
                    class_name="mt-4 max-w-2xl text-sm leading-relaxed text-slate-300 sm:text-base text-center",
                ),
                rx.el.div(
                    rx.el.a(
                        "Crear cuenta ahora",
                        href=_app_href("/registro?producto=food"),
                        on_click=rx.call_script(_track_event_script("click_food_registro", "food_bottom_cta_primary")),
                        class_name="inline-flex items-center justify-center rounded-xl bg-orange-500 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-orange-400",
                    ),
                    rx.el.a(
                        "Agendar demo",
                        href=_food_demo_link,
                        target="_blank",
                        rel="noopener noreferrer",
                        on_click=rx.call_script(_track_event_script("click_food_demo", "food_bottom_cta_secondary")),
                        class_name="inline-flex items-center justify-center rounded-xl border border-slate-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-slate-800",
                    ),
                    class_name="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center",
                ),
                class_name="reveal mx-auto w-full max-w-7xl overflow-hidden rounded-3xl bg-slate-900 border border-slate-800 px-8 py-14 sm:px-12 sm:py-16 shadow-2xl flex flex-col items-center",
            ),
        ),
        class_name="mx-auto w-full max-w-7xl px-4 pb-16 sm:px-6 lg:px-8",
    )


def _food_footer() -> rx.Component:
    return rx.el.footer(
        rx.el.div(
            rx.el.div(
                # Columna marca
                rx.el.div(
                    rx.el.a(
                        rx.icon("utensils", class_name="h-7 w-7 text-orange-500"),
                        rx.el.span("TUWAYKIFOOD", class_name="text-lg font-extrabold tracking-tight text-slate-900"),
                        href=_site_href("/food"),
                        class_name="inline-flex items-center gap-2.5",
                    ),
                    rx.el.p(
                        "Sistema de gestión para restaurantes y restobares. Carta digital, mesas, cocina y caja integrados.",
                        class_name="mt-3 max-w-xs text-sm text-slate-600",
                    ),
                    rx.el.a(
                        "WhatsApp +5491168376517",
                        href=f"https://wa.me/{WHATSAPP_NUMBER}",
                        target="_blank",
                        rel="noopener noreferrer",
                        on_click=rx.call_script(_track_event_script("click_whatsapp_cta", "food_footer_contact")),
                        class_name="mt-3 inline-flex text-sm font-semibold text-emerald-700 hover:text-emerald-800",
                    ),
                ),
                # Columna producto
                rx.el.div(
                    rx.el.h4("Producto", class_name="text-sm font-bold text-slate-900"),
                    _footer_link("Características", "#caracteristicas", "click_food_footer_features", "food_footer_producto"),
                    _footer_link("Cómo funciona", "#como-funciona", "click_food_footer_steps", "food_footer_producto"),
                    _footer_link("Módulos", "#modulos-extra", "click_food_footer_modulos", "food_footer_producto"),
                    _footer_link("FAQ", "#faq", "click_food_footer_faq", "food_footer_producto"),
                    class_name="flex flex-col gap-2",
                ),
                # Columna empresa
                rx.el.div(
                    rx.el.h4("Empresa", class_name="text-sm font-bold text-slate-900"),
                    _footer_link("Agendar demo", _food_demo_link, "click_food_footer_demo", "food_footer_empresa", external=True),
                    _footer_link("Hablar con ventas", _food_demo_link, "click_food_footer_sales", "food_footer_empresa", external=True),
                    _footer_link("← Ver todos los productos", _site_href("/"), "click_food_footer_home", "food_footer_empresa"),
                    class_name="flex flex-col gap-2",
                ),
                # Columna accesos
                rx.el.div(
                    rx.el.h4("Accesos", class_name="text-sm font-bold text-slate-900"),
                    _footer_link("Ingresar a TUWAYKIFOOD", _food_href("/login"), "click_food_footer_login", "food_footer_accesos"),
                    _footer_link("Crear cuenta", _app_href("/registro?producto=food"), "click_food_footer_signup", "food_footer_accesos"),
                    _footer_link("WhatsApp directo", f"https://wa.me/{WHATSAPP_NUMBER}", "click_food_footer_whatsapp", "food_footer_accesos", external=True),
                    class_name="flex flex-col gap-2",
                ),
                # Columna legal
                rx.el.div(
                    rx.el.h4("Legal", class_name="text-sm font-bold text-slate-900"),
                    _footer_link("Términos y condiciones", _site_href("/terminos"), "click_food_footer_terms", "food_footer_legal"),
                    _footer_link("Política de privacidad", _site_href("/privacidad"), "click_food_footer_privacy", "food_footer_legal"),
                    _footer_link("Política de cookies", _site_href("/cookies"), "click_food_footer_cookies", "food_footer_legal"),
                    class_name="flex flex-col gap-2",
                ),
                class_name="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-5",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.p("TUWAYKIAPP © 2026. Todos los derechos reservados.", class_name="text-sm leading-relaxed text-slate-500"),
                    rx.el.p("Hecho con foco en la operación real de restaurantes.", class_name="text-sm leading-relaxed text-slate-500"),
                    class_name="space-y-1",
                ),
                rx.el.div(
                    rx.el.p("Creado por", class_name="text-xs text-slate-400 uppercase tracking-wider"),
                    rx.el.a(
                        "Trebor Oscorima",
                        href="https://www.facebook.com/trebor.oscorima/?locale=es_LA",
                        target="_blank",
                        rel="noopener noreferrer",
                        class_name="text-sm font-semibold text-slate-700 hover:text-orange-600 transition-colors",
                    ),
                    class_name="mt-1 flex flex-col gap-0.5 items-start sm:mt-0 sm:items-end sm:text-right",
                ),
                class_name="mt-8 flex flex-col items-start justify-between gap-4 border-t border-slate-200 pt-4 sm:flex-row sm:items-center",
            ),
            class_name="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8",
        ),
        class_name="border-t border-slate-200 bg-white",
    )


def _food_floating_whatsapp() -> rx.Component:
    return rx.el.a(
        rx.icon("message-circle", class_name="h-5 w-5"),
        rx.el.span("WhatsApp", class_name="hidden text-sm font-semibold sm:inline"),
        href=_food_demo_link,
        target="_blank",
        rel="noopener noreferrer",
        on_click=rx.call_script(_track_event_script("click_whatsapp_cta", "food_floating_button")),
        class_name="fixed bottom-5 right-5 z-[60] inline-flex items-center gap-2 rounded-full bg-emerald-600 px-4 py-3 text-white shadow-lg transition-all hover:-translate-y-0.5 hover:bg-emerald-700",
        aria_label="Contactar por WhatsApp",
    )
