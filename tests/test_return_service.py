"""Tests unitarios para return_service.process_return.

Cubre:
- Venta no encontrada
- Venta ya cancelada / ya devuelta
- Sin ítems seleccionados
- Ítem que no pertenece a la venta
- Cantidad que excede lo disponible
- Todas las cantidades en cero
- Clave de idempotencia duplicada → DuplicateReturnError
- Happy path: devolución parcial (producto sin variante ni lote)
- Happy path: devolución total → sale.status = "returned"
"""
from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-return-service-32chars-ok")
os.environ.setdefault("TENANT_STRICT", "0")

from app.enums import SaleStatus
from app.services.return_service import (
    DuplicateReturnError,
    ReturnItemRequest,
    ReturnResult,
    process_return,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class _Exec:
    """Responde `session.exec()` consumiendo una cola de respuestas."""

    def __init__(self, *responses):
        self._queue = list(responses)

    def __call__(self, _query):
        if self._queue:
            return self._queue.pop(0)
        result = MagicMock()
        result.first.return_value = None
        result.all.return_value = []
        return result


def _empty():
    """Resultado vacío."""
    r = MagicMock()
    r.first.return_value = None
    r.all.return_value = []
    return r


def _first(obj):
    """Resultado con un único objeto."""
    r = MagicMock()
    r.first.return_value = obj
    return r


def _all(*objs):
    r = MagicMock()
    r.all.return_value = list(objs)
    return r


def _make_sale_item(
    *,
    id_: int = 1,
    product_id: int = 10,
    product_name_snapshot: str = "Producto A",
    quantity: Decimal = Decimal("2"),
    unit_price: Decimal = Decimal("50.00"),
    product_variant_id=None,
    product_batch_id=None,
):
    si = MagicMock()
    si.id = id_
    si.product_id = product_id
    si.product_name_snapshot = product_name_snapshot
    si.quantity = quantity
    si.unit_price = unit_price
    si.product_variant_id = product_variant_id
    si.product_batch_id = product_batch_id
    si.kit_product_name = None
    return si


def _make_sale(
    *,
    id_: int = 100,
    company_id: int = 1,
    branch_id: int = 1,
    status: str = SaleStatus.completed,
    payment_condition: str = "contado",
    client_id=None,
    items=None,
):
    sale = MagicMock()
    sale.id = id_
    sale.company_id = company_id
    sale.branch_id = branch_id
    sale.status = status
    sale.payment_condition = payment_condition
    sale.client_id = client_id
    sale.items = items or []
    return sale


def _make_session(*exec_responses):
    session = MagicMock()
    session.exec = _Exec(*exec_responses)
    session.info = {}
    session.flush = MagicMock()
    session.rollback = MagicMock()
    session.add = MagicMock()
    return session


# ─────────────────────────────────────────────────────────────────────────────
# Tests de validación (rutas de error tempranas)
# ─────────────────────────────────────────────────────────────────────────────

def _call(session, items=None, **kwargs):
    """Invoca process_return con defaults razonables."""
    defaults = dict(
        sale_id=100,
        company_id=1,
        branch_id=1,
        user_id=5,
        reason="defecto",
        notes="",
        items=items or [],
    )
    defaults.update(kwargs)
    return process_return(session, **defaults)


@patch("app.services.return_service.recalculate_stock_totals")
@patch("app.services.return_service.set_tenant_context")
def test_sale_no_encontrada(mock_tc, mock_recalc):
    session = _make_session(
        _empty(),   # idempotency_key check (no key → skip), sale lookup → None
    )
    # Without idempotency_key, first exec is the sale .with_for_update()
    result = _call(session)
    assert not result.success
    assert "no encontrada" in result.error.lower()
    mock_recalc.assert_not_called()


@patch("app.services.return_service.recalculate_stock_totals")
@patch("app.services.return_service.set_tenant_context")
def test_venta_ya_cancelada(mock_tc, mock_recalc):
    sale = _make_sale(status=SaleStatus.cancelled)
    session = _make_session(_first(sale))
    result = _call(session)
    assert not result.success
    assert "anulada" in result.error.lower()


@patch("app.services.return_service.recalculate_stock_totals")
@patch("app.services.return_service.set_tenant_context")
def test_venta_ya_devuelta(mock_tc, mock_recalc):
    sale = _make_sale(status=SaleStatus.returned)
    session = _make_session(_first(sale))
    result = _call(session)
    assert not result.success
    assert "devuelta" in result.error.lower()


@patch("app.services.return_service.recalculate_stock_totals")
@patch("app.services.return_service.set_tenant_context")
def test_sin_items(mock_tc, mock_recalc):
    si = _make_sale_item()
    sale = _make_sale(items=[si])
    session = _make_session(_first(sale), _all())  # sale + existing_returns
    result = _call(session, items=[])
    assert not result.success
    assert "ítems" in result.error.lower() or "item" in result.error.lower()


@patch("app.services.return_service.recalculate_stock_totals")
@patch("app.services.return_service.set_tenant_context")
def test_item_no_pertenece_a_venta(mock_tc, mock_recalc):
    si = _make_sale_item(id_=1)
    sale = _make_sale(items=[si])
    session = _make_session(_first(sale), _all())  # sale + existing_returns
    req = ReturnItemRequest(sale_item_id=999, quantity=Decimal("1"))
    result = _call(session, items=[req])
    assert not result.success
    assert "999" in result.error


@patch("app.services.return_service.recalculate_stock_totals")
@patch("app.services.return_service.set_tenant_context")
def test_cantidad_excede_disponible(mock_tc, mock_recalc):
    si = _make_sale_item(id_=1, quantity=Decimal("2"))
    sale = _make_sale(items=[si])
    session = _make_session(_first(sale), _all())
    req = ReturnItemRequest(sale_item_id=1, quantity=Decimal("5"))
    result = _call(session, items=[req])
    assert not result.success
    assert "disponibles" in result.error.lower() or "devolver" in result.error.lower()


@patch("app.services.return_service.recalculate_stock_totals")
@patch("app.services.return_service.set_tenant_context")
def test_todas_cantidades_en_cero(mock_tc, mock_recalc):
    si = _make_sale_item(id_=1, quantity=Decimal("2"))
    sale = _make_sale(items=[si])
    session = _make_session(_first(sale), _all())
    req = ReturnItemRequest(sale_item_id=1, quantity=Decimal("0"))
    result = _call(session, items=[req])
    assert not result.success


@patch("app.services.return_service.recalculate_stock_totals")
@patch("app.services.return_service.set_tenant_context")
def test_idempotency_key_duplicada(mock_tc, mock_recalc):
    existing_return = MagicMock()
    existing_return.id = 42
    # First exec: idempotency_key lookup → returns existing return
    session = _make_session(_first(existing_return))
    req = ReturnItemRequest(sale_item_id=1, quantity=Decimal("1"))
    with pytest.raises(DuplicateReturnError) as exc_info:
        _call(session, items=[req], idempotency_key="abc123")
    assert exc_info.value.sale_return_id == 42


# ─────────────────────────────────────────────────────────────────────────────
# Happy path
# ─────────────────────────────────────────────────────────────────────────────

@patch("app.services.return_service.recalculate_stock_totals")
@patch("app.services.return_service.set_tenant_context")
def test_devolucion_parcial_producto_simple(mock_tc, mock_recalc):
    """Devolución de 1 unidad de un producto sin variante ni lote."""
    si1 = _make_sale_item(id_=1, quantity=Decimal("3"), unit_price=Decimal("100.00"))
    si2 = _make_sale_item(id_=2, quantity=Decimal("2"), unit_price=Decimal("50.00"))
    sale = _make_sale(items=[si1, si2])

    sale_return = MagicMock()
    sale_return.id = 77

    session = _make_session(
        _first(sale),   # sale WITH FOR UPDATE
        _all(),         # existing_returns
        # variant, product, batch batch-loads: all empty (no variant_ids, product_id=10)
        _all(),         # variants_map
        _all(),         # products_map (with_for_update)
        _all(),         # batches_map
    )
    # Simulate flush assigning ID to sale_return
    def _flush_side_effect():
        session._last_sale_return.id = 77
    session.flush.side_effect = lambda: None

    # Capture the SaleReturn added to session
    added_objects = []
    session.add.side_effect = lambda obj: added_objects.append(obj)

    req = ReturnItemRequest(sale_item_id=1, quantity=Decimal("1"))
    result = _call(session, items=[req])

    assert result.success
    assert result.refund_amount == Decimal("100.00")
    assert result.items_returned == 1
    # Sale should NOT be marked returned (only 1 of 3 returned for si1, si2 untouched)
    assert sale.status != SaleStatus.returned
    mock_recalc.assert_called_once()


@patch("app.services.return_service.recalculate_stock_totals")
@patch("app.services.return_service.set_tenant_context")
def test_devolucion_total_marca_returned(mock_tc, mock_recalc):
    """Devolución completa de todos los ítems → sale.status = returned."""
    si = _make_sale_item(id_=1, quantity=Decimal("2"), unit_price=Decimal("25.00"))
    sale = _make_sale(items=[si])

    session = _make_session(
        _first(sale),
        _all(),   # existing_returns empty
        _all(),   # products_map
    )
    session.flush.return_value = None

    req = ReturnItemRequest(sale_item_id=1, quantity=Decimal("2"))
    result = _call(session, items=[req])

    assert result.success
    assert result.refund_amount == Decimal("50.00")
    assert sale.status == SaleStatus.returned


@patch("app.services.return_service.recalculate_stock_totals")
@patch("app.services.return_service.set_tenant_context")
def test_devolucion_parcial_considera_previas(mock_tc, mock_recalc):
    """Si ya se devolvieron unidades previas, se descuentan del disponible."""
    si = _make_sale_item(id_=1, quantity=Decimal("3"), unit_price=Decimal("10.00"))
    sale = _make_sale(items=[si])

    # Simular que ya se devolvieron 2 unidades antes
    prev_return_item = MagicMock()
    prev_return_item.sale_item_id = 1
    prev_return_item.quantity = Decimal("2")

    session = _make_session(
        _first(sale),
        _all(prev_return_item),  # existing_returns → 2 ya devueltas
        _all(),                   # products_map
    )
    session.flush.return_value = None

    # Intentar devolver 2, pero solo queda 1 disponible
    req = ReturnItemRequest(sale_item_id=1, quantity=Decimal("2"))
    result = _call(session, items=[req])
    assert not result.success
    assert "disponibles" in result.error.lower() or "devolver" in result.error.lower()
