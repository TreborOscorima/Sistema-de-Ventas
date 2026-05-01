"""Helpers de pricing compartidos entre sale_service y el preview del carrito.

Este módulo es la **única fuente de verdad** para:

  * Lookup de override de precio por lista (PriceListItem).
  * Lookup de precio por volumen (PriceTier).
  * Match de promoción aplicable a un ítem (Promotion).

Los helpers son puros (no mutan el modelo, no incrementan ``current_uses``).
El caller decide cuándo aplicar efectos secundarios:

  - ``sale_service`` los usa al cobrar la venta, e incrementa ``current_uses``
    de la promoción aplicada en su propia sesión.
  - ``cart_mixin`` los usa para el feedback visual del carrito sin tocar nada
    en BD más allá del SELECT.

Mantener un único origen evita la divergencia silenciosa que causa que el
precio mostrado en el carrito difiera del cobrado al confirmar la venta.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func as _sql_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select


def sqla_func_upper(col):  # alias local para evitar import-shadow en lectura
    return _sql_func.upper(col)

from app.models.inventory import PriceTier, Product
from app.models.price_lists import PriceListItem
from app.models.promotions import Promotion, PromotionProduct, PromotionScope, PromotionType
from app.utils.timezone import utc_now_naive


# ─── Constantes ──────────────────────────────────────────────────────────────


class PriceSource(str):
    """Origen del ``base_price`` antes de aplicar promociones."""
    PRICE_LIST = "price_list"
    TIER = "tier"
    BASE = "base"


@dataclass
class PriceResolution:
    """Resultado de resolver el precio efectivo de un ítem.

    Attributes:
        base_price: Precio antes de aplicar promoción.
        final_price: Precio final tras aplicar promoción (== base si no hubo).
        source: Origen del ``base_price`` (price_list | tier | base).
        applied_promotion: Promoción aplicada, o None si no hubo match.
    """
    base_price: Decimal
    final_price: Decimal
    source: str
    applied_promotion: Optional[Promotion]


# ─── Helpers de lookup ───────────────────────────────────────────────────────


async def resolve_price_list_price(
    session: AsyncSession,
    *,
    product_id: int,
    variant_id: int | None,
    price_list_id: int,
    company_id: int,
    branch_id: int,
) -> Decimal | None:
    """Busca el override de precio en la lista del cliente.

    Prioriza la variante específica; si no existe, cae al producto base.
    Retorna ``None`` si la lista no contiene el producto/variante.
    """
    if variant_id:
        stmt = (
            select(PriceListItem)
            .where(PriceListItem.price_list_id == price_list_id)
            .where(PriceListItem.product_id == product_id)
            .where(PriceListItem.product_variant_id == variant_id)
            .where(PriceListItem.company_id == company_id)
            .where(PriceListItem.branch_id == branch_id)
        )
        item = (await session.exec(stmt)).first()
        if item:
            return Decimal(str(item.unit_price))

    stmt = (
        select(PriceListItem)
        .where(PriceListItem.price_list_id == price_list_id)
        .where(PriceListItem.product_id == product_id)
        .where(PriceListItem.product_variant_id.is_(None))
        .where(PriceListItem.company_id == company_id)
        .where(PriceListItem.branch_id == branch_id)
    )
    item = (await session.exec(stmt)).first()
    if item:
        return Decimal(str(item.unit_price))
    return None


async def resolve_price_tier_price(
    session: AsyncSession,
    *,
    product_id: int | None,
    variant_id: int | None,
    quantity: Decimal,
    company_id: int,
    branch_id: int,
) -> Decimal | None:
    """Retorna el precio del tier que aplica a la cantidad solicitada.

    Busca primero por variante; si no aplica, por producto. El tier elegido
    es el de mayor ``min_quantity`` que sea ``<= quantity``.
    """
    base_filters = (
        (PriceTier.company_id == company_id),
        (PriceTier.branch_id == branch_id),
        (PriceTier.min_quantity <= quantity),
    )
    if variant_id:
        stmt = (
            select(PriceTier)
            .where(PriceTier.product_variant_id == variant_id)
            .where(*base_filters)
            .order_by(PriceTier.min_quantity.desc())
        )
        tier = (await session.exec(stmt)).first()
        if tier and tier.unit_price is not None:
            return Decimal(str(tier.unit_price))

    if product_id:
        stmt = (
            select(PriceTier)
            .where(PriceTier.product_id == product_id)
            .where(*base_filters)
            .order_by(PriceTier.min_quantity.desc())
        )
        tier = (await session.exec(stmt)).first()
        if tier and tier.unit_price is not None:
            return Decimal(str(tier.unit_price))

    return None


# ─── Promociones ─────────────────────────────────────────────────────────────


async def find_applicable_promotion(
    session: AsyncSession,
    *,
    product_id: int,
    category: str | None,
    quantity: Decimal,
    company_id: int,
    branch_id: int,
    now: datetime | None = None,
    lock_for_update: bool = False,
    coupon_code: str | None = None,
    cart_subtotal: Decimal | None = None,
) -> Promotion | None:
    """Retorna la promoción más específica aplicable al ítem, o None.

    Jerarquía: cupón ingresado > PRODUCT > CATEGORY > ALL.
    Filtra por vigencia, ``min_quantity``, ``max_uses``, día/banda horaria,
    y opcionalmente por ``min_cart_amount`` (umbral de subtotal del carrito).
    **No muta** el modelo.

    ``coupon_code``: cuando se pasa, se incluyen además las promos cuyo
    ``coupon_code`` coincide (case-insensitive). Promos con ``coupon_code``
    *sin* haberlo ingresado quedan excluidas. Las promos con cupón aplicable
    ganan prioridad sobre las automáticas para el mismo ítem.

    ``cart_subtotal``: subtotal del carrito (sumatoria de ``qty × base_price``
    pre-promo). Cuando se omite (None) las promos con ``min_cart_amount > 0``
    se descartan para evitar disparar mal por falta de contexto. Cuando se
    pasa explícitamente Decimal("0"), las promos con umbral > 0 también se
    descartan. Promos con ``min_cart_amount == 0`` siempre pasan este filtro.

    ``lock_for_update``: cuando ``True`` agrega ``FOR UPDATE`` al SELECT para
    serializar el match bajo concurrencia (caller debe estar en transacción).
    Útil al cobrar la venta efectiva; innecesario para preview del carrito.
    """
    effective_now = now or utc_now_naive()
    normalized_coupon = (coupon_code or "").strip().upper() or None

    today_start = effective_now.replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = (
        select(Promotion)
        .where(Promotion.company_id == company_id)
        .where(Promotion.branch_id == branch_id)
        .where(Promotion.is_active == True)  # noqa: E712 — SQL boolean
        .where(Promotion.starts_at <= effective_now)
        .where(Promotion.ends_at >= today_start)
    )

    if normalized_coupon is None:
        # Sin cupón ingresado: solo promos automáticas.
        stmt = stmt.where(Promotion.coupon_code.is_(None))
    else:
        # Con cupón: automáticas + las que matcheen el código.
        stmt = stmt.where(
            (Promotion.coupon_code.is_(None))
            | (sqla_func_upper(Promotion.coupon_code) == normalized_coupon)
        )

    # Ordenar para que las con cupón salgan primero (ganan prioridad), luego
    # por scope (PRODUCT > CATEGORY > ALL).
    stmt = stmt.order_by(
        Promotion.coupon_code.is_(None).asc(),  # None al final
        Promotion.scope.desc(),
    )

    if lock_for_update:
        stmt = stmt.with_for_update()
    promotions = (await session.exec(stmt)).all()

    # Pre-cargar product_ids multi-producto para promos con scope=PRODUCT.
    # Evita N+1: una sola query antes del loop.
    product_scope_ids = [p.id for p in promotions if p.scope == PromotionScope.PRODUCT]
    product_ids_by_promo: dict[int, set[int]] = {}
    if product_scope_ids:
        pp_rows = (await session.exec(
            select(PromotionProduct).where(
                PromotionProduct.promotion_id.in_(product_scope_ids)
            )
        )).all()
        for pp in pp_rows:
            product_ids_by_promo.setdefault(pp.promotion_id, set()).add(pp.product_id)

    for promo in promotions:
        # Defensa: si la promo tiene cupón y el caller no lo ingresó (o es
        # distinto), descartar. La query SQL ya filtra esto, pero el guard en
        # Python facilita los tests con mocks.
        promo_coupon = (getattr(promo, "coupon_code", None) or "").strip().upper() or None
        if promo_coupon is not None and promo_coupon != normalized_coupon:
            continue

        if promo.max_uses is not None and (promo.current_uses or 0) >= promo.max_uses:
            continue
        if quantity < Decimal(str(promo.min_quantity)):
            continue

        # Filtro por umbral de subtotal del carrito. getattr defensivo para
        # tolerar mocks legacy y filas pre-migración (default 0 = sin umbral).
        # Si el caller no pasó cart_subtotal pero la promo exige uno, descartar
        # antes que aplicar mal: mejor no dar el descuento que cobrarlo
        # incorrectamente.
        min_cart = getattr(promo, "min_cart_amount", None)
        min_cart_dec = Decimal(str(min_cart or 0))
        if min_cart_dec > 0:
            if cart_subtotal is None:
                continue
            if Decimal(str(cart_subtotal)) < min_cart_dec:
                continue

        # Filtro por día de semana (bitmask Mon=1..Sun=64). getattr defensivo
        # para tolerar mocks legacy y filas pre-migración (default 127).
        mask = getattr(promo, "weekdays_mask", 127) or 127
        weekday_bit = 1 << effective_now.weekday()
        if not (mask & weekday_bit):
            continue

        # Filtro por banda horaria. Si time_from > time_to, el rango cruza
        # medianoche y se evalúa como unión (>= from OR <= to).
        time_from = getattr(promo, "time_from", None)
        time_to = getattr(promo, "time_to", None)
        if time_from is not None and time_to is not None:
            cur_t = effective_now.time()
            if time_from <= time_to:
                in_window = time_from <= cur_t <= time_to
            else:
                in_window = cur_t >= time_from or cur_t <= time_to
            if not in_window:
                continue

        applies = False
        if promo.scope == PromotionScope.ALL:
            applies = True
        elif promo.scope == PromotionScope.PRODUCT:
            allowed = product_ids_by_promo.get(promo.id)
            if allowed:
                applies = product_id in allowed
            else:
                # Fallback legacy: promo sin filas en join-table
                applies = promo.product_id == product_id
        elif promo.scope == PromotionScope.CATEGORY and (promo.category or "") == (category or ""):
            applies = True

        if applies:
            return promo
    return None


def apply_promotion_to_price(promo: Promotion, unit_price: Decimal) -> Decimal:
    """Calcula el precio unitario tras aplicar la promoción.

    Función pura: no muta ``promo`` ni el caller. El redondeo queda a cargo
    del caller (cada capa tiene su propia política de quantize).
    """
    disc_val = Decimal(str(promo.discount_value or 0))

    if promo.promotion_type == PromotionType.PERCENTAGE:
        factor = (Decimal("100") - disc_val) / Decimal("100")
        return unit_price * factor

    if promo.promotion_type == PromotionType.FIXED_AMOUNT:
        return max(Decimal("0"), unit_price - disc_val)

    if promo.promotion_type == PromotionType.BUY_X_GET_Y:
        min_q = Decimal(str(promo.min_quantity))
        free_q = Decimal(str(promo.free_quantity or 0))
        total_group = min_q + free_q
        if total_group > 0:
            return unit_price * (min_q / total_group)

    return unit_price


# ─── Resolución compuesta ────────────────────────────────────────────────────


async def resolve_effective_price(
    session: AsyncSession,
    *,
    product: Product,
    variant_id: int | None,
    quantity: Decimal,
    company_id: int,
    branch_id: int,
    client_price_list_id: int | None,
    now: datetime | None = None,
    coupon_code: str | None = None,
    cart_subtotal: Decimal | None = None,
) -> PriceResolution:
    """Resuelve el precio efectivo de un ítem aplicando la jerarquía completa.

    Orden de precedencia para ``base_price``:
      1. PriceListItem (si el cliente tiene lista asignada).
      2. PriceTier (precio por volumen).
      3. ``product.sale_price``.

    Luego intenta aplicar una promoción para producir ``final_price``.
    No incrementa ``current_uses``: el caller debe hacerlo si va a registrar
    una venta efectiva.
    """
    base_price: Decimal | None = None
    source = PriceSource.BASE

    if client_price_list_id:
        pl_price = await resolve_price_list_price(
            session,
            product_id=product.id,
            variant_id=variant_id,
            price_list_id=client_price_list_id,
            company_id=company_id,
            branch_id=branch_id,
        )
        if pl_price is not None and pl_price > 0:
            base_price = pl_price
            source = PriceSource.PRICE_LIST

    if base_price is None:
        tier_price = await resolve_price_tier_price(
            session,
            product_id=product.id,
            variant_id=variant_id,
            quantity=quantity,
            company_id=company_id,
            branch_id=branch_id,
        )
        if tier_price is not None and tier_price > 0:
            base_price = tier_price
            source = PriceSource.TIER

    if base_price is None:
        base_price = Decimal(str(product.sale_price or 0))
        source = PriceSource.BASE

    promo = await find_applicable_promotion(
        session,
        product_id=product.id,
        category=product.category,
        quantity=quantity,
        company_id=company_id,
        branch_id=branch_id,
        now=now,
        coupon_code=coupon_code,
        cart_subtotal=cart_subtotal,
    )
    final_price = apply_promotion_to_price(promo, base_price) if promo else base_price

    return PriceResolution(
        base_price=base_price,
        final_price=final_price,
        source=source,
        applied_promotion=promo,
    )
