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
        return self._value


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
            Decimal("25"),  # SUM query result
            product,        # Product SELECT result
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
            Decimal("50"),  # SUM query result
            product,        # Product SELECT result
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
            Decimal("25"),  # Phase 2: SUM variants
            product,        # Phase 2: Product SELECT
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
            Decimal("10.7"),  # SUM result
            product,
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
            Decimal("15"),  # Phase 1: SUM batches for variant
            variant,        # Phase 1: Variant SELECT
            Decimal("15"),  # Phase 2: SUM variants for product (auto-added)
            product,        # Phase 2: Product SELECT
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
        """If product SELECT returns None, no crash — just skip."""
        session = self._make_session([
            Decimal("10"),  # SUM result
            None,           # Product not found
        ])

        result = recalculate_stock_totals(
            session=session,
            company_id=1,
            branch_id=1,
            products_from_variants={999},
        )

        assert result == set()
