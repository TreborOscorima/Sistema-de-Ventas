import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  INPUT_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  form_textarea,
  modal_container,
  status_badge,
)


def delete_sale_modal() -> rx.Component:
  """Modal de confirmación para eliminar una venta."""
  return modal_container(
    is_open=State.sale_delete_modal_open,
    on_close=State.close_sale_delete_modal,
    title="Eliminar venta",
    description="Ingrese el motivo para eliminar la venta seleccionada. Esta acción no se puede deshacer.",
    children=[
      form_textarea(
        label="Motivo de eliminación",
        default_value=State.sale_delete_reason,
        on_blur=State.set_sale_delete_reason,
        placeholder="Detalle aquí el motivo...",
      )
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_sale_delete_modal,
        class_name=BUTTON_STYLES["secondary"],
      ),
      rx.el.button(
        rx.icon("trash-2", class_name="h-4 w-4"),
        "Eliminar",
        on_click=State.delete_sale,
        class_name=BUTTON_STYLES["danger"],
      ),
      class_name="flex justify-end gap-3 mt-4",
    ),
  )


def close_cashbox_modal() -> rx.Component:
  """Modal de cierre de caja con resumen."""
  return modal_container(
    is_open=State.cashbox_close_modal_open,
    on_close=State.close_cashbox_close_modal,
    title="Resumen de Caja",
    description="Cierre de caja para " + State.current_user["username"],
    max_width="max-w-4xl",
    children=[
      rx.el.div(
        rx.el.h4(
          "Resumen de caja",
          class_name=f"{TYPOGRAPHY['card_title']} mb-2",
        ),
        rx.el.table(
          rx.el.tbody(
            rx.el.tr(
              rx.el.td("Apertura", class_name="py-2 px-3 text-left text-sm"),
              rx.el.td(
                State.cashbox_close_opening_amount_display,
                class_name="py-2 px-3 text-right text-sm font-semibold",
              ),
              class_name="border-b",
            ),
            rx.el.tr(
              rx.el.td("Ingresos reales", class_name="py-2 px-3 text-left text-sm"),
              rx.el.td(
                State.cashbox_close_income_total_display,
                class_name="py-2 px-3 text-right text-sm font-semibold",
              ),
              class_name="border-b",
            ),
            rx.el.tr(
              rx.el.td("Devoluciones y egresos", class_name="py-2 px-3 text-left text-sm"),
              rx.el.td(
                State.cashbox_close_expense_total_display,
                class_name="py-2 px-3 text-right text-sm font-semibold",
              ),
              class_name="border-b",
            ),
            rx.el.tr(
              rx.el.td(
                rx.el.span("Saldo esperado", class_name="font-semibold"),
                class_name="py-2 px-3 text-left text-sm",
              ),
              rx.el.td(
                State.cashbox_close_expected_total_display,
                class_name="py-2 px-3 text-right text-sm font-bold",
              ),
              class_name="border-t border-slate-200 bg-slate-50",
            ),
          ),
          class_name="min-w-full text-sm border rounded-lg",
        ),
        class_name="overflow-x-auto mb-6",
      ),
      rx.el.div(
        rx.el.h4(
          "Ingresos por metodo",
          class_name=f"{TYPOGRAPHY['card_title']} mb-2",
        ),
        rx.el.table(
          rx.el.thead(
            rx.el.tr(
              rx.el.th("Metodo", scope="col", class_name=TABLE_STYLES["header_cell"]),
              rx.el.th("Mov.", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center"),
              rx.el.th("Ingresos", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right"),
              rx.el.th("Devoluciones", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right"),
              rx.el.th("Neto", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right"),
              class_name=TABLE_STYLES["header"],
            )
          ),
          rx.el.tbody(
            rx.foreach(
              State.cashbox_close_totals,
              lambda item: rx.el.tr(
                rx.el.td(
                  item["method"],
                  class_name="py-2 px-3 text-left text-sm",
                ),
                rx.el.td(
                  item["count"],
                  class_name="py-2 px-3 text-center text-sm font-semibold",
                ),
                rx.el.td(
                  item["total"],
                  class_name="py-2 px-3 text-right text-sm text-slate-500",
                ),
                rx.el.td(
                  rx.cond(
                    item["has_refund"],
                    rx.el.span("-", item["refund"], class_name="text-red-500 font-medium"),
                    rx.el.span("—", class_name="text-slate-300"),
                  ),
                  class_name="py-2 px-3 text-right text-sm",
                ),
                rx.el.td(
                  item["net_total"],
                  class_name="py-2 px-3 text-right text-sm font-semibold text-slate-900",
                ),
                class_name="border-b",
              ),
            ),
            rx.el.tr(
              rx.el.td(
                rx.el.span("Total neto", class_name="font-semibold"),
                class_name="py-2 px-3 text-left text-sm",
              ),
              rx.el.td(
                rx.el.span("-", class_name="text-slate-400"),
                class_name="py-2 px-3 text-center text-sm",
              ),
              rx.el.td(
                State.cashbox_close_income_total_display,
                class_name="py-2 px-3 text-right text-sm text-slate-400",
              ),
              rx.el.td(
                rx.cond(
                  State.cashbox_close_refund_total > 0,
                  rx.el.span(
                    "-", State.cashbox_close_refund_total_display,
                    class_name="text-red-500 font-medium",
                  ),
                  rx.el.span("—", class_name="text-slate-300"),
                ),
                class_name="py-2 px-3 text-right text-sm",
              ),
              rx.el.td(
                rx.el.span(State.cashbox_close_net_income_display, class_name="font-bold text-slate-900"),
                class_name="py-2 px-3 text-right text-sm",
              ),
              class_name="border-t border-slate-200 bg-slate-50",
            )
          ),
          class_name="min-w-full text-sm border rounded-lg",
        ),
        class_name="overflow-x-auto mb-6",
      ),
      rx.el.div(
        rx.el.h4(
          "Detalle de ingresos",
          class_name=f"{TYPOGRAPHY['card_title']} mb-2",
        ),
        rx.el.div(
          rx.el.table(
            rx.el.thead(
              rx.el.tr(
                rx.el.th("Hora", scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Concepto", scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th(
                  "Monto", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right"
                ),
                class_name=TABLE_STYLES["header"],
              )
            ),
            rx.el.tbody(
              rx.foreach(
                State.cashbox_close_sales,
                lambda sale: rx.el.tr(
                  rx.el.td(
                    sale["time"],
                    class_name="py-2 px-3 text-sm text-slate-500 font-mono whitespace-nowrap",
                  ),
                  rx.el.td(
                    rx.el.p(
                      sale["concept"],
                      class_name="text-sm font-medium text-slate-900 max-w-md truncate",
                      title=sale["concept"],
                    ),
                    class_name="py-2 px-3 text-sm",
                  ),
                  rx.el.td(
                    State.currency_symbol,
                    sale["total"],
                    class_name="py-2 px-3 text-right text-sm font-semibold",
                  ),
                  class_name="border-b",
                ),
              )
            ),
            class_name="min-w-full text-sm",
          ),
          class_name="max-h-64 overflow-y-auto overflow-x-auto border rounded-lg",
        ),
        class_name="mb-6",
      ),
      # Detalle de egresos (devoluciones y gastos caja chica)
      rx.cond(
        State.cashbox_close_expense_total > 0,
        rx.el.div(
          rx.el.h4(
            "Detalle de egresos",
            class_name=f"{TYPOGRAPHY['card_title']} mb-2",
          ),
          rx.el.div(
            rx.el.table(
              rx.el.thead(
                rx.el.tr(
                  rx.el.th("Hora", scope="col", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th("Concepto", scope="col", class_name=TABLE_STYLES["header_cell"]),
                  rx.el.th(
                    "Monto", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right"
                  ),
                  class_name=TABLE_STYLES["header"],
                )
              ),
              rx.el.tbody(
                rx.foreach(
                  State.cashbox_close_summary_returns,
                  lambda exp: rx.el.tr(
                    rx.el.td(
                      exp["time"],
                      class_name="py-2 px-3 text-sm text-slate-500 font-mono whitespace-nowrap",
                    ),
                    rx.el.td(
                      rx.el.p(
                        exp["concept"],
                        class_name="text-sm font-medium text-slate-900 max-w-md truncate",
                        title=exp["concept"],
                      ),
                      class_name="py-2 px-3 text-sm",
                    ),
                    rx.el.td(
                      rx.el.span(
                        "-", State.currency_symbol, exp["amount"],
                        class_name="text-red-600 font-semibold",
                      ),
                      class_name="py-2 px-3 text-right text-sm",
                    ),
                    class_name="border-b",
                  ),
                )
              ),
              class_name="min-w-full text-sm",
            ),
            class_name="max-h-48 overflow-y-auto overflow-x-auto border rounded-lg",
          ),
          class_name="mb-6",
        ),
      ),
      # Sección de arqueo por denominación
      rx.el.div(
        rx.el.div(
          rx.el.h4(
            "Arqueo de efectivo",
            class_name=f"{TYPOGRAPHY['card_title']}",
          ),
          rx.el.p(
            "Conteo de billetes y monedas en caja",
            class_name="text-xs text-slate-500",
          ),
          rx.el.button(
            rx.icon("eraser", class_name="h-3.5 w-3.5"),
            "Limpiar",
            on_click=State.clear_denomination_counts,
            class_name="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1 ml-auto",
          ),
          class_name="flex items-center gap-3 mb-3",
        ),
        rx.el.div(
          rx.el.table(
            rx.el.thead(
              rx.el.tr(
                rx.el.th("Denominación", scope="col", class_name=TABLE_STYLES["header_cell"]),
                rx.el.th("Cantidad", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center w-24"),
                rx.el.th("Subtotal", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-right"),
                class_name=TABLE_STYLES["header"],
              )
            ),
            rx.el.tbody(
              rx.foreach(
                State.denomination_rows,
                lambda row: rx.el.tr(
                  rx.el.td(
                    rx.cond(
                      row["type"] == "bill",
                      rx.icon("banknote", class_name="h-4 w-4 text-green-600 inline mr-1.5"),
                      rx.icon("circle", class_name="h-4 w-4 text-amber-500 inline mr-1.5"),
                    ),
                    row["label"],
                    class_name="py-1.5 px-3 text-sm flex items-center",
                  ),
                  rx.el.td(
                    rx.el.input(
                      type="number",
                      min="0",
                      value=row["count"].to_string(),
                      on_change=lambda val, k=row["key"]: State.set_denomination_count(k, val),
                      class_name="w-20 text-center text-sm border rounded px-2 py-1 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500",
                    ),
                    class_name="py-1.5 px-3 text-center",
                  ),
                  rx.el.td(
                    row["subtotal"],
                    class_name="py-1.5 px-3 text-right text-sm font-mono",
                  ),
                  class_name="border-b",
                ),
              ),
            ),
            class_name="min-w-full text-sm",
          ),
          class_name="max-h-56 overflow-y-auto overflow-x-auto border rounded-lg",
        ),
        # Resultado del arqueo
        rx.el.div(
          rx.el.table(
            rx.el.tbody(
              rx.el.tr(
                rx.el.td("Total contado", class_name="py-2 px-3 text-left text-sm font-semibold"),
                rx.el.td(
                  State.cashbox_close_counted_total_display,
                  class_name="py-2 px-3 text-right text-sm font-bold",
                ),
                class_name="border-b bg-slate-50",
              ),
              rx.el.tr(
                rx.el.td("Saldo esperado", class_name="py-2 px-3 text-left text-sm"),
                rx.el.td(
                  State.cashbox_close_expected_total_display,
                  class_name="py-2 px-3 text-right text-sm font-semibold",
                ),
                class_name="border-b",
              ),
              rx.el.tr(
                rx.el.td(
                  rx.el.span("Diferencia", class_name="font-semibold"),
                  class_name="py-2 px-3 text-left text-sm",
                ),
                rx.el.td(
                  State.cashbox_close_discrepancy_display,
                  class_name=rx.cond(
                    State.cashbox_close_discrepancy == 0,
                    "py-2 px-3 text-right text-sm font-bold text-green-600",
                    "py-2 px-3 text-right text-sm font-bold text-red-600",
                  ),
                ),
                class_name="border-t-2 border-slate-300",
              ),
            ),
            class_name="w-full text-sm border rounded-lg",
          ),
          class_name="mt-3",
        ),
        class_name="mb-6",
      ),
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_cashbox_close_modal,
        class_name=BUTTON_STYLES["secondary"],
      ),
      rx.cond(
        (State.cashbox_close_sales.length() > 0)
        | (State.cashbox_close_totals.length() > 0),
        rx.el.button(
          rx.icon("file-text", class_name="h-4 w-4"),
          "Descargar PDF",
          on_click=State.export_cashbox_close_pdf,
          class_name=BUTTON_STYLES["danger"],
        ),
        rx.fragment(),
      ),
      rx.el.button(
        rx.icon("lock", class_name="h-4 w-4"),
        "Confirmar Cierre",
        on_click=State.close_cashbox_day,
        class_name=f"{BUTTON_STYLES['primary']} min-h-[42px]",
      ),
      class_name="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 sm:gap-3 mt-4",
    ),
  )


def cashbox_log_modal() -> rx.Component:
  return modal_container(
    is_open=State.cashbox_log_modal_open,
    on_close=State.close_cashbox_log_modal,
    title="Detalle de apertura/cierre",
    description="Resumen del movimiento de caja seleccionado.",
    max_width="max-w-2xl",
    children=[
      rx.cond(
        State.cashbox_log_selected == None,
        rx.el.p("Registro no disponible.", class_name="text-sm text-slate-600"),
        rx.el.div(
          rx.el.div(
            rx.el.div(
              rx.el.span("Fecha y hora", class_name=f"{TYPOGRAPHY['caption']} uppercase tracking-wide"),
              rx.el.p(State.cashbox_log_selected["timestamp"], class_name="text-sm font-semibold text-slate-900"),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.span("Evento", class_name=f"{TYPOGRAPHY['caption']} uppercase tracking-wide"),
              rx.cond(
                State.cashbox_log_selected["action"] == "apertura",
                status_badge("Apertura", status_colors={"apertura": ("bg-emerald-100", "text-emerald-700")}),
                status_badge("Cierre", status_colors={"cierre": ("bg-orange-100", "text-orange-700")}),
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.span("Usuario", class_name=f"{TYPOGRAPHY['caption']} uppercase tracking-wide"),
              rx.el.p(State.cashbox_log_selected["user"], class_name="text-sm font-semibold text-slate-900"),
              class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-1 sm:grid-cols-3 gap-3",
          ),
          rx.el.div(
            rx.el.div(
              rx.el.span("Monto apertura", class_name=f"{TYPOGRAPHY['caption']} uppercase tracking-wide"),
              rx.el.p(State.currency_symbol, State.cashbox_log_selected["opening_amount"], class_name="text-lg font-semibold text-slate-900"),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.span("Monto cierre", class_name=f"{TYPOGRAPHY['caption']} uppercase tracking-wide"),
              rx.el.p(State.currency_symbol, State.cashbox_log_selected["closing_total"], class_name="text-lg font-semibold text-slate-900"),
              class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 gap-3",
          ),
          rx.cond(
            State.cashbox_log_selected["totals_by_method"].length() == 0,
            rx.el.div(
              rx.el.h4("Totales por metodo", class_name="text-sm font-semibold text-slate-700"),
              rx.el.p("Sin totales registrados para este evento.", class_name="text-sm text-slate-600"),
              class_name="bg-slate-50 border border-slate-200 rounded-lg p-3",
            ),
            rx.el.div(
              rx.el.h4("Totales por metodo", class_name="text-sm font-semibold text-slate-700"),
              rx.el.ul(
                rx.foreach(
                  State.cashbox_log_selected["totals_by_method"],
                  lambda item: rx.el.li(
                    rx.el.span(item["method"], class_name=TYPOGRAPHY["body"]),
                    rx.el.span(State.currency_symbol, item["amount"], class_name=TYPOGRAPHY["mono_value"]),
                    class_name="flex items-center justify-between",
                  ),
                ),
                class_name="flex flex-col gap-2",
              ),
              class_name="bg-slate-50 border border-slate-200 rounded-lg p-3",
            ),
          ),
          rx.el.div(
            rx.el.span("Notas", class_name=f"{TYPOGRAPHY['caption']} uppercase tracking-wide"),
            rx.el.p(
              rx.cond(
                State.cashbox_log_selected["notes"] == "",
                "Sin notas adicionales.",
                State.cashbox_log_selected["notes"],
              ),
              class_name=TYPOGRAPHY["body"],
            ),
            class_name="flex flex-col gap-1",
          ),
          class_name="flex flex-col gap-4",
        ),
      ),
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cerrar",
        on_click=State.close_cashbox_log_modal,
        class_name=BUTTON_STYLES["secondary"],
      ),
      class_name="flex justify-end pt-2",
    ),
  )


def petty_cash_modal() -> rx.Component:
  return modal_container(
    is_open=State.petty_cash_modal_open,
    on_close=State.close_petty_cash_modal,
    title=rx.cond(
      State.petty_cash_type == "egreso",
      "Registrar Egreso",
      "Registrar Ingreso",
    ),
    description=rx.cond(
      State.petty_cash_type == "egreso",
      "Detalle del gasto o salida de dinero de la caja chica.",
      "Detalle del ingreso o entrada de dinero a la caja chica.",
    ),
    children=[
      rx.el.div(
        # ── Tipo de movimiento ─────────────────────────────────────────
        rx.el.div(
          rx.el.label("Tipo de movimiento", class_name=TYPOGRAPHY["label"]),
          rx.el.div(
            rx.el.button(
              rx.icon("circle-arrow-down", class_name="w-4 h-4 shrink-0"),
              "Egreso",
              on_click=State.set_petty_cash_type("egreso"),
              class_name=rx.cond(
                State.petty_cash_type == "egreso",
                "flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-semibold bg-red-600 text-white shadow-sm transition-colors",
                "flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium bg-white text-slate-600 hover:bg-slate-100 transition-colors border border-slate-200",
              ),
            ),
            rx.el.button(
              rx.icon("circle-arrow-up", class_name="w-4 h-4 shrink-0"),
              "Ingreso",
              on_click=State.set_petty_cash_type("ingreso"),
              class_name=rx.cond(
                State.petty_cash_type == "ingreso",
                "flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-semibold bg-green-600 text-white shadow-sm transition-colors",
                "flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium bg-white text-slate-600 hover:bg-slate-100 transition-colors border border-slate-200",
              ),
            ),
            class_name="flex gap-2 p-1 bg-slate-50 rounded-xl border border-slate-200",
          ),
          class_name="flex flex-col gap-2",
        ),
        # ── Categoría ──────────────────────────────────────────────────
        rx.el.div(
          rx.el.label("Categoría", class_name=TYPOGRAPHY["label"]),
          rx.el.select(
            rx.el.option("Limpieza",            value="Limpieza"),
            rx.el.option("Mantenimiento",       value="Mantenimiento"),
            rx.el.option("Viáticos",            value="Viáticos"),
            rx.el.option("Alimentación",        value="Alimentación"),
            rx.el.option("Transporte",          value="Transporte"),
            rx.el.option("Material de Oficina", value="Material de Oficina"),
            rx.el.option("Servicios",           value="Servicios"),
            rx.el.option("Reposición de Caja",  value="Reposición de Caja"),
            rx.el.option("Devolución",          value="Devolución"),
            rx.el.option("Otro",                value="Otro"),
            default_value=State.petty_cash_category,
            on_change=State.set_petty_cash_category,
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-2",
        ),
        # ── Motivo ─────────────────────────────────────────────────────
        form_textarea(
          label="Motivo / Descripción",
          default_value=State.petty_cash_reason,
          on_blur=State.set_petty_cash_reason,
          placeholder=rx.cond(
            State.petty_cash_type == "egreso",
            "Ej: Compra de útiles de limpieza",
            "Ej: Reposición de fondo de caja chica",
          ),
        ),
        # ── Cantidad + Unidad ──────────────────────────────────────────
        rx.el.div(
          rx.el.div(
            rx.el.label("Cantidad", class_name=TYPOGRAPHY["label"]),
            rx.el.input(
              type="number",
              step="0.01",
              default_value=State.petty_cash_quantity,
              on_blur=State.set_petty_cash_quantity,
              class_name=INPUT_STYLES["default"],
            ),
            class_name="flex flex-col gap-2"
          ),
          rx.el.div(
            rx.el.label("Unidad", class_name=TYPOGRAPHY["label"]),
            rx.el.select(
              rx.foreach(State.units, lambda u: rx.el.option(u, value=u)),
              default_value=State.petty_cash_unit,
              on_change=State.set_petty_cash_unit,
              class_name=INPUT_STYLES["default"],
            ),
            class_name="flex flex-col gap-2"
          ),
          class_name="grid grid-cols-1 sm:grid-cols-2 gap-4"
        ),
        # ── Costo unitario + Total ─────────────────────────────────────
        rx.el.div(
          rx.el.div(
            rx.el.label("Costo Unitario", class_name=TYPOGRAPHY["label"]),
            rx.el.div(
              rx.el.span(State.currency_symbol, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 font-medium"),
              rx.el.input(
                type="number",
                step="0.01",
                default_value=State.petty_cash_cost,
                on_blur=State.set_petty_cash_cost,
                placeholder="0.00",
                class_name=f"{INPUT_STYLES['default']} pl-8 pr-4",
              ),
              class_name="relative"
            ),
            class_name="flex flex-col gap-2"
          ),
          rx.el.div(
            rx.el.label("Total", class_name=TYPOGRAPHY["label"]),
            rx.el.div(
              rx.el.span(State.currency_symbol, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 font-medium"),
              rx.el.input(
                type="number",
                step="0.01",
                value=State.petty_cash_amount,
                read_only=True,
                placeholder="0.00",
                class_name=f"{INPUT_STYLES['disabled']} pl-8 pr-4",
              ),
              class_name="relative"
            ),
            class_name="flex flex-col gap-2"
          ),
          class_name="grid grid-cols-1 sm:grid-cols-2 gap-4"
        ),
        class_name="flex flex-col gap-4 py-4"
      )
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_petty_cash_modal,
        class_name=BUTTON_STYLES["secondary"],
      ),
      rx.el.button(
        rx.cond(
          State.petty_cash_type == "egreso",
          rx.icon("circle-arrow-down", class_name="h-4 w-4"),
          rx.icon("circle-arrow-up", class_name="h-4 w-4"),
        ),
        rx.cond(
          State.petty_cash_type == "egreso",
          "Registrar Egreso",
          "Registrar Ingreso",
        ),
        on_click=State.add_petty_cash_movement,
        class_name=rx.cond(
          State.petty_cash_type == "egreso",
          "inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-red-600 hover:bg-red-700 text-white transition-colors shadow-sm",
          "inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-green-600 hover:bg-green-700 text-white transition-colors shadow-sm",
        ),
      ),
      class_name="flex justify-end gap-3 pt-2",
    )
  )


def petty_cash_edit_modal() -> rx.Component:
  """Modal para editar un movimiento de caja chica existente."""
  return modal_container(
    is_open=State.petty_cash_edit_modal_open,
    on_close=State.close_petty_cash_edit_modal,
    title=rx.cond(
      State.petty_cash_edit_type == "egreso",
      "Editar Egreso",
      "Editar Ingreso",
    ),
    description="Corregí el concepto, categoría, cantidad o costo del movimiento.",
    children=[
      # key=edit_id fuerza remount completo al abrir un item diferente,
      # lo que garantiza que default_value se inicialice con los valores correctos.
      rx.el.div(
        # ── Tipo (solo visual, no editable) ───────────────────────────
        rx.el.div(
          rx.cond(
            State.petty_cash_edit_type == "egreso",
            rx.el.span(
              rx.icon("circle-arrow-down", class_name="w-4 h-4"),
              "Egreso",
              class_name="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold bg-red-100 text-red-700 border border-red-200",
            ),
            rx.el.span(
              rx.icon("circle-arrow-up", class_name="w-4 h-4"),
              "Ingreso",
              class_name="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold bg-green-100 text-green-700 border border-green-200",
            ),
          ),
          rx.el.span(
            "El tipo no se puede cambiar.",
            class_name="text-xs text-slate-400 ml-2",
          ),
          class_name="flex items-center",
        ),
        # ── Categoría ──────────────────────────────────────────────────
        rx.el.div(
          rx.el.label("Categoría", class_name="text-sm font-medium text-slate-700"),
          rx.el.select(
            rx.el.option("Limpieza",            value="Limpieza"),
            rx.el.option("Mantenimiento",       value="Mantenimiento"),
            rx.el.option("Viáticos",            value="Viáticos"),
            rx.el.option("Alimentación",        value="Alimentación"),
            rx.el.option("Transporte",          value="Transporte"),
            rx.el.option("Material de Oficina", value="Material de Oficina"),
            rx.el.option("Servicios",           value="Servicios"),
            rx.el.option("Reposición de Caja",  value="Reposición de Caja"),
            rx.el.option("Devolución",          value="Devolución"),
            rx.el.option("Otro",                value="Otro"),
            default_value=State.petty_cash_edit_category,
            on_change=State.set_petty_cash_edit_category,
            class_name=INPUT_STYLES["default"],
          ),
          class_name="flex flex-col gap-2",
        ),
        # ── Motivo — on_blur para evitar que el cursor salte al final ─
        rx.el.div(
          rx.el.label("Motivo / Descripción", class_name="text-sm font-medium text-slate-700"),
          rx.el.textarea(
            default_value=State.petty_cash_edit_reason,
            on_blur=State.set_petty_cash_edit_reason,
            placeholder="Ej: Compra de útiles de limpieza",
            rows=3,
            class_name=f"{INPUT_STYLES['default']} resize-none",
          ),
          class_name="flex flex-col gap-2",
        ),
        # ── Cantidad + Unidad ──────────────────────────────────────────
        rx.el.div(
          rx.el.div(
            rx.el.label("Cantidad", class_name="text-sm font-medium text-slate-700"),
            rx.el.input(
              type="number",
              step="0.01",
              default_value=State.petty_cash_edit_quantity,
              on_blur=State.set_petty_cash_edit_quantity,
              class_name=INPUT_STYLES["default"],
            ),
            class_name="flex flex-col gap-2",
          ),
          rx.el.div(
            rx.el.label("Unidad", class_name="text-sm font-medium text-slate-700"),
            rx.el.select(
              rx.foreach(State.units, lambda u: rx.el.option(u, value=u)),
              default_value=State.petty_cash_edit_unit,
              on_change=State.set_petty_cash_edit_unit,
              class_name=INPUT_STYLES["default"],
            ),
            class_name="flex flex-col gap-2",
          ),
          class_name="grid grid-cols-1 sm:grid-cols-2 gap-4",
        ),
        # ── Costo Unitario + Total ─────────────────────────────────────
        rx.el.div(
          rx.el.div(
            rx.el.label("Costo Unitario", class_name="text-sm font-medium text-slate-700"),
            rx.el.div(
              rx.el.span(State.currency_symbol, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 font-medium"),
              rx.el.input(
                type="number",
                step="0.01",
                default_value=State.petty_cash_edit_cost,
                on_blur=State.set_petty_cash_edit_cost,
                placeholder="0.00",
                class_name=f"{INPUT_STYLES['default']} pl-8 pr-4",
              ),
              class_name="relative",
            ),
            class_name="flex flex-col gap-2",
          ),
          rx.el.div(
            rx.el.label("Total", class_name="text-sm font-medium text-slate-700"),
            rx.el.div(
              rx.el.span(State.currency_symbol, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 font-medium"),
              rx.el.input(
                type="number",
                step="0.01",
                value=State.petty_cash_edit_amount,
                read_only=True,
                placeholder="0.00",
                class_name=f"{INPUT_STYLES['disabled']} pl-8 pr-4",
              ),
              class_name="relative",
            ),
            class_name="flex flex-col gap-2",
          ),
          class_name="grid grid-cols-1 sm:grid-cols-2 gap-4",
        ),
        key=State.petty_cash_edit_id,
        class_name="flex flex-col gap-4 py-4",
      )
    ],
    footer=rx.el.div(
      rx.el.button(
        "Cancelar",
        on_click=State.close_petty_cash_edit_modal,
        class_name=BUTTON_STYLES["secondary"],
      ),
      rx.el.button(
        rx.icon("save", class_name="h-4 w-4"),
        "Guardar Cambios",
        on_click=State.save_petty_cash_edit,
        class_name=BUTTON_STYLES["primary"],
      ),
      class_name="flex justify-end gap-3 pt-2",
    ),
  )
