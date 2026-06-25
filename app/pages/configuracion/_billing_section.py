import reflex as rx
from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  CARD_STYLES,
  INPUT_STYLES,
  SELECT_STYLES,
  TYPOGRAPHY,
)


def _failed_doc_row(doc: dict) -> rx.Component:
  """Fila de un documento fiscal fallido con botón de reintento."""
  return rx.el.div(
    rx.el.div(
      rx.el.span(
        doc["full_number"],
        class_name="text-sm font-mono font-medium text-slate-700",
      ),
      rx.el.span(
        doc["receipt_type"],
        class_name="text-xs bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded",
      ),
      rx.el.span(
        rx.cond(
          doc["status"] == "error",
          "Error",
          "Pendiente",
        ),
        class_name=rx.cond(
          doc["status"] == "error",
          "text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded",
          "text-xs bg-amber-100 text-amber-600 px-1.5 py-0.5 rounded",
        ),
      ),
      rx.el.span(
        "Intento " + doc["retry_count"].to_string() + "/3",
        class_name="text-xs text-slate-400",
      ),
      class_name="flex items-center gap-2 flex-wrap",
    ),
    rx.el.div(
      rx.el.span(
        "Venta #" + doc["sale_id"] + " | " + doc["created_at"],
        class_name="text-xs text-slate-400",
      ),
      rx.el.button(
        "Reintentar",
        on_click=State.retry_fiscal_doc(doc["id"]),
        disabled=State.retry_loading,
        class_name="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-600 px-3 py-1 rounded-md disabled:opacity-50",
      ),
      class_name="flex items-center justify-between gap-2",
    ),
    class_name="py-2 space-y-1",
  )


