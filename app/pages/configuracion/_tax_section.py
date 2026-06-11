import reflex as rx
from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  INPUT_STYLES,
  TYPOGRAPHY,
  action_button,
  modal_container,
  toggle_switch,
)


def _tax_rate_row(rate: rx.Var) -> rx.Component:
  """Fila de una tasa de impuesto en la tabla."""
  _default_badge = "px-2 py-0.5 rounded text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100"
  return rx.el.div(
    rx.el.div(
      rx.el.span(
        rate["tax_name"],
        class_name="text-sm font-bold text-slate-800 font-mono",
      ),
      rx.el.span(
        rate["label"],
        class_name="text-sm text-slate-500",
      ),
      rx.cond(
        rate["is_default"],
        rx.el.span("Default", class_name=_default_badge),
        rx.fragment(),
      ),
      class_name="flex items-center gap-3 flex-1 flex-wrap",
    ),
    rx.el.div(
      rx.el.span(
        rate["rate"].to(str) + "%",
        class_name="text-sm font-semibold text-slate-700 font-mono min-w-[52px] text-right",
      ),
      rx.cond(
        ~rate["is_default"],
        rx.el.button(
          rx.icon("star", class_name="h-3.5 w-3.5"),
          on_click=State.set_as_default_rate(rate["id"]),
          class_name="p-1.5 rounded hover:bg-amber-50 text-slate-400 hover:text-amber-500 transition-colors",
          title="Marcar como default",
        ),
        rx.icon("star", class_name="h-3.5 w-3.5 fill-amber-400 text-amber-400 mx-1.5"),
      ),
      rx.el.button(
        rx.icon("pencil", class_name="h-3.5 w-3.5"),
        on_click=State.open_edit_tax_dialog(rate["id"]),
        class_name="p-1.5 rounded hover:bg-indigo-50 text-slate-400 hover:text-indigo-600 transition-colors",
        title="Editar",
      ),
      rx.el.button(
        rx.icon("trash-2", class_name="h-3.5 w-3.5"),
        on_click=State.confirm_delete_tax_rate(rate["id"]),
        class_name="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors",
        title="Eliminar",
      ),
      class_name="flex items-center gap-1",
    ),
    class_name=rx.cond(
      rate["is_default"],
      "flex items-center justify-between px-3 py-2.5 rounded-md border border-indigo-300 bg-indigo-100 shadow-sm transition-colors",
      "flex items-center justify-between px-3 py-2.5 rounded-md border border-slate-100 bg-slate-50 hover:bg-white transition-colors",
    ),
  )


def _tax_rate_dialog() -> rx.Component:
  """Modal para agregar o editar una tasa de impuesto."""
  _input = INPUT_STYLES["default"]
  _label = TYPOGRAPHY["label"]
  return modal_container(
    is_open=State.tax_dialog_open,
    on_close=State.close_tax_dialog,
    title=rx.cond(State.editing_is_new, "Agregar tasa de impuesto", "Editar tasa"),
    description="Configura el nombre, etiqueta y porcentaje de la tasa.",
    children=[
      rx.el.div(
        rx.el.label("Nombre del impuesto (sigla)", class_name=_label),
        rx.el.input(
          placeholder="IGV, IVA, IVA-I...",
          default_value=State.editing_tax_name,
          on_blur=State.set_editing_tax_name,
          key=State.editing_rate_id,
          class_name=_input,
          max_length=20,
        ),
        rx.el.p(
          "Sigla oficial: IGV (Perú), IVA (Argentina/Colombia/Chile), etc.",
          class_name=TYPOGRAPHY["caption"],
        ),
        class_name="space-y-1",
      ),
      rx.el.div(
        rx.el.label("Etiqueta descriptiva", class_name=_label),
        rx.el.input(
          placeholder="Estándar, Reducida, Incrementada...",
          default_value=State.editing_label,
          on_blur=State.set_editing_label,
          key=State.editing_rate_id,
          class_name=_input,
          max_length=50,
        ),
        class_name="space-y-1",
      ),
      rx.el.div(
        rx.el.label("Porcentaje (%)", class_name=_label),
        rx.el.div(
          rx.el.input(
            placeholder="18.00",
            default_value=State.editing_rate_str,
            on_blur=State.set_editing_rate_str,
            key=State.editing_rate_id,
            type="text",
            inputmode="decimal",
            class_name=f"{_input} pr-9",
          ),
          rx.el.span(
            "%",
            class_name="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm pointer-events-none",
          ),
          class_name="relative",
        ),
        class_name="space-y-1",
      ),
      rx.el.div(
        rx.el.div(
          rx.el.div(
            rx.el.p("Marcar como tasa default", class_name=_label),
            rx.el.p(
              "Se usará en documentos fiscales y vista previa de recibos.",
              class_name=TYPOGRAPHY["caption"],
            ),
            class_name="flex flex-col",
          ),
          toggle_switch(
            checked=State.editing_is_default,
            on_change=State.set_editing_is_default,
          ),
          class_name="flex items-center justify-between",
        ),
        class_name="rounded-md border border-slate-200 bg-slate-50 p-3",
      ),
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_tax_dialog,
        class_name=BUTTON_STYLES["ghost"],
      ),
      action_button(
        "Guardar",
        on_click=State.save_tax_rate,
        icon="save",
      ),
      class_name="flex justify-end gap-3",
    ),
  )


