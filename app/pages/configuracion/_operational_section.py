import reflex as rx
from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  INPUT_STYLES,
  SELECT_STYLES,
  TYPOGRAPHY,
  toggle_switch,
)

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


def currency_section() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.h2(
        "SELECTOR DE MONEDAS", class_name="text-xl font-semibold text-slate-700"
      ),
      rx.el.p(
        "Configura las monedas disponibles y el símbolo que se muestra en los módulos.",
        class_name=TYPOGRAPHY["body_secondary"],
      ),
      class_name="space-y-1",
    ),
    rx.el.div(
      rx.el.div(
        rx.el.label("Código", class_name=TYPOGRAPHY["label"]),
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
        rx.el.label("Símbolo", class_name=TYPOGRAPHY["label"]),
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
        "Define las unidades que podrás seleccionar en inventario, ingresos y ventas.",
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
                disabled=rx.cond(
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
        "MÉTODOS DE PAGO", class_name="text-xl font-semibold text-slate-700"
      ),
      rx.el.p(
        "Activa, crea o elimina los botones que verás en el módulo de Venta.",
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
        rx.el.label("Descripción", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          placeholder="Breve detalle del método",
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
                method["description"] != "Sin descripción",
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
