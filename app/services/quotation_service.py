"""Servicio de Presupuestos / Cotizaciones.

Responsabilidades:
  - Crear presupuestos con sus ítems y snapshots.
  - Convertir un presupuesto aceptado en una Sale (delegando a SaleService).
  - Generar el PDF del presupuesto (similar a receipt_service).

Patrones seguidos:
  - Mismo patrón de sesión opcional que sale_service (session=None → managed).
  - Tenant context via set_tenant_context + finally reset.
  - Snapshots de producto para auditoría histórica.
  - Idempotencia via idempotency_key.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import (
    Client,
    Product,
    ProductVariant,
    Quotation,
    QuotationItem,
    Sale,
)
from app.models.quotations import QuotationStatus
from app.utils.db import get_async_session
from app.utils.tenant import set_tenant_context
from app.utils.timezone import utc_now_naive

logger = logging.getLogger(__name__)


# ─── DTOs ────────────────────────────────────────────────────────────────────

@dataclass
class QuotationItemDTO:
    product_id: int | None
    product_variant_id: int | None
    quantity: float
    unit_price: float
    discount_percentage: float = 0.0


@dataclass
class CreateQuotationDTO:
    client_id: int | None
    user_id: int | None
    company_id: int
    branch_id: int
    items: list[QuotationItemDTO]
    validity_days: int = 15
    discount_percentage: float = 0.0
    notes: str | None = None
    idempotency_key: str | None = None


# ─── Servicio ────────────────────────────────────────────────────────────────

class QuotationService:

    # ── Crear presupuesto ────────────────────────────────────────────────

    @staticmethod
    async def create_quotation(
        dto: CreateQuotationDTO,
        session: AsyncSession | None = None,
    ) -> Quotation:
        set_tenant_context(dto.company_id, dto.branch_id)
        try:
            if session is None:
                async with get_async_session() as s:
                    result = await QuotationService._create_impl(s, dto)
                    await s.commit()
                    return result
            return await QuotationService._create_impl(session, dto)
        finally:
            set_tenant_context(None, None)

    @staticmethod
    async def _create_impl(session: AsyncSession, dto: CreateQuotationDTO) -> Quotation:
        # Idempotencia: si ya existe para esta empresa, devolver el existente
        if dto.idempotency_key:
            existing_stmt = (
                select(Quotation)
                .where(Quotation.company_id == dto.company_id)
                .where(Quotation.idempotency_key == dto.idempotency_key)
            )
            existing = (await session.execute(existing_stmt)).scalar_one_or_none()
            if existing:
                return existing

        now = utc_now_naive()
        expires = now + timedelta(days=dto.validity_days)

        quotation = Quotation(
            company_id=dto.company_id,
            branch_id=dto.branch_id,
            client_id=dto.client_id,
            user_id=dto.user_id,
            status=QuotationStatus.DRAFT,
            validity_days=dto.validity_days,
            expires_at=expires,
            discount_percentage=Decimal(str(dto.discount_percentage)),
            notes=dto.notes,
            idempotency_key=dto.idempotency_key,
            created_at=now,
        )
        session.add(quotation)
        await session.flush()  # obtener quotation.id

        total = Decimal("0.00")
        for item_dto in dto.items:
            product_name = ""
            product_barcode = ""
            product_category = ""

            # Resolver snapshots del producto
            if item_dto.product_id:
                product_stmt = select(Product).where(Product.id == item_dto.product_id)
                product = (await session.execute(product_stmt)).scalar_one_or_none()
                if product:
                    product_name = product.description or ""
                    product_barcode = product.barcode or ""
                    product_category = product.category or ""

            qty = Decimal(str(item_dto.quantity))
            price = Decimal(str(item_dto.unit_price))
            discount_pct = Decimal(str(item_dto.discount_percentage))
            discount_factor = (Decimal("100") - discount_pct) / Decimal("100")
            subtotal = (qty * price * discount_factor).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            qi = QuotationItem(
                company_id=dto.company_id,
                branch_id=dto.branch_id,
                quotation_id=quotation.id,
                product_id=item_dto.product_id,
                product_variant_id=item_dto.product_variant_id,
                quantity=qty,
                unit_price=price,
                discount_percentage=discount_pct,
                subtotal=subtotal,
                product_name_snapshot=product_name,
                product_barcode_snapshot=product_barcode,
                product_category_snapshot=product_category,
            )
            session.add(qi)
            total += subtotal

        # Aplicar descuento global al total
        global_discount_factor = (
            (Decimal("100") - Decimal(str(dto.discount_percentage))) / Decimal("100")
        )
        quotation.total_amount = (total * global_discount_factor).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        await session.flush()
        return quotation

    # ── Convertir a Venta ────────────────────────────────────────────────

    @staticmethod
    async def mark_converted(
        quotation_id: int,
        sale_id: int,
        company_id: int,
        branch_id: int,
        session: AsyncSession | None = None,
    ) -> None:
        """Marca el presupuesto como convertido, enlazando al Sale creado."""
        set_tenant_context(company_id, branch_id)
        try:
            if session is None:
                async with get_async_session() as s:
                    await QuotationService._mark_converted_impl(s, quotation_id, sale_id)
                    await s.commit()
            else:
                await QuotationService._mark_converted_impl(session, quotation_id, sale_id)
        finally:
            set_tenant_context(None, None)

    @staticmethod
    async def _mark_converted_impl(
        session: AsyncSession, quotation_id: int, sale_id: int
    ) -> None:
        stmt = select(Quotation).where(Quotation.id == quotation_id)
        quotation = (await session.execute(stmt)).scalar_one_or_none()
        if quotation:
            quotation.status = QuotationStatus.CONVERTED
            quotation.converted_sale_id = sale_id
            await session.flush()

    # ── Cambiar estado ───────────────────────────────────────────────────

    @staticmethod
    async def update_status(
        quotation_id: int,
        new_status: str,
        company_id: int,
        branch_id: int,
        session: AsyncSession | None = None,
    ) -> None:
        set_tenant_context(company_id, branch_id)
        try:
            if session is None:
                async with get_async_session() as s:
                    await QuotationService._update_status_impl(s, quotation_id, new_status)
                    await s.commit()
            else:
                await QuotationService._update_status_impl(session, quotation_id, new_status)
        finally:
            set_tenant_context(None, None)

    @staticmethod
    async def _update_status_impl(
        session: AsyncSession, quotation_id: int, new_status: str
    ) -> None:
        stmt = select(Quotation).where(Quotation.id == quotation_id)
        q = (await session.execute(stmt)).scalar_one_or_none()
        if q:
            q.status = new_status
            await session.flush()

    # ── Generar PDF ──────────────────────────────────────────────────────

    @staticmethod
    def generate_pdf(
        quotation: Quotation,
        items: list[dict[str, Any]],
        company_settings: dict[str, Any],
    ) -> bytes:
        """Genera el PDF del presupuesto usando reportlab.

        Retorna bytes del PDF listo para descargar.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib import colors
        except ImportError:
            logger.error("reportlab no está instalado.")
            raise

        buffer = io.BytesIO()
        page_w, page_h = A4
        margin = 20 * mm
        content_w = page_w - 2 * margin

        c = rl_canvas.Canvas(buffer, pagesize=A4)

        # ── Encabezado ─────────────────────────────────────────────────
        y = page_h - margin
        company_name = company_settings.get("company_name") or "Empresa"
        tax_id_label = company_settings.get("tax_id_label") or "RUC"
        ruc = company_settings.get("ruc") or ""
        address = company_settings.get("address") or ""
        phone = company_settings.get("phone") or ""
        currency_symbol = company_settings.get("currency_symbol") or "S/ "

        # Nombre empresa
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y, company_name)
        y -= 6 * mm

        c.setFont("Helvetica", 9)
        if ruc:
            c.drawString(margin, y, f"{tax_id_label}: {ruc}")
            y -= 5 * mm
        if address:
            c.drawString(margin, y, f"Dir: {address}")
            y -= 5 * mm
        if phone:
            c.drawString(margin, y, f"Tel: {phone}")
            y -= 5 * mm

        # Separador
        y -= 3 * mm
        c.setStrokeColor(colors.HexColor("#4F46E5"))
        c.setLineWidth(1.5)
        c.line(margin, y, page_w - margin, y)
        y -= 5 * mm

        # Título del documento
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(page_w / 2, y, "PRESUPUESTO / COTIZACIÓN")
        y -= 6 * mm

        # Número y fecha
        c.setFont("Helvetica", 9)
        q_id = f"#{quotation.id:05d}"
        created_str = quotation.created_at.strftime("%d/%m/%Y") if quotation.created_at else "-"
        expires_str = quotation.expires_at.strftime("%d/%m/%Y") if quotation.expires_at else "-"
        c.drawString(margin, y, f"Nro: {q_id}    Fecha: {created_str}    Válido hasta: {expires_str}")
        y -= 5 * mm

        # Cliente
        client_name = company_settings.get("client_name") or "Público en general"
        c.drawString(margin, y, f"Cliente: {client_name}")
        y -= 8 * mm

        # ── Tabla de ítems ──────────────────────────────────────────────
        c.setFont("Helvetica-Bold", 9)
        col_x = {
            "item": margin,
            "desc": margin + 12 * mm,
            "qty": margin + 85 * mm,
            "price": margin + 105 * mm,
            "disc": margin + 130 * mm,
            "subtotal": margin + 155 * mm,
        }

        # Header de tabla
        c.setFillColor(colors.HexColor("#4F46E5"))
        c.rect(margin, y - 5 * mm, content_w, 6 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.drawString(col_x["item"], y - 3.5 * mm, "#")
        c.drawString(col_x["desc"], y - 3.5 * mm, "Descripción")
        c.drawString(col_x["qty"], y - 3.5 * mm, "Cant.")
        c.drawString(col_x["price"], y - 3.5 * mm, "P. Unit.")
        c.drawString(col_x["disc"], y - 3.5 * mm, "Desc.%")
        c.drawString(col_x["subtotal"], y - 3.5 * mm, "Subtotal")
        y -= 6 * mm
        c.setFillColor(colors.black)

        c.setFont("Helvetica", 8)
        for i, item in enumerate(items, 1):
            if y < margin + 20 * mm:
                c.showPage()
                y = page_h - margin

            row_bg = colors.HexColor("#F8FAFC") if i % 2 == 0 else colors.white
            c.setFillColor(row_bg)
            c.rect(margin, y - 5 * mm, content_w, 5.5 * mm, fill=1, stroke=0)
            c.setFillColor(colors.black)

            desc = item.get("name") or item.get("product_name_snapshot") or "-"
            if len(desc) > 38:
                desc = desc[:35] + "..."

            qty = item.get("quantity", 0)
            price = item.get("unit_price", 0)
            disc = item.get("discount_percentage", 0)
            subtotal = item.get("subtotal", 0)

            c.drawString(col_x["item"], y - 3.5 * mm, str(i))
            c.drawString(col_x["desc"], y - 3.5 * mm, desc)
            c.drawRightString(col_x["qty"] + 15 * mm, y - 3.5 * mm, f"{float(qty):.2f}")
            c.drawRightString(col_x["price"] + 20 * mm, y - 3.5 * mm, f"{currency_symbol}{float(price):.2f}")
            c.drawRightString(col_x["disc"] + 20 * mm, y - 3.5 * mm, f"{float(disc):.1f}%")
            c.drawRightString(col_x["subtotal"] + 20 * mm, y - 3.5 * mm, f"{currency_symbol}{float(subtotal):.2f}")
            y -= 5.5 * mm

        # Línea divisoria
        y -= 2 * mm
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.setLineWidth(0.5)
        c.line(margin, y, page_w - margin, y)
        y -= 4 * mm

        # ── Totales ──────────────────────────────────────────────────
        disc_pct = float(quotation.discount_percentage or 0)
        total = float(quotation.total_amount or 0)

        c.setFont("Helvetica", 9)
        if disc_pct > 0:
            c.drawRightString(page_w - margin, y, f"Descuento global: {disc_pct:.1f}%")
            y -= 5 * mm

        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(page_w - margin, y, f"TOTAL: {currency_symbol}{total:.2f}")
        y -= 8 * mm

        # ── Notas ─────────────────────────────────────────────────────
        if quotation.notes:
            c.setFont("Helvetica-Oblique", 8)
            c.setFillColor(colors.HexColor("#64748B"))
            c.drawString(margin, y, f"Notas: {quotation.notes[:200]}")
            y -= 8 * mm

        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#94A3B8"))
        c.drawCentredString(
            page_w / 2,
            margin,
            f"Presupuesto válido hasta el {expires_str} — {company_name}",
        )

        c.save()
        buffer.seek(0)
        return buffer.read()
