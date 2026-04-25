"""Tests del motor de pricing — :mod:`app.services.pricing`.

Cobertura:
  * ``resolve_price_list_price``: prioridad variante > producto, retorno None.
  * ``resolve_price_tier_price``: tier por variante primero, fallback producto.
  * ``find_applicable_promotion``: jerarquía PRODUCT > CATEGORY > ALL,
    filtrado por vigencia, ``min_quantity`` y ``max_uses``.
  * ``apply_promotion_to_price``: PERCENTAGE, FIXED_AMOUNT, BUY_X_GET_Y.
  * ``resolve_effective_price``: jerarquía completa + promo.

Estos helpers son puros (no mutan modelo), así que se testean contra
``FakeAsyncSession`` agotando ``exec.side_effect`` con ``ExecResult``.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.utils.timezone import utc_now_naive
from app.services.pricing import (
    PriceResolution,
    PriceSource,
    apply_promotion_to_price,
    find_applicable_promotion,
    resolve_effective_price,
    resolve_price_list_price,
    resolve_price_tier_price,
)


# ─── Fakes mínimos (no usar modelos ORM reales para evitar acoplar Tests con DB) ──


def _make_price_list_item(unit_price: str | Decimal) -> SimpleNamespace:
    return SimpleNamespace(unit_price=Decimal(str(unit_price)))


def _make_tier(unit_price: str | Decimal) -> SimpleNamespace:
    return SimpleNamespace(unit_price=Decimal(str(unit_price)))


def _make_promotion(
    *,
    promo_id: int = 1,
    name: str = "Promo Test",
    promotion_type: str = "percentage",
    scope: str = "all",
    discount_value: str | Decimal = "10",
    min_quantity: int = 1,
    free_quantity: int = 0,
    is_active: bool = True,
    max_uses: int | None = None,
    current_uses: int = 0,
    product_id: int | None = None,
    category: str | None = None,
    starts_at=None,
    ends_at=None,
) -> SimpleNamespace:
    now = utc_now_naive()
    return SimpleNamespace(
        id=promo_id,
        name=name,
        promotion_type=promotion_type,
        scope=scope,
        discount_value=Decimal(str(discount_value)),
        min_quantity=min_quantity,
        free_quantity=free_quantity,
        is_active=is_active,
        max_uses=max_uses,
        current_uses=current_uses,
        product_id=product_id,
        category=category,
        starts_at=starts_at or (now - timedelta(days=1)),
        ends_at=ends_at or (now + timedelta(days=30)),
    )


def _make_product(
    *,
    product_id: int = 1,
    sale_price: str | Decimal = "100.00",
    category: str = "General",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=product_id,
        sale_price=Decimal(str(sale_price)),
        category=category,
    )


# ──────────────────────────────────────────────────────────────────────────────
# resolve_price_list_price
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_price_list_variant_match_takes_precedence(
    session_mock, exec_result
):
    """Si hay match por variante, retorna ese precio sin consultar producto."""
    session_mock.exec.side_effect = [
        exec_result(first_item=_make_price_list_item("80.00")),
    ]

    price = await resolve_price_list_price(
        session_mock,
        product_id=1,
        variant_id=10,
        price_list_id=5,
        company_id=1,
        branch_id=1,
    )

    assert price == Decimal("80.00")
    # Solo una query: la de variante (no cae al fallback de producto).
    assert session_mock.exec.call_count == 1


@pytest.mark.asyncio
async def test_price_list_falls_back_to_product_when_variant_missing(
    session_mock, exec_result
):
    """Sin match por variante → consulta producto base de la lista."""
    session_mock.exec.side_effect = [
        exec_result(first_item=None),  # variant lookup
        exec_result(first_item=_make_price_list_item("90.00")),  # product
    ]

    price = await resolve_price_list_price(
        session_mock,
        product_id=1,
        variant_id=10,
        price_list_id=5,
        company_id=1,
        branch_id=1,
    )

    assert price == Decimal("90.00")
    assert session_mock.exec.call_count == 2


@pytest.mark.asyncio
async def test_price_list_returns_none_when_product_not_in_list(
    session_mock, exec_result
):
    session_mock.exec.side_effect = [
        exec_result(first_item=None),
        exec_result(first_item=None),
    ]

    price = await resolve_price_list_price(
        session_mock,
        product_id=1,
        variant_id=None,
        price_list_id=5,
        company_id=1,
        branch_id=1,
    )

    assert price is None


# ──────────────────────────────────────────────────────────────────────────────
# resolve_price_tier_price
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier_variant_match_returns_tier_price(session_mock, exec_result):
    session_mock.exec.side_effect = [
        exec_result(first_item=_make_tier("75.00")),
    ]

    price = await resolve_price_tier_price(
        session_mock,
        product_id=1,
        variant_id=10,
        quantity=Decimal("5"),
        company_id=1,
        branch_id=1,
    )

    assert price == Decimal("75.00")


@pytest.mark.asyncio
async def test_tier_returns_none_when_no_tier_matches(
    session_mock, exec_result
):
    session_mock.exec.side_effect = [
        exec_result(first_item=None),  # variant
        exec_result(first_item=None),  # product
    ]

    price = await resolve_price_tier_price(
        session_mock,
        product_id=1,
        variant_id=10,
        quantity=Decimal("5"),
        company_id=1,
        branch_id=1,
    )

    assert price is None


# ──────────────────────────────────────────────────────────────────────────────
# find_applicable_promotion — filtros y jerarquía
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_promotion_skipped_when_max_uses_reached(
    session_mock, exec_result
):
    """Una promo con current_uses >= max_uses no debe matchear aunque esté vigente."""
    promo = _make_promotion(max_uses=10, current_uses=10)
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1,
        category="General",
        quantity=Decimal("1"),
        company_id=1,
        branch_id=1,
    )

    assert result is None


@pytest.mark.asyncio
async def test_promotion_skipped_when_quantity_below_minimum(
    session_mock, exec_result
):
    promo = _make_promotion(min_quantity=5)
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1,
        category="General",
        quantity=Decimal("3"),
        company_id=1,
        branch_id=1,
    )

    assert result is None


@pytest.mark.asyncio
async def test_promotion_product_scope_must_match_product_id(
    session_mock, exec_result
):
    """scope=PRODUCT solo aplica si product_id coincide."""
    promo = _make_promotion(scope="product", product_id=42)
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    miss = await find_applicable_promotion(
        session_mock,
        product_id=1,  # distinto de promo.product_id (42)
        category="General",
        quantity=Decimal("1"),
        company_id=1,
        branch_id=1,
    )
    assert miss is None


@pytest.mark.asyncio
async def test_promotion_category_scope_matches_category_string(
    session_mock, exec_result
):
    promo = _make_promotion(scope="category", category="Bebidas")
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1,
        category="Bebidas",
        quantity=Decimal("1"),
        company_id=1,
        branch_id=1,
    )

    assert result is promo


@pytest.mark.asyncio
async def test_promotion_all_scope_applies_universally(
    session_mock, exec_result
):
    promo = _make_promotion(scope="all")
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=999,
        category="cualquiera",
        quantity=Decimal("1"),
        company_id=1,
        branch_id=1,
    )

    assert result is promo


@pytest.mark.asyncio
async def test_promotion_first_match_wins_in_iteration_order(
    session_mock, exec_result
):
    """El SQL ordena por scope desc; el helper toma el primero que valida."""
    specific = _make_promotion(promo_id=1, scope="product", product_id=42)
    generic = _make_promotion(promo_id=2, scope="all")
    # El query del helper retorna en orden ya por scope desc; el test
    # verifica que el primer elemento iterado que aplique gana.
    session_mock.exec.side_effect = [exec_result(all_items=[specific, generic])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=42,
        category="X",
        quantity=Decimal("1"),
        company_id=1,
        branch_id=1,
    )

    assert result is specific


# ──────────────────────────────────────────────────────────────────────────────
# apply_promotion_to_price — pure function, sin DB
# ──────────────────────────────────────────────────────────────────────────────


def test_apply_percentage_discount():
    promo = _make_promotion(promotion_type="percentage", discount_value="20")
    final = apply_promotion_to_price(promo, Decimal("100.00"))
    assert final == Decimal("80.00")


def test_apply_fixed_amount_clamps_to_zero():
    promo = _make_promotion(promotion_type="fixed_amount", discount_value="50")
    final = apply_promotion_to_price(promo, Decimal("30.00"))
    # No permite precio negativo
    assert final == Decimal("0")


def test_apply_buy_x_get_y_unit_factor():
    """Promo 3x2: min_quantity=2 paga, free_quantity=1 regalo, total_group=3.

    Precio efectivo unitario = unit * (2/3).
    """
    promo = _make_promotion(
        promotion_type="buy_x_get_y", min_quantity=2, free_quantity=1
    )
    final = apply_promotion_to_price(promo, Decimal("30.00"))
    expected = Decimal("30.00") * (Decimal("2") / Decimal("3"))
    assert final == expected


def test_apply_unknown_type_returns_unit_price_unchanged():
    promo = _make_promotion(promotion_type="invalido")
    final = apply_promotion_to_price(promo, Decimal("100.00"))
    assert final == Decimal("100.00")


def test_apply_buy_x_get_y_with_zero_total_group_is_safe():
    """Edge case: free_quantity ajustado a un valor que haría total_group=0
    no debe dividir por cero."""
    promo = _make_promotion(
        promotion_type="buy_x_get_y", min_quantity=1, free_quantity=-1
    )
    # min_q + free_q = 0, retorna unit_price intacto
    final = apply_promotion_to_price(promo, Decimal("50.00"))
    assert final == Decimal("50.00")


# ──────────────────────────────────────────────────────────────────────────────
# resolve_effective_price — orquestación completa
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_effective_price_uses_price_list_then_promotion(
    session_mock, exec_result
):
    """Cliente con lista asignada: precio base = lista, después aplica promo."""
    product = _make_product(sale_price="100.00", category="General")
    pl_item = _make_price_list_item("80.00")
    promo = _make_promotion(promotion_type="percentage", discount_value="10")

    session_mock.exec.side_effect = [
        # 1. resolve_price_list_price (sin variant → directo a producto)
        exec_result(first_item=pl_item),
        # 2. find_applicable_promotion
        exec_result(all_items=[promo]),
    ]

    res = await resolve_effective_price(
        session_mock,
        product=product,
        variant_id=None,
        quantity=Decimal("1"),
        company_id=1,
        branch_id=1,
        client_price_list_id=5,
    )

    assert isinstance(res, PriceResolution)
    assert res.source == PriceSource.PRICE_LIST
    assert res.base_price == Decimal("80.00")
    assert res.final_price == Decimal("72.00")  # 80 * 0.9
    assert res.applied_promotion is promo


@pytest.mark.asyncio
async def test_effective_price_falls_through_to_tier_when_no_list(
    session_mock, exec_result
):
    product = _make_product(sale_price="100.00")
    tier = _make_tier("70.00")

    session_mock.exec.side_effect = [
        # No price_list_id → no consulta lista
        exec_result(first_item=tier),  # resolve_price_tier_price (product branch)
        exec_result(all_items=[]),     # find_applicable_promotion (sin promos)
    ]

    res = await resolve_effective_price(
        session_mock,
        product=product,
        variant_id=None,
        quantity=Decimal("3"),
        company_id=1,
        branch_id=1,
        client_price_list_id=None,
    )

    assert res.source == PriceSource.TIER
    assert res.base_price == Decimal("70.00")
    assert res.final_price == Decimal("70.00")
    assert res.applied_promotion is None


@pytest.mark.asyncio
async def test_effective_price_falls_through_to_base_sale_price(
    session_mock, exec_result
):
    """Sin lista, sin tier, sin promo → product.sale_price."""
    product = _make_product(sale_price="100.00")

    session_mock.exec.side_effect = [
        exec_result(first_item=None),  # tier (product branch)
        exec_result(all_items=[]),     # promo
    ]

    res = await resolve_effective_price(
        session_mock,
        product=product,
        variant_id=None,
        quantity=Decimal("1"),
        company_id=1,
        branch_id=1,
        client_price_list_id=None,
    )

    assert res.source == PriceSource.BASE
    assert res.base_price == Decimal("100.00")
    assert res.final_price == Decimal("100.00")
