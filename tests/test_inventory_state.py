from unittest.mock import Mock

import reflex as rx

from app.models import Category
from app.states.inventory_state import InventoryState


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
    state.current_user = {"privileges": {"edit_inventario": True}}
    state.new_category_name = "Bebidas"
    fake_session = FakeSession(existing_category=None)
    monkeypatch.setattr(rx, "session", lambda: fake_session)
    monkeypatch.setattr(rx, "toast", lambda *args, **kwargs: "toast")
    load_called = {"value": False}
    state.load_categories = lambda: load_called.update(value=True)

    result = state.add_category()

    assert result == "toast"
    assert state.new_category_name == ""
    assert load_called["value"] is True
    assert any(
        isinstance(obj, Category) and obj.name == "Bebidas"
        for obj in fake_session.added
    )
    fake_session.commit.assert_called_once()


def test_remove_category_deletes_when_exists(monkeypatch):
    state = InventoryState()
    state.current_user = {"privileges": {"edit_inventario": True}}
    fake_category = Category(name="Bebidas")
    fake_session = FakeSession(existing_category=fake_category)
    monkeypatch.setattr(rx, "session", lambda: fake_session)
    monkeypatch.setattr(rx, "toast", lambda *args, **kwargs: "toast")
    load_called = {"value": False}
    state.load_categories = lambda: load_called.update(value=True)

    result = state.remove_category("Bebidas")

    assert result == "toast"
    assert fake_category in fake_session.deleted
    fake_session.commit.assert_called_once()
    assert load_called["value"] is True


def test_inventory_list_denies_without_permission():
    state = InventoryState()
    state.current_user = {"privileges": {"view_inventario": False}}

    assert state.inventory_list == []
