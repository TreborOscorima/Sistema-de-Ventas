"""Servicio de Generador Masivo de Etiquetas.

Genera un PDF con etiquetas de código de barras listas para imprimir.

Filtros disponibles:
  - "all"           : todos los productos activos
  - "price_changed" : productos cuyo sale_price cambió en los últimos N días
  - "no_barcode"    : productos con barcode vacío o genérico (para asignar código)

Tamaños de etiqueta soportados:
  - "small"   : 50x30mm — precio + código de barras + nombre corto
  - "medium"  : 70x40mm — todo + categoría
  - "large"   : 100x60mm — todo + precio de compra opcional

Los barcodes se generan con reportlab.graphics.barcode (incluido en reportlab).
Si el producto no tiene barcode válido se usa el ID formateado como EAN-interno.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, and_, or_

from app.models import Product, ProductVariant
from app.utils.db import get_async_session
from app.utils.tenant import set_tenant_context
from app.utils.timezone import utc_now_naive

logger = logging.getLogger(__name__)

LabelSize = Literal["small", "medium", "large"]
LabelFilter = Literal["all", "price_changed", "no_barcode"]
LabelPageFormat = Literal["a4", "thermal_58", "thermal_80"]

_LABEL_DIMS: dict[str, tuple[float, float]] = {
    # (ancho_mm, alto_mm)
    "small": (50.0, 30.0),
    "medium": (70.0, 40.0),
    "large": (100.0, 60.0),
}
_LABELS_PER_ROW = {"small": 4, "medium": 3, "large": 2}
# Área imprimible de rollo térmico (papel - márgenes mínimos)
_THERMAL_PRINTABLE_W: dict[str, float] = {"thermal_58": 48.0, "thermal_80": 72.0}
_GENERIC_BARCODES = {"0000000000000", "0", "", "N/A", "n/a"}


@dataclass
class LabelConfig:
    size: LabelSize = "medium"
    filter_type: LabelFilter = "all"
    price_changed_days: int = 7
    show_purchase_price: bool = False
    copies: int = 1  # copias por producto
    company_name: str = ""
    currency_symbol: str = "S/ "
    category: str | None = None          # None = todas las categorías
    page_format: LabelPageFormat = "a4"  # a4 | thermal_58 | thermal_80


class LabelService:

    @staticmethod
    def resolve_barcode(product) -> str:
        """Retorna el barcode del producto o genera uno interno basado en el ID."""
        bc = (getattr(product, "barcode", None) or "").strip()
        if not bc or bc in _GENERIC_BARCODES:
            return f"INT{product.id:010d}"
        return bc

    # ── Obtener productos para etiquetar ────────────────────────────────

    @staticmethod
    async def get_products_for_labels(
        config: LabelConfig,
        company_id: int,
        branch_id: int,
        session: AsyncSession | None = None,
    ) -> list[dict]:
        set_tenant_context(company_id, branch_id)
        try:
            if session is None:
                async with get_async_session() as s:
                    return await LabelService._query_products(s, config, company_id, branch_id)
            return await LabelService._query_products(session, config, company_id, branch_id)
        finally:
            set_tenant_context(None, None)

    @staticmethod
    async def _query_products(
        session: AsyncSession,
        config: LabelConfig,
        company_id: int,
        branch_id: int,
    ) -> list[dict]:
        stmt = (
            select(Product)
            .options(selectinload(Product.variants))
            .where(Product.company_id == company_id)
            .where(Product.branch_id == branch_id)
            .where(Product.is_active == True)
        )

        if config.filter_type == "price_changed":
            cutoff = utc_now_naive() - timedelta(days=config.price_changed_days)
            stmt = stmt.where(Product.sale_price_updated_at >= cutoff)

        if config.category:
            stmt = stmt.where(Product.category == config.category)

        stmt = stmt.order_by(Product.category, Product.description)
        products = (await session.execute(stmt)).scalars().all()

        result: list[dict] = []
        for p in products:
            active_variants = [
                v for v in (p.variants or [])
                if v.company_id == company_id and v.branch_id == branch_id
            ]
            if active_variants:
                for v in active_variants:
                    parts = []
                    if v.size:
                        parts.append(str(v.size).strip())
                    if v.color:
                        parts.append(str(v.color).strip())
                    label = " ".join(parts)
                    sku = (v.sku or "").strip()
                    # Solo nombre + talla/color; el SKU/barcode va bajo el código de barras
                    description = (p.description or "") + (f" ({label})" if label else "")
                    bc_valid = sku and sku not in _GENERIC_BARCODES
                    bc = sku if bc_valid else f"INT{p.id:010d}"
                    if config.filter_type == "no_barcode" and bc_valid:
                        continue
                    result.append({
                        "id": p.id,
                        "variant_id": v.id,
                        "barcode": bc,
                        "description": description,
                        "category": p.category or "",
                        "sale_price": float(p.sale_price or 0),
                        "purchase_price": float(p.purchase_price or 0),
                        "unit": p.unit or "Unidad",
                    })
            else:
                bc = LabelService.resolve_barcode(p)
                if config.filter_type == "no_barcode" and not bc.startswith("INT"):
                    continue
                result.append({
                    "id": p.id,
                    "variant_id": None,
                    "barcode": bc,
                    "description": p.description or "",
                    "category": p.category or "",
                    "sale_price": float(p.sale_price or 0),
                    "purchase_price": float(p.purchase_price or 0),
                    "unit": p.unit or "Unidad",
                })
        return result

    # ── Generar PDF de etiquetas ────────────────────────────────────────

    @staticmethod
    def generate_pdf(products: list[dict], config: LabelConfig) -> bytes:
        """Genera PDF con etiquetas de código de barras para imprimir."""
        if config.page_format == "a4":
            return LabelService._generate_pdf_a4(products, config)
        return LabelService._generate_pdf_thermal(products, config)

    @staticmethod
    def _generate_pdf_a4(products: list[dict], config: LabelConfig) -> bytes:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas as rl_canvas
        except ImportError:
            logger.error("reportlab no está instalado.")
            raise

        buffer = io.BytesIO()
        page_w, page_h = A4
        margin = 10 * mm

        label_w_mm, label_h_mm = _LABEL_DIMS[config.size]
        label_w = label_w_mm * mm
        label_h = label_h_mm * mm
        labels_per_row = _LABELS_PER_ROW[config.size]

        gap_h = 2 * mm
        gap_v = 2 * mm

        c = rl_canvas.Canvas(buffer, pagesize=A4)

        all_labels: list[dict] = [
            p for p in products for _ in range(max(1, config.copies))
        ]

        if not all_labels:
            c.setFont("Helvetica", 12)
            c.drawCentredString(page_w / 2, page_h / 2, "Sin productos para etiquetar.")
            c.save()
            buffer.seek(0)
            return buffer.read()

        col = 0
        row = 0
        max_rows_per_page = int((page_h - 2 * margin) / (label_h + gap_v))

        for product in all_labels:
            if col == labels_per_row:
                col = 0
                row += 1

            if row >= max_rows_per_page:
                c.showPage()
                row = 0
                col = 0

            x = margin + col * (label_w + gap_h)
            y = page_h - margin - (row + 1) * (label_h + gap_v) + gap_v

            _draw_label(c, x, y, label_w, label_h, product, config)
            col += 1

        c.save()
        buffer.seek(0)
        return buffer.read()

    @staticmethod
    def _generate_pdf_thermal(products: list[dict], config: LabelConfig) -> bytes:
        """Genera PDF para impresora térmica de rollo (58mm o 80mm).

        Cada etiqueta ocupa una página del PDF con las dimensiones exactas del
        rollo. El driver de la impresora térmica avanza/corta entre páginas.
        """
        try:
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas as rl_canvas
        except ImportError:
            logger.error("reportlab no está instalado.")
            raise

        roll_w = _THERMAL_PRINTABLE_W[config.page_format] * mm
        _, label_h_mm = _LABEL_DIMS[config.size]
        label_h = label_h_mm * mm

        buffer = io.BytesIO()
        c = rl_canvas.Canvas(buffer, pagesize=(roll_w, label_h))

        all_labels: list[dict] = [
            p for p in products for _ in range(max(1, config.copies))
        ]

        if not all_labels:
            c.setFont("Helvetica", 7)
            c.drawCentredString(roll_w / 2, label_h / 2, "Sin productos.")
            c.save()
            buffer.seek(0)
            return buffer.read()

        for i, product in enumerate(all_labels):
            _draw_label(c, 0, 0, roll_w, label_h, product, config)
            if i < len(all_labels) - 1:
                c.showPage()

        c.save()
        buffer.seek(0)
        return buffer.read()


# ─── Helpers internos ────────────────────────────────────────────────────────

def _resolve_barcode(product: Product) -> str:
    """Retorna el barcode del producto o genera uno interno basado en el ID."""
    bc = (product.barcode or "").strip()
    if not bc or bc in _GENERIC_BARCODES:
        return f"INT{product.id:010d}"
    return bc


def _wrap_text(
    text: str, font_name: str, font_size: float, max_width: float
) -> list[str]:
    """Divide texto en líneas que caben en max_width (puntos ReportLab)."""
    from reportlab.pdfbase.pdfmetrics import stringWidth

    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        if stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            # Palabra sola más ancha que el área: truncar
            if stringWidth(word, font_name, font_size) > max_width:
                while len(word) > 1 and stringWidth(word + "…", font_name, font_size) > max_width:
                    word = word[:-1]
                word += "…"
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _draw_label(
    c: "rl_canvas.Canvas",
    x: float,
    y: float,
    w: float,
    h: float,
    product: dict,
    config: LabelConfig,
) -> None:
    """Dibuja una etiqueta individual con marcas de corte y nombre con wrap."""
    from reportlab.lib.units import mm
    from reportlab.graphics.barcode import code128
    from reportlab.lib import colors
    from reportlab.pdfbase.pdfmetrics import stringWidth

    pad = 2 * mm
    inner_x = x + pad
    inner_w = w - 2 * pad

    # ── Marcas de corte en las cuatro esquinas ────────────────────────
    c.setStrokeColor(colors.HexColor("#94A3B8"))
    c.setLineWidth(0.5)
    cut = 3 * mm
    # Inferior-izquierda
    c.line(x, y, x + cut, y)
    c.line(x, y, x, y + cut)
    # Inferior-derecha
    c.line(x + w - cut, y, x + w, y)
    c.line(x + w, y, x + w, y + cut)
    # Superior-izquierda
    c.line(x, y + h, x + cut, y + h)
    c.line(x, y + h, x, y + h - cut)
    # Superior-derecha
    c.line(x + w - cut, y + h, x + w, y + h)
    c.line(x + w, y + h, x + w, y + h - cut)

    # ── Métricas de fuentes ───────────────────────────────────────────
    name_font = "Helvetica-Bold"
    name_size = 7 if config.size == "small" else 8
    price_font = "Helvetica-Bold"
    price_size = 9 if config.size == "small" else 11 if config.size == "medium" else 13
    line_h = name_size * 1.3  # interlineado en puntos

    # ── Precio: calcular ancho antes de posicionar el nombre ──────────
    price = product.get("sale_price", 0)
    currency = config.currency_symbol.strip()
    price_str = f"{currency} {float(price):.2f}"
    c.setFont(price_font, price_size)
    price_w = stringWidth(price_str, price_font, price_size)

    # ── Nombre con word-wrap (reserva espacio para el precio) ─────────
    name = product.get("description") or ""
    name_avail_w = inner_w - price_w - 2 * mm
    c.setFont(name_font, name_size)
    name_lines = _wrap_text(name, name_font, name_size, name_avail_w)

    max_lines = 2
    if len(name_lines) > max_lines:
        name_lines = name_lines[:max_lines]
        last = name_lines[-1]
        while last and stringWidth(last + "…", name_font, name_size) > name_avail_w:
            last = last[:-1]
        name_lines[-1] = last + "…"

    # ── Baseline de la primera línea (anclada al borde superior) ──────
    top_y = y + h - pad - name_size * 0.4 * mm

    # ── Dibujar nombre línea a línea ──────────────────────────────────
    c.setFillColor(colors.black)
    c.setFont(name_font, name_size)
    for i, line in enumerate(name_lines):
        c.drawString(inner_x, top_y - i * line_h, line)

    # ── Dibujar precio (alineado top-right al mismo baseline) ─────────
    c.setFont(price_font, price_size)
    c.setFillColor(colors.HexColor("#4F46E5"))
    c.drawRightString(x + w - pad, top_y, price_str)
    c.setFillColor(colors.black)

    # Y después del bloque de nombre
    after_name_y = top_y - len(name_lines) * line_h

    # ── Categoría (medium / large) ────────────────────────────────────
    if config.size != "small":
        cat = (product.get("category") or "").strip()
        if cat:
            if len(cat) > 30:
                cat = cat[:29] + "…"
            c.setFont("Helvetica", 6)
            c.setFillColor(colors.HexColor("#64748B"))
            c.drawString(inner_x, after_name_y - 1.5, cat)
            c.setFillColor(colors.black)

    # ── Precio de compra (large + activado) ───────────────────────────
    if config.size == "large" and config.show_purchase_price:
        pp = product.get("purchase_price", 0)
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.HexColor("#94A3B8"))
        c.drawRightString(
            x + w - pad,
            after_name_y - 1.5,
            f"Costo: {currency} {float(pp):.2f}",
        )
        c.setFillColor(colors.black)

    # ── Código de barras ──────────────────────────────────────────────
    barcode_val = product.get("barcode") or ""
    if barcode_val:
        try:
            bc_height = {
                "small": 8 * mm,
                "medium": 12 * mm,
                "large": 16 * mm,
            }[config.size]
            bc = code128.Code128(
                barcode_val,
                barHeight=bc_height,
                barWidth=0.6,
                humanReadable=True,
                fontSize=6,
                fontName="Helvetica",
            )
            if bc.width > inner_w:
                ratio = (inner_w * 0.92) / bc.width
                bc = code128.Code128(
                    barcode_val,
                    barHeight=bc_height,
                    barWidth=max(0.22, 0.6 * ratio),
                    humanReadable=True,
                    fontSize=6,
                    fontName="Helvetica",
                )
            bc_x = x + (w - bc.width) / 2
            bc_y = y + pad
            bc.drawOn(c, bc_x, bc_y)
        except Exception:
            c.setFont("Helvetica", 6)
            c.drawCentredString(x + w / 2, y + pad + 3 * mm, barcode_val)
