import reflex as rx
from typing import Callable

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  TABLE_STYLES,
  empty_state,
  pagination_controls,
  page_title,
  permission_guard,
)

PAYMENT_METHOD_OPTIONS = [
  "Efectivo",
  "Transferencia",
  "Yape",
  "Plin",
  "T. Debito",
  "T. Credito",
  "Pago Mixto",
]


def stats_dashboard_component(
  pagadas: rx.Var[int],
  pendientes: rx.Var[int],
  export_event: Callable,
  overdue: rx.Var[int] | None = None,
  paid_click: Callable | None = None,
  pending_click: Callable | None = None,
  overdue_click: Callable | None = None,
) -> rx.Component:
  cards = [
    rx.el.div(
      rx.el.div(
        rx.el.div(
          rx.icon(
            "circle-check",
            class_name="h-5 w-5 text-emerald-600",
          ),
          class_name="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-50",
        ),
        rx.el.div(
          rx.el.p(
            "Cuotas Pagadas",
            class_name="text-sm font-semibold text-slate-600",
          ),
          rx.el.p(
            pagadas.to_string(),
            class_name="text-3xl font-bold text-slate-900",
          ),
          class_name="flex flex-col gap-1",
        ),
        class_name="flex items-center gap-3",
      ),
      on_click=paid_click if paid_click else None,
      class_name=(
        "bg-white rounded-xl border border-slate-200 shadow-sm p-4 "
        "cursor-pointer hover:bg-slate-50 transition-colors"
        if paid_click
        else "bg-white rounded-xl border border-slate-200 shadow-sm p-4"
      ),
    ),
    rx.el.div(
      rx.el.div(
        rx.el.div(
          rx.icon(
            "clock",
            class_name="h-5 w-5 text-amber-500",
          ),
          class_name="flex h-9 w-9 items-center justify-center rounded-full bg-amber-50",
        ),
        rx.el.div(
          rx.el.p(
            "Cuotas Pendientes",
            class_name="text-sm font-semibold text-slate-600",
          ),
          rx.el.p(
            pendientes.to_string(),
            class_name="text-3xl font-bold text-slate-900",
          ),
          class_name="flex flex-col gap-1",
        ),
        class_name="flex items-center gap-3",
      ),
      on_click=pending_click if pending_click else None,
      class_name=(
        "bg-white rounded-xl border border-slate-200 shadow-sm p-4 "
        "cursor-pointer hover:bg-slate-50 transition-colors"
        if pending_click
        else "bg-white rounded-xl border border-slate-200 shadow-sm p-4"
      ),
    ),
  ]

  if overdue is not None:
    cards.append(
      rx.el.div(
        rx.el.div(
          rx.el.div(
            rx.icon(
              "triangle-alert",
              class_name="h-5 w-5 text-red-600",
            ),
            class_name="flex h-9 w-9 items-center justify-center rounded-full bg-red-50",
          ),
          rx.el.div(
            rx.el.p(
              "Cuotas Vencidas",
              class_name="text-sm font-semibold text-rose-700",
            ),
            rx.el.p(
              overdue.to_string(),
              class_name="text-3xl font-bold text-rose-700",
            ),
            class_name="flex flex-col gap-1",
          ),
          class_name="flex items-center gap-3",
        ),
        on_click=overdue_click if overdue_click else None,
        class_name=(
          "bg-red-50/70 rounded-xl border border-red-200 shadow-sm p-4 "
          "cursor-pointer hover:bg-red-50 transition-colors"
        ),
      )
    )

  cards.append(
    rx.el.div(
      rx.el.div(
        rx.el.span(
          "Reporte de Cuentas",
          class_name="text-xs font-semibold uppercase tracking-wide text-indigo-600",
        ),
        rx.el.p(
          "Descarga el reporte completo de cuotas.",
          class_name="text-sm font-semibold text-slate-800",
        ),
        rx.el.p(
          "Incluye fecha, cliente, concepto, monto y estado.",
          class_name="text-xs text-slate-500",
        ),
        class_name="flex flex-col gap-1",
      ),
            rx.el.button(
                rx.icon("download", class_name="h-4 w-4"),
                "Exportar",
                on_click=export_event,
                class_name="w-full h-10 flex items-center justify-center gap-2 rounded-md bg-indigo-600 px-4 text-white font-medium hover:bg-indigo-700",
            ),
      class_name="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex flex-col gap-4",
    ),
  )

  grid_cols = (
    "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 my-4"
    if overdue is not None
    else "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 my-4"
  )
  return rx.grid(
    *cards,
    columns="1",
    class_name=grid_cols,
  )


