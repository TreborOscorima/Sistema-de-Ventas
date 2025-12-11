import reflex as rx
from app.state import State

CONFIG_SUBSECTIONS = [
    {"key": "usuarios", "label": "Gestion de Usuarios", "icon": "users"},
    {"key": "monedas", "label": "Selector de Monedas", "icon": "coins"},
    {"key": "unidades", "label": "Unidades de Medida", "icon": "ruler"},
    {"key": "pagos", "label": "Metodos de Pago", "icon": "credit-card"},
    {"key": "precios_campo", "label": "Precios de Campo", "icon": "tags"},
]

SERVICES_SUBSECTIONS = [
    {"key": "campo", "label": "Alquiler de Campo", "icon": "trees"},
    {"key": "piscina", "label": "Alquiler de Piscina", "icon": "waves"},
]

CASH_SUBSECTIONS = [
    {"key": "resumen", "label": "Resumen de Caja", "icon": "layout-dashboard"},
    {"key": "movimientos", "label": "Movimientos de Caja Chica", "icon": "arrow-left-right"},
]

def nav_item(text: str, icon: str, page: str) -> rx.Component:
    return rx.el.a(
        rx.el.div(
            rx.icon(icon, class_name="h-5 w-5"),
            rx.el.span(
                text, class_name=rx.cond(State.sidebar_open, "opacity-100", "opacity-0")
            ),
            class_name=rx.cond(
                State.active_page == page,
                "flex items-center gap-3 rounded-lg bg-indigo-100 px-3 py-2 text-indigo-700 transition-all hover:text-indigo-900 font-semibold",
                "flex items-center gap-3 rounded-lg px-3 py-2 text-gray-500 transition-all hover:text-gray-900 font-medium",
            ),
        ),
        on_click=lambda: State.set_page(page),
        href="#",
        class_name="w-full",
    )


def sidebar() -> rx.Component:
    return rx.fragment(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.icon("box", class_name="h-8 w-8 text-indigo-600"),
                        rx.cond(
                            State.sidebar_open,
                            rx.el.span("StockFlow", class_name="text-xl font-bold"),
                            rx.fragment(),
                        ),
                        class_name="flex items-center gap-2 font-semibold",
                    ),
                    rx.el.button(
                        rx.icon("panel-left-close", class_name="h-5 w-5"),
                        on_click=State.toggle_sidebar,
                        class_name="p-2 rounded-full hover:bg-gray-200",
                    ),
                    class_name="flex h-16 items-center justify-between border-b px-4",
                ),
                rx.el.nav(
                    rx.cond(
                        State.navigation_items.length() == 0,
                        rx.el.div(
                            rx.el.p(
                                "Sin modulos disponibles",
                                class_name="text-sm text-gray-500 px-3",
                            ),
                            class_name="py-2",
                        ),
                        rx.el.div(
                            rx.foreach(
                                State.navigation_items,
                                lambda item: rx.el.div(
                                    nav_item(item["label"], item["icon"], item["page"]),
                                    rx.cond(
                                        (item["page"] == "Configuracion")
                                        & (State.active_page == "Configuracion"),
                                        rx.el.div(
                                            rx.foreach(
                                                CONFIG_SUBSECTIONS,
                                                lambda section: rx.el.button(
                                                    rx.el.div(
                                                        rx.icon(
                                                            section["icon"],
                                                            class_name="h-4 w-4 text-indigo-600",
                                                        ),
                                                        rx.el.span(
                                                            section["label"],
                                                            class_name="text-sm",
                                                        ),
                                                        class_name="flex items-center gap-2",
                                                    ),
                                                    on_click=lambda _,
                                                    key=section["key"]: State.go_to_config_tab(
                                                        key
                                                    ),
                                                    class_name=rx.cond(
                                                        State.config_active_tab
                                                        == section["key"],
                                                        "w-full text-left rounded-md bg-indigo-50 text-indigo-700 px-3 py-2 border border-indigo-100",
                                                        "w-full text-left rounded-md px-3 py-2 text-gray-600 hover:bg-gray-50",
                                                    ),
                                                ),
                                            ),
                                            class_name="mt-2 ml-4 flex flex-col gap-1",
                                        ),
                                        rx.fragment(),
                                    ),
                                    rx.cond(
                                        (item["page"] == "Gestion de Caja")
                                        & (State.active_page == "Gestion de Caja"),
                                        rx.el.div(
                                            rx.foreach(
                                                CASH_SUBSECTIONS,
                                                lambda section: rx.el.button(
                                                    rx.el.div(
                                                        rx.icon(
                                                            section["icon"],
                                                            class_name="h-4 w-4 text-indigo-600",
                                                        ),
                                                        rx.el.span(
                                                            section["label"],
                                                            class_name="text-sm",
                                                        ),
                                                        class_name="flex items-center gap-2",
                                                    ),
                                                    on_click=lambda _, key=section[
                                                        "key"
                                                    ]: State.set_cash_tab(key),
                                                    class_name=rx.cond(
                                                        State.cash_active_tab
                                                        == section["key"],
                                                        "w-full text-left rounded-md bg-indigo-50 text-indigo-700 px-3 py-2 border border-indigo-100",
                                                        "w-full text-left rounded-md px-3 py-2 text-gray-600 hover:bg-gray-50",
                                                    ),
                                                ),
                                            ),
                                            class_name="mt-2 ml-4 flex flex-col gap-1",
                                        ),
                                        rx.fragment(),
                                    ),
                                    rx.cond(
                                        (item["page"] == "Servicios")
                                        & (State.active_page == "Servicios"),
                                        rx.el.div(
                                            rx.foreach(
                                                SERVICES_SUBSECTIONS,
                                                lambda section: rx.el.button(
                                                    rx.el.div(
                                                        rx.icon(
                                                            section["icon"],
                                                            class_name="h-4 w-4 text-indigo-600",
                                                        ),
                                                        rx.el.span(
                                                            section["label"],
                                                            class_name="text-sm",
                                                        ),
                                                        class_name="flex items-center gap-2",
                                                    ),
                                                    on_click=lambda _, key=section[
                                                        "key"
                                                    ]: State.set_service_tab(key),
                                                    class_name=rx.cond(
                                                        State.service_active_tab
                                                        == section["key"],
                                                        "w-full text-left rounded-md bg-indigo-50 text-indigo-700 px-3 py-2 border border-indigo-100",
                                                        "w-full text-left rounded-md px-3 py-2 text-gray-600 hover:bg-gray-50",
                                                    ),
                                                ),
                                            ),
                                            class_name="mt-2 ml-4 flex flex-col gap-1",
                                        ),
                                        rx.fragment(),
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                            ),
                            class_name="flex flex-col gap-2 p-4",
                        ),
                    ),
                ),
                class_name="flex-1 overflow-auto",
            ),
            rx.el.div(
                rx.el.div(
                    rx.image(
                        src=f"https://api.dicebear.com/9.x/initials/svg?seed={State.current_user['username']}",
                        class_name="h-10 w-10 rounded-full",
                    ),
                    rx.cond(
                        State.sidebar_open,
                        rx.el.div(
                            rx.el.p(
                                State.current_user["username"], class_name="font-semibold"
                            ),
                            rx.el.p(
                                State.current_user["role"],
                                class_name="text-xs text-gray-500",
                            ),
                            class_name="flex flex-col",
                        ),
                        rx.fragment(),
                    ),
                    class_name="flex items-center gap-3 p-4",
                ),
                rx.el.button(
                    rx.icon("log-out", class_name="h-5 w-5"),
                    rx.cond(State.sidebar_open, rx.el.span("Cerrar Sesión"), rx.fragment()),
                    on_click=State.logout,
                    class_name="flex items-center gap-3 w-full text-left px-4 py-2 text-red-500 hover:bg-red-100",
                ),
                class_name="border-t",
            ),
            class_name=rx.cond(
                State.sidebar_open,
                "flex flex-col h-screen bg-gray-50 border-r transition-all duration-300 w-64",
                "w-0 overflow-hidden transition-all duration-300",
            ),
        ),
        rx.cond(
            ~State.sidebar_open,
            rx.el.button(
                rx.icon("panel-left-open", class_name="h-6 w-6 text-indigo-600"),
                on_click=State.toggle_sidebar,
                class_name="fixed top-4 left-4 z-50 p-2 bg-white rounded-full shadow-md hover:bg-gray-100 border border-gray-200 cursor-pointer",
            ),
            rx.fragment(),
        )
    )
