import reflex as rx
from app.state import State
from app.constants import WHATSAPP_NUMBER


def cambiar_contrasena_page() -> rx.Component:
    """Página de cambio obligatorio de contraseña inicial."""
    return rx.el.div(
        rx.el.div(
            class_name=(
                "fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r "
                "from-amber-400 via-rose-500 to-indigo-500 z-[60]"
            ),
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
                        class_name="text-xs text-slate-500 text-center",
                    ),
                    class_name="flex flex-col items-center leading-tight",
                ),
                class_name="flex items-center justify-center gap-3 mb-6",
            ),
            rx.el.form(
                rx.el.div(
                    rx.el.label(
                        "Nueva Contraseña",
                        class_name="block text-sm font-medium text-slate-700",
                    ),
                    rx.el.div(
                        rx.el.input(
                            placeholder="Mínimo 6 caracteres",
                            name="password",
                            type=rx.cond(State.show_change_password, "text", "password"),
                            class_name="block w-full h-10 px-3 pr-10 text-sm bg-white border border-slate-200 rounded-md placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
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
                        class_name="block text-sm font-medium text-slate-700",
                    ),
                    rx.el.div(
                        rx.el.input(
                            placeholder="Repite la contraseña",
                            name="confirm_password",
                            type=rx.cond(State.show_change_confirm_password, "text", "password"),
                            class_name="block w-full h-10 px-3 pr-10 text-sm bg-white border border-slate-200 rounded-md placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
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
                    class_name="w-full h-10 flex justify-center items-center px-4 rounded-md text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20",
                ),
                on_submit=State.change_password,
            ),
            rx.cond(
                State.password_change_error != "",
                rx.el.div(
                    rx.icon("flag_triangle_right", class_name="h-5 w-5 text-red-500"),
                    rx.el.p(
                        State.password_change_error,
                        class_name="text-sm text-red-700",
                    ),
                    class_name="flex items-center gap-2 mt-4 bg-red-100 p-3 rounded-md border border-red-200",
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
            class_name="w-full max-w-md p-6 sm:p-8 bg-white rounded-xl shadow-sm border border-slate-200",
        ),
        class_name="flex items-center justify-center min-h-screen bg-slate-50 px-4",
        style={"fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif"},
    )
