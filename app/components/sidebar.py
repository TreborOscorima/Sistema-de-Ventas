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
    # Páginas con submódulos: en rail mostramos un punto indicador.
    has_submenu = (
        (page == "Configuracion")
        | (page == "Gestion de Caja")
        | (page == "Servicios")
    )
    show_submenu_dot = has_submenu & ~State.sidebar_open

    # Estilos para item activo vs inactivo (responsive: rail vs expandido).
    # En el rail (colapsado) usamos un tile cuadrado h-10 w-10 centrado para
    # que los iconos queden visualmente equilibrados dentro del rail de 64px.
    active_class = rx.cond(
        State.sidebar_open,
        f"relative flex items-center gap-3 min-w-0 {RADIUS['lg']} bg-indigo-600 text-white px-3 py-2 font-semibold {SHADOWS['sm']} {TRANSITIONS['fast']}",
        f"relative flex items-center justify-center mx-auto h-10 w-10 {RADIUS['lg']} bg-indigo-600 text-white {SHADOWS['sm']} {TRANSITIONS['fast']}",
    )
    inactive_class = rx.cond(
        State.sidebar_open,
        f"relative flex items-center gap-3 min-w-0 {RADIUS['lg']} px-3 py-2 text-slate-600 hover:bg-white/60 hover:text-slate-900 font-medium {TRANSITIONS['fast']}",
        f"relative flex items-center justify-center mx-auto h-10 w-10 {RADIUS['lg']} text-slate-600 hover:bg-indigo-50 hover:text-indigo-700 {TRANSITIONS['fast']}",
    )

    target_route = rx.cond(
        has_overdue,
        "/cuentas?filter=overdue",
        route,
    )
    is_active = State.active_page == page

    # Indicador de submódulo: un punto en la esquina del tile cuando el rail
    # está colapsado, para señalar que el item tiene submódulos accesibles
    # via flyout en hover. Sólo se muestra en rail (no expandido) y para
    # páginas con submódulos.
    submenu_dot = rx.cond(
        show_submenu_dot,
        rx.el.span(
            class_name=rx.cond(
                is_active,
                "absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-white/80",
                "absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-indigo-400",
            ),
        ),
        rx.fragment(),
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
            submenu_dot,
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
    item_idx: rx.Var[int],
) -> rx.Component:
    """Popover lateral con submenú cuando el sidebar está colapsado.

    Visibilidad controlada por `State.open_flyout` (state-driven, no CSS
    hover). El item del rail dispara `open_rail_flyout` en `mouse_enter` y
    `schedule_close_rail_flyout` (debounced 180ms) en `mouse_leave`.

    Posicionamiento adyacente al icono (`absolute left-full`) en vez de
    centrado en viewport. Para items en la mitad inferior del rail, el
    panel se ancla al fondo del icono y crece hacia arriba (`bottom-0`),
    así no se corta contra el borde inferior del viewport — caso típico
    de Configuración con 8 submódulos al final del rail.
    """
    is_open = State.open_flyout == page_label
    # Flip: items en la mitad inferior anclan el panel a `bottom-0` para
    # extenderse hacia arriba. Heurística por índice (no necesita medir
    # el DOM): suficiente para un rail vertical estable.
    flip = item_idx >= (State.navigation_items.length() / 2)
    return rx.cond(
        (item["page"] == page_label) & ~State.sidebar_open,
        rx.el.div(
            # Panel flotante con submódulos.
            rx.el.div(
                # Encabezado del flyout con el nombre del módulo padre
                rx.el.div(
                    rx.el.span(
                        page_label,
                        class_name="text-xs font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap",
                    ),
                    class_name="px-3 py-2 border-b border-slate-100 flex-shrink-0",
                ),
                # Lista de subsecciones — `flex-1 min-h-0 overflow-y-auto`
                # garantiza que el scroll interno se active cuando el
                # contenido excede la altura disponible del panel.
                rx.el.div(
                    rx.foreach(
                        subsections,
                        lambda section: rx.link(
                            rx.el.div(
                                rx.icon(section["icon"], class_name="h-4 w-4 flex-shrink-0"),
                                rx.el.span(
                                    section["label"],
                                    class_name="text-sm whitespace-nowrap",
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
                    class_name=(
                        "flex-1 min-h-0 overflow-y-auto p-2 flex flex-col gap-0.5 "
                        "scrollbar-thin scrollbar-thumb-slate-300 scrollbar-track-transparent"
                    ),
                ),
                class_name=(
                    "w-64 max-h-[calc(100vh-2rem)] bg-white border border-slate-200 rounded-xl shadow-xl "
                    "flex flex-col overflow-hidden"
                ),
            ),
            # Wrapper: `absolute left-full` lo posiciona inmediatamente a
            # la derecha del item del rail (que es `relative`), eliminando
            # el viaje diagonal del cursor desde el icono al panel. El
            # gap visual con el rail viene de `pl-2` (padding-left).
            #
            # Anclaje vertical condicional:
            #   - Items en la mitad superior (`flip=False`): `top-0` —
            #     panel anclado al borde superior del icono, crece hacia
            #     abajo.
            #   - Items en la mitad inferior (`flip=True`): `bottom-0` —
            #     panel anclado al borde inferior del icono, crece hacia
            #     arriba. Evita que paneles tall (Configuración con 8
            #     submódulos) se corten contra el borde inferior del
            #     viewport cuando el icono está al final del rail.
            #
            # El sidebar ya está en `overflow-visible` cuando colapsado,
            # así que el `absolute` no se recorta.
            #
            # Pointer-events-auto sólo cuando el flyout está abierto: el
            # wrapper actúa como "safe area" — cursor sobre el wrapper
            # mantiene el flyout. Cuando cerrado: `invisible` +
            # `pointer-events-none` — no bloquea contenido del fondo.
            on_mouse_enter=State.open_rail_flyout(page_label),
            on_mouse_leave=State.schedule_close_rail_flyout(page_label),
            class_name=rx.cond(
                flip,
                rx.cond(
                    is_open,
                    "hidden md:block absolute left-full bottom-0 pl-2 z-[60] "
                    "opacity-100 visible pointer-events-auto "
                    "transition-opacity duration-150",
                    "hidden md:block absolute left-full bottom-0 pl-2 z-[60] "
                    "opacity-0 invisible pointer-events-none "
                    "transition-opacity duration-150",
                ),
                rx.cond(
                    is_open,
                    "hidden md:block absolute left-full top-0 pl-2 z-[60] "
                    "opacity-100 visible pointer-events-auto "
                    "transition-opacity duration-150",
                    "hidden md:block absolute left-full top-0 pl-2 z-[60] "
                    "opacity-0 invisible pointer-events-none "
                    "transition-opacity duration-150",
                ),
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
                        lambda item, idx: rx.el.div(
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
                            # submódulos sin tener que expandir. `idx` se pasa
                            # para decidir el anclaje vertical del panel
                            # (top-0 vs bottom-0) según la posición del item.
                            _rail_flyout(
                                item,
                                "Configuracion",
                                "/configuracion",
                                CONFIG_SUBSECTIONS,
                                State.config_tab,
                                idx,
                            ),
                            _rail_flyout(
                                item,
                                "Gestion de Caja",
                                "/caja",
                                CASH_SUBSECTIONS,
                                State.cash_tab,
                                idx,
                            ),
                            _rail_flyout(
                                item,
                                "Servicios",
                                "/servicios",
                                SERVICES_SUBSECTIONS,
                                State.service_tab,
                                idx,
                            ),
                            # `relative` en el wrapper colapsado mantiene el
                            # contexto de posicionamiento. La apertura del
                            # flyout es state-driven: `on_mouse_enter` abre
                            # el flyout para esta página, `on_mouse_leave`
                            # programa un cierre debounced (180ms) que se
                            # cancela si el cursor reentra al item o entra
                            # al panel del flyout. Los handlers están
                            # siempre conectados; el evento `open_rail_flyout`
                            # hace early-return si `sidebar_open` es True,
                            # así que no genera cambios de estado spurios.
                            on_mouse_enter=State.open_rail_flyout(item["page"]),
                            on_mouse_leave=State.schedule_close_rail_flyout(item["page"]),
                            class_name=rx.cond(
                                State.sidebar_open,
                                "flex flex-col gap-0.5 pt-2",
                                "relative flex flex-col",
                            ),
                        ),
                    ),
                    class_name=rx.cond(
                        State.sidebar_open,
                        "flex flex-col gap-0.5 p-2",
                        "flex flex-col gap-1 py-2",
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
                # En expandido scrolleamos verticalmente y cortamos en X.
                # En colapsado usamos overflow-visible en ambos ejes:
                # mezclar overflow-y:auto con overflow-x:visible activa
                # `overflow: auto` en ambos por spec del navegador, y eso
                # recorta el flyout absoluto. El rail (≤18 items @ h-10)
                # cabe sobradamente en viewport sin necesidad de scroll.
                class_name=rx.cond(
                    State.sidebar_open,
                    "flex-1 min-w-0 overflow-y-auto overflow-x-hidden scrollbar-thin scrollbar-thumb-slate-300 scrollbar-track-transparent",
                    "flex-1 min-w-0 overflow-visible",
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
        # En colapsado: overflow-visible en ambos ejes para que el flyout
        # de submódulos no se recorte. El viewport mismo recorta cualquier
        # overflow vertical inesperado (sidebar usa h-screen).
        f"fixed inset-y-0 left-0 z-50 flex flex-col h-screen overflow-visible bg-gradient-to-b from-slate-50 to-white/95 backdrop-blur-xl border-r border-slate-200/50 {TRANSITIONS['slow']} w-0 md:w-16",
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
