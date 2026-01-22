"""Mixin de Exportación para CashState.

Este módulo gestiona la exportación de reportes de caja:
- Reporte de ventas (Excel)
- Cierre de caja (PDF)
- Aperturas y cierres (Excel)
- Movimientos de caja chica (Excel)

Utiliza las utilidades de app.utils.exports para generar los archivos.
"""
import datetime
import io
from typing import Any

import reflex as rx

from app.utils.exports import (
    create_excel_workbook,
    style_header_row,
    auto_adjust_column_widths,
    create_pdf_report,
    add_company_header,
    add_totals_row_with_formulas,
    add_notes_section,
    CURRENCY_FORMAT,
    THIN_BORDER,
)


class CashExportMixin:
    """Mixin para exportación de reportes de caja.
    
    Atributos requeridos del State padre:
        - current_user: dict con username y privileges
        - _cashbox_guard(): método de validación
        - _fetch_cashbox_sales(): obtiene ventas
        - _fetch_cashbox_logs(): obtiene logs de caja
        - petty_cash_movements: lista de movimientos caja chica
        - cashbox_close_summary_*: datos del cierre
        - _build_cashbox_close_breakdown(): construye resumen
        - _get_day_sales(): ventas del día
        - _format_currency(): formateo de moneda
        - _round_currency(): redondeo
        - _normalize_wallet_label(): normaliza etiquetas
        - _payment_details_text(): texto de detalles de pago
    """

    # =========================================================================
    # EXPORTACIÓN: Reporte de Ventas (Excel)
    # =========================================================================

    @rx.event
    def export_cashbox_report(self):
        """Exporta el reporte de ventas de caja a Excel."""
        denial = self._cashbox_guard()
        if denial:
            return denial
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)
        
        sales = self._fetch_cashbox_sales()
        if not sales:
            return rx.toast("No hay ventas para exportar.", duration=3000)
        
        # Obtener nombre de empresa
        company_name = getattr(self, "company_name", "") or "EMPRESA"
        today = datetime.datetime.now().strftime("%d/%m/%Y")
        
        wb, ws = create_excel_workbook("Resumen de Caja")
        
        # Agregar encabezado profesional
        row = add_company_header(ws, company_name, "RESUMEN DE GESTIÓN DE CAJA", f"Fecha: {today}", columns=8)
        
        headers = [
            "Fecha y Hora",
            "Vendedor",
            "Método de Pago",
            "Detalle del Método",
            "Referencia/Descripción",
            "Monto Total (S/)",
            "Monto Cobrado (S/)",
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
                        method_raw = "No especificado"
                if (method_label or "").strip().lower() in invalid_labels:
                    if (method_raw or "").strip().lower() not in invalid_labels:
                        method_label = method_raw
                    else:
                        method_label = "No especificado"
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
            details = ", ".join(item_parts) if item_parts else "Sin detalle"
            
            ws.cell(row=row, column=1, value=sale["timestamp"])
            ws.cell(row=row, column=2, value=sale["user"])
            ws.cell(row=row, column=3, value=method_raw)
            ws.cell(row=row, column=4, value=method_label)
            ws.cell(row=row, column=5, value=payment_details)
            ws.cell(row=row, column=6, value=float(sale["total"] or 0)).number_format = CURRENCY_FORMAT
            ws.cell(row=row, column=7, value=float(sale.get("amount", 0) or 0)).number_format = CURRENCY_FORMAT
            ws.cell(row=row, column=8, value=details)
            
            for col in range(1, 9):
                ws.cell(row=row, column=col).border = THIN_BORDER
            row += 1
        
        # Fila de totales con fórmulas
        totals_row = row
        add_totals_row_with_formulas(ws, totals_row, data_start, [
            {"type": "label", "value": "TOTALES"},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "sum", "col_letter": "F", "number_format": CURRENCY_FORMAT},
            {"type": "sum", "col_letter": "G", "number_format": CURRENCY_FORMAT},
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

    # =========================================================================
    # EXPORTACIÓN: Cierre de Caja (PDF)
    # =========================================================================

    @rx.event
    def export_cashbox_close_pdf(self):
        """Exporta el reporte de cierre de caja a PDF."""
        if not (
            self.current_user["privileges"]["view_cashbox"]
            and self.current_user["privileges"]["export_data"]
        ):
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)

        report_date = self.cashbox_close_summary_date or datetime.datetime.now().strftime(
            "%Y-%m-%d"
        )
        breakdown = self._build_cashbox_close_breakdown(report_date)
        summary = breakdown["summary"]
        day_sales = self.cashbox_close_summary_sales or self._get_day_sales(report_date)

        if not summary and not day_sales and breakdown["opening_amount"] == 0:
            return rx.toast("No hay movimientos de caja para exportar.", duration=3000)

        info_dict = {
            "Fecha Cierre": report_date,
            "Responsable": self.current_user["username"],
        }
        total_value = 0.0
        for item in summary:
            total = item.get("total", 0) or 0
            if total <= 0:
                continue
            method = (item.get("method", "No especificado") or "").strip() or "No especificado"
            info_dict[f"Total {method}"] = self._format_currency(total)
            total_value += float(total)

        info_dict["Apertura"] = self._format_currency(breakdown["opening_amount"])
        info_dict["Ingresos reales"] = self._format_currency(breakdown["income_total"])
        info_dict["Egresos caja chica"] = self._format_currency(breakdown["expense_total"])
        info_dict["Saldo esperado"] = self._format_currency(breakdown["expected_total"])

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

        headers = ["Hora", "Operación", "Método", "Referencia", "Monto"]
        data = []
        for sale in day_sales:
            if sale.get("is_deleted"):
                continue
            operation_raw = sale.get("action") or sale.get("type") or "Venta"
            operation = str(operation_raw).replace("_", " ").strip().title() or "Venta"
            method_raw = sale.get("payment_label") or sale.get("payment_method") or ""
            method_label = (
                self._normalize_wallet_label(method_raw) if method_raw else "No especificado"
            )
            reference = self._payment_details_text(sale.get("payment_details", ""))
            amount = sale.get("total")
            if amount is None:
                amount = sale.get("amount", 0)
            data.append(
                [
                    _format_time(sale.get("timestamp", "")),
                    operation,
                    method_label,
                    reference,
                    _format_amount(amount),
                ]
            )

        output = io.BytesIO()
        create_pdf_report(
            output,
            "Reporte de Cierre de Caja",
            data,
            headers,
            info_dict,
        )

        return rx.download(data=output.getvalue(), filename="cierre_caja.pdf")

    # =========================================================================
    # EXPORTACIÓN: Aperturas y Cierres (Excel)
    # =========================================================================

    @rx.event
    def export_cashbox_sessions(self):
        """Exporta el historial de aperturas y cierres a Excel."""
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)
        logs = self._fetch_cashbox_logs()
        if not logs:
            return rx.toast("No hay aperturas o cierres para exportar.", duration=3000)
        
        company_name = getattr(self, "company_name", "") or "EMPRESA"
        today = datetime.datetime.now().strftime("%d/%m/%Y")
        
        wb, ws = create_excel_workbook("Aperturas y Cierres")
        
        # Encabezado profesional
        row = add_company_header(ws, company_name, "REGISTRO DE APERTURAS Y CIERRES DE CAJA", f"Generado: {today}", columns=7)
        
        headers = [
            "Fecha y Hora",
            "Tipo de Operación",
            "Responsable",
            "Monto Apertura (S/)",
            "Monto Cierre (S/)",
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
            action_display = "Apertura de Caja" if action == "apertura" else "Cierre de Caja" if action == "cierre" else action.capitalize()
            
            opening_amount = float(log.get("opening_amount", 0) or 0)
            closing_amount = float(log.get("closing_total", 0) or 0)
            
            if action == "apertura":
                total_aperturas += opening_amount
            elif action == "cierre":
                total_cierres += closing_amount
            
            totals_detail = ", ".join(
                f"{item.get('method', 'Otro')}: S/{self._round_currency(item.get('amount', 0))}"
                for item in log.get("totals_by_method", [])
                if item.get("amount", 0)
            ) or "Sin desglose"
            
            ws.cell(row=row, column=1, value=log.get("timestamp", ""))
            ws.cell(row=row, column=2, value=action_display)
            ws.cell(row=row, column=3, value=log.get("user", "Desconocido"))
            ws.cell(row=row, column=4, value=opening_amount).number_format = CURRENCY_FORMAT
            ws.cell(row=row, column=5, value=closing_amount).number_format = CURRENCY_FORMAT
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
            {"type": "sum", "col_letter": "D", "number_format": CURRENCY_FORMAT},
            {"type": "sum", "col_letter": "E", "number_format": CURRENCY_FORMAT},
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

    # =========================================================================
    # EXPORTACIÓN: Caja Chica (Excel)
    # =========================================================================

    @rx.event
    def export_petty_cash_report(self):
        """Exporta los movimientos de caja chica a Excel."""
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)
        
        movements = self.petty_cash_movements
        if not movements:
            return rx.toast("No hay movimientos para exportar.", duration=3000)
        
        company_name = getattr(self, "company_name", "") or "EMPRESA"
        today = datetime.datetime.now().strftime("%d/%m/%Y")
        
        wb, ws = create_excel_workbook("Caja Chica")
        
        # Encabezado profesional
        row = add_company_header(ws, company_name, "MOVIMIENTOS DE CAJA CHICA", f"Generado: {today}", columns=7)
        
        headers = [
            "Fecha y Hora",
            "Responsable",
            "Concepto/Motivo",
            "Cantidad",
            "Unidad",
            "Costo Unitario (S/)",
            "Total Egreso (S/)",
        ]
        style_header_row(ws, row, headers)
        data_start = row + 1
        row += 1
        
        for item in movements:
            # Extraer valores numéricos para las fórmulas
            quantity_str = item.get("formatted_quantity", "0")
            cost_str = item.get("formatted_cost", "0")
            
            # Limpiar strings de formato para obtener números
            try:
                quantity = float(str(quantity_str).replace(",", "").replace("S/", "").strip() or 0)
            except:
                quantity = 0
            try:
                cost = float(str(cost_str).replace(",", "").replace("S/", "").strip() or 0)
            except:
                cost = 0
            
            ws.cell(row=row, column=1, value=item.get("timestamp", ""))
            ws.cell(row=row, column=2, value=item.get("user", "Desconocido"))
            ws.cell(row=row, column=3, value=item.get("notes", "") or "Sin motivo especificado")
            ws.cell(row=row, column=4, value=quantity)
            ws.cell(row=row, column=5, value=item.get("unit", "Unid."))
            ws.cell(row=row, column=6, value=cost).number_format = CURRENCY_FORMAT
            # Total = Fórmula: Cantidad × Costo Unitario
            ws.cell(row=row, column=7, value=f"=D{row}*F{row}").number_format = CURRENCY_FORMAT
            
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
            {"type": "sum", "col_letter": "G", "number_format": CURRENCY_FORMAT},
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
