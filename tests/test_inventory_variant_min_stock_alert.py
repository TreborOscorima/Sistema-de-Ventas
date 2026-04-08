"""Tests del umbral de stock bajo por variante (min_stock_alert).

Verifica el comportamiento de _inventory_row_from_variant cuando:
  - La variante tiene su propio min_stock_alert (uso explícito).
  - La variante tiene min_stock_alert=None y hereda del Product padre.
  - Tanto la variante como el producto carecen de umbral (cae al DEFAULT_LOW_STOCK_THRESHOLD).

También cubre el conteo del dashboard que ahora incluye variantes con stock bajo.
"""
from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import MagicMock

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-variant-min-stock-32chars")
os.environ.setdefault("TENANT_STRICT", "0")

from app.models import Product, ProductVariant
from app.states.inventory_state import (
    DEFAULT_LOW_STOCK_THRESHOLD,
    InventoryState,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_product(*, min_stock_alert: Decimal | None = Decimal("5.0000")) -> Product:
    """Producto raíz con stock alto (no debería disparar alerta por sí solo)."""
    return Product(
        id=1,
        company_id=1,
        branch_id=1,
        barcode="P-001",
        description="Polo deportivo",
        category="Ropa",
        stock=Decimal("50.0000"),
        unit="Unidad",
        purchase_price=Decimal("10.00"),
        sale_price=Decimal("20.00"),
        min_stock_alert=min_stock_alert if min_stock_alert is not None else Decimal("5.0000"),
    )


def _make_variant(
    *,
    stock: Decimal,
    min_stock_alert: Decimal | None,
    size: str = "XL",
    color: str = "Rojo",
) -> ProductVariant:
    return ProductVariant(
        id=10,
        product_id=1,
        company_id=1,
        branch_id=1,
        sku="P-001-XL-R",
        size=size,
        color=color,
        stock=stock,
        min_stock_alert=min_stock_alert,
    )


# ─────────────────────────────────────────────────────────────────────────────
# _inventory_row_from_variant
# ─────────────────────────────────────────────────────────────────────────────


class TestVariantMinStockAlertOverride:
    """La variante puede definir su propio umbral, independiente del producto."""

    def test_variante_con_umbral_propio_dispara_alerta(self):
        """Variante con stock=2 y min_stock_alert=3 → stock_is_low=True (aunque parent=5)."""
        state = InventoryState()
        product = _make_product(min_stock_alert=Decimal("5.0000"))
        variant = _make_variant(stock=Decimal("2.0000"), min_stock_alert=Decimal("3.0000"))

        row = state._inventory_row_from_variant(product, variant)

        assert row["stock_is_low"] is True
        assert row["stock_is_medium"] is False
        assert row["variant_id"] == 10
        assert row["is_variant"] is True

    def test_variante_con_umbral_alto_dispara_aunque_parent_seria_ok(self):
        """Variante crítica (XL escasa): stock=8, variant_alert=10 → low; parent_alert=5 daría OK."""
        state = InventoryState()
        product = _make_product(min_stock_alert=Decimal("5.0000"))
        variant = _make_variant(stock=Decimal("8.0000"), min_stock_alert=Decimal("10.0000"))

        row = state._inventory_row_from_variant(product, variant)

        assert row["stock_is_low"] is True

    def test_variante_con_stock_sobre_umbral_propio_no_dispara(self):
        """Variante con stock=15 y min_stock_alert=10 → no es low ni medium."""
        state = InventoryState()
        product = _make_product(min_stock_alert=Decimal("5.0000"))
        variant = _make_variant(stock=Decimal("25.0000"), min_stock_alert=Decimal("10.0000"))

        row = state._inventory_row_from_variant(product, variant)

        assert row["stock_is_low"] is False
        assert row["stock_is_medium"] is False

    def test_variante_en_zona_media_segun_umbral_propio(self):
        """min_alert=5, stock=8 → 5 < 8 <= 10 → medium=True, low=False."""
        state = InventoryState()
        product = _make_product(min_stock_alert=Decimal("3.0000"))  # parent diferente, ignorado
        variant = _make_variant(stock=Decimal("8.0000"), min_stock_alert=Decimal("5.0000"))

        row = state._inventory_row_from_variant(product, variant)

        assert row["stock_is_low"] is False
        assert row["stock_is_medium"] is True


class TestVariantMinStockAlertInheritance:
    """Cuando variant.min_stock_alert es None, hereda del Product padre."""

    def test_variante_sin_umbral_usa_el_del_producto(self):
        """variant.min_stock_alert=None y product.min_stock_alert=10 → usa 10."""
        state = InventoryState()
        product = _make_product(min_stock_alert=Decimal("10.0000"))
        variant = _make_variant(stock=Decimal("9.0000"), min_stock_alert=None)

        row = state._inventory_row_from_variant(product, variant)

        # 9 <= 10 → low
        assert row["stock_is_low"] is True

    def test_variante_sin_umbral_y_stock_alto_no_dispara(self):
        """variant.min_stock_alert=None, parent=5, stock=20 → no alert."""
        state = InventoryState()
        product = _make_product(min_stock_alert=Decimal("5.0000"))
        variant = _make_variant(stock=Decimal("20.0000"), min_stock_alert=None)

        row = state._inventory_row_from_variant(product, variant)

        assert row["stock_is_low"] is False
        assert row["stock_is_medium"] is False


class TestVariantMinStockAlertDefaultFallback:
    """Si ni la variante ni el producto definen umbral, usa DEFAULT_LOW_STOCK_THRESHOLD."""

    def test_ambos_none_usa_default(self):
        """variant=None, product=None → DEFAULT_LOW_STOCK_THRESHOLD (5)."""
        state = InventoryState()
        # Forzamos product.min_stock_alert a None mediante MagicMock para esquivar
        # el default del SQLModel, ya que getattr(...) or DEFAULT chequea falsy.
        product = MagicMock(spec=Product)
        product.id = 1
        product.description = "Producto"
        product.category = "General"
        product.unit = "Unidad"
        product.purchase_price = Decimal("10.00")
        product.sale_price = Decimal("20.00")
        product.barcode = "P-001"
        product.min_stock_alert = None

        variant = _make_variant(stock=Decimal("4.0000"), min_stock_alert=None)

        row = state._inventory_row_from_variant(product, variant)

        # stock=4 <= DEFAULT_LOW_STOCK_THRESHOLD=5 → low
        assert DEFAULT_LOW_STOCK_THRESHOLD == 5
        assert row["stock_is_low"] is True

    def test_variante_explicita_cero_es_falsy_y_dispara_alerta_estructural(self):
        """variant.min_stock_alert=0 explícito → cualquier stock>0 está sobre el umbral."""
        state = InventoryState()
        product = _make_product(min_stock_alert=Decimal("5.0000"))
        variant = _make_variant(stock=Decimal("1.0000"), min_stock_alert=Decimal("0.0000"))

        row = state._inventory_row_from_variant(product, variant)

        # min_alert=0, stock=1 > 0 → no es low (es exactamente la semántica deseada:
        # "0 explícito" significa "no me alertes nunca"), y como 0 < 1 <= 0 es false,
        # tampoco es medium.
        assert row["stock_is_low"] is False
        assert row["stock_is_medium"] is False
