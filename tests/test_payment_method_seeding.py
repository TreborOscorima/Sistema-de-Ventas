from types import SimpleNamespace

import reflex as rx

from app.states.config_state import ConfigState
from app.utils.db_seeds import get_payment_methods_for_country, is_reserved_payment_method


class FakeExecResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items

    def first(self):
        return self._items[0] if self._items else None


class FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.info = {}
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


def test_pago_mixto_is_universal_across_countries():
    """Regresión: 'Pago Mixto' debe existir para TODO país.

    tuwayki_core no lo incluye en los universales; sin el wrapper de db_seeds,
    cambiar de país lo desactiva y los pagos mixtos quedan indisponibles.
    """
    for code in ("PE", "AR", "CO", "CL", "MX", "EC"):
        methods = get_payment_methods_for_country(code)
        codes = {(m.get("code") or "").lower() for m in methods}
        names = {m["name"] for m in methods}
        assert "mixed" in codes, f"Falta Pago Mixto (code=mixed) en {code}"
        assert "Pago Mixto" in names, f"Falta 'Pago Mixto' en {code}"


def test_all_supported_countries_have_full_config_and_methods():
    """Cada país soportado debe tener config completa + métodos (universal +
    billeteras propias + Pago Mixto)."""
    from tuwayki_core.countries import SUPPORTED_COUNTRIES, COUNTRY_PAYMENT_METHODS
    import zoneinfo

    expected = {"PE", "AR", "EC", "CO", "CL", "MX", "BO", "UY", "PY", "VE"}
    assert set(SUPPORTED_COUNTRIES) == expected
    # Todo país soportado tiene billeteras propias definidas.
    assert set(COUNTRY_PAYMENT_METHODS) == expected
    required = {
        "name", "currency", "currency_symbol", "timezone",
        "tax_id_label", "personal_id_label", "denominations",
    }
    for code, cfg in SUPPORTED_COUNTRIES.items():
        assert required <= set(cfg), f"{code} sin campos: {required - set(cfg)}"
        zoneinfo.ZoneInfo(cfg["timezone"])  # zona horaria válida
        assert cfg["denominations"], f"{code} sin denominaciones"
        names = {m["name"] for m in get_payment_methods_for_country(code)}
        assert "Pago Mixto" in names, f"{code} sin Pago Mixto"
        assert "Efectivo" in names, f"{code} sin Efectivo"


def test_new_countries_have_local_wallets():
    """Los países agregados deben traer sus billeteras locales sembradas."""
    expected_wallets = {
        "BO": {"Tigo Money", "QR Simple"},
        "UY": {"Mercado Pago", "Prex"},
        "PY": {"Tigo Money", "Billetera Personal"},
        "VE": {"Pago Móvil", "Biopago"},
    }
    for code, wallets in expected_wallets.items():
        names = {m["name"] for m in get_payment_methods_for_country(code)}
        assert wallets <= names, f"{code} faltan billeteras: {wallets - names}"


def test_tax_preset_countries_are_all_supported():
    """Consistencia: todo país con preset de impuestos debe ser País de
    Operación soportado (habría cazado la brecha original BO/UY/PY)."""
    from app.utils.tax_presets import COUNTRY_TAX_PRESETS
    from tuwayki_core.countries import SUPPORTED_COUNTRIES

    orphans = set(COUNTRY_TAX_PRESETS) - set(SUPPORTED_COUNTRIES)
    assert not orphans, f"Países con impuestos pero sin config de país: {orphans}"


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
            [],  # CompanySettings branch query (first)
            [],  # CompanySettings fallback query (first)
            [SimpleNamespace(code="PEN", name="Sol peruano (PEN)", symbol="S/")],
            [],
            [
                SimpleNamespace(
                    id=1,
                    method_id="cash",
                    code="cash",
                    name="Efectivo",
                    description="Billetes, Monedas",
                    kind="cash",
                    enabled=True,
                ),
                SimpleNamespace(
                    id=2,
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
