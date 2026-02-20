import reflex as rx
from app.state import State
from app.components.ui import BUTTON_STYLES, RADIUS, SHADOWS, TRANSITIONS
from app.constants import WHATSAPP_NUMBER


def periodo_prueba_finalizado_page() -> rx.Component:
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
                    rx.icon("triangle-alert", class_name="h-8 w-8 text-white"),
                    class_name=f"p-3 bg-amber-500 {RADIUS['xl']} {SHADOWS['lg']}",
                ),
                rx.el.h1(
                    "Periodo de prueba finalizado",
                    class_name="text-2xl font-bold text-slate-900 tracking-tight text-center",
                ),
                rx.el.p(
                    "Tu periodo de prueba ha terminado. Para continuar usando el sistema, "
                    "activa tu suscripción o contacta a soporte.",
                    class_name="text-sm text-slate-600 text-center",
                ),
                class_name="flex flex-col items-center gap-3",
            ),
            rx.el.div(
                rx.el.a(
                    rx.icon("message-circle", class_name="h-4 w-4"),
                    "Contactar soporte",
                    href=f"https://wa.me/{WHATSAPP_NUMBER}",
                    target="_blank",
                    rel="noopener noreferrer",
                    class_name=BUTTON_STYLES["warning"] + " w-full justify-center",
                ),
                rx.el.button(
                    rx.icon("log-out", class_name="h-4 w-4"),
                    "Cerrar sesión",
                    on_click=State.logout,
                    class_name=BUTTON_STYLES["secondary"] + " w-full justify-center",
                ),
                class_name="flex flex-col gap-3 mt-6",
            ),
            rx.el.div(
                rx.el.span("¿Necesitas ayuda inmediata?", class_name="text-slate-400"),
                rx.el.a(
                    f"WhatsApp +{WHATSAPP_NUMBER}",
                    href=f"https://wa.me/{WHATSAPP_NUMBER}",
                    target="_blank",
                    rel="noopener noreferrer",
                    class_name=f"text-slate-400 hover:text-emerald-600 {TRANSITIONS['fast']}",
                ),
                class_name="mt-6 pt-6 border-t border-slate-100 flex flex-col items-center gap-2 text-xs",
            ),
            class_name=f"w-full max-w-md p-6 sm:p-8 bg-white {RADIUS['xl']} {SHADOWS['xl']} border border-slate-100",
        ),
        class_name="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 px-4",
        style={"fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif"},
    )
