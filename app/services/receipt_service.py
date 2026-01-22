"""Servicio de Generación de Recibos.

Este módulo genera recibos de venta en formato HTML optimizado
para impresoras térmicas (POS) de 58mm y 80mm.

Características principales:
- Generación de HTML con estilos inline para compatibilidad
- Soporte para anchos de papel configurables (58mm, 80mm)
- Formateo de texto con word-wrap automático
- Escape de caracteres HTML para seguridad
- Secciones: encabezado empresa, items, totales, pie de página

Clase principal:
    ReceiptService: Métodos estáticos para generar recibos

Ejemplo de uso::

    from app.services.receipt_service import ReceiptService
    
    html = ReceiptService.generate_receipt_html(
        receipt_data={
            "items": [...],
            "total": 150.00,
            "timestamp": "2026-01-22 10:30:00",
            "user_name": "admin",
            "payment_summary": "Efectivo S/ 150.00",
            "width": 42,
            "paper_width_mm": 80,
        },
        company_settings={
            "company_name": "Mi Empresa",
            "ruc": "12345678901",
            "address": "Av. Principal 123",
            "phone": "999-888-777",
            "footer_message": "¡Gracias por su compra!",
        },
    )
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import html
from typing import Any, Dict, List


class ReceiptService:
    """Servicio para generación de recibos de venta.
    
    Genera HTML formateado para impresión en impresoras térmicas POS.
    Soporta anchos de 24 a 64 caracteres (58mm a 80mm de papel).
    
    Attributes:
        DEFAULT_WIDTH: Ancho por defecto en caracteres (42 para 80mm)
    """
    
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
        """Divide texto en líneas que caben en el ancho del recibo.
        
        Implementa word-wrap inteligente que:
        - Respeta límites de palabras
        - Corta palabras largas si exceden el ancho
        - Elimina líneas vacías
        
        Args:
            text: Texto a formatear
            width: Ancho máximo en caracteres
            
        Returns:
            Lista de líneas formateadas
        """
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
        """Genera HTML del recibo para impresión térmica.
        
        Crea un documento HTML completo con estilos inline optimizados
        para impresoras POS térmicas de 58mm u 80mm.
        
        Args:
            receipt_data: Diccionario con datos de la venta:
                - items (list): Productos vendidos [{description, quantity, unit, price, subtotal}]
                - total (float): Total de la venta
                - timestamp (str): Fecha/hora de la venta
                - user_name (str): Nombre del vendedor
                - payment_summary (str): Resumen del pago
                - width (int): Ancho en caracteres (default 42)
                - paper_width_mm (int): Ancho del papel en mm (58 o 80)
                - currency_symbol (str): Símbolo de moneda (default "S/ ")
                - reservation_context (dict): Datos de reserva (opcional)
                
            company_settings: Configuración de la empresa:
                - company_name (str): Nombre de la empresa
                - ruc (str): RUC o identificación fiscal
                - address (str): Dirección
                - phone (str): Teléfono
                - footer_message (str): Mensaje de pie de página
                
        Returns:
            String HTML completo listo para renderizar/imprimir
            
        Note:
            El HTML usa fuente monoespaciada (Courier New) para
            alineación consistente en impresoras térmicas.
        """
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
        tax_id_label = company.get("tax_id_label", "RUC")  # Dinámico por país
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
                ReceiptService._center(f"{tax_id_label}: {ruc}", width)
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
