"""
Calculation utilities for sales and inventory.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any

def calculate_subtotal(quantity: float, price: float) -> float:
    """
    Calculate subtotal for a line item.
    """
    return float(
        (Decimal(str(quantity)) * Decimal(str(price))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )

def calculate_total(items: List[Dict[str, Any]], key: str = "subtotal") -> float:
    """
    Calculate total from a list of items.
    """
    total = Decimal("0.00")
    for item in items:
        val = item.get(key, 0)
        total += Decimal(str(val))
    
    return float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def calculate_change(payment: float, total: float) -> float:
    """
    Calculate change to return to customer.
    """
    change = Decimal(str(payment)) - Decimal(str(total))
    return float(change.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if change > 0 else 0.0
