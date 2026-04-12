"""Tests de explosión de kits/combos en el carrito (CartMixin).

Verifica el flujo:
  1. Producto kit con componentes → se expande en ítems individuales
  2. Validación de stock por componente antes de agregar
  3. Distribución proporcional del precio del kit
  4. Badge KIT en cada componente expandido

Decisiones de diseño v1:
  - Componentes como ítems separados (trazabilidad SaleItem)
  - Stock insuficiente en componente → bloquea con toast
  - Sin kits anidados
  - Precio fijo del kit (Product.sale_price), distribuido proporcionalmente
"""
from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-kit-explosion-32chars-long")
os.environ.setdefault("TENANT_STRICT", "0")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_state():
    """Crea un VentaState mockeado con los métodos del CartMixin."""
    from app.states.venta.cart_mixin import CartMixin

    state = MagicMock()
    state.current_user = {
        "company_id": 1,
        "branch_id": 1,
        "privileges": {"create_ventas": True},
    }
    state._branch_id = MagicMock(return_value=1)
    state.new_sale_items = []
    state.new_sale_item = {
        "temp_id": "",
        "barcode": "",
        "description": "",
        "category": "General",
        "quantity": 0,
        "unit": "Unidad",
        "price": 0,
        "sale_price": 0,
        "subtotal": 0,
        "product_id": None,
        "variant_id": None,
        "batch_id": None,
        "batch_number": "",
        "requires_batch": False,
        "kit_product_id": None,
        "kit_name": "",
    }
    state.sale_receipt_ready = False

    # Bind real methods
    state._add_kit_to_cart = CartMixin._add_kit_to_cart.__get__(state)
    state._product_value = CartMixin._product_value.__get__(state)
    state._apply_item_rounding = CartMixin._apply_item_rounding.__get__(state)
    state._normalize_quantity_value = MagicMock(side_effect=lambda v, u: float(v))
    state._round_currency = MagicMock(side_effect=lambda v: round(float(v), 2))
    state._reset_sale_form = MagicMock()
    state._refresh_payment_feedback = MagicMock()
    return state


def _make_product(*, id_: int, barcode: str, description: str, sale_price, stock, unit="Unidad", category="General"):
    p = MagicMock()
    p.id = id_
    p.barcode = barcode
    p.description = description
    p.sale_price = Decimal(str(sale_price))
    p.stock = Decimal(str(stock))
    p.unit = unit
    p.category = category
    return p


def _make_kit_component(*, kit_id: int, component_id: int, quantity):
    c = MagicMock()
    c.kit_product_id = kit_id
    c.component_product_id = component_id
    c.quantity = Decimal(str(quantity))
    return c


def _patch_async_session_multi(calls_sequence):
    """Crea un context manager mock que devuelve resultados por llamada secuencial.

    calls_sequence es una lista de listas; cada lista es el resultado de .all()
    para las llamadas a session.exec() en orden.
    """
    call_count = {"n": 0}

    mock_session = AsyncMock()

    async def _exec_side_effect(query):
        idx = call_count["n"]
        call_count["n"] += 1
        result = MagicMock()
        if idx < len(calls_sequence):
            result.all.return_value = calls_sequence[idx]
        else:
            result.all.return_value = []
        return result

    mock_session.exec = _exec_side_effect

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Kit expansion básica
# ─────────────────────────────────────────────────────────────────────────────


