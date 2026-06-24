import datetime
from decimal import Decimal

import reflex as rx

from app.states.cash import CashState


class ExecResult:
    def __init__(self, all_items=None, first_item=None) -> None:
        self._all_items = all_items if all_items is not None else []
        self._first_item = first_item

    def all(self):
        return self._all_items

    def first(self):
        return self._first_item


class FakeSession:
    def __init__(self, results, refund_results=None):
        # results: lista de filas para la primera exec (ingresos por método)
        # refund_results: lista de filas para la segunda exec (devoluciones); por defecto vacío
        self._results_queue = [results, refund_results if refund_results is not None else []]
        self._call_index = 0
        self.info = {}
        self.statement = None

    def exec(self, statement):
        self.statement = statement
        items = self._results_queue[self._call_index] if self._call_index < len(self._results_queue) else []
        self._call_index += 1
        return ExecResult(all_items=items)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_build_cashbox_summary_formats_and_sorts(monkeypatch):
    state = CashState()
    state.current_user = {"company_id": 1, "privileges": {"view_cashbox": True}}
    state.selected_branch_id = "1"
    # Primera exec → ingresos por método (3 cols); segunda exec → devoluciones (2 cols, vacío)
    fake_session = FakeSession(
        [
            ("Efectivo", 2, Decimal("20.00")),
            (None, 1, Decimal("5.00")),
        ],
        refund_results=[],
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
    state.current_user = {"company_id": 1, "privileges": {"view_cashbox": True}}
    state.selected_branch_id = "1"
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
