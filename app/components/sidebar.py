import reflex as rx
from app.state import State
from app.components.ui import RADIUS, SHADOWS, TRANSITIONS

CONFIG_SUBSECTIONS = [
    {"key": "empresa", "label": "Datos de Empresa", "icon": "building"},
    {"key": "sucursales", "label": "Sucursales", "icon": "map-pin"},
    {"key": "usuarios", "label": "Gestion de Usuarios", "icon": "users"},
    {"key": "monedas", "label": "Selector de Monedas", "icon": "coins"},
    {"key": "unidades", "label": "Unidades de Medida", "icon": "ruler"},
    {"key": "pagos", "label": "Metodos de Pago", "icon": "credit-card"},
    {"key": "suscripcion", "label": "Suscripcion", "icon": "sparkles"},
]

SERVICES_SUBSECTIONS = [
    {"key": "campo", "label": "Alquiler de Campo", "icon": "trophy"},
    {"key": "precios_campo", "label": "Precios de Campo", "icon": "tags"},
    # {"key": "piscina", "label": "Alquiler de Piscina", "icon": "waves"},
]

CASH_SUBSECTIONS = [
    {"key": "resumen", "label": "Resumen de Caja", "icon": "layout-dashboard"},
    {"key": "movimientos", "label": "Movimientos de Caja Chica", "icon": "arrow-left-right"},
]


def nav_item(text: str, icon: str, page: str, route: str) -> rx.Component:
    """Item de navegación con indicador lateral activo."""
    has_overdue = (
        (page == "Cuentas Corrientes")
        & (State.overdue_alerts_count > 0)
    )
    show_badge = has_overdue & State.sidebar_open
    current_path = State.router.page.path

    # Estilos para item activo vs inactivo
    active_class = f"relative flex items-center gap-3 min-w-0 {RADIUS['lg']} bg-indigo-600 text-white px-3 py-2 font-semibold {SHADOWS['sm']} {TRANSITIONS['fast']}"
    inactive_class = f"relative flex items-center gap-3 min-w-0 {RADIUS['lg']} px-3 py-2 text-slate-600 hover:bg-white/60 hover:text-slate-900 font-medium {TRANSITIONS['fast']}"

    target_route = rx.cond(
        has_overdue,
        "/cuentas?filter=overdue",
        route,
    )
    is_active = rx.cond(
        route == "/ingreso",
        (current_path == "/ingreso") | (current_path == "/"),
        current_path == route,
    )

    link = rx.link(
        rx.el.div(
            rx.icon(icon, class_name="h-5 w-5 flex-shrink-0"),
            rx.el.span(
                text,
                class_name=rx.cond(
                    State.sidebar_open,
                    "opacity-100 min-w-0 flex-1 truncate",
                    "opacity-0 w-0"
                )
            ),
            rx.cond(
                show_badge,
                rx.el.span(
                    State.overdue_alerts_count.to_string(),
                    class_name=f"ml-auto px-2 py-0.5 text-xs font-bold bg-red-500 text-white {RADIUS['full']}",
                ),
                rx.fragment(),
            ),
            class_name=rx.cond(
                is_active,
                active_class,
                inactive_class,
            ),
        ),
        href=target_route,
        underline="none",
        class_name="block w-full min-w-0 text-left",
    )
    return rx.cond(
        page == "Servicios",
        rx.cond(
            State.can_view_servicios,
            link,
            rx.fragment(),
        ),
        rx.cond(
            page == "Clientes",
            rx.cond(
                State.can_view_clientes,
                link,
                rx.fragment(),
            ),
            rx.cond(
                page == "Cuentas Corrientes",
                rx.cond(
                    State.can_view_cuentas,
                    link,
                    rx.fragment(),
                ),
                link,
            ),
        ),
    )


_SUBMENU_ACTIVE = (
    f"block w-full min-w-0 text-left no-underline {RADIUS['lg']} "
    f"bg-white text-indigo-700 px-3 py-1.5 {SHADOWS['sm']} border-l-2 border-indigo-500"
)
_SUBMENU_INACTIVE = (
    f"block w-full min-w-0 text-left no-underline {RADIUS['lg']} "
    f"px-3 py-1.5 text-slate-500 hover:bg-white/60 hover:text-slate-700 {TRANSITIONS['fast']}"
)


