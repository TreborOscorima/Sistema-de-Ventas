import reflex as rx
from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  CARD_STYLES,
  INPUT_STYLES,
  SELECT_STYLES,
  TYPOGRAPHY,
  action_button,
  modal_container,
)


def company_settings_section() -> rx.Component:
  """Sección de configuración de datos de empresa."""
  return rx.el.div(
    rx.el.div(
      rx.el.h2(
        "DATOS DE MI EMPRESA", class_name="text-xl font-semibold text-slate-700"
      ),
      rx.el.p(
        "Actualiza la información que aparece en recibos y reportes.",
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
          rx.el.label(State.tax_id_label, class_name=TYPOGRAPHY["label"]),
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
            rx.el.option("Ferretería", value="ferreteria"),
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
          rx.el.label("Papel de Impresión", class_name=TYPOGRAPHY["label"]),
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
            "Deja en blanco para usar el ancho automático.",
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
            "Guardar Configuración",
            on_click=State.save_settings,
            class_name=f"{BUTTON_STYLES['primary']} w-full sm:w-auto min-h-[44px]",
          ),
          class_name="flex justify-end sm:justify-start",
        ),
        class_name="flex flex-col sm:flex-row sm:items-center justify-between gap-3",
      ),
            class_name=f"{CARD_STYLES['default']} space-y-4",
    ),
    # ── Márgenes de Ganancia ──────────────────────────────────────────────
    rx.el.div(
      rx.el.div(
        rx.el.h2(
          "MÁRGENES DE GANANCIA",
          class_name="text-xl font-semibold text-slate-700",
        ),
        rx.el.p(
          "Porcentaje aplicado al precio de compra para calcular el precio de venta sugerido.",
          class_name=TYPOGRAPHY["body_secondary"],
        ),
        class_name="space-y-1",
      ),
      rx.el.div(
        # Margen global de empresa
        rx.el.div(
          rx.el.label(
            "Margen Global de Empresa (%)",
            class_name=TYPOGRAPHY["label"],
          ),
          rx.el.div(
            rx.el.input(
              default_value=State.company_profit_margin,
              on_blur=State.set_company_profit_margin,
              placeholder="Ej: 30",
              type_="number",
              min="0",
              max="9999",
              step="0.01",
              key=State.company_form_key.to_string() + "-company_margin",
              class_name=INPUT_STYLES["default"],
            ),
            rx.el.span(
              "%",
              class_name="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm pointer-events-none",
            ),
            class_name="relative",
          ),
          rx.el.p(
            "Se aplica a todas las sucursales que no tengan margen propio.",
            class_name=TYPOGRAPHY["caption"],
          ),
          class_name="flex flex-col gap-1",
        ),
        # Override de sucursal actual
        rx.el.div(
          rx.el.label(
            "Margen de Esta Sucursal (%) — opcional",
            class_name=TYPOGRAPHY["label"],
          ),
          rx.el.div(
            rx.el.input(
              default_value=State.branch_profit_margin,
              on_blur=State.set_branch_profit_margin,
              placeholder="Vacío = usa margen de empresa",
              type_="number",
              min="0",
              max="9999",
              step="0.01",
              key=State.company_form_key.to_string() + "-branch_margin",
              class_name=INPUT_STYLES["default"],
            ),
            rx.el.span(
              "%",
              class_name="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm pointer-events-none",
            ),
            class_name="relative",
          ),
          rx.el.p(
            "Deja en blanco para heredar el margen global de empresa.",
            class_name=TYPOGRAPHY["caption"],
          ),
          class_name="flex flex-col gap-1",
        ),
        class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
      ),
      # Vista previa del margen efectivo
      rx.el.div(
        rx.el.div(
          rx.icon("trending-up", class_name="h-4 w-4 text-indigo-500"),
          rx.el.span(
            "Margen efectivo de esta sucursal: ",
            class_name="text-sm text-slate-500",
          ),
          rx.el.span(
            State.effective_profit_margin + "%",
            class_name="text-sm font-semibold text-indigo-600",
          ),
          rx.el.span(
            " → precio de compra $10 genera precio de venta $" +
            State.effective_profit_margin_preview,
            class_name="text-xs text-slate-400 ml-1",
          ),
          class_name="flex items-center gap-2 flex-wrap",
        ),
        class_name="rounded-lg bg-indigo-50 border border-indigo-100 px-4 py-3",
      ),
      rx.el.div(
        rx.el.button(
          "Guardar Márgenes",
          on_click=State.save_profit_margin,
          class_name=f"{BUTTON_STYLES['primary']} w-full sm:w-auto min-h-[44px]",
        ),
        class_name="flex justify-end sm:justify-start",
      ),
      # ── Aplicar al inventario existente ──────────────────────────────────
      rx.el.div(
        rx.el.div(
          rx.el.p(
            "Aplicar al inventario existente",
            class_name="text-sm font-semibold text-slate-700",
          ),
          rx.el.p(
            "Normaliza todos los productos al margen global activo. "
            "Los precios y márgenes personalizados se eliminan; "
            "los productos calcularán su precio desde el margen global vigente.",
            class_name=TYPOGRAPHY["caption"],
          ),
          class_name="space-y-1",
        ),
        rx.el.button(
          rx.cond(
            State.applying_margin_to_inventory,
            rx.icon("loader", class_name="h-4 w-4 animate-spin"),
            rx.icon("refresh-cw", class_name="h-4 w-4"),
          ),
          rx.cond(
            State.applying_margin_to_inventory,
            "Normalizando...",
            "Normalizar al margen global",
          ),
          on_click=State.open_normalize_confirm,
          disabled=State.applying_margin_to_inventory,
          class_name=f"{BUTTON_STYLES['secondary']} flex items-center gap-2 min-h-[44px]",
        ),
        class_name="pt-3 border-t border-slate-100 space-y-3",
      ),
      # ── Modal de confirmación ─────────────────────────────────────────────
      rx.dialog.root(
        rx.dialog.content(
          rx.el.div(
            rx.el.div(
              rx.icon("alert-triangle", class_name="h-8 w-8 text-amber-500"),
              class_name="flex justify-center mb-3",
            ),
            rx.el.p(
              "¿Normalizar todos los productos?",
              class_name="text-base font-semibold text-slate-800 text-center mb-2",
            ),
            rx.el.p(
              "Esta acción eliminará los precios fijos y márgenes personalizados "
              "de todos los productos. A partir de ese momento, cada producto "
              "calculará su precio de venta desde el margen global activo.",
              class_name="text-sm text-slate-600 text-center mb-5",
            ),
            rx.el.div(
              rx.el.button(
                "Cancelar",
                on_click=State.close_normalize_confirm,
                class_name=f"{BUTTON_STYLES['secondary']} min-h-[40px]",
              ),
              rx.el.button(
                "Sí, normalizar todo",
                on_click=State.apply_global_margin_to_inventory,
                class_name=f"{BUTTON_STYLES['danger']} min-h-[40px]",
              ),
              class_name="flex gap-3 justify-center",
            ),
            class_name="p-2",
          ),
          max_width="420px",
        ),
        open=State.show_normalize_confirm,
        on_open_change=State.close_normalize_confirm,
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
      rx.el.h2("MI SUSCRIPCIÓN", class_name="text-xl font-semibold text-slate-700"),
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