def debtor_row(client: rx.Var[dict]) -> rx.Component:
  return rx.el.tr(
    rx.el.td(client["name"], class_name="py-3 px-4 font-medium text-slate-900"),
    rx.el.td(client["dni"], class_name="py-3 px-4 hidden md:table-cell"),
    rx.el.td(
      rx.cond(
        client["phone"] == None,
        rx.el.span("-", class_name="text-slate-400"),
        client["phone"],
      ),
      class_name="py-3 px-4 hidden md:table-cell",
    ),
    rx.el.td(
      State.currency_symbol,
      client["current_debt"].to_string(),
      class_name="py-3 px-4 text-right font-semibold text-rose-600",
    ),
        rx.el.td(
            rx.el.div(
                rx.el.button(
                    rx.icon("eye", class_name="h-4 w-4"),
                    "Ver Cuenta",
                    on_click=lambda _, client=client: State.open_detail(client),
                    class_name=BUTTON_STYLES["link_primary"] + " h-10",
                ),
                class_name="flex h-full items-center justify-center",
            ),
            class_name="py-3 px-4 align-middle",
        ),
    class_name="border-b hover:bg-slate-50 transition-colors",
  )


def installment_overview_row(installment: rx.Var[dict]) -> rx.Component:
  return rx.el.tr(
    rx.el.td(
      installment["client_name"],
      class_name="py-3 px-4 font-medium text-slate-900",
    ),
    rx.el.td(
      installment["client_dni"],
      class_name="py-3 px-4 text-slate-600 hidden md:table-cell",
    ),
    rx.el.td(
      rx.el.span(
        installment["due_date"],
        class_name=rx.cond(
          installment["is_overdue"],
          "text-red-600 font-semibold",
          "text-slate-700",
        ),
      ),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      State.currency_symbol,
      installment["amount"].to_string(),
      class_name="py-3 px-4 text-right",
    ),
    rx.el.td(
      State.currency_symbol,
      installment["paid_amount"].to_string(),
      class_name="py-3 px-4 text-right text-emerald-700",
    ),
    rx.el.td(
      State.currency_symbol,
      installment["pending_amount"].to_string(),
      class_name=rx.cond(
        installment["has_pending"],
        "py-3 px-4 text-right font-semibold text-amber-700",
        "py-3 px-4 text-right text-slate-500",
      ),
    ),
    rx.el.td(
      rx.el.span(
        installment["status_label"],
        class_name=rx.match(
          installment["status"],
          (
            "paid",
            "px-2 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-700",
          ),
          (
            "partial",
            "px-2 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-700",
          ),
          (
            "pending",
            "px-2 py-1 text-xs font-semibold rounded-full bg-slate-100 text-slate-700",
          ),
          "px-2 py-1 text-xs font-semibold rounded-full bg-slate-100 text-slate-700",
        ),
      ),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      rx.cond(
        installment["client"] != None,
        rx.el.button(
          rx.icon("eye", class_name="h-4 w-4"),
          "Ver Cuenta",
          on_click=lambda _, client=installment["client"]: State.open_detail(client),
          class_name=BUTTON_STYLES["link_primary"] + " h-10",
        ),
        rx.el.span("-", class_name="text-slate-400"),
      ),
      class_name="py-3 px-4 text-center",
    ),
    class_name=rx.cond(
      installment["is_overdue"],
      "border-b bg-red-50/40",
      "border-b",
    ),
  )


