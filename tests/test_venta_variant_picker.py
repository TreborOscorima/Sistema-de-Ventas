"""Tests del selector visual de variante en el POS (CartMixin).

Verifica el flujo:
  1. open_variant_picker(product_id) — carga variantes y arma matriz talla×color
  2. select_variant_for_sale(variant_id) — busca SKU y delega en _process_barcode
  3. close_variant_picker() — limpia state del modal
  4. add_product_to_sale_by_id auto-detecta variantes y abre el picker

Útil para rubros como ropa o juguetería donde los productos tienen
combinaciones de talla y color que hoy obligaban al cajero a teclear el SKU.
"""
from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-variant-picker-32chars")
os.environ.setdefault("TENANT_STRICT", "0")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_state():
    """VentaState mockeado con métodos del CartMixin enlazados."""
    from app.states.venta.cart_mixin import CartMixin

    state = MagicMock()
    state.current_user = {"company_id": 1, "branch_id": 1}
    state._branch_id = MagicMock(return_value=1)
    state.new_sale_items = []
    # Defaults del state del variant picker
    state.variant_picker_open = False
    state.variant_picker_product_id = None
    state.variant_picker_description = ""
    state.variant_picker_loading = False
    state.variant_picker_colors = []
    state.variant_picker_rows = []
    # Defaults necesarios para add_product_to_sale_by_id
    state.new_sale_item = {"quantity": 0}
    # Bind methods reales
    state.open_variant_picker = CartMixin.open_variant_picker.__get__(state)
    state.close_variant_picker = CartMixin.close_variant_picker.__get__(state)
    state.select_variant_for_sale = CartMixin.select_variant_for_sale.__get__(
        state
    )
    state.add_product_to_sale_by_id = (
        CartMixin.add_product_to_sale_by_id.__get__(state)
    )
    # _process_barcode debe ser AsyncMock para que select_variant_for_sale pueda awaitarlo
    state._process_barcode = AsyncMock(return_value="processed")
    return state


def _make_variant(
    *, id_: int, sku: str, size: str | None, color: str | None, stock: str
):
    v = MagicMock()
    v.id = id_
    v.sku = sku
    v.size = size
    v.color = color
    v.stock = Decimal(stock)
    return v


def _make_product(*, id_: int = 1, description: str = "Polo Manga Corta"):
    p = MagicMock()
    p.id = id_
    p.barcode = "PARENT-001"
    p.description = description
    p.category = "Ropa"
    p.unit = "Unidad"
    p.sale_price = Decimal("39.90")
    p.purchase_price = Decimal("18.00")
    p.stock = Decimal("0")
    return p


def _patch_async_session(*, exec_results: list):
    """Patch get_async_session con una lista de resultados secuenciales.

    Cada elemento de exec_results es un MagicMock con .first() / .all()
    configurados según el orden esperado de session.exec() calls.
    """
    mock_session = AsyncMock()
    mock_session.exec.side_effect = exec_results

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return patch(
        "app.states.venta.cart_mixin.get_async_session",
        return_value=cm,
    )


def _exec_first(value):
    r = MagicMock()
    r.first.return_value = value
    return r


def _exec_all(values):
    r = MagicMock()
    r.all.return_value = values
    return r


# ─────────────────────────────────────────────────────────────────────────────
# open_variant_picker
# ─────────────────────────────────────────────────────────────────────────────