def billing_config_section() -> rx.Component:
  """Sección de configuración de facturación electrónica.

  Vista simplificada para el usuario final: solo datos fiscales
  básicos (RUC, Razón Social, Dirección). Los campos técnicos
  (Nubefact, ambiente, series) se gestionan desde el panel Owner.
  """
  _input = INPUT_STYLES["default"]
  _label = TYPOGRAPHY["label"]
  _help = TYPOGRAPHY["caption"]
  _fk = State.billing_form_key.to_string()
  _badge_active = "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium bg-emerald-50 text-emerald-700 border border-emerald-200"
  _badge_inactive = "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium bg-slate-50 text-slate-500 border border-slate-200"
  _badge_sandbox = "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200"
  _badge_prod = "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200"

  return rx.el.div(
    rx.el.div(
      rx.el.h2(
        "FACTURACION ELECTRONICA", class_name="text-xl font-semibold text-slate-700"
      ),
      rx.el.p(
        "Datos fiscales de tu empresa para la emision de boletas y facturas electronicas.",
        class_name=TYPOGRAPHY["body_secondary"],
      ),
      class_name="space-y-1",
    ),
    rx.el.div(
      # ── Estado + País + Ambiente (badges informativos) ──
      rx.el.div(
        rx.el.div(
          rx.el.label("Estado", class_name=_label),
          rx.cond(
            State.billing_is_active,
            rx.el.span(
              rx.icon("circle-check", class_name="h-3.5 w-3.5"),
              "Activa",
              class_name=_badge_active,
            ),
            rx.el.span(
              rx.icon("circle-x", class_name="h-3.5 w-3.5"),
              "Pendiente de activacion",
              class_name=_badge_inactive,
            ),
          ),
          class_name="flex flex-col gap-1.5",
        ),
        rx.el.div(
          rx.el.label("Pais", class_name=_label),
          rx.el.select(
            rx.el.option("Peru", value="PE"),
            rx.el.option("Argentina", value="AR"),
            value=State.billing_country,
            on_change=State.set_billing_country,
            key=_fk + "-bcountry",
            class_name=SELECT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label("Ambiente", class_name=_label),
          rx.cond(
            State.billing_environment == "production",
            rx.el.span(
              rx.icon("shield-check", class_name="h-3 w-3"),
              "Produccion",
              class_name=_badge_prod,
            ),
            rx.el.span(
              rx.icon("flask-conical", class_name="h-3 w-3"),
              "Sandbox (pruebas)",
              class_name=_badge_sandbox,
            ),
          ),
          class_name="flex flex-col gap-1.5",
        ),
        class_name="grid grid-cols-1 md:grid-cols-3 gap-4",
      ),
      # ── Datos fiscales del negocio ──
      rx.el.div(
        rx.el.div(
          rx.el.label(
            rx.cond(State.billing_country == "AR", "CUIT", "RUC"),
            class_name=_label,
          ),
          rx.el.input(
            default_value=State.billing_tax_id,
            on_blur=State.set_billing_tax_id,
            placeholder=rx.cond(
              State.billing_country == "AR", "Ej: 30716549877", "Ej: 20123456789"
            ),
            key=_fk + "-btaxid",
            class_name=_input,
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label("Razon Social", class_name=_label),
          rx.el.input(
            default_value=State.billing_business_name,
            on_blur=State.set_billing_business_name,
            placeholder="Ej: MI EMPRESA SAC",
            key=_fk + "-bbizname",
            class_name=_input,
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label("Direccion Fiscal", class_name=_label),
          rx.el.input(
            default_value=State.billing_business_address,
            on_blur=State.set_billing_business_address,
            placeholder="Ej: Av. Principal 123",
            key=_fk + "-bbizaddr",
            class_name=_input,
          ),
          class_name="flex flex-col gap-1 md:col-span-2",
        ),
        class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
      ),
      # ── API de Consulta RUC/DNI (solo Perú) ──
      rx.cond(
        State.billing_country == "PE",
        rx.el.div(
          rx.el.h3(
            "API de Consulta RUC/DNI",
            class_name="text-base font-semibold text-slate-600 border-b pb-1",
          ),
          rx.el.div(
            rx.el.div(
              rx.el.label("URL de API de Consulta", class_name=_label),
              rx.el.input(
                default_value=State.billing_lookup_api_url,
                on_blur=State.set_lookup_api_url,
                placeholder="https://api.apis.net.pe/v2",
                key=_fk + "-blookupurl",
                class_name=_input,
              ),
              rx.el.p(
                "Endpoint para consultar RUC y DNI (apis.net.pe)",
                class_name=_help,
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.label("Token de Consulta", class_name=_label),
              rx.el.input(
                default_value=State.billing_lookup_api_token_display,
                on_blur=State.save_lookup_api_token,
                placeholder="Bearer token",
                type="password",
                key=_fk + "-blookuptoken",
                class_name=_input,
              ),
              rx.el.p(
                "Se guarda encriptado al salir del campo.",
                class_name=_help,
              ),
              class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
          ),
          class_name="space-y-3",
        ),
        rx.fragment(),
      ),
      # ── Configuración Argentina (solo AR) ──
      rx.cond(
        State.billing_country == "AR",
        rx.el.div(
          rx.el.h3(
            "Configuracion Fiscal Argentina",
            class_name="text-base font-semibold text-slate-600 border-b pb-1",
          ),
          rx.el.div(
            rx.el.div(
              rx.el.label("Condicion IVA del Emisor", class_name=_label),
              rx.el.select(
                rx.el.option("Responsable Inscripto", value="RI"),
                rx.el.option("Monotributo", value="monotributo"),
                rx.el.option("Exento", value="exento"),
                value=State.billing_emisor_iva,
                on_change=State.set_emisor_iva,
                key=_fk + "-bemisoriva",
                class_name=SELECT_STYLES["default"],
              ),
              rx.el.p(
                "Determina el tipo de comprobante (A/B/C)",
                class_name=_help,
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.label("Umbral Factura B (AFIP)", class_name=_label),
              rx.el.input(
                default_value=State.billing_ar_threshold,
                on_blur=State.set_ar_threshold,
                placeholder="68782.00",
                type="number",
                key=_fk + "-barthreshold",
                class_name=_input,
              ),
              rx.el.p(
                "Monto a partir del cual se requiere identificar al comprador en Factura B",
                class_name=_help,
              ),
              class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
          ),
          # ── Wizard de certificados AFIP ──────────────────────────
          rx.el.div(
            rx.el.h4("Certificados AFIP", class_name="text-sm font-semibold text-slate-600 border-b border-slate-100 pb-1"),
            # ── Guía de 3 pasos ──
            rx.el.div(
              # Paso 1
              rx.el.div(
                rx.el.div(
                  rx.el.span("1", class_name="text-xs font-bold text-white"),
                  class_name="w-5 h-5 rounded-full bg-indigo-500 flex items-center justify-center shrink-0",
                ),
                rx.el.div(
                  rx.el.p("Genera tu clave privada RSA", class_name="text-xs font-semibold text-slate-700"),
                  rx.el.p("En tu terminal ejecuta:", class_name="text-xs text-slate-500 mt-0.5"),
                  rx.el.code(
                    "openssl genrsa -out mi_clave.key 2048",
                    class_name="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded font-mono block mt-1",
                  ),
                  class_name="flex flex-col",
                ),
                class_name="flex items-start gap-2",
              ),
              # Paso 2
              rx.el.div(
                rx.el.div(
                  rx.el.span("2", class_name="text-xs font-bold text-white"),
                  class_name="w-5 h-5 rounded-full bg-indigo-500 flex items-center justify-center shrink-0",
                ),
                rx.el.div(
                  rx.el.p("Solicita el certificado en AFIP", class_name="text-xs font-semibold text-slate-700"),
                  rx.el.p(
                    "Ingresa al portal AFIP con tu CUIT → Administración de Certificados Digitales → Nuevo Certificado → sube tu clave pública (.csr).",
                    class_name="text-xs text-slate-500 mt-0.5",
                  ),
                  rx.el.a(
                    "→ Portal AFIP (wsass.afip.gov.ar)",
                    href="https://wsass.afip.gov.ar/wsass/portal/main.aspx",
                    target="_blank",
                    rel="noopener noreferrer",
                    class_name="text-xs text-indigo-600 hover:underline mt-0.5 inline-block",
                  ),
                  class_name="flex flex-col",
                ),
                class_name="flex items-start gap-2",
              ),
              # Paso 3
              rx.el.div(
                rx.el.div(
                  rx.el.span("3", class_name="text-xs font-bold text-white"),
                  class_name=rx.cond(
                    (State.billing_cert_status == "configurado") & (State.billing_key_status == "configurado"),
                    "w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center shrink-0",
                    "w-5 h-5 rounded-full bg-indigo-500 flex items-center justify-center shrink-0",
                  ),
                ),
                rx.el.div(
                  rx.el.p("Pega los archivos descargados abajo", class_name="text-xs font-semibold text-slate-700"),
                  rx.el.p("Pega el contenido completo del .pem y .key en los campos de abajo y sal de cada campo para guardar.", class_name="text-xs text-slate-500 mt-0.5"),
                  class_name="flex flex-col",
                ),
                class_name="flex items-start gap-2",
              ),
              class_name="flex flex-col gap-3 bg-slate-50 border border-slate-100 rounded-lg p-3 text-xs",
            ),
            # ── Campos de carga ──
            rx.el.div(
              # Certificado X.509
              rx.el.div(
                rx.el.label("Certificado X.509 (.crt / .pem)", class_name=_label),
                rx.cond(
                  State.billing_cert_status == "configurado",
                  rx.el.div(
                    rx.el.div(
                      rx.icon("circle-check", class_name="h-4 w-4 text-emerald-500 shrink-0"),
                      rx.el.span("Certificado configurado", class_name="text-sm font-medium text-emerald-700"),
                      rx.cond(
                        State.billing_cert_days_remaining >= 0,
                        rx.cond(
                          State.billing_cert_days_remaining <= 30,
                          rx.el.span(
                            rx.icon("triangle-alert", class_name="h-3 w-3 inline mr-0.5"),
                            "Expira en ",
                            State.billing_cert_days_remaining,
                            " días",
                            class_name="text-xs text-amber-600 font-medium ml-2",
                          ),
                          rx.el.span(
                            "Válido hasta ",
                            State.billing_cert_not_after,
                            class_name="text-xs text-slate-400 ml-2",
                          ),
                        ),
                        rx.fragment(),
                      ),
                      class_name="flex items-center gap-1 flex-wrap",
                    ),
                    rx.cond(
                      State.billing_cert_subject != "",
                      rx.el.p(
                        rx.el.span("CN: ", class_name="font-medium"),
                        State.billing_cert_subject,
                        class_name="text-xs text-slate-500 font-mono mt-0.5",
                      ),
                      rx.fragment(),
                    ),
                    rx.cond(
                      State.billing_cert_issuer != "",
                      rx.el.p(
                        rx.el.span("Emisor: ", class_name="font-medium"),
                        State.billing_cert_issuer,
                        class_name="text-xs text-slate-400 font-mono",
                      ),
                      rx.fragment(),
                    ),
                    class_name="flex flex-col gap-0.5 mb-1",
                  ),
                  rx.fragment(),
                ),
                rx.el.textarea(
                  placeholder="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
                  rows=4,
                  on_blur=State.save_afip_certificate,
                  key=_fk + "-bcert",
                  class_name=_input + " font-mono text-xs resize-none",
                ),
                rx.el.p(
                  "Pega el contenido completo del archivo .crt o .pem descargado de AFIP.",
                  class_name=_help,
                ),
                class_name="flex flex-col gap-1",
              ),
              # Clave Privada RSA
              rx.el.div(
                rx.el.label("Clave Privada RSA (.key)", class_name=_label),
                rx.cond(
                  State.billing_key_status == "configurado",
                  rx.el.div(
                    rx.icon("circle-check", class_name="h-4 w-4 text-emerald-500 shrink-0"),
                    rx.el.span("Clave privada configurada (RSA)", class_name="text-sm font-medium text-emerald-700"),
                    class_name="flex items-center gap-1 mb-1",
                  ),
                  rx.fragment(),
                ),
                rx.el.textarea(
                  placeholder="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
                  rows=4,
                  on_blur=State.save_afip_private_key,
                  key=_fk + "-bkey",
                  class_name=_input + " font-mono text-xs resize-none",
                ),
                rx.el.p(
                  "Nunca se muestra en pantalla. Se guarda encriptado (Fernet) al salir del campo.",
                  class_name=_help,
                ),
                class_name="flex flex-col gap-1",
              ),
              class_name="grid grid-cols-1 gap-4",
            ),
            class_name="space-y-3",
          ),
          class_name="space-y-3",
        ),
        rx.fragment(),
      ),
      # ── Series / Numeración (solo lectura) ──
      rx.cond(
        State.billing_config_exists,
        rx.el.div(
          rx.el.h3(
            "Series y Numeracion",
            class_name="text-base font-semibold text-slate-600 border-b pb-1",
          ),
          rx.el.div(
            rx.el.div(
              rx.el.label("Serie Factura", class_name=_label),
              rx.el.span(
                State.billing_serie_factura,
                class_name="text-sm font-mono text-slate-600 h-10 flex items-center px-3 bg-slate-50 rounded-md border border-slate-100",
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.label("Serie Boleta", class_name=_label),
              rx.el.span(
                State.billing_serie_boleta,
                class_name="text-sm font-mono text-slate-600 h-10 flex items-center px-3 bg-slate-50 rounded-md border border-slate-100",
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.label("Ult. Nro Factura", class_name=_label),
              rx.el.span(
                State.billing_seq_factura.to_string(),
                class_name="text-sm font-mono text-slate-600 h-10 flex items-center px-3 bg-slate-50 rounded-md border border-slate-100",
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.label("Ult. Nro Boleta", class_name=_label),
              rx.el.span(
                State.billing_seq_boleta.to_string(),
                class_name="text-sm font-mono text-slate-600 h-10 flex items-center px-3 bg-slate-50 rounded-md border border-slate-100",
              ),
              class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-2 md:grid-cols-4 gap-4",
          ),
          class_name="space-y-3",
        ),
        rx.fragment(),
      ),
      # ── Cuota mensual ──
      rx.cond(
        State.billing_config_exists,
        rx.el.div(
          rx.el.div(
            rx.el.span("Documentos emitidos este mes: ", class_name="text-sm text-slate-600"),
            rx.el.span(
              State.billing_current_count.to_string(),
              class_name="text-sm font-semibold",
            ),
            rx.el.span(" / ", class_name="text-sm text-slate-400"),
            rx.el.span(
              State.billing_max_limit.to_string(),
              class_name="text-sm font-semibold text-indigo-600",
            ),
            class_name="flex items-center gap-1",
          ),
          class_name="p-3 bg-slate-50 rounded-lg",
        ),
        rx.fragment(),
      ),
      # ── Info: si no está activa ──
      rx.cond(
        ~State.billing_is_active,
        rx.el.div(
          rx.el.div(
            rx.icon("info", class_name="h-4 w-4 text-indigo-500 shrink-0 mt-0.5"),
            rx.el.div(
              rx.el.p(
                "Para activar la facturacion electronica, completa tus datos fiscales y guarda.",
                class_name=TYPOGRAPHY["body"],
              ),
              rx.el.p(
                "El equipo de TuWaykiApp configurara la conexion con el servicio de emision (Nubefact/AFIP) y activara tu cuenta.",
                class_name=f"{TYPOGRAPHY['caption']} mt-1",
              ),
            ),
            class_name="flex gap-2",
          ),
          class_name="p-3 bg-indigo-50 rounded-lg border border-indigo-100",
        ),
        rx.fragment(),
      ),
      # ── Guardar ──
      rx.el.div(
        rx.el.p(
          "Estos datos se usan para la emision de comprobantes electronicos.",
          class_name=_help,
        ),
        rx.el.div(
          rx.el.button(
            "Guardar Datos Fiscales",
            on_click=State.save_billing_config,
            class_name=f"{BUTTON_STYLES['primary']} w-full sm:w-auto min-h-[44px]",
          ),
          class_name="flex justify-end sm:justify-start",
        ),
        class_name="flex flex-col sm:flex-row sm:items-center justify-between gap-3",
      ),
      class_name=f"{CARD_STYLES['default']} space-y-5",
    ),
    # ── Documentos fiscales con errores ──
    rx.cond(
      State.billing_config_exists,
      rx.el.div(
        rx.el.div(
          rx.el.h3(
            "Documentos Fiscales Pendientes / Con Error",
            class_name="text-base font-semibold text-slate-700",
          ),
          rx.el.button(
            "Actualizar lista",
            on_click=State.load_failed_fiscal_docs,
            class_name="text-xs bg-slate-100 hover:bg-slate-200 text-slate-600 px-3 py-1.5 rounded-md",
          ),
          class_name="flex items-center justify-between",
        ),
        rx.cond(
          State.failed_fiscal_docs.length() > 0,
          rx.el.div(
            rx.foreach(
              State.failed_fiscal_docs,
              _failed_doc_row,
            ),
            class_name="divide-y divide-slate-100",
          ),
          rx.el.p(
            "No hay documentos con errores.",
            class_name="text-sm text-slate-500 text-center py-4",
          ),
        ),
        on_mount=State.load_failed_fiscal_docs,
        class_name=f"{CARD_STYLES['default']} space-y-3",
      ),
      rx.fragment(),
    ),
    on_mount=State.load_billing_config,
    class_name="space-y-4",
  )
