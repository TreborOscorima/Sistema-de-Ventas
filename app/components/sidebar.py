import reflex as rx
from app.state import State
from app.components.ui import RADIUS, SHADOWS, TRANSITIONS
from app.constants import CONFIG_SUBSECTIONS, CASH_SUBSECTIONS, SERVICES_SUBSECTIONS


def nav_item(text: str, icon: str, page: str, route: str) -> rx.Component:
    """Item de navegación con indicador lateral activo."""
    has_overdue = (
        (page == "Cuentas Corrientes")
        & (State.overdue_alerts_count > 0)
    )
    show_badge = has_overdue & State.sidebar_open

    # Estilos para item activo vs inactivo (responsive: rail vs expandido)
    active_class = rx.cond(
        State.sidebar_open,
        f"relative flex items-center gap-3 min-w-0 {RADIUS['lg']} bg-indigo-600 text-white px-3 py-2 font-semibold {SHADOWS['sm']} {TRANSITIONS['fast']}",
        f"relative flex items-center justify-center {RADIUS['md']} bg-indigo-600 text-white p-1.5 {TRANSITIONS['fast']}",
    )
    inactive_class = rx.cond(
        State.sidebar_open,
        f"relative flex items-center gap-3 min-w-0 {RADIUS['lg']} px-3 py-2 text-slate-600 hover:bg-white/60 hover:text-slate-900 font-medium {TRANSITIONS['fast']}",
        f"relative flex items-center justify-center {RADIUS['md']} p-1.5 text-slate-600 hover:bg-white/60 hover:text-slate-900 {TRANSITIONS['fast']}",
    )

    target_route = rx.cond(
        has_overdue,
        "/cuentas?filter=overdue",
        route,
    )
    is_active = State.active_page == page

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
        title=rx.cond(State.sidebar_open, "", text),
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
    active_tab: rx.Var[str],
) -> rx.Component:
    """Renderiza un bloque de submenú si la página y ruta coinciden."""
    return rx.cond(
        (item["page"] == page_label) & (State.active_page == page_label) & State.sidebar_open,
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
                        active_tab == section["key"],
                        _SUBMENU_ACTIVE,
                        _SUBMENU_INACTIVE,
                    ),
                ),
            ),
            class_name="mt-1 ml-3 pl-3 flex flex-col gap-0.5 border-l border-slate-200",
        ),
        rx.fragment(),
    )


