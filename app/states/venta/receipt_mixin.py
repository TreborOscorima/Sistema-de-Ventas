import json
from decimal import Decimal
from typing import Any, Dict, List

import reflex as rx
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.models import Sale
from app.services.receipt_service import ReceiptService
from app.utils.db import get_async_session


class ReceiptMixin:
    last_sale_id: str = ""
    last_sale_receipt: List[Dict[str, Any]] = []
    last_sale_total: float = 0
    last_sale_timestamp: str = ""
    sale_receipt_ready: bool = False
    last_sale_reservation_context: Dict | None = None
    last_payment_summary: str = ""
    show_sale_receipt_modal: bool = False

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
        branch_id = None
        use_state = False
        if (
            receipt_id
            and self.sale_receipt_ready
            and self.last_sale_receipt
            and str(receipt_id) == str(getattr(self, "last_sale_id", ""))
        ):
            use_state = True

        if receipt_id and not use_state:
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

                    branch_id = sale.branch_id
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
            if hasattr(self, "_branch_id"):
                branch_id = self._branch_id()
            payment_summary = self.last_payment_summary
            if not payment_summary or payment_summary == "No especificado":
                payment_summary = self._legacy_payment_summary(
                    getattr(self, "last_payment_details", None),
                    getattr(self, "last_payment_method", None),
                )

        company = self._company_settings_snapshot(branch_id=branch_id)
        receipt_width = self._receipt_width(branch_id=branch_id)
        paper_width_mm = self._receipt_paper_mm(branch_id=branch_id)
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
            "branch_id": branch_id,
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
        if self.last_sale_reservation_context and (not receipt_id or use_state):
            if hasattr(self, "reservation_payment_id"):
                self.reservation_payment_id = ""
            if hasattr(self, "reservation_payment_amount"):
                self.reservation_payment_amount = ""
            self.last_sale_reservation_context = None

        if not receipt_id or use_state:
            self._reset_payment_fields()
            self._refresh_payment_feedback()

        return rx.call_script(script)

    @rx.event
    def print_sale_receipt(self):
        receipt_id = str(self.last_sale_id or "").strip()
        return self._print_receipt_logic(receipt_id or None)

    @rx.event
    def print_sale_receipt_by_id(self, receipt_id: str):
        return self._print_receipt_logic(receipt_id)

    @rx.event
    def print_receipt(self):
        receipt_id = str(self.last_sale_id or "").strip()
        self.show_sale_receipt_modal = False
        return self._print_receipt_logic(receipt_id or None)

    @rx.event
    def close_sale_receipt_modal(self):
        self.show_sale_receipt_modal = False

    def _notify_error(self, message: str):
        if hasattr(self, "notification_message"):
            self.notification_message = str(message or "")
            self.notification_type = "error"
            self.is_notification_open = True
        return None

    @rx.event
    async def download_pdf_receipt(self):
        self.show_sale_receipt_modal = False
        receipt_id = str(self.last_sale_id or "").strip()
        if not receipt_id:
            self._notify_error(
                "No hay comprobante disponible. Confirme una venta primero."
            )
            return

        receipt_items = []
        total = 0.0
        timestamp = ""
        user_name = ""
        payment_summary = ""
        reservation_context = None
        branch_id = None

        use_state = bool(self.sale_receipt_ready and self.last_sale_receipt)
        if use_state:
            receipt_items = self.last_sale_receipt
            reservation_context = self.last_sale_reservation_context
            total = (
                reservation_context.get("charged_total", self.last_sale_total)
                if reservation_context
                else self.last_sale_total
            )
            timestamp = self.last_sale_timestamp
            user_name = self.current_user.get("username", "Desconocido")
            if hasattr(self, "_branch_id"):
                branch_id = self._branch_id()
            payment_summary = self.last_payment_summary
            if not payment_summary or payment_summary == "No especificado":
                payment_summary = self._legacy_payment_summary(
                    getattr(self, "last_payment_details", None),
                    getattr(self, "last_payment_method", None),
                )
        else:
            company_id = None
            if hasattr(self, "current_user"):
                company_id = self.current_user.get("company_id")
            if hasattr(self, "_branch_id"):
                branch_id = self._branch_id()
            if not company_id or not branch_id:
                self._notify_error("Empresa o sucursal no definida.")
                return

            try:
                sale_id = int(receipt_id)
            except (TypeError, ValueError):
                self._notify_error("ID de venta inválido.")
                return

            async with get_async_session() as session:
                sale = (
                    await session.exec(
                        select(Sale)
                        .where(Sale.id == sale_id)
                        .where(Sale.company_id == int(company_id))
                        .where(Sale.branch_id == int(branch_id))
                        .options(
                            selectinload(Sale.payments),
                            selectinload(Sale.items),
                            selectinload(Sale.user),
                        )
                    )
                ).first()

            if not sale:
                self._notify_error("Venta no encontrada.")
                return

            branch_id = sale.branch_id
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

        company = self._company_settings_snapshot(branch_id=branch_id)
        receipt_width = self._receipt_width(branch_id=branch_id)
        paper_width_mm = self._receipt_paper_mm(branch_id=branch_id)
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
            "branch_id": branch_id,
        }

        try:
            pdf_bytes = ReceiptService.generate_receipt_pdf(
                receipt_data, company
            )
        except Exception:
            self._notify_error("Error al generar el PDF del comprobante.")
            return

        filename = f"comprobante_venta_{receipt_id}.pdf"
        return rx.download(data=pdf_bytes, filename=filename)
