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
    weekdays_mask: int = 127,
    time_from=None,
    time_to=None,
    coupon_code: str | None = None,
    min_cart_amount: str | Decimal | int = "0",
    max_units_per_transaction: int | None = None,
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
        weekdays_mask=weekdays_mask,
        time_from=time_from,
        time_to=time_to,
        coupon_code=coupon_code,
        min_cart_amount=Decimal(str(min_cart_amount)),
        max_units_per_transaction=max_units_per_transaction,
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
# Filtros de día y banda horaria
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_promotion_skipped_when_today_not_in_weekdays_mask(
    session_mock, exec_result
):
    """mask=1 (sólo lunes) no debe matchear un miércoles."""
    from datetime import datetime as _dt
    wednesday_noon = _dt(2026, 4, 29, 12, 0)  # 2026-04-29 es miércoles
    promo = _make_promotion(weekdays_mask=1)  # solo lunes (bit 0)
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1,
        category="General",
        quantity=Decimal("1"),
        company_id=1,
        branch_id=1,
        now=wednesday_noon,
    )
    assert result is None


@pytest.mark.asyncio
async def test_promotion_matches_when_today_in_weekdays_mask(
    session_mock, exec_result
):
    from datetime import datetime as _dt
    wednesday_noon = _dt(2026, 4, 29, 12, 0)
    promo = _make_promotion(weekdays_mask=4)  # solo miércoles (bit 2)
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1,
        category="General",
        quantity=Decimal("1"),
        company_id=1,
        branch_id=1,
        now=wednesday_noon,
    )
    assert result is promo


@pytest.mark.asyncio
async def test_promotion_skipped_outside_time_window(
    session_mock, exec_result
):
    from datetime import datetime as _dt, time as _t
    noon = _dt(2026, 4, 29, 12, 0)
    promo = _make_promotion(time_from=_t(15, 0), time_to=_t(18, 0))
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1,
        category="General",
        quantity=Decimal("1"),
        company_id=1,
        branch_id=1,
        now=noon,
    )
    assert result is None


@pytest.mark.asyncio
async def test_promotion_matches_inside_time_window(
    session_mock, exec_result
):
    from datetime import datetime as _dt, time as _t
    afternoon = _dt(2026, 4, 29, 16, 30)
    promo = _make_promotion(time_from=_t(15, 0), time_to=_t(18, 0))
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1,
        category="General",
        quantity=Decimal("1"),
        company_id=1,
        branch_id=1,
        now=afternoon,
    )
    assert result is promo


@pytest.mark.asyncio
async def test_promotion_time_window_crosses_midnight(
    session_mock, exec_result
):
    """time_from > time_to debe interpretarse como rango cruzando medianoche."""
    from datetime import datetime as _dt, time as _t
    promo = _make_promotion(time_from=_t(22, 0), time_to=_t(2, 0))

    # 23:30 → dentro del rango (22:00-medianoche)
    late_night = _dt(2026, 4, 29, 23, 30)
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]
    result = await find_applicable_promotion(
        session_mock,
        product_id=1, category="General", quantity=Decimal("1"),
        company_id=1, branch_id=1, now=late_night,
    )
    assert result is promo

    # 12:00 → fuera del rango
    midday = _dt(2026, 4, 29, 12, 0)
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]
    result = await find_applicable_promotion(
        session_mock,
        product_id=1, category="General", quantity=Decimal("1"),
        company_id=1, branch_id=1, now=midday,
    )
    assert result is None


# ──────────────────────────────────────────────────────────────────────────────
# Cupones
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_promotion_with_coupon_skipped_when_no_coupon_provided(
    session_mock, exec_result
):
    """Una promo con coupon_code no debe aplicar si el caller no lo ingresó."""
    promo = _make_promotion(coupon_code="VERANO20")
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1, category="General", quantity=Decimal("1"),
        company_id=1, branch_id=1,
        coupon_code=None,
    )
    assert result is None


@pytest.mark.asyncio
async def test_promotion_with_coupon_skipped_when_code_mismatch(
    session_mock, exec_result
):
    promo = _make_promotion(coupon_code="VERANO20")
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1, category="General", quantity=Decimal("1"),
        company_id=1, branch_id=1,
        coupon_code="OTRO",
    )
    assert result is None


