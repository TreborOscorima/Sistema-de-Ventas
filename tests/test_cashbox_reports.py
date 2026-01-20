import datetime
from decimal import Decimal

import reflex as rx

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
    def __init__(self, results):
        self.results = results
        self.statement = None

    def exec(self, statement):
        self.statement = statement
        return ExecResult(all_items=self.results)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_build_cashbox_summary_formats_and_sorts(monkeypatch):
    state = CashState()
    fake_session = FakeSession(
        [
            ("Efectivo", 2, Decimal("20.00")),
            (None, 1, Decimal("5.00")),
        ]
    )
    monkeypatch.setattr(rx, "session", lambda: fake_session)
    monkeypatch.setattr(
        state,
        "_cashbox_time_range",
        lambda date: (
            datetime.datetime(2024, 1, 1),
            datetime.datetime(2024, 1, 2),
            None,
        ),
    )

    summary = state._build_cashbox_summary("2024-01-01")

    assert summary[0]["method"] == "Efectivo"
    assert summary[0]["total"] == 20.0
    assert summary[1]["method"] == "No especificado"
    assert summary[1]["count"] == 1


def test_build_cashbox_summary_filters_voided_and_dates(monkeypatch):
    state = CashState()
    fake_session = FakeSession([])
    monkeypatch.setattr(rx, "session", lambda: fake_session)
    monkeypatch.setattr(
        state,
        "_cashbox_time_range",
        lambda date: (
            datetime.datetime(2024, 1, 1),
            datetime.datetime(2024, 1, 2),
            None,
        ),
    )

    state._build_cashbox_summary("2024-01-01")

    statement = str(fake_session.statement)
    assert "cashboxlog.is_voided" in statement
    assert "cashboxlog.timestamp" in statement


def test_build_cashbox_close_breakdown_uses_totals():
    state = CashState()
    state._build_cashbox_summary = lambda date: [
        {"total": 10.0},
        {"total": 5.0},
    ]
    state._cashbox_opening_amount_value = lambda date: 5.0
    state._cashbox_expense_total = lambda date: 2.0

    breakdown = state._build_cashbox_close_breakdown("2024-01-01")

    assert breakdown["opening_amount"] == 5.0
    assert breakdown["income_total"] == 15.0
    assert breakdown["expense_total"] == 2.0
    assert breakdown["expected_total"] == 18.0
