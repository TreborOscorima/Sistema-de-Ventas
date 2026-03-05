"""Página de Términos y Condiciones — TUWAYKIAPP."""

import os

import reflex as rx

PUBLIC_SITE_URL = (os.getenv("PUBLIC_SITE_URL") or "https://tuwayki.app").strip().rstrip("/")

LAST_UPDATED = "4 de marzo de 2026"


def _legal_header() -> rx.Component:
    return rx.el.header(
        rx.el.div(
            rx.el.a(
                rx.icon("box", class_name="h-7 w-7 text-indigo-600"),
                rx.el.span("TUWAYKIAPP", class_name="text-lg font-extrabold tracking-tight text-slate-900"),
                href="/",
                class_name="inline-flex items-center gap-2.5",
            ),
            class_name="mx-auto flex w-full max-w-4xl items-center px-4 py-4 sm:px-6 lg:px-8",
        ),
        class_name="border-b border-slate-200 bg-white",
    )


def _back_link() -> rx.Component:
    return rx.el.a(
        rx.icon("arrow-left", class_name="h-4 w-4"),
        "Volver al inicio",
        href="/",
        class_name="inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-700 transition-colors",
    )


def terminos_page() -> rx.Component:
    """Página pública de Términos y Condiciones."""
    return rx.el.div(
        _legal_header(),
        rx.el.main(
            rx.el.div(
                _back_link(),
                rx.el.h1(
                    "Términos y Condiciones",
                    class_name="mt-6 text-3xl font-extrabold tracking-tight text-slate-900",
                ),
                rx.el.p(
                    f"Última actualización: {LAST_UPDATED}",
                    class_name="mt-2 text-sm text-slate-500",
                ),
                rx.el.div(
                    # 1. Aceptación
                    rx.el.h2("1. Aceptación de los Términos", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "Al acceder y utilizar TUWAYKIAPP (en adelante, \"la Plataforma\"), usted acepta estos Términos y Condiciones "
                        "en su totalidad. Si no está de acuerdo con alguna parte, no utilice la Plataforma.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 2. Descripción del Servicio
                    rx.el.h2("2. Descripción del Servicio", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "TUWAYKIAPP es una plataforma SaaS (Software como Servicio) de gestión comercial que permite a negocios "
                        "administrar ventas, inventario, caja, reservas, clientes y reportes. El servicio opera bajo un modelo "
                        "multi-tenant donde cada empresa mantiene sus datos aislados.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 3. Registro y Cuenta
                    rx.el.h2("3. Registro y Cuenta de Usuario", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "Para utilizar la Plataforma, debe registrarse proporcionando información veraz y actualizada. "
                        "Usted es responsable de mantener la confidencialidad de sus credenciales de acceso y de todas "
                        "las actividades realizadas bajo su cuenta.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 4. Periodo de Prueba
                    rx.el.h2("4. Periodo de Prueba Gratuito", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "TUWAYKIAPP ofrece un periodo de prueba gratuito de 15 días. Durante este periodo, tendrá acceso "
                        "a las funcionalidades del plan seleccionado. Al finalizar el periodo de prueba, deberá elegir un plan "
                        "de suscripción para continuar utilizando el servicio.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 5. Planes y Pagos
                    rx.el.h2("5. Planes y Pagos", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "Los precios de los planes están publicados en la Plataforma y pueden ser actualizados con previo aviso. "
                        "Los pagos se realizan de forma mensual o anual según el plan elegido. La falta de pago podrá resultar "
                        "en la suspensión temporal del acceso al servicio.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 6. Uso Aceptable
                    rx.el.h2("6. Uso Aceptable", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p("El usuario se compromete a:", class_name="mt-3 text-slate-700 leading-relaxed"),
                    rx.el.ul(
                        rx.el.li("Utilizar la Plataforma únicamente para fines comerciales legítimos."),
                        rx.el.li("No intentar acceder a datos de otros tenants o empresas."),
                        rx.el.li("No realizar ingeniería inversa ni intentar comprometer la seguridad del sistema."),
                        rx.el.li("No utilizar la Plataforma para actividades ilegales o fraudulentas."),
                        rx.el.li("Mantener actualizados sus datos de contacto y facturación."),
                        class_name="mt-2 list-disc pl-6 space-y-1 text-slate-700",
                    ),

                    # 7. Propiedad Intelectual
                    rx.el.h2("7. Propiedad Intelectual", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "TUWAYKIAPP, su código fuente, diseño, marca y contenidos son propiedad de sus desarrolladores. "
                        "El usuario conserva todos los derechos sobre los datos comerciales que ingrese en la Plataforma.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 8. Disponibilidad
                    rx.el.h2("8. Disponibilidad del Servicio", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "Nos esforzamos por mantener la Plataforma disponible de forma continua. Sin embargo, pueden existir "
                        "interrupciones por mantenimiento programado, actualizaciones o causas de fuerza mayor. No garantizamos "
                        "disponibilidad del 100%.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 9. Limitación de Responsabilidad
                    rx.el.h2("9. Limitación de Responsabilidad", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "TUWAYKIAPP no será responsable por daños indirectos, pérdida de beneficios, pérdida de datos "
                        "o interrupciones de negocio derivadas del uso o imposibilidad de uso de la Plataforma. "
                        "La responsabilidad máxima se limita al monto pagado por el usuario en los últimos 12 meses.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 10. Cancelación
                    rx.el.h2("10. Cancelación y Terminación", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "El usuario puede cancelar su suscripción en cualquier momento. Tras la cancelación, el acceso "
                        "se mantendrá hasta el final del periodo pagado. Nos reservamos el derecho de suspender o terminar "
                        "cuentas que violen estos términos.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 11. Modificaciones
                    rx.el.h2("11. Modificaciones a los Términos", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "Podemos actualizar estos Términos y Condiciones. Las modificaciones serán publicadas en esta página "
                        "y notificadas a los usuarios registrados. El uso continuado de la Plataforma tras las modificaciones "
                        "implica la aceptación de los nuevos términos.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 12. Contacto
                    rx.el.h2("12. Contacto", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "Para consultas sobre estos Términos y Condiciones, puede contactarnos a través de:",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),
                    rx.el.ul(
                        rx.el.li("WhatsApp: +54 9 11 6837-6517"),
                        rx.el.li(rx.el.span("Sitio web: ", rx.el.a("tuwayki.app", href="https://tuwayki.app", class_name="text-indigo-600 hover:underline"))),
                        class_name="mt-2 list-disc pl-6 space-y-1 text-slate-700",
                    ),

                    # 13. Ley Aplicable
                    rx.el.h2("13. Ley Aplicable y Jurisdicción", class_name="text-xl font-bold text-slate-900 mt-8 mb-3"),
                    rx.el.p(
                        "Estos Términos se rigen por las leyes de la República Argentina. Cualquier disputa será sometida "
                        "a los tribunales competentes de la Ciudad Autónoma de Buenos Aires.",
                        class_name="text-slate-700 leading-relaxed",
                    ),

                    class_name="prose max-w-none",
                ),
                class_name="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:px-8",
            ),
            class_name="min-h-screen bg-slate-50",
        ),
        rx.el.footer(
            rx.el.div(
                rx.el.p(
                    "TUWAYKIAPP © 2026. Todos los derechos reservados.",
                    class_name="text-sm text-slate-500 text-center",
                ),
                class_name="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6 lg:px-8",
            ),
            class_name="border-t border-slate-200 bg-white",
        ),
        class_name="min-h-screen bg-slate-50",
    )