@pytest.mark.asyncio
async def test_promotion_with_coupon_matches_case_insensitive(
    session_mock, exec_result
):
    promo = _make_promotion(coupon_code="VERANO20")
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1, category="General", quantity=Decimal("1"),
        company_id=1, branch_id=1,
        coupon_code="verano20",
    )
    assert result is promo


@pytest.mark.asyncio
async def test_promotion_with_coupon_wins_over_automatic(
    session_mock, exec_result
):
    """Cuando el cupón matchea, gana sobre la promo automática."""
    coupon_promo = _make_promotion(promo_id=1, coupon_code="VERANO20", scope="all")
    auto_promo = _make_promotion(promo_id=2, coupon_code=None, scope="all")
    # El motor confía en el orden del SQL (coupon_code NULL al final). Mock
    # respeta ese orden.
    session_mock.exec.side_effect = [exec_result(all_items=[coupon_promo, auto_promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1, category="General", quantity=Decimal("1"),
        company_id=1, branch_id=1,
        coupon_code="VERANO20",
    )
    assert result is coupon_promo


# ──────────────────────────────────────────────────────────────────────────────
# find_applicable_promotion — filtro min_cart_amount
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_promotion_with_min_cart_skipped_when_subtotal_below(
    session_mock, exec_result
):
    """Promo con umbral de carrito no aplica si el subtotal está por debajo."""
    promo = _make_promotion(min_cart_amount="1000")
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1, category="General", quantity=Decimal("1"),
        company_id=1, branch_id=1,
        cart_subtotal=Decimal("500"),
    )
    assert result is None


@pytest.mark.asyncio
async def test_promotion_with_min_cart_applies_when_subtotal_meets(
    session_mock, exec_result
):
    """Promo con umbral aplica cuando el subtotal alcanza el mínimo exacto."""
    promo = _make_promotion(min_cart_amount="1000")
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1, category="General", quantity=Decimal("1"),
        company_id=1, branch_id=1,
        cart_subtotal=Decimal("1000"),
    )
    assert result is promo


@pytest.mark.asyncio
async def test_promotion_with_min_cart_skipped_when_subtotal_omitted(
    session_mock, exec_result
):
    """Sin cart_subtotal explícito, una promo con umbral > 0 se descarta.

    Defensa: mejor no aplicar el descuento que cobrarlo mal por falta de
    contexto del carrito.
    """
    promo = _make_promotion(min_cart_amount="1000")
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1, category="General", quantity=Decimal("1"),
        company_id=1, branch_id=1,
        # cart_subtotal omitido a propósito
    )
    assert result is None


@pytest.mark.asyncio
async def test_promotion_without_min_cart_ignores_subtotal_arg(
    session_mock, exec_result
):
    """Promo con min_cart_amount=0 aplica aunque no se pase subtotal."""
    promo = _make_promotion(min_cart_amount="0")
    session_mock.exec.side_effect = [exec_result(all_items=[promo])]

    result = await find_applicable_promotion(
        session_mock,
        product_id=1, category="General", quantity=Decimal("1"),
        company_id=1, branch_id=1,
    )
    assert result is promo


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


def test_apply_buy_x_get_y_exact_group():
    """Lleva 3 paga 2: comprar exactamente 3 → 1 gratis → paga 2."""
    promo = _make_promotion(
        promotion_type="buy_x_get_y", min_quantity=3, free_quantity=1
    )
    # 3 unidades → 1 grupo completo → 1 gratis → paga 2
    # precio efectivo por unidad = 30 * (2/3); total = 3 * 20 = 60 = 2 * 30
    final = apply_promotion_to_price(promo, Decimal("30.00"), Decimal("3"))
    assert final * Decimal("3") == Decimal("60.00")


def test_apply_buy_x_get_y_two_complete_groups():
    """Lleva 3 paga 2 con 6 unidades: 2 grupos → 2 gratis → paga 4."""
    promo = _make_promotion(
        promotion_type="buy_x_get_y", min_quantity=3, free_quantity=1
    )
    final = apply_promotion_to_price(promo, Decimal("30.00"), Decimal("6"))
    assert final * Decimal("6") == Decimal("120.00")  # 4 × 30


