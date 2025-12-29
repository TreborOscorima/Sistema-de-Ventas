import json
from typing import Any, Dict, List

import reflex as rx
from sqlmodel import select

from app.models import Sale


class ReceiptMixin:
    last_sale_receipt: List[Dict[str, Any]] = []
    last_sale_total: float = 0
    last_sale_timestamp: str = ""
    sale_receipt_ready: bool = False
    last_sale_reservation_context: Dict | None = None
    last_payment_summary: str = ""

    def _print_receipt_logic(self, receipt_id: str | None = None):
        # Determine data source
        receipt_items = []
        total = 0.0
        timestamp = ""
        user_name = ""
        payment_summary = ""
        reservation_context = None

        if receipt_id:
            # Fetch from DB for reprint
            with rx.session() as session:
                try:
                    sale = session.exec(select(Sale).where(Sale.id == int(receipt_id))).first()
                    if not sale:
                        return rx.toast("Venta no encontrada.", duration=3000)

                    timestamp = sale.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    total = sale.total_amount
                    payment_summary = (
                        self._payment_details_text(sale.payment_details)
                        or sale.payment_method
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
            # Use current state
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

        # Funciones auxiliares para formato de texto plano
        def center(text, width=42):
            return text.center(width)

        def line(width=42):
            return "-" * width

        def row(left, right, width=42):
            spaces = width - len(left) - len(right)
            return left + " " * max(spaces, 1) + right

        # Construir recibo l¡nea por l¡nea
        receipt_lines = [
            "",
            center("LUXETY SPORT S.A.C."),
            "",
            center("RUC: 20601348676"),
            "",
            center("AV. ALFONSO UGARTE NRO. 096"),
            center("LIMA-LIMA"),
            "",
            line(),
            center("COMPROBANTE DE PAGO"),
            line(),
            "",
            f"Fecha: {timestamp}",
            "",
            f"Atendido por: {user_name}",
            "",
            line(),
        ]

        # Agregar contexto de reserva si existe
        if reservation_context:
            ctx = reservation_context
            header = ctx.get("header", "")
            products_total = ctx.get("products_total", 0)

            if header:
                receipt_lines.append("")
                receipt_lines.append(center(header))
                receipt_lines.append("")
                receipt_lines.append(line())

            receipt_lines.append("")
            receipt_lines.append(row("TOTAL RESERVA:", self._format_currency(ctx["total"])))
            receipt_lines.append("")
            receipt_lines.append(
                row("Adelanto previo:", self._format_currency(ctx["paid_before"]))
            )
            receipt_lines.append("")
            receipt_lines.append(row("PAGO ACTUAL:", self._format_currency(ctx["paid_now"])))
            receipt_lines.append("")

            if products_total > 0:
                receipt_lines.append(row("PRODUCTOS:", self._format_currency(products_total)))
                receipt_lines.append("")

            receipt_lines.append(
                row("Saldo pendiente:", self._format_currency(ctx.get("balance_after", 0)))
            )
            receipt_lines.append("")
            receipt_lines.append(line())

        # Agregar ¡tems
        for item in receipt_items:
            receipt_lines.append("")
            receipt_lines.append(item["description"])
            receipt_lines.append(
                f"{item['quantity']} {item['unit']} x {self._format_currency(item['price'])}    {self._format_currency(item['subtotal'])}"
            )
            receipt_lines.append("")
            receipt_lines.append(line())

        # Total y m‚todo de pago
        receipt_lines.extend(
            [
                "",
                row("TOTAL A PAGAR:", self._format_currency(total)),
                "",
                f"Metodo de Pago: {payment_summary}",
                "",
                line(),
                "",
                center("GRACIAS POR SU PREFERENCIA"),
                " ",
                " ",
                " ",
            ]
        )

        receipt_text = chr(10).join(receipt_lines)

        html_content = f"""<html>
<head>
<meta charset='utf-8'/>
<title>Comprobante de Pago</title>
<style>
@page {{ size: 80mm auto; margin: 0; }}
body {{ margin: 0; padding: 2mm; }}
pre {{ font-family: monospace; font-size: 12px; margin: 0; white-space: pre-wrap; }}
</style>
</head>
<body>
<pre>{receipt_text}</pre>
</body>
</html>"""

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
