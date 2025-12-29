"""
Calculation utilities for sales and inventory.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any

MONEY_QUANT = Decimal("0.01")


def _to_decimal(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value or 0))


def calculate_subtotal(quantity: Decimal, price: Decimal) -> Decimal:
    """
    Calculate subtotal for a line item.
    """
    return (_to_decimal(quantity) * _to_decimal(price)).quantize(
        MONEY_QUANT, rounding=ROUND_HALF_UP
    )


def calculate_total(items: List[Dict[str, Any]], key: str = "subtotal") -> Decimal:
    """
    Calculate total from a list of items.
    """
    total = Decimal("0.00")
    for item in items:
        total += _to_decimal(item.get(key, 0))

    return total.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def calculate_change(payment: Decimal, total: Decimal) -> Decimal:
    """
    Calculate change to return to customer.
    """
    change = _to_decimal(payment) - _to_decimal(total)
    if change <= 0:
        return Decimal("0.00")
    return change.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