def test_apply_buy_x_get_y_partial_group_no_extra_discount():
    """1 grupo completo (3) + 1 unidad suelta → 4 total, paga 3 (solo 1 gratis)."""
    promo = _make_promotion(
        promotion_type="buy_x_get_y", min_quantity=3, free_quantity=1
    )
    final = apply_promotion_to_price(promo, Decimal("30.00"), Decimal("4"))
    assert final * Decimal("4") == Decimal("90.00")  # 3 × 30


def test_apply_nth_unit_discount_exact_group():
    """Cada 3u, la 3ra con 50% off: comprando 3 → paga 2.5."""
    promo = _make_promotion(
        promotion_type="nth_unit_discount", min_quantity=3, discount_value="50"
    )
    # 1 grupo completo: descuento = 1 × 0.5 × 100 / 3 = 16.67 por unidad
    # total = 3 × 83.33 = 250 (= 2 full + 1 al 50%)
    final = apply_promotion_to_price(promo, Decimal("100.00"), Decimal("3"))
    assert final * Decimal("3") == Decimal("250.00")


def test_apply_nth_unit_discount_two_groups():
    """Cada 3u, la 3ra con 50% off: comprando 6 → 2 grupos → paga 5."""
    promo = _make_promotion(
        promotion_type="nth_unit_discount", min_quantity=3, discount_value="50"
    )
    final = apply_promotion_to_price(promo, Decimal("100.00"), Decimal("6"))
    assert final * Decimal("6") == Decimal("500.00")  # 5 × 100


def test_apply_nth_unit_discount_partial_group_no_extra_discount():
    """1 grupo completo (3) + 1 suelta → paga 3.5, no 3 (la suelta es full)."""
    promo = _make_promotion(
        promotion_type="nth_unit_discount", min_quantity=3, discount_value="50"
    )
    # 4 unidades: 1 grupo → descuento = 50 total distribuido en 4 = 12.5/u
    # total = 4 × 87.5 = 350 (= 3 full + 1 al 50%)
    final = apply_promotion_to_price(promo, Decimal("100.00"), Decimal("4"))
    assert final * Decimal("4") == Decimal("350.00")


def test_apply_nth_unit_discount_second_unit_70pct():
    """Caso real del super: cada 2u, la 2da con 70% off. 2 unidades → promedio $1201.85."""
    promo = _make_promotion(
        promotion_type="nth_unit_discount", min_quantity=2, discount_value="70"
    )
    price = Decimal("1849.00")
    final = apply_promotion_to_price(promo, price, Decimal("2"))
    # Unit1=1849 + Unit2=554.70 = 2403.70 → promedio = 1201.85
    assert (final * Decimal("2")).quantize(Decimal("0.01")) == Decimal("2403.70")


def test_apply_nth_unit_discount_zero_pct_is_safe():
    """discount_value=0 no aplica descuento."""
    promo = _make_promotion(
        promotion_type="nth_unit_discount", min_quantity=2, discount_value="0"
    )
    final = apply_promotion_to_price(promo, Decimal("100.00"), Decimal("2"))
    assert final == Decimal("100.00")


def test_apply_unknown_type_returns_unit_price_unchanged():
    promo = _make_promotion(promotion_type="invalido")
    final = apply_promotion_to_price(promo, Decimal("100.00"))
    assert final == Decimal("100.00")


def test_apply_buy_x_get_y_with_zero_free_quantity_is_safe():
    """free_quantity=0 o negativo no debe dar descuento ni dividir por cero."""
    promo = _make_promotion(
        promotion_type="buy_x_get_y", min_quantity=1, free_quantity=-1
    )
    final = apply_promotion_to_price(promo, Decimal("50.00"), Decimal("3"))
    assert final == Decimal("50.00")


# ──────────────────────────────────────────────────────────────────────────────
# apply_promotion_to_price — max_units_per_transaction (cap)
# ──────────────────────────────────────────────────────────────────────────────


