"""Página de Política de Privacidad — TUWAYKIAPP."""

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


def privacidad_page() -> rx.Component:
    """Página pública de Política de Privacidad."""
    return rx.el.div(
        _legal_header(),
        rx.el.main(
            rx.el.div(
                _back_link(),
                rx.el.h1(
                    "Política de Privacidad",
                    class_name="mt-6 text-3xl font-extrabold tracking-tight text-slate-900",
                ),
                rx.el.p(
                    f"Última actualización: {LAST_UPDATED}",
                    class_name="mt-2 text-sm text-slate-500",
                ),
                rx.el.div(
                    # 1. Introducción
                    rx.el.h2("1. Introducción", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "En TUWAYKIAPP nos comprometemos a proteger la privacidad de nuestros usuarios. Esta Política "
                        "de Privacidad describe cómo recopilamos, usamos, almacenamos y protegemos su información personal "
                        "cuando utiliza nuestra plataforma.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 2. Datos que recopilamos
                    rx.el.h2("2. Datos que Recopilamos", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.h3("2.1 Datos proporcionados por el usuario", class_name="text-lg font-semibold text-slate-800 mt-4"),
                    rx.el.ul(
                        rx.el.li("Nombre completo y datos de contacto (email, teléfono)."),
                        rx.el.li("Nombre de la empresa y datos comerciales."),
                        rx.el.li("Credenciales de acceso (contraseña almacenada en forma cifrada)."),
                        rx.el.li("Datos operativos: productos, ventas, inventario, clientes y movimientos de caja."),
                        class_name="mt-2 list-disc pl-6 space-y-1 text-slate-700",
                    ),
                    rx.el.h3("2.2 Datos recopilados automáticamente", class_name="text-lg font-semibold text-slate-800 mt-4"),
                    rx.el.ul(
                        rx.el.li("Dirección IP y datos de navegador (user-agent)."),
                        rx.el.li("Páginas visitadas y tiempo de permanencia (solo con consentimiento de cookies de analítica)."),
                        rx.el.li("Datos de uso del sistema para mejorar la experiencia del producto."),
                        class_name="mt-2 list-disc pl-6 space-y-1 text-slate-700",
                    ),

                    # 3. Uso de los datos
                    rx.el.h2("3. Uso de los Datos", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p("Utilizamos sus datos para:", class_name="mt-3 text-slate-700 leading-relaxed"),
                    rx.el.ul(
                        rx.el.li("Proveer y mantener el servicio de la Plataforma."),
                        rx.el.li("Gestionar su cuenta y suscripción."),
                        rx.el.li("Enviar comunicaciones relacionadas con el servicio."),
                        rx.el.li("Mejorar la funcionalidad y experiencia de usuario."),
                        rx.el.li("Cumplir con obligaciones legales y regulatorias."),
                        rx.el.li("Analizar el uso de la landing page para optimizar la conversión (solo con consentimiento)."),
                        class_name="mt-2 list-disc pl-6 space-y-1 text-slate-700",
                    ),

                    # 4. Base Legal
                    rx.el.h2("4. Base Legal del Tratamiento", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.ul(
                        rx.el.li(rx.el.strong("Ejecución del contrato:"), " procesamiento necesario para prestar el servicio contratado."),
                        rx.el.li(rx.el.strong("Consentimiento:"), " para cookies de analítica y marketing (Google Analytics, Meta Pixel)."),
                        rx.el.li(rx.el.strong("Interés legítimo:"), " mejora del producto y seguridad del sistema."),
                        rx.el.li(rx.el.strong("Obligación legal:"), " cumplimiento de requerimientos normativos aplicables."),
                        class_name="mt-3 list-disc pl-6 space-y-1 text-slate-700",
                    ),

                    # 5. Cookies y Analytics
                    rx.el.h2("5. Cookies y Tecnologías de Seguimiento", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "Utilizamos cookies esenciales para el funcionamiento del sistema. Las cookies de analítica "
                        "(Google Analytics 4) y marketing (Meta Pixel) solo se activan cuando el usuario da su consentimiento "
                        "explícito a través del banner de cookies. Para más detalles, consulte nuestra ",
                        rx.el.a("Política de Cookies", href="/cookies", class_name="text-indigo-600 hover:underline"),
                        ".",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 6. Aislamiento de Datos
                    rx.el.h2("6. Aislamiento y Seguridad de Datos", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "TUWAYKIAPP opera bajo una arquitectura multi-tenant con aislamiento lógico de datos. "
                        "Esto significa que los datos de cada empresa están completamente separados y no son accesibles "
                        "por otros tenants. Implementamos medidas de seguridad que incluyen:",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),
                    rx.el.ul(
                        rx.el.li("Cifrado de contraseñas con algoritmos seguros (bcrypt)."),
                        rx.el.li("Conexiones HTTPS/TLS obligatorias."),
                        rx.el.li("Control de acceso basado en roles y permisos granulares."),
                        rx.el.li("Auditoría de acciones con registro de usuario, timestamp y sucursal."),
                        rx.el.li("Backups periódicos de la base de datos."),
                        class_name="mt-2 list-disc pl-6 space-y-1 text-slate-700",
                    ),

                    # 7. Compartición de Datos
                    rx.el.h2("7. Compartición de Datos con Terceros", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "No vendemos ni compartimos sus datos personales con terceros para fines de marketing. "
                        "Podemos compartir datos con:",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),
                    rx.el.ul(
                        rx.el.li("Proveedores de infraestructura (hosting, base de datos) bajo acuerdos de confidencialidad."),
                        rx.el.li("Herramientas de analítica (Google Analytics, Meta) solo con su consentimiento explícito."),
                        rx.el.li("Autoridades competentes cuando sea requerido por ley."),
                        class_name="mt-2 list-disc pl-6 space-y-1 text-slate-700",
                    ),

                    # 8. Retención
                    rx.el.h2("8. Retención de Datos", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "Conservamos sus datos mientras mantenga una cuenta activa. Tras la cancelación, los datos operativos "
                        "se retienen por un periodo razonable para cumplir obligaciones legales y luego se eliminan de forma segura.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 9. Derechos del Usuario
                    rx.el.h2("9. Sus Derechos", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p("Usted tiene derecho a:", class_name="mt-3 text-slate-700 leading-relaxed"),
                    rx.el.ul(
                        rx.el.li(rx.el.strong("Acceso:"), " solicitar una copia de sus datos personales."),
                        rx.el.li(rx.el.strong("Rectificación:"), " corregir datos inexactos o incompletos."),
                        rx.el.li(rx.el.strong("Eliminación:"), " solicitar la eliminación de sus datos personales."),
                        rx.el.li(rx.el.strong("Portabilidad:"), " recibir sus datos en un formato estructurado."),
                        rx.el.li(rx.el.strong("Oposición:"), " oponerse al tratamiento de sus datos en ciertos casos."),
                        rx.el.li(rx.el.strong("Revocación del consentimiento:"), " retirar su consentimiento para cookies de analítica en cualquier momento."),
                        class_name="mt-2 list-disc pl-6 space-y-1 text-slate-700",
                    ),

                    # 10. Menores
                    rx.el.h2("10. Menores de Edad", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "TUWAYKIAPP no está dirigida a menores de 18 años. No recopilamos conscientemente datos "
                        "de menores de edad.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 11. Cambios
                    rx.el.h2("11. Cambios en esta Política", class_name="text-xl font-bold text-slate-900 mt-8"),
                    rx.el.p(
                        "Podemos actualizar esta Política de Privacidad. Los cambios se publicarán en esta página "
                        "con la fecha de actualización correspondiente. El uso continuado de la Plataforma implica "
                        "la aceptación de los cambios.",
                        class_name="mt-3 text-slate-700 leading-relaxed",
                    ),

                    # 12. Contacto
                    rx.el.h2("12. Contacto", class_name="text-xl font-bold text-slate-900 mt-8 mb-3"),
                    rx.el.p(
                        "Para ejercer sus derechos o realizar consultas sobre privacidad:",
                        class_name="text-slate-700 leading-relaxed",
                    ),
                    rx.el.ul(
                        rx.el.li("WhatsApp: +54 9 11 6837-6517"),
                        rx.el.li(rx.el.span("Sitio web: ", rx.el.a("tuwayki.app", href="https://tuwayki.app", class_name="text-indigo-600 hover:underline"))),
                        class_name="mt-2 list-disc pl-6 space-y-1 text-slate-700",
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
