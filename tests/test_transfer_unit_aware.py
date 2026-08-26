"""El editor de cantidad de transferencias es unit-aware.

Cada fila del carrito expone `allows_decimal` según la unidad del producto, para
que el modal muestre un campo fraccionado (kg/L/ml, se tipea 0,253) o el stepper
entero con botones ±1 (unidad/caja). El backend de transferencias ya persiste
decimales (cubierto en test_stock_transfer.py); acá fijamos el flag que gobierna
la UI y que "agregar todo el stock" conserva la fracción.
"""
from __future__ import annotations

import os
from decimal import Decimal

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-transfer-unit-aware-32chars")
os.environ.setdefault("TENANT_STRICT", "0")

from app.states.mixin_state import MixinState
from app.states.inventory._transfer_mixin import TransferMixin


class _FakeProduct:
    def __init__(self, unit, stock=Decimal("5")):
        self.id = 1
        self.barcode = "COD-1"
        self.description = "Producto"
        self.stock = stock
        self.unit = unit


class _FakeVariant:
    def __init__(self, stock=Decimal("5")):
        self.id = 7
        self.sku = "SKU-1"
        self.size = "M"
        self.color = "Rojo"
        self.stock = stock

    def label(self, **kwargs):
        return "M / Rojo"


def _stub():
    class _Stub:
        decimal_units = {"kg", "g", "l", "ml", "m", "cm"}
        _unit_allows_decimal = MixinState._unit_allows_decimal
        _fmt_stock = TransferMixin._fmt_stock
        _full_stock_qty = TransferMixin._full_stock_qty
        _fmt_qty = staticmethod(TransferMixin._fmt_qty)
        _product_row = TransferMixin._product_row
        _variant_row = TransferMixin._variant_row

    return _Stub()


class TestTransferRowUnitAware:
    def test_producto_kg_permite_decimal(self):
        row = _stub()._product_row(_FakeProduct("kg"))
        assert row["allows_decimal"] is True
        assert row["unit"] == "kg"

    def test_producto_unidad_no_permite_decimal(self):
        row = _stub()._product_row(_FakeProduct("unidad"))
        assert row["allows_decimal"] is False

    def test_variante_hereda_unidad_del_producto(self):
        row = _stub()._variant_row(_FakeProduct("l"), _FakeVariant())
        assert row["allows_decimal"] is True

    def test_agregar_todo_conserva_fraccion_en_decimal(self):
        # "Agregar todo el stock" de un producto por peso conserva la fracción.
        row = _stub()._product_row(_FakeProduct("kg", stock=Decimal("2.5")))
        assert row["full_qty"] == "2.5"

    def test_agregar_todo_redondea_a_entero_en_unidad(self):
        row = _stub()._product_row(_FakeProduct("unidad", stock=Decimal("3")))
        assert row["full_qty"] == "3"