def _rail_flyout(
    item: rx.Var[dict],
    page_label: str,
    route: str,
    subsections: list,
    active_tab: rx.Var[str],
) -> rx.Component:
    """Popover lateral con submenú cuando el sidebar está colapsado.

    Aparece en hover (CSS `group-hover`) sobre items que tienen submódulos.
    Permite acceder a las subsecciones sin expandir el sidebar.
    """
    return rx.cond(
        (item["page"] == page_label) & ~State.sidebar_open,
        rx.el.div(
            # Encabezado del flyout con el nombre del módulo padre
            rx.el.div(
                rx.el.span(
                    page_label,
                    class_name="text-xs font-semibold text-slate-500 uppercase tracking-wider",
                ),
                class_name="px-3 py-2 border-b border-slate-100",
            ),
            # Lista de subsecciones
            rx.el.div(
                rx.foreach(
                    subsections,
                    lambda section: rx.link(
                        rx.el.div(
                            rx.icon(section["icon"], class_name="h-4 w-4 flex-shrink-0"),
                            rx.el.span(
                                section["label"],
                                class_name="text-sm",
                            ),
                            class_name="flex items-center gap-2",
                        ),
                        href=route + "?tab=" + section["key"],
                        underline="none",
                        class_name=rx.cond(
                            (State.active_page == page_label) & (active_tab == section["key"]),
                            _SUBMENU_ACTIVE,
                            _SUBMENU_INACTIVE,
                        ),
                    ),
                ),
                class_name="flex flex-col gap-0.5 p-2",
            ),
            # Posicionado al lado derecho del rail. `hidden md:block` evita que
            # aparezca en mobile (donde el rail mismo está oculto con w-0).
            # `group-hover:opacity-100` + `pointer-events-auto` activan el panel
            # al pasar el mouse por el wrapper `group`.
            class_name=(
                "hidden md:flex md:flex-col absolute left-full top-0 ml-2 z-[60] "
                "min-w-56 bg-white border border-slate-200 rounded-xl shadow-lg "
                "opacity-0 invisible pointer-events-none "
                "group-hover:opacity-100 group-hover:visible group-hover:pointer-events-auto "
                "focus-within:opacity-100 focus-within:visible focus-within:pointer-events-auto "
                "transition-all duration-150"
            ),
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


def _sidebar_guest_content() -> rx.Component:
    """Contenido del sidebar para visitantes no autenticados."""
    return rx.el.div(
        # Separador
        rx.el.div(class_name="h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent mx-4"),
        # Mensaje de bienvenida
        rx.el.div(
            rx.el.div(
                rx.icon("sparkles", class_name="h-8 w-8 text-indigo-500"),
                class_name="flex justify-center mb-3",
            ),
            rx.el.h2(
                "¡Bienvenido!",
                class_name="text-lg font-bold text-slate-900 text-center",
            ),
            rx.el.p(
                "Gestiona tu negocio de forma inteligente con TUWAYKIAPP.",
                class_name="text-sm text-slate-500 text-center mt-1 leading-relaxed",
            ),
            class_name="px-4 py-6",
        ),
        # Características destacadas
        rx.el.div(
            rx.el.div(
                rx.icon("chart-no-axes-combined", class_name="h-4 w-4 text-emerald-500 shrink-0"),
                rx.el.span("Control de ventas en tiempo real", class_name="text-xs text-slate-600"),
                class_name="flex items-center gap-2",
            ),
            rx.el.div(
                rx.icon("package", class_name="h-4 w-4 text-indigo-500 shrink-0"),
                rx.el.span("Inventario y stock automatizado", class_name="text-xs text-slate-600"),
                class_name="flex items-center gap-2",
            ),
            rx.el.div(
                rx.icon("file-spreadsheet", class_name="h-4 w-4 text-amber-500 shrink-0"),
                rx.el.span("Reportes y análisis financiero", class_name="text-xs text-slate-600"),
                class_name="flex items-center gap-2",
            ),
            rx.el.div(
                rx.icon("users", class_name="h-4 w-4 text-rose-500 shrink-0"),
                rx.el.span("Gestión de clientes y créditos", class_name="text-xs text-slate-600"),
                class_name="flex items-center gap-2",
            ),
            class_name="flex flex-col gap-3 px-5 py-4 mx-4 bg-slate-50 rounded-xl border border-slate-100",
        ),
        # Separador
        rx.el.div(class_name="h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent mx-4 my-4"),
        # CTA de registro
        rx.el.div(
            rx.el.p(
                "¿Aún no tienes cuenta?",
                class_name="text-sm font-semibold text-slate-700 text-center",
            ),
            rx.el.p(
                "Prueba gratis por 15 días, sin compromiso.",
                class_name="text-xs text-slate-400 text-center mt-1",
            ),
            rx.link(
                rx.el.button(
                    rx.icon("rocket", class_name="h-4 w-4"),
                    rx.el.span("Crear cuenta gratis"),
                    class_name=f"flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-indigo-600 text-white text-sm font-semibold {RADIUS['lg']} hover:bg-indigo-700 {TRANSITIONS['fast']} {SHADOWS['sm']}",
                ),
                href="/registro",
                underline="none",
                class_name="block w-full mt-3",
            ),
            class_name="px-4 py-2",
        ),
        # Separador
        rx.el.div(class_name="h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent mx-4 my-3"),
        # Indicación de login
        rx.el.div(
            rx.el.p(
                "¿Ya eres parte de nosotros?",
                class_name="text-sm font-semibold text-slate-700 text-center",
            ),
            rx.el.p(
                "Ingresa tus credenciales para continuar.",
                class_name="text-xs text-slate-400 text-center mt-1",
            ),
            class_name="px-4 py-2",
        ),
        class_name="flex-1 flex flex-col",
    )


def _sidebar_auth_content() -> rx.Component:
    """Contenido del sidebar para usuarios autenticados."""
    return rx.fragment(
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
                            # Submenús inline (sólo cuando el sidebar está expandido).
                            _submenu_section(
                                item,
                                "Configuracion",
                                "/configuracion",
                                CONFIG_SUBSECTIONS,
                                State.config_tab,
                            ),
                            _submenu_section(
                                item,
                                "Gestion de Caja",
                                "/caja",
                                CASH_SUBSECTIONS,
                                State.cash_tab,
                            ),
                            _submenu_section(
                                item,
                                "Servicios",
                                "/servicios",
                                SERVICES_SUBSECTIONS,
                                State.service_tab,
                            ),
                            # Flyout lateral en hover (sólo cuando el sidebar
                            # está colapsado / rail). Permite acceder a los
                            # submódulos sin tener que expandir.
                            _rail_flyout(
                                item,
                                "Configuracion",
                                "/configuracion",
                                CONFIG_SUBSECTIONS,
                                State.config_tab,
                            ),
                            _rail_flyout(
                                item,
                                "Gestion de Caja",
                                "/caja",
                                CASH_SUBSECTIONS,
                                State.cash_tab,
                            ),
                            _rail_flyout(
                                item,
                                "Servicios",
                                "/servicios",
                                SERVICES_SUBSECTIONS,
                                State.service_tab,
                            ),
                            # `relative group` en el wrapper colapsado permite
                            # que el flyout absoluto se posicione al costado
                            # del item y reciba el hover.
                            class_name=rx.cond(
                                State.sidebar_open,
                                "flex flex-col gap-0.5 pt-2",
                                "relative group flex flex-col",
                            ),
                        ),
                    ),
                    class_name=rx.cond(
                        State.sidebar_open,
                        "flex flex-col gap-0.5 p-2",
                        "flex flex-col gap-0.5 px-1.5 py-1",
                    ),
                ),
            ),
        ),
    )


