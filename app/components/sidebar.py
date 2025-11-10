import reflex as rx
from app.state import State
from app.states.auth_state import AuthState


def nav_item(text: str, icon: str, page: str) -> rx.Component:
    return rx.el.a(
        rx.el.div(
            rx.icon(icon, class_name="h-5 w-5"),
            rx.el.span(
                text, class_name=rx.cond(State.sidebar_open, "opacity-100", "opacity-0")
            ),
            class_name=rx.cond(
                State.current_page == page,
                "flex items-center gap-3 rounded-lg bg-indigo-100 px-3 py-2 text-indigo-700 transition-all hover:text-indigo-900 font-semibold",
                "flex items-center gap-3 rounded-lg px-3 py-2 text-gray-500 transition-all hover:text-gray-900 font-medium",
            ),
        ),
        on_click=lambda: State.set_page(page),
        href="#",
        class_name="w-full",
    )


def sidebar() -> rx.Component:
    return rx.el.div(
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
                nav_item("Ingreso", "arrow-down-to-line", "Ingreso"),
                nav_item("Venta", "arrow-up-from-line", "Venta"),
                nav_item("Inventario", "boxes", "Inventario"),
                nav_item("Historial", "history", "Historial"),
                nav_item("Configuracion", "settings", "Configuracion"),
                class_name="flex flex-col gap-2 p-4",
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
            "flex flex-col h-screen bg-gray-50 border-r transition-all duration-300 w-20",
        ),
    )