"""Página de Documentos Fiscales — Dashboard completo de comprobantes electrónicos.

Permite al usuario ver, filtrar y gestionar todos los documentos fiscales emitidos
(boletas, facturas, notas de crédito/débito) con soporte para reintento manual
y emisión de Notas de Crédito para anular comprobantes autorizados.
"""
import reflex as rx
from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    TABLE_STYLES,
    page_title,
    permission_guard,
)


# ════════════════════════════════════════════════════════════
# COMPONENTES DE BADGE
# ════════════════════════════════════════════════════════════

def _status_badge(status: rx.Var) -> rx.Component:
    """Badge coloreado según el estado fiscal."""
    return rx.match(
        status,
        ("authorized", rx.el.span(
            "Autorizado",
            class_name="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800",
        )),
        ("pending", rx.el.span(
            "Pendiente",
            class_name="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800",
        )),
        ("sent", rx.el.span(
            "Enviado",
            class_name="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800",
        )),
        ("error", rx.el.span(
            "Error",
            class_name="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800",
        )),
        ("rejected", rx.el.span(
            "Rechazado",
            class_name="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-700",
        )),
        rx.el.span(
            status,
            class_name="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700",
        ),
    )


def _receipt_badge(receipt_type: rx.Var) -> rx.Component:
    """Badge según el tipo de comprobante."""
    return rx.match(
        receipt_type,
        ("boleta", rx.el.span(
            "Boleta",
            class_name="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-sky-100 text-sky-800",
        )),
        ("factura", rx.el.span(
            "Factura",
            class_name="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-800",
        )),
        ("nota_credito", rx.el.span(
            "NC",
            class_name="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800",
        )),
        ("nota_debito", rx.el.span(
            "ND",
            class_name="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800",
        )),
        rx.el.span(
            receipt_type,
            class_name="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700",
        ),
    )


# ════════════════════════════════════════════════════════════
# FILTROS
# ════════════════════════════════════════════════════════════

def _fiscal_filters() -> rx.Component:
    """Barra de filtros para el dashboard fiscal."""
    return rx.el.div(
        # ── Fila de filtros ─────────────────────────────────
        rx.el.div(
            # Estado
            rx.el.div(
                rx.el.label("Estado", class_name="text-sm font-medium text-slate-600"),
                rx.el.select(
                    rx.el.option("Todos los estados", value="todos"),
                    rx.el.option("Autorizado", value="authorized"),
                    rx.el.option("Pendiente", value="pending"),
                    rx.el.option("Enviado", value="sent"),
                    rx.el.option("Error", value="error"),
                    rx.el.option("Rechazado", value="rejected"),
                    value=State.fiscal_docs_status_filter,
                    on_change=State.set_fiscal_docs_status_filter,
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                ),
                class_name="flex flex-col gap-1 min-w-[160px] flex-1",
            ),
            # Tipo de comprobante
            rx.el.div(
                rx.el.label("Tipo", class_name="text-sm font-medium text-slate-600"),
                rx.el.select(
                    rx.el.option("Todos los tipos", value="todos"),
                    rx.el.option("Boleta", value="boleta"),
                    rx.el.option("Factura", value="factura"),
                    rx.el.option("Nota de Crédito", value="nota_credito"),
                    rx.el.option("Nota de Débito", value="nota_debito"),
                    value=State.fiscal_docs_receipt_filter,
                    on_change=State.set_fiscal_docs_receipt_filter,
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                ),
                class_name="flex flex-col gap-1 min-w-[160px] flex-1",
            ),
            # Búsqueda
            rx.el.div(
                rx.el.label("Buscar", class_name="text-sm font-medium text-slate-600"),
                rx.el.input(
                    placeholder="Nro., receptor, RUC/CUIT...",
                    on_blur=State.set_fiscal_docs_search,
                    default_value=State.fiscal_docs_search,
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                ),
                class_name="flex flex-col gap-1 min-w-[200px] flex-1",
            ),
            # Fecha desde
            rx.el.div(
                rx.el.label("Desde", class_name="text-sm font-medium text-slate-600"),
                rx.el.input(
                    type="date",
                    value=State.fiscal_docs_date_from,
                    on_change=State.set_fiscal_docs_date_from,
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                ),
                class_name="flex flex-col gap-1 min-w-[145px]",
            ),
            # Fecha hasta
            rx.el.div(
                rx.el.label("Hasta", class_name="text-sm font-medium text-slate-600"),
                rx.el.input(
                    type="date",
                    value=State.fiscal_docs_date_to,
                    on_change=State.set_fiscal_docs_date_to,
                    class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                ),
                class_name="flex flex-col gap-1 min-w-[145px]",
            ),
            class_name="flex flex-wrap lg:flex-nowrap gap-3 items-end",
        ),
        # ── Botones de acción ────────────────────────────────
        rx.el.div(
            rx.el.button(
                rx.icon("search", class_name="h-4 w-4"),
                "Buscar",
                on_click=State.apply_fiscal_docs_filters,
                class_name=BUTTON_STYLES["primary"],
            ),
            rx.el.button(
                "Limpiar",
                on_click=State.reset_fiscal_docs_filters,
                class_name=BUTTON_STYLES["secondary"],
            ),
            class_name="flex flex-wrap gap-2 justify-end",
        ),
        class_name="flex flex-col gap-3 pb-4 border-b border-slate-200",
    )