def _tax_delete_confirm_dialog() -> rx.Component:
  """Modal de confirmación de borrado de tasa."""
  return modal_container(
    is_open=State.delete_confirm_open,
    on_close=State.close_delete_confirm,
    title="Eliminar tasa de impuesto",
    description="Esta acción no puede deshacerse. La tasa quedará inactiva.",
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_delete_confirm,
        class_name=BUTTON_STYLES["ghost"],
      ),
      action_button(
        "Eliminar",
        on_click=State.execute_delete_tax_rate,
        variant="danger",
        icon="trash-2",
      ),
      class_name="flex justify-end gap-3",
    ),
  )


def impuestos_section() -> rx.Component:
  """Sección de configuración de impuestos multi-tasa."""
  _label = TYPOGRAPHY["label"]
  _caption = TYPOGRAPHY["caption"]

  preset_countries = [
    ("PE", "🇵🇪 Perú (IGV 18%)"),
    ("AR", "🇦🇷 Argentina (IVA 21%/10.5%/27%)"),
    ("CO", "🇨🇴 Colombia (IVA 19%/5%)"),
    ("CL", "🇨🇱 Chile (IVA 19%)"),
    ("EC", "🇪🇨 Ecuador (IVA 12%/5%)"),
    ("BO", "🇧🇴 Bolivia (IVA 13%)"),
    ("UY", "🇺🇾 Uruguay (IVA 22%/10%)"),
    ("PY", "🇵🇾 Paraguay (IVA 10%/5%)"),
    ("MX", "🇲🇽 México (IVA 16%)"),
  ]

  return rx.el.div(
    # ── Encabezado ────────────────────────────────────────────────────────
    rx.el.div(
      rx.el.div(
        rx.icon("percent", class_name="h-6 w-6 text-indigo-600"),
        rx.el.div(
          rx.el.h2(
            "Configuración de Impuestos",
            class_name="text-xl font-semibold text-slate-700",
          ),
          rx.el.p(
            "Define las tasas aplicables a tus ventas. Puedes cargar defaults por país o crear tasas personalizadas.",
            class_name=_caption,
          ),
          class_name="space-y-0.5",
        ),
        class_name="flex items-start gap-3",
      ),
      class_name="pb-4",
    ),

    # ── Presets por país ──────────────────────────────────────────────────
    rx.el.div(
      rx.el.div(
        rx.el.p("Cargar configuración por país", class_name=_label),
        rx.el.p(
          "Reemplaza las tasas actuales con los valores predefinidos del país seleccionado.",
          class_name=_caption,
        ),
        class_name="space-y-0.5",
      ),
      rx.el.div(
        *[
          rx.el.button(
            country_label,
            on_click=State.apply_country_presets(country_code),
            class_name=rx.cond(
              State.active_preset_country == country_code,
              "text-xs px-3 py-1.5 rounded-md border border-indigo-300 "
              "bg-indigo-50 text-indigo-700 font-semibold transition-colors",
              "text-xs px-3 py-1.5 rounded-md border border-slate-200 "
              "bg-white hover:bg-indigo-50 hover:border-indigo-200 "
              "hover:text-indigo-700 text-slate-600 transition-colors font-medium",
            ),
          )
          for country_code, country_label in preset_countries
        ],
        class_name="flex flex-wrap gap-2 pt-1",
      ),
      class_name="rounded-xl border border-slate-200 bg-white p-4 space-y-3",
    ),

    # ── Tabla de tasas ────────────────────────────────────────────────────
    rx.el.div(
      rx.el.div(
        rx.el.p("Tasas configuradas", class_name=_label),
        action_button(
          "Agregar tasa",
          on_click=State.open_add_tax_dialog,
          icon="plus",
          variant="secondary",
        ),
        class_name="flex items-center justify-between",
      ),
      rx.cond(
        State.tax_rates.length() == 0,
        rx.el.div(
          rx.icon("info", class_name="h-5 w-5 text-slate-400"),
          rx.el.p(
            "No hay tasas configuradas. Carga un preset de país o agrega una tasa manualmente.",
            class_name="text-sm text-slate-500 text-center",
          ),
          class_name="flex flex-col items-center gap-2 py-6",
        ),
        rx.el.div(
          rx.foreach(State.tax_rates, _tax_rate_row),
          class_name="space-y-1.5",
        ),
      ),
      class_name="rounded-xl border border-slate-200 bg-white p-4 space-y-3",
    ),

    # ── Toggle mostrar impuesto en recibo ─────────────────────────────────
    rx.el.div(
      rx.el.div(
        rx.icon("receipt", class_name="h-5 w-5 text-slate-500 mt-0.5 flex-shrink-0"),
        rx.el.div(
          rx.el.p("Mostrar impuesto en recibo", class_name=_label),
          rx.el.p(
            "Muestra el desglose del impuesto (base + impuesto + total) en los recibos de venta.",
            class_name=_caption,
          ),
          class_name="flex-1 space-y-0.5",
        ),
        toggle_switch(
          checked=State.show_tax_on_receipt,
          on_change=State.set_show_tax_on_receipt,
        ),
        class_name="flex items-start gap-3",
      ),
      class_name="rounded-xl border border-slate-200 bg-white p-4",
    ),

    # ── Vista previa ──────────────────────────────────────────────────────
    rx.el.div(
      rx.el.p("Vista previa", class_name=_label),
      rx.el.div(
        rx.el.div(
          rx.el.span("Subtotal:", class_name="text-sm text-slate-500"),
          rx.el.span("100.00", class_name="text-sm text-slate-600 font-mono"),
          class_name="flex justify-between",
        ),
        rx.cond(
          State.show_tax_on_receipt,
          rx.el.div(
            rx.el.span(
              State.default_tax_display + ":",
              class_name="text-sm text-slate-500",
            ),
            rx.el.span(
              State.preview_tax_amount,
              class_name="text-sm text-indigo-600 font-mono font-semibold",
            ),
            class_name="flex justify-between",
          ),
          rx.fragment(),
        ),
        rx.el.div(
          rx.el.span("Total:", class_name="text-sm font-bold text-slate-700"),
          rx.el.span(
            State.preview_total,
            class_name="text-sm font-bold text-slate-800 font-mono",
          ),
          class_name="flex justify-between border-t border-slate-100 pt-2 mt-1",
        ),
        class_name="space-y-2",
      ),
      class_name="rounded-xl border border-slate-200 bg-white p-4 space-y-3",
    ),

    # ── Dialogs ───────────────────────────────────────────────────────────
    _tax_rate_dialog(),
    _tax_delete_confirm_dialog(),

    class_name="space-y-4",
  )
