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


# ── Regresión: re-parse de montos de display (crash de cierre de caja) ──
#
# El bug: la UI guarda montos como texto locale (ej. "3.042,45" en AR) en dicts
# de venta/log; recibos y Excel los re-parseaban con float()/Decimal(), que
# revientan (InvalidOperation/ValueError) en monedas con coma decimal o miles
# con punto (AR/UY/CO/BO/VE/PYG/CLP). Fix: MixinState._coerce_amount, inverso
# exacto de _fmt_amount usando el spec de la moneda activa. Estos tests ejercitan
# los MÉTODOS REALES del estado (sin Reflex/DB) para que CI cace la regresión —
# los tests puros del core no la cazaban.

def _state_stub(code: str, symbol: str = "$ "):
    """Instancia mínima con los helpers reales de MixinState enlazados."""
    from app.states.mixin_state import MixinState

    class _Stub:
        pass

    for name in (
        "_coerce_amount", "_fmt_amount", "_format_currency",
        "_round_currency", "_currency_symbol_clean",
    ):
        setattr(_Stub, name, getattr(MixinState, name))
    s = _Stub()
    s.selected_currency_code = code
    s.currency_symbol = symbol
    return s


@pytest.mark.parametrize("code", ["ARS", "PEN", "PYG", "CLP", "COP", "UYU", "BOB", "VES", "USD", "MXN"])
@pytest.mark.parametrize("value", [0.0, 5.5, 41.29, 1234.5, 3042.45, 17532.43, 1000000.0])
def test_coerce_amount_is_inverse_of_fmt_amount(code, value):
    """_coerce_amount(_fmt_amount(v)) recupera el valor con los decimales de la moneda.

    PYG/CLP tienen 0 decimales: _fmt_amount(17532.43,"CLP")="17.532" y el re-parse
    da 17532.0 — correcto (esas monedas no llevan centavos).
    """
    s = _state_stub(code)
    disp = s._fmt_amount(value)               # lo que la UI guarda como texto
    back = s._coerce_amount(disp)             # lo que re-parsea recibo/Excel
    expected = round_currency(value, currency_decimals(code))
    assert abs(back - expected) < 0.005, (code, value, disp, back, expected)


def test_coerce_amount_reformat_roundtrip_no_crash():
    """El camino exacto del cierre de caja: _format_currency(_coerce_amount(str))."""
    for code, sym in [("ARS", "$ "), ("PYG", "Gs "), ("PEN", "S/ "), ("CLP", "$ "), ("COP", "$ ")]:
        s = _state_stub(code, sym)
        for raw in [0.0, 41.29, 3042.45, 1000000.0]:
            disp = s._fmt_amount(raw)                        # sale["total"] de _get_day_sales
            reprinted = s._format_currency(s._coerce_amount(disp))
            # Debe coincidir con formatear el número original directamente.
            assert reprinted == s._format_currency(raw), (code, raw, disp, reprinted)


def test_coerce_amount_tolerates_symbol_and_edge_inputs():
    s = _state_stub("ARS", "$ ")
    assert s._coerce_amount("$ 3.042,45") == 3042.45   # con símbolo embebido
    assert s._coerce_amount("-1.234,50") == -1234.5    # negativo
    assert s._coerce_amount(3042.45) == 3042.45        # numérico pasa directo
    assert s._coerce_amount(None) == 0.0
    assert s._coerce_amount("") == 0.0
    assert s._coerce_amount("Gs 0") == 0.0
    # PYG: "3.042" (cero decimales, punto de miles) NO debe leerse como 3.042
    p = _state_stub("PYG", "Gs ")
    assert p._coerce_amount("3.042") == 3042.0
