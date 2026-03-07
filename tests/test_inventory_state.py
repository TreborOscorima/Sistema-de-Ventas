import time
from unittest.mock import Mock

import reflex as rx
import pytest

from app.models import Category
from app.states.inventory_state import InventoryState
from app.state import State


class ExecResult:
    def __init__(self, all_items=None, first_item=None) -> None:
        self._all_items = all_items if all_items is not None else []
        self._first_item = first_item

    def all(self):
        return self._all_items

    def first(self):
        return self._first_item


class FakeSession:
    def __init__(self, existing_category=None):
        self.existing_category = existing_category
        self.added = []
        self.deleted = []
        self.commit = Mock()

    def exec(self, statement):
        return ExecResult(first_item=self.existing_category)

    def add(self, obj):
        self.added.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_add_category_requires_privilege(monkeypatch):
    state = InventoryState()
    state.current_user = {"privileges": {"edit_inventario": False}}
    sentinel = object()
    monkeypatch.setattr(rx, "toast", lambda *args, **kwargs: sentinel)

    result = state.add_category()

    assert result is sentinel


def test_remove_category_requires_privilege(monkeypatch):
    state = InventoryState()
    state.current_user = {"privileges": {"edit_inventario": False}}
    sentinel = object()
    monkeypatch.setattr(rx, "toast", lambda *args, **kwargs: sentinel)

    result = state.remove_category("Bebidas")

    assert result is sentinel


def test_add_category_creates_when_missing(monkeypatch):
    state = InventoryState()
    state.current_user = {"company_id": 1, "privileges": {"edit_inventario": True}}
    state.selected_branch_id = "1"
    state.new_category_name = "Bebidas"
    fake_session = FakeSession(existing_category=None)
    monkeypatch.setattr(rx, "session", lambda: fake_session)
    monkeypatch.setattr(rx, "toast", lambda *args, **kwargs: "toast")
    monkeypatch.setattr(state, "_emit_runtime_sync_event", lambda: "sync")
    load_called = {"value": False}
    state.load_categories = lambda: load_called.update(value=True)

    result = state.add_category()

    assert result == ["sync", "toast"]
    assert state.new_category_name == ""
    assert load_called["value"] is True
    assert any(
        isinstance(obj, Category) and obj.name == "Bebidas"
        for obj in fake_session.added
    )
    fake_session.commit.assert_called_once()


def test_remove_category_deletes_when_exists(monkeypatch):
    state = InventoryState()
    state.current_user = {"company_id": 1, "privileges": {"edit_inventario": True}}
    state.selected_branch_id = "1"
    fake_category = Category(name="Bebidas")
    fake_session = FakeSession(existing_category=fake_category)
    monkeypatch.setattr(rx, "session", lambda: fake_session)
    monkeypatch.setattr(rx, "toast", lambda *args, **kwargs: "toast")
    monkeypatch.setattr(state, "_emit_runtime_sync_event", lambda: "sync")
    load_called = {"value": False}
    state.load_categories = lambda: load_called.update(value=True)

    result = state.remove_category("Bebidas")

    assert result == ["sync", "toast"]
    assert fake_category in fake_session.deleted
    fake_session.commit.assert_called_once()
    assert load_called["value"] is True


def test_inventory_list_denies_without_permission():
    state = InventoryState()
    state.current_user = {"privileges": {"view_inventario": False}}

    assert state.inventory_list == []


def test_ensure_categories_loaded_uses_tenant_cache():
    state = InventoryState()
    state.current_user = {"company_id": 1, "privileges": {}}
    state.selected_branch_id = "1"
    calls = {"count": 0}

    def fake_load():
        calls["count"] += 1
        state.categories = ["General"]
        state._categories_loaded_company_id = 1
        state._categories_loaded_branch_id = 1

    state.load_categories = fake_load

    state.ensure_categories_loaded()
    state.ensure_categories_loaded()

    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_runtime_refresh_loads_categories_even_with_general_placeholder():
    class DummyState:
        is_authenticated = True

        def __init__(self):
            self.subscription_snapshot = {"plan_type": "pro"}
            self.categories = ["General"]
            self.units = ["unidad"]
            self.available_currencies = [{"code": "USD", "symbol": "$", "name": "Dólar"}]
            self.payment_methods = [{"name": "Efectivo"}]
            self.runtime_ctx_loaded = False
            self._last_runtime_refresh_ts = 0.0
            self._runtime_refresh_ttl = 30.0
            self.ensure_categories_loaded = Mock()
            self.refresh_auth_runtime_cache = Mock()
            self.refresh_cashbox_status = Mock()
            self.check_overdue_alerts = Mock()
            self._refresh_payment_config_with_ttl = Mock()

    state = DummyState()

    await State._do_runtime_refresh(state)

    state.ensure_categories_loaded.assert_called_once_with(force=False)


@pytest.mark.asyncio
async def test_runtime_refresh_rebuilds_branch_context_even_with_recent_snapshot():
    class DummyState:
        is_authenticated = True

        def __init__(self):
            self.subscription_snapshot = {"plan_type": "trial"}
            self.categories = ["General"]
            self.units = ["unidad"]
            self.available_currencies = [{"code": "USD", "symbol": "$", "name": "Dólar"}]
            self.payment_methods = [{"name": "Efectivo"}]
            self.available_branches = []
            self.active_branch_name = ""
            self.runtime_ctx_loaded = True
            self._last_runtime_refresh_ts = time.time()
            self._runtime_refresh_ttl = 30.0
            self.ensure_categories_loaded = Mock()
            self.refresh_branch_access_cache = Mock()
            self.refresh_auth_runtime_cache = Mock()
            self.refresh_cashbox_status = Mock()
            self.check_overdue_alerts = Mock()
            self._refresh_payment_config_with_ttl = Mock()

    state = DummyState()

    await State._do_runtime_refresh(state)

    state.refresh_auth_runtime_cache.assert_called_once()
