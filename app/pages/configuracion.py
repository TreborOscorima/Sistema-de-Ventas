import reflex as rx
from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  CARD_STYLES,
  INPUT_STYLES,
  SELECT_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  action_button,
  limit_reached_modal,
  modal_container,
  pricing_modal,
  toggle_switch,
  page_title,
  permission_guard,
)

CONFIG_SECTIONS: list[dict[str, str]] = [
  {
    "key": "empresa",
    "label": "Datos de Empresa",
    "description": "Informacion fiscal y de contacto",
    "icon": "building",
  },
  {
    "key": "sucursales",
    "label": "Sucursales",
    "description": "Gestion de sedes y accesos",
    "icon": "map-pin",
  },
  {
    "key": "usuarios",
    "label": "Gestion de Usuarios",
    "description": "Roles, accesos y credenciales",
    "icon": "users",
  },
  {
    "key": "monedas",
    "label": "Selector de Monedas",
    "description": "Moneda activa y lista disponible",
    "icon": "coins",
  },
  {
    "key": "unidades",
    "label": "Unidades de Medida",
    "description": "Unidades visibles en inventario y ventas",
    "icon": "ruler",
  },
  {
    "key": "pagos",
    "label": "Metodos de Pago",
    "description": "Botones y opciones que veras en Venta",
    "icon": "credit-card",
  },
  {
    "key": "facturacion",
    "label": "Facturacion Electronica",
    "description": "Boletas y facturas SUNAT / AFIP",
    "icon": "file-text",
  },
  {
    "key": "suscripcion",
    "label": "Suscripcion",
    "description": "Estado del plan y consumo",
    "icon": "sparkles",
  },
]

PAYMENT_KIND_LABELS: dict[str, str] = {
  "cash": "Efectivo",
  "debit": "Tarjeta de Débito",
  "credit": "Tarjeta de Crédito",
  "yape": "Billetera Digital (Yape)",
  "plin": "Billetera Digital (Plin)",
  "transfer": "Transferencia Bancaria",
  "mixed": "Pago Mixto",
  "other": "Otro",
  "card": "Tarjeta de Crédito",
  "wallet": "Billetera Digital (Yape)",
}

PRIVILEGE_SECTIONS: list[tuple[str, list[tuple[str, str]]]] = [
  (
    "Ingresos",
    [
      ("Ver Ingresos", "view_ingresos"),
      ("Crear Ingresos", "create_ingresos"),
    ],
  ),
  (
    "Compras y Proveedores",
    [
      ("Ver Compras", "view_compras"),
      ("Gestionar Proveedores", "manage_proveedores"),
    ],
  ),
  (
    "Ventas y Caja",
    [
      ("Ver Ventas", "view_ventas"),
      ("Crear Ventas", "create_ventas"),
      ("Ver Gestion de Caja", "view_cashbox"),
      ("Abrir/Cerrar Caja", "manage_cashbox"),
      ("Eliminar Ventas", "delete_sales"),
    ],
  ),
  (
    "Inventario",
    [
      ("Ver Inventario", "view_inventario"),
      ("Editar Inventario", "edit_inventario"),
    ],
  ),
  (
    "Historial y Reportes",
    [
      ("Ver Historial", "view_historial"),
      ("Exportar Datos", "export_data"),
    ],
  ),
  (
    "Servicios",
    [
      ("Ver Servicios", "view_servicios"),
      ("Gestionar Reservas", "manage_reservations"),
    ],
  ),
  (
    "Clientes y Cuentas",
    [
      ("Ver Clientes", "view_clientes"),
      ("Gestionar Clientes", "manage_clientes"),
      ("Ver Cuentas Ctes.", "view_cuentas"),
      ("Gestionar Deudas", "manage_cuentas"),
    ],
  ),
  (
    "Administracion",
    [
      ("Gestionar Usuarios", "manage_users"),
      ("Configuracion Global", "manage_config"),
    ],
  ),
]

PRIVILEGE_LABELS: list[tuple[str, str]] = [
  (label, key) for _, items in PRIVILEGE_SECTIONS for label, key in items
]


def privilege_switch(label: str, privilege: str) -> rx.Component:
  return rx.el.div(
    rx.el.label(label, class_name=TYPOGRAPHY["label"]),
    rx.el.div(
      toggle_switch(
        checked=State.new_user_data["privileges"][privilege],
        on_change=lambda value: State.toggle_privilege(privilege),
      ),
    ),
    class_name=(
      "flex items-center justify-between rounded-md border border-slate-200 "
      "bg-white px-3 py-2"
    ),
  )


def privilege_section(title: str, privileges: list[tuple[str, str]]) -> rx.Component:
  return rx.el.div(
    rx.el.p(title, class_name=TYPOGRAPHY["label_secondary"]),
    rx.el.div(
      *[privilege_switch(label, key) for label, key in privileges],
      class_name="grid grid-cols-1 md:grid-cols-2 gap-3",
    ),
    class_name="p-4 rounded-xl bg-white space-y-3 border border-slate-200",
  )


def privilege_badges(user: rx.Var[dict]) -> rx.Component:
  return rx.el.div(
    *[
      rx.cond(
        user["privileges"][key],
        rx.el.span(
          label,
          class_name="px-2 py-1 text-xs font-semibold rounded-md bg-indigo-50 text-indigo-700 border border-indigo-100",
        ),
        rx.fragment(),
      )
      for label, key in PRIVILEGE_LABELS
    ],
    class_name="flex flex-wrap gap-2 w-full",
  )


