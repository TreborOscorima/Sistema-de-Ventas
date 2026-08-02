"""Tests del formateo de moneda locale-aware (decimales + separadores por país).

Regresión del hallazgo: el guaraní (PYG) y el peso chileno (CLP) son de CERO
decimales y usan punto de miles; el resto respeta la convención de su país.
"""
import pytest

from tuwayki_core.utils.formatting import (
    format_currency,
    format_number,
    round_currency,
    currency_decimals,
    currency_spec,
)


@pytest.mark.parametrize(
    "value, code, expected",
    [
        # Cero decimales, punto de miles
        (15000, "PYG", "15.000"),
        (15000, "CLP", "15.000"),
        (4.5, "PYG", "5"),          # redondeo a entero (hallazgo)
        (4.4, "PYG", "4"),
        (0, "PYG", "0"),
        (1234567, "PYG", "1.234.567"),
        # Punto de miles, coma decimal (2 dec.)
        (1234.5, "ARS", "1.234,50"),
        (1234567.89, "COP", "1.234.567,89"),
        (1000, "BOB", "1.000,00"),
        (50, "UYU", "50,00"),
        (99.9, "VES", "99,90"),
        # Coma de miles, punto decimal (2 dec.)
        (1234.567, "PEN", "1,234.57"),
        (1234.5, "MXN", "1,234.50"),
        (1000000, "USD", "1,000,000.00"),
    ],
)
def test_format_number_by_currency(value, code, expected):
    assert format_number(value, code) == expected


def test_format_currency_prepends_symbol():
    assert format_currency(15000, "₲", "PYG") == "₲15.000"
    assert format_currency(1234.5, "$", "ARS") == "$1.234,50"
    assert format_currency(1234.5, "S/", "PEN") == "S/1,234.50"


def test_currency_decimals():
    assert currency_decimals("PYG") == 0
    assert currency_decimals("CLP") == 0
    assert currency_decimals("ARS") == 2
    assert currency_decimals("PEN") == 2
    # Desconocida → default 2
    assert currency_decimals("XXX") == 2
    assert currency_decimals(None) == 2


def test_round_currency_respects_decimals():
    assert round_currency(4.5, 0) == 5.0
    assert round_currency(4.4, 0) == 4.0
    assert round_currency(1.005, 2) == 1.01
    # Sin arg → 2 decimales (retrocompatible)
    assert round_currency(1.005) == 1.01


def test_negative_and_zero():
    assert format_currency(-1234.5, "$", "ARS") == "$-1.234,50"
    assert format_currency(0, "₲", "PYG") == "₲0"


def test_backward_compat_without_code():
    # Sin code usa el spec por defecto (2 dec., coma de miles).
    assert format_currency(1234.5, "S/") == "S/1,234.50"
    assert currency_spec(None)["decimals"] == 2
