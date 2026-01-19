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


def parse_float_safe(value: str, default: float = 0.0) -> float:
    """
    Convierte un string a float de forma segura y retorna default en error.
    
    Parametros:
        value: String a convertir
        default: Valor a retornar si falla el parseo
        
    Retorna:
        Float parseado o valor default
    """
    try:
        return float(value) if value else default
    except (ValueError, TypeError):
        return default


def normalize_quantity_value(value: float, unit: str, decimal_units: set) -> float:
    """
    Normaliza una cantidad segun el tipo de unidad.
    
    Para unidades decimales (kg, litro, etc.), redondea a 2 decimales.
    Para unidades no decimales, redondea a entero.
    
    Parametros:
        value: Valor de la cantidad
        unit: Unidad de medida
        decimal_units: Set de unidades en minuscula que permiten decimales
                      (ej. {'kg', 'litro', 'gramo'})
        
    Retorna:
        Valor de cantidad normalizado
    """
    unit_lower = (unit or "").lower()
    if unit_lower in decimal_units:
        return float(
            Decimal(str(value or 0)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        )
    return int(
        Decimal(str(value or 0)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )
