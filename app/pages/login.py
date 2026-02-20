import reflex as rx
from app.state import State
from app.components.ui import (
    INPUT_STYLES,
    BUTTON_STYLES,
    RADIUS,
    SHADOWS,
    TRANSITIONS,
)


def login_page() -> rx.Component:
    return rx.el.div(
        # Gradient bar top
        rx.el.div(
            class_name=(
                "fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r "
                "from-amber-400 via-rose-500 to-indigo-500 z-[60]"
            ),
        ),
        # Login card
        rx.el.div(
            # Logo section
            rx.el.div(
                rx.el.div(
                    rx.icon("box", class_name="h-8 w-8 text-white"),
                    class_name=f"p-3 bg-indigo-600 {RADIUS['xl']} {SHADOWS['lg']}",
                ),
                rx.el.div(
                    rx.el.h1(
                        "TUWAYKIAPP",
                        class_name="text-2xl font-bold text-slate-900 tracking-tight",
                    ),
                    rx.el.p(
                        "Tu socio en el Negocio",
                        class_name="text-xs text-slate-500",
                    ),
                    class_name="text-center",
                ),
                class_name="flex flex-col items-center gap-4 mb-8",
            ),
            # Login form
            rx.el.form(
                rx.el.div(
                    rx.el.label(
                        "Correo o usuario",
                        class_name="block text-sm font-medium text-slate-700 mb-1.5",
                    ),
                    rx.el.input(
                        placeholder="correo@empresa.com",
                        name="username",
                        auto_complete="email",
                        class_name=INPUT_STYLES["default"],
                    ),
                    class_name="space-y-1",
                ),
                rx.el.div(
                    rx.el.label(
                        "Contraseña",
                        class_name="block text-sm font-medium text-slate-700 mb-1.5",
                    ),
                    rx.el.div(
                        rx.el.input(
                            placeholder="••••••••",
                            name="password",
                            type=rx.cond(
                                State.show_login_password,
                                "text",
                                "password",
                            ),
                            auto_complete="current-password",
                            class_name=INPUT_STYLES["default"] + " pr-11",
                        ),
                        rx.el.button(
                            rx.cond(
                                State.show_login_password,
                                rx.icon("eye_off", class_name="h-4 w-4"),
                                rx.icon("eye", class_name="h-4 w-4"),
                            ),
                            type="button",
                            on_click=State.toggle_login_password_visibility,
                            class_name=(
                                "absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-7 w-7 "
                                "items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 "
                                "hover:text-slate-700 transition-colors duration-150"
                            ),
                            aria_label=rx.cond(
                                State.show_login_password,
                                "Ocultar contraseña",
                                "Mostrar contraseña",
                            ),
                            title=rx.cond(
                                State.show_login_password,
                                "Ocultar contraseña",
                                "Mostrar contraseña",
                            ),
                        ),
                        class_name="relative",
                    ),
                    class_name="space-y-1",
                ),
                # Submit button
                rx.el.button(
                    "Iniciar Sesión",
                    type="submit",
                    class_name=BUTTON_STYLES["primary"] + " w-full min-h-[44px]",
                ),
                on_submit=State.login,
                class_name="space-y-5",
            ),
            # Mensaje de error
            rx.cond(
                State.error_message != "",
                rx.el.div(
                    rx.icon("circle-alert", class_name="h-5 w-5 text-red-500 flex-shrink-0"),
                    rx.el.p(State.error_message, class_name="text-sm text-red-700"),
                    class_name=f"flex items-center gap-3 mt-5 bg-red-50 p-4 {RADIUS['lg']} border border-red-200",
                ),
            ),
            # Footer
            rx.el.div(
                rx.el.div(
                    rx.el.span("Creado por", class_name="text-slate-400"),
                    rx.el.a(
                        "Trebor Oscorima",
                        href="https://www.facebook.com/trebor.oscorima/?locale=es_LA",
                        target="_blank",
                        rel="noopener noreferrer",
                        class_name=f"text-indigo-600 hover:text-indigo-700 {TRANSITIONS['fast']} font-medium",
                    ),
                    rx.el.span("🧉⚽️"),
                    class_name="flex items-center gap-1.5",
                ),
                rx.el.a(
                    "WhatsApp +5491168376517",
                    href="https://wa.me/5491168376517",
                    target="_blank",
                    rel="noopener noreferrer",
                    class_name=f"text-slate-400 hover:text-emerald-600 {TRANSITIONS['fast']}",
                ),
                class_name="mt-8 pt-6 border-t border-slate-100 flex flex-col items-center gap-2 text-xs",
            ),
            class_name=f"w-full max-w-md p-6 sm:p-8 bg-white {RADIUS['xl']} {SHADOWS['xl']} border border-slate-100",
        ),
        class_name="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 px-4",
        style={"fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif"},
    )