def _submenu_section(
    item: rx.Var[dict],
    page_label: str,
    route: str,
    subsections: list,
    default_key: str,
) -> rx.Component:
    """Renderiza un bloque de submenú si la página y ruta coinciden."""
    return rx.cond(
        (item["page"] == page_label) & (State.router.page.path == route),
        rx.el.div(
            rx.foreach(
                subsections,
                lambda section: rx.link(
                    rx.el.div(
                        rx.icon(section["icon"], class_name="h-4 w-4"),
                        rx.el.span(
                            section["label"],
                            class_name="text-sm min-w-0 flex-1 truncate",
                        ),
                        class_name="flex items-center gap-2 min-w-0",
                    ),
                    href=route + "?tab=" + section["key"],
                    underline="none",
                    class_name=rx.cond(
                        (State.router.page.path == route)
                        & (
                            (State.router.page.params["tab"] == section["key"])
                            | (
                                (section["key"] == default_key)
                                & (
                                    (State.router.page.params["tab"] == "")
                                    | (State.router.page.params["tab"] == None)
                                )
                            )
                        ),
                        _SUBMENU_ACTIVE,
                        _SUBMENU_INACTIVE,
                    ),
                ),
            ),
            class_name="mt-1 ml-3 pl-3 flex flex-col gap-0.5 border-l border-slate-200",
        ),
        rx.fragment(),
    )


def _submenu_button(section: dict, active_key: rx.Var, on_click_handler) -> rx.Component:
    """Botón de submenú con estilo mejorado."""
    active_class = f"w-full text-left {RADIUS['lg']} bg-white text-indigo-700 px-3 py-1.5 {SHADOWS['sm']} border-l-2 border-indigo-500"
    inactive_class = f"w-full text-left {RADIUS['lg']} px-3 py-1.5 text-slate-500 hover:bg-white/60 hover:text-slate-700 {TRANSITIONS['fast']}"

    return rx.el.button(
        rx.el.div(
            rx.icon(section["icon"], class_name="h-4 w-4"),
            rx.el.span(section["label"], class_name="text-sm min-w-0 flex-1 truncate"),
            class_name="flex items-center gap-2 min-w-0",
        ),
        on_click=on_click_handler,
        class_name=rx.cond(
            active_key == section["key"],
            active_class,
            inactive_class,
        ),
    )


