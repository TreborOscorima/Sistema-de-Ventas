"""Tests del :mod:`app.services.label_service`.

Cobertura:
  * ``_resolve_barcode``: genera código interno cuando el producto no tiene
    barcode válido (vacío, None o genérico).
  * ``get_products_for_labels``: retorna mapeo de productos consumible por
    el generador (filtros ``all``, ``no_barcode``, ``price_changed``).
  * ``generate_pdf``: produce bytes PDF válidos en los 3 tamaños y maneja
    correctamente el caso "sin productos".
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.label_service import (
    LabelConfig,
    LabelService,
    _resolve_barcode,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_product(
    *,
    pid: int = 1,
    barcode: str = "7891234567890",
    description: str = "Producto Test",
    category: str = "General",
    sale_price: str | Decimal = "100.00",
    purchase_price: str | Decimal = "60.00",
    unit: str = "Unidad",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=pid,
        barcode=barcode,
        description=description,
        category=category,
        sale_price=Decimal(str(sale_price)),
        purchase_price=Decimal(str(purchase_price)),
        unit=unit,
    )


class _ScalarsResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items


# ─── _resolve_barcode ────────────────────────────────────────────────────────


def test_resolve_barcode_returns_real_barcode_when_valid():
    p = _make_product(pid=7, barcode="7891234567890")
    assert _resolve_barcode(p) == "7891234567890"


@pytest.mark.parametrize("bad_value", ["", "0", "0000000000000", "N/A", "n/a"])
def test_resolve_barcode_generates_internal_code_for_invalid_values(bad_value):
    p = _make_product(pid=42, barcode=bad_value)
    assert _resolve_barcode(p) == "INT0000000042"


def test_resolve_barcode_handles_none_barcode():
    """Un producto sin barcode (None) debe generar código interno también."""
    p = _make_product(pid=5, barcode=None)
    assert _resolve_barcode(p) == "INT0000000005"


def test_resolve_barcode_strips_whitespace():
    p = _make_product(pid=8, barcode="   7891234567890   ")
    assert _resolve_barcode(p) == "7891234567890"


# ─── get_products_for_labels ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_products_for_labels_returns_dict_mapping():
    """Convierte filas del ORM a dicts con barcode resuelto y precios float."""
    rows = [
        _make_product(pid=1, barcode="123", description="A", sale_price="50.00"),
        _make_product(
            pid=2, barcode="", description="B", sale_price="20.00"
        ),  # genera INT0000000002
    ]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_ScalarsResult(rows))

    config = LabelConfig(size="medium", filter_type="all")
    result = await LabelService.get_products_for_labels(
        config, company_id=1, branch_id=1, session=session
    )

    assert len(result) == 2
    assert result[0]["barcode"] == "123"
    assert result[0]["description"] == "A"
    assert result[0]["sale_price"] == 50.00
    # Producto sin barcode: usa código interno generado.
    assert result[1]["barcode"] == "INT0000000002"


@pytest.mark.asyncio
async def test_get_products_returns_empty_when_no_match():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_ScalarsResult([]))

    config = LabelConfig(size="small", filter_type="no_barcode")
    result = await LabelService.get_products_for_labels(
        config, company_id=1, branch_id=1, session=session
    )

    assert result == []
    # Verificó que filter_type='no_barcode' NO crashea (ramita no_barcode del
    # builder usa or_(barcode None|""|genericos))
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_get_products_price_changed_filter_does_not_crash():
    """Smoke test del builder con filter_type='price_changed' + N días.

    Verifica que el path del filtro (que usa Product.sale_price_updated_at >=
    cutoff) construye el statement sin error, aunque la verificación
    semántica detallada se delega a tests de integración con DB real.
    """
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_ScalarsResult([]))

    config = LabelConfig(
        size="large",
        filter_type="price_changed",
        price_changed_days=14,
    )
    result = await LabelService.get_products_for_labels(
        config, company_id=1, branch_id=1, session=session
    )

    assert result == []


# ─── generate_pdf ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("size", ["small", "medium", "large"])
def test_generate_pdf_returns_valid_pdf_bytes_in_all_sizes(size):
    products = [
        {
            "id": 1,
            "barcode": "7891234567890",
            "description": "Producto Demo",
            "category": "Bebidas",
            "sale_price": 50.00,
            "purchase_price": 30.00,
            "unit": "Unidad",
        }
    ]
    config = LabelConfig(size=size, filter_type="all", copies=1)

    pdf = LabelService.generate_pdf(products, config)

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 500


def test_generate_pdf_handles_zero_products_gracefully():
    """Sin productos a etiquetar, retorna PDF de 1 página con mensaje."""
    config = LabelConfig(size="medium", filter_type="all")
    pdf = LabelService.generate_pdf([], config)

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")


def test_generate_pdf_expands_copies_correctly():
    """copies=N produce N etiquetas por producto en el grid.

    Verificación indirecta: con 3 copies y 1 producto, el PDF tiene tamaño
    similar a 3 productos con copies=1 (mismo número de barcodes dibujados).
    """
    products = [
        {
            "id": 1,
            "barcode": "1234567890123",
            "description": "Test",
            "category": "X",
            "sale_price": 10.00,
            "purchase_price": 5.00,
            "unit": "u",
        }
    ]
    config_1 = LabelConfig(size="medium", filter_type="all", copies=1)
    config_3 = LabelConfig(size="medium", filter_type="all", copies=3)

    pdf_1 = LabelService.generate_pdf(products, config_1)
    pdf_3 = LabelService.generate_pdf(products, config_3)

    assert len(pdf_3) > len(pdf_1)


def test_generate_pdf_includes_purchase_price_when_enabled_in_large_size():
    """Solo el tamaño 'large' con show_purchase_price renderiza el costo."""
    products = [
        {
            "id": 1,
            "barcode": "1234567890123",
            "description": "Test",
            "category": "X",
            "sale_price": 10.00,
            "purchase_price": 5.00,
            "unit": "u",
        }
    ]
    config = LabelConfig(
        size="large",
        filter_type="all",
        copies=1,
        show_purchase_price=True,
    )
    pdf = LabelService.generate_pdf(products, config)
    # No verificamos el contenido renderizado (binario PDF), solo que el path
    # no crashea cuando show_purchase_price=True. El render real se inspeccionaría
    # en pruebas visuales / integración manual.
    assert pdf.startswith(b"%PDF-")
