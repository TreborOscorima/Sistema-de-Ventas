"""Mixin de reportes y exportaciones para CashState.

Contiene métodos de exportación a Excel, PDF e impresión de recibos
extraídos de cash_state.py para reducir el tamaño de la clase principal.
"""

import reflex as rx
import datetime
import uuid
import logging
import html
import io
import json
import re
from io import BytesIO
from typing import Any, List
from decimal import Decimal

import sqlalchemy
from sqlmodel import select, desc
from sqlalchemy.orm import selectinload

from app.enums import PaymentMethodType, SaleStatus
from app.models import (
    CashboxSession as CashboxSessionModel,
    CashboxLog as CashboxLogModel,
    User as UserModel,
    Sale,
    SaleItem,
    SalePayment,
)
from app.utils.exports import (
    create_excel_workbook,
    style_header_row,
    add_data_rows,
    auto_adjust_column_widths,
    apply_wrap_text,
    create_pdf_report,
    add_company_header,
    add_totals_row_with_formulas,
    add_notes_section,
    CURRENCY_FORMAT,
    THIN_BORDER,
    POSITIVE_FILL,
    NEGATIVE_FILL,
    WARNING_FILL,
)
from app.i18n import MSG
from app.constants import CASHBOX_INCOME_ACTIONS, CASHBOX_EXPENSE_ACTIONS
from ..types import CashboxSale, CashboxLogEntry
from app.utils.tenant import set_tenant_context


