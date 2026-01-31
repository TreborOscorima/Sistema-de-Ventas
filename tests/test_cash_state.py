from decimal import Decimal
from unittest.mock import Mock

import pytest
import reflex as rx

from app.enums import SaleStatus
from app.models import CashboxLog, Product, Sale, SaleItem, StockMovement
from app.states.cash_state import CashState


class ExecResult:
    def __init__(self, all_items=None, first_item=None) -> None:
        self._all_items = all_items if all_items is not None else []
        self._first_item = first_item

    def all(self):
        return self._all_items

    def first(self):
        return self._first_item


class FakeSession:
    def __init__(self, exec_results):
        self.exec_results = exec_results
        self.exec_calls = []
        self.added = []
        self.commit = Mock()

    def exec(self, statement):
        self.exec_calls.append(statement)
        return self.exec_results[len(self.exec_calls) - 1]

    def add(self, obj):
        self.added.append(obj)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_delete_sale_marks_logs_voided_and_restores_stock(monkeypatch):
    sale_item = SaleItem(
        sale_id=1,
        product_id=10,
        quantity=Decimal("2.0000"),
        unit_price=Decimal("5.00"),
        subtotal=Decimal("10.00"),
    )
    sale_db = Sale(id=1, status=SaleStatus.completed)
    sale_db.items = [sale_item]
    product = Product(
        id=10,
        barcode="P-10",
        description="Producto Test",
        unit="Unidad",
        stock=Decimal("5.0000"),
        sale_price=Decimal("5.00"),
    )
    log = CashboxLog(
        id=1,
        action="Venta",
        amount=Decimal("10.00"),
        sale_id=1,
        notes="Venta #1",
        is_voided=False,
    )
    fake_session = FakeSession(
        [
            ExecResult(first_item=sale_db),
            ExecResult(all_items=[log]),
            ExecResult(first_item=product),
        ]
    )
    monkeypatch.setattr(rx, "session", lambda: fake_session)
    monkeypatch.setattr(rx, "toast", lambda *args, **kwargs: None)

    state = CashState()
    state.current_user = {
        "id": 99,
        "username": "tester",
        "company_id": 1,
        "privileges": {"view_cashbox": True, "delete_sales": True},
    }
    state.selected_branch_id = "1"
    state.sale_to_delete = "1"
    state.sale_delete_reason = "Error"
    state._cashbox_update_trigger = 0
    state._cashbox_guard = lambda: None

    state.delete_sale()

    assert sale_db.status == SaleStatus.cancelled
    assert sale_db.delete_reason == "Error"
    assert log.is_voided is True
    assert "ANULADA: Error" in (log.notes or "")
    assert product.stock == Decimal("7.0000")
    assert any(isinstance(obj, StockMovement) for obj in fake_session.added)
    fake_session.commit.assert_called_once()
    assert state._cashbox_update_trigger == 1
