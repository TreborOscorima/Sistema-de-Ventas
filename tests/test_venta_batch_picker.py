"""Tests del selector manual de lote en el POS (CartMixin).

Verifica el flujo:
  1. open_batch_picker(temp_id) — carga lotes disponibles del producto del carrito
  2. select_batch_for_item(batch_id) — actualiza el ítem con el lote elegido
  3. close_batch_picker() — limpia el state del modal

Permite al cajero cambiar el lote auto-asignado por FEFO desde el carrito,
útil cuando el cliente pide un lote específico (farmacias).
"""
from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-batch-picker-32chars-long")
os.environ.setdefault("TENANT_STRICT", "0")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_state():
    """Crea un VentaState mockeado con los métodos del CartMixin enlazados.

    Usa el mismo patrón que test_user_flow_scenarios.py: MagicMock + __get__.
    """
    from app.states.venta.cart_mixin import CartMixin

    state = MagicMock()
    state.current_user = {"company_id": 1, "branch_id": 1}
    state._branch_id = MagicMock(return_value=1)
    state.new_sale_items = []
    state.batch_picker_open = False
    state.batch_picker_temp_id = ""
    state.batch_picker_description = ""
    state.batch_picker_options = []
    state.batch_picker_loading = False

    # Bind real methods al mock para ejecutar la lógica real
    state.open_batch_picker = CartMixin.open_batch_picker.__get__(state)
    state.select_batch_for_item = CartMixin.select_batch_for_item.__get__(state)
    state.close_batch_picker = CartMixin.close_batch_picker.__get__(state)
    return state


def _make_batch(*, id_: int, batch_number: str, stock: str, expiration: datetime | None):
    b = MagicMock()
    b.id = id_
    b.batch_number = batch_number
    b.stock = Decimal(stock)
    b.expiration_date = expiration
    return b


def _patch_async_session(batches):
    """Crea un context manager mock para get_async_session()."""
    mock_session = AsyncMock()
    exec_result = MagicMock()
    exec_result.all.return_value = batches
    mock_session.exec.return_value = exec_result

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return patch(
        "app.states.venta.cart_mixin.get_async_session",
        return_value=cm,
    )


# ─────────────────────────────────────────────────────────────────────────────
# open_batch_picker
# ─────────────────────────────────────────────────────────────────────────────


class TestOpenBatchPicker:
    """El cajero abre el modal selector de lote desde un ítem del carrito."""

    @pytest.mark.asyncio
    async def test_carga_lotes_disponibles_marca_actual(self):
        """Carga lotes con stock>0 y marca el lote actual con is_current=True."""
        state = _make_state()
        state.new_sale_items = [
            {
                "temp_id": "abc-1",
                "description": "Ibuprofeno 400mg",
                "product_id": 10,
                "variant_id": None,
                "batch_id": 50,
                "batch_number": "L-A",
                "requires_batch": True,
            }
        ]

        batches = [
            _make_batch(
                id_=50, batch_number="L-A", stock="20",
                expiration=datetime(2026, 6, 1),
            ),
            _make_batch(
                id_=51, batch_number="L-B", stock="15",
                expiration=datetime(2026, 9, 15),
            ),
        ]
        with _patch_async_session(batches):
            await state.open_batch_picker("abc-1")

        assert state.batch_picker_open is True
        assert state.batch_picker_temp_id == "abc-1"
        assert state.batch_picker_description == "Ibuprofeno 400mg"
        assert len(state.batch_picker_options) == 2
        assert state.batch_picker_options[0]["id"] == 50
        assert state.batch_picker_options[0]["batch_number"] == "L-A"
        assert state.batch_picker_options[0]["is_current"] is True
        assert state.batch_picker_options[0]["stock"] == 20.0
        assert state.batch_picker_options[0]["expiration_date"] == "2026-06-01"
        assert state.batch_picker_options[1]["id"] == 51
        assert state.batch_picker_options[1]["is_current"] is False
        assert state.batch_picker_loading is False

    @pytest.mark.asyncio
    async def test_lote_sin_vencimiento_se_serializa_vacio(self):
        """ProductBatch.expiration_date=None → expiration_date='' en el dict."""
        state = _make_state()
        state.new_sale_items = [
            {
                "temp_id": "x-1",
                "description": "Sal de mesa",
                "product_id": 7,
                "variant_id": None,
                "batch_id": None,
                "batch_number": "",
                "requires_batch": True,
            }
        ]
        batches = [
            _make_batch(id_=200, batch_number="SAL-001", stock="100", expiration=None),
        ]
        with _patch_async_session(batches):
            await state.open_batch_picker("x-1")

        assert len(state.batch_picker_options) == 1
        assert state.batch_picker_options[0]["expiration_date"] == ""
        assert state.batch_picker_options[0]["is_current"] is False  # batch_id=None

    @pytest.mark.asyncio
    async def test_temp_id_inexistente_no_abre_modal(self):
        """Si el temp_id no está en new_sale_items, retorna toast y no abre."""
        state = _make_state()
        state.new_sale_items = [{"temp_id": "real-1", "product_id": 1}]

        result = await state.open_batch_picker("fantasma")

        assert state.batch_picker_open is False
        assert result is not None  # rx.toast retornado

    @pytest.mark.asyncio
    async def test_sin_company_id_no_abre_modal(self):
        """Sin company_id/branch_id no se puede consultar lotes."""
        state = _make_state()
        state.current_user = {}
        state._branch_id = MagicMock(return_value=None)
        state.new_sale_items = [
            {"temp_id": "abc-1", "product_id": 10, "variant_id": None}
        ]

        result = await state.open_batch_picker("abc-1")

        assert state.batch_picker_open is False
        assert result is not None  # rx.toast

    @pytest.mark.asyncio
    async def test_sin_product_id_ni_variant_id_falla(self):
        """Ítem sin identificador de stock no puede consultar lotes."""
        state = _make_state()
        state.new_sale_items = [
            {"temp_id": "x-1", "product_id": None, "variant_id": None}
        ]

        result = await state.open_batch_picker("x-1")

        assert state.batch_picker_open is False
        assert result is not None  # rx.toast

    @pytest.mark.asyncio
    async def test_excepcion_db_deja_modal_abierto_sin_opciones(self):
        """Si la DB falla, el modal se abre vacío y loading vuelve a False."""
        state = _make_state()
        state.new_sale_items = [
            {
                "temp_id": "abc-1",
                "description": "Producto X",
                "product_id": 10,
                "variant_id": None,
            }
        ]

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=RuntimeError("DB down"))
        cm.__aexit__ = AsyncMock(return_value=False)
        with patch(
            "app.states.venta.cart_mixin.get_async_session",
            return_value=cm,
        ):
            await state.open_batch_picker("abc-1")

        assert state.batch_picker_open is True
        assert state.batch_picker_options == []
        assert state.batch_picker_loading is False


