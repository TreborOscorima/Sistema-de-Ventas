"""El buscador de productos del POS no debe "comerse" letras al escribir rápido.

Causa raíz (corregida): el input estaba ligado con ``value=`` directamente a
``new_sale_item["description"]``. Como ``rx.debounce_input`` (react-debounce-input)
resincroniza su estado interno cada vez que cambia el prop ``value`` (ver
``componentDidUpdate``), el eco TARDÍO del backend —que llega después del
``asyncio.sleep(0.2)`` del autocomplete, serializado por sesión— reescribía las
letras recién tipeadas.

El fix desacopla el TEXTO MOSTRADO (``product_search_display``) del texto que se
tipea: ``product_search_display`` solo cambia al SELECCIONAR/ESCANEAR/LIMPIAR,
nunca por cada tecla. Mientras se escribe, el prop ``value`` queda constante y el
debounce_input jamás pisa lo tipeado.

Estos tests fijan ese invariante a nivel de estado (CartMixin):
  * al llenar desde un producto (click en sugerencia o escaneo) → refleja el nombre
  * al resetear la barra (tras agregar / limpiar / Esc) → queda vacío
  * escribir (``handle_sale_change("description", ...)``) NO toca el display var
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-search-display-32chars-lng")
os.environ.setdefault("TENANT_STRICT", "0")


def _make_state():
    """VentaState mockeado con los métodos reales del CartMixin enlazados."""
    from app.states.venta.cart_mixin import CartMixin

    state = MagicMock()
    state.product_search_display = ""
    state.sale_form_key = 0
    state.new_sale_item = {"quantity": 0}
    state.autocomplete_suggestions = []
    state.autocomplete_results = []
    state.autocomplete_selected_index = -1
    state.selected_product = None
    # Métodos reales (lógica pura, sin BD)
    state._product_value = CartMixin._product_value.__get__(state)
    state._fill_sale_item_from_product = (
        CartMixin._fill_sale_item_from_product.__get__(state)
    )
    state._reset_sale_form = CartMixin._reset_sale_form.__get__(state)
    # Colaboradores de formato/redondeo → stubs deterministas
    state._normalize_quantity_value = lambda qty, unit: float(qty)
    state._round_currency = lambda v: round(float(v), 2)
    return state


class TestSearchDisplayDecoupling:
    def test_fill_desde_producto_refleja_el_nombre(self):
        state = _make_state()
        state._fill_sale_item_from_product(
            {"description": "CARNE DE POLLO", "unit": "kg", "sale_price": 12.5}
        )
        assert state.product_search_display == "CARNE DE POLLO"
        assert state.new_sale_item["description"] == "CARNE DE POLLO"

    def test_reset_limpia_el_display(self):
        state = _make_state()
        state.product_search_display = "algo tipeado a medias"
        state._reset_sale_form()
        assert state.product_search_display == ""

    @pytest.mark.asyncio
    async def test_escribir_no_toca_el_display(self):
        """Tipear en el buscador NO cambia ``product_search_display``.

        Es la garantía anti-clobber: mientras el cajero escribe, el prop
        ``value`` del debounce_input (ligado a ``product_search_display``)
        queda constante y no pisa las letras recién tipeadas. El texto tipeado
        sí actualiza ``new_sale_item["description"]`` (para validar/agregar),
        pero el display var solo cambia al seleccionar/escanear/limpiar.
        """
        from app.states.venta.cart_mixin import CartMixin

        state = _make_state()
        state.current_user = {"company_id": 1}
        state._branch_id = MagicMock(return_value=1)
        state._autocomplete_debounce_seq = 0
        state.new_sale_item = {"quantity": 0, "price": 0, "description": ""}
        state.handle_sale_change = CartMixin.handle_sale_change.__get__(state)

        with patch(
            "app.states.venta.cart_mixin.SaleService.search_products",
            new=AsyncMock(return_value=[]),
        ):
            await state.handle_sale_change("description", "coca")

        # El texto tipeado va al item (para poder agregar), PERO el display var
        # que alimenta el value= del input permanece intacto → sin clobber.
        assert state.new_sale_item["description"] == "coca"
        assert state.product_search_display == ""
