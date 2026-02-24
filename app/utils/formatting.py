"""
Utilidades de formateo para moneda y numeros.

Funciones puras extraidas de State para reutilizacion.
"""
from decimal import Decimal, ROUND_HALF_UP


def round_currency(value: float) -> float:
    """
    Redondea un valor a 2 decimales usando ROUND_HALF_UP.

    Parametros:
        value: Valor a redondear

    Retorna:
        Valor redondeado como float con 2 decimales
    """
    return float(
        Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def format_currency(value: float, symbol: str) -> str:
    """
    Formatea un valor como moneda con el simbolo indicado.

    Parametros:
        value: Valor numerico
        symbol: Simbolo de moneda (ej. "S/ ", "$ ")

    Retorna:
        Cadena formateada como "S/ 100.00"
    """
    return f"{symbol}{round_currency(value):.2f}"



