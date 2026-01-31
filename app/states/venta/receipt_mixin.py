import json
from decimal import Decimal
from typing import Any, Dict, List

import reflex as rx
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.models import Sale
from app.services.receipt_service import ReceiptService


class ReceiptMixin:
    last_sale_receipt: List[Dict[str, Any]] = []
    last_sale_total: float = 0
    last_sale_timestamp: str = ""
    sale_receipt_ready: bool = False
    last_sale_reservation_context: Dict | None = None
    last_payment_summary: str = ""

    def _payment_method_key(self, method_type: Any) -> str:
        if hasattr(method_type, "value"):
            key = str(method_type.value).strip().lower()
        else:
            key = str(method_type or "").strip().lower()
        if key == "card":
            return "credit"
        if key == "wallet":
            return "yape"
        return key

    def _payment_method_label(self, method_key: str) -> str:
        mapping = {
            "cash": "Efectivo",
            "debit": "Tarjeta de Débito",
            "credit": "Tarjeta de Crédito",
            "yape": "Billetera Digital (Yape)",
            "plin": "Billetera Digital (Plin)",
            "transfer": "Transferencia Bancaria",
            "mixed": "Pago Mixto",
            "other": "Otros",
        }
        return mapping.get(method_key, "Otros")

    def _sorted_payment_keys(self, keys: list[str]) -> list[str]:
        order = [
            "cash",
            "debit",
            "credit",
            "yape",
            "plin",
            "transfer",
            "mixed",
            "other",
        ]
        ordered = [key for key in order if key in keys]
        for key in keys:
            if key not in ordered:
                ordered.append(key)
        return ordered

    def _payment_summary_from_payments(self, payments: list[Any]) -> str:
        if not payments:
            return "No especificado"
        totals: dict[str, Decimal] = {}
        for payment in payments:
            key = self._payment_method_key(getattr(payment, "method_type", None))
            if not key:
                continue
            amount = Decimal(str(getattr(payment, "amount", 0) or 0))
            totals[key] = totals.get(key, Decimal("0.00")) + amount
        if not totals:
            return "No especificado"
        parts = []
        for key in self._sorted_payment_keys(list(totals.keys())):
            label = self._payment_method_label(key)
            parts.append(f"{label}: {self._format_currency(totals[key])}")
        return ", ".join(parts)

    def _legacy_payment_summary(self, details: Any, method: Any) -> str:
        if details:
            formatter = getattr(self, "_payment_details_text", None)
            if callable(formatter):
                text = formatter(details)
                if text:
                    return text
            if isinstance(details, (dict, list)):
                try:
                    return json.dumps(details)
                except Exception:
                    return str(details)
            return str(details)
        if method:
            return str(method)
        return "No especificado"

    def _print_receipt_logic(self, receipt_id: str | None = None):
        # Determinar fuente de datos
        receipt_items = []
        total = 0.0
        timestamp = ""
        user_name = ""
        payment_summary = ""
        reservation_context = None

        if receipt_id:
            # Traer desde BD para reimpresion
            with rx.session() as session:
                try:
                    company_id = None
                    branch_id = None
                    if hasattr(self, "current_user"):
                        company_id = self.current_user.get("company_id")
                    if hasattr(self, "_branch_id"):
                        branch_id = self._branch_id()
                    if not company_id or not branch_id:
                        return rx.toast("Empresa o sucursal no definida.", duration=3000)
                    sale = session.exec(
                        select(Sale)
                        .where(Sale.id == int(receipt_id))
                        .where(Sale.company_id == int(company_id))
                        .where(Sale.branch_id == int(branch_id))
                        .options(
                            selectinload(Sale.payments),
                            selectinload(Sale.items),
                            selectinload(Sale.user),
                        )
                    ).first()
                    if not sale:
                        return rx.toast("Venta no encontrada.", duration=3000)

                    timestamp = sale.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    total = sale.total_amount
                    payment_summary = self._payment_summary_from_payments(
                        sale.payments or []
                    )
                    if not payment_summary or payment_summary == "No especificado":
                        payment_summary = self._legacy_payment_summary(
                            getattr(sale, "payment_details", None),
                            getattr(sale, "payment_method", None),
                        )
                    user_name = sale.user.username if sale.user else "Desconocido"

                    for item in sale.items:
                        receipt_items.append(
                            {
                                "description": item.product_name_snapshot,
                                "quantity": item.quantity,
                                "unit": "Unidad",
                                "price": item.unit_price,
                                "subtotal": item.subtotal,
                            }
                        )
                except ValueError:
                    return rx.toast("ID de venta inv lido.", duration=3000)
        else:
            # Usar estado actual
            if not self.sale_receipt_ready or not self.last_sale_receipt:
                return rx.toast(
                    "No hay comprobante disponible. Confirme una venta primero.",
                    duration=3000,
                )
            receipt_items = self.last_sale_receipt
            reservation_context = self.last_sale_reservation_context
            total = (
                reservation_context.get("charged_total", self.last_sale_total)
                if reservation_context
                else self.last_sale_total
            )
            timestamp = self.last_sale_timestamp
            user_name = self.current_user.get("username", "Desconocido")
            payment_summary = self.last_payment_summary
            if not payment_summary or payment_summary == "No especificado":
                payment_summary = self._legacy_payment_summary(
                    getattr(self, "last_payment_details", None),
                    getattr(self, "last_payment_method", None),
                )

        company = self._company_settings_snapshot()
        receipt_width = self._receipt_width()
        paper_width_mm = self._receipt_paper_mm()
        receipt_data = {
            "items": receipt_items,
            "total": total,
            "timestamp": timestamp,
            "user_name": user_name,
            "payment_summary": payment_summary,
            "reservation_context": reservation_context,
            "currency_symbol": self.currency_symbol,
            "width": receipt_width,
            "paper_width_mm": paper_width_mm,
        }

        html_content = ReceiptService.generate_receipt_html(
            receipt_data, company
        )

        script = f"""
        const receiptWindow = window.open('', '_blank');
        receiptWindow.document.write({json.dumps(html_content)});
        receiptWindow.document.close();
        receiptWindow.focus();
        receiptWindow.print();
        """
        # Para cobros de reserva, libera seleccion despues de imprimir
        if self.last_sale_reservation_context and not receipt_id:
            if hasattr(self, "reservation_payment_id"):
                self.reservation_payment_id = ""
            if hasattr(self, "reservation_payment_amount"):
                self.reservation_payment_amount = ""
            self.last_sale_reservation_context = None

        if not receipt_id:
            self._reset_payment_fields()
            self._refresh_payment_feedback()

        return rx.call_script(script)

    @rx.event
    def print_sale_receipt(self):
        return self._print_receipt_logic(None)

    @rx.event
    def print_sale_receipt_by_id(self, receipt_id: str):
        return self._print_receipt_logic(receipt_id)