# ════════════════════════════════════════════════════════════
# FILA DE TABLA
# ════════════════════════════════════════════════════════════

def _fiscal_doc_row(doc: rx.Var) -> rx.Component:
    """Fila de un documento fiscal en la tabla."""
    return rx.el.tr(
        # Fecha
        rx.el.td(
            doc["created_at"],
            class_name="py-3 px-4 text-sm text-slate-600 whitespace-nowrap",
        ),
        # Número
        rx.el.td(
            rx.el.span(
                doc["full_number"],
                class_name="font-mono font-medium text-slate-900 text-sm",
            ),
            class_name="py-3 px-4 whitespace-nowrap",
        ),
        # Tipo
        rx.el.td(
            _receipt_badge(doc["receipt_type"]),
            class_name="py-3 px-4",
        ),
        # Receptor
        rx.el.td(
            rx.el.div(
                rx.el.span(
                    doc["buyer_name"],
                    class_name="text-sm text-slate-800 font-medium block",
                ),
                rx.el.span(
                    doc["buyer_doc_number"],
                    class_name="text-xs text-slate-500",
                ),
                class_name="flex flex-col",
            ),
            class_name="py-3 px-4 min-w-[180px]",
        ),
        # Total
        rx.el.td(
            rx.el.span(
                State.currency_symbol,
                " ",
                doc["total_amount"],
                class_name="font-semibold tabular-nums text-slate-900",
            ),
            class_name="py-3 px-4 text-right whitespace-nowrap",
        ),
        # Estado
        rx.el.td(
            _status_badge(doc["status"]),
            class_name="py-3 px-4",
        ),
        # Reintentos
        rx.el.td(
            doc["retry_count"],
            class_name="py-3 px-4 text-center text-sm text-slate-500",
        ),
        # Acciones
        rx.el.td(
            rx.el.button(
                rx.icon("eye", class_name="h-4 w-4"),
                " Detalle",
                on_click=State.open_fiscal_doc_detail(doc["id"]),
                class_name=BUTTON_STYLES["link_primary"],
            ),
            class_name="py-3 px-4 text-center whitespace-nowrap",
        ),
        class_name="border-b border-slate-100 hover:bg-slate-50/80",
    )


# ════════════════════════════════════════════════════════════
# TABLA PRINCIPAL
# ════════════════════════════════════════════════════════════

