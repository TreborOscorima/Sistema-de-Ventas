from datetime import datetime
from decimal import Decimal

import reflex as rx

from app.states.dashboard_state import DashboardState


class _ExecResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows, capture: dict):
        self._rows = rows
        self._capture = capture

    def exec(self, statement):
        self._capture["sql"] = str(statement)
        return _ExecResult(self._rows)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_query_sales_by_category_includes_services_snapshot(monkeypatch):
    state = DashboardState()
    capture = {}
    rows = [("Servicios", Decimal("120.00")), ("Bebidas", Decimal("80.00"))]

    monkeypatch.setattr(
        state,
        "_get_period_dates",
        lambda: (
            datetime(2026, 2, 1, 0, 0, 0),
            datetime(2026, 2, 9, 23, 59, 59),
            datetime(2026, 1, 1, 0, 0, 0),
            datetime(2026, 1, 31, 23, 59, 59),
        ),
    )
    monkeypatch.setattr(state, "_company_id", lambda: 1)
    monkeypatch.setattr(state, "_branch_id", lambda: 1)
    monkeypatch.setattr(rx, "session", lambda: _FakeSession(rows, capture))

    result = state._query_sales_by_category(limit=None)

    assert result[0]["category"] == "Servicios"
    assert result[0]["total"] == 120.0
    assert "LEFT OUTER JOIN" in capture["sql"].upper()
    assert "product.company_id" not in capture["sql"]
