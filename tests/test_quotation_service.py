"""Tests del :mod:`app.services.quotation_service`.

Cobertura:
  * Idempotencia: re-llamar ``create_quotation`` con la misma key retorna el
    mismo Quotation, no crea uno nuevo.
  * ``mark_converted`` setea status=CONVERTED y converted_sale_id.
  * ``update_status`` cambia el status arbitrariamente.
  * ``generate_pdf`` produce bytes válidos (header PDF) sin crashear.

Los tests inyectan una sesión async fake — no tocan DB real.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest

from app.models.quotations import Quotation, QuotationStatus
from app.services.quotation_service import (
    CreateQuotationDTO,
    QuotationItemDTO,
    QuotationService,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


class _ScalarResult:
    """Imita el objeto retornado por ``await session.execute(...)``."""

    def __init__(self, scalar=None, all_items=None):
        self._scalar = scalar
        self._all_items = all_items or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return self._all_items


class _FakeAsyncSession:
    """Async session mínima compatible con quotation_service.

    Maneja ``execute`` (await) con cola de side_effect estilo AsyncMock,
    además de ``add``, ``flush``, ``commit``, ``rollback`` async-friendly.
    """

    def __init__(self):
        self.added: list = []
        self.add = Mock(side_effect=self._add)
        self.flush = AsyncMock(side_effect=self._flush)
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self._execute_queue: list = []
        self.execute_calls: list = []

    def queue_execute(self, *results: _ScalarResult) -> None:
        self._execute_queue.extend(results)

    async def execute(self, stmt):
        self.execute_calls.append(stmt)
        if self._execute_queue:
            return self._execute_queue.pop(0)
        return _ScalarResult()

    def _add(self, obj):
        self.added.append(obj)
        # Asignar id sintético al primer Quotation insertado
        if isinstance(obj, Quotation) and getattr(obj, "id", None) is None:
            obj.id = 42

    async def _flush(self):
        # Refrescar id de Quotation insertados, igual que rebote del DB.
        for obj in self.added:
            if isinstance(obj, Quotation) and getattr(obj, "id", None) is None:
                obj.id = 42


# ─── Idempotencia de create_quotation ────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_quotation_returns_existing_when_idempotency_key_matches():
    """Re-call con misma key NO debe crear un Quotation nuevo."""
    existing = Quotation(
        id=99,
        company_id=1,
        branch_id=1,
        status=QuotationStatus.DRAFT,
        idempotency_key="abc-123",
        total_amount=Decimal("250.00"),
    )
    session = _FakeAsyncSession()
    session.queue_execute(_ScalarResult(scalar=existing))

    dto = CreateQuotationDTO(
        client_id=None,
        user_id=1,
        company_id=1,
        branch_id=1,
        items=[
            QuotationItemDTO(
                product_id=1,
                product_variant_id=None,
                quantity=2.0,
                unit_price=125.0,
            )
        ],
        validity_days=15,
        idempotency_key="abc-123",
    )

    result = await QuotationService.create_quotation(dto, session=session)

    assert result is existing
    # No se agregó nada (la idempotencia corta antes de session.add).
    assert session.added == []


@pytest.mark.asyncio
async def test_create_quotation_persists_items_and_computes_total():
    """Sin idempotency match, crea Quotation + items y total final."""
    session = _FakeAsyncSession()
    # Lookup idempotency: no encuentra
    session.queue_execute(_ScalarResult(scalar=None))
    # Lookup product_id=1: producto fake
    product = SimpleNamespace(
        description="Café Premium 250g",
        barcode="7890",
        category="Bebidas",
    )
    session.queue_execute(_ScalarResult(scalar=product))

    dto = CreateQuotationDTO(
        client_id=None,
        user_id=1,
        company_id=1,
        branch_id=1,
        items=[
            QuotationItemDTO(
                product_id=1,
                product_variant_id=None,
                quantity=2.0,
                unit_price=100.0,
                discount_percentage=10.0,
            )
        ],
        validity_days=20,
        discount_percentage=5.0,
        idempotency_key="new-key",
    )

    result = await QuotationService.create_quotation(dto, session=session)

    assert isinstance(result, Quotation)
    assert result.id == 42
    assert result.status == QuotationStatus.DRAFT
    assert result.idempotency_key == "new-key"
    # Subtotal por línea: 2 * 100 * 0.9 = 180
    # Total con descuento global 5%: 180 * 0.95 = 171.00
    assert result.total_amount == Decimal("171.00")
    # Snapshots del producto se copiaron a QuotationItem
    qis = [obj for obj in session.added if obj is not result]
    assert len(qis) == 1
    qi = qis[0]
    assert qi.product_name_snapshot == "Café Premium 250g"
    assert qi.product_barcode_snapshot == "7890"
    assert qi.product_category_snapshot == "Bebidas"


# ─── mark_converted ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mark_converted_links_sale_id_and_sets_status():
    """Después de cobrar la venta el presupuesto queda CONVERTED + sale_id."""
    quotation = Quotation(
        id=10,
        company_id=1,
        branch_id=1,
        status=QuotationStatus.ACCEPTED,
    )
    session = _FakeAsyncSession()
    session.queue_execute(_ScalarResult(scalar=quotation))

    await QuotationService.mark_converted(
        quotation_id=10,
        sale_id=555,
        company_id=1,
        branch_id=1,
        session=session,
    )

    assert quotation.status == QuotationStatus.CONVERTED
    assert quotation.converted_sale_id == 555


@pytest.mark.asyncio
async def test_mark_converted_silently_noops_when_quotation_not_found():
    session = _FakeAsyncSession()
    session.queue_execute(_ScalarResult(scalar=None))

    # No debe levantar
    await QuotationService.mark_converted(
        quotation_id=999,
        sale_id=1,
        company_id=1,
        branch_id=1,
        session=session,
    )


# ─── update_status ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "new_status",
    [
        QuotationStatus.SENT,
        QuotationStatus.ACCEPTED,
        QuotationStatus.REJECTED,
        QuotationStatus.EXPIRED,
    ],
)
async def test_update_status_writes_arbitrary_status(new_status):
    quotation = Quotation(
        id=7, company_id=1, branch_id=1, status=QuotationStatus.DRAFT
    )
    session = _FakeAsyncSession()
    session.queue_execute(_ScalarResult(scalar=quotation))

    await QuotationService.update_status(
        quotation_id=7,
        new_status=new_status,
        company_id=1,
        branch_id=1,
        session=session,
    )

    assert quotation.status == new_status


# ─── generate_pdf ────────────────────────────────────────────────────────────


def test_generate_pdf_returns_valid_pdf_bytes():
    """El PDF mínimo debe empezar con el header %PDF-."""
    quotation = Quotation(
        id=33,
        company_id=1,
        branch_id=1,
        status=QuotationStatus.SENT,
        total_amount=Decimal("250.50"),
        discount_percentage=Decimal("0.00"),
        notes="Pago contra entrega",
        created_at=datetime(2026, 4, 24, 10, 0, 0),
        expires_at=datetime(2026, 5, 9, 10, 0, 0),
    )
    items = [
        {
            "product_name_snapshot": "Producto A",
            "quantity": 2.0,
            "unit_price": 50.0,
            "discount_percentage": 0.0,
            "subtotal": 100.0,
        },
        {
            "product_name_snapshot": "Producto B",
            "quantity": 3.0,
            "unit_price": 50.17,
            "discount_percentage": 0.0,
            "subtotal": 150.50,
        },
    ]
    settings = {
        "company_name": "Empresa Demo SAC",
        "tax_id_label": "RUC",
        "ruc": "20123456789",
        "address": "Av. Demo 123, Lima",
        "phone": "999-555-444",
        "currency_symbol": "S/ ",
        "client_name": "Cliente Demo",
    }

    pdf = QuotationService.generate_pdf(quotation, items, settings)

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 500  # PDF razonablemente mínimo