def _fiscal_docs_table() -> rx.Component:
    """Tabla de documentos fiscales con carga dinámica."""
    return rx.el.div(
        rx.cond(
            State.fiscal_docs_loading,
            rx.el.div(
                rx.icon("loader-circle", class_name="h-8 w-8 text-indigo-500 animate-spin"),
                rx.el.p("Cargando documentos...", class_name="text-sm text-slate-500 mt-2"),
                class_name="flex flex-col items-center justify-center py-16",
            ),
            rx.cond(
                State.fiscal_docs_list,
                rx.el.div(
                    # Tabla
                    rx.el.div(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    rx.el.th("Fecha", class_name=TABLE_STYLES["header_cell"]),
                                    rx.el.th("Número", class_name=TABLE_STYLES["header_cell"]),
                                    rx.el.th("Tipo", class_name=TABLE_STYLES["header_cell"]),
                                    rx.el.th("Receptor", class_name=TABLE_STYLES["header_cell"]),
                                    rx.el.th(
                                        "Total",
                                        class_name=f"{TABLE_STYLES['header_cell']} text-right",
                                    ),
                                    rx.el.th("Estado", class_name=TABLE_STYLES["header_cell"]),
                                    rx.el.th(
                                        "Reintentos",
                                        class_name=f"{TABLE_STYLES['header_cell']} text-center",
                                    ),
                                    rx.el.th(
                                        "Acciones",
                                        class_name=f"{TABLE_STYLES['header_cell']} text-center",
                                    ),
                                ),
                                class_name=TABLE_STYLES["header"],
                            ),
                            rx.el.tbody(
                                rx.foreach(State.fiscal_docs_list, _fiscal_doc_row),
                            ),
                            class_name="w-full text-left border-collapse",
                        ),
                        class_name="overflow-x-auto",
                    ),
                    # Paginación
                    rx.el.div(
                        rx.el.span(
                            "Total: ",
                            rx.el.strong(State.fiscal_docs_total.to_string()),
                            " documentos",
                            class_name="text-sm text-slate-500",
                        ),
                        rx.el.div(
                            rx.el.button(
                                rx.icon("chevron-left", class_name="h-4 w-4"),
                                " Anterior",
                                on_click=State.fiscal_docs_prev_page,
                                disabled=~State.fiscal_docs_has_prev,
                                class_name=rx.cond(
                                    State.fiscal_docs_has_prev,
                                    BUTTON_STYLES["secondary"],
                                    f"{BUTTON_STYLES['secondary']} opacity-40 cursor-not-allowed",
                                ),
                            ),
                            rx.el.span(
                                State.fiscal_docs_page_display,
                                class_name="px-4 py-2 text-sm font-medium text-slate-700",
                            ),
                            rx.el.button(
                                "Siguiente ",
                                rx.icon("chevron-right", class_name="h-4 w-4"),
                                on_click=State.fiscal_docs_next_page,
                                disabled=~State.fiscal_docs_has_next,
                                class_name=rx.cond(
                                    State.fiscal_docs_has_next,
                                    BUTTON_STYLES["secondary"],
                                    f"{BUTTON_STYLES['secondary']} opacity-40 cursor-not-allowed",
                                ),
                            ),
                            class_name="flex items-center gap-2",
                        ),
                        class_name="flex items-center justify-between pt-4 mt-2 border-t border-slate-100",
                    ),
                    class_name="flex flex-col gap-2",
                ),
                # Estado vacío
                rx.el.div(
                    rx.icon("file-x", class_name="h-12 w-12 text-slate-300 mx-auto mb-3"),
                    rx.el.p(
                        "Sin documentos fiscales",
                        class_name="text-slate-600 font-medium text-center",
                    ),
                    rx.el.p(
                        "No se encontraron comprobantes con los filtros seleccionados.",
                        class_name="text-sm text-slate-400 text-center",
                    ),
                    class_name="flex flex-col items-center justify-center py-16",
                ),
            ),
        ),
    )


# ════════════════════════════════════════════════════════════
# MODAL DE DETALLE
# ════════════════════════════════════════════════════════════

