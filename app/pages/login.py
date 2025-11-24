import reflex as rx
from app.states.auth_state import AuthState


def login_page() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("box", class_name="h-10 w-10 text-indigo-600"),
                rx.el.h1("StockFlow", class_name="text-3xl font-bold text-gray-800"),
                class_name="flex items-center justify-center gap-3 mb-8",
            ),
            rx.el.form(
                rx.el.div(
                    rx.el.label(
                        "Usuario", class_name="block text-sm font-medium text-gray-700"
                    ),
                    rx.el.input(
                        placeholder="admin",
                        name="username",
                        class_name="mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm",
                    ),
                    class_name="mb-4",
                ),
                rx.el.div(
                    rx.el.label(
                        "Contraseña",
                        class_name="block text-sm font-medium text-gray-700",
                    ),
                    rx.el.input(
                        placeholder="••••••••",
                        name="password",
                        type="password",
                        class_name="mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm",
                    ),
                    class_name="mb-6",
                ),
                rx.el.button(
                    "Iniciar Sesión",
                    type="submit",
                    class_name="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 min-h-[44px]",
                ),
                on_submit=AuthState.login,
            ),
            rx.cond(
                AuthState.error_message != "",
                rx.el.div(
                    rx.icon("flag_triangle_right", class_name="h-5 w-5 text-red-500"),
                    rx.el.p(AuthState.error_message, class_name="text-sm text-red-700"),
                    class_name="flex items-center gap-2 mt-4 bg-red-100 p-3 rounded-md border border-red-200",
                ),
            ),
            class_name="w-full max-w-md p-6 sm:p-8 bg-white rounded-2xl shadow-lg border",
        ),
        class_name="flex items-center justify-center min-h-screen bg-gray-100 px-4",
    )
