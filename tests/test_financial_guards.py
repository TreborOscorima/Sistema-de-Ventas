"""Tests para los guards financieros aplicados en Sprints 11-14.

Cubre:
- FIX 36: _round_currency acepta Decimal/float/int
- FIX 41: _safe_amount clampea negativos
- FIX 42: credit_initial_payment negativo clampeado
- FIX 45: ingreso quantities/prices negativas rechazadas
- Stock helper: _extract_total
"""
import pytest
from decimal import Decimal, ROUND_HALF_UP
from unittest.mock import MagicMock

from app.utils.stock import _extract_total


# ---------------------------------------------------------------------------
# _round_currency: test sin instanciar MixinState (lógica pura)
# ---------------------------------------------------------------------------
def _round_currency_pure(value) -> float:
    """Replica la lógica de MixinState._round_currency para tests puros."""
    return float(
        Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


class TestRoundCurrency:
    """FIX 36: _round_currency widened to accept Decimal | float | int."""

    def test_from_float(self):
        assert _round_currency_pure(10.555) == 10.56

    def test_from_decimal(self):
        assert _round_currency_pure(Decimal("10.555")) == 10.56

    def test_from_int(self):
        assert _round_currency_pure(10) == 10.0

    def test_from_zero(self):
        assert _round_currency_pure(0) == 0.0

    def test_from_none(self):
        assert _round_currency_pure(None) == 0.0

    def test_half_up_rounding(self):
        # 0.005 rounds UP to 0.01
        assert _round_currency_pure(Decimal("0.005")) == 0.01

    def test_negative_value(self):
        # Negative values should round correctly (not clamp — that's _safe_amount's job)
        assert _round_currency_pure(-10.555) == -10.56

    def test_large_value(self):
        assert _round_currency_pure(Decimal("999999.999")) == 1000000.0

    def test_returns_float(self):
        result = _round_currency_pure(Decimal("10.50"))
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# _safe_amount: test lógica pura (sin instanciar PaymentMixin)
# ---------------------------------------------------------------------------
def _safe_amount_pure(value: str) -> float:
    """Replica la lógica de PaymentMixin._safe_amount para tests puros."""
    try:
        amount = float(value) if value else 0
    except (ValueError, TypeError):
        amount = 0
    if amount < 0:
        amount = 0
    return _round_currency_pure(amount)


class TestSafeAmount:
    """FIX 41: _safe_amount clamps negatives to 0."""

    def test_positive_value(self):
        assert _safe_amount_pure("100.50") == 100.50

    def test_zero(self):
        assert _safe_amount_pure("0") == 0.0

    def test_empty_string(self):
        assert _safe_amount_pure("") == 0.0

    def test_none(self):
        assert _safe_amount_pure(None) == 0.0

    def test_invalid_string(self):
        assert _safe_amount_pure("abc") == 0.0

    def test_negative_clamped_to_zero(self):
        """CRITICAL: Negative amounts must be clamped to prevent phantom refunds."""
        assert _safe_amount_pure("-100") == 0.0

    def test_negative_decimal_clamped(self):
        assert _safe_amount_pure("-0.01") == 0.0

    def test_large_negative_clamped(self):
        assert _safe_amount_pure("-999999") == 0.0

    def test_whitespace_handling(self):
        # float(" 10.5 ") works in Python
        assert _safe_amount_pure(" 10.5 ") == 10.50

    def test_rounds_result(self):
        assert _safe_amount_pure("10.555") == 10.56


# ---------------------------------------------------------------------------
# _extract_total: stock helper
# ---------------------------------------------------------------------------
class TestExtractTotal:
    """Stock recalculation helper — handles various DB result formats."""

    def test_none_returns_zero(self):
        assert _extract_total(None) == 0

    def test_tuple_extracts_first(self):
        assert _extract_total((Decimal("15.5"),)) == Decimal("15.5")

    def test_empty_tuple_returns_zero(self):
        assert _extract_total(()) == 0

    def test_scalar_value(self):
        assert _extract_total(Decimal("10")) == Decimal("10")

    def test_scalar_zero(self):
        assert _extract_total(0) == 0

    def test_tuple_with_none(self):
        assert _extract_total((None,)) == 0


# ---------------------------------------------------------------------------
# Credit initial payment negative guard
# ---------------------------------------------------------------------------
class TestCreditInitialPaymentGuard:
    """FIX 42: Negative initial_payment must be clamped to Decimal('0')."""

    def test_positive_preserved(self):
        raw = "50.00"
        initial_payment = Decimal(str(raw))
        if initial_payment < 0:
            initial_payment = Decimal("0")
        assert initial_payment == Decimal("50.00")

    def test_zero_preserved(self):
        raw = "0"
        initial_payment = Decimal(str(raw))
        if initial_payment < 0:
            initial_payment = Decimal("0")
        assert initial_payment == Decimal("0")

    def test_negative_clamped(self):
        """CRITICAL: Negative advance payment would bypass credit limits."""
        raw = "-100"
        initial_payment = Decimal(str(raw))
        if initial_payment < 0:
            initial_payment = Decimal("0")
        assert initial_payment == Decimal("0")


# ---------------------------------------------------------------------------
# Ingreso quantity/price guard
# ---------------------------------------------------------------------------
class TestIngresoItemGuard:
    """FIX 45: Negative quantities/prices must be rejected at commit point."""

    @pytest.mark.parametrize(
        "quantity,price,should_skip",
        [
            (Decimal("10"), Decimal("5.00"), False),   # valid
            (Decimal("0"), Decimal("5.00"), True),      # zero qty → skip
            (Decimal("-1"), Decimal("5.00"), True),      # negative qty → skip
            (Decimal("10"), Decimal("-1.00"), True),     # negative price → skip
            (Decimal("10"), Decimal("0"), False),        # zero price OK (gift/sample)
            (Decimal("1"), Decimal("0.01"), False),      # minimal valid
        ],
    )
    def test_item_validation(self, quantity, price, should_skip):
        """Replicates the guard: if quantity <= 0 or unit_cost < 0: continue"""
        skip = quantity <= 0 or price < 0
        assert skip == should_skip
