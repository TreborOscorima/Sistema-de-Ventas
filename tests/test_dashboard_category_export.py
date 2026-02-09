import reflex as rx

from app.states.dashboard_state import DashboardState


def test_load_sales_by_category_uses_top_10_query(monkeypatch):
    state = DashboardState()
    captured = {"limit": None}

    def fake_query(limit=None):
        captured["limit"] = limit
        return [{"category": "Bebidas", "total": 100.0, "percentage": 100.0}]

    monkeypatch.setattr(state, "_query_sales_by_category", fake_query)

    state._load_sales_by_category()

    assert captured["limit"] == 10
    assert len(state.dash_sales_by_category) == 1


def test_export_categories_excel_queries_all_categories(monkeypatch):
    state = DashboardState()
    captured = {"limit": "not-called"}

    def fake_query(limit=None):
        captured["limit"] = limit
        return [
            {"category": "Cat A", "total": 100.0, "percentage": 50.0},
            {"category": "Cat B", "total": 100.0, "percentage": 50.0},
        ]

    monkeypatch.setattr(state, "_query_sales_by_category", fake_query)
    monkeypatch.setattr(rx, "call_script", lambda script: script)

    result = state.export_categories_excel()

    assert captured["limit"] is None
    assert "ventas_categoria_" in result