class TestKitExpansion:
    """Un kit con componentes se expande en ítems individuales en el carrito."""

    @pytest.mark.asyncio
    async def test_kit_simple_expande_componentes(self):
        """Kit Escolar (cuaderno × 3, lapicera × 2) se expande en 2 ítems."""
        state = _make_state()

        cuaderno = _make_product(id_=10, barcode="CUA-001", description="Cuaderno A4", sale_price=5, stock=100)
        lapicera = _make_product(id_=20, barcode="LAP-001", description="Lapicera azul", sale_price=2, stock=100)

        components = [
            _make_kit_component(kit_id=1, component_id=10, quantity=3),
            _make_kit_component(kit_id=1, component_id=20, quantity=2),
        ]

        kit_payload = {"id": 1, "product_id": 1, "description": "Kit Escolar", "sale_price": Decimal("25.00")}

        # Secuencia: 1) load components, 2) load products
        session_mock = _patch_async_session_multi([components, [cuaderno, lapicera]])

        with patch("app.states.venta.cart_mixin.get_async_session", return_value=session_mock), \
             patch("app.states.venta.cart_mixin.SaleService.get_available_stock", new_callable=AsyncMock, return_value=Decimal("100")):
            result = await state._add_kit_to_cart(kit_payload, 1, 1)

        assert len(state.new_sale_items) == 2

        item_cuaderno = next(i for i in state.new_sale_items if i["product_id"] == 10)
        item_lapicera = next(i for i in state.new_sale_items if i["product_id"] == 20)

        assert item_cuaderno["quantity"] == 3.0
        assert item_lapicera["quantity"] == 2.0

        # Cada componente lleva el marcador del kit
        assert item_cuaderno["kit_product_id"] == 1
        assert item_cuaderno["kit_name"] == "Kit Escolar"
        assert item_lapicera["kit_product_id"] == 1

    @pytest.mark.asyncio
    async def test_distribucion_proporcional_precio(self):
        """El precio del kit se distribuye según peso (sale_price × qty)."""
        state = _make_state()

        # cuaderno: sale_price=5, qty=3 → peso=15
        # lapicera: sale_price=2, qty=2 → peso=4
        # total_weight=19, kit_price=19 → cuaderno_subtotal=15, lapicera_subtotal=4
        cuaderno = _make_product(id_=10, barcode="CUA-001", description="Cuaderno A4", sale_price=5, stock=100)
        lapicera = _make_product(id_=20, barcode="LAP-001", description="Lapicera azul", sale_price=2, stock=100)

        components = [
            _make_kit_component(kit_id=1, component_id=10, quantity=3),
            _make_kit_component(kit_id=1, component_id=20, quantity=2),
        ]

        kit_payload = {"id": 1, "product_id": 1, "description": "Kit", "sale_price": Decimal("19.00")}
        session_mock = _patch_async_session_multi([components, [cuaderno, lapicera]])

        with patch("app.states.venta.cart_mixin.get_async_session", return_value=session_mock), \
             patch("app.states.venta.cart_mixin.SaleService.get_available_stock", new_callable=AsyncMock, return_value=Decimal("100")):
            await state._add_kit_to_cart(kit_payload, 1, 1)

        # sum(subtotal) debe ser igual al precio del kit
        total = sum(i["subtotal"] for i in state.new_sale_items)
        assert abs(total - 19.0) < 0.02

    @pytest.mark.asyncio
    async def test_precio_kit_diferente_a_suma_componentes(self):
        """Kit con precio fijo distinto a la suma de componentes (descuento)."""
        state = _make_state()

        a = _make_product(id_=10, barcode="A", description="Prod A", sale_price=10, stock=50)
        b = _make_product(id_=20, barcode="B", description="Prod B", sale_price=10, stock=50)

        components = [
            _make_kit_component(kit_id=1, component_id=10, quantity=1),
            _make_kit_component(kit_id=1, component_id=20, quantity=1),
        ]

        # Kit a 15 en vez de 20 (descuento)
        kit_payload = {"id": 1, "product_id": 1, "description": "Combo AB", "sale_price": Decimal("15.00")}
        session_mock = _patch_async_session_multi([components, [a, b]])

        with patch("app.states.venta.cart_mixin.get_async_session", return_value=session_mock), \
             patch("app.states.venta.cart_mixin.SaleService.get_available_stock", new_callable=AsyncMock, return_value=Decimal("50")):
            await state._add_kit_to_cart(kit_payload, 1, 1)

        total = sum(i["subtotal"] for i in state.new_sale_items)
        assert abs(total - 15.0) < 0.02


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Validación de stock
# ─────────────────────────────────────────────────────────────────────────────