def _fiscal_doc_detail_modal() -> rx.Component:
    """Modal de detalle de un documento fiscal con retry y NC."""
    doc = State.fiscal_doc_selected

    return rx.radix.primitives.dialog.root(
        rx.radix.primitives.dialog.portal(
            rx.radix.primitives.dialog.overlay(
                class_name="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
            ),
            rx.radix.primitives.dialog.content(
                rx.el.div(
                    # ── Header ──────────────────────────────────────
                    rx.el.div(
                        rx.el.div(
                            rx.el.div(
                                rx.icon("file-text", class_name="h-5 w-5 text-indigo-600"),
                                class_name="p-2 bg-indigo-100 rounded-lg",
                            ),
                            rx.el.div(
                                rx.el.h3(
                                    "Detalle del Comprobante Fiscal",
                                    class_name="text-lg font-semibold text-slate-800",
                                ),
                                rx.el.p(
                                    doc.get("full_number", ""),
                                    class_name="text-sm text-slate-500 font-mono",
                                ),
                                class_name="flex flex-col",
                            ),
                            class_name="flex items-center gap-3",
                        ),
                        rx.el.button(
                            rx.icon("x", class_name="h-5 w-5"),
                            on_click=State.close_fiscal_doc_detail,
                            class_name="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100",
                        ),
                        class_name="flex items-start justify-between pb-4 border-b border-slate-200",
                    ),

                    # ── Cuerpo ───────────────────────────────────────
                    rx.el.div(
                        # Estado, tipo y reintentos
                        rx.el.div(
                            rx.el.div(
                                rx.el.span("Estado", class_name="text-xs text-slate-500 uppercase tracking-wide block mb-1"),
                                _status_badge(doc.get("status", "")),
                            ),
                            rx.el.div(
                                rx.el.span("Tipo", class_name="text-xs text-slate-500 uppercase tracking-wide block mb-1"),
                                _receipt_badge(doc.get("receipt_type", "")),
                            ),
                            rx.el.div(
                                rx.el.span("Reintentos", class_name="text-xs text-slate-500 uppercase tracking-wide block mb-1"),
                                rx.el.span(doc.get("retry_count", "0"), class_name="text-sm font-semibold text-slate-800"),
                            ),
                            class_name="grid grid-cols-3 gap-4 p-4 bg-slate-50 rounded-lg",
                        ),

                        # Receptor
                        rx.el.div(
                            rx.el.h4("Receptor", class_name="text-sm font-semibold text-slate-700 mb-2"),
                            rx.el.div(
                                rx.el.div(
                                    rx.el.span("Nombre / Razón Social", class_name="text-xs text-slate-500"),
                                    rx.el.span(doc.get("buyer_name", "—"), class_name="text-sm text-slate-800 font-medium"),
                                    class_name="flex flex-col gap-0.5",
                                ),
                                rx.el.div(
                                    rx.el.span("Documento", class_name="text-xs text-slate-500"),
                                    rx.el.span(doc.get("buyer_doc_number", "—"), class_name="text-sm text-slate-800 font-mono"),
                                    class_name="flex flex-col gap-0.5",
                                ),
                                class_name="grid grid-cols-2 gap-3",
                            ),
                            class_name="border-t border-slate-200 pt-3",
                        ),

                        # Montos
                        rx.el.div(
                            rx.el.h4("Montos", class_name="text-sm font-semibold text-slate-700 mb-2"),
                            rx.el.div(
                                rx.el.div(
                                    rx.el.span("Base imponible", class_name="text-xs text-slate-500"),
                                    rx.el.span(
                                        State.currency_symbol, " ", doc.get("taxable_amount", "0.00"),
                                        class_name="text-sm text-slate-800 font-mono",
                                    ),
                                    class_name="flex flex-col gap-0.5",
                                ),
                                rx.el.div(
                                    rx.el.span("IGV / IVA", class_name="text-xs text-slate-500"),
                                    rx.el.span(
                                        State.currency_symbol, " ", doc.get("tax_amount", "0.00"),
                                        class_name="text-sm text-slate-800 font-mono",
                                    ),
                                    class_name="flex flex-col gap-0.5",
                                ),
                                rx.el.div(
                                    rx.el.span("Total", class_name="text-xs text-slate-500"),
                                    rx.el.span(
                                        State.currency_symbol, " ", doc.get("total_amount", "0.00"),
                                        class_name="text-sm font-bold text-slate-900 font-mono",
                                    ),
                                    class_name="flex flex-col gap-0.5",
                                ),
                                class_name="grid grid-cols-3 gap-3",
                            ),
                            class_name="border-t border-slate-200 pt-3",
                        ),

                        # Fechas
                        rx.el.div(
                            rx.el.h4("Fechas", class_name="text-sm font-semibold text-slate-700 mb-2"),
                            rx.el.div(
                                rx.el.div(
                                    rx.el.span("Creado", class_name="text-xs text-slate-500"),
                                    rx.el.span(doc.get("created_at", "—"), class_name="text-sm text-slate-700"),
                                    class_name="flex flex-col gap-0.5",
                                ),
                                rx.el.div(
                                    rx.el.span("Enviado", class_name="text-xs text-slate-500"),
                                    rx.el.span(doc.get("sent_at", "—"), class_name="text-sm text-slate-700"),
                                    class_name="flex flex-col gap-0.5",
                                ),
                                rx.el.div(
                                    rx.el.span("Autorizado", class_name="text-xs text-slate-500"),
                                    rx.el.span(doc.get("authorized_at", "—"), class_name="text-sm text-slate-700"),
                                    class_name="flex flex-col gap-0.5",
                                ),
                                class_name="grid grid-cols-3 gap-3",
                            ),
                            class_name="border-t border-slate-200 pt-3",
                        ),

                        # Hash SUNAT
                        rx.cond(
                            doc.get("hash_code", "") != "",
                            rx.el.div(
                                rx.el.span("Hash SUNAT", class_name="text-xs text-slate-500 block mb-1"),
                                rx.el.code(
                                    doc.get("hash_code", ""),
                                    class_name="text-xs font-mono bg-slate-100 px-2 py-1 rounded text-slate-700 break-all block",
                                ),
                                class_name="border-t border-slate-200 pt-3",
                            ),
                        ),

                        # Errores
                        rx.cond(
                            doc.get("errors", "") != "",
                            rx.el.div(
                                rx.el.span(
                                    "Detalle del error",
                                    class_name="text-xs text-red-500 font-semibold block mb-1",
                                ),
                                rx.el.div(
                                    rx.el.code(
                                        doc.get("errors", ""),
                                        class_name="text-xs font-mono text-red-700 whitespace-pre-wrap break-all",
                                    ),
                                    class_name="bg-red-50 border border-red-200 rounded p-3 max-h-32 overflow-y-auto",
                                ),
                                class_name="border-t border-slate-200 pt-3",
                            ),
                        ),

                        class_name="flex flex-col gap-4 py-4 max-h-[55vh] overflow-y-auto pr-1",
                    ),

                    # ── Footer / Acciones ────────────────────────────
                    rx.el.div(
                        # Reintento (solo en error/pending)
                        rx.cond(
                            (doc.get("status", "") == "error") | (doc.get("status", "") == "pending"),
                            rx.el.button(
                                rx.cond(
                                    State.fiscal_docs_loading,
                                    rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"),
                                    rx.icon("refresh-cw", class_name="h-4 w-4"),
                                ),
                                " Reintentar",
                                on_click=State.retry_fiscal_doc_from_dashboard(doc["id"]),
                                disabled=State.fiscal_docs_loading,
                                class_name=BUTTON_STYLES["warning"],
                            ),
                        ),
                        # NC (solo en authorized + boleta/factura)
                        rx.cond(
                            (doc.get("status", "") == "authorized")
                            & (
                                (doc.get("receipt_type", "") == "boleta")
                                | (doc.get("receipt_type", "") == "factura")
                            ),
                            rx.el.button(
                                rx.cond(
                                    State.nota_credito_loading,
                                    rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"),
                                    rx.icon("file-minus", class_name="h-4 w-4"),
                                ),
                                " Nota de Crédito",
                                on_click=State.emit_credit_note(doc["id"], "ANULACIÓN"),
                                disabled=State.nota_credito_loading,
                                class_name=BUTTON_STYLES["danger"],
                            ),
                        ),
                        rx.el.button(
                            "Cerrar",
                            on_click=State.close_fiscal_doc_detail,
                            class_name=BUTTON_STYLES["secondary"],
                        ),
                        class_name="flex items-center justify-end gap-3 pt-4 border-t border-slate-200",
                    ),

                    class_name="flex flex-col gap-0 p-6",
                ),
                class_name="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden",
            ),
        ),
        open=State.fiscal_doc_detail_open,
    )


