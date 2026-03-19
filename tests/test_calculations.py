"""Tests para app/utils/calculations.py — precisión financiera."""
import pytest
from decimal import Decimal
from app.utils.calculations import calculate_subtotal, calculate_total, _to_decimal


class TestToDecimal:
    def test_from_string(self):
        assert _to_decimal("10.50") == Decimal("10.50")

    def test_from_int(self):
        assert _to_decimal(10) == Decimal("10")

    def test_from_float(self):
        assert _to_decimal(10.5) == Decimal("10.5")

    def test_from_decimal(self):
        assert _to_decimal(Decimal("10.50")) == Decimal("10.50")

    def test_from_zero(self):
        assert _to_decimal(0) == Decimal("0")

    def test_from_none(self):
        assert _to_decimal(None) == Decimal("0")

    def test_from_empty_string(self):
        assert _to_decimal("") == Decimal("0")


class TestCalculateSubtotal:
    def test_basic(self):
        result = calculate_subtotal(Decimal("3"), Decimal("10.50"))
        assert result == Decimal("31.50")

    def test_rounds_half_up(self):
        # 3 * 10.555 = 31.665 -> rounds to 31.67 (ROUND_HALF_UP)
        result = calculate_subtotal(Decimal("3"), Decimal("10.555"))
        assert result == Decimal("31.67")

    def test_zero_quantity(self):
        result = calculate_subtotal(Decimal("0"), Decimal("10.00"))
        assert result == Decimal("0.00")

    def test_precision_two_decimals(self):
        result = calculate_subtotal(Decimal("1"), Decimal("9.999"))
        assert result == Decimal("10.00")


class TestCalculateTotal:
    def test_basic_sum(self):
        items = [
            {"subtotal": Decimal("10.50")},
            {"subtotal": Decimal("20.30")},
        ]
        assert calculate_total(items) == Decimal("30.80")

    def test_empty_list(self):
        assert calculate_total([]) == Decimal("0.00")

    def test_custom_key(self):
        items = [
            {"amount": Decimal("5.00")},
            {"amount": Decimal("3.50")},
        ]
        assert calculate_total(items, key="amount") == Decimal("8.50")

    def test_missing_key_defaults_to_zero(self):
        items = [{"other": Decimal("10.00")}]
        assert calculate_total(items, key="subtotal") == Decimal("0.00")

    def test_rounds_final_total(self):
        items = [
            {"subtotal": Decimal("10.333")},
            {"subtotal": Decimal("10.333")},
            {"subtotal": Decimal("10.334")},
        ]
        assert calculate_total(items) == Decimal("31.00")
