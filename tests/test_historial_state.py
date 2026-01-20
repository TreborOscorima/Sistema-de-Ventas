import datetime
from decimal import Decimal

import reflex as rx

from app.enums import PaymentMethodType, SaleStatus
from app.models import CashboxLog, Sale, SalePayment, User
from app.states.historial_state import HistorialState


class ExecResult:
    def __init__(self, all_items=None, first_item=None) -> None:
        self._all_items = all_items if all_items is not None else []
        self._first_item = first_item

    def all(self):
        return self._all_items

    def first(self):
        return self._first_item


class FakeSession:
    def __init__(self, logs):
        self.logs = logs
        self.last_statement = None

    def exec(self, statement):
        self.last_statement = statement
        return ExecResult(all_items=self.logs)


class SequencedSession:
    def __init__(self, results):
        self.results = results
        self.calls = 0
        self.statements = []

    def exec(self, statement):
        self.statements.append(statement)
        result = self.results[self.calls]
        self.calls += 1
        return ExecResult(all_items=result)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_sale_log_payment_info_uses_sale_id():
    state = HistorialState()
    log = CashboxLog(
        action="Venta",
        amount=Decimal("5.00"),
        payment_method="Efectivo",
        notes="Sin referencia",
        sale_id=10,
    )
    session = FakeSession([log])

    info = state._sale_log_payment_info(session, [10])

    assert info[10]["payment_method"] == "Efectivo"
    assert info[10]["payment_details"] == "Sin referencia"


def test_sale_log_payment_info_falls_back_to_notes():
    state = HistorialState()
    log = CashboxLog(
        action="Venta",
        amount=Decimal("5.00"),
        payment_method="Efectivo",
        notes="Venta #20",
        sale_id=None,
    )
    session = FakeSession([log])

    info = state._sale_log_payment_info(session, [20])

    assert 20 in info
    assert info[20]["payment_method"] == "Efectivo"


def test_sale_log_payment_info_filters_voided_in_query():
    state = HistorialState()
    session = FakeSession([])

    state._sale_log_payment_info(session, [1])

    assert "cashboxlog.is_voided" in str(session.last_statement)


def test_build_report_entries_filters_by_method_and_user(monkeypatch):
    state = HistorialState()
    state.report_filter_method = "cash"
    state.report_filter_source = "Todos"
    state.report_filter_user = "Alice"

    user_a = User(username="Alice", password_hash="x", role_id=1)
    user_b = User(username="Bob", password_hash="x", role_id=1)
    sale_a = Sale(id=1, status=SaleStatus.completed)
    sale_a.user = user_a
    sale_b = Sale(id=2, status=SaleStatus.completed)
    sale_b.user = user_b

    payment_cash = SalePayment(
        sale_id=1,
        amount=Decimal("10.00"),
        method_type=PaymentMethodType.cash,
        created_at=datetime.datetime(2024, 1, 1),
    )
    payment_cash.sale = sale_a
    payment_debit = SalePayment(
        sale_id=2,
        amount=Decimal("5.00"),
        method_type=PaymentMethodType.debit,
        created_at=datetime.datetime(2024, 1, 1),
    )
    payment_debit.sale = sale_b

    log_cash = CashboxLog(
        action="Cobranza",
        amount=Decimal("7.00"),
        payment_method="Efectivo",
        notes="Cobranza",
    )
    log_yape = CashboxLog(
        action="Cobranza",
        amount=Decimal("6.00"),
        payment_method="Yape",
        notes="Cobranza",
    )

    session = SequencedSession(
        [
            [payment_cash, payment_debit],
            [(log_cash, "Alice"), (log_yape, "Bob")],
        ]
    )
    monkeypatch.setattr(rx, "session", lambda: session)

    entries = state._build_report_entries()

    assert len(entries) == 2
    assert {entry["source"] for entry in entries} == {"Venta", "Cobranza"}
    assert all(entry["method_key"] == "cash" for entry in entries)
    assert all(entry["user"] == "Alice" for entry in entries)
    assert "cashboxlog.is_voided" in str(session.statements[1])


def test_build_report_entries_sales_only_skips_cancelled(monkeypatch):
    state = HistorialState()
    state.report_filter_method = "Todos"
    state.report_filter_source = "Ventas"
    state.report_filter_user = "Todos"

    user = User(username="User", password_hash="x", role_id=1)
    sale_ok = Sale(id=1, status=SaleStatus.completed)
    sale_ok.user = user
    sale_cancelled = Sale(id=2, status=SaleStatus.cancelled)
    sale_cancelled.user = user

    payment_ok = SalePayment(
        sale_id=1,
        amount=Decimal("10.00"),
        method_type=PaymentMethodType.cash,
        created_at=datetime.datetime(2024, 1, 1),
    )
    payment_ok.sale = sale_ok
    payment_cancelled = SalePayment(
        sale_id=2,
        amount=Decimal("8.00"),
        method_type=PaymentMethodType.cash,
        created_at=datetime.datetime(2024, 1, 1),
    )
    payment_cancelled.sale = sale_cancelled

    session = SequencedSession([[payment_ok, payment_cancelled]])
    monkeypatch.setattr(rx, "session", lambda: session)

    entries = state._build_report_entries()

    assert len(entries) == 1
    assert entries[0]["reference"] == "Venta #1"
    assert session.calls == 1
