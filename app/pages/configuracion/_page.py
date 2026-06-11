import reflex as rx
from app.state import State
from app.components.ui import (
  CARD_STYLES,
  TYPOGRAPHY,
  limit_reached_modal,
  pricing_modal,
  page_title,
  permission_guard,
)
from ._billing_section import billing_config_section
from ._company_section import company_settings_section, subscription_section, _upgrade_plan_modal
from ._user_section import user_section, branch_section
from ._operational_section import currency_section, unit_section, payment_methods_section
from ._tax_section import impuestos_section

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
    "key": "impuestos",
    "label": "Impuestos",
    "description": "Tasas de IGV, IVA y configuracion fiscal",
    "icon": "percent",
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
            ("impuestos", impuestos_section()),
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