def test_cap_percentage_exact_limit():
    """25% off, máx 8 u.: comprar 8 → todas reciben descuento."""
    promo = _make_promotion(
        promotion_type="percentage",
        discount_value="25",
        max_units_per_transaction=8,
    )
    # 8 unidades × $100 × 0.75 = $600 → precio unitario = $75
    final = apply_promotion_to_price(promo, Decimal("100.00"), Decimal("8"))
    assert final == Decimal("75.00")


def test_cap_percentage_over_limit():
    """25% off, máx 8 u.: comprar 10 → solo 8 reciben descuento."""
    promo = _make_promotion(
        promotion_type="percentage",
        discount_value="25",
        max_units_per_transaction=8,
    )
    # 8 a $75 + 2 a $100 = 600 + 200 = 800 → precio unitario = 80
    final = apply_promotion_to_price(promo, Decimal("100.00"), Decimal("10"))
    assert final == Decimal("80.00")


def test_cap_percentage_under_limit():
    """25% off, máx 8 u.: comprar 5 → todas reciben descuento (sin blend)."""
    promo = _make_promotion(
        promotion_type="percentage",
        discount_value="25",
        max_units_per_transaction=8,
    )
    final = apply_promotion_to_price(promo, Decimal("100.00"), Decimal("5"))
    assert final == Decimal("75.00")


def test_cap_fixed_amount_over_limit():
    """$20 off por unidad, máx 4 u.: comprar 6 → solo 4 reciben descuento."""
    promo = _make_promotion(
        promotion_type="fixed_amount",
        discount_value="20",
        max_units_per_transaction=4,
    )
    # 4 a $80 + 2 a $100 = 320 + 200 = 520 → unitario = 520/6 ≈ 86.666...
    final = apply_promotion_to_price(promo, Decimal("100.00"), Decimal("6"))
    expected = (Decimal("4") * Decimal("80") + Decimal("2") * Decimal("100")) / Decimal("6")
    assert final == expected


def test_cap_none_no_blend():
    """Sin cap (None): el descuento aplica a todas las unidades normalmente."""
    promo = _make_promotion(
        promotion_type="percentage",
        discount_value="10",
        max_units_per_transaction=None,
    )
    final = apply_promotion_to_price(promo, Decimal("100.00"), Decimal("100"))
    assert final == Decimal("90.00")


def test_cap_buy_x_get_y_over_limit():
    """3x2 con máx 6 u.: comprar 9 → solo primeras 6 acceden al lleva3paga2."""
    promo = _make_promotion(
        promotion_type="buy_x_get_y",
        min_quantity=3,
        free_quantity=1,
        max_units_per_transaction=6,
    )
    # Capped: 6 u. → floor(6/3)=2 grupos → 2 gratis → 4 pagadas → unit_price * (4/6)
    # discounted_unit_6 = 100 * (4/6) = 66.666...
    # remaining: 3 u. a $100
    # total = 6 * 66.666... + 3 * 100 = 400 + 300 = 700
    # unitario = 700/9 ≈ 77.777...
    final = apply_promotion_to_price(promo, Decimal("100.00"), Decimal("9"))
    discounted_unit_capped = Decimal("100") * (Decimal("4") / Decimal("6"))
    expected = (Decimal("6") * discounted_unit_capped + Decimal("3") * Decimal("100")) / Decimal("9")
    assert final == expected


def test_buy_x_get_y_subtotal_exact_no_rounding_artifact():
    """BUY_X_GET_Y: subtotal de 3u a $5.50 (1 gratis c/3) debe ser $11.00 exacto.

    Sin la corrección, _round_money(5.50 × 2/3) = 3.67 → 3.67 × 3 = $11.01.
    Con NUMERIC(10,4) el precio intermedio se guarda sin redondear y
    calculate_subtotal aplica el redondeo solo al total.
    """
    from app.utils.calculations import calculate_subtotal

    promo = _make_promotion(
        promotion_type="buy_x_get_y", min_quantity=3, free_quantity=1
    )
    unit_price = apply_promotion_to_price(promo, Decimal("5.50"), Decimal("3"))
    assert calculate_subtotal(Decimal("3"), unit_price) == Decimal("11.00")


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
