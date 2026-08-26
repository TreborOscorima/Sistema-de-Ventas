"""Tests para app/utils/stock.py — recalculate_stock_totals (FIX 22).

Usa mocks de sesión para verificar la lógica de las 3 fases de recalculación
sin necesidad de base de datos real.
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, call

from app.utils.stock import _extract_total, recalculate_stock_totals
from app.models import Product, ProductVariant


class FakeExecResult:
    """Simula el resultado de session.exec()."""

    def __init__(self, value):
        self._value = value

    def first(self):
        if isinstance(self._value, list):
            return self._value[0] if self._value else None
        return self._value

    def all(self):
        if isinstance(self._value, list):
            return self._value
        return [self._value] if self._value is not None else []


class TestExtractTotal:
    def test_none(self):
        assert _extract_total(None) == 0

    def test_tuple_with_value(self):
        assert _extract_total((Decimal("25.5"),)) == Decimal("25.5")

    def test_tuple_with_none(self):
        assert _extract_total((None,)) == 0

    def test_empty_tuple(self):
        assert _extract_total(()) == 0

    def test_scalar_decimal(self):
        assert _extract_total(Decimal("10")) == Decimal("10")

    def test_scalar_int(self):
        assert _extract_total(5) == 5

    def test_scalar_zero(self):
        assert _extract_total(0) == 0


class TestRecalculateStockTotals:
    def _make_session(self, exec_results):
        """Create a mock session that returns specified results sequentially."""
        session = MagicMock()
        results_iter = iter(exec_results)

        def fake_exec(stmt):
            return FakeExecResult(next(results_iter))

        session.exec.side_effect = fake_exec
        return session

    def test_empty_sets_no_queries(self):
        session = MagicMock()
        result = recalculate_stock_totals(
            session=session,
            company_id=1,
            branch_id=1,
        )
        assert result == set()
        session.exec.assert_not_called()

    def test_phase2_product_from_variants(self):
        """Phase 2: Product stock = SUM(variants.stock)."""
        product = Product(id=10, stock=Decimal("0"))

        session = self._make_session([
            [(10, Decimal("25"))],  # SUM GROUP BY query: list of (product_id, sum)
            [product],              # Product SELECT IN: list of products
        ])

        result = recalculate_stock_totals(
            session=session,
            company_id=1,
            branch_id=1,
            products_from_variants={10},
        )

        assert result == {10}
        assert product.stock == Decimal("25")
        session.add.assert_called_with(product)

    def test_phase3_product_from_batches(self):
        """Phase 3: Product stock = SUM(direct batches.stock)."""
        product = Product(id=20, stock=Decimal("0"))

        session = self._make_session([
            [(20, Decimal("50"))],  # SUM GROUP BY query
            [product],              # Product SELECT IN
        ])

        result = recalculate_stock_totals(
            session=session,
            company_id=1,
            branch_id=1,
            products_from_batches={20},
        )

        assert result == {20}
        assert product.stock == Decimal("50")

    def test_phase3_skips_products_already_in_phase2(self):
        """Phase 3 skips product_ids already handled by Phase 2."""
        product = Product(id=10, stock=Decimal("0"))

        session = self._make_session([
            [(10, Decimal("25"))],  # Phase 2: SUM variants GROUP BY
            [product],              # Phase 2: Product SELECT IN
        ])

        result = recalculate_stock_totals(
            session=session,
            company_id=1,
            branch_id=1,
            products_from_variants={10},
            products_from_batches={10},  # same ID — should be skipped
        )

        assert result == {10}
        # Only 2 exec calls (Phase 2), not 4 (Phase 2 + Phase 3)
        assert session.exec.call_count == 2

    def test_normalize_fn_applied(self):
        """normalize_fn is called when provided."""
        product = Product(id=10, stock=Decimal("0"))

        session = self._make_session([
            [(10, Decimal("10.7"))],  # SUM GROUP BY
            [product],
        ])

        def my_normalizer(stock, prod):
            return int(stock)  # Round down

        result = recalculate_stock_totals(
            session=session,
            company_id=1,
            branch_id=1,
            products_from_variants={10},
            normalize_fn=my_normalizer,
        )

        assert product.stock == 10

    def test_phase1_variant_populates_phase2(self):
        """Phase 1 adds variant.product_id to products_from_variants set."""
        variant = ProductVariant(id=5, product_id=10, stock=Decimal("0"))
        product = Product(id=10, stock=Decimal("0"))

        session = self._make_session([
            [(5, Decimal("15"))],   # Phase 1: SUM batches GROUP BY variant_id
            [variant],              # Phase 1: Variant SELECT IN
            [(10, Decimal("15"))],  # Phase 2: SUM variants GROUP BY product_id
            [product],              # Phase 2: Product SELECT IN
        ])

        result = recalculate_stock_totals(
            session=session,
            company_id=1,
            branch_id=1,
            variants_from_batches={5},
        )

        assert variant.stock == Decimal("15")
        assert product.stock == Decimal("15")
        assert result == {10}

    def test_product_not_found_no_crash(self):
        """If product SELECT returns empty list, no crash — just skip."""
        session = self._make_session([
            [(999, Decimal("10"))],  # SUM GROUP BY
            [],                      # Product not found
        ])

        result = recalculate_stock_totals(
            session=session,
            company_id=1,
            branch_id=1,
            products_from_variants={999},
        )

        assert result == set()


# ── Tests: build_stock_adjustment_movement (trazabilidad de ajuste manual) ──
import datetime as _dt

from app.utils.stock import build_stock_adjustment_movement, ADJUSTMENT_MOVEMENT_TYPE

_TS = _dt.datetime(2026, 7, 26, 12, 0, 0)


def _adj(old, new):
    return build_stock_adjustment_movement(
        product_id=33, old_stock=old, new_stock=new,
        user_id=1, company_id=1, branch_id=2, timestamp=_TS,
    )


def test_adjustment_positive_delta():
    mov = _adj(5, 8)
    assert mov is not None
    assert mov.type == ADJUSTMENT_MOVEMENT_TYPE
    assert mov.quantity == Decimal("3")
    assert mov.product_id == 33 and mov.company_id == 1 and mov.branch_id == 2
    assert mov.user_id == 1 and mov.timestamp == _TS


def test_adjustment_negative_delta():
    mov = _adj(8, 5)
    assert mov is not None
    assert mov.quantity == Decimal("-3")


def test_adjustment_no_change_returns_none():
    assert _adj(5, 5) is None
    assert _adj(Decimal("5.0000"), 5) is None


def test_adjustment_decimal_quantities():
    mov = _adj(Decimal("2.5"), Decimal("4.75"))
    assert mov is not None
    assert mov.quantity == Decimal("2.25")


def test_adjustment_handles_none_and_bad_values():
    # old None => tratado como 0; delta = 7
    mov = _adj(None, 7)
    assert mov is not None and mov.quantity == Decimal("7")
    # valor no parseable => tratado como 0 (sin excepción)
    mov2 = _adj("", 3)
    assert mov2 is not None and mov2.quantity == Decimal("3")


class TestQuantityDisplayResolution:
    """Resolución de cantidad para unidades decimales: 1 g / 1 ml (0.001)."""

    def test_constant_is_gram_ml_resolution(self):
        from app.constants import QUANTITY_DISPLAY_QUANT

        assert QUANTITY_DISPLAY_QUANT == Decimal("0.001")

    def _stub_state(self):
        # MixinState importa reflex; garantizamos el env mínimo antes.
        import os

        os.environ.setdefault(
            "AUTH_SECRET_KEY", "test-secret-key-quantity-normalize-32chars"
        )
        os.environ.setdefault("TENANT_STRICT", "0")
        from app.states.mixin_state import MixinState

        class _StubState:
            decimal_units = {"kg", "l", "ml", "g", "m", "cm"}
            _unit_allows_decimal = MixinState._unit_allows_decimal
            _normalize_quantity_value = MixinState._normalize_quantity_value

        return _StubState()

    def test_unidad_decimal_preserva_gramos_y_ml(self):
        s = self._stub_state()
        # 253 g de pollo y 375 ml de aceite vendidos por kg / L: exactos.
        assert s._normalize_quantity_value(0.253, "kg") == 0.253
        assert s._normalize_quantity_value(0.375, "l") == 0.375
        assert s._normalize_quantity_value(0.095, "ml") == 0.095

    def test_unidad_entera_redondea_a_entero(self):
        s = self._stub_state()
        result = s._normalize_quantity_value(2.6, "unidad")
        assert result == 3
        assert isinstance(result, int)
