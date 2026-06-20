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
from app.utils.formatting import fmt_input_num
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


@dataclass
class UpdateQuotationDTO:
    quotation_id: int
    client_id: int | None
    company_id: int
    branch_id: int
    items: list[QuotationItemDTO]
    validity_days: int = 15
    discount_percentage: float = 0.0
    notes: str | None = None


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

    # ── Actualizar presupuesto ───────────────────────────────────────────

    @staticmethod
    async def update_quotation(
        dto: UpdateQuotationDTO,
        session: AsyncSession | None = None,
    ) -> Quotation:
        set_tenant_context(dto.company_id, dto.branch_id)
        try:
            if session is None:
                async with get_async_session() as s:
                    result = await QuotationService._update_impl(s, dto)
                    await s.commit()
                    return result
            return await QuotationService._update_impl(session, dto)
        finally:
            set_tenant_context(None, None)

    @staticmethod
    async def _update_impl(session: AsyncSession, dto: UpdateQuotationDTO) -> Quotation:
        from sqlalchemy import delete as sa_delete

        stmt = (
            select(Quotation)
            .where(Quotation.id == dto.quotation_id)
            .where(Quotation.company_id == dto.company_id)
            .where(Quotation.branch_id == dto.branch_id)
        )
        quotation = (await session.execute(stmt)).scalar_one_or_none()
        if not quotation:
            raise ValueError(f"Presupuesto #{dto.quotation_id} no encontrado.")
        if quotation.status not in (QuotationStatus.DRAFT, QuotationStatus.SENT, QuotationStatus.ACCEPTED):
            raise ValueError("Solo se pueden editar presupuestos en estado Borrador, Enviado o Aceptado.")

        was_accepted = quotation.status == QuotationStatus.ACCEPTED

        # Eliminar ítems anteriores
        await session.execute(
            sa_delete(QuotationItem).where(QuotationItem.quotation_id == dto.quotation_id)
        )

        # Actualizar cabecera
        quotation.client_id = dto.client_id
        quotation.validity_days = dto.validity_days
        quotation.discount_percentage = Decimal(str(dto.discount_percentage))
        quotation.notes = dto.notes
        now = utc_now_naive()
        quotation.expires_at = now + timedelta(days=dto.validity_days)
        if was_accepted:
            quotation.status = QuotationStatus.DRAFT

        # Recrear ítems
        total = Decimal("0.00")
        for item_dto in dto.items:
            product_name = ""
            product_barcode = ""
            product_category = ""
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
                quotation_id=dto.quotation_id,
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
                    await QuotationService._mark_converted_impl(s, quotation_id, sale_id, company_id, branch_id)
                    await s.commit()
            else:
                await QuotationService._mark_converted_impl(session, quotation_id, sale_id, company_id, branch_id)
        finally:
            set_tenant_context(None, None)

    @staticmethod
    async def _mark_converted_impl(
        session: AsyncSession, quotation_id: int, sale_id: int, company_id: int, branch_id: int
    ) -> None:
        stmt = (
            select(Quotation)
            .where(Quotation.id == quotation_id)
            .where(Quotation.company_id == company_id)
            .where(Quotation.branch_id == branch_id)
        )
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
                    await QuotationService._update_status_impl(s, quotation_id, new_status, company_id, branch_id)
                    await s.commit()
            else:
                await QuotationService._update_status_impl(session, quotation_id, new_status, company_id, branch_id)
        finally:
            set_tenant_context(None, None)

    @staticmethod
    async def _update_status_impl(
        session: AsyncSession, quotation_id: int, new_status: str, company_id: int, branch_id: int
    ) -> None:
        stmt = (
            select(Quotation)
            .where(Quotation.id == quotation_id)
            .where(Quotation.company_id == company_id)
            .where(Quotation.branch_id == branch_id)
        )
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
        """Genera el PDF del presupuesto usando reportlab."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib import colors
        except ImportError:
            logger.error("reportlab no está instalado.")
            raise

        # ── Paleta limpia (estilo Cierre de Caja) ─────────────────────
        NAVY     = colors.HexColor("#1e3a5f")   # header tabla
        GRAY_800 = colors.HexColor("#1f2937")   # texto principal
        GRAY_500 = colors.HexColor("#6B7280")   # texto secundario
        GRAY_200 = colors.HexColor("#E5E7EB")   # bordes
        GRAY_50  = colors.HexColor("#F9FAFB")   # fila alterna
        WHITE    = colors.white

        buffer = io.BytesIO()
        page_w, page_h = A4
        margin    = 18 * mm
        content_w = page_w - 2 * margin
        c = rl_canvas.Canvas(buffer, pagesize=A4)

        # ── Datos ─────────────────────────────────────────────────────
        company_name = company_settings.get("company_name") or "Empresa"
        tax_id_label = company_settings.get("tax_id_label") or "RUC"
        ruc          = company_settings.get("ruc") or ""
        address      = company_settings.get("address") or ""
        phone        = company_settings.get("phone") or ""
        cur          = (company_settings.get("currency_symbol") or "$").strip()
        client_name  = company_settings.get("client_name") or "Público en general"

        created_str = quotation.created_at.strftime("%d/%m/%Y") if quotation.created_at else "-"
        expires_str = quotation.expires_at.strftime("%d/%m/%Y") if quotation.expires_at else "-"
        q_id        = f"#{quotation.id:05d}"

        def fmt(amount) -> str:
            return f"{cur} {float(amount):,.2f}"

        y = page_h - margin

        # ── CABECERA: empresa ──────────────────────────────────────────
        c.setFillColor(GRAY_800)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y, company_name)
        y -= 5.5 * mm

        c.setFont("Helvetica", 8.5)
        c.setFillColor(GRAY_500)
        info_parts = []
        if ruc:
            info_parts.append(f"{tax_id_label}: {ruc}")
        if address:
            info_parts.append(address)
        if phone:
            info_parts.append(f"Tel: {phone}")
        if info_parts:
            c.drawString(margin, y, "  ·  ".join(info_parts))
            y -= 5 * mm

        y -= 4 * mm

        # ── TÍTULO DEL DOCUMENTO ──────────────────────────────────────
        c.setFillColor(GRAY_800)
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(page_w / 2, y, "PRESUPUESTO / COTIZACIÓN")
        y -= 5 * mm
        c.setFont("Helvetica", 9)
        c.setFillColor(GRAY_500)
        c.drawCentredString(page_w / 2, y,
            f"{q_id}   |   Fecha: {created_str}   |   Válido hasta: {expires_str}")
        y -= 4 * mm

        # ── LÍNEA SEPARADORA ──────────────────────────────────────────
        c.setStrokeColor(GRAY_200)
        c.setLineWidth(1)
        c.line(margin, y, page_w - margin, y)
        y -= 6 * mm

        # ── TABLA DE METADATOS ────────────────────────────────────────
        meta_row_h = 6 * mm
        meta_labels = ["Cliente", "Validez"]
        meta_values = [client_name, f"{quotation.validity_days} días"]
        col_lbl = margin
        col_val = margin + 30 * mm

        for lbl, val in zip(meta_labels, meta_values):
            # borde inferior suave
            c.setStrokeColor(GRAY_200)
            c.setLineWidth(0.4)
            c.line(margin, y - meta_row_h + 1 * mm, page_w - margin, y - meta_row_h + 1 * mm)
            c.setFont("Helvetica-Bold", 8.5)
            c.setFillColor(GRAY_800)
            c.drawString(col_lbl, y - 3.5 * mm, lbl)
            c.setFont("Helvetica", 8.5)
            c.setFillColor(GRAY_500)
            c.drawString(col_val, y - 3.5 * mm, val)
            y -= meta_row_h

        y -= 6 * mm

        # ── TABLA DE ÍTEMS ─────────────────────────────────────────────
        cx = {
            "num":    margin,
            "desc":   margin + 0.05 * content_w,
            "qty_r":  margin + 0.47 * content_w,
            "prc_r":  margin + 0.62 * content_w,
            "dsc_r":  margin + 0.75 * content_w,
            "sub_r":  margin + content_w,
        }
        row_h = 5.5 * mm
        hdr_h = 6.5 * mm

        # Header navy oscuro
        c.setFillColor(NAVY)
        c.rect(margin, y - hdr_h, content_w, hdr_h, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        hy = y - hdr_h + 2.2 * mm
        c.drawString(cx["num"] + 1 * mm, hy, "#")
        c.drawString(cx["desc"],          hy, "Descripción")
        c.drawRightString(cx["qty_r"],    hy, "Cant.")
        c.drawRightString(cx["prc_r"],    hy, "P. Unit.")
        c.drawRightString(cx["dsc_r"],    hy, "Desc.%")
        c.drawRightString(cx["sub_r"],    hy, "Subtotal")
        y -= hdr_h

        subtotal_bruto   = 0.0
        descuentos_items = 0.0

        for i, item in enumerate(items, 1):
            if y < margin + 35 * mm:
                c.showPage()
                y = page_h - margin

            row_bg = GRAY_50 if i % 2 == 0 else WHITE
            c.setFillColor(row_bg)
            c.rect(margin, y - row_h, content_w, row_h, fill=1, stroke=0)
            # borde inferior
            c.setStrokeColor(GRAY_200)
            c.setLineWidth(0.3)
            c.line(margin, y - row_h, page_w - margin, y - row_h)

            desc     = item.get("name") or item.get("product_name_snapshot") or "-"
            if len(desc) > 42:
                desc = desc[:39] + "..."
            qty      = float(item.get("quantity", 0))
            price    = float(item.get("unit_price", 0))
            disc_pct = float(item.get("discount_percentage", 0))
            sub      = float(item.get("subtotal", 0))
            subtotal_bruto   += qty * price
            descuentos_items += (qty * price - sub)

            ry = y - row_h + 1.5 * mm
            c.setFont("Helvetica", 8)
            c.setFillColor(GRAY_500)
            c.drawString(cx["num"] + 1 * mm, ry, str(i))
            c.setFillColor(GRAY_800)
            c.drawString(cx["desc"],          ry, desc)
            c.drawRightString(cx["qty_r"],    ry, f"{qty:.2f}")
            c.drawRightString(cx["prc_r"],    ry, fmt(price))
            c.drawRightString(cx["dsc_r"],    ry, f"{fmt_input_num(disc_pct)}%")
            c.setFont("Helvetica-Bold", 8)
            c.drawRightString(cx["sub_r"],    ry, fmt(sub))
            y -= row_h

        # ── TOTALES ───────────────────────────────────────────────────
        y -= 5 * mm
        tx_lbl = margin + content_w * 0.57
        tx_val = page_w - margin

        disc_global_pct = float(quotation.discount_percentage or 0)
        total_final     = float(quotation.total_amount or 0)

        def tot_line(label: str, value: str, bold: bool = False):
            nonlocal y
            c.setFont("Helvetica-Bold" if bold else "Helvetica", 8.5)
            c.setFillColor(GRAY_500 if not bold else GRAY_800)
            c.drawString(tx_lbl, y, label)
            c.setFillColor(GRAY_800)
            c.setFont("Helvetica-Bold" if bold else "Helvetica", 8.5)
            c.drawRightString(tx_val, y, value)
            y -= 5 * mm

        tot_line("Subtotal bruto:", fmt(subtotal_bruto))
        if descuentos_items > 0.005:
            tot_line("Descuentos por ítem:", f"- {fmt(descuentos_items)}")
        if disc_global_pct > 0:
            disc_global_amt = subtotal_bruto - descuentos_items - total_final
            tot_line(f"Descuento global ({fmt_input_num(disc_global_pct)}%):", f"- {fmt(disc_global_amt)}")

        # Línea y total final
        c.setStrokeColor(GRAY_800)
        c.setLineWidth(0.8)
        c.line(tx_lbl, y + 3 * mm, tx_val, y + 3 * mm)
        y -= 1 * mm
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(GRAY_800)
        c.drawString(tx_lbl, y, "TOTAL")
        c.drawRightString(tx_val, y, fmt(total_final))
        y -= 8 * mm

        # ── NOTAS ────────────────────────────────────────────────────
        if quotation.notes:
            c.setFont("Helvetica-Bold", 8.5)
            c.setFillColor(GRAY_800)
            c.drawString(margin, y, "Notas:")
            y -= 5 * mm
            c.setFont("Helvetica", 8.5)
            c.setFillColor(GRAY_500)
            c.drawString(margin, y, (quotation.notes or "")[:140])
            y -= 8 * mm

        # ── PIE ───────────────────────────────────────────────────────
        c.setStrokeColor(GRAY_200)
        c.setLineWidth(0.5)
        c.line(margin, margin + 6 * mm, page_w - margin, margin + 6 * mm)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(GRAY_500)
        c.drawString(margin, margin + 2 * mm,
                     f"Presupuesto válido hasta el {expires_str}  ·  {company_name}")
        c.drawRightString(page_w - margin, margin + 2 * mm, q_id)

        c.save()
        buffer.seek(0)
        return buffer.read()
