import reflex as rx

from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    CARD_STYLES,
    INPUT_STYLES,
    RADIUS,
    SELECT_STYLES,
    TYPOGRAPHY,
)


def _platform_billing_section() -> rx.Component:
    """Sección de Configuración Global de Billing para el Owner panel."""
    _label = "text-xs font-medium text-slate-600 mb-1"
    _help = "text-xs text-slate-400 mt-1"
    _input = INPUT_STYLES["default"] + " text-sm"

    return rx.el.div(
        # Header
        rx.el.div(
            rx.el.div(
                rx.icon("globe", class_name="w-5 h-5 text-indigo-600"),
                rx.el.h2(
                    "Configuración Global de Billing — Perú (Nubefact Integrador)",
                    class_name="text-base font-semibold text-slate-700",
                ),
                class_name="flex items-center gap-2",
            ),
            # Badge de estado
            rx.cond(
                State.platform_billing_configured,
                rx.el.span(
                    "✓ Credenciales maestras configuradas",
                    class_name="text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full",
                ),
                rx.el.span(
                    "⚠ Sin configurar — las empresas PE no pueden facturar",
                    class_name="text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full",
                ),
            ),
            class_name="flex items-center justify-between flex-wrap gap-2",
        ),
        # Descripción
        rx.el.p(
            "Cuenta integradora de Nubefact compartida por todas las empresas peruanas del SaaS. "
            "Configurá una sola vez y todas las empresas PE pueden emitir comprobantes automáticamente.",
            class_name="text-xs text-slate-500",
        ),
        # Campos
        rx.el.div(
            # URL Nubefact Master
            rx.el.div(
                rx.el.label("URL Nubefact Integrador", class_name=_label),
                rx.el.input(
                    default_value=State.platform_nubefact_url,
                    on_change=State.platform_set_nubefact_url,
                    on_blur=State.save_platform_nubefact_url,
                    placeholder="https://api.nubefact.com/api/v1/...",
                    class_name=_input,
                ),
                rx.el.p(
                    "URL del endpoint integrador. Se guarda al salir del campo.",
                    class_name=_help,
                ),
                class_name="flex flex-col",
            ),
            # Token Nubefact Master
            rx.el.div(
                rx.el.label("Token Nubefact Integrador", class_name=_label),
                rx.el.input(
                    default_value=State.platform_nubefact_token_display,
                    on_blur=State.save_platform_nubefact_token,
                    placeholder=rx.cond(
                        State.platform_nubefact_token_display != "",
                        "****configurado**** (pegá nuevo para reemplazar)",
                        "Pegá el token API y salí del campo",
                    ),
                    type="password",
                    class_name=_input,
                ),
                rx.el.p(
                    "Se guarda encriptado (Fernet) al salir del campo. Nunca se muestra en texto plano.",
                    class_name=_help,
                ),
                class_name="flex flex-col",
            ),
            class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        class_name=CARD_STYLES["default"] + " space-y-4 mb-6",
    )


def _billing_modal() -> rx.Component:
    """Modal de gestión de billing técnico para una empresa."""
    _input = INPUT_STYLES["default"]
    _select = SELECT_STYLES["default"]
    _label = TYPOGRAPHY["label"]
    _help = TYPOGRAPHY["caption"]

    return rx.cond(
        State.owner_billing_modal_open,
        rx.el.div(
            # Overlay
            rx.el.div(
                on_click=State.owner_close_billing_modal,
                class_name="fixed inset-0 bg-black/40 z-[70] modal-overlay",
            ),
            # Panel
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.icon("file-text", class_name="h-5 w-5 text-indigo-600"),
                            class_name=f"p-2 bg-indigo-50 {RADIUS['lg']}",
                        ),
                        rx.el.div(
                            rx.el.h2(
                                "Configuración de Billing",
                                class_name=TYPOGRAPHY["section_title"],
                            ),
                            rx.el.p(
                                State.owner_billing_company_name,
                                class_name=TYPOGRAPHY["body_secondary"],
                            ),
                        ),
                        class_name="flex items-center gap-3",
                    ),
                    rx.el.button(
                        rx.icon("x", class_name="h-5 w-5"),
                        on_click=State.owner_close_billing_modal,
                        title="Cerrar",
                        aria_label="Cerrar",
                        class_name=BUTTON_STYLES["icon_ghost"],
                    ),
                    class_name="flex items-center justify-between p-4 border-b border-slate-200",
                ),
                # Body
                rx.cond(
                    State.owner_billing_loading,
                    rx.el.div(
                        rx.icon("loader-circle", class_name="h-6 w-6 text-slate-400 animate-spin"),
                        class_name="flex items-center justify-center py-12",
                    ),
                    rx.el.div(
                        # Context info (read-only)
                        rx.el.div(
                            rx.el.span(
                                "País: ", State.owner_billing_country,
                                class_name=TYPOGRAPHY["caption"],
                            ),
                            rx.el.span(" | ", class_name="text-xs text-slate-300"),
                            rx.el.span(
                                "RUC/CUIT: ", State.owner_billing_tax_id,
                                class_name=TYPOGRAPHY["caption"],
                            ),
                            rx.el.span(" | ", class_name="text-xs text-slate-300"),
                            rx.el.span(
                                State.owner_billing_business_name,
                                class_name="text-xs text-slate-600 font-medium",
                            ),
                            class_name="flex flex-wrap items-center gap-1 p-2 bg-slate-50 rounded-md",
                        ),
                        # Toggle activo
                        rx.el.div(
                            rx.el.label(
                                rx.el.input(
                                    type="checkbox",
                                    checked=State.owner_billing_is_active,
                                    on_change=State.owner_set_billing_is_active,
                                    class_name="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500",
                                ),
                                " Billing Activo",
                                class_name="flex items-center gap-2 text-sm font-medium text-slate-700 cursor-pointer",
                            ),
                            class_name="mt-1",
                        ),
                        # Ambiente
                        rx.el.div(
                            rx.el.label("Ambiente", class_name=_label),
                            rx.el.select(
                                rx.el.option("Sandbox (pruebas)", value="sandbox"),
                                rx.el.option("Producción", value="production"),
                                value=State.owner_billing_environment,
                                on_change=State.owner_set_billing_environment,
                                class_name=_select,
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                        # Nubefact (PE) — credenciales maestras de plataforma
                        rx.cond(
                            State.owner_billing_country == "PE",
                            rx.el.div(
                                rx.icon("info", class_name="w-4 h-4 text-indigo-500 shrink-0"),
                                rx.el.span(
                                    rx.el.span("Credenciales Nubefact: ", class_name="font-medium"),
                                    "Esta empresa usa las credenciales maestras del integrador configuradas en ",
                                    rx.el.span("Configuración Global de Billing", class_name="font-medium text-indigo-600"),
                                    ". Estado: ",
                                    rx.cond(
                                        State.platform_billing_configured,
                                        rx.el.span("✓ Configuradas", class_name="text-emerald-600 font-medium"),
                                        rx.el.span("⚠ Sin configurar", class_name="text-amber-600 font-medium"),
                                    ),
                                ),
                                class_name="flex items-start gap-2 text-xs text-slate-600 bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-2",
                            ),
                            rx.fragment(),
                        ),
                        # AFIP (AR)
                        rx.cond(
                            State.owner_billing_country == "AR",
                            rx.el.div(
                                rx.el.div(
                                    rx.el.label("Punto de Venta AFIP", class_name=_label),
                                    rx.el.input(
                                        type="number",
                                        value=State.owner_billing_afip_punto_venta,
                                        on_change=State.owner_set_billing_afip_punto_venta,
                                        min="1",
                                        class_name=_input,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.label("Condición IVA Emisor", class_name=_label),
                                    rx.el.select(
                                        rx.el.option("Resp. Inscripto", value="RI"),
                                        rx.el.option("Monotributista", value="monotributo"),
                                        rx.el.option("Exento", value="exento"),
                                        value=State.owner_billing_emisor_iva,
                                        on_change=State.owner_set_billing_emisor_iva,
                                        class_name=_select,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.label("Concepto AFIP", class_name=_label),
                                    rx.el.select(
                                        rx.el.option("Productos", value="1"),
                                        rx.el.option("Servicios", value="2"),
                                        rx.el.option("Productos y Servicios", value="3"),
                                        value=State.owner_billing_afip_concepto,
                                        on_change=State.owner_set_billing_afip_concepto,
                                        class_name=_select,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.label("Umbral Identificación Factura B (ARS)", class_name=_label),
                                    rx.el.input(
                                        type="number",
                                        value=State.owner_billing_ar_threshold,
                                        on_change=State.owner_set_billing_ar_threshold,
                                        class_name=_input,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                class_name="grid grid-cols-1 md:grid-cols-4 gap-3",
                            ),
                            rx.fragment(),
                        ),
                        # Certificados AFIP (AR)
                        rx.cond(
                            State.owner_billing_country == "AR",
                            rx.el.div(
                                rx.el.h4(
                                    "Certificados AFIP",
                                    class_name="text-sm font-semibold text-slate-600",
                                ),
                                rx.el.p(
                                    "Pegue el contenido PEM completo (incluyendo BEGIN/END). "
                                    "Se guardan encriptados al salir del campo.",
                                    class_name=_help,
                                ),
                                rx.el.div(
                                    rx.el.div(
                                        rx.el.label("Certificado X.509 (.pem)", class_name=_label),
                                        rx.el.textarea(
                                            placeholder=rx.cond(
                                                State.owner_billing_cert_display != "",
                                                "****certificado configurado**** — pegue uno nuevo para reemplazar",
                                                "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
                                            ),
                                            on_blur=State.owner_save_afip_certificate,
                                            rows="4",
                                            class_name=_input + " font-mono text-xs resize-y min-h-[80px]",
                                        ),
                                        rx.cond(
                                            State.owner_billing_cert_display != "",
                                            rx.el.span(
                                                "✓ Certificado configurado",
                                                class_name="text-xs text-emerald-600 font-medium",
                                            ),
                                            rx.el.span(
                                                "⚠ Sin certificado",
                                                class_name="text-xs text-amber-600 font-medium",
                                            ),
                                        ),
                                        class_name="flex flex-col gap-1",
                                    ),
                                    rx.el.div(
                                        rx.el.label("Clave Privada RSA (.key)", class_name=_label),
                                        rx.el.textarea(
                                            placeholder=rx.cond(
                                                State.owner_billing_key_display != "",
                                                "****clave configurada**** — pegue una nueva para reemplazar",
                                                "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
                                            ),
                                            on_blur=State.owner_save_afip_private_key,
                                            rows="4",
                                            class_name=_input + " font-mono text-xs resize-y min-h-[80px]",
                                        ),
                                        rx.cond(
                                            State.owner_billing_key_display != "",
                                            rx.el.span(
                                                "✓ Clave privada configurada",
                                                class_name="text-xs text-emerald-600 font-medium",
                                            ),
                                            rx.el.span(
                                                "⚠ Sin clave privada",
                                                class_name="text-xs text-amber-600 font-medium",
                                            ),
                                        ),
                                        class_name="flex flex-col gap-1",
                                    ),
                                    class_name="grid grid-cols-1 md:grid-cols-2 gap-3",
                                ),
                                class_name="space-y-2 p-3 bg-amber-50/50 rounded-lg border border-amber-200/50",
                            ),
                            rx.fragment(),
                        ),
                        # Sincronizar Secuencia AFIP (AR)
                        rx.cond(
                            State.owner_billing_country == "AR",
                            rx.el.div(
                                rx.el.div(
                                    rx.el.span(
                                        "Sincronizar Secuencia AFIP",
                                        class_name="text-sm font-semibold text-slate-700",
                                    ),
                                    rx.el.p(
                                        "Consulta FECompUltimoAutorizado y actualiza los contadores de factura/boleta "
                                        "para evitar rechazos por numeración incorrecta. Usar al migrar desde otro sistema.",
                                        class_name="text-xs text-slate-500 mt-0.5",
                                    ),
                                    class_name="flex-1",
                                ),
                                rx.el.button(
                                    rx.cond(
                                        State.owner_billing_ar_sync_loading,
                                        rx.fragment(
                                            rx.icon("loader-circle", class_name="w-4 h-4 animate-spin"),
                                            rx.el.span("Sincronizando..."),
                                        ),
                                        rx.fragment(
                                            rx.icon("refresh-cw", class_name="w-4 h-4"),
                                            rx.el.span("Sincronizar con AFIP"),
                                        ),
                                    ),
                                    on_click=State.sync_ar_billing_sequence,
                                    disabled=State.owner_billing_ar_sync_loading,
                                    class_name="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0",
                                ),
                                rx.cond(
                                    State.owner_billing_ar_sync_result == "ok",
                                    rx.el.span(
                                        rx.icon("circle-check", class_name="w-3.5 h-3.5 inline mr-1"),
                                        "Sincronizado",
                                        class_name="text-xs text-emerald-600 font-medium",
                                    ),
                                    rx.cond(
                                        State.owner_billing_ar_sync_result == "error",
                                        rx.el.span(
                                            rx.icon("circle-alert", class_name="w-3.5 h-3.5 inline mr-1"),
                                            "Error al sincronizar",
                                            class_name="text-xs text-red-600 font-medium",
                                        ),
                                        rx.fragment(),
                                    ),
                                ),
                                class_name="flex flex-col sm:flex-row items-start sm:items-center gap-3 p-3 bg-indigo-50 border border-indigo-100 rounded-lg",
                            ),
                            rx.fragment(),
                        ),
                        # Series / Numeración
                        rx.el.div(
                            rx.el.h4("Series y Numeración", class_name="text-sm font-semibold text-slate-600"),
                            rx.el.div(
                                rx.el.div(
                                    rx.el.label("Serie Factura", class_name=_label),
                                    rx.el.input(
                                        value=State.owner_billing_serie_factura,
                                        on_change=State.owner_set_billing_serie_factura,
                                        placeholder=rx.cond(
                                            State.owner_billing_country == "AR", "0001", "F001"
                                        ),
                                        class_name=_input,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                rx.el.div(
                                    rx.el.label("Serie Boleta", class_name=_label),
                                    rx.el.input(
                                        value=State.owner_billing_serie_boleta,
                                        on_change=State.owner_set_billing_serie_boleta,
                                        placeholder=rx.cond(
                                            State.owner_billing_country == "AR", "0001", "B001"
                                        ),
                                        class_name=_input,
                                    ),
                                    class_name="flex flex-col gap-1",
                                ),
                                class_name="grid grid-cols-2 gap-3",
                            ),
                            class_name="space-y-2",
                        ),
                        # Cuota mensual
                        rx.el.div(
                            rx.el.label("Límite Mensual de Documentos", class_name=_label),
                            rx.el.input(
                                type="number",
                                value=State.owner_billing_max_limit,
                                on_change=State.owner_set_billing_max_limit,
                                min="0",
                                class_name=_input,
                            ),
                            rx.el.p(
                                "Standard=500, Professional=1000, Enterprise=2000",
                                class_name=_help,
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                        class_name="space-y-4 p-4 max-h-[60vh] overflow-y-auto",
                    ),
                ),
                # Footer
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=State.owner_close_billing_modal,
                        class_name=BUTTON_STYLES["secondary"],
                    ),
                    rx.el.button(
                        rx.cond(
                            State.owner_billing_loading,
                            rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"),
                            rx.icon("save", class_name="h-4 w-4"),
                        ),
                        " Guardar Configuración",
                        on_click=State.owner_save_billing_config,
                        disabled=State.owner_billing_loading,
                        class_name=rx.cond(
                            State.owner_billing_loading,
                            BUTTON_STYLES["disabled"],
                            BUTTON_STYLES["primary"],
                        ),
                    ),
                    class_name="flex items-center justify-end gap-3 p-4 border-t border-slate-200",
                ),
                class_name=(
                    "fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 "
                    "z-[71] w-[95vw] max-w-2xl bg-white rounded-xl shadow-2xl "
                    "border border-slate-200 modal-content"
                ),
            ),
        ),
        rx.fragment(),
    )