def sidebar() -> rx.Component:
    return rx.fragment(
        # Sidebar principal
        rx.el.div(
            rx.el.div(
                # Header con logo
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.icon("box", class_name="h-6 w-6 text-white"),
                            class_name=f"p-2 bg-indigo-600 {RADIUS['lg']} {SHADOWS['sm']}",
                        ),
                        rx.cond(
                            State.sidebar_open,
                            rx.el.div(
                                rx.el.div(
                                    rx.el.span(
                                        "TUWAYKIAPP",
                                        class_name="text-lg font-bold text-slate-900 tracking-tight truncate",
                                    ),
                                    rx.cond(
                                        State.subscription_snapshot["is_trial"],
                                        rx.badge("TRIAL", color_scheme="orange"),
                                        rx.fragment(),
                                    ),
                                    class_name="flex items-center gap-2 min-w-0",
                                ),
                                rx.el.span(
                                    "Sistema de Ventas",
                                    class_name="text-[10px] text-slate-400 uppercase tracking-wider truncate",
                                ),
                                class_name="flex flex-col leading-tight min-w-0",
                            ),
                            rx.fragment(),
                        ),
                        class_name="flex items-center gap-3 min-w-0 flex-1",
                    ),
                    rx.el.button(
                        rx.icon("panel-left-close", class_name="h-5 w-5 text-slate-400"),
                        on_click=State.toggle_sidebar,
                        class_name=f"p-2 shrink-0 {RADIUS['lg']} hover:bg-white/60 {TRANSITIONS['fast']}",
                    ),
                    class_name="flex h-16 items-center justify-between px-4",
                ),
                rx.cond(
                    State.sidebar_open,
                    rx.el.div(
                        rx.el.label(
                            rx.cond(
                                State.available_branches.length() > 1,
                                "Sucursal actual",
                                "Sucursal",
                            ),
                            class_name="text-xs font-medium text-slate-500",
                        ),
                        rx.cond(
                            State.available_branches.length() > 1,
                            rx.el.select(
                                rx.foreach(
                                    State.available_branches,
                                    lambda branch: rx.el.option(
                                        branch["name"], value=branch["id"]
                                    ),
                                ),
                                value=State.selected_branch_id,
                                on_change=State.set_active_branch,
                                class_name="w-full h-9 px-2 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                            ),
                            rx.el.div(
                                rx.el.span(
                                    rx.cond(
                                        State.active_branch_name != "",
                                        State.active_branch_name,
                                        "Sin sucursal",
                                    ),
                                    class_name="text-sm font-semibold text-slate-800",
                                ),
                                class_name="w-full h-9 px-2 flex items-center bg-white border border-slate-200 rounded-md",
                            ),
                        ),
                        rx.fragment(),
                        class_name="px-4 pb-3 flex flex-col gap-2",
                    ),
                    rx.fragment(),
                ),
                # Separador con gradiente sutil
                rx.el.div(class_name="h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent mx-4"),
                # Navegación
                rx.el.nav(
                    rx.cond(
                        State.navigation_items.length() == 0,
                        rx.el.div(
                            rx.el.p(
                                "Sin modulos disponibles",
                                class_name="text-sm text-slate-500 px-3",
                            ),
                            class_name="py-2",
                        ),
                        rx.el.div(
                            rx.foreach(
                                State.navigation_items,
                                lambda item: rx.el.div(
                                    nav_item(item["label"], item["icon"], item["page"], item["route"]),
                                    _submenu_section(item, "Configuracion", "/configuracion", CONFIG_SUBSECTIONS, "usuarios"),
                                    _submenu_section(item, "Gestion de Caja", "/caja", CASH_SUBSECTIONS, "resumen"),
                                    _submenu_section(item, "Servicios", "/servicios", SERVICES_SUBSECTIONS, "campo"),
                            class_name="flex flex-col gap-0.5 pt-2",
                        ),
                    ),
                    class_name="flex flex-col gap-0.5 p-2",
                ),
            ),
        ),
        id="sidebar-nav",
        class_name="flex-1 min-w-0 overflow-y-auto overflow-x-hidden scrollbar-thin scrollbar-thumb-slate-300 scrollbar-track-transparent",
    ),
    # Footer con usuario
    rx.el.div(
        # Separador
        rx.el.div(class_name="h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent mx-4"),
        # Info del usuario
        rx.el.div(
            rx.el.div(
                rx.image(
                    src=f"https://api.dicebear.com/9.x/initials/svg?seed={State.current_user['username']}&backgroundColor=6366f1&textColor=ffffff",
                    class_name=f"h-10 w-10 {RADIUS['full']} ring-2 ring-indigo-100",
                ),
                rx.cond(
                    State.sidebar_open,
                    rx.el.div(
                        rx.el.p(
                            State.current_user["username"],
                            class_name="font-semibold text-slate-900 text-sm truncate"
                        ),
                        rx.el.p(
                            State.current_user["role"],
                            class_name=f"text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 {RADIUS['full']} inline-block mt-0.5 truncate",
                        ),
                        class_name="flex flex-col min-w-0",
                    ),
                    rx.fragment(),
                ),
                class_name="flex items-center gap-3 min-w-0",
            ),
            class_name="p-4",
        ),
        # Botón logout
        rx.el.button(
            rx.icon("log-out", class_name="h-5 w-5"),
            rx.cond(State.sidebar_open, rx.el.span("Cerrar Sesión"), rx.fragment()),
            on_click=State.logout,
            class_name=f"flex items-center gap-3 w-full text-left px-4 py-3 text-red-500 hover:bg-red-50 {TRANSITIONS['fast']}",
        ),
    ),
    class_name=rx.cond(
        State.sidebar_open,
        f"fixed md:relative inset-y-0 left-0 z-50 flex flex-col h-screen overflow-hidden bg-gradient-to-b from-slate-50 to-white/95 backdrop-blur-xl border-r border-slate-200/50 {TRANSITIONS['slow']} w-[88vw] max-w-[320px] md:w-64 xl:w-72 {SHADOWS['lg']} md:shadow-none",
        f"w-0 overflow-hidden md:relative {TRANSITIONS['slow']}",
    ),
    key="sidebar-root",
),
# Overlay móvil con blur
rx.cond(
    State.sidebar_open,
    rx.el.div(
        on_click=State.toggle_sidebar,
        class_name="sidebar-overlay fixed inset-0 z-40 bg-black/30 backdrop-blur-sm md:hidden",
    ),
    rx.fragment(),
),
# Botón flotante para abrir sidebar
rx.cond(
    ~State.sidebar_open,
    rx.el.button(
        rx.icon("menu", class_name="h-5 w-5 text-indigo-600"),
        on_click=State.toggle_sidebar,
        class_name=f"fixed top-4 left-4 md:top-5 md:left-5 z-[55] p-2.5 bg-white/90 backdrop-blur-sm {RADIUS['xl']} {SHADOWS['md']} hover:bg-white border border-slate-200/50 {TRANSITIONS['fast']} hover:scale-105",
    ),
    rx.fragment(),
)
    )
