"""Resolución de precios con soporte de margen dinámico.

Cascada: variant.sale_price → product.sale_price → purchase × margen_global.
NULL en cualquier nivel = "sin precio explícito, usar nivel siguiente".
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.inventory import Product, ProductVariant


def resolve_effective_price(
    product: "Product",
    variant: Optional["ProductVariant"] = None,
    global_margin: float = 0.0,
) -> Decimal:
    """Devuelve el precio de venta efectivo.

    Nivel 1 — variante con precio propio (usuario lo personalizó/redondeó).
    Nivel 2 — precio explícito del producto padre.
    Nivel 3 — P. COMPRA × (1 + margen_global / 100)  (dinámico).
    """
    if variant is not None:
        vp = getattr(variant, "sale_price", None)
        if vp is not None:
            return Decimal(str(vp))

    if product.sale_price is not None:
        return Decimal(str(product.sale_price))

    pp = float(product.purchase_price or 0)
    if pp > 0 and global_margin > 0:
        return Decimal(str(round(pp * (1 + global_margin / 100), 2)))
    return Decimal("0.00")


def price_matches_margin(
    sale_price: float,
    purchase_price: float,
    margin: float,
    tolerance: float = 0.02,
) -> bool:
    """True si el precio de venta coincide con lo que daría el margen.

    Tolerancia de 2 centavos para cubrir diferencias de redondeo.
    """
    if purchase_price <= 0 or margin <= 0 or sale_price <= 0:
        return False
    computed = purchase_price * (1 + margin / 100)
    return abs(sale_price - computed) <= tolerance
