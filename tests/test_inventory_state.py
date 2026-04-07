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


# ═════════════════════════════════════════════════════════════
# BATCHES (lotes con vencimiento) — Farmacia / Supermercado
# ═════════════════════════════════════════════════════════════


def test_set_show_batches_initializes_row():
    state = InventoryState()
    state.batches = []

    state.set_show_batches(True)

    assert state.show_batches is True
    assert len(state.batches) == 1
    assert state.batches[0]["batch_number"] == ""
    assert state.batches[0]["expiration_date"] == ""


def test_set_show_batches_accepts_string_truthy():
    state = InventoryState()
    state.batches = [{"id": None, "batch_number": "L1", "expiration_date": "", "stock": 0}]

    state.set_show_batches("true")
    assert state.show_batches is True
    assert len(state.batches) == 1  # no se duplica si ya hay filas

    state.set_show_batches("0")
    assert state.show_batches is False


def test_add_and_remove_batch_row():
    state = InventoryState()
    state.batches = []
    state.add_batch_row()
    state.add_batch_row()
    assert len(state.batches) == 2

    state.remove_batch_row(0)
    assert len(state.batches) == 1

    # índice fuera de rango no rompe
    state.remove_batch_row(99)
    assert len(state.batches) == 1


def test_update_batch_field_text_and_numeric():
    state = InventoryState()
    state.batches = [{"id": None, "batch_number": "", "expiration_date": "", "stock": 0}]

    state.update_batch_field(0, "batch_number", "LOT-2026-001")
    assert state.batches[0]["batch_number"] == "LOT-2026-001"

    state.update_batch_field(0, "expiration_date", "2026-12-31")
    assert state.batches[0]["expiration_date"] == "2026-12-31"

    state.update_batch_field(0, "stock", "150.5")
    assert state.batches[0]["stock"] == 150.5

    # invalid numeric → no rompe
    state.update_batch_field(0, "stock", "abc")
    assert state.batches[0]["stock"] == 150.5

    # índice fuera de rango → no rompe
    state.update_batch_field(99, "batch_number", "X")
    assert len(state.batches) == 1


def test_batches_stock_total_sum():
    state = InventoryState()
    state.batches = [
        {"id": None, "batch_number": "L1", "expiration_date": "", "stock": 10},
        {"id": None, "batch_number": "L2", "expiration_date": "", "stock": 25.5},
        {"id": None, "batch_number": "L3", "expiration_date": "", "stock": "invalid"},
    ]
    # invalid stock se ignora
    assert state.batches_stock_total == 35.5


# ═════════════════════════════════════════════════════════════
# ATTRIBUTES (EAV dinámicos) — Ferretería / Farmacia
# ═════════════════════════════════════════════════════════════


def test_set_show_attributes_initializes_row():
    state = InventoryState()
    state.attributes = []

    state.set_show_attributes(True)

    assert state.show_attributes is True
    assert len(state.attributes) == 1
    assert state.attributes[0]["name"] == ""
    assert state.attributes[0]["value"] == ""


def test_set_show_attributes_no_double_init():
    state = InventoryState()
    state.attributes = [{"id": None, "name": "material", "value": "acero"}]

    state.set_show_attributes(True)
    assert len(state.attributes) == 1


def test_add_and_remove_attribute_row():
    state = InventoryState()
    state.attributes = []
    state.add_attribute_row()
    state.add_attribute_row()
    state.add_attribute_row()
    assert len(state.attributes) == 3

    state.remove_attribute_row(1)
    assert len(state.attributes) == 2

    state.remove_attribute_row(-5)
    assert len(state.attributes) == 2


def test_update_attribute_field():
    state = InventoryState()
    state.attributes = [{"id": None, "name": "", "value": ""}]

    state.update_attribute_field(0, "name", "principio_activo")
    assert state.attributes[0]["name"] == "principio_activo"

    state.update_attribute_field(0, "value", "ibuprofeno 400mg")
    assert state.attributes[0]["value"] == "ibuprofeno 400mg"


def test_batch_rows_includes_index():
    state = InventoryState()
    state.batches = [
        {"id": None, "batch_number": "A", "expiration_date": "", "stock": 0},
        {"id": None, "batch_number": "B", "expiration_date": "", "stock": 0},
    ]
    rows = state.batch_rows
    assert rows[0]["index"] == 0
    assert rows[1]["index"] == 1
    assert rows[0]["batch_number"] == "A"


def test_attribute_rows_includes_index():
    state = InventoryState()
    state.attributes = [
        {"id": None, "name": "calibre", "value": '1/2"'},
        {"id": None, "name": "rosca", "value": "fina"},
    ]
    rows = state.attribute_rows
    assert rows[0]["index"] == 0
    assert rows[1]["index"] == 1
    assert rows[1]["name"] == "rosca"
