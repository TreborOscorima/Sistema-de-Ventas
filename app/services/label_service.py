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
from app.utils.pricing import resolve_effective_price as _resolve_price
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
    show_pretax_price: bool = True        # muestra "PRECIO SIN IMPUESTOS" cuando tax_rate > 0


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
        global_margin: float = 0.0,
    ) -> list[dict]:
        set_tenant_context(company_id, branch_id)
        try:
            if session is None:
                async with get_async_session() as s:
                    return await LabelService._query_products(s, config, company_id, branch_id, global_margin)
            return await LabelService._query_products(session, config, company_id, branch_id, global_margin)
        finally:
            set_tenant_context(None, None)

    @staticmethod
    async def _query_products(
        session: AsyncSession,
        config: LabelConfig,
        company_id: int,
        branch_id: int,
        global_margin: float = 0.0,
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
                        "sale_price": float(_resolve_price(p, v, global_margin)),
                        "purchase_price": float(p.purchase_price or 0),
                        "unit": p.unit or "Unidad",
                        "tax_rate": float(getattr(p, "tax_rate", 0) or 0),
                        "tax_included": bool(getattr(p, "tax_included", True)),
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
                    "sale_price": float(_resolve_price(p, global_margin=global_margin)),
                    "purchase_price": float(p.purchase_price or 0),
                    "unit": p.unit or "Unidad",
                    "tax_rate": float(getattr(p, "tax_rate", 0) or 0),
                    "tax_included": bool(getattr(p, "tax_included", True)),
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
        gap_h = 2 * mm
        gap_v = 2 * mm

        _, label_h_mm = _LABEL_DIMS[config.size]
        label_h = label_h_mm * mm
        labels_per_row = _LABELS_PER_ROW[config.size]

        # Calcular ancho dinámicamente para que las columnas quepan siempre en el área imprimible
        available_w = page_w - 2 * margin
        label_w = (available_w - (labels_per_row - 1) * gap_h) / labels_per_row

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


def _fmt_thousands(
    value: float,
    decimals: int = 2,
    thousands_sep: str = ".",
    decimal_sep: str = ",",
) -> str:
    """Formatea número con separadores locales. Ej: 2179.5 → '2.179,50'"""
    s = f"{value:,.{decimals}f}"          # Python: "2,179.50"
    s = s.replace(",", "\x00").replace(".", decimal_sep).replace("\x00", thousands_sep)
    return s


def _draw_label(
    c: "rl_canvas.Canvas",
    x: float,
    y: float,
    w: float,
    h: float,
    product: dict,
    config: LabelConfig,
) -> None:
    """Dibuja etiqueta estilo supermercado: nombre, precio grande, pre-tax, barcode."""
    from reportlab.lib.units import mm
    from reportlab.graphics.barcode import code128
    from reportlab.lib import colors
    from reportlab.pdfbase.pdfmetrics import stringWidth

    size = config.size
    pad = 1.5 * mm
    ix = x + pad          # inner left
    iw = w - 2 * pad      # inner width

    # ── Borde exterior ────────────────────────────────────────────────
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, fill=0)

    # ── Tamaños de fuente ─────────────────────────────────────────────
    name_fs  = {"small": 6.5, "medium": 7.5, "large": 9.5 }[size]
    label_fs = {"small": 5.5, "medium": 6.0, "large": 7.5 }[size]
    price_fs = {"small": 14,  "medium": 21,  "large": 30  }[size]
    sub_fs   = {"small": 5.0, "medium": 5.5, "large": 6.5 }[size]

    # ── Proporciones de secciones (fracciones del inner height) ───────
    inner_h = h - 2 * pad
    show_info = size != "small" and config.show_pretax_price

    if size == "small":
        s_bc, s_price, s_info, s_name = 0.38, 0.35, 0.00, 0.27
    elif size == "medium":
        s_bc, s_price, s_info, s_name = 0.32, 0.27, 0.20, 0.21
    else:
        s_bc, s_price, s_info, s_name = 0.30, 0.27, 0.17, 0.26

    if not show_info:
        half = s_info / 2
        s_name += half
        s_price += half
        s_info = 0.0

    h_bc    = inner_h * s_bc
    h_price = inner_h * s_price
    h_info  = inner_h * s_info
    h_name  = inner_h * s_name

    # Coordenadas Y por sección (bottom-up)
    y_bc_bot    = y + pad
    y_bc_top    = y_bc_bot + h_bc
    y_info_bot  = y_bc_top
    y_info_top  = y_info_bot + h_info
    y_price_bot = y_info_top
    y_price_top = y_price_bot + h_price
    y_name_bot  = y_price_top

    # ── Separadores horizontales ──────────────────────────────────────
    c.setStrokeColor(colors.HexColor("#333333"))
    c.setLineWidth(0.4)
    c.line(x, y_bc_top, x + w, y_bc_top)
    if show_info and h_info > 0:
        c.line(x, y_info_top, x + w, y_info_top)
    c.line(x, y_price_top, x + w, y_price_top)

    # ── Nombre (sección superior) ─────────────────────────────────────
    name = (product.get("description") or "").upper()
    c.setFont("Helvetica-Bold", name_fs)
    name_lines = _wrap_text(name, "Helvetica-Bold", name_fs, iw)

    max_name_lines = max(1, int(h_name / (name_fs * 1.25)))
    if len(name_lines) > max_name_lines:
        name_lines = name_lines[:max_name_lines]
        last = name_lines[-1]
        while last and stringWidth(last + "…", "Helvetica-Bold", name_fs) > iw:
            last = last[:-1]
        name_lines[-1] = last + "…"

    c.setFillColor(colors.black)
    name_lh = name_fs * 1.25
    total_name_h = len(name_lines) * name_lh
    name_start_y = y_name_bot + (h_name + total_name_h) / 2 - name_fs * 0.3
    for i, line in enumerate(name_lines):
        c.drawString(ix, name_start_y - i * name_lh, line)

    # ── Precio (sección central) ──────────────────────────────────────
    price = float(product.get("sale_price", 0))
    currency = config.currency_symbol.strip()
    unit = (product.get("unit") or "Unidad").lower()
    is_weight = any(k in unit for k in ("kg", "kilo", "k.", "gramo", "gr", "libra", "lb"))
    unit_lbl = "KILO" if is_weight else "UNIDAD"

    price_rounded = round(price, 2)
    if price_rounded == int(price_rounded):
        price_display = _fmt_thousands(price_rounded, decimals=0)
    else:
        price_display = _fmt_thousands(price_rounded, decimals=2)
    price_big = f"$ {price_display}"

    # Ajustar fuente si el número no cabe junto a "PRECIO X UNIDAD"
    label_text_w = max(
        stringWidth("PRECIO X", "Helvetica-Bold", label_fs),
        stringWidth(unit_lbl,   "Helvetica-Bold", label_fs),
    )
    max_price_w = iw - label_text_w - 2 * mm
    _price_fs = price_fs
    while _price_fs > 8 and stringWidth(price_big, "Helvetica-Bold", _price_fs) > max_price_w:
        _price_fs -= 1

    price_cy = y_price_bot + h_price / 2
    lh_lbl   = label_fs * 1.3
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", label_fs)
    c.drawString(ix, price_cy + lh_lbl * 0.45, "PRECIO X")
    c.drawString(ix, price_cy - lh_lbl * 0.85, unit_lbl)

    c.setFont("Helvetica-Bold", _price_fs)
    c.drawRightString(x + w - pad, price_cy - _price_fs * 0.3, price_big)

    # ── Info / pre-impuestos (medium + large) ─────────────────────────
    if show_info and h_info > 0:
        tax_rate_pct = float(product.get("tax_rate", 0) or 0)
        tax_included = bool(product.get("tax_included", True))
        per_lbl = "Kg." if is_weight else "Und."
        price_sub = f"Precio x 1 {per_lbl}   $ {_fmt_thousands(price_rounded)}"

        c.setFillColor(colors.HexColor("#374151"))
        info_lh = sub_fs * 1.35

        if tax_rate_pct > 0 and tax_included:
            pretax = price_rounded / (1 + tax_rate_pct / 100)
            pretax_str = f"$ {_fmt_thousands(pretax)}"
            tax_line = f"PRECIO SIN IMPUESTOS: {pretax_str}"
            c.setFont("Helvetica", sub_fs)
            c.drawString(ix, y_info_top - info_lh, price_sub)
            c.setFont("Helvetica-Bold", sub_fs)
            if stringWidth(tax_line, "Helvetica-Bold", sub_fs) > iw:
                tax_line = f"SIN IMPUESTOS: {pretax_str}"
            c.drawString(ix, y_info_top - info_lh * 2, tax_line)
        else:
            c.setFont("Helvetica", sub_fs)
            line_y = y_info_bot + h_info / 2 - sub_fs * 0.3
            c.drawString(ix, line_y, price_sub)

        c.setFillColor(colors.black)

    # ── Código de barras (sección inferior) ───────────────────────────
    barcode_val = product.get("barcode") or ""
    if barcode_val:
        bc_bar_h = h_bc * 0.70
        try:
            bc = code128.Code128(
                barcode_val,
                barHeight=bc_bar_h,
                barWidth=0.6,
                humanReadable=True,
                fontSize=6,
                fontName="Helvetica",
            )
            if bc.width > iw:
                ratio = iw * 0.90 / bc.width
                bc = code128.Code128(
                    barcode_val,
                    barHeight=bc_bar_h,
                    barWidth=max(0.22, 0.6 * ratio),
                    humanReadable=True,
                    fontSize=6,
                    fontName="Helvetica",
                )
            bc.drawOn(c, x + (w - bc.width) / 2, y_bc_bot + pad * 0.3)
        except Exception:
            c.setFont("Helvetica", 6)
            c.drawCentredString(x + w / 2, y_bc_bot + h_bc / 2, barcode_val)