# ════════════════════════════════════════════════════════════
# TARJETA DE RESUMEN
# ════════════════════════════════════════════════════════════

def _summary_card(icon_name: str, label: str, color: str, count_var: rx.Var) -> rx.Component:
    """Tarjeta de resumen rápido."""
    color_map = {
        "emerald": ("bg-emerald-50 border-emerald-200", "bg-emerald-100", "text-emerald-600"),
        "red":     ("bg-white border-red-200",     "bg-red-100",     "text-red-600"),
        "amber":   ("bg-white border-amber-200",   "bg-amber-100",   "text-amber-600"),
    }
    card_cls, icon_bg, text_cls = color_map.get(color, ("bg-white border-slate-200", "bg-slate-100", "text-slate-600"))

    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon(icon_name, class_name=f"h-5 w-5 {text_cls}"),
                class_name=f"p-2.5 rounded-lg {icon_bg}",
            ),
            rx.el.div(
                rx.el.p(label, class_name="text-sm text-slate-500"),
                rx.el.p(count_var.to_string(), class_name=f"text-2xl font-bold {text_cls}"),
                class_name="flex flex-col",
            ),
            class_name="flex items-center gap-3",
        ),
        class_name=f"bg-white border {card_cls} rounded-xl p-4 shadow-sm",
    )


