from types import SimpleNamespace

import reflex as rx

from app.states.config_state import ConfigState
from app.utils.db_seeds import get_payment_methods_for_country, is_reserved_payment_method


class FakeExecResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self._index = 0

    def exec(self, statement):
        response = self._responses[self._index]
        self._index += 1
        return FakeExecResult(response)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_country_payment_methods_exclude_reserved_credit_sale():
    methods = get_payment_methods_for_country("PE")
    ids = {method["method_id"] for method in methods}
    names = {method["name"] for method in methods}

    assert "credit_sale" not in ids
    assert "Crédito / Fiado" not in names


def test_reserved_credit_sale_name_detection():
    assert is_reserved_payment_method(name="Crédito / Fiado") is True
    assert is_reserved_payment_method(name="Venta al crédito") is True
    assert is_reserved_payment_method(name="Tarjeta de Crédito") is False


def test_add_payment_method_rejects_reserved_credit_sale_name(monkeypatch):
    state = ConfigState()
    state.current_user = {"privileges": {"manage_config": True}}
    state.new_payment_method_name = "Crédito / Fiado"
    state.new_payment_method_description = "Venta al crédito"
    state.new_payment_method_kind = "other"

    sentinel = object()
    monkeypatch.setattr(rx, "toast", lambda *args, **kwargs: sentinel)

    result = state.add_payment_method()

    assert result is sentinel


def test_load_config_data_filters_legacy_credit_sale_method(monkeypatch):
    state = ConfigState()
    monkeypatch.setattr(state, "_company_id", lambda: 1)
    monkeypatch.setattr(state, "_branch_id", lambda: 1)

    fake_session = FakeSession(
        [
            [SimpleNamespace(code="PEN", name="Sol peruano (PEN)", symbol="S/")],
            [],
            [
                SimpleNamespace(
                    method_id="cash",
                    code="cash",
                    name="Efectivo",
                    description="Billetes, Monedas",
                    kind="cash",
                    enabled=True,
                ),
                SimpleNamespace(
                    method_id="credit_sale",
                    code="credit_sale",
                    name="Crédito / Fiado",
                    description="Venta al crédito",
                    kind="credit",
                    enabled=True,
                ),
            ],
        ]
    )
    monkeypatch.setattr(rx, "session", lambda: fake_session)

    state.load_config_data()

    assert [method["id"] for method in state.payment_methods] == ["cash"]