class ReportsMixin:
    """Mixin con métodos de exportación y reportes de caja."""

    @rx.event
    def export_cashbox_report(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast(MSG.PERM_EXPORT, duration=3000)

        sales = self._fetch_cashbox_sales()
        if not sales:
            return rx.toast(MSG.SALE_NO_EXPORT, duration=3000)

        currency_label = self._currency_symbol_clean()
        currency_format = self._currency_excel_format()
        # Obtener nombre de empresa
        company_name = getattr(self, "company_name", "") or "EMPRESA"
        today = self._current_local_display_date()
        period_start = self.cashbox_filter_start_date or "Inicio"
        period_end = self.cashbox_filter_end_date or "Actual"
        period_label = f"Período: {period_start} a {period_end}"

        total_operations = 0
        total_facturado = 0.0
        total_cobrado = 0.0
        total_pendiente = 0.0
        credit_operations = 0

        for sale in sales:
            if sale.get("is_deleted"):
                continue
            total_operations += 1
            total_amount = float(sale.get("total", 0) or 0)
            paid_amount = float(sale.get("amount", 0) or 0)
            payment_condition = (sale.get("payment_condition") or "").strip().lower()
            payment_type = (sale.get("payment_type") or "").strip().lower()
            is_credit = (
                bool(sale.get("is_credit"))
                or payment_type == "credit"
                or payment_condition in {"credito", "credit"}
            )
            if is_credit:
                credit_operations += 1
            total_facturado += total_amount
            total_cobrado += paid_amount
            total_pendiente += max(total_amount - paid_amount, 0)

        wb, ws = create_excel_workbook("Resumen de Caja")

        # Agregar encabezado profesional
        row = add_company_header(
            ws,
            company_name,
            "RESUMEN DE GESTIÓN DE CAJA",
            period_label,
            columns=8,
            generated_at=self._display_now(),
        )

        row += 1
        ws.cell(row=row, column=1, value="RESUMEN EJECUTIVO")
        row += 1
        ws.cell(row=row, column=1, value="Fecha de corte:")
        ws.cell(row=row, column=2, value=today)
        row += 1
        ws.cell(row=row, column=1, value="Operaciones registradas:")
        ws.cell(row=row, column=2, value=total_operations)
        row += 1
        ws.cell(row=row, column=1, value="Operaciones a crédito:")
        ws.cell(row=row, column=2, value=credit_operations)
        row += 1
        ws.cell(row=row, column=1, value=f"Total facturado ({currency_label}):")
        ws.cell(row=row, column=2, value=total_facturado).number_format = currency_format
        row += 1
        ws.cell(row=row, column=1, value=f"Total cobrado ({currency_label}):")
        ws.cell(row=row, column=2, value=total_cobrado).number_format = currency_format
        row += 1
        ws.cell(row=row, column=1, value=f"Saldo pendiente ({currency_label}):")
        ws.cell(row=row, column=2, value=total_pendiente).number_format = currency_format

        row += 2

        headers = [
            "Fecha y Hora",
            "Vendedor",
            "Método de Pago",
            "Detalle del Método",
            "Referencia/Descripción",
            f"Monto Total ({currency_label})",
            f"Monto Cobrado ({currency_label})",
            "Productos Vendidos",
        ]
        style_header_row(ws, row, headers)
        data_start = row + 1
        row += 1

        invalid_labels = {"", "-", "no especificado"}
        for sale in sales:
            if sale.get("is_deleted"):
                continue
            payment_condition = (sale.get("payment_condition") or "").strip().lower()
            payment_type = (sale.get("payment_type") or "").strip().lower()
            is_credit = (
                bool(sale.get("is_credit"))
                or payment_type == "credit"
                or payment_condition in {"credito", "credit"}
            )
            method_raw = self._normalize_wallet_label(sale.get("payment_method", ""))
            method_label = self._normalize_wallet_label(
                sale.get("payment_label", sale.get("payment_method", ""))
            )
            payment_details = self._payment_details_text(
                sale.get("payment_details", "")
            ).strip()
            if is_credit:
                method_raw = "Venta a Crédito / Fiado"
                method_label = method_raw
                amount_paid = sale.get("amount_paid")
                if amount_paid is None:
                    amount_paid = sale.get("amount", 0)
                try:
                    amount_paid_value = float(amount_paid or 0)
                except (TypeError, ValueError):
                    amount_paid_value = 0.0
                try:
                    total_amount_value = float(sale.get("total", 0) or 0)
                except (TypeError, ValueError):
                    total_amount_value = 0.0
                if total_amount_value > 0 and amount_paid_value >= total_amount_value:
                    payment_details = "Crédito (Completado)"
                elif amount_paid_value > 0:
                    payment_details = (
                        f"Crédito (Adelanto: {self._format_currency(amount_paid_value)})"
                    )
                else:
                    payment_details = "Crédito (Pendiente Total)"
            else:
                if (method_raw or "").strip().lower() in invalid_labels:
                    if (method_label or "").strip().lower() not in invalid_labels:
                        method_raw = method_label
                    else:
                        method_raw = MSG.FALLBACK_NOT_SPECIFIED
                if (method_label or "").strip().lower() in invalid_labels:
                    if (method_raw or "").strip().lower() not in invalid_labels:
                        method_label = method_raw
                    else:
                        method_label = MSG.FALLBACK_NOT_SPECIFIED
                if (payment_details or "").strip().lower() in invalid_labels:
                    if (method_label or "").strip().lower() not in invalid_labels:
                        payment_details = f"Pago en {method_label}"
                    else:
                        payment_details = "Pago registrado"
            item_parts = []
            for item in sale.get("items", []):
                name = (item.get("description") or "").strip() or "Producto"
                quantity = item.get("quantity", 0)
                unit_price = item.get("price")
                if unit_price is None:
                    unit_price = item.get("sale_price")
                if unit_price is None:
                    unit_price = item.get("subtotal")
                price_display = self._format_currency(unit_price or 0)
                item_parts.append(f"{name} (x{quantity}) - {price_display}")
            details = "\n".join(item_parts) if item_parts else "Sin detalle"

            ws.cell(row=row, column=1, value=sale["timestamp"])
            ws.cell(row=row, column=2, value=sale["user"])
            ws.cell(row=row, column=3, value=method_raw)
            ws.cell(row=row, column=4, value=method_label)
            ws.cell(row=row, column=5, value=payment_details)
            ws.cell(row=row, column=6, value=sale["total"] or 0).number_format = currency_format
            ws.cell(row=row, column=7, value=sale.get("amount", 0) or 0).number_format = currency_format
            ws.cell(row=row, column=8, value=details)

            for col in range(1, 9):
                ws.cell(row=row, column=col).border = THIN_BORDER
            row += 1

        if row > data_start:
            apply_wrap_text(ws, [8], data_start, row - 1)

        # Fila de totales con fórmulas
        totals_row = row
        add_totals_row_with_formulas(ws, totals_row, data_start, [
            {"type": "label", "value": "TOTALES"},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "sum", "col_letter": "F", "number_format": currency_format},
            {"type": "sum", "col_letter": "G", "number_format": currency_format},
            {"type": "text", "value": ""},
        ])

        # Notas explicativas
        add_notes_section(ws, totals_row, [
            "Monto Total: Precio total de la venta según productos.",
            "Monto Cobrado: Dinero efectivamente recibido (puede diferir en ventas a crédito).",
            "Crédito (Completado): El cliente pagó la totalidad del crédito.",
            "Crédito (Adelanto): El cliente realizó un pago parcial.",
            "Crédito (Pendiente Total): No se ha recibido ningún pago aún.",
        ], columns=8)

        auto_adjust_column_widths(ws)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return rx.download(data=output.getvalue(), filename="resumen_gestion_caja.xlsx")

    @rx.event
    def export_cashbox_close_pdf(self):
        if not (
            self.current_user["privileges"]["view_cashbox"]
            and self.current_user["privileges"]["export_data"]
        ):
            return rx.toast(MSG.PERM_EXPORT, duration=3000)

        report_date = self.cashbox_close_summary_date or self._current_local_date_str()
        breakdown = self._build_cashbox_close_breakdown(report_date)
        summary = breakdown["summary"]
        day_sales = self.cashbox_close_summary_sales or self._get_day_sales(report_date)

        if not summary and not day_sales and breakdown["opening_amount"] == 0:
            return rx.toast(MSG.CASH_NO_MOVEMENTS_EXPORT, duration=3000)

        info_dict = {
            "Fecha Cierre": report_date,
            "Responsable": self.current_user["username"],
        }
        total_value = 0.0
        for item in summary:
            total = item.get("total", 0) or 0
            if total <= 0:
                continue
            method = (item.get("method", MSG.FALLBACK_NOT_SPECIFIED) or "").strip() or MSG.FALLBACK_NOT_SPECIFIED
            info_dict[f"Total {method}"] = self._format_currency(total)
            total_value += float(total)

        info_dict["Apertura"] = self._format_currency(breakdown["opening_amount"])
        info_dict["Ingresos reales"] = self._format_currency(breakdown["income_total"])
        info_dict["Egresos caja chica"] = self._format_currency(breakdown["expense_total"])
        info_dict["Saldo esperado"] = self._format_currency(breakdown["expected_total"])
        if self.cashbox_close_has_counted:
            info_dict["Total contado"] = self._format_currency(self.cashbox_close_counted_total)
            diff = self.cashbox_close_discrepancy
            sign = "+" if diff > 0 else ""
            info_dict["Diferencia"] = f"{sign}{self._format_currency(diff)}"

        def _format_time(timestamp: str) -> str:
            if not timestamp:
                return ""
            if " " in timestamp:
                return timestamp.split(" ", 1)[1]
            try:
                parsed = datetime.datetime.fromisoformat(timestamp)
                return parsed.strftime("%H:%M:%S")
            except ValueError:
                return timestamp

        def _format_amount(value: Any) -> str:
            try:
                amount = float(value or 0)
            except (TypeError, ValueError):
                amount = 0.0
            return self._format_currency(amount)

        headers = ["N°", "Hora", "Operación", "Método", "Referencia", "Monto"]
        data = []
        sales_rows = [sale for sale in day_sales if not sale.get("is_deleted")]
        seq = len(sales_rows)
        for sale in sales_rows:
            if sale.get("is_deleted"):
                continue
            operation_raw = sale.get("action") or sale.get("type") or "Venta"
            operation = str(operation_raw).replace("_", " ").strip().title() or "Venta"
            method_raw = sale.get("payment_label") or sale.get("payment_method") or ""
            method_label = (
                self._normalize_wallet_label(method_raw) if method_raw else MSG.FALLBACK_NOT_SPECIFIED
            )
            reference = self._payment_details_text(sale.get("payment_details", ""))
            reference_clean = re.sub(r"#\s*\d+", "", reference or "").strip()
            if not reference_clean:
                reference_clean = reference
            amount = sale.get("total")
            if amount is None:
                amount = sale.get("amount", 0)
            data.append(
                [
                    seq,
                    _format_time(sale.get("timestamp", "")),
                    operation,
                    method_label,
                    reference_clean,
                    _format_amount(amount),
                ]
            )
            seq -= 1

        info_dict["column_widths"] = [0.06, 0.12, 0.16, 0.18, 0.36, 0.12]
        info_dict["wrap_columns"] = [4]

        output = io.BytesIO()
        create_pdf_report(
            output,
            "Reporte de Cierre de Caja",
            data,
            headers,
            info_dict,
        )

        return rx.download(data=output.getvalue(), filename="cierre_caja.pdf")

    @rx.event
    def export_cashbox_close_pdf_for_log(self, log_id: str):
        if not (
            self.current_user["privileges"]["view_cashbox"]
            and self.current_user["privileges"]["export_data"]
        ):
            return rx.toast(MSG.PERM_EXPORT, duration=3000)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast(MSG.VAL_COMPANY_BRANCH_UNDEFINED, duration=3000)
        set_tenant_context(company_id, branch_id)
        try:
            log_id_int = int(log_id)
        except (TypeError, ValueError):
            return rx.toast(MSG.CASH_CLOSE_INVALID, duration=3000)
        with rx.session() as session:
            log = session.exec(
                select(CashboxLogModel)
                .where(CashboxLogModel.id == log_id_int)
                .where(CashboxLogModel.company_id == company_id)
                .where(CashboxLogModel.branch_id == branch_id)
                .execution_options(
                    tenant_company_id=company_id,
                    tenant_branch_id=branch_id,
                )
            ).first()
        if not log or (log.action or "").lower() != "cierre":
            return rx.toast(MSG.CASH_CLOSE_NOT_CLOSE, duration=3000)

        start_dt, end_dt, user_id, report_date, closing_timestamp = self._cashbox_range_for_log(log)
        company_id = int(log.company_id or company_id)
        branch_id = int(log.branch_id or branch_id)
        set_tenant_context(company_id, branch_id)
        responsable = ""
        if user_id:
            with rx.session() as session:
                user = session.exec(
                    select(UserModel)
                    .where(UserModel.id == user_id)
                    .where(UserModel.company_id == company_id)
                    .execution_options(
                        tenant_company_id=company_id,
                        tenant_branch_id=branch_id,
                    )
                ).first()
                if user:
                    responsable = user.username or ""
        if not responsable:
            responsable = self.current_user.get("username") or ""

        summary = self._build_cashbox_summary_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )
        opening_amount = self._cashbox_opening_amount_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )
        expense_total = self._cashbox_expense_total_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )
        income_total = self._round_currency(sum(item.get("total", 0) for item in summary))
        expected_total = self._round_currency(opening_amount + income_total - expense_total)
        day_sales = self._get_sales_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )

        if not summary and not day_sales and opening_amount == 0:
            return rx.toast(MSG.CASH_NO_MOVEMENTS_EXPORT, duration=3000)

        info_dict = {
            "Fecha Cierre": report_date,
            "Responsable": responsable,
        }
        for item in summary:
            total = item.get("total", 0) or 0
            if total <= 0:
                continue
            method = (item.get("method", MSG.FALLBACK_NOT_SPECIFIED) or "").strip() or MSG.FALLBACK_NOT_SPECIFIED
            info_dict[f"Total {method}"] = self._format_currency(total)
        info_dict["Apertura"] = self._format_currency(opening_amount)
        info_dict["Ingresos reales"] = self._format_currency(income_total)
        info_dict["Egresos caja chica"] = self._format_currency(expense_total)
        info_dict["Saldo esperado"] = self._format_currency(expected_total)

        def _format_time(timestamp: str) -> str:
            if not timestamp:
                return ""
            if " " in timestamp:
                return timestamp.split(" ", 1)[1]
            try:
                parsed = datetime.datetime.fromisoformat(timestamp)
                return parsed.strftime("%H:%M:%S")
            except ValueError:
                return timestamp

        def _format_amount(value: Any) -> str:
            try:
                amount = float(value or 0)
            except (TypeError, ValueError):
                amount = 0.0
            return self._format_currency(amount)

        headers = ["N°", "Hora", "Operación", "Método", "Referencia", "Monto"]
        data = []
        sales_rows = [sale for sale in day_sales if not sale.get("is_deleted")]
        seq = len(sales_rows)
        for sale in sales_rows:
            operation_raw = sale.get("action") or sale.get("type") or "Venta"
            operation = str(operation_raw).replace("_", " ").strip().title() or "Venta"
            method_raw = sale.get("payment_label") or sale.get("payment_method") or ""
            method_label = (
                self._normalize_wallet_label(method_raw) if method_raw else MSG.FALLBACK_NOT_SPECIFIED
            )
            reference = self._payment_details_text(sale.get("payment_details", ""))
            reference_clean = re.sub(r"#\s*\d+", "", reference or "").strip()
            if not reference_clean:
                reference_clean = reference
            amount = sale.get("total")
            if amount is None:
                amount = sale.get("amount", 0)
            data.append(
                [
                    seq,
                    _format_time(sale.get("timestamp", "")),
                    operation,
                    method_label,
                    reference_clean,
                    _format_amount(amount),
                ]
            )
            seq -= 1

        info_dict["column_widths"] = [0.06, 0.12, 0.16, 0.18, 0.36, 0.12]
        info_dict["wrap_columns"] = [4]

        output = io.BytesIO()
        create_pdf_report(
            output,
            "Reporte de Cierre de Caja",
            data,
            headers,
            info_dict,
        )

        return rx.download(data=output.getvalue(), filename="cierre_caja.pdf")

    @rx.event
    def print_cashbox_close_summary_for_log(self, log_id: str):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast(MSG.PERM_CASH_MGMT, duration=3000)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast(MSG.VAL_COMPANY_BRANCH_UNDEFINED, duration=3000)
        set_tenant_context(company_id, branch_id)
        try:
            log_id_int = int(log_id)
        except (TypeError, ValueError):
            return rx.toast(MSG.CASH_CLOSE_INVALID, duration=3000)
        with rx.session() as session:
            log = session.exec(
                select(CashboxLogModel)
                .where(CashboxLogModel.id == log_id_int)
                .where(CashboxLogModel.company_id == company_id)
                .where(CashboxLogModel.branch_id == branch_id)
                .execution_options(
                    tenant_company_id=company_id,
                    tenant_branch_id=branch_id,
                )
            ).first()
        if not log or (log.action or "").lower() != "cierre":
            return rx.toast(MSG.CASH_CLOSE_NOT_CLOSE, duration=3000)

        start_dt, end_dt, user_id, report_date, closing_timestamp = self._cashbox_range_for_log(log)
        company_id = int(log.company_id or company_id)
        branch_id = int(log.branch_id or branch_id)
        set_tenant_context(company_id, branch_id)
        responsable = ""
        if user_id:
            with rx.session() as session:
                user = session.exec(
                    select(UserModel)
                    .where(UserModel.id == user_id)
                    .where(UserModel.company_id == company_id)
                    .execution_options(
                        tenant_company_id=company_id,
                        tenant_branch_id=branch_id,
                    )
                ).first()
                if user:
                    responsable = user.username or ""
        if not responsable:
            responsable = self.current_user.get("username") or ""

        summary = self._build_cashbox_summary_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )
        opening_amount = self._cashbox_opening_amount_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )
        expense_total = self._cashbox_expense_total_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )
        income_total = self._round_currency(sum(item.get("total", 0) for item in summary))
        expected_total = self._round_currency(opening_amount + income_total - expense_total)
        day_sales = self._get_sales_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )

        if not summary and not day_sales and opening_amount == 0:
            return rx.toast(MSG.CASH_NO_MOVEMENTS_PRINT, duration=3000)

        totals_list = [
            {
                "method": item.get("method", MSG.FALLBACK_NOT_SPECIFIED),
                "amount": self._round_currency(item.get("total", 0)),
            }
            for item in summary
            if item.get("total", 0) > 0
        ]

        receipt_width = self._receipt_width()
        paper_width_mm = self._receipt_paper_mm()

        def center(text, width=receipt_width):
            return text.center(width)

        def line(width=receipt_width):
            return "-" * width

        def row(left, right, width=receipt_width):
            spaces = width - len(left) - len(right)
            return left + " " * max(spaces, 1) + right

        company = self._company_settings_snapshot()
        company_name = (company.get("company_name") or "").strip()
        ruc = (company.get("ruc") or "").strip()
        tax_id_label = company.get("tax_id_label", "RUC")
        address = (company.get("address") or "").strip()
        phone = (company.get("phone") or "").strip()
        address_lines = self._wrap_receipt_lines(address, receipt_width)

        receipt_lines = [""]
        if company_name:
            for name_line in self._wrap_receipt_lines(company_name, receipt_width):
                receipt_lines.append(center(name_line))
            receipt_lines.append("")
        if ruc:
            receipt_lines.append(center(f"{tax_id_label}: {ruc}"))
            receipt_lines.append("")
        for addr_line in address_lines:
            receipt_lines.append(center(addr_line))
        if address_lines:
            receipt_lines.append("")
        if phone:
            receipt_lines.append(center(f"Tel: {phone}"))
            receipt_lines.append("")
        receipt_lines.extend(
            [
                line(),
                center("RESUMEN DIARIO DE CAJA"),
                line(),
                "",
                f"Fecha: {report_date}",
                "",
                f"Responsable: {responsable}",
                "",
                f"Cierre: {self._format_event_timestamp(closing_timestamp)}",
                "",
                line(),
                "",
                "RESUMEN DE CAJA",
                "",
                row("Apertura:", self._format_currency(opening_amount)),
                row("Ingresos:", self._format_currency(income_total)),
                row("Egresos:", self._format_currency(expense_total)),
                row("Saldo esperado:", self._format_currency(expected_total)),
                "",
                line(),
                "",
                "INGRESOS POR METODO",
                "",
            ]
        )

        for item in totals_list:
            amount = item.get("amount", 0)
            if amount > 0:
                method = item.get("method", MSG.FALLBACK_NOT_SPECIFIED)
                receipt_lines.append(
                    row(f"{method}:", self._format_currency(amount))
                )
                receipt_lines.append("")

        receipt_lines.append(
            row("TOTAL CIERRE:", self._format_currency(expected_total))
        )
        receipt_lines.append("")
        receipt_lines.append(line())
        receipt_lines.append("")
        receipt_lines.append("DETALLE DE INGRESOS")
        receipt_lines.append("")

        sales_rows = [sale for sale in day_sales if not sale.get("is_deleted")]
        seq = len(sales_rows)
        for sale in sales_rows:
            method_label = sale.get("payment_label", sale.get("payment_method", ""))
            payment_detail = self._payment_details_text(sale.get("payment_details", ""))
            payment_detail = re.sub(r"#\s*\d+", "", payment_detail or "").strip()
            receipt_lines.append(f"{sale['timestamp']}")
            receipt_lines.extend(
                self._wrap_receipt_label_value(
                    "Correlativo", f"#{seq}", receipt_width
                )
            )
            receipt_lines.extend(
                self._wrap_receipt_label_value(
                    "Usuario", sale["user"], receipt_width
                )
            )
            receipt_lines.extend(
                self._wrap_receipt_label_value(
                    "Metodo", method_label, receipt_width
                )
            )
            if payment_detail and payment_detail != method_label:
                receipt_lines.extend(
                    self._wrap_receipt_label_value(
                        "Detalle", payment_detail, receipt_width
                    )
                )
            receipt_lines.append(row("Total:", self._format_currency(sale['total'])))
            receipt_lines.append(line())
            seq -= 1

        receipt_lines.extend(
            [
                "",
                center("FIN DEL REPORTE"),
                " ",
                " ",
                " ",
            ]
        )

        receipt_text = chr(10).join(receipt_lines)
        safe_receipt_text = html.escape(receipt_text)

        html_content = f"""<html>
<head>
<meta charset='utf-8'/>
<title>Resumen de Caja</title>
<style>
@page {{ size: {paper_width_mm}mm auto; margin: 0; }}
body {{ margin: 0; padding: 2mm; }}
pre {{ font-family: monospace; font-size: 12px; margin: 0; white-space: pre-wrap; word-break: break-word; }}
</style>
</head>
<body>
<pre>{safe_receipt_text}</pre>
</body>
</html>"""

        script = f"""
        const cashboxWindow = window.open('', '_blank');
        cashboxWindow.document.write({json.dumps(html_content)});
        cashboxWindow.document.close();
        cashboxWindow.focus();
        cashboxWindow.print();
        """
        return rx.call_script(script)

    @rx.event
    def export_cashbox_sessions(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast(MSG.PERM_CASH_MGMT, duration=3000)
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast(MSG.PERM_EXPORT, duration=3000)
        logs = self._fetch_cashbox_logs()
        if not logs:
            return rx.toast(MSG.CASH_NO_OPENCLOSE_EXPORT, duration=3000)

        currency_label = self._currency_symbol_clean()
        currency_format = self._currency_excel_format()
        company_name = getattr(self, "company_name", "") or "EMPRESA"
        today = self._current_local_display_date()
        period_start = self.cashbox_log_filter_start_date or "Inicio"
        period_end = self.cashbox_log_filter_end_date or "Actual"
        period_label = f"Período: {period_start} a {period_end}"

        opening_count = 0
        closing_count = 0
        opening_total = 0.0
        closing_total = 0.0
        for log in logs:
            action = (log.get("action") or "").strip().lower()
            opening_amount = float(log.get("opening_amount", 0) or 0)
            closing_amount = float(log.get("closing_total", 0) or 0)
            if action == "apertura":
                opening_count += 1
                opening_total += opening_amount
            elif action == "cierre":
                closing_count += 1
                closing_total += closing_amount

        wb, ws = create_excel_workbook("Aperturas y Cierres")

        # Encabezado profesional
        row = add_company_header(
            ws,
            company_name,
            "REGISTRO DE APERTURAS Y CIERRES DE CAJA",
            period_label,
            columns=7,
            generated_at=self._display_now(),
        )

        row += 1
        ws.cell(row=row, column=1, value="RESUMEN DE OPERACIONES")
        row += 1
        ws.cell(row=row, column=1, value="Fecha de corte:")
        ws.cell(row=row, column=2, value=today)
        row += 1
        ws.cell(row=row, column=1, value="Cantidad de aperturas:")
        ws.cell(row=row, column=2, value=opening_count)
        row += 1
        ws.cell(row=row, column=1, value="Cantidad de cierres:")
        ws.cell(row=row, column=2, value=closing_count)
        row += 1
        ws.cell(row=row, column=1, value=f"Total aperturas ({currency_label}):")
        ws.cell(row=row, column=2, value=opening_total).number_format = currency_format
        row += 1
        ws.cell(row=row, column=1, value=f"Total cierres ({currency_label}):")
        ws.cell(row=row, column=2, value=closing_total).number_format = currency_format
        row += 2

        headers = [
            "Fecha y Hora",
            "Tipo de Operación",
            "Responsable",
            f"Monto Apertura ({currency_label})",
            f"Monto Cierre ({currency_label})",
            "Desglose por Método",
            "Observaciones",
        ]
        style_header_row(ws, row, headers)
        data_start = row + 1
        row += 1

        total_aperturas = 0.0
        total_cierres = 0.0

        for log in logs:
            action = (log.get("action") or "").lower()
            action_display = (
                "Apertura de Caja"
                if action == "apertura"
                else "Cierre de Caja"
                if action == "cierre"
                else str(action).replace("_", " ").strip().title()
            )

            opening_amount = float(log.get("opening_amount", 0) or 0)
            closing_amount = float(log.get("closing_total", 0) or 0)

            if action == "apertura":
                total_aperturas += opening_amount
            elif action == "cierre":
                total_cierres += closing_amount

            totals_detail = ", ".join(
                f"{item.get('method', 'Otro')}: {self._format_currency(item.get('amount', 0))}"
                for item in log.get("totals_by_method", [])
                if item.get("amount", 0)
            ) or "Sin desglose"

            ws.cell(row=row, column=1, value=log.get("timestamp", ""))
            ws.cell(row=row, column=2, value=action_display)
            ws.cell(row=row, column=3, value=log.get("user", MSG.FALLBACK_UNKNOWN))
            ws.cell(row=row, column=4, value=opening_amount).number_format = currency_format
            ws.cell(row=row, column=5, value=closing_amount).number_format = currency_format
            ws.cell(row=row, column=6, value=totals_detail)
            ws.cell(row=row, column=7, value=log.get("notes", "") or "Sin observaciones")

            for col in range(1, 8):
                ws.cell(row=row, column=col).border = THIN_BORDER
            row += 1

        # Fila de totales
        totals_row = row
        add_totals_row_with_formulas(ws, totals_row, data_start, [
            {"type": "label", "value": "TOTALES"},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "sum", "col_letter": "D", "number_format": currency_format},
            {"type": "sum", "col_letter": "E", "number_format": currency_format},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
        ])

        # Notas explicativas
        add_notes_section(ws, totals_row, [
            "Apertura de Caja: Monto inicial con el que se inicia la jornada.",
            "Cierre de Caja: Monto total contado al finalizar la jornada.",
            "Desglose por Método: Distribución del dinero según forma de pago (solo en cierres).",
            "La diferencia entre Cierres y Aperturas debe coincidir con las ventas del día.",
        ], columns=7)

        auto_adjust_column_widths(ws)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return rx.download(
            data=output.getvalue(), filename="aperturas_cierres_caja.xlsx"
        )

    @rx.event
    def export_petty_cash_report(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast(MSG.PERM_CASH_MGMT, duration=3000)
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast(MSG.PERM_EXPORT, duration=3000)

        movements = self.petty_cash_movements
        if not movements:
            return rx.toast(MSG.CASH_NO_MOVEMENTS_GENERIC, duration=3000)

        currency_label = self._currency_symbol_clean()
        currency_format = self._currency_excel_format()
        company_name = getattr(self, "company_name", "") or "EMPRESA"
        today = self._current_local_display_date()

        def _parse_numeric(value: Any) -> float:
            if value is None:
                return 0.0
            raw = str(value)
            # Extrae el primer número del string, ignorando símbolos
            match = re.search(r"([0-9]+(?:[.,][0-9]{3})*(?:[.,][0-9]+)?)", raw)
            if not match:
                return 0.0
            num = match.group(1)
            if "," in num and "." in num:
                num = num.replace(",", "")
            elif "," in num and "." not in num:
                num = num.replace(",", ".")
            try:
                return float(num)
            except ValueError:
                return 0.0

        total_movements = len(movements)
        total_units = sum(
            _parse_numeric(item.get("formatted_quantity", "0"))
            for item in movements
        )
        total_expense = sum(
            _parse_numeric(item.get("formatted_total", "0"))
            for item in movements
        )

        wb, ws = create_excel_workbook("Caja Chica")

        # Encabezado profesional
        row = add_company_header(
            ws,
            company_name,
            "MOVIMIENTOS DE CAJA CHICA",
            f"Corte: {today}",
            columns=7,
            generated_at=self._display_now(),
        )

        row += 1
        ws.cell(row=row, column=1, value="RESUMEN DE EGRESOS")
        row += 1
        ws.cell(row=row, column=1, value="Movimientos registrados:")
        ws.cell(row=row, column=2, value=total_movements)
        row += 1
        ws.cell(row=row, column=1, value="Unidades egresadas:")
        ws.cell(row=row, column=2, value=total_units)
        row += 1
        ws.cell(row=row, column=1, value=f"Total egresado ({currency_label}):")
        ws.cell(row=row, column=2, value=total_expense).number_format = currency_format
        row += 2

        headers = [
            "Fecha y Hora",
            "Responsable",
            "Concepto/Motivo",
            "Cantidad",
            MSG.FALLBACK_UNIT,
            f"Costo Unitario ({currency_label})",
            f"Total Egreso ({currency_label})",
        ]
        style_header_row(ws, row, headers)
        data_start = row + 1
        row += 1

        for item in movements:
            # Extraer valores numéricos para las fórmulas
            quantity = _parse_numeric(item.get("formatted_quantity", "0"))
            cost = _parse_numeric(item.get("formatted_cost", "0"))

            ws.cell(row=row, column=1, value=item.get("timestamp", ""))
            ws.cell(row=row, column=2, value=item.get("user", MSG.FALLBACK_UNKNOWN))
            ws.cell(row=row, column=3, value=item.get("notes", "") or "Sin motivo especificado")
            ws.cell(row=row, column=4, value=quantity)
            ws.cell(row=row, column=5, value=item.get("unit", "Unid."))
            ws.cell(row=row, column=6, value=cost).number_format = currency_format
            # Total = Fórmula: Cantidad × Costo Unitario
            ws.cell(row=row, column=7, value=f"=D{row}*F{row}").number_format = currency_format

            for col in range(1, 8):
                ws.cell(row=row, column=col).border = THIN_BORDER
            row += 1

        # Fila de totales
        totals_row = row
        add_totals_row_with_formulas(ws, totals_row, data_start, [
            {"type": "label", "value": "TOTAL EGRESOS"},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "sum", "col_letter": "D"},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "sum", "col_letter": "G", "number_format": currency_format},
        ])

        # Notas explicativas
        add_notes_section(ws, totals_row, [
            "Caja Chica: Fondo destinado a gastos menores del día a día.",
            "Cada movimiento representa un egreso (salida de dinero).",
            "Total Egreso = Cantidad × Costo Unitario (fórmula verificable).",
            "Este monto se descuenta del efectivo al momento del cierre de caja.",
        ], columns=7)

        auto_adjust_column_widths(ws)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return rx.download(
            data=output.getvalue(), filename="movimientos_caja_chica.xlsx"
        )

    @rx.event
    def reprint_sale_receipt(self, sale_id: str):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para ver comprobantes.", duration=3000)

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast(MSG.VAL_COMPANY_UNDEFINED, duration=3000)
        sale_data = None
        with rx.session() as session:
            try:
                sale_db_id = int(sale_id)
                sale = session.exec(
                    select(Sale)
                    .where(Sale.id == sale_db_id)
                    .where(Sale.company_id == company_id)
                    .where(Sale.branch_id == branch_id)
                    .options(
                        selectinload(Sale.items),
                        selectinload(Sale.payments),
                        selectinload(Sale.user),
                    )
                ).first()
                if sale:
                    items_data = []
                    for item in sale.items:
                        items_data.append({
                            "description": item.product_name_snapshot,
                            "quantity": item.quantity,
                            "unit": MSG.FALLBACK_UNIT,
                            "price": item.unit_price,
                            "subtotal": item.subtotal
                        })

                    sale_data = {
                        "timestamp": self._format_event_timestamp(sale.timestamp),
                        "total": sale.total_amount,
                        "payment_details": self._payment_summary_from_payments(
                            sale.payments or []
                        ),
                        "payment_method": self._payment_method_display(
                            sale.payments or []
                        ),
                        "items": items_data,
                        "user": sale.user.username if sale.user else MSG.FALLBACK_UNKNOWN
                    }
            except ValueError:
                pass

        if not sale_data:
            return rx.toast("Venta no encontrada.", duration=3000)

        receipt_width = self._receipt_width()
        paper_width_mm = self._receipt_paper_mm()

        # Funciones auxiliares para formato de texto plano
        def center(text, width=receipt_width):
            return text.center(width)

        def line(width=receipt_width):
            return "-" * width

        def row(left, right, width=receipt_width):
            spaces = width - len(left) - len(right)
            return left + " " * max(spaces, 1) + right

        company = self._company_settings_snapshot()
        company_name = (company.get("company_name") or "").strip()
        branch_name = (company.get("branch_name") or "").strip()
        ruc = (company.get("ruc") or "").strip()
        tax_id_label = company.get("tax_id_label", "RUC")  # Dinámico por país
        address = (company.get("address") or "").strip()
        phone = (company.get("phone") or "").strip()
        footer_message = (company.get("footer_message") or "").strip()
        address_lines = self._wrap_receipt_lines(address, receipt_width)

        items = sale_data.get("items", [])
        payment_summary = self._payment_details_text(
            sale_data.get("payment_details")
        ) or sale_data.get("payment_method", "")

        # Construir recibo línea por línea
        receipt_lines = [""]
        if company_name:
            for name_line in self._wrap_receipt_lines(company_name, receipt_width):
                receipt_lines.append(center(name_line))
            receipt_lines.append("")
        if branch_name and branch_name != company_name:
            for bl in self._wrap_receipt_lines(branch_name, receipt_width):
                receipt_lines.append(center(bl))
            receipt_lines.append("")
        if ruc:
            receipt_lines.append(center(f"{tax_id_label}: {ruc}"))
            receipt_lines.append("")
        for addr_line in address_lines:
            receipt_lines.append(center(addr_line))
        if address_lines:
            receipt_lines.append("")
        if phone:
            receipt_lines.append(center(f"Tel: {phone}"))
            receipt_lines.append("")
        receipt_lines.extend(
            [
                line(),
                center("COMPROBANTE DE PAGO"),
                line(),
                "",
                f"Fecha: {sale_data.get('timestamp', '')}",
                "",
                f"Atendido por: {sale_data.get('user', 'Desconocido')}",
                "",
                line(),
            ]
        )

        # Agregar ítems
        for item in items:
            receipt_lines.append("")
            description = item.get("description", "")
            for desc_line in self._wrap_receipt_lines(description, receipt_width):
                receipt_lines.append(desc_line)
            left_text = (
                f"{item.get('quantity', 0)} {item.get('unit', '')} x "
                f"{self._format_currency(item.get('price', 0))}"
            )
            right_text = self._format_currency(item.get("subtotal", 0))
            available = max(receipt_width - len(right_text) - 1, 1)
            left_lines = self._wrap_receipt_lines(left_text, available)
            if left_lines:
                for line_part in left_lines[:-1]:
                    receipt_lines.append(line_part)
                receipt_lines.append(row(left_lines[-1], right_text, receipt_width))
            else:
                receipt_lines.append(row("", right_text, receipt_width))
            receipt_lines.append("")
            receipt_lines.append(line())

        # Total y método de pago
        receipt_lines.append("")
        receipt_lines.append(
            row("TOTAL A PAGAR:", self._format_currency(sale_data.get("total", 0)))
        )
        receipt_lines.append("")
        receipt_lines.extend(
            self._wrap_receipt_label_value(
                "Metodo de Pago", payment_summary, receipt_width
            )
        )
        receipt_lines.append("")
        receipt_lines.append(line())
        receipt_lines.append("")
        if footer_message:
            for footer_line in self._wrap_receipt_lines(footer_message, receipt_width):
                receipt_lines.append(center(footer_line))
        receipt_lines.extend([" ", " ", " "])

        receipt_text = chr(10).join(receipt_lines)
        safe_receipt_text = html.escape(receipt_text)

        html_content = f"""<html>
<head>
<meta charset='utf-8'/>
<title>Comprobante de Pago</title>
<style>
@page {{ size: {paper_width_mm}mm auto; margin: 0; }}
body {{ margin: 0; padding: 2mm; }}
pre {{ font-family: monospace; font-size: 12px; margin: 0; white-space: pre-wrap; word-break: break-word; }}
</style>
</head>
<body>
<pre>{safe_receipt_text}</pre>
</body>
</html>"""

        script = f"""
        const receiptWindow = window.open('', '_blank');
        receiptWindow.document.write({json.dumps(html_content)});
        receiptWindow.document.close();
        receiptWindow.focus();
        receiptWindow.print();
        """
        return rx.call_script(script)