# ════════════════════════════════════════════════════════════
# PÁGINA PRINCIPAL
# ════════════════════════════════════════════════════════════

def documentos_fiscales_page() -> rx.Component:
    """Página principal del dashboard de documentos fiscales."""
    content = rx.fragment(
        rx.cond(
            ~State.billing_is_active,
            # Billing no activo — placeholder
            rx.el.div(
                rx.icon("file-x", class_name="h-12 w-12 text-slate-300 mx-auto mb-3"),
                rx.el.h2(
                    "Facturación electrónica no configurada",
                    class_name="text-lg font-semibold text-slate-700 text-center",
                ),
                rx.el.p(
                    "Active y configure la facturación electrónica desde ",
                    rx.el.a(
                        "Configuración > Facturación",
                        href="/configuracion?tab=facturacion",
                        class_name="text-indigo-600 hover:underline font-medium",
                    ),
                    " para usar este módulo.",
                    class_name="text-sm text-slate-500 text-center mt-1",
                ),
                class_name="flex flex-col items-center justify-center py-20",
            ),
            # Billing activo — mostrar dashboard
            rx.el.div(
                # Encabezado
                page_title(
                    "DOCUMENTOS FISCALES",
                    "Historial de comprobantes electrónicos emitidos (SUNAT / AFIP)",
                ),

                # Panel de filtros
                rx.el.div(
                    _fiscal_filters(),
                    class_name="bg-white border border-slate-200 rounded-xl shadow-sm p-4",
                ),

                # Tabla
                rx.el.div(
                    _fiscal_docs_table(),
                    class_name="bg-white border border-slate-200 rounded-xl shadow-sm p-4",
                ),

                # Modal de detalle
                _fiscal_doc_detail_modal(),

                class_name="flex flex-col gap-6",
            ),
        ),
    )

    return permission_guard(
        has_permission=State.can_view_ventas,
        content=content,
        redirect_message="Acceso denegado a Documentos Fiscales",
    )
