from types import SimpleNamespace

import pytest

from app.state import State


@pytest.mark.asyncio
async def test_runtime_refresh_loads_categories_when_state_was_not_hydrated(monkeypatch):
    load_calls = []
    state = SimpleNamespace(
        is_authenticated=True,
        _last_runtime_refresh_ts=0.0,
        _runtime_refresh_ttl=30.0,
        runtime_ctx_loaded=False,
        subscription_snapshot={"plan_type": "trial"},
        categories=["General"],
        _categories_loaded_once=False,
        units=["Unidad"],
        field_prices=["loaded"],
        available_currencies=["PEN"],
        payment_methods=["cash"],
        refresh_auth_runtime_cache=lambda: None,
        refresh_cashbox_status=lambda: None,
        check_overdue_alerts=lambda: None,
        load_categories=lambda: load_calls.append("load"),
    )

    await State._do_runtime_refresh(state)

    assert load_calls == ["load"]


@pytest.mark.asyncio
async def test_runtime_refresh_force_reloads_categories(monkeypatch):
    load_calls = []
    state = SimpleNamespace(
        is_authenticated=True,
        _last_runtime_refresh_ts=0.0,
        _runtime_refresh_ttl=30.0,
        runtime_ctx_loaded=False,
        subscription_snapshot={"plan_type": "trial"},
        categories=["General", "Bebidas"],
        _categories_loaded_once=True,
        units=["Unidad"],
        field_prices=["loaded"],
        available_currencies=["PEN"],
        payment_methods=["cash"],
        refresh_auth_runtime_cache=lambda: None,
        refresh_cashbox_status=lambda: None,
        check_overdue_alerts=lambda: None,
        load_categories=lambda: load_calls.append("load"),
    )

    await State._do_runtime_refresh(state, force=True)

    assert load_calls == ["load"]
