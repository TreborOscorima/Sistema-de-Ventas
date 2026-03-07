from datetime import datetime

import reflex as rx

from app.states.dashboard_state import DashboardState
import app.states.mixin_state as mixin_state_module


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
    monkeypatch.setattr(
        state,
        "_display_now",
        lambda: datetime(2026, 3, 7, 14, 25, 25),
    )

    result = state.export_categories_excel()

    assert captured["limit"] is None
    assert "ventas_categoria_20260307_142525.xlsx" in result


def test_dashboard_display_now_uses_company_timezone(monkeypatch):
    state = DashboardState()
    captured = {}

    monkeypatch.setattr(
        state,
        "_company_settings_snapshot",
        lambda: {
            "country_code": "AR",
            "timezone": "America/Argentina/Buenos_Aires",
        },
    )

    def fake_country_now(country_code, timezone=None):
        captured["country_code"] = country_code
        captured["timezone"] = timezone
        return datetime(2026, 3, 7, 14, 25, 25)

    monkeypatch.setattr(mixin_state_module, "country_now", fake_country_now)

    result = state._display_now()

    assert result == datetime(2026, 3, 7, 14, 25, 25)
    assert captured == {
        "country_code": "AR",
        "timezone": "America/Argentina/Buenos_Aires",
    }