class TestOpenVariantPicker:
    """El cajero abre la grilla talla×color para un producto con variantes."""

    @pytest.mark.asyncio
    async def test_arma_matriz_talla_x_color_correctamente(self):
        """Variantes S/M en Rojo/Azul → grilla 2x2 con celdas reales."""
        state = _make_state()
        product = _make_product(id_=10, description="Polo Manga Corta")
        variants = [
            _make_variant(id_=101, sku="POLO-S-RED", size="S", color="Rojo", stock="5"),
            _make_variant(id_=102, sku="POLO-S-BLU", size="S", color="Azul", stock="0"),
            _make_variant(id_=103, sku="POLO-M-RED", size="M", color="Rojo", stock="8"),
            _make_variant(id_=104, sku="POLO-M-BLU", size="M", color="Azul", stock="3"),
        ]

        with _patch_async_session(
            exec_results=[_exec_first(product), _exec_all(variants)]
        ):
            await state.open_variant_picker(10)

        assert state.variant_picker_open is True
        assert state.variant_picker_product_id == 10
        assert state.variant_picker_description == "Polo Manga Corta"
        assert state.variant_picker_loading is False

        # 2 tallas → 2 filas (preserva el orden del query mockeado)
        assert len(state.variant_picker_rows) == 2
        sizes = [r["size"] for r in state.variant_picker_rows]
        assert sizes == ["S", "M"]

        # 2 colores → 2 columnas (orden de aparición en el query)
        assert state.variant_picker_colors == ["Rojo", "Azul"]

        # Cada fila tiene 2 celdas
        for row in state.variant_picker_rows:
            assert len(row["cells"]) == 2

        # Verificar celda específica: M Rojo, stock 8, available
        m_row = next(r for r in state.variant_picker_rows if r["size"] == "M")
        m_red_cell = next(c for c in m_row["cells"] if c["color"] == "Rojo")
        assert m_red_cell["variant_id"] == 103
        assert m_red_cell["sku"] == "POLO-M-RED"
        assert m_red_cell["stock"] == 8.0
        assert m_red_cell["available"] is True
        assert m_red_cell["is_placeholder"] is False

        # S Azul tiene stock 0 → no available
        s_row = next(r for r in state.variant_picker_rows if r["size"] == "S")
        s_blue = next(c for c in s_row["cells"] if c["color"] == "Azul")
        assert s_blue["available"] is False

    @pytest.mark.asyncio
    async def test_combinaciones_faltantes_se_rellenan_como_placeholder(self):
        """Si falta talla M color Rojo, esa celda queda como placeholder."""
        state = _make_state()
        product = _make_product(id_=11)
        variants = [
            _make_variant(id_=1, sku="A", size="S", color="Rojo", stock="5"),
            _make_variant(id_=2, sku="B", size="M", color="Azul", stock="3"),
            # Falta S/Azul y M/Rojo
        ]
        with _patch_async_session(
            exec_results=[_exec_first(product), _exec_all(variants)]
        ):
            await state.open_variant_picker(11)

        assert len(state.variant_picker_rows) == 2
        # S row: Rojo real + Azul placeholder
        s_row = next(r for r in state.variant_picker_rows if r["size"] == "S")
        s_red = next(c for c in s_row["cells"] if c["color"] == "Rojo")
        s_blue = next(c for c in s_row["cells"] if c["color"] == "Azul")
        assert s_red["is_placeholder"] is False
        assert s_blue["is_placeholder"] is True
        assert s_blue["variant_id"] == 0
        assert s_blue["available"] is False

    @pytest.mark.asyncio
    async def test_variante_sin_color_usa_marcador_dash(self):
        """Variante con color=None se agrupa bajo la columna '—'."""
        state = _make_state()
        product = _make_product(id_=12, description="Cinto cuero")
        variants = [
            _make_variant(id_=1, sku="CINT-S", size="S", color=None, stock="2"),
            _make_variant(id_=2, sku="CINT-M", size="M", color=None, stock="4"),
        ]
        with _patch_async_session(
            exec_results=[_exec_first(product), _exec_all(variants)]
        ):
            await state.open_variant_picker(12)

        assert state.variant_picker_colors == ["—"]
        for row in state.variant_picker_rows:
            assert len(row["cells"]) == 1
            assert row["cells"][0]["color"] == "—"

    @pytest.mark.asyncio
    async def test_producto_sin_variantes_cierra_modal_y_avisa(self):
        """Sin variantes registradas, el modal se cierra y se muestra toast."""
        state = _make_state()
        product = _make_product(id_=13)
        with _patch_async_session(
            exec_results=[_exec_first(product), _exec_all([])]
        ):
            result = await state.open_variant_picker(13)

        assert state.variant_picker_open is False
        assert result is not None  # toast

    @pytest.mark.asyncio
    async def test_producto_inexistente_cierra_modal(self):
        """Si el producto no existe, el modal se cierra y muestra toast."""
        state = _make_state()
        with _patch_async_session(exec_results=[_exec_first(None)]):
            result = await state.open_variant_picker(999)

        assert state.variant_picker_open is False
        assert result is not None

    @pytest.mark.asyncio
    async def test_sin_company_id_no_abre_modal(self):
        """Sin contexto de empresa, retorna toast y no abre."""
        state = _make_state()
        state.current_user = {}
        state._branch_id = MagicMock(return_value=None)

        result = await state.open_variant_picker(10)

        assert state.variant_picker_open is False
        assert result is not None

    @pytest.mark.asyncio
    async def test_product_id_invalido_retorna_toast(self):
        state = _make_state()
        result = await state.open_variant_picker("no-num")
        assert state.variant_picker_open is False
        assert result is not None


# ─────────────────────────────────────────────────────────────────────────────
# select_variant_for_sale
# ─────────────────────────────────────────────────────────────────────────────


