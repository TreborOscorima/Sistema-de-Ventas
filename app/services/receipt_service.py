from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import html
from typing import Any, Dict, List


class ReceiptService:
    DEFAULT_WIDTH = 42

    @staticmethod
    def _round_currency(value: Any) -> Decimal:
        return Decimal(str(value or 0)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @staticmethod
    def _format_currency(value: Any, currency_symbol: str) -> str:
        rounded = ReceiptService._round_currency(value)
        return f"{currency_symbol}{float(rounded):.2f}"

    @staticmethod
    def _wrap_receipt_lines(text: str, width: int) -> List[str]:
        if not text:
            return []
        width = max(int(width), 1)
        parts = [part.strip() for part in text.splitlines() if part.strip()]
        if not parts:
            return []
        lines: List[str] = []
        for part in parts:
            words = part.split()
            if not words:
                continue
            current = ""
            for word in words:
                while len(word) > width:
                    if current:
                        lines.append(current)
                        current = ""
                    lines.append(word[:width])
                    word = word[width:]
                if not current:
                    current = word
                elif len(current) + 1 + len(word) <= width:
                    current = f"{current} {word}"
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)
        return lines

    @staticmethod
    def _wrap_receipt_label_value(label: str, value: str, width: int) -> List[str]:
        label = (label or "").strip()
        value = (value or "").strip()
        if not label:
            return ReceiptService._wrap_receipt_lines(value, width)
        prefix = f"{label}: "
        if not value:
            return [prefix.rstrip()]
        available = max(width - len(prefix), 1)
        value_lines = ReceiptService._wrap_receipt_lines(value, available)
        if not value_lines:
            return [prefix.rstrip()]
        lines = [prefix + value_lines[0]]
        indent = " " * len(prefix)
        lines.extend(f"{indent}{line}" for line in value_lines[1:])
        return lines

    @staticmethod
    def _center(text: str, width: int) -> str:
        return text.center(width)

    @staticmethod
    def _line(width: int) -> str:
        return "-" * width

    @staticmethod
    def _row(left: str, right: str, width: int) -> str:
        spaces = width - len(left) - len(right)
        return left + " " * max(spaces, 1) + right

    @staticmethod
    def generate_receipt_html(
        receipt_data: Dict[str, Any], company_settings: Dict[str, Any]
    ) -> str:
        data = receipt_data or {}
        company = company_settings or {}
        try:
            width = int(data.get("width", ReceiptService.DEFAULT_WIDTH))
        except (TypeError, ValueError):
            width = ReceiptService.DEFAULT_WIDTH
        width = max(24, min(width, 64))
        try:
            paper_width_mm = int(data.get("paper_width_mm", 80))
        except (TypeError, ValueError):
            paper_width_mm = 80
        if paper_width_mm < 40 or paper_width_mm > 90:
            paper_width_mm = 80
        currency_symbol = data.get("currency_symbol") or "S/ "

        receipt_items = data.get("items") or []
        total = data.get("total", 0)
        timestamp = data.get("timestamp", "")
        user_name = data.get("user_name", "")
        payment_summary = data.get("payment_summary", "")
        reservation_context = data.get("reservation_context")

        company_name = (company.get("company_name") or "").strip()
        ruc = (company.get("ruc") or "").strip()
        address = (company.get("address") or "").strip()
        phone = (company.get("phone") or "").strip()
        footer_message = (company.get("footer_message") or "").strip()
        address_lines = ReceiptService._wrap_receipt_lines(address, width)

        receipt_lines: list[str] = [""]
        if company_name:
            name_lines = ReceiptService._wrap_receipt_lines(company_name, width)
            for name_line in name_lines:
                receipt_lines.append(ReceiptService._center(name_line, width))
            receipt_lines.append("")
        if ruc:
            receipt_lines.append(
                ReceiptService._center(f"RUC: {ruc}", width)
            )
            receipt_lines.append("")
        for addr_line in address_lines:
            receipt_lines.append(ReceiptService._center(addr_line, width))
        if address_lines:
            receipt_lines.append("")
        if phone:
            receipt_lines.append(
                ReceiptService._center(f"Tel: {phone}", width)
            )
            receipt_lines.append("")
        receipt_lines.extend(
            [
                ReceiptService._line(width),
                ReceiptService._center("COMPROBANTE DE PAGO", width),
                ReceiptService._line(width),
                "",
                f"Fecha: {timestamp}",
                "",
                f"Atendido por: {user_name}",
                "",
                ReceiptService._line(width),
            ]
        )

        if reservation_context:
            ctx = reservation_context
            header = ctx.get("header", "")
            products_total = ctx.get("products_total", 0)

            if header:
                receipt_lines.append("")
                for header_line in ReceiptService._wrap_receipt_lines(header, width):
                    receipt_lines.append(ReceiptService._center(header_line, width))
                receipt_lines.append("")
                receipt_lines.append(ReceiptService._line(width))

            receipt_lines.append("")
            receipt_lines.append(
                ReceiptService._row(
                    "TOTAL RESERVA:",
                    ReceiptService._format_currency(ctx["total"], currency_symbol),
                    width,
                )
            )
            receipt_lines.append("")
            receipt_lines.append(
                ReceiptService._row(
                    "Adelanto previo:",
                    ReceiptService._format_currency(
                        ctx["paid_before"], currency_symbol
                    ),
                    width,
                )
            )
            receipt_lines.append("")
            receipt_lines.append(
                ReceiptService._row(
                    "PAGO ACTUAL:",
                    ReceiptService._format_currency(
                        ctx["paid_now"], currency_symbol
                    ),
                    width,
                )
            )
            receipt_lines.append("")

            if products_total > 0:
                receipt_lines.append(
                    ReceiptService._row(
                        "PRODUCTOS:",
                        ReceiptService._format_currency(
                            products_total, currency_symbol
                        ),
                        width,
                    )
                )
                receipt_lines.append("")

            receipt_lines.append(
                ReceiptService._row(
                    "Saldo pendiente:",
                    ReceiptService._format_currency(
                        ctx.get("balance_after", 0), currency_symbol
                    ),
                    width,
                )
            )
            receipt_lines.append("")
            receipt_lines.append(ReceiptService._line(width))

        for item in receipt_items:
            receipt_lines.append("")
            description = item.get("description", "")
            description_lines = ReceiptService._wrap_receipt_lines(description, width)
            for desc_line in description_lines:
                receipt_lines.append(desc_line)
            receipt_lines.append(
                (
                    f"{item['quantity']} {item['unit']} x "
                    f"{ReceiptService._format_currency(item['price'], currency_symbol)}"
                    f"    {ReceiptService._format_currency(item['subtotal'], currency_symbol)}"
                )
            )
            receipt_lines.append("")
            receipt_lines.append(ReceiptService._line(width))

        receipt_lines.append("")
        receipt_lines.append(
            ReceiptService._row(
                "TOTAL A PAGAR:",
                ReceiptService._format_currency(total, currency_symbol),
                width,
            )
        )
        receipt_lines.append("")
        receipt_lines.extend(
            ReceiptService._wrap_receipt_label_value(
                "Metodo de Pago", payment_summary, width
            )
        )
        receipt_lines.append("")
        receipt_lines.append(ReceiptService._line(width))
        receipt_lines.append("")
        if footer_message:
            footer_lines = ReceiptService._wrap_receipt_lines(footer_message, width)
            for footer_line in footer_lines:
                receipt_lines.append(ReceiptService._center(footer_line, width))
        receipt_lines.extend([" ", " ", " "])

        receipt_text = chr(10).join(receipt_lines)
        safe_receipt_text = html.escape(receipt_text)

        return f"""<html>
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