def _sidebar_auth_footer() -> rx.Component:
    """Footer del sidebar para usuarios autenticados."""
    return rx.el.div(
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
            title=rx.cond(State.sidebar_open, "", "Cerrar Sesión"),
            class_name=rx.cond(
                State.sidebar_open,
                f"flex items-center gap-3 w-full text-left px-4 py-3 text-red-500 hover:bg-red-50 {TRANSITIONS['fast']}",
                f"flex items-center justify-center w-full px-2 py-3 text-red-500 hover:bg-red-50 {TRANSITIONS['fast']}",
            ),
        ),
    )


def sidebar() -> rx.Component:
    """Componente principal del sidebar con navegación y contenido condicional."""
    return rx.fragment(
        # Sidebar principal
        rx.el.div(
            rx.el.div(
                # Header con logo (compartido entre autenticado e invitado)
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
                                        State.is_authenticated & State.subscription_snapshot["is_trial"],
                                        rx.badge("TRIAL", color_scheme="orange"),
                                        rx.fragment(),
                                    ),
                                    class_name="flex items-center gap-2 min-w-0",
                                ),
                                rx.el.span(
                                    "Sistema de Ventas",
                                    class_name="text-xs text-slate-400 uppercase tracking-wider truncate",
                                ),
                                class_name="flex flex-col leading-tight min-w-0",
                            ),
                            rx.fragment(),
                        ),
                        class_name="flex items-center gap-3 min-w-0 flex-1",
                    ),
                    rx.el.button(
                        rx.icon(
                            rx.cond(State.sidebar_open, "panel-left-close", "panel-left-open"),
                            class_name="h-5 w-5 text-slate-400",
                        ),
                        on_click=State.toggle_sidebar,
                        title=rx.cond(State.sidebar_open, "Ocultar menu lateral", "Mostrar menu lateral"),
                        aria_label=rx.cond(State.sidebar_open, "Ocultar menu lateral", "Mostrar menu lateral"),
                        class_name=f"p-2 shrink-0 {RADIUS['lg']} hover:bg-white/60 {TRANSITIONS['fast']}",
                    ),
                    class_name=rx.cond(
                        State.sidebar_open,
                        "flex h-16 items-center justify-between px-4",
                        "hidden md:flex h-14 items-center justify-center px-2",
                    ),
                ),
                # Contenido condicional: autenticado vs invitado
                rx.cond(
                    State.is_authenticated,
                    _sidebar_auth_content(),
                    _sidebar_guest_content(),
                ),
                id="sidebar-nav",
                # En colapsado permitimos overflow-x para que el flyout de
                # submódulos pueda extenderse hacia la derecha del rail.
                # En expandido mantenemos el corte horizontal estándar.
                class_name=rx.cond(
                    State.sidebar_open,
                    "flex-1 min-w-0 overflow-y-auto overflow-x-hidden scrollbar-thin scrollbar-thumb-slate-300 scrollbar-track-transparent",
                    "flex-1 min-w-0 overflow-y-auto overflow-x-visible scrollbar-thin scrollbar-thumb-slate-300 scrollbar-track-transparent",
                ),
            ),
            # Footer condicional: solo para autenticados
            rx.cond(
                State.is_authenticated,
                _sidebar_auth_footer(),
                rx.fragment(),
            ),
            class_name=rx.cond(
        State.sidebar_open,
        f"fixed inset-y-0 left-0 z-50 flex flex-col h-screen overflow-hidden bg-gradient-to-b from-slate-50 to-white/95 backdrop-blur-xl border-r border-slate-200/50 {TRANSITIONS['slow']} w-[88vw] max-w-[320px] md:w-64 xl:w-72 {SHADOWS['lg']} md:shadow-none",
        # En colapsado: overflow-y-hidden permite que el contenido scrollee dentro,
        # pero overflow-x-visible deja al flyout de submódulos escapar el rail.
        f"fixed inset-y-0 left-0 z-50 flex flex-col h-screen overflow-y-hidden overflow-x-visible bg-gradient-to-b from-slate-50 to-white/95 backdrop-blur-xl border-r border-slate-200/50 {TRANSITIONS['slow']} w-0 md:w-16",
    ),
    style={"height": "100dvh"},
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
# Zona de reactivación izquierda + botón flotante con auto-hide
rx.cond(
    ~State.sidebar_open,
    rx.el.div(
        # Zona sensible del borde izquierdo — solo en móvil (desktop usa icon rail)
        rx.el.button(
            on_click=State.toggle_sidebar,
            title="Abrir menu lateral",
            aria_label="Abrir menu lateral",
            type="button",
            class_name="sidebar-hover-zone fixed top-3 left-0 z-[54] h-14 w-5 border-0 bg-transparent p-0 m-0 appearance-none md:hidden",
        ),
        # Botón de menú: visible al colapsar en móvil — en desktop el icon rail es suficiente
        rx.el.button(
            rx.icon("menu", class_name="h-4 w-4 text-indigo-500"),
            on_click=State.toggle_sidebar,
            title="Mostrar menu lateral",
            aria_label="Mostrar menu lateral",
            class_name=(
                f"sidebar-toggle-btn fixed top-4 left-4 z-[55] md:hidden "
                f"p-2 bg-white/80 backdrop-blur-sm {RADIUS['xl']} {SHADOWS['sm']} "
                f"hover:bg-white border border-slate-200/40 {TRANSITIONS['fast']} "
                f"hover:scale-105 hover:shadow-md hover:border-slate-300/60 "
                f"opacity-0 pointer-events-none"
            ),
        ),
        # CSS + JS para auto-hide y reveal por hover/tap en el borde izquierdo
        rx.script(src="/js/sidebar-toggle.js"),
    ),
    rx.fragment(),
)
    )