# ─────────────────────────────────────────────────────────────────────────────
# select_batch_for_item
# ─────────────────────────────────────────────────────────────────────────────


class TestSelectBatchForItem:
    """El cajero elige un lote del modal y lo aplica al ítem del carrito."""

    def test_actualiza_batch_id_y_batch_number_del_item(self):
        """select_batch_for_item muta el ítem activo en new_sale_items."""
        state = _make_state()
        state.new_sale_items = [
            {
                "temp_id": "abc-1",
                "description": "Ibuprofeno",
                "product_id": 10,
                "batch_id": 50,
                "batch_number": "L-A",
                "requires_batch": True,
            }
        ]
        state.batch_picker_temp_id = "abc-1"
        state.batch_picker_options = [
            {"id": 50, "batch_number": "L-A", "stock": 20.0, "is_current": True},
            {"id": 51, "batch_number": "L-B", "stock": 15.0, "is_current": False},
        ]
        state.batch_picker_open = True

        result = state.select_batch_for_item(51)

        assert state.new_sale_items[0]["batch_id"] == 51
        assert state.new_sale_items[0]["batch_number"] == "L-B"
        assert state.new_sale_items[0]["requires_batch"] is True
        # Modal se cierra
        assert state.batch_picker_open is False
        assert state.batch_picker_temp_id == ""
        assert result is not None  # toast de confirmación

    def test_batch_id_inexistente_en_opciones_no_muta_carrito(self):
        """Si el batch_id no está en las opciones cargadas, retorna toast error."""
        state = _make_state()
        state.new_sale_items = [
            {
                "temp_id": "abc-1",
                "batch_id": 50,
                "batch_number": "L-A",
            }
        ]
        state.batch_picker_temp_id = "abc-1"
        state.batch_picker_options = [
            {"id": 50, "batch_number": "L-A", "stock": 20.0, "is_current": True},
        ]

        result = state.select_batch_for_item(999)

        assert state.new_sale_items[0]["batch_id"] == 50  # sin cambios
        assert result is not None  # toast

    def test_sin_temp_id_solo_cierra_modal(self):
        """Si el state no tiene temp_id activo, se limita a cerrar el modal."""
        state = _make_state()
        state.batch_picker_open = True
        state.batch_picker_temp_id = ""

        state.select_batch_for_item(42)

        assert state.batch_picker_open is False

    def test_batch_id_invalido_retorna_toast(self):
        """Un batch_id no convertible a int retorna toast de error."""
        state = _make_state()
        state.new_sale_items = [{"temp_id": "abc-1", "batch_id": 1}]
        state.batch_picker_temp_id = "abc-1"
        state.batch_picker_options = [
            {"id": 1, "batch_number": "L-1", "stock": 5.0, "is_current": True}
        ]

        result = state.select_batch_for_item("no-es-numero")

        assert result is not None  # toast
        assert state.new_sale_items[0]["batch_id"] == 1  # sin cambios


# ─────────────────────────────────────────────────────────────────────────────
# close_batch_picker
# ─────────────────────────────────────────────────────────────────────────────


class TestCloseBatchPicker:
    """Cerrar el modal limpia todo el state asociado."""

    def test_limpia_todo_el_state_del_modal(self):
        state = _make_state()
        state.batch_picker_open = True
        state.batch_picker_temp_id = "abc-1"
        state.batch_picker_description = "Producto X"
        state.batch_picker_options = [{"id": 1}, {"id": 2}]
        state.batch_picker_loading = True

        state.close_batch_picker()

        assert state.batch_picker_open is False
        assert state.batch_picker_temp_id == ""
        assert state.batch_picker_description == ""
        assert state.batch_picker_options == []
        assert state.batch_picker_loading is False
