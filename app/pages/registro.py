import reflex as rx
from app.state import State
from app.components.ui import INPUT_STYLES, BUTTON_STYLES, RADIUS, SHADOWS, TRANSITIONS


COUNTRY_DIAL_OPTIONS = [
    ("PE (+51)", "+51"),
    ("AR (+54)", "+54"),
    ("EC (+593)", "+593"),
    ("CO (+57)", "+57"),
    ("CL (+56)", "+56"),
    ("MX (+52)", "+52"),
]


def registro_page() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            class_name=(
                "fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r "
                "from-amber-400 via-rose-500 to-indigo-500 z-[60]"
            ),
        ),
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("building-2", class_name="h-8 w-8 text-white"),
                    class_name=f"p-3 bg-indigo-600 {RADIUS['xl']} {SHADOWS['lg']}",
                ),
                rx.el.h1(
                    "Registra tu Negocio",
                    class_name="text-2xl font-bold text-slate-900 tracking-tight text-center",
                ),
                rx.el.p(
                    "Crea tu empresa y comienza tu prueba gratis de 15 dias.",
                    class_name="text-sm text-slate-600 text-center",
                ),
                class_name="flex flex-col items-center gap-3 mb-8",
            ),
            rx.el.form(
                rx.el.div(
                    rx.el.label(
                        "Nombre de la Empresa",
                        class_name="block text-sm font-medium text-slate-700 mb-1.5",
                    ),
                    rx.el.input(
                        placeholder="Mi Negocio",
                        name="company_name",
                        class_name=INPUT_STYLES["default"],
                    ),
                    class_name="space-y-1",
                ),
                rx.el.div(
                    rx.el.label(
                        "Usuario",
                        class_name="block text-sm font-medium text-slate-700 mb-1.5",
                    ),
                    rx.el.input(
                        placeholder="admin",
                        name="username",
                        auto_complete="username",
                        class_name=INPUT_STYLES["default"],
                    ),
                    class_name="space-y-1",
                ),
                rx.el.div(
                    rx.el.label(
                        "Correo",
                        class_name="block text-sm font-medium text-slate-700 mb-1.5",
                    ),
                    rx.el.input(
                        placeholder="tu@empresa.com",
                        name="email",
                        type="email",
                        auto_complete="email",
                        class_name=INPUT_STYLES["default"],
                    ),
                    class_name="space-y-1",
                ),
                rx.el.div(
                    rx.el.label(
                        "Número de contacto",
                        class_name="block text-sm font-medium text-slate-700 mb-1.5",
                    ),
                    rx.el.div(
                        rx.el.select(
                            *[
                                rx.el.option(label, value=value)
                                for label, value in COUNTRY_DIAL_OPTIONS
                            ],
                            name="contact_phone_country",
                            default_value="+54",
                            class_name=(
                                INPUT_STYLES["default"]
                                + " !w-full !px-2 sm:!px-3 text-xs sm:text-sm"
                            ),
                        ),
                        rx.el.input(
                            placeholder="9 11 1234 5678",
                            name="contact_phone_number",
                            type="tel",
                            auto_complete="tel-national",
                            input_mode="numeric",
                            class_name=INPUT_STYLES["default"] + " !w-full",
                        ),
                        class_name="grid grid-cols-[116px_1fr] sm:grid-cols-[130px_1fr] items-center gap-2",
                    ),
                    rx.el.p(
                        "Selecciona el código de país y luego escribe tu número.",
                        class_name="text-xs text-slate-500",
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
                                State.show_register_password,
                                "text",
                                "password",
                            ),
                            auto_complete="new-password",
                            class_name=INPUT_STYLES["default"] + " pr-11",
                        ),
                        rx.el.button(
                            rx.cond(
                                State.show_register_password,
                                rx.icon("eye_off", class_name="h-4 w-4"),
                                rx.icon("eye", class_name="h-4 w-4"),
                            ),
                            type="button",
                            on_click=State.toggle_register_password_visibility,
                            class_name=(
                                "absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-7 w-7 "
                                "items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 "
                                "hover:text-slate-700 transition-colors duration-150"
                            ),
                            aria_label=rx.cond(
                                State.show_register_password,
                                "Ocultar contraseña",
                                "Mostrar contraseña",
                            ),
                            title=rx.cond(
                                State.show_register_password,
                                "Ocultar contraseña",
                                "Mostrar contraseña",
                            ),
                        ),
                        class_name="relative",
                    ),
                    class_name="space-y-1",
                ),
                rx.el.div(
                    rx.el.label(
                        "Confirmar Contraseña",
                        class_name="block text-sm font-medium text-slate-700 mb-1.5",
                    ),
                    rx.el.div(
                        rx.el.input(
                            placeholder="••••••••",
                            name="confirm_password",
                            type=rx.cond(
                                State.show_register_confirm_password,
                                "text",
                                "password",
                            ),
                            auto_complete="new-password",
                            class_name=INPUT_STYLES["default"] + " pr-11",
                        ),
                        rx.el.button(
                            rx.cond(
                                State.show_register_confirm_password,
                                rx.icon("eye_off", class_name="h-4 w-4"),
                                rx.icon("eye", class_name="h-4 w-4"),
                            ),
                            type="button",
                            on_click=State.toggle_register_confirm_password_visibility,
                            class_name=(
                                "absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-7 w-7 "
                                "items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 "
                                "hover:text-slate-700 transition-colors duration-150"
                            ),
                            aria_label=rx.cond(
                                State.show_register_confirm_password,
                                "Ocultar contraseña",
                                "Mostrar contraseña",
                            ),
                            title=rx.cond(
                                State.show_register_confirm_password,
                                "Ocultar contraseña",
                                "Mostrar contraseña",
                            ),
                        ),
                        class_name="relative",
                    ),
                    class_name="space-y-1",
                ),
                rx.el.button(
                    rx.cond(
                        State.is_registering,
                        "Creando...",
                        "Comenzar Prueba Gratis",
                    ),
                    type="submit",
                    disabled=State.is_registering,
                    class_name=BUTTON_STYLES["primary"] + " w-full min-h-[44px]",
                ),
                on_submit=State.handle_registration,
                class_name="space-y-5",
            ),
            rx.cond(
                State.register_error != "",
                rx.el.div(
                    rx.icon(
                        "circle-alert",
                        class_name="h-5 w-5 text-red-500 flex-shrink-0",
                    ),
                    rx.el.p(State.register_error, class_name="text-sm text-red-700"),
                    class_name=(
                        "flex items-center gap-3 mt-5 bg-red-50 p-4 "
                        f"{RADIUS['lg']} border border-red-200"
                    ),
                ),
            ),
            rx.el.div(
                rx.el.span("¿Ya tienes cuenta?", class_name="text-slate-400"),
                rx.el.a(
                    "Inicia sesion",
                    href="/",
                    class_name=f"text-indigo-600 hover:text-indigo-700 {TRANSITIONS['fast']} font-medium",
                ),
                class_name="mt-5 pt-4 border-t border-slate-100 flex items-center justify-center gap-2 text-xs text-center",
            ),
            class_name=f"w-full max-w-md p-8 bg-white {RADIUS['xl']} {SHADOWS['xl']} border border-slate-100",
        ),
        class_name="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 px-4",
        style={"fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif"},
    )
