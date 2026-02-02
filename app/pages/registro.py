import reflex as rx
from app.state import State
from app.components.ui import INPUT_STYLES, BUTTON_STYLES, RADIUS, SHADOWS, TRANSITIONS


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
                    rx.el.input(
                        placeholder="+54 9 11 1234 5678",
                        name="contact_phone",
                        type="tel",
                        auto_complete="tel",
                        class_name=INPUT_STYLES["default"],
                    ),
                    class_name="space-y-1",
                ),
                rx.el.div(
                    rx.el.label(
                        "Contraseña",
                        class_name="block text-sm font-medium text-slate-700 mb-1.5",
                    ),
                    rx.el.input(
                        placeholder="••••••••",
                        name="password",
                        type="password",
                        auto_complete="new-password",
                        class_name=INPUT_STYLES["default"],
                    ),
                    class_name="space-y-1",
                ),
                rx.el.div(
                    rx.el.label(
                        "Confirmar Contraseña",
                        class_name="block text-sm font-medium text-slate-700 mb-1.5",
                    ),
                    rx.el.input(
                        placeholder="••••••••",
                        name="confirm_password",
                        type="password",
                        auto_complete="new-password",
                        class_name=INPUT_STYLES["default"],
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
                class_name="mt-8 pt-6 border-t border-slate-100 flex items-center justify-center gap-2 text-xs text-center",
            ),
            class_name=f"w-full max-w-md p-8 bg-white {RADIUS['xl']} {SHADOWS['xl']} border border-slate-100",
        ),
        class_name="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 px-4",
        style={"fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif"},
    )
