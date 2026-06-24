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
    def __init__(self, rows_sequence, capture: dict):
        # rows_sequence: lista de listas de filas para exec() secuenciales
        # Primera exec() → ventas por categoría; segunda exec() → devoluciones (vacío por default)
        if isinstance(rows_sequence[0], tuple) or not isinstance(rows_sequence[0], list):
            # Se pasó una sola lista de filas → primera exec la usa, segunda devuelve []
            self._queue = [rows_sequence, []]
        else:
            self._queue = rows_sequence
        self._call_index = 0
        self.info = {}
        self._capture = capture

    def exec(self, statement):
        self._capture["sql"] = str(statement)
        items = self._queue[self._call_index] if self._call_index < len(self._queue) else []
        self._call_index += 1
        return _ExecResult(items)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_query_sales_by_category_includes_services_snapshot(monkeypatch):
    state = DashboardState()
    capture = {}
    # Primera exec → filas de ventas; segunda exec → sin devoluciones
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
