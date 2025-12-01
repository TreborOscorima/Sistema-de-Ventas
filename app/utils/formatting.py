"""
Formatting utilities for currency and numbers.

Pure functions extracted from State for reusability.
"""
from decimal import Decimal, ROUND_HALF_UP


def round_currency(value: float) -> float:
    """
    Round a value to 2 decimal places using ROUND_HALF_UP.
    
    Args:
        value: The value to round
        
    Returns:
        The rounded value as a float with 2 decimal precision
    """
    return float(
        Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def format_currency(value: float, symbol: str) -> str:
    """
    Format a value as currency with the given symbol.
    
    Args:
        value: The numeric value
        symbol: The currency symbol (e.g., "S/ ", "$ ")
        
    Returns:
        Formatted string like "S/ 100.00"
    """
    return f"{symbol}{round_currency(value):.2f}"


def parse_float_safe(value: str, default: float = 0.0) -> float:
    """
    Safely parse a string to float, returning default on error.
    
    Args:
        value: The string to parse
        default: Value to return if parsing fails
        
    Returns:
        Parsed float or default value
    """
    try:
        return float(value) if value else default
    except (ValueError, TypeError):
        return default


def normalize_quantity_value(value: float, unit: str, decimal_units: set) -> float:
    """
    Normalize a quantity value based on the unit type.
    
    For decimal units (kg, litro, etc.), rounds to 2 decimal places.
    For non-decimal units, rounds to integer.
    
    Args:
        value: The quantity value
        unit: The unit of measurement
        decimal_units: Set of unit names in lowercase that allow decimal values
                      (e.g., {'kg', 'litro', 'gramo'})
        
    Returns:
        Normalized quantity value
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
