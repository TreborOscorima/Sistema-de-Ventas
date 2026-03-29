import reflex as rx
from app.state import State
from app.constants import WHATSAPP_NUMBER
from app.components.ui import (
    INPUT_STYLES,
    BUTTON_STYLES,
    TYPOGRAPHY,
    RADIUS,
    GRADIENT_BRAND_BAR,
)


def cambiar_contrasena_page() -> rx.Component:
    """Página de cambio obligatorio de contraseña inicial."""
    return rx.el.div(
        rx.el.div(
            class_name=f"fixed top-0 left-0 right-0 h-[3px] {GRADIENT_BRAND_BAR} z-[60]",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon("lock", class_name="h-10 w-10 text-indigo-600"),
                rx.el.div(
                    rx.el.h1(
                        "Actualizar Contraseña",
                        class_name="text-2xl font-bold text-slate-800 text-center",
                    ),
                    rx.el.p(
                        "Por seguridad debes cambiar tu clave inicial.",
                        class_name=f"{TYPOGRAPHY['caption']} text-center",
                    ),
                    class_name="flex flex-col items-center leading-tight",
                ),
                class_name="flex items-center justify-center gap-3 mb-6",
            ),
            rx.el.form(
                rx.el.div(
                    rx.el.label(
                        "Nueva Contraseña",
                        class_name=f"block {TYPOGRAPHY['label']}",
                    ),
                    rx.el.div(
                        rx.el.input(
                            placeholder="Mínimo 6 caracteres",
                            name="password",
                            type=rx.cond(State.show_change_password, "text", "password"),
                            class_name=INPUT_STYLES["default"] + " pr-10",
                        ),
                        rx.el.button(
                            rx.cond(
                                State.show_change_password,
                                rx.icon("eye-off", class_name="h-4 w-4 text-slate-400"),
                                rx.icon("eye", class_name="h-4 w-4 text-slate-400"),
                            ),
                            type="button",
                            on_click=State.toggle_change_password_visibility,
                            class_name="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 hover:bg-slate-100 rounded transition-colors",
                        ),
                        class_name="relative mt-1",
                    ),
                    class_name="mb-4",
                ),
                rx.el.div(
                    rx.el.label(
                        "Confirmar Contraseña",
                        class_name=f"block {TYPOGRAPHY['label']}",
                    ),
                    rx.el.div(
                        rx.el.input(
                            placeholder="Repite la contraseña",
                            name="confirm_password",
                            type=rx.cond(State.show_change_confirm_password, "text", "password"),
                            class_name=INPUT_STYLES["default"] + " pr-10",
                        ),
                        rx.el.button(
                            rx.cond(
                                State.show_change_confirm_password,
                                rx.icon("eye-off", class_name="h-4 w-4 text-slate-400"),
                                rx.icon("eye", class_name="h-4 w-4 text-slate-400"),
                            ),
                            type="button",
                            on_click=State.toggle_change_confirm_password_visibility,
                            class_name="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 hover:bg-slate-100 rounded transition-colors",
                        ),
                        class_name="relative mt-1",
                    ),
                    class_name="mb-6",
                ),
                rx.el.button(
                    "Actualizar",
                    type="submit",
                    class_name=BUTTON_STYLES["primary"] + " w-full",
                ),
                on_submit=State.change_password,
            ),
            rx.cond(
                State.password_change_error != "",
                rx.el.div(
                    rx.icon("flag-triangle-right", class_name="h-5 w-5 text-red-500"),
                    rx.el.p(
                        State.password_change_error,
                        class_name=TYPOGRAPHY["error_message"],
                    ),
                    role="alert",
                    class_name=f"flex items-center gap-2 mt-4 bg-red-100 p-3 {RADIUS['md']} border border-red-200",
                ),
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.span("Creado por", class_name="text-slate-500"),
                    rx.el.a(
                        "Trebor Oscorima",
                        href="https://www.facebook.com/trebor.oscorima/?locale=es_LA",
                        target="_blank",
                        rel="noopener noreferrer",
                        class_name="text-indigo-600 hover:text-indigo-700 transition-colors",
                    ),
                    rx.el.span("-", class_name="text-slate-500"),
                    class_name="flex items-center gap-1",
                ),
                rx.el.a(
                    f"WhatsApp +{WHATSAPP_NUMBER}",
                    href=f"https://wa.me/{WHATSAPP_NUMBER}",
                    target="_blank",
                    rel="noopener noreferrer",
                    class_name="text-slate-500 hover:text-emerald-600 transition-colors",
                ),
                class_name="mt-6 flex flex-col items-center gap-1 text-xs",
            ),
            class_name=f"w-full max-w-md p-6 sm:p-8 bg-white {RADIUS['lg']} shadow-sm border border-slate-200",
        ),
        class_name="flex items-center justify-center min-h-screen bg-slate-50 px-4",
    )