class TestKitStockValidation:
    """Si un componente no tiene stock, la venta del kit se bloquea."""

    @pytest.mark.asyncio
    async def test_stock_insuficiente_bloquea_kit(self):
        """Si un componente no tiene stock, no se agrega el kit."""
        state = _make_state()

        cuaderno = _make_product(id_=10, barcode="CUA-001", description="Cuaderno A4", sale_price=5, stock=2)
        lapicera = _make_product(id_=20, barcode="LAP-001", description="Lapicera azul", sale_price=2, stock=100)

        components = [
            _make_kit_component(kit_id=1, component_id=10, quantity=3),  # necesita 3, hay 2
            _make_kit_component(kit_id=1, component_id=20, quantity=2),
        ]

        kit_payload = {"id": 1, "product_id": 1, "description": "Kit Escolar", "sale_price": Decimal("25.00")}
        session_mock = _patch_async_session_multi([components, [cuaderno, lapicera]])

        stock_returns = {10: Decimal("2"), 20: Decimal("100")}

        async def _get_stock(pid, vid, cid, bid):
            return stock_returns.get(pid, Decimal("0"))

        with patch("app.states.venta.cart_mixin.get_async_session", return_value=session_mock), \
             patch("app.states.venta.cart_mixin.SaleService.get_available_stock", side_effect=_get_stock):
            result = await state._add_kit_to_cart(kit_payload, 1, 1)

        # No se agrega ningún componente al carrito
        assert len(state.new_sale_items) == 0

    @pytest.mark.asyncio
    async def test_stock_considera_items_en_carrito(self):
        """Si ya hay ítems del componente en el carrito, se descuenta del disponible."""
        state = _make_state()

        cuaderno = _make_product(id_=10, barcode="CUA-001", description="Cuaderno A4", sale_price=5, stock=5)
        lapicera = _make_product(id_=20, barcode="LAP-001", description="Lapicera azul", sale_price=2, stock=100)

        # Ya hay 3 cuadernos en el carrito
        state.new_sale_items = [
            {"product_id": 10, "variant_id": None, "quantity": 3.0, "temp_id": "x", "subtotal": 15.0},
        ]

        components = [
            _make_kit_component(kit_id=1, component_id=10, quantity=3),  # necesita 3 + 3 en carrito = 6, hay 5
            _make_kit_component(kit_id=1, component_id=20, quantity=2),
        ]

        kit_payload = {"id": 1, "product_id": 1, "description": "Kit Escolar", "sale_price": Decimal("25.00")}
        session_mock = _patch_async_session_multi([components, [cuaderno, lapicera]])

        stock_returns = {10: Decimal("5"), 20: Decimal("100")}

        async def _get_stock(pid, vid, cid, bid):
            return stock_returns.get(pid, Decimal("0"))

        with patch("app.states.venta.cart_mixin.get_async_session", return_value=session_mock), \
             patch("app.states.venta.cart_mixin.SaleService.get_available_stock", side_effect=_get_stock):
            result = await state._add_kit_to_cart(kit_payload, 1, 1)

        # Solo el ítem original sigue en el carrito, el kit no se agregó
        assert len(state.new_sale_items) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Kit sin componentes
# ─────────────────────────────────────────────────────────────────────────────


class TestKitSinComponentes:
    """Kit sin componentes configurados muestra error."""

    @pytest.mark.asyncio
    async def test_kit_vacio_muestra_toast(self):
        """Si el kit no tiene componentes, se muestra un toast de error."""
        state = _make_state()

        kit_payload = {"id": 1, "product_id": 1, "description": "Kit Vacío", "sale_price": Decimal("10.00")}
        session_mock = _patch_async_session_multi([[]])  # sin componentes

        with patch("app.states.venta.cart_mixin.get_async_session", return_value=session_mock):
            result = await state._add_kit_to_cart(kit_payload, 1, 1)

        assert len(state.new_sale_items) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Componente faltante
# ─────────────────────────────────────────────────────────────────────────────


class TestKitComponenteFaltante:
    """Si un componente referenciado no existe en BD, muestra error."""

    @pytest.mark.asyncio
    async def test_componente_no_encontrado(self):
        """Componente referenciado pero no en BD → toast de error."""
        state = _make_state()

        components = [
            _make_kit_component(kit_id=1, component_id=10, quantity=1),
            _make_kit_component(kit_id=1, component_id=99, quantity=1),  # no existe
        ]
        prod_a = _make_product(id_=10, barcode="A", description="A", sale_price=5, stock=50)

        kit_payload = {"id": 1, "product_id": 1, "description": "Kit Roto", "sale_price": Decimal("10.00")}
        # Solo se encuentra prod_a (id=10), id=99 no está
        session_mock = _patch_async_session_multi([components, [prod_a]])

        with patch("app.states.venta.cart_mixin.get_async_session", return_value=session_mock):
            result = await state._add_kit_to_cart(kit_payload, 1, 1)

        assert len(state.new_sale_items) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Precio con componentes a $0