class TestSelectVariantForSale:
    """El cajero hace click en una celda → la variante se agrega al carrito."""

    @pytest.mark.asyncio
    async def test_celda_disponible_delega_en_process_barcode(self):
        """Selecciona una variante con stock → llama a _process_barcode(sku)."""
        state = _make_state()
        state.variant_picker_open = True
        state.variant_picker_rows = [
            {
                "size": "M",
                "cells": [
                    {
                        "color": "Rojo",
                        "variant_id": 103,
                        "sku": "POLO-M-RED",
                        "stock": 8.0,
                        "available": True,
                        "is_placeholder": False,
                    }
                ],
            }
        ]

        await state.select_variant_for_sale(103)

        state._process_barcode.assert_awaited_once_with("POLO-M-RED")
        # Modal se cerró
        assert state.variant_picker_open is False
        assert state.variant_picker_rows == []

    @pytest.mark.asyncio
    async def test_celda_sin_stock_no_agrega(self):
        """Celda con available=False retorna toast sin llamar process_barcode."""
        state = _make_state()
        state.variant_picker_rows = [
            {
                "size": "S",
                "cells": [
                    {
                        "color": "Azul",
                        "variant_id": 102,
                        "sku": "POLO-S-BLU",
                        "stock": 0.0,
                        "available": False,
                        "is_placeholder": False,
                    }
                ],
            }
        ]

        result = await state.select_variant_for_sale(102)

        assert result is not None
        state._process_barcode.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_celda_placeholder_no_agrega(self):
        """Celdas placeholder (combinación inexistente) no agregan nada."""
        state = _make_state()
        state.variant_picker_rows = [
            {
                "size": "S",
                "cells": [
                    {
                        "color": "Verde",
                        "variant_id": 0,
                        "sku": "",
                        "stock": 0.0,
                        "available": False,
                        "is_placeholder": True,
                    }
                ],
            }
        ]

        result = await state.select_variant_for_sale(0)
        assert result is not None
        state._process_barcode.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_variant_id_inexistente_retorna_toast(self):
        state = _make_state()
        state.variant_picker_rows = [
            {
                "size": "S",
                "cells": [
                    {
                        "color": "Rojo",
                        "variant_id": 1,
                        "sku": "A",
                        "available": True,
                        "is_placeholder": False,
                    }
                ],
            }
        ]
        result = await state.select_variant_for_sale(999)
        assert result is not None
        state._process_barcode.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_variant_id_invalido_retorna_toast(self):
        state = _make_state()
        result = await state.select_variant_for_sale("no-num")
        assert result is not None
        state._process_barcode.assert_not_awaited()


# ─────────────────────────────────────────────────────────────────────────────
# close_variant_picker
# ─────────────────────────────────────────────────────────────────────────────


class TestCloseVariantPicker:
    def test_limpia_todo_el_state(self):
        state = _make_state()
        state.variant_picker_open = True
        state.variant_picker_product_id = 10
        state.variant_picker_description = "Polo X"
        state.variant_picker_colors = ["Rojo", "Azul"]
        state.variant_picker_rows = [{"size": "S", "cells": []}]
        state.variant_picker_loading = True

        state.close_variant_picker()

        assert state.variant_picker_open is False
        assert state.variant_picker_product_id is None
        assert state.variant_picker_description == ""
        assert state.variant_picker_colors == []
        assert state.variant_picker_rows == []
        assert state.variant_picker_loading is False


# ─────────────────────────────────────────────────────────────────────────────
# add_product_to_sale_by_id — auto-detección de variantes
# ─────────────────────────────────────────────────────────────────────────────


class TestAddProductAutoDetectVariants:
    """add_product_to_sale_by_id debe abrir el picker si hay variantes."""

    @pytest.mark.asyncio
    async def test_producto_con_variantes_abre_picker_no_agrega(self):
        """Si existe al menos 1 variante, se abre el modal y NO se agrega el padre."""
        state = _make_state()
        # Mock open_variant_picker para verificar invocación
        state.open_variant_picker = AsyncMock(return_value="picker_opened")
        # Mock add_item_to_sale para verificar que NO se llama
        state.add_item_to_sale = AsyncMock()

        product = _make_product(id_=10)
        variant_marker = MagicMock()  # solo necesita ser truthy

        with _patch_async_session(
            exec_results=[_exec_first(product), _exec_first(variant_marker)]
        ):
            result = await state.add_product_to_sale_by_id(10)

        state.open_variant_picker.assert_awaited_once_with(10)
        state.add_item_to_sale.assert_not_awaited()
        assert result == "picker_opened"

    @pytest.mark.asyncio
    async def test_producto_sin_variantes_se_agrega_directo(self):
        """Sin variantes, se conserva el flujo original (add_item_to_sale)."""
        state = _make_state()
        state.open_variant_picker = AsyncMock()
        state.add_item_to_sale = AsyncMock(return_value="added")

        product = _make_product(id_=20)

        with _patch_async_session(
            exec_results=[_exec_first(product), _exec_first(None)]
        ):
            result = await state.add_product_to_sale_by_id(20)

        state.open_variant_picker.assert_not_awaited()
        state.add_item_to_sale.assert_awaited_once()
        assert result == "added"
        # Cantidad por defecto seteada a 1
        assert state.new_sale_item["quantity"] == 1