def installment_action(installment: rx.Var[dict]) -> rx.Component:
  return rx.el.div(
    rx.cond(
      installment["is_paid"],
      rx.el.span("Pagado", class_name="text-xs text-slate-400"),
      rx.el.button(
        rx.icon("credit-card", class_name="h-4 w-4"),
        "Pagar",
        on_click=lambda _, installment_id=installment["id"], amount=installment[
          "pending_amount"
        ]: State.prepare_payment(installment_id, amount),
        class_name=BUTTON_STYLES["link_primary"],
      ),
    ),
    rx.cond(
      State.selected_installment_id == installment["id"],
      rx.el.div(
        rx.el.div(
          rx.el.span(
            "Metodo de pago",
            class_name="text-[11px] uppercase tracking-wide text-slate-500",
          ),
          rx.el.select(
            *[
              rx.el.option(option, value=option)
              for option in PAYMENT_METHOD_OPTIONS
            ],
            value=State.installment_payment_method,
            on_change=State.set_installment_payment_method,
            class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.span(
            State.currency_symbol,
            class_name="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm",
          ),
          rx.el.input(
            type="number",
            step="0.01",
            min="0",
            default_value=State.payment_amount,
            on_blur=State.set_payment_amount,
            placeholder="Monto",
            class_name="w-full h-10 pl-8 pr-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
          ),
          class_name="relative",
        ),
        rx.el.div(
          rx.el.button(
            "Confirmar Pago",
            on_click=State.submit_payment,
            disabled=State.is_loading,
            loading=State.is_loading,
            class_name=BUTTON_STYLES["success_sm"],
          ),
          rx.el.button(
            "Cancelar",
            on_click=State.clear_payment_selection,
            class_name=BUTTON_STYLES["secondary_sm"],
          ),
          class_name="flex flex-col gap-2 sm:flex-row",
        ),
        class_name="mt-2 flex flex-col gap-3 w-full",
      ),
      rx.fragment(),
    ),
    class_name="flex flex-col items-start gap-2",
  )


def installment_row(installment: rx.Var[dict]) -> rx.Component:
  return rx.el.tr(
    rx.el.td(
      installment["number"].to_string(),
      class_name="py-3 px-4 text-center font-medium",
    ),
    rx.el.td(
      rx.el.span(
        installment["due_date"],
        class_name=rx.cond(
          installment["is_overdue"],
          "text-red-600 font-semibold",
          "text-slate-700",
        ),
      ),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      State.currency_symbol,
      installment["amount"].to_string(),
      class_name="py-3 px-4 text-right",
    ),
    rx.el.td(
      State.currency_symbol,
      installment["paid_amount"].to_string(),
      class_name="py-3 px-4 text-right text-emerald-700",
    ),
    rx.el.td(
      State.currency_symbol,
      installment["pending_amount"].to_string(),
      class_name=rx.cond(
        installment["has_pending"],
        "py-3 px-4 text-right font-semibold text-amber-700",
        "py-3 px-4 text-right text-slate-500",
      ),
    ),
    rx.el.td(
      rx.el.span(
        installment["status_label"],
        class_name=rx.match(
          installment["status"],
          (
            "paid",
            "px-2 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-700",
          ),
          (
            "partial",
            "px-2 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-700",
          ),
          (
            "pending",
            "px-2 py-1 text-xs font-semibold rounded-full bg-slate-100 text-slate-700",
          ),
          "px-2 py-1 text-xs font-semibold rounded-full bg-slate-100 text-slate-700",
        ),
      ),
      class_name="py-3 px-4",
    ),
    rx.el.td(
      installment_action(installment),
      class_name="py-3 px-4 min-w-[220px]",
    ),
    class_name=rx.cond(
      installment["is_overdue"],
      "border-b bg-red-50/40",
      "border-b",
    ),
  )


def cuentas_detail_modal() -> rx.Component:
  return rx.cond(
    State.show_payment_modal,
    rx.el.div(
      rx.el.div(
        on_click=State.close_detail,
        class_name="fixed inset-0 bg-black/40 backdrop-blur-sm modal-overlay",
      ),
      rx.el.div(
        rx.el.div(
          rx.cond(
            State.selected_client == None,
            rx.el.p(
              "Cliente no disponible.",
              class_name="text-sm text-slate-600",
            ),
            rx.el.div(
              rx.el.div(
                rx.el.h3(
                  State.selected_client["name"],
                  class_name="text-xl font-semibold text-slate-900",
                ),
                rx.el.div(
                  rx.el.span(
                    "DNI:",
                    class_name="text-xs uppercase tracking-wide text-slate-400",
                  ),
                  rx.el.span(
                    State.selected_client["dni"],
                    class_name="text-sm text-slate-700 font-medium",
                  ),
                  class_name="flex items-center gap-2",
                ),
                rx.el.div(
                  rx.el.span(
                    "Telefono:",
                    class_name="text-xs uppercase tracking-wide text-slate-400",
                  ),
                  rx.el.span(
                    rx.cond(
                      State.selected_client["phone"] == None,
                      "-",
                      State.selected_client["phone"],
                    ),
                    class_name="text-sm text-slate-700 font-medium",
                  ),
                  class_name="flex items-center gap-2",
                ),
                class_name="flex flex-col gap-2",
              ),
              rx.el.div(
                rx.el.span(
                  "Deuda Total",
                  class_name="text-xs uppercase tracking-wide text-slate-400",
                ),
                rx.el.p(
                  State.currency_symbol,
                  State.selected_client["current_debt"].to_string(),
                  class_name="text-3xl font-bold text-rose-600",
                ),
                class_name="flex flex-col items-end",
              ),
              class_name="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between",
            ),
          ),
          rx.el.button(
            rx.icon("x", class_name="h-4 w-4"),
            on_click=State.close_detail,
            class_name="p-2 rounded-full hover:bg-slate-100",
          ),
          class_name="flex items-start justify-between gap-4",
        ),
        rx.divider(color="slate-100"),
        rx.el.div(
          stats_dashboard_component(
            pagadas=State.current_client_pagadas,
            pendientes=State.current_client_pendientes,
            export_event=State.export_cuentas_excel(
              State.selected_client_id
            ),
          ),
          rx.el.div(
            rx.el.h4(
              "Estado de Cuenta",
              class_name="text-lg font-semibold text-slate-800",
            ),
            rx.el.div(
              rx.el.table(
                                rx.el.thead(
                                    rx.el.tr(
                                        rx.el.th(
                                            "Nro",
                                            class_name=f"{TABLE_STYLES['header_cell']} text-center",
                                        ),
                                        rx.el.th(
                                            "Vencimiento",
                                            class_name=TABLE_STYLES["header_cell"],
                                        ),
                                        rx.el.th(
                                            "Total",
                                            class_name=f"{TABLE_STYLES['header_cell']} text-right",
                                        ),
                                        rx.el.th(
                                            "Pagado",
                                            class_name=f"{TABLE_STYLES['header_cell']} text-right",
                                        ),
                                        rx.el.th(
                                            "Pendiente",
                                            class_name=f"{TABLE_STYLES['header_cell']} text-right",
                                        ),
                                        rx.el.th(
                                            "Estado",
                                            class_name=TABLE_STYLES["header_cell"],
                                        ),
                                        rx.el.th(
                                            "Acciones",
                                            class_name=TABLE_STYLES["header_cell"],
                                        ),
                                        class_name=TABLE_STYLES["header"],
                                    )
                                ),
                rx.el.tbody(
                  rx.foreach(
                    State.client_installments_view,
                    installment_row,
                  )
                ),
                class_name="min-w-full text-sm",
              ),
              rx.cond(
                State.client_installments_view.length() == 0,
                empty_state(
                  "Este cliente no tiene cuotas registradas."
                ),
                rx.fragment(),
              ),
                            class_name="overflow-x-auto rounded-xl border border-slate-200",
            ),
            class_name="flex flex-col gap-4",
          ),
          class_name="flex-1 overflow-y-auto min-h-0 space-y-6",
        ),
        class_name="relative z-10 w-full max-w-5xl rounded-xl bg-white p-6 shadow-xl max-h-[90vh] overflow-hidden flex flex-col gap-6",
      ),
      class_name="fixed inset-0 z-50 flex items-start sm:items-center justify-center px-4 py-6 overflow-hidden",
    ),
    rx.fragment(),
  )


def cuentas_page() -> rx.Component:
  content = rx.fragment(
    rx.el.div(
      page_title(
        "CUENTAS CORRIENTES",
        "Gestiona clientes con saldo pendiente y registra pagos por cuota.",
      ),
      stats_dashboard_component(
        pagadas=State.total_pagadas,
        pendientes=State.total_pendientes,
        export_event=State.export_cuentas_excel(None),
        overdue=State.overdue_installments_count,
        paid_click=State.set_filter_paid,
        pending_click=State.set_filter_pending,
        overdue_click=State.set_filter_overdue,
      ),
      rx.el.div(
        rx.el.div(
          rx.el.button(
            "Clientes con deuda",
            on_click=lambda _: State.set_view_mode("clients"),
            class_name=rx.cond(
              State.view_mode == "clients",
              "px-4 py-2 rounded-md bg-indigo-600 text-white text-sm font-medium",
              "px-4 py-2 rounded-md border border-slate-200 text-slate-600 text-sm hover:bg-slate-50",
            ),
          ),
          rx.el.button(
            "Cuotas",
            on_click=lambda _: State.set_view_mode("installments"),
            class_name=rx.cond(
              State.view_mode == "installments",
              "px-4 py-2 rounded-md bg-indigo-600 text-white text-sm font-medium",
              "px-4 py-2 rounded-md border border-slate-200 text-slate-600 text-sm hover:bg-slate-50",
            ),
          ),
          class_name="flex flex-wrap gap-2",
        ),
        rx.el.div(
          rx.cond(
            State.view_mode == "installments",
            rx.el.div(
              rx.el.span(
                rx.match(
                  State.filter_mode,
                  ("paid", "Filtro: Pagadas"),
                  ("pending", "Filtro: Pendientes"),
                  ("overdue", "Filtro: Vencidas"),
                  "Filtro: Todas",
                ),
                class_name="text-xs font-semibold text-slate-500 uppercase tracking-wide",
              ),
              rx.el.button(
                "Ver todas",
                on_click=State.set_filter_all,
                class_name="text-xs font-semibold text-indigo-600 hover:text-indigo-700",
              ),
              class_name="flex items-center gap-3",
            ),
            rx.el.span(
              "Listado: Clientes con saldo pendiente",
              class_name="text-xs font-semibold text-slate-500 uppercase tracking-wide",
            ),
          ),
        ),
        class_name="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2",
      ),
      rx.el.div(
        rx.cond(
          State.view_mode == "clients",
          rx.el.div(
            rx.el.table(
              rx.el.thead(
                rx.el.tr(
                  rx.el.th(
                    "Cliente", class_name=TABLE_STYLES["header_cell"]
                  ),
                  rx.el.th(
                    "DNI", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"
                  ),
                  rx.el.th(
                    "Telefono", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"
                  ),
                  rx.el.th(
                    "Deuda",
                    class_name=f"{TABLE_STYLES['header_cell']} text-right",
                  ),
                  rx.el.th(
                    "Acciones",
                    class_name=f"{TABLE_STYLES['header_cell']} text-center",
                  ),
                  class_name=TABLE_STYLES["header"],
                )
              ),
              rx.el.tbody(rx.foreach(State.paginated_debtors, debtor_row)),
              class_name="min-w-full text-sm",
            ),
            rx.cond(
              State.debtors.length() == 0,
              empty_state("No hay clientes con deuda registrada."),
              rx.fragment(),
            ),
            rx.cond(
              State.debtors_total_pages > 1,
              pagination_controls(
                current_page=State.debtors_page,
                total_pages=State.debtors_total_pages,
                on_prev=State.prev_debtors_page,
                on_next=State.next_debtors_page,
              ),
              rx.fragment(),
            ),
            class_name="flex flex-col gap-4",
          ),
          rx.el.div(
            rx.el.table(
              rx.el.thead(
                rx.el.tr(
                  rx.el.th(
                    "Cliente", class_name=TABLE_STYLES["header_cell"]
                  ),
                  rx.el.th(
                    "DNI", class_name=f"{TABLE_STYLES['header_cell']} hidden md:table-cell"
                  ),
                  rx.el.th(
                    "Vencimiento", class_name=TABLE_STYLES["header_cell"]
                  ),
                  rx.el.th(
                    "Monto",
                    class_name=f"{TABLE_STYLES['header_cell']} text-right",
                  ),
                  rx.el.th(
                    "Pagado",
                    class_name=f"{TABLE_STYLES['header_cell']} text-right hidden md:table-cell",
                  ),
                  rx.el.th(
                    "Pendiente",
                    class_name=f"{TABLE_STYLES['header_cell']} text-right",
                  ),
                  rx.el.th(
                    "Estado",
                    class_name=TABLE_STYLES["header_cell"],
                  ),
                  rx.el.th(
                    "Acciones",
                    class_name=f"{TABLE_STYLES['header_cell']} text-center",
                  ),
                  class_name=TABLE_STYLES["header"],
                )
              ),
              rx.el.tbody(
                rx.foreach(
                  State.paginated_installments_rows,
                  installment_overview_row,
                )
              ),
              class_name="min-w-full text-sm",
            ),
            rx.cond(
              State.installments_rows.length() == 0,
              empty_state("No hay cuotas registradas para este filtro."),
              rx.fragment(),
            ),
            rx.cond(
              State.installments_total_pages > 1,
              pagination_controls(
                current_page=State.installments_page,
                total_pages=State.installments_total_pages,
                on_prev=State.prev_installments_page,
                on_next=State.next_installments_page,
              ),
              rx.fragment(),
            ),
            class_name="flex flex-col gap-4",
          ),
        ),
        class_name="bg-white p-4 sm:p-6 rounded-xl border border-slate-200 shadow-sm overflow-x-auto flex flex-col gap-4",
      ),
      class_name="flex flex-col gap-6 p-4 sm:p-6 w-full",
    ),
    cuentas_detail_modal(),
    on_mount=State.load_debtors_background,
  )
  return permission_guard(
    has_permission=State.can_view_cuentas,
    content=content,
    redirect_message="Acceso denegado a Cuentas Corrientes",
  )