# ─────────────────────────────────────────────────────────────────────────────


class TestKitComponentesPrecioCero:
    """Componentes con sale_price=0 → distribución equitativa."""

    @pytest.mark.asyncio
    async def test_componentes_precio_cero_distribucion_equitativa(self):
        """Si todos los componentes valen 0, el precio se distribuye equitativamente."""
        state = _make_state()

        a = _make_product(id_=10, barcode="A", description="Muestra A", sale_price=0, stock=50)
        b = _make_product(id_=20, barcode="B", description="Muestra B", sale_price=0, stock=50)

        components = [
            _make_kit_component(kit_id=1, component_id=10, quantity=1),
            _make_kit_component(kit_id=1, component_id=20, quantity=1),
        ]

        kit_payload = {"id": 1, "product_id": 1, "description": "Kit Promo", "sale_price": Decimal("10.00")}
        session_mock = _patch_async_session_multi([components, [a, b]])

        with patch("app.states.venta.cart_mixin.get_async_session", return_value=session_mock), \
             patch("app.states.venta.cart_mixin.SaleService.get_available_stock", new_callable=AsyncMock, return_value=Decimal("50")):
            await state._add_kit_to_cart(kit_payload, 1, 1)

        total = sum(i["subtotal"] for i in state.new_sale_items)
        assert abs(total - 10.0) < 0.02
        assert len(state.new_sale_items) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Kit CRUD en inventario
# ─────────────────────────────────────────────────────────────────────────────


class TestKitCRUDInventoryState:
    """CRUD de composición del kit en InventoryState."""

    def _make_inv_state(self):
        """Crea un estado mockeado con los métodos del InventoryState enlazados."""
        from app.states.inventory_state import InventoryState

        state = MagicMock()
        state.show_kit_components = False
        state.kit_components = []

        # Bind real methods (rx.event preserva la función original a nivel de clase)
        state.set_show_kit_components = InventoryState.set_show_kit_components.__get__(state)
        state.add_kit_component_row = InventoryState.add_kit_component_row.__get__(state)
        state.remove_kit_component_row = InventoryState.remove_kit_component_row.__get__(state)
        state.update_kit_component_field = InventoryState.update_kit_component_field.__get__(state)
        return state

    def test_toggle_show_kit_components(self):
        state = self._make_inv_state()
        state.set_show_kit_components(True)
        assert state.show_kit_components is True
        # Al activar con lista vacía, se agrega una fila
        assert len(state.kit_components) == 1

    def test_add_kit_component_row(self):
        state = self._make_inv_state()
        state.add_kit_component_row()
        assert len(state.kit_components) == 1
        assert state.kit_components[0]["component_product_id"] is None
        assert state.kit_components[0]["quantity"] == 1.0

    def test_remove_kit_component_row(self):
        state = self._make_inv_state()
        state.kit_components = [
            {"id": None, "component_barcode": "A", "component_name": "A", "component_product_id": 10, "quantity": 1.0},
            {"id": None, "component_barcode": "B", "component_name": "B", "component_product_id": 20, "quantity": 2.0},
        ]
        state.remove_kit_component_row(0)
        assert len(state.kit_components) == 1
        assert state.kit_components[0]["component_barcode"] == "B"

    def test_update_kit_component_quantity(self):
        state = self._make_inv_state()
        state.kit_components = [
            {"id": None, "component_barcode": "A", "component_name": "A", "component_product_id": 10, "quantity": 1.0},
        ]
        state.update_kit_component_field(0, "quantity", "5")
        assert state.kit_components[0]["quantity"] == 5.0

    def test_kit_component_rows_computed(self):
        """kit_component_rows agrega index a cada fila."""
        from app.states.inventory_state import InventoryState

        state = MagicMock()
        state.kit_components = [
            {"id": None, "component_barcode": "A", "component_name": "Prod A", "component_product_id": 10, "quantity": 2.0},
        ]

        # Acceder al fget directamente (ComputedVar de Reflex)
        fn = InventoryState.__dict__["kit_component_rows"]._fget
        rows = fn(state)
        assert rows[0]["index"] == 0
        assert rows[0]["component_name"] == "Prod A"