def config_nav() -> rx.Component:
  return rx.el.div(
    rx.el.p(
      "Submenus de configuracion",
      class_name="text-sm font-semibold text-slate-700",
    ),
    rx.el.div(
      *[
        rx.link(
          rx.el.div(
            rx.icon(section["icon"], class_name="h-5 w-5"),
            rx.el.div(
              rx.el.span(section["label"], class_name="font-semibold"),
              rx.el.span(
                section["description"],
                class_name=TYPOGRAPHY["caption"],
              ),
              class_name="flex flex-col items-start",
            ),
            class_name="flex items-center gap-3",
          ),
          href=f"/configuracion?tab={section['key']}",
          underline="none",
          class_name=rx.cond(
            State.config_tab == section["key"],
            "w-full text-left bg-indigo-100 text-indigo-700 border border-indigo-200 px-3 py-2 rounded-md shadow-sm",
            "w-full text-left bg-white text-slate-700 border px-3 py-2 rounded-md hover:bg-slate-50",
          ),
        )
        for section in CONFIG_SECTIONS
      ],
      class_name="flex flex-col gap-2",
    ),
    class_name=f"{CARD_STYLES['compact']} space-y-3",
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
        "Intento " + doc["retry_count"] + "/3",
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
                on_blur=State.save_lookup_api_token,  # guarda encriptado al salir del campo
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
                  rx.el.p("Generá tu clave privada RSA", class_name="text-xs font-semibold text-slate-700"),
                  rx.el.p("En tu terminal ejecutá:", class_name="text-xs text-slate-500 mt-0.5"),
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
                  rx.el.p("Solicitá el certificado en AFIP", class_name="text-xs font-semibold text-slate-700"),
                  rx.el.p(
                    "Ingresá al portal AFIP con tu CUIT → Administración de Certificados Digitales → Nuevo Certificado → subí tu clave pública (.csr).",
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
                  rx.el.p("Pegá los archivos descargados abajo", class_name="text-xs font-semibold text-slate-700"),
                  rx.el.p("Pegá el contenido completo del .pem y .key en los campos de abajo y salí de cada campo para guardar.", class_name="text-xs text-slate-500 mt-0.5"),
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
                            f"Expira en {State.billing_cert_days_remaining} días",
                            class_name="text-xs text-amber-600 font-medium ml-2",
                          ),
                          rx.el.span(
                            f"Válido hasta {State.billing_cert_not_after}",
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
                  "Pegá el contenido completo del archivo .crt o .pem descargado de AFIP.",
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


def company_settings_section() -> rx.Component:
  """Sección de configuración de datos de empresa."""
  return rx.el.div(
    rx.el.div(
      rx.el.h2(
        "DATOS DE MI EMPRESA", class_name="text-xl font-semibold text-slate-700"
      ),
      rx.el.p(
        "Actualiza la informacion que aparece en recibos y reportes.",
        class_name=TYPOGRAPHY["body_secondary"],
      ),
      class_name="space-y-1",
    ),
    rx.el.div(
      rx.el.div(
        rx.el.div(
          rx.el.label(
            "Razón Social / Nombre de Empresa", class_name=TYPOGRAPHY["label"]
          ),
          rx.el.input(
            default_value=State.company_name,
            on_blur=State.set_company_name,
            placeholder="Ej: Tu Empresa SAC",
            key=State.company_form_key.to_string() + "-company_name",
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label("N° de Registro de Empresa", class_name=TYPOGRAPHY["label"]),
          rx.el.input(
            default_value=State.ruc,
            on_blur=State.set_ruc,
            placeholder="N° de Registro de Empresa",
            key=State.company_form_key.to_string() + "-ruc",
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label("Dirección Fiscal", class_name=TYPOGRAPHY["label"]),
          rx.el.input(
            default_value=State.address,
            on_blur=State.set_address,
            placeholder="Ej: Av. Principal 123",
            key=State.company_form_key.to_string() + "-address",
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1 md:col-span-2",
        ),
        rx.el.div(
          rx.el.label("Teléfono / Celular", class_name=TYPOGRAPHY["label"]),
          rx.el.input(
            default_value=State.phone,
            on_blur=State.set_phone,
            placeholder="Ej: 999 999 999",
            key=State.company_form_key.to_string() + "-phone",
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label("Zona Horaria (IANA)", class_name=TYPOGRAPHY["label"]),
          rx.el.select(
            rx.el.option(
              rx.cond(
                State.timezone_placeholder != "",
                "Usar zona del país (" + State.timezone_placeholder + ")",
                "Usar zona del país",
              ),
              value="",
            ),
            rx.foreach(
              State.timezone_options,
              lambda tz: rx.el.option(tz, value=tz),
            ),
            value=State.timezone,
            on_change=State.set_timezone,
            key=State.company_form_key.to_string() + "-timezone",
            class_name=SELECT_STYLES["default"],
          ),
          rx.el.p(
            "Selecciona una zona horaria IANA. Deja en blanco para usar la zona del país.",
            class_name=TYPOGRAPHY["caption"],
          ),
          class_name="flex flex-col gap-1",
        ),
        # Rubro del negocio
        rx.el.div(
          rx.el.label(
            "Rubro del Negocio", class_name=TYPOGRAPHY["label"]
          ),
          rx.el.select(
            rx.el.option("General (Multi-rubro)", value="general"),
            rx.el.option("Bodega / Kiosko", value="bodega"),
            rx.el.option("Ferreteria", value="ferreteria"),
            rx.el.option("Farmacia", value="farmacia"),
            rx.el.option("Tienda de Ropa", value="ropa"),
            rx.el.option("Jugueteria", value="jugueteria"),
            rx.el.option("Restaurante / Cafe", value="restaurante"),
            rx.el.option("Supermercado", value="supermercado"),
            value=State.selected_business_vertical,
            on_change=State.set_business_vertical,
            class_name=SELECT_STYLES["default"],
          ),
          rx.el.p(
            "Define el tipo de negocio para adaptar la interfaz del punto de venta.",
            class_name=TYPOGRAPHY["caption"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label(
            "Mensaje en Recibo/Ticket", class_name=TYPOGRAPHY["label"]
          ),
          rx.el.input(
            default_value=State.footer_message,
            on_blur=State.set_footer_message,
            placeholder="Ej: Gracias por su compra",
            key=State.company_form_key.to_string() + "-footer_message",
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1 md:col-span-2",
        ),
        rx.el.div(
          rx.el.label("Papel de Impresion", class_name=TYPOGRAPHY["label"]),
          rx.el.select(
            rx.el.option("80 mm (default)", value="80"),
            rx.el.option("58 mm", value="58"),
            value=State.receipt_paper,
            on_change=State.set_receipt_paper,
            class_name=SELECT_STYLES["default"],
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.label(
            "Ancho de Recibo (opcional)", class_name=TYPOGRAPHY["label"]
          ),
          rx.el.input(
            default_value=State.receipt_width,
            on_blur=State.set_receipt_width,
            placeholder="Ej: 42",
            type_="number",
            min="24",
            max="64",
            key=State.company_form_key.to_string() + "-receipt_width",
            class_name=INPUT_STYLES["default"],
          ),
          rx.el.p(
            "Deja en blanco para usar el ancho automatico.",
            class_name=TYPOGRAPHY["caption"],
          ),
          class_name="flex flex-col gap-1",
        ),
        class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
      ),
      rx.el.div(
        rx.el.p(
          "Estos datos se muestran en recibos y reportes.",
          class_name=TYPOGRAPHY["caption"],
        ),
        rx.el.div(
          rx.el.button(
            "Guardar Configuracion",
            on_click=State.save_settings,
            class_name=f"{BUTTON_STYLES['primary']} w-full sm:w-auto min-h-[44px]",
          ),
          class_name="flex justify-end sm:justify-start",
        ),
        class_name="flex flex-col sm:flex-row sm:items-center justify-between gap-3",
      ),
            class_name=f"{CARD_STYLES['default']} space-y-4",
    ),
    class_name="space-y-4",
  )


def _usage_meter(
  title: str,
  icon: str,
  used: rx.Var,
  limit_label: rx.Var | str,
  percent: rx.Var,
  is_full: rx.Var,
  is_unlimited: rx.Var,
) -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.div(
        rx.icon(icon, class_name="h-5 w-5 text-slate-600"),
        class_name="p-2 rounded-lg bg-slate-100",
      ),
      rx.el.div(
        rx.el.p(title, class_name=TYPOGRAPHY["label_secondary"]),
        rx.el.p(
          rx.el.span(used, class_name="tabular-nums"),
          rx.el.span(" / ", class_name="text-slate-400"),
          rx.el.span(limit_label, class_name="tabular-nums"),
          class_name=rx.cond(
            is_full,
            "text-sm font-semibold text-red-600",
            "text-sm font-semibold text-slate-800",
          ),
        ),
        class_name="flex flex-col gap-1",
      ),
      class_name="flex items-center gap-3",
    ),
    rx.cond(
      is_unlimited,
      rx.el.p("Ilimitado", class_name="text-xs font-semibold text-emerald-600"),
      rx.progress(
        value=percent,
        max=100,
        color_scheme=rx.cond(is_full, "red", "indigo"),
        class_name="h-2",
      ),
    ),
    class_name=f"{CARD_STYLES['compact']} space-y-3",
  )


def _upgrade_plan_modal() -> rx.Component:
  return modal_container(
    is_open=State.show_upgrade_modal,
    on_close=State.close_upgrade_modal,
    title="Contactar a Ventas",
    description="Conversemos para encontrar el plan que mejor se adapte a tu negocio.",
    children=[
      rx.el.div(
        rx.el.p(
          "Nuestro equipo puede ayudarte a ampliar límites y activar módulos adicionales.",
          class_name="text-sm text-slate-600",
        ),
        class_name="space-y-2",
      )
    ],
    footer=rx.el.div(
      action_button("Cerrar", State.close_upgrade_modal, variant="secondary"),
      action_button("Contactar a Ventas", State.contact_sales_whatsapp, variant="primary"),
      class_name="flex flex-col sm:flex-row justify-end gap-2",
    ),
    max_width="max-w-md",
  )


def subscription_section() -> rx.Component:
  """Sección de información y estado de suscripción."""
  return rx.el.div(
    rx.el.div(
      rx.el.h2("MI SUSCRIPCION", class_name="text-xl font-semibold text-slate-700"),
      rx.el.p(
        "Consulta tu plan actual y el consumo de recursos.",
        class_name=TYPOGRAPHY["body_secondary"],
      ),
      class_name="space-y-1",
    ),
    rx.card(
      rx.el.div(
        rx.el.div(
          rx.el.div(
            rx.el.span(
              State.subscription_snapshot["plan_display"],
              class_name="text-sm font-semibold text-slate-800",
            ),
            rx.badge(
              State.subscription_snapshot["status_label"],
              color_scheme=State.subscription_snapshot["status_tone"],
            ),
            class_name="flex items-center gap-2",
          ),
          rx.el.p(
            rx.cond(
              State.subscription_snapshot["is_trial"],
              rx.el.span(
                "Trial · ",
                State.subscription_snapshot["trial_days_left"],
                " días restantes",
              ),
              rx.el.span("Plan activo"),
            ),
            class_name="text-sm text-slate-600",
          ),
          rx.cond(
            State.subscription_snapshot["is_trial"],
            rx.el.p(
              rx.el.span("Vence: ", class_name="text-slate-500"),
              State.subscription_snapshot["trial_ends_on"],
              class_name=TYPOGRAPHY["caption"],
            ),
            rx.fragment(),
          ),
          class_name="flex flex-col gap-1",
        ),
        class_name="flex items-start justify-between",
      ),
      class_name=CARD_STYLES["compact"],
    ),
    rx.el.div(
      _usage_meter(
        "Sucursales",
        "store",
        State.subscription_snapshot["branches_used"],
        State.subscription_snapshot["branches_limit_label"],
        State.subscription_snapshot["branches_percent"],
        State.subscription_snapshot["branches_full"],
        State.subscription_snapshot["branches_unlimited"],
      ),
      _usage_meter(
        "Usuarios",
        "user",
        State.subscription_snapshot["users_used"],
        State.subscription_snapshot["users_limit_label"],
        State.subscription_snapshot["users_percent"],
        State.subscription_snapshot["users_full"],
        State.subscription_snapshot["users_unlimited"],
      ),
      class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
    ),
    rx.el.div(
      action_button(
        "Contactar a Ventas",
        State.contact_sales_whatsapp,
        variant="secondary",
        icon="message-circle",
      ),
      action_button(
        "Mejorar Plan",
        State.open_pricing_modal,
        variant="primary",
        icon="rocket",
      ),
      class_name="flex flex-col sm:flex-row justify-end gap-2",
    ),
    class_name="space-y-4",
  )


def user_form() -> rx.Component:
  return rx.radix.primitives.dialog.root(
    rx.radix.primitives.dialog.trigger(
      rx.el.button(
        "Crear Nuevo Usuario",
        on_click=State.show_create_user_form,
        class_name=f"{BUTTON_STYLES['primary']} w-full sm:w-auto mb-6",
      ),
      as_child=True,
    ),
    rx.radix.primitives.dialog.portal(
      rx.radix.primitives.dialog.overlay(
        class_name="fixed inset-0 bg-black/40 backdrop-blur-sm modal-overlay"
      ),
        rx.radix.primitives.dialog.content(
          rx.radix.primitives.dialog.title(
            rx.cond(State.editing_user, "Editar Usuario", "Crear Nuevo Usuario"),
            class_name=f"{TYPOGRAPHY['section_title']} flex-shrink-0",
          ),
          rx.divider(color="slate-100"),
          rx.el.div(
          rx.el.div(
            rx.el.label("Nombre de Usuario", class_name=TYPOGRAPHY["label"]),
            rx.el.input(
              default_value=State.new_user_data["username"],
              on_blur=lambda v: State.handle_new_user_change(
                "username", v
              ),
              is_disabled=rx.cond(State.editing_user, True, False),
              class_name=f"{INPUT_STYLES['default']} mt-1",
            ),
            class_name="mb-4",
          ),
          rx.el.div(
            rx.el.label("Correo", class_name=TYPOGRAPHY["label"]),
            rx.el.input(
              type="email",
              placeholder="usuario@empresa.com",
              default_value=State.new_user_data["email"],
              on_blur=lambda v: State.handle_new_user_change(
                "email", v
              ),
              class_name=f"{INPUT_STYLES['default']} mt-1",
            ),
            class_name="mb-4",
          ),
          rx.el.div(
            rx.el.label("Rol", class_name=TYPOGRAPHY["label"]),
            rx.el.select(
              rx.foreach(
                State.roles,
                lambda role: rx.el.option(role, value=role),
              ),
              value=State.new_user_data["role"],
              on_change=lambda v: State.handle_new_user_change("role", v),
              class_name=f"{SELECT_STYLES['default']} mt-1",
            ),
            rx.el.p(
              "Los privilegios se cargan de acuerdo al rol seleccionado. Puedes afinar y guardar nuevos roles debajo.",
              class_name=f"{TYPOGRAPHY['caption']} mt-2",
            ),
            class_name="mb-4",
          ),
          rx.el.div(
            rx.el.label("Crear nuevo rol", class_name=TYPOGRAPHY["label"]),
            rx.el.div(
              rx.el.input(
                placeholder="Ej: Administrador, Cajero, Auditor",
                default_value=State.new_role_name,
                on_blur=lambda v: State.update_new_role_name(v),
                class_name=f"flex-1 {INPUT_STYLES['default']}",
              ),
              rx.el.button(
                "Crear rol con estos privilegios",
                on_click=State.create_role_from_current_privileges,
                class_name=f"{BUTTON_STYLES['secondary']} whitespace-nowrap",
              ),
              class_name="flex flex-col sm:flex-row sm:items-center gap-3 mt-2",
            ),
            class_name="mb-4",
          ),
          rx.el.div(
            rx.el.label("Contraseña", class_name=TYPOGRAPHY["label"]),
            rx.el.div(
              rx.el.input(
                type=rx.cond(
                  State.show_user_form_password,
                  "text",
                  "password",
                ),
                placeholder=rx.cond(
                  State.editing_user,
                  "Dejar en blanco para no cambiar",
                  "",
                ),
                default_value=State.new_user_data["password"],
                on_blur=lambda v: State.handle_new_user_change(
                  "password", v
                ),
                class_name=f"{INPUT_STYLES['default']} pr-11",
              ),
              rx.el.button(
                rx.cond(
                  State.show_user_form_password,
                  rx.icon("eye-off", class_name="h-4 w-4"),
                  rx.icon("eye", class_name="h-4 w-4"),
                ),
                type="button",
                on_click=State.toggle_user_form_password_visibility,
                class_name=(
                  "absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-7 w-7 "
                  "items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 "
                  "hover:text-slate-700 transition-colors duration-150"
                ),
                aria_label=rx.cond(
                  State.show_user_form_password,
                  "Ocultar contraseña",
                  "Mostrar contraseña",
                ),
                title=rx.cond(
                  State.show_user_form_password,
                  "Ocultar contraseña",
                  "Mostrar contraseña",
                ),
              ),
              class_name="relative mt-1",
            ),
            class_name="mb-4",
          ),
          rx.el.div(
            rx.el.label("Confirmar Contraseña", class_name=TYPOGRAPHY["label"]),
            rx.el.div(
              rx.el.input(
                type=rx.cond(
                  State.show_user_form_confirm_password,
                  "text",
                  "password",
                ),
                default_value=State.new_user_data["confirm_password"],
                on_blur=lambda v: State.handle_new_user_change(
                  "confirm_password", v
                ),
                class_name=f"{INPUT_STYLES['default']} pr-11",
              ),
              rx.el.button(
                rx.cond(
                  State.show_user_form_confirm_password,
                  rx.icon("eye-off", class_name="h-4 w-4"),
                  rx.icon("eye", class_name="h-4 w-4"),
                ),
                type="button",
                on_click=State.toggle_user_form_confirm_password_visibility,
                class_name=(
                  "absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-7 w-7 "
                  "items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 "
                  "hover:text-slate-700 transition-colors duration-150"
                ),
                aria_label=rx.cond(
                  State.show_user_form_confirm_password,
                  "Ocultar contraseña",
                  "Mostrar contraseña",
                ),
                title=rx.cond(
                  State.show_user_form_confirm_password,
                  "Ocultar contraseña",
                  "Mostrar contraseña",
                ),
              ),
              class_name="relative mt-1",
            ),
            class_name="mb-4",
          ),
          rx.el.div(
            rx.el.div(
              rx.el.h3(
                "Privilegios", class_name=TYPOGRAPHY["card_title"]
              ),
              rx.el.p(
                "Asigna los accesos para el rol elegido. Si necesitas volver a los permisos sugeridos del rol, usa el boton.",
                class_name=TYPOGRAPHY["body_secondary"],
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.button(
                "Restaurar privilegios del rol",
                on_click=State.apply_role_privileges,
                class_name=BUTTON_STYLES["secondary_sm"],
              ),
              rx.el.button(
                "Guardar como plantilla de rol",
                on_click=State.save_role_template,
                class_name=BUTTON_STYLES["secondary_sm"],
              ),
              class_name="flex flex-col sm:flex-row sm:items-center gap-2",
            ),
            class_name="flex flex-wrap justify-between items-start gap-3 mt-4 mb-2",
          ),
          rx.el.div(
            *[
              privilege_section(title, items)
              for title, items in PRIVILEGE_SECTIONS
            ],
            class_name="space-y-3",
          ),
          class_name="flex-1 overflow-y-auto min-h-0 p-1 scroll-smooth",
          style={"scroll-behavior": "auto"},
          id="user-form-content",
          key=State.user_form_key.to_string(),
        ),
        rx.divider(color="slate-100"),
        rx.el.div(
          rx.el.button(
            "Cancelar",
            on_click=State.hide_user_form,
            class_name=BUTTON_STYLES["secondary"],
          ),
          rx.el.button(
            "Guardar",
            on_click=State.save_user,
            class_name=BUTTON_STYLES["success"],
          ),
          class_name="flex flex-col sm:flex-row justify-end items-stretch sm:items-center gap-3 sm:gap-4 flex-shrink-0 pt-3 border-t border-slate-100",
        ),
        class_name=(
          "fixed left-1/2 top-1/2 w-[calc(100%-2rem)] max-w-3xl -translate-x-1/2 "
          "-translate-y-1/2 rounded-xl bg-white p-5 sm:p-6 shadow-xl focus:outline-none "
          "max-h-[90vh] flex flex-col gap-4 border border-slate-200"
        ),
      ),
    ),
    open=State.show_user_form,
    on_open_change=State.set_user_form_open,
  )



def user_section() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.div(
        rx.el.h2(
          "GESTION DE USUARIOS", class_name="text-xl font-semibold text-slate-700"
        ),
        rx.el.p(
          "Crea usuarios, roles y ajusta sus privilegios.",
          class_name=TYPOGRAPHY["body_secondary"],
        ),
        class_name="flex flex-col",
      ),
      user_form(),
      class_name="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-2",
    ),
    rx.el.div(
      rx.el.table(
        rx.el.thead(
          rx.el.tr(
            rx.el.th("Usuario", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-32"),
            rx.el.th("Rol", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-28"),
            rx.el.th("Privilegios", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-full"),
            rx.el.th(
              "Acciones", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center w-24"
            ),
            class_name=TABLE_STYLES["header"],
          )
        ),
        rx.el.tbody(
          rx.foreach(
            State.users_list,
            lambda user: rx.el.tr(
              rx.el.td(user["username"], class_name="py-3 px-4 w-32 truncate"),
              rx.el.td(user["role"], class_name="py-3 px-4 w-28 truncate"),
              rx.el.td(
                privilege_badges(user),
                class_name="py-3 px-4 w-full",
              ),
              rx.el.td(
                rx.el.div(
                  rx.el.button(
                    rx.icon("pencil", class_name="h-4 w-4"),
                    on_click=lambda _,
                    username=user["username"]: State.show_edit_user_form_by_username(
                      username
                    ),
                    title="Editar usuario",
                    aria_label="Editar usuario",
                    class_name=BUTTON_STYLES["icon_primary"],
                  ),
                  rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda _,
                    username=user["username"]: State.delete_user(
                      username
                    ),
                    title="Eliminar usuario",
                    aria_label="Eliminar usuario",
                    class_name=BUTTON_STYLES["icon_danger"],
                  ),
                  class_name="flex justify-center gap-2",
                )
              ),
              class_name="border-b",
              key=user["username"],
            ),
          )
        ),
      ),
      class_name=f"{CARD_STYLES['default']} overflow-x-auto",
    ),
    class_name="space-y-4",
  )


def branch_users_modal() -> rx.Component:
  return rx.dialog.root(
    rx.dialog.content(
      rx.el.div(
        rx.el.div(
          rx.el.h3(
            rx.el.span("Acceso por Sucursal", class_name="text-xl font-semibold text-slate-800"),
            rx.el.span(
              State.branch_users_branch_name,
              class_name="text-sm font-medium text-slate-500",
            ),
            class_name="flex flex-col gap-1",
          ),
          rx.el.button(
            rx.icon("x", class_name="h-4 w-4"),
            on_click=State.close_branch_users,
            title="Cerrar",
            aria_label="Cerrar",
            class_name=BUTTON_STYLES["icon_ghost"],
          ),
          class_name="flex items-start justify-between",
        ),
        rx.el.div(
          rx.el.div(
            rx.foreach(
              State.branch_users_rows,
              lambda user: rx.el.div(
                rx.el.div(
                  rx.el.div(
                    rx.el.span(user["username"], class_name="font-semibold text-slate-800"),
                    rx.el.span(
                      user["role"],
                      class_name=TYPOGRAPHY["caption"],
                    ),
                    class_name="flex flex-col",
                  ),
                  rx.el.span(user["email"], class_name="text-xs text-slate-400"),
                  class_name="flex flex-col",
                ),
                rx.el.div(
                  toggle_switch(
                    checked=user["has_access"],
                    on_change=lambda value, uid=user["id"]: State.set_branch_user_access(uid, value),
                  ),
                ),
                class_name="flex items-center justify-between gap-4 p-3 border border-slate-200 rounded-lg bg-white",
              ),
            ),
            class_name="space-y-3",
          ),
          class_name="max-h-[55vh] overflow-y-auto",
        ),
        rx.el.div(
          rx.el.button(
            "Cancelar",
            on_click=State.close_branch_users,
            class_name=BUTTON_STYLES["secondary"],
          ),
          rx.el.button(
            "Guardar",
            on_click=State.save_branch_users,
            class_name=BUTTON_STYLES["success"],
          ),
          class_name="flex flex-col sm:flex-row justify-end gap-3 pt-3 border-t border-slate-100",
        ),
        class_name="flex flex-col gap-4",
      ),
      class_name="bg-white rounded-xl shadow-xl border border-slate-200 p-5 w-[calc(100%-2rem)] max-w-2xl",
    ),
    open=State.branch_users_modal_open,
    on_open_change=State.close_branch_users,
  )


def branch_section() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.h2(
        "SUCURSALES", class_name="text-xl font-semibold text-slate-700"
      ),
      rx.el.p(
        "Crea sucursales y asigna usuarios por empresa.",
        class_name=TYPOGRAPHY["body_secondary"],
      ),
      class_name="space-y-1",
    ),
    branch_users_modal(),
    rx.el.div(
      rx.el.div(
        rx.el.label("Nombre de Sucursal", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          default_value=rx.cond(
            State.editing_branch_id != "",
            State.editing_branch_name,
            State.new_branch_name,
          ),
          on_blur=State.handle_branch_name_change,
          placeholder="Ej: Casa Matriz, Sucursal Centro",
          key=State.editing_branch_id + "-branch-name",
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Dirección", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          default_value=rx.cond(
            State.editing_branch_id != "",
            State.editing_branch_address,
            State.new_branch_address,
          ),
          on_blur=State.handle_branch_address_change,
          placeholder="Ej: Av. Principal 123",
          key=State.editing_branch_id + "-branch-address",
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.button(
          rx.cond(State.editing_branch_id != "", "Actualizar", "Crear"),
          on_click=rx.cond(State.editing_branch_id != "", State.save_branch, State.create_branch),
          class_name=BUTTON_STYLES["success"],
        ),
        rx.cond(
          State.editing_branch_id != "",
          rx.el.button(
            "Cancelar",
            on_click=State.cancel_edit_branch,
            class_name=BUTTON_STYLES["secondary"],
          ),
          rx.fragment(),
        ),
        class_name="flex flex-col sm:flex-row gap-2 items-stretch sm:items-end",
      ),
      class_name=f"grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 {CARD_STYLES['compact']}",
    ),
    rx.el.div(
      rx.el.table(
        rx.el.thead(
          rx.el.tr(
            rx.el.th("Sucursal", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Dirección", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Usuarios", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Acciones", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center"),
            class_name=TABLE_STYLES["header"],
          )
        ),
        rx.el.tbody(
          rx.foreach(
            State.branches_list,
            lambda branch: rx.el.tr(
              rx.el.td(branch["name"], class_name=TABLE_STYLES["cell"]),
              rx.el.td(branch["address"], class_name=TABLE_STYLES["cell"]),
              rx.el.td(branch["users_count"].to_string(), class_name=TABLE_STYLES["cell"]),
              rx.el.td(
                rx.el.div(
                  rx.el.button(
                    rx.icon("users", class_name="h-4 w-4"),
                    on_click=lambda _, bid=branch["id"]: State.open_branch_users(bid),
                    title="Gestionar usuarios por sucursal",
                    aria_label="Gestionar usuarios por sucursal",
                    class_name=BUTTON_STYLES["icon_primary"],
                  ),
                  rx.el.button(
                    rx.icon("pencil", class_name="h-4 w-4"),
                    on_click=lambda _, bid=branch["id"]: State.start_edit_branch(bid),
                    title="Editar sucursal",
                    aria_label="Editar sucursal",
                    class_name=BUTTON_STYLES["icon_primary"],
                  ),
                  rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda _, bid=branch["id"]: State.delete_branch(bid),
                    title="Eliminar sucursal",
                    aria_label="Eliminar sucursal",
                    class_name=BUTTON_STYLES["icon_danger"],
                  ),
                  class_name="flex justify-center gap-2",
                ),
                class_name=TABLE_STYLES["cell"],
              ),
              class_name=TABLE_STYLES["row"],
              key=branch["id"],
            ),
          )
        ),
        class_name="w-full table-fixed",
      ),
      class_name=f"{CARD_STYLES['default']} overflow-x-auto",
    ),
    class_name="space-y-4",
  )


def currency_section() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.h2(
        "SELECTOR DE MONEDAS", class_name="text-xl font-semibold text-slate-700"
      ),
      rx.el.p(
        "Configura las monedas disponibles y el simbolo que se muestra en los modulos.",
        class_name=TYPOGRAPHY["body_secondary"],
      ),
      class_name="space-y-1",
    ),
    rx.el.div(
      rx.el.div(
        rx.el.label("Codigo", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          default_value=State.new_currency_code,
          on_blur=State.set_new_currency_code,
          placeholder="PEN, USD, EUR",
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Nombre", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          default_value=State.new_currency_name,
          on_blur=State.set_new_currency_name,
          placeholder="Sol peruano, Dolar, Peso",
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Simbolo", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          default_value=State.new_currency_symbol,
          on_blur=State.set_new_currency_symbol,
          placeholder="S/, $, EUR",
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.button(
        rx.icon("plus", class_name="h-4 w-4"),
        "Agregar moneda",
        on_click=State.add_currency,
        class_name=f"{BUTTON_STYLES['success']} w-full md:w-auto min-h-[44px]",
      ),
      class_name="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 bg-white p-3 rounded-xl shadow-sm border items-end",
    ),
    rx.el.div(
      rx.el.span("Moneda activa:", class_name="text-xs text-slate-600"),
      rx.el.span(
        State.currency_name,
        class_name="text-xs font-semibold text-indigo-700",
      ),
      class_name="flex flex-wrap items-center gap-2 bg-indigo-50 border border-indigo-100 rounded-md px-3 py-2",
    ),
    rx.el.div(
      rx.foreach(
        State.available_currencies,
        lambda currency: rx.el.div(
          rx.el.div(
            rx.el.div(
              rx.el.div(
                rx.el.span(
                  currency["code"],
                  class_name="text-sm font-semibold text-slate-900",
                ),
                rx.cond(
                  State.selected_currency_code == currency["code"],
                  rx.el.span(
                    "Activa",
                    class_name="px-2 py-0.5 text-xs rounded-md bg-indigo-50 text-indigo-700 border border-indigo-100",
                  ),
                  rx.fragment(),
                ),
                class_name="flex items-center gap-2",
              ),
              rx.el.p(
                currency["name"],
                class_name=TYPOGRAPHY["caption"],
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.span(
                currency["symbol"],
                class_name="px-2 py-0.5 text-xs rounded-md bg-slate-100 text-slate-600 border border-slate-200",
              ),
              class_name="flex items-center gap-2",
            ),
            class_name="flex items-start justify-between gap-2",
          ),
          rx.el.div(
            rx.el.button(
              "Seleccionar",
              on_click=lambda _,
              code=currency["code"]: State.set_currency(code),
              class_name="px-3 py-1 rounded-md border text-xs hover:bg-slate-50",
            ),
            rx.el.button(
              rx.icon("trash-2", class_name="h-4 w-4"),
              on_click=lambda _,
              code=currency["code"]: State.remove_currency(code),
              title="Eliminar moneda",
              aria_label="Eliminar moneda",
              class_name=BUTTON_STYLES["icon_danger"],
            ),
            class_name="flex items-center justify-end gap-2",
          ),
          class_name=rx.cond(
            State.selected_currency_code == currency["code"],
            "border border-indigo-200 bg-indigo-50 rounded-md p-2 shadow-sm",
            "border border-slate-200 rounded-md p-2 shadow-sm",
          ),
        ),
      ),
      class_name="bg-white p-2 sm:p-3 rounded-xl border border-slate-200 shadow-sm grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2",
    ),
    class_name="space-y-3",
  )


def unit_section() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.h2(
        "UNIDADES DE MEDIDA", class_name="text-xl font-semibold text-slate-700"
      ),
      rx.el.p(
        "Define las unidades que podras seleccionar en inventario, ingresos y ventas.",
        class_name=TYPOGRAPHY["body_secondary"],
      ),
      class_name="space-y-1",
    ),
    rx.el.div(
      rx.el.div(
        rx.el.label("Nombre de la unidad", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          placeholder="Ej: Caja, Paquete, Docena",
          default_value=State.new_unit_name,
          on_blur=State.set_new_unit_name,
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Permite decimales", class_name=TYPOGRAPHY["label"]),
        toggle_switch(
          checked=State.new_unit_allows_decimal,
          on_change=State.set_new_unit_allows_decimal,
        ),
        class_name="flex items-center gap-2 mt-1",
      ),
      rx.el.button(
        rx.icon("plus", class_name="h-4 w-4"),
        "Agregar unidad",
        on_click=State.add_unit,
        class_name=f"{BUTTON_STYLES['success']} w-full md:w-auto min-h-[44px]",
      ),
      class_name="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 bg-white p-3 rounded-xl shadow-sm border items-end",
    ),
    rx.el.div(
      rx.foreach(
        State.unit_rows,
        lambda unit: rx.el.div(
          rx.el.div(
            rx.el.div(
              rx.el.span(
                unit["name"],
                class_name="text-sm font-semibold text-slate-900",
              ),
              rx.cond(
                unit["allows_decimal"],
                rx.el.span(
                  "Si",
                  class_name="px-2 py-0.5 text-xs rounded-md bg-indigo-50 text-indigo-700 border border-indigo-100",
                ),
                rx.el.span(
                  "No",
                  class_name="px-2 py-0.5 text-xs rounded-md bg-slate-100 text-slate-600 border border-slate-200",
                ),
              ),
              class_name="flex items-center gap-2",
            ),
            rx.el.div(
              rx.el.span(
                "Decimales",
                class_name=f"{TYPOGRAPHY['caption']} hidden sm:inline",
              ),
              toggle_switch(
                checked=unit["allows_decimal"].bool(),
                on_change=lambda value,
                name=unit["name"]: State.set_unit_decimal(
                  name, value
                ),
              ),
              rx.el.button(
                rx.icon("trash-2", class_name="h-4 w-4"),
                on_click=lambda _,
                name=unit["name"]: State.remove_unit(name),
                is_disabled=rx.cond(
                  unit["name"] == "Unidad", True, False
                ),
                title="Eliminar unidad",
                aria_label="Eliminar unidad",
                class_name=BUTTON_STYLES["icon_danger"],
              ),
              class_name="flex items-center gap-2",
            ),
            class_name="flex items-center justify-between gap-2",
          ),
          class_name="border border-slate-200 rounded-md p-2 shadow-sm",
        ),
      ),
      class_name="bg-white p-2 sm:p-3 rounded-xl border border-slate-200 shadow-sm grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2",
    ),
    class_name="space-y-3",
  )


def payment_methods_section() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.h2(
        "METODOS DE PAGO", class_name="text-xl font-semibold text-slate-700"
      ),
      rx.el.p(
        "Activa, crea o elimina los botones que veras en el modulo de Venta.",
        class_name=TYPOGRAPHY["body_secondary"],
      ),
      class_name="space-y-1",
    ),
    rx.el.div(
      rx.el.div(
        rx.el.label("Nombre", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          placeholder="Ej: Transferencia, Deposito",
          default_value=State.new_payment_method_name,
          on_blur=State.set_new_payment_method_name,
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Descripcion", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          placeholder="Breve detalle del metodo",
          default_value=State.new_payment_method_description,
          on_blur=State.set_new_payment_method_description,
          class_name=INPUT_STYLES["default"],
          debounce_timeout=600,
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Tipo", class_name=TYPOGRAPHY["label"]),
        rx.el.select(
          *[
            rx.el.option(PAYMENT_KIND_LABELS[kind], value=kind)
            for kind in [
              "cash",
              "debit",
              "credit",
              "yape",
              "plin",
              "transfer",
              "mixed",
              "other",
            ]
          ],
          value=State.new_payment_method_kind,
          on_change=State.set_new_payment_method_kind,
          class_name=SELECT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.button(
        rx.icon("plus", class_name="h-4 w-4"),
        "Agregar metodo",
        on_click=State.add_payment_method,
        class_name=f"{BUTTON_STYLES['success']} w-full md:w-auto min-h-[44px]",
      ),
      class_name="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 bg-white p-3 rounded-xl shadow-sm border items-end",
    ),
    rx.el.div(
      rx.foreach(
        State.payment_methods,
        lambda method: rx.el.div(
          rx.el.div(
            rx.el.div(
              rx.el.div(
                rx.el.span(
                  method["name"],
                  class_name="text-sm font-semibold text-slate-900",
                ),
                rx.cond(
                  State.payment_method == method["name"],
                  rx.el.span(
                    "En uso",
                    class_name="px-2 py-0.5 text-xs rounded-md bg-indigo-50 text-indigo-700 border border-indigo-100",
                  ),
                  rx.fragment(),
                ),
                class_name="flex items-center gap-2",
              ),
              rx.el.div(
                rx.el.span(
                  PAYMENT_KIND_LABELS.get(method["kind"], "Otro"),
                  class_name="px-2 py-0.5 text-xs rounded-md bg-indigo-50 text-indigo-700 border border-indigo-100",
                ),
                rx.cond(
                  method["enabled"],
                  rx.el.span(
                    "Activo",
                    class_name="px-2 py-0.5 text-xs rounded-md bg-emerald-50 text-emerald-700 border border-emerald-100",
                  ),
                  rx.el.span(
                    "Inactivo",
                    class_name="px-2 py-0.5 text-xs rounded-md bg-slate-100 text-slate-600 border border-slate-200",
                  ),
                ),
                class_name="flex items-center gap-2",
              ),
              rx.cond(
                method["description"] != "Sin descripcion",
                rx.el.p(
                  method["description"],
                  class_name=TYPOGRAPHY["caption"],
                ),
                rx.fragment(),
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.div(
                rx.el.span(
                  "Visible en Venta",
                  class_name=f"{TYPOGRAPHY['caption']} hidden sm:inline",
                ),
                toggle_switch(
                  checked=method["enabled"],
                  on_change=lambda value,
                  mid=method["id"]: State.toggle_payment_method_enabled(
                    mid, value
                  ),
                ),
                class_name="flex items-center gap-2",
              ),
              rx.el.button(
                rx.icon("trash-2", class_name="h-4 w-4"),
                on_click=lambda _,
                mid=method["id"]: State.remove_payment_method(mid),
                title="Eliminar método de pago",
                aria_label="Eliminar método de pago",
                class_name=BUTTON_STYLES["icon_danger"],
              ),
              class_name="flex items-center gap-2",
            ),
            class_name="flex items-center justify-between gap-2",
          ),
          class_name="border border-slate-200 rounded-md p-2 shadow-sm",
        ),
      ),
      class_name="bg-white p-2 sm:p-3 rounded-xl border border-slate-200 shadow-sm grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2",
    ),
    class_name="space-y-3",
  )


def configuracion_page() -> rx.Component:
  """Página principal de configuración del sistema."""
  content = rx.fragment(
    rx.el.div(
      page_title(
        "CONFIGURACION DEL SISTEMA",
        "Gestiona usuarios, monedas, unidades y metodos de pago desde un solo lugar.",
      ),
      rx.el.div(
          rx.match(
            State.config_tab,
            ("empresa", company_settings_section()),
            ("sucursales", branch_section()),
            ("usuarios", user_section()),
            ("monedas", currency_section()),
            ("unidades", unit_section()),
            ("pagos", payment_methods_section()),
            ("facturacion", billing_config_section()),
            ("suscripcion", subscription_section()),
            user_section(),
          ),
          class_name="space-y-4",
        ),
      class_name="p-4 sm:p-6 pb-4 w-full flex flex-col gap-5",
    ),
    limit_reached_modal(
      is_open=State.show_limit_modal,
      on_close=State.close_limit_modal,
      message=State.limit_modal_message,
      on_primary=State.open_upgrade_modal,
    ),
    limit_reached_modal(
      is_open=State.show_user_limit_modal,
      on_close=State.close_user_limit_modal,
      message=State.user_limit_modal_message,
      on_primary=State.open_upgrade_modal,
    ),
    pricing_modal(
      is_open=State.show_pricing_modal,
      on_close=State.close_pricing_modal,
    ),
    _upgrade_plan_modal(),
    on_mount=State.load_config_page_background,
  )
  return permission_guard(
    has_permission=State.is_admin,
    content=content,
    redirect_message="Acceso denegado a Configuración",
  )
