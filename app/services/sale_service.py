"""Servicio de Ventas - Lógica de negocio principal.

Este módulo contiene la lógica central para procesar ventas,
incluyendo:

- Validación de stock y productos
- Cálculo de totales y redondeo monetario
- Procesamiento de pagos (efectivo, tarjeta, billetera, mixto)
- Ventas a crédito con plan de cuotas
- Integración con reservas de canchas
- Registro en caja (CashboxLog) y movimientos de stock

Clases principales:
    SaleService: Servicio estático con el método principal `process_sale`
    SaleProcessResult: Dataclass con el resultado de una venta procesada
    StockError: Excepción específica para errores de inventario

Ejemplo de uso::

    from app.services.sale_service import SaleService, StockError
    
    async with get_async_session() as session:
        try:
            result = await SaleService.process_sale(
                session=session,
                user_id=1,
                company_id=1,
                items=[...],
                payment_data=payment_info,
            )
            await session.commit()
        except StockError as e:
            await session.rollback()
            # Manejar error de stock
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

from sqlmodel import select
from sqlalchemy import func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession  # ✅ IMPORTANTE

from app.constants import CASHBOX_INCOME_ACTIONS
from app.enums import PaymentMethodType, ReservationStatus, SaleStatus
from app.models import (
    CashboxLog,
    Client,
    FieldReservation,
    PaymentMethod,
    PriceTier,
    Product,
    ProductBatch,
    ProductVariant,
    Sale,
    SaleInstallment,
    SaleItem,
    SalePayment,
    Unit,
)
from app.schemas.sale_schemas import PaymentInfoDTO, SaleItemDTO
from app.utils.calculations import calculate_subtotal, calculate_total
from app.utils.db import get_async_session as get_session
from app.utils.logger import get_logger

# Nota: get_session es un alias de get_async_session para uso interno.

QTY_DECIMAL_QUANT = Decimal("0.0001")
QTY_DISPLAY_QUANT = Decimal("0.01")
QTY_INTEGER_QUANT = Decimal("1")

logger = get_logger("SaleService")


def _apply_company_filter(query, model, company_id: int | None):
    if not company_id:
        return query
    company_attr = getattr(model, "company_id", None)
    if company_attr is None:
        return query
    return query.where(company_attr == company_id)


def _apply_branch_filter(query, model, branch_id: int | None):
    if not branch_id:
        return query
    branch_attr = getattr(model, "branch_id", None)
    if branch_attr is None:
        return query
    return query.where(branch_attr == branch_id)


def _apply_tenant_filters(query, model, company_id: int | None, branch_id: int | None):
    query = _apply_company_filter(query, model, company_id)
    return _apply_branch_filter(query, model, branch_id)

def _variant_label(variant: ProductVariant) -> str:
    parts = []
    if variant.size:
        parts.append(str(variant.size).strip())
    if variant.color:
        parts.append(str(variant.color).strip())
    return " ".join([p for p in parts if p])


def _normalize_cashbox_action(action: str | None) -> str:
    value = (action or "").replace("_", " ").strip()
    if not value:
        return "Movimiento"
    if value.islower():
        return value.title()
    return value


def _compact_notes(text: str, max_length: int = 90) -> str:
    if not text:
        return ""
    compact = " ".join(text.split())
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 3].rstrip() + "..."


def _extract_detail_from_notes(
    notes: str,
    action_label: str,
) -> str:
    raw = " ".join((notes or "").split()).strip()
    if not raw:
        return ""

    action_lower = (action_label or "").strip().lower()
    detail = raw

    if detail.startswith("#") and ":" in detail:
        detail = detail.split(":", 1)[1].strip()
    elif detail.lower().startswith("inicial #") and "(" in detail and ")" in detail:
        start = detail.find("(") + 1
        end = detail.find(")", start)
        if end > start:
            detail = detail[start:end].strip()

    lowered = detail.lower()
    if " - cliente" in lowered:
        detail = detail[: lowered.index(" - cliente")].strip()
    elif "cliente:" in lowered:
        detail = detail[: lowered.index("cliente:")].strip()

    if action_lower and detail.lower().startswith(action_lower):
        detail = detail[len(action_label):].lstrip(" -:").strip()

    return detail


async def get_recent_activity(
    session: AsyncSession,
    branch_id: int,
    limit: int = 15,
    company_id: int | None = None,
) -> list[dict[str, Any]]:
    """Obtiene los movimientos recientes de caja para una sucursal."""
    if not branch_id:
        return []
    limit_value = int(limit) if limit else 15
    if limit_value < 1:
        limit_value = 15

    query = (
        select(CashboxLog, Sale, Client)
        .join(Sale, CashboxLog.sale_id == Sale.id, isouter=True)
        .join(Client, Sale.client_id == Client.id, isouter=True)
        .where(CashboxLog.branch_id == branch_id)
        .where(CashboxLog.is_voided == False)
        .where(CashboxLog.action.in_(CASHBOX_INCOME_ACTIONS))
        .order_by(desc(CashboxLog.timestamp))
        .limit(limit_value)
    )
    if company_id:
        query = query.where(CashboxLog.company_id == company_id)

    rows = (await session.exec(query)).all()
    sale_ids = list({log.sale_id for log, _sale, _client in rows if log.sale_id})
    items_by_sale: dict[int, list[dict[str, Any]]] = {}
    if sale_ids:
        items_query = select(SaleItem).where(SaleItem.sale_id.in_(sale_ids))
        items_query = _apply_tenant_filters(
            items_query, SaleItem, company_id, branch_id
        )
        items_query = items_query.order_by(SaleItem.sale_id, SaleItem.id)
        sale_items = (await session.exec(items_query)).all()
        for item in sale_items:
            if not item.sale_id:
                continue
            items_by_sale.setdefault(item.sale_id, []).append(
                {
                    "description": item.product_name_snapshot
                    or item.product_barcode_snapshot
                    or "Producto",
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "subtotal": item.subtotal,
                }
            )
    results: list[dict[str, Any]] = []
    for log, sale, client in rows:
        action_label = _normalize_cashbox_action(log.action)
        payment_method = (log.payment_method or "").strip()
        detail = action_label
        if payment_method:
            detail = f"{detail} ({payment_method})"
        notes_detail = _extract_detail_from_notes(log.notes, action_label)
        detail_full = detail
        detail_short = detail
        if notes_detail:
            detail_full = f"{detail} - {notes_detail}"
            detail_short = f"{detail} - {_compact_notes(notes_detail)}"
        client_name = ""
        if client and client.name:
            client_name = client.name

        timestamp = log.timestamp
        time_display = ""
        timestamp_display = ""
        if timestamp:
            time_display = timestamp.strftime("%H:%M")
            timestamp_display = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        results.append(
            {
                "id": str(log.id),
                "timestamp": timestamp_display,
                "time": time_display,
                "detail_full": detail_full,
                "detail_short": detail_short,
                "client": client_name,
                "amount": float(log.amount or 0),
                "sale_id": str(log.sale_id) if log.sale_id else "",
                "items": items_by_sale.get(log.sale_id or 0, []),
            }
        )
    return results


def _adapt_product_payload(product: Product) -> dict[str, Any]:
    payload = {
        "id": product.id,
        "product_id": product.id,
        "variant_id": None,
        "is_variant": False,
        "barcode": product.barcode,
        "description": product.description,
        "category": product.category,
        "unit": product.unit,
        "sale_price": product.sale_price,
        "purchase_price": getattr(product, "purchase_price", None),
        "stock": product.stock,
    }
    if hasattr(product, "image"):
        payload["image"] = getattr(product, "image")
    if hasattr(product, "image_url"):
        payload["image_url"] = getattr(product, "image_url")
    if hasattr(product, "location"):
        payload["location"] = getattr(product, "location")
    return payload


def _adapt_variant_payload(
    variant: ProductVariant,
    parent: Product,
) -> dict[str, Any]:
    label = _variant_label(variant)
    description = parent.description
    if label:
        description = f"{parent.description} ({label})"
    payload = _adapt_product_payload(parent)
    payload.update(
        {
            "barcode": variant.sku,
            "description": description,
            "stock": variant.stock,
            "is_variant": True,
            "variant_id": variant.id,
            "product_id": parent.id,
        }
    )
    return payload


async def get_product_by_barcode(
    barcode: str | None,
    company_id: int | None,
    branch_id: int | None,
    session: AsyncSession | None = None,
) -> dict[str, Any] | None:
    """Busca un producto por SKU (variante) o barcode (producto estándar)."""
    code = (barcode or "").strip()
    if not code:
        return None

    async def _run(current_session: AsyncSession) -> dict[str, Any] | None:
        variant_query = select(ProductVariant).where(ProductVariant.sku == code)
        variant = (
            await current_session.exec(
                _apply_tenant_filters(
                    variant_query, ProductVariant, company_id, branch_id
                )
            )
        ).first()
        if variant:
            parent_query = select(Product).where(
                Product.id == variant.product_id
            )
            parent = (
                await current_session.exec(
                    _apply_tenant_filters(
                        parent_query, Product, company_id, branch_id
                    )
                )
            ).first()
            if parent:
                return _adapt_variant_payload(variant, parent)

        product_query = select(Product).where(Product.barcode == code)
        product = (
            await current_session.exec(
                _apply_tenant_filters(
                    product_query, Product, company_id, branch_id
                )
            )
        ).first()
        if product:
            return _adapt_product_payload(product)
        return None

    if session is not None:
        return await _run(session)
    async with get_session() as current_session:
        return await _run(current_session)


async def search_products(
    query: str | None,
    company_id: int | None,
    branch_id: int | None,
    *,
    limit: int = 10,
    session: AsyncSession | None = None,
) -> list[dict[str, Any]]:
    term = (query or "").strip()
    if not term:
        return []
    like_search = f"%{term}%"

    async def _run(current_session: AsyncSession) -> list[dict[str, Any]]:
        product_query = select(Product).where(
            or_(
                Product.description.ilike(like_search),
                Product.barcode.ilike(like_search),
            )
        )
        product_query = _apply_tenant_filters(
            product_query, Product, company_id, branch_id
        )
        products = (
            await current_session.exec(product_query.limit(limit))
        ).all()

        variant_query = (
            select(ProductVariant, Product)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(
                or_(
                    ProductVariant.sku.ilike(like_search),
                    ProductVariant.size.ilike(like_search),
                    ProductVariant.color.ilike(like_search),
                    Product.description.ilike(like_search),
                    func.concat(
                        Product.description,
                        " (",
                        func.coalesce(ProductVariant.size, ""),
                        " ",
                        func.coalesce(ProductVariant.color, ""),
                        ")",
                    ).ilike(like_search),
                )
            )
        )
        variant_query = _apply_tenant_filters(
            variant_query, ProductVariant, company_id, branch_id
        )
        variant_query = _apply_tenant_filters(
            variant_query, Product, company_id, branch_id
        )
        variant_rows = (
            await current_session.exec(variant_query.limit(limit))
        ).all()

        results: list[dict[str, Any]] = [
            _adapt_product_payload(product) for product in products
        ]
        for variant, parent in variant_rows:
            if parent:
                results.append(_adapt_variant_payload(variant, parent))
        return results

    if session is not None:
        return await _run(session)
    async with get_session() as current_session:
        return await _run(current_session)


async def calculate_item_price(
    product_id: int | None,
    qty: Decimal,
    company_id: int | None,
    branch_id: int | None,
    session: AsyncSession | None = None,
) -> Decimal:
    if not product_id:
        return Decimal("0.00")

    async def _run(current_session: AsyncSession) -> Decimal:
        tier_query = select(PriceTier).where(
            PriceTier.product_id == product_id,
            PriceTier.min_quantity <= qty,
        )
        tier_query = _apply_tenant_filters(
            tier_query, PriceTier, company_id, branch_id
        )
        tier_query = tier_query.order_by(PriceTier.min_quantity.desc())
        tier = (await current_session.exec(tier_query)).first()
        if tier and tier.unit_price is not None:
            return _round_money(tier.unit_price)

        product_query = select(Product).where(Product.id == product_id)
        product = (
            await current_session.exec(
                _apply_tenant_filters(
                    product_query, Product, company_id, branch_id
                )
            )
        ).first()
        if not product:
            return Decimal("0.00")
        return _round_money(product.sale_price)

    if session is not None:
        return await _run(session)
    async with get_session() as current_session:
        return await _run(current_session)


async def get_available_stock(
    product_id: int | None,
    variant_id: int | None,
    company_id: int | None,
    branch_id: int | None,
    session: AsyncSession | None = None,
) -> Decimal:
    async def _run(current_session: AsyncSession) -> Decimal:
        product = None
        variant = None
        if variant_id:
            variant_query = select(ProductVariant).where(
                ProductVariant.id == variant_id
            )
            variant = (
                await current_session.exec(
                    _apply_tenant_filters(
                        variant_query, ProductVariant, company_id, branch_id
                    )
                )
            ).first()
            if variant and variant.product_id:
                product_query = select(Product).where(
                    Product.id == variant.product_id
                )
                product = (
                    await current_session.exec(
                        _apply_tenant_filters(
                            product_query, Product, company_id, branch_id
                        )
                    )
                ).first()

        if product is None and product_id:
            product_query = select(Product).where(Product.id == product_id)
            product = (
                await current_session.exec(
                    _apply_tenant_filters(
                        product_query, Product, company_id, branch_id
                    )
                )
            ).first()

        allows_decimal = False
        unit_name = getattr(product, "unit", None) if product else None
        if unit_name:
            unit_query = select(Unit).where(Unit.name == unit_name)
            unit_query = _apply_tenant_filters(unit_query, Unit, company_id, branch_id)
            unit = (await current_session.exec(unit_query)).first()
            if unit is not None:
                allows_decimal = bool(unit.allows_decimal)

        batch_query = None
        if variant:
            batch_query = select(ProductBatch).where(
                ProductBatch.product_variant_id == variant.id
            )
        elif product:
            batch_query = select(ProductBatch).where(
                ProductBatch.product_id == product.id
            )

        batches: list[ProductBatch] = []
        if batch_query is not None:
            batch_query = batch_query.where(ProductBatch.stock > 0)
            batch_query = _apply_tenant_filters(
                batch_query, ProductBatch, company_id, branch_id
            )
            batch_query = batch_query.order_by(
                ProductBatch.expiration_date.asc(), ProductBatch.id.asc()
            )
            batches = (await current_session.exec(batch_query)).all()

        if batches:
            return _sum_batch_stock(batches, allows_decimal)
        if variant:
            return _round_quantity(variant.stock, allows_decimal)
        if product:
            variant_sum_query = select(
                func.coalesce(func.sum(ProductVariant.stock), 0)
            ).where(ProductVariant.product_id == product.id)
            variant_sum_query = _apply_tenant_filters(
                variant_sum_query, ProductVariant, company_id, branch_id
            )
            variant_total = (await current_session.exec(variant_sum_query)).one()
            try:
                if Decimal(str(variant_total)) > 0:
                    return _round_quantity(variant_total, allows_decimal)
            except Exception:
                pass
            return _round_quantity(product.stock, allows_decimal)
        return Decimal("0")

    if session is not None:
        return await _run(session)
    async with get_session() as current_session:
        return await _run(current_session)


async def _get_price_tier(
    session: AsyncSession,
    *,
    product_id: int | None = None,
    variant_id: int | None = None,
    qty: Decimal,
    company_id: int | None,
    branch_id: int | None,
) -> PriceTier | None:
    if variant_id:
        query = select(PriceTier).where(PriceTier.product_variant_id == variant_id)
    else:
        query = select(PriceTier).where(PriceTier.product_id == product_id)
    query = query.where(PriceTier.min_quantity <= qty)
    query = _apply_tenant_filters(query, PriceTier, company_id, branch_id)
    query = query.order_by(PriceTier.min_quantity.desc())
    return (await session.exec(query)).first()


async def _calculate_item_price(
    session: AsyncSession,
    product: Product,
    variant: ProductVariant | None,
    qty: Decimal,
    company_id: int | None,
    branch_id: int | None,
) -> Decimal:
    tier = None
    if variant:
        tier = await _get_price_tier(
            session,
            variant_id=variant.id,
            qty=qty,
            company_id=company_id,
            branch_id=branch_id,
        )
    if tier is None:
        tier = await _get_price_tier(
            session,
            product_id=product.id,
            qty=qty,
            company_id=company_id,
            branch_id=branch_id,
        )
    if tier and tier.unit_price is not None:
        return _round_money(tier.unit_price)
    return _round_money(product.sale_price)


def _sum_batch_stock(
    batches: list[ProductBatch],
    allows_decimal: bool,
) -> Decimal:
    total = Decimal("0.0000")
    for batch in batches:
        total += _round_quantity(batch.stock, allows_decimal)
    return _round_quantity(total, allows_decimal)


def _deduct_from_batches(
    batches: list[ProductBatch],
    quantity: Decimal,
    allows_decimal: bool,
) -> list[ProductBatch]:
    remaining = _round_quantity(quantity, allows_decimal)
    used_batches: list[ProductBatch] = []
    for batch in batches:
        if remaining <= 0:
            break
        available = _round_quantity(batch.stock, allows_decimal)
        if available <= 0:
            continue
        deduct = min(available, remaining)
        batch.stock = _round_quantity(available - deduct, allows_decimal)
        remaining = _round_quantity(remaining - deduct, allows_decimal)
        used_batches.append(batch)
    if remaining > 0:
        raise StockError("Stock insuficiente en lotes para completar la venta.")
    return used_batches


class StockError(ValueError):
    """Excepción para errores relacionados con inventario.
    
    Se lanza cuando:
    - El producto no existe en inventario
    - El stock es insuficiente para la cantidad solicitada
    - Hay ambigüedad en la descripción del producto
    
    Attributes:
        args: Mensaje descriptivo del error
    """
    pass


@dataclass
class SaleProcessResult:
    """Resultado de una venta procesada exitosamente.
    
    Contiene toda la información necesaria para generar el recibo
    y actualizar la UI después de procesar una venta.
    
    Attributes:
        sale: Objeto Sale persistido en base de datos
        receipt_items: Lista de items formateados para el recibo
            Cada item contiene: description, quantity, unit, price, subtotal
        sale_total: Total de la venta en Decimal (precisión completa)
        sale_total_display: Total redondeado para mostrar (float)
        timestamp: Fecha/hora de la transacción
        payment_summary: Resumen del pago para mostrar en recibo
            Ej: "Efectivo S/ 50.00" o "Mixto: Efectivo + Yape"
        reservation_context: Datos de reserva si aplica, None si es venta directa
        reservation_balance: Saldo pendiente de reserva cobrado
        reservation_balance_display: Saldo de reserva formateado (float)
    """
    sale: Sale
    receipt_items: List[Dict[str, Any]]
    sale_total: Decimal
    sale_total_display: float
    timestamp: datetime.datetime
    payment_summary: str
    reservation_context: Dict[str, Any] | None
    reservation_balance: Decimal
    reservation_balance_display: float


def _to_decimal(value: Any) -> Decimal:
    """Convierte cualquier valor numérico a Decimal.
    
    Args:
        value: Valor a convertir (int, float, str, None)
        
    Returns:
        Decimal del valor, o Decimal(0) si es None/vacío
    """
    return Decimal(str(value or 0))


def _round_money(value: Any) -> Decimal:
    """Redondea un valor monetario a 2 decimales.
    
    Usa ROUND_HALF_UP para consistencia contable.
    
    Args:
        value: Monto a redondear
        
    Returns:
        Decimal redondeado a centavos (0.01)
    """
    return calculate_total([{"subtotal": value}], key="subtotal")


def _round_quantity(value: Any, allows_decimal: bool, display: bool = False) -> Decimal:
    if allows_decimal:
        quant = QTY_DISPLAY_QUANT if display else QTY_DECIMAL_QUANT
    else:
        quant = QTY_INTEGER_QUANT
    return _to_decimal(value).quantize(quant, rounding=ROUND_HALF_UP)


def _quantity_for_receipt(value: Any, allows_decimal: bool) -> float | int:
    rounded = _round_quantity(value, allows_decimal, display=True)
    if allows_decimal:
        return float(rounded)
    return int(rounded)


def _money_to_float(value: Decimal) -> float:
    return float(_round_money(value))


def _money_display(value: Decimal, currency_symbol: str | None = None) -> str:
    symbol = (currency_symbol or "").strip()
    if symbol:
        symbol = f"{symbol} "
    else:
        symbol = "S/ "
    return f"{symbol}{float(_round_money(value)):.2f}"


def _reservation_status_value(status: Any) -> str:
    if isinstance(status, ReservationStatus):
        return status.value
    return str(status or "").strip().lower()


def _method_type_from_kind(kind: str) -> PaymentMethodType:
    normalized = (kind or "").strip().lower()
    if normalized == "cash":
        return PaymentMethodType.cash
    if normalized == "debit":
        return PaymentMethodType.debit
    if normalized == "credit":
        return PaymentMethodType.credit
    if normalized == "yape":
        return PaymentMethodType.yape
    if normalized == "plin":
        return PaymentMethodType.plin
    if normalized == "transfer":
        return PaymentMethodType.transfer
    if normalized == "mixed":
        return PaymentMethodType.mixed
    if normalized == "card":
        return PaymentMethodType.credit
    if normalized == "wallet":
        return PaymentMethodType.yape
    return PaymentMethodType.other


def _card_method_type(card_type: str) -> PaymentMethodType:
    value = (card_type or "").strip().lower()
    if "deb" in value:
        return PaymentMethodType.debit
    return PaymentMethodType.credit


def _wallet_method_type(provider: str) -> PaymentMethodType:
    value = (provider or "").strip().lower()
    if "plin" in value:
        return PaymentMethodType.plin
    return PaymentMethodType.yape


def _allocate_mixed_payments(
    sale_total: Decimal,
    cash_amount: Decimal,
    card_amount: Decimal,
    wallet_amount: Decimal,
    card_type: PaymentMethodType,
    wallet_type: PaymentMethodType,
) -> list[tuple[PaymentMethodType, Decimal]]:
    remaining = _round_money(sale_total)
    allocations: list[tuple[PaymentMethodType, Decimal]] = []

    def apply(amount: Decimal, method_type: PaymentMethodType) -> None:
        nonlocal remaining
        amount = _round_money(amount)
        if amount <= 0 or remaining <= 0:
            return
        applied = min(amount, remaining)
        allocations.append((method_type, _round_money(applied)))
        remaining = _round_money(remaining - applied)

    apply(card_amount, card_type)
    apply(wallet_amount, wallet_type)
    apply(cash_amount, PaymentMethodType.cash)

    if remaining > 0:
        if allocations:
            method_type, amount = allocations[0]
            allocations[0] = (method_type, _round_money(amount + remaining))
        else:
            allocations.append((PaymentMethodType.other, _round_money(sale_total)))

    return allocations


def _build_sale_payments(
    payment_data: PaymentInfoDTO,
    sale_total: Decimal,
) -> list[tuple[PaymentMethodType, Decimal]]:
    kind = (payment_data.method_kind or "other").strip().lower()
    if kind == "mixed":
        non_cash_kind = (payment_data.mixed.non_cash_kind or "").strip().lower()
        card_type = _card_method_type(payment_data.card.type)
        wallet_type = _wallet_method_type(
            payment_data.wallet.provider or payment_data.wallet.choice
        )
        if non_cash_kind in {"debit", "credit", "transfer"}:
            card_type = _method_type_from_kind(non_cash_kind)
        elif non_cash_kind in {"yape", "plin"}:
            wallet_type = _method_type_from_kind(non_cash_kind)
        return _allocate_mixed_payments(
            sale_total,
            _to_decimal(payment_data.mixed.cash),
            _to_decimal(payment_data.mixed.card),
            _to_decimal(payment_data.mixed.wallet),
            card_type,
            wallet_type,
        )
    if kind == "card":
        method_type = _card_method_type(payment_data.card.type)
    elif kind == "wallet":
        method_type = _wallet_method_type(
            payment_data.wallet.provider or payment_data.wallet.choice
        )
    else:
        method_type = _method_type_from_kind(kind)
    if method_type == PaymentMethodType.cash:
        amount = min(_to_decimal(payment_data.cash.amount), sale_total)
    else:
        amount = sale_total
    return [(method_type, _round_money(amount))]


def _payment_method_code(method_type: PaymentMethodType) -> str | None:
    if method_type == PaymentMethodType.cash:
        return "cash"
    if method_type == PaymentMethodType.yape:
        return "yape"
    if method_type == PaymentMethodType.plin:
        return "plin"
    if method_type == PaymentMethodType.transfer:
        return "transfer"
    if method_type == PaymentMethodType.debit:
        return "debit_card"
    if method_type == PaymentMethodType.credit:
        return "credit_card"
    return None


def _split_installments(total: Decimal, count: int) -> list[Decimal]:
    """Divide un monto total en cuotas iguales.
    
    Distribuye cualquier diferencia por redondeo en las primeras cuotas
    para garantizar que la suma exacta sea igual al total.
    
    Args:
        total: Monto total a dividir
        count: Número de cuotas
        
    Returns:
        Lista de montos por cuota (Decimal)
        
    Example:
        >>> _split_installments(Decimal("100.00"), 3)
        [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]
    """
    total = _round_money(total)
    if count <= 0:
        return []
    quant = Decimal("0.01")
    base = (total / count).quantize(quant, rounding=ROUND_HALF_UP)
    amounts = [base for _ in range(count)]
    distributed = (base * count).quantize(quant, rounding=ROUND_HALF_UP)
    remainder = (total - distributed).quantize(quant, rounding=ROUND_HALF_UP)
    if remainder != 0:
        step = quant if remainder > 0 else -quant
        steps = int(abs(remainder / quant))
        for i in range(steps):
            amounts[i] = (amounts[i] + step).quantize(
                quant, rounding=ROUND_HALF_UP
            )
    return amounts


class SaleService:
    """Servicio para procesamiento de ventas.
    
    Proporciona métodos estáticos para procesar ventas completas,
    incluyendo validación, descuento de stock, registro de pagos
    y generación de datos para recibos.
    
    Todos los métodos son asíncronos y requieren una sesión de BD.
    """

    @staticmethod
    async def get_product_by_barcode(
        barcode: str | None,
        company_id: int | None,
        branch_id: int | None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any] | None:
        return await get_product_by_barcode(
            barcode,
            company_id,
            branch_id,
            session=session,
        )

    @staticmethod
    async def search_products(
        query: str | None,
        company_id: int | None,
        branch_id: int | None,
        *,
        limit: int = 10,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        return await search_products(
            query,
            company_id,
            branch_id,
            limit=limit,
            session=session,
        )

    @staticmethod
    async def calculate_item_price(
        product_id: int | None,
        qty: Decimal,
        company_id: int | None,
        branch_id: int | None,
        session: AsyncSession | None = None,
    ) -> Decimal:
        return await calculate_item_price(
            product_id,
            qty,
            company_id,
            branch_id,
            session=session,
        )

    @staticmethod
    async def get_available_stock(
        product_id: int | None,
        variant_id: int | None,
        company_id: int | None,
        branch_id: int | None,
        session: AsyncSession | None = None,
    ) -> Decimal:
        return await get_available_stock(
            product_id,
            variant_id,
            company_id,
            branch_id,
            session=session,
        )

    @staticmethod
    async def get_recent_activity(
        session: AsyncSession,
        branch_id: int,
        limit: int = 15,
        company_id: int | None = None,
    ) -> list[dict[str, Any]]:
        return await get_recent_activity(
            session=session,
            branch_id=branch_id,
            limit=limit,
            company_id=company_id,
        )
    
    @staticmethod
    async def process_sale(
        session: AsyncSession | None,
        user_id: int | None,
        company_id: int | None,
        branch_id: int | None,
        items: list[SaleItemDTO],
        payment_data: PaymentInfoDTO,
        reservation_id: str | None = None,
        currency_symbol: str | None = None,
    ) -> SaleProcessResult:
        """Procesa una venta completa de forma atómica.
        
        Este es el método principal del servicio. Realiza todas las
        validaciones y operaciones necesarias para completar una venta:
        
        1. Valida método de pago seleccionado
        2. Verifica reserva asociada (si aplica)
        3. Valida existencia y stock de productos
        4. Bloquea productos para evitar race conditions
        5. Calcula totales con precisión decimal
        6. Crea registro de venta (Sale)
        7. Crea items de venta (SaleItem)
        8. Registra pagos (SalePayment)
        9. Descuenta stock y registra movimientos
        10. Crea registro en caja (CashboxLog)
        11. Para créditos: crea plan de cuotas (SaleInstallment)
        
        Args:
            session: Sesión async de SQLAlchemy (debe manejarse externamente)
            user_id: ID del usuario que realiza la venta (puede ser None)
            company_id: ID de la empresa (tenant) del usuario actual
            items: Lista de productos a vender (SaleItemDTO)
            payment_data: Información de pago (PaymentInfoDTO)
            reservation_id: ID de reserva asociada (opcional)
            
        Returns:
            SaleProcessResult con todos los datos de la venta procesada
            
        Raises:
            ValueError: Para errores de validación (pago, cliente, montos)
            StockError: Para errores de inventario (stock insuficiente, producto no encontrado)
            
        Note:
            El commit/rollback debe manejarse externamente.
            En caso de error, se recomienda hacer rollback de la sesión.
            
        Example::
        
            result = await SaleService.process_sale(
                session=session,
                user_id=current_user.id,
                company_id=current_user.company_id,
                items=[SaleItemDTO(description="Producto", quantity=2, price=10.0, unit="Unidad")],
                payment_data=PaymentInfoDTO(method="Efectivo", method_kind="cash"),
            )
            await session.commit()
            print(f"Venta #{result.sale.id} - Total: {result.sale_total_display}")
        """
        if session is None:
            async with get_session() as managed_session:
                return await SaleService.process_sale(
                    session=managed_session,
                    user_id=user_id,
                    company_id=company_id,
                    branch_id=branch_id,
                    items=items,
                    payment_data=payment_data,
                    reservation_id=reservation_id,
                    currency_symbol=currency_symbol,
                )

        payment_method = (payment_data.method or "").strip()
        symbol = (currency_symbol or "").strip()
        if symbol:
            symbol = f"{symbol} "
        else:
            symbol = "S/ "
        if not payment_method:
            raise ValueError("Seleccione un metodo de pago.")

        if not company_id:
            raise ValueError("Empresa no definida para procesar la venta.")
        company_id = int(company_id)
        if not branch_id:
            raise ValueError("Sucursal no definida para procesar la venta.")
        branch_id = int(branch_id)

        all_methods = (
            await session.exec(
                _apply_tenant_filters(
                    select(PaymentMethod), PaymentMethod, company_id, branch_id
                )
            )
        ).all()
        methods_map = {
            (method.code or "").strip().lower(): method.id
            for method in all_methods
            if method.code
        }

        def resolve_payment_method_id(code: str | None) -> int | None:
            if not code:
                return None
            return methods_map.get(code.strip().lower())

        # --- AQUI EMPIEZA LA LÓGICA DE NEGOCIO ---
        # Ya no usamos 'async with get_async_session()' porque 'session' ya llegó como argumento.

        reservation = None
        reservation_balance = Decimal("0.00")
        if reservation_id:
            reservation_query = select(FieldReservation).where(
                FieldReservation.id == reservation_id
            )
            reservation = (
                await session.exec(
                    _apply_tenant_filters(
                        reservation_query,
                        FieldReservation,
                        company_id,
                        branch_id,
                    )
                )
            ).first()
            if reservation:
                status_value = _reservation_status_value(reservation.status)
                if status_value in {
                    ReservationStatus.cancelled.value,
                    ReservationStatus.refunded.value,
                    "cancelado",
                    "eliminado",
                }:
                    raise ValueError(
                        "No se puede cobrar una reserva cancelada o eliminada."
                    )
            if reservation:
                raw_balance = reservation.total_amount - reservation.paid_amount
                if raw_balance < 0:
                    raw_balance = Decimal("0.00")
                reservation_balance = _round_money(raw_balance)

        if not items and reservation_balance <= Decimal("0.00"):
            if reservation:
                raise ValueError("La reserva ya esta pagada.")
            raise ValueError("No hay productos en la venta.")

        units = (
            await session.exec(
                _apply_tenant_filters(select(Unit), Unit, company_id, branch_id)
            )
        ).all()
        decimal_units = {
            u.name.strip().lower(): u.allows_decimal for u in units
        }

        product_snapshot: list[Dict[str, Any]] = []
        decimal_snapshot: list[Dict[str, Any]] = []
        pending_items: list[Dict[str, Any]] = []
        for item in items:
            description = (item.description or "").strip()
            if not description:
                raise ValueError("Producto sin descripcion.")
            unit = (item.unit or "").strip()
            allows_decimal = decimal_units.get(unit.lower(), False)
            quantity_receipt = _quantity_for_receipt(
                item.quantity, allows_decimal
            )
            quantity_db = _round_quantity(item.quantity, allows_decimal)
            if quantity_db <= 0:
                raise ValueError(
                    f"Cantidad invalida para {description}."
                )
            pending_items.append(
                {
                    "description": description,
                    "quantity": quantity_db,
                    "quantity_receipt": quantity_receipt,
                    "unit": unit,
                    "barcode": item.barcode or "",
                    "product_id": item.product_id,
                    "variant_id": getattr(item, "variant_id", None),
                    "allows_decimal": allows_decimal,
                }
            )

        descriptions: list[str] = []
        barcodes: list[str] = []
        product_ids: list[int] = []
        variant_ids: list[int] = []
        for item in pending_items:
            pid = item.get("product_id")
            if pid:
                product_ids.append(pid)
            vid = item.get("variant_id")
            if vid:
                variant_ids.append(vid)
            description = (item.get("description") or "").strip()
            if description:
                descriptions.append(description)
            barcode = (item.get("barcode") or "").strip()
            if barcode:
                barcodes.append(barcode)

        unique_product_ids = list(dict.fromkeys(product_ids))
        unique_variant_ids = list(dict.fromkeys(variant_ids))
        unique_descriptions = list(dict.fromkeys(descriptions))
        unique_barcodes = list(dict.fromkeys(barcodes))
        
        products_by_id: dict[int, Product] = {}
        products_by_description: dict[str, Product] = {}
        products_by_barcode: dict[str, Product] = {}
        ambiguous_descriptions: set[str] = set()
        filters = []
        
        if unique_product_ids:
            filters.append(Product.id.in_(unique_product_ids))
        if unique_barcodes:
            filters.append(Product.barcode.in_(unique_barcodes))
        if unique_descriptions:
            filters.append(Product.description.in_(unique_descriptions))
        
        if filters:
            if len(filters) == 1:
                query = select(Product).where(filters[0])
            else:
                query = select(Product).where(or_(*filters))
            query = _apply_tenant_filters(query, Product, company_id, branch_id)
            products = (await session.exec(query.with_for_update())).all()
            
            # Map products by all possible keys
            for product in products:
                # Map by ID
                if product.id:
                    products_by_id[product.id] = product
                
                # Map by Description
                description = (product.description or "").strip()
                if description:
                    if description in products_by_description:
                        ambiguous_descriptions.add(description)
                    else:
                        products_by_description[description] = product
                
                # Map by Barcode
                if product.barcode:
                    products_by_barcode[product.barcode] = product

            # Clean up ambiguous maps
            for description in ambiguous_descriptions:
                products_by_description.pop(description, None)

        variants_by_sku: dict[str, ProductVariant] = {}
        variants_by_id: dict[int, ProductVariant] = {}
        if unique_barcodes:
            variant_query = select(ProductVariant).where(
                ProductVariant.sku.in_(unique_barcodes)
            )
            variant_query = _apply_tenant_filters(
                variant_query, ProductVariant, company_id, branch_id
            )
            variants = (await session.exec(variant_query.with_for_update())).all()
            for variant in variants:
                if variant.sku:
                    variants_by_sku[variant.sku] = variant

        if unique_variant_ids:
            variant_id_query = select(ProductVariant).where(
                ProductVariant.id.in_(unique_variant_ids)
            )
            variant_id_query = _apply_tenant_filters(
                variant_id_query, ProductVariant, company_id, branch_id
            )
            variants = (
                await session.exec(variant_id_query.with_for_update())
            ).all()
            for variant in variants:
                if variant.id:
                    variants_by_id[variant.id] = variant

        missing_variant_ids = [
            pid for pid in unique_product_ids if pid not in products_by_id
        ]
        if missing_variant_ids:
            variant_id_query = select(ProductVariant).where(
                ProductVariant.id.in_(missing_variant_ids)
            )
            variant_id_query = _apply_tenant_filters(
                variant_id_query, ProductVariant, company_id, branch_id
            )
            variants = (
                await session.exec(variant_id_query.with_for_update())
            ).all()
            for variant in variants:
                if variant.id:
                    variants_by_id[variant.id] = variant

        variant_product_ids = {
            variant.product_id
            for variant in list(variants_by_sku.values())
            + list(variants_by_id.values())
            if variant.product_id
        }
        missing_variant_products = [
            pid for pid in variant_product_ids if pid not in products_by_id
        ]
        if missing_variant_products:
            missing_query = select(Product).where(
                Product.id.in_(missing_variant_products)
            )
            missing_query = _apply_tenant_filters(
                missing_query, Product, company_id, branch_id
            )
            extra_products = (
                await session.exec(missing_query.with_for_update())
            ).all()
            for product in extra_products:
                if product.id:
                    products_by_id[product.id] = product
                description = (product.description or "").strip()
                if description:
                    if description in products_by_description:
                        ambiguous_descriptions.add(description)
                    else:
                        products_by_description[description] = product
                if product.barcode:
                    products_by_barcode[product.barcode] = product
            for description in ambiguous_descriptions:
                products_by_description.pop(description, None)

        resolved_items: list[Dict[str, Any]] = []
        batch_cache: dict[tuple[str, int], list[ProductBatch]] = {}
        for item in pending_items:
            product = None
            variant = None

            # 1. Intentar búsqueda por ID de variante (más confiable para variantes)
            vid = item.get("variant_id")
            if vid:
                variant = variants_by_id.get(vid)
                if variant:
                    product = products_by_id.get(variant.product_id)

            # 2. Intentar búsqueda por ID (más confiable para productos)
            pid = item.get("product_id")
            if pid and not product:
                product = products_by_id.get(pid)
                if not product:
                    variant = variants_by_id.get(pid)
                    if variant:
                        product = products_by_id.get(variant.product_id)

            # 3. Intentar búsqueda por código de barras (SKU de variante)
            if not product:
                barcode = (item.get("barcode") or "").strip()
                if barcode:
                    variant = variants_by_sku.get(barcode)
                    if variant:
                        product = products_by_id.get(variant.product_id)

            # 4. Intentar búsqueda por código de barras (producto)
            if not product:
                barcode = (item.get("barcode") or "").strip()
                if barcode:
                    product = products_by_barcode.get(barcode)

            # 5. Intentar búsqueda por descripción
            if not product:
                description = item.get("description", "")
                if description in ambiguous_descriptions:
                    raise StockError(
                        f"Producto '{description}' tiene multiples coincidencias en inventario. "
                        "Use codigo de barras."
                    )
                product = products_by_description.get(description)

            # 5. Final validation
            if not product:
                identifier = ""
                if item.get("barcode"):
                    identifier = f"código {item['barcode']}"
                elif item.get("description"):
                    identifier = item["description"]
                else:
                    identifier = "desconocido"

                raise StockError(
                    f"Producto {identifier} no encontrado en inventario."
                )

            unit_price = await _calculate_item_price(
                session,
                product,
                variant,
                item["quantity"],
                company_id,
                branch_id,
            )
            if unit_price <= 0:
                raise ValueError(
                    f"Precio invalido para {item['description']}."
                )
            subtotal = calculate_subtotal(item["quantity"], unit_price)

            product_snapshot.append(
                {
                    "description": item["description"],
                    "quantity": item["quantity_receipt"],
                    "unit": item["unit"],
                    "price": _money_to_float(unit_price),
                    "subtotal": _money_to_float(subtotal),
                }
            )
            decimal_item = {
                "description": item["description"],
                "quantity": item["quantity"],
                "unit": item["unit"],
                "price": unit_price,
                "subtotal": subtotal,
                "barcode": item.get("barcode") or "",
                "product_id": product.id,
                "product_variant_id": variant.id if variant else None,
                "product_batch_id": None,
            }
            decimal_snapshot.append(decimal_item)

            # Cargar lotes (FEFO) si aplica
            cache_key = (
                ("variant", variant.id)
                if variant
                else ("product", product.id)
            )
            batches = batch_cache.get(cache_key)
            if batches is None:
                if variant:
                    batch_query = select(ProductBatch).where(
                        ProductBatch.product_variant_id == variant.id
                    )
                else:
                    batch_query = select(ProductBatch).where(
                        ProductBatch.product_id == product.id
                    )
                batch_query = batch_query.where(ProductBatch.stock > 0)
                batch_query = _apply_tenant_filters(
                    batch_query, ProductBatch, company_id, branch_id
                )
                batch_query = batch_query.order_by(
                    ProductBatch.expiration_date.is_(None),
                    ProductBatch.expiration_date.asc(),
                    ProductBatch.id.asc(),
                )
                batches = (
                    await session.exec(batch_query.with_for_update())
                ).all()
                batch_cache[cache_key] = batches

            allows_decimal = item["allows_decimal"]
            if batches:
                available_stock = _sum_batch_stock(batches, allows_decimal)
            elif variant:
                available_stock = _round_quantity(variant.stock, allows_decimal)
            else:
                available_stock = _round_quantity(product.stock, allows_decimal)

            if available_stock < item["quantity"]:
                raise StockError(
                    f"Stock insuficiente para {item['description']}."
                )

            resolved_items.append(
                {
                    "item": decimal_item,
                    "product": product,
                    "variant": variant,
                    "batches": batches,
                    "allows_decimal": allows_decimal,
                }
            )

        items_total = calculate_total(decimal_snapshot)
        sale_total = _round_money(items_total + reservation_balance)
        if sale_total <= Decimal("0.00"):
            raise ValueError("No hay importe para cobrar.")

        is_credit = bool(payment_data.is_credit)
        initial_payment = _round_money(payment_data.initial_payment)
        if initial_payment < 0:
            raise ValueError("Monto inicial invalido.")
        initial_payment_input = initial_payment

        kind = (payment_data.method_kind or "other").strip().lower()
        total_paid_now = Decimal("0.00")
        if kind == "cash":
            cash_amount = _to_decimal(payment_data.cash.amount)
            total_paid_now = _round_money(cash_amount)
            if not is_credit:
                if cash_amount <= 0 or cash_amount < sale_total:
                    message = (
                        payment_data.cash.message
                        or "Ingrese un monto valido en efectivo."
                    )
                    raise ValueError(message)
            elif cash_amount < 0:
                message = (
                    payment_data.cash.message
                    or "Ingrese un monto valido en efectivo."
                )
                raise ValueError(message)
        elif kind == "mixed":
            total_paid_now = _round_money(
                _to_decimal(payment_data.mixed.cash)
                + _to_decimal(payment_data.mixed.card)
                + _to_decimal(payment_data.mixed.wallet)
            )
            if not is_credit:
                if total_paid_now <= 0 or total_paid_now < sale_total:
                    message = (
                        payment_data.mixed.message
                        or "Complete los montos del pago mixto."
                    )
                    raise ValueError(message)
            elif total_paid_now < 0:
                message = (
                    payment_data.mixed.message
                    or "Complete los montos del pago mixto."
                )
                raise ValueError(message)
        else:
            if is_credit:
                total_paid_now = _round_money(initial_payment)
            else:
                total_paid_now = sale_total

        if (
            is_credit
            and initial_payment_input > Decimal("0.00")
            and total_paid_now <= Decimal("0.00")
        ):
            total_paid_now = initial_payment_input

        if is_credit and kind in {"cash", "mixed"} and initial_payment_input <= Decimal(
            "0.00"
        ):
            initial_payment = total_paid_now

        sale_payment_label = payment_method
        if is_credit:
            sale_payment_label = (
                "Crédito c/ Inicial"
                if initial_payment > Decimal("0.00")
                else "Crédito"
            )

        client = None
        installments_plan: list[tuple[datetime.datetime, Decimal]] = []
        financed_amount = Decimal("0.00")
        if is_credit:
            if payment_data.client_id is None:
                raise ValueError("Cliente requerido para venta a credito.")
            client_query = select(Client).where(Client.id == payment_data.client_id)
            client = (
                await session.exec(
                    _apply_tenant_filters(
                        client_query, Client, company_id, branch_id
                    )
                )
            ).first()
            if not client:
                raise ValueError("Cliente no encontrado.")
            credit_base = _round_money(sale_total - initial_payment)
            if credit_base < Decimal("0.00"):
                credit_base = Decimal("0.00")
            if _round_money(client.current_debt) + credit_base > _round_money(
                client.credit_limit
            ):
                raise ValueError("Limite de credito excedido.")

        try:
            timestamp = datetime.datetime.now()
            sale_total_display = _money_to_float(sale_total)
    
            new_sale = Sale(
                timestamp=timestamp,
                total_amount=sale_total,
                status=SaleStatus.completed,
                company_id=company_id,
                branch_id=branch_id,
                user_id=user_id,
            )
            if hasattr(Sale, "payment_method"):
                new_sale.payment_method = sale_payment_label
            if is_credit:
                new_sale.payment_condition = "credito"
                new_sale.client_id = client.id
            session.add(new_sale)
            await session.flush()
            await session.refresh(new_sale)
    
            paid_now_total = sale_total
            if is_credit:
                paid_now_total = total_paid_now
    
            payment_allocations = _build_sale_payments(payment_data, paid_now_total)
            valid_allocations = [
                (method_type, amount)
                for method_type, amount in payment_allocations
                if amount > 0
            ]
            for method_type, amount in valid_allocations:
                method_code = _payment_method_code(method_type)
                method_id = resolve_payment_method_id(method_code)
                session.add(
                    SalePayment(
                        sale_id=new_sale.id,
                        company_id=company_id,
                        branch_id=branch_id,
                        amount=amount,
                        method_type=method_type,
                        reference_code=None,
                        payment_method_id=method_id,
                        created_at=timestamp,
                    )
                )
    
            cashbox_amount = paid_now_total
            if is_credit and initial_payment_input > Decimal("0.00"):
                cashbox_amount = initial_payment_input
    
            if cashbox_amount > 0:
                cashbox_method_id = None
                main_payment_code = None
                if kind == "cash":
                    main_payment_code = "cash"
                elif kind == "card":
                    card_type = _card_method_type(payment_data.card.type)
                    main_payment_code = _payment_method_code(card_type)
                elif kind == "wallet":
                    wallet_type = _wallet_method_type(
                        payment_data.wallet.provider or payment_data.wallet.choice
                    )
                    main_payment_code = _payment_method_code(wallet_type)
                elif kind == "mixed":
                    if valid_allocations:
                        primary_method_type, _ = max(
                            valid_allocations, key=lambda item: item[1]
                        )
                        main_payment_code = _payment_method_code(primary_method_type)
                else:
                    main_payment_code = _payment_method_code(
                        _method_type_from_kind(kind)
                    )
                cashbox_method_id = resolve_payment_method_id(main_payment_code)
                action_label = "Venta"
                summary_items: list[str] = []
                if reservation is not None:
                    field_name = (reservation.field_name or "").strip()
                    if field_name:
                        summary_items.append(f"Alquiler {field_name}")
                    else:
                        summary_items.append("Alquiler")
                for item in decimal_snapshot:
                    description = (item.get("description") or "").strip()
                    if not description:
                        continue
                    qty_value = _to_decimal(item.get("quantity", 0))
                    if qty_value == qty_value.to_integral_value():
                        qty_display = str(int(qty_value))
                    else:
                        qty_display = format(qty_value.normalize(), "f").rstrip("0").rstrip(".")
                    summary_items.append(f"{description} (x{qty_display})")
                summary_text = ", ".join(summary_items)
                notes = f"#{new_sale.id}: {summary_text}"
                if is_credit:
                    action_label = "Inicial Credito"
                    client_name = ""
                    if client:
                        client_name = (client.name or "").strip() or f"ID {client.id}"
                    notes = f"Inicial #{new_sale.id} ({summary_text})"
                    if client_name:
                        notes = f"{notes} - Cliente {client_name}"
                if len(notes) > 250:
                    notes = notes[:250]
                session.add(
                    CashboxLog(
                        action=action_label,
                        amount=cashbox_amount,
                        payment_method=payment_method,
                        payment_method_id=cashbox_method_id,
                        notes=notes,
                        timestamp=timestamp,
                        company_id=company_id,
                        branch_id=branch_id,
                        user_id=user_id,
                        sale_id=new_sale.id,
                    )
                )
    
            if is_credit:
                financed_amount = _round_money(sale_total - total_paid_now)
                if financed_amount < Decimal("0.00"):
                    financed_amount = Decimal("0.00")
                if financed_amount > 0:
                    installments_count = int(payment_data.installments or 1)
                    if installments_count < 1:
                        raise ValueError("Cantidad de cuotas invalida.")
                    interval_days = int(payment_data.interval_days or 0)
                    if interval_days <= 0:
                        interval_days = 30
                    for number, amount in enumerate(
                        _split_installments(financed_amount, installments_count),
                        start=1,
                    ):
                        due_date = timestamp + datetime.timedelta(
                            days=interval_days * number
                        )
                        installments_plan.append((due_date, amount))
                        session.add(
                            SaleInstallment(
                                sale_id=new_sale.id,
                                company_id=company_id,
                                branch_id=branch_id,
                                number=number,
                                amount=amount,
                                due_date=due_date,
                                status="pending",
                                paid_amount=Decimal("0.00"),
                                payment_date=None,
                            )
                        )
                    client.current_debt = _round_money(
                        client.current_debt + financed_amount
                    )
                    session.add(client)
    
            products_to_recalculate: set[int] = set()
            for entry in resolved_items:
                item = entry["item"]
                product = entry["product"]
                variant = entry["variant"]
                batches = entry["batches"]
                allows_decimal = entry["allows_decimal"]

                batch_id = None
                if variant:
                    if batches:
                        used_batches = _deduct_from_batches(
                            batches, item["quantity"], allows_decimal
                        )
                        if len(used_batches) == 1:
                            batch_id = used_batches[0].id
                        for batch in used_batches:
                            session.add(batch)
                        variant.stock = _sum_batch_stock(
                            batches, allows_decimal
                        )
                        session.add(variant)
                    else:
                        current_stock = _round_quantity(
                            variant.stock, allows_decimal
                        )
                        variant.stock = _round_quantity(
                            current_stock - item["quantity"], allows_decimal
                        )
                        session.add(variant)
                    products_to_recalculate.add(product.id)
                else:
                    if batches:
                        used_batches = _deduct_from_batches(
                            batches, item["quantity"], allows_decimal
                        )
                        if len(used_batches) == 1:
                            batch_id = used_batches[0].id
                        for batch in used_batches:
                            session.add(batch)
                        product.stock = _sum_batch_stock(
                            batches, allows_decimal
                        )
                        session.add(product)
                    else:
                        current_stock = _round_quantity(
                            product.stock, allows_decimal
                        )
                        product.stock = _round_quantity(
                            current_stock - item["quantity"], allows_decimal
                        )
                        session.add(product)

                barcode_snapshot = (
                    variant.sku if variant else product.barcode
                )
                variant_label = _variant_label(variant) if variant else ""
                name_snapshot = product.description
                if variant_label:
                    name_snapshot = f"{product.description} ({variant_label})"
                sale_item = SaleItem(
                    sale_id=new_sale.id,
                    product_id=product.id,
                    product_variant_id=variant.id if variant else None,
                    product_batch_id=batch_id,
                    company_id=company_id,
                    branch_id=branch_id,
                    quantity=item["quantity"],
                    unit_price=item["price"],
                    subtotal=item["subtotal"],
                    product_name_snapshot=name_snapshot,
                    product_barcode_snapshot=barcode_snapshot,
                    product_category_snapshot=product.category or "General",
                )
                session.add(sale_item)

            if products_to_recalculate:
                for product_id in products_to_recalculate:
                    total_query = select(
                        func.coalesce(func.sum(ProductVariant.stock), 0)
                    ).where(ProductVariant.product_id == product_id)
                    total_query = _apply_tenant_filters(
                        total_query, ProductVariant, company_id, branch_id
                    )
                    total_row = (await session.exec(total_query)).first()
                    if total_row is None:
                        total_stock = Decimal("0.0000")
                    elif isinstance(total_row, tuple):
                        total_stock = total_row[0]
                    else:
                        total_stock = total_row
                    product = products_by_id.get(product_id)
                    if product:
                        allows_decimal = decimal_units.get(
                            (product.unit or "").strip().lower(), False
                        )
                        product.stock = _round_quantity(
                            total_stock, allows_decimal
                        )
                        session.add(product)
    
            reservation_context = None
            reservation_balance_display = _money_to_float(reservation_balance)
            if reservation and reservation_balance > Decimal("0.00"):
                applied_amount = reservation_balance
                paid_before = reservation.paid_amount
                reservation.paid_amount = _round_money(
                    reservation.paid_amount + applied_amount
                )
                if reservation.paid_amount >= reservation.total_amount:
                    reservation.status = ReservationStatus.paid
                session.add(reservation)
    
                res_item = SaleItem(
                    sale_id=new_sale.id,
                    product_id=None,
                    company_id=company_id,
                    branch_id=branch_id,
                    quantity=Decimal("1.0000"),
                    unit_price=applied_amount,
                    subtotal=applied_amount,
                    product_name_snapshot=(
                        f"Alquiler {reservation.field_name} "
                        f"({reservation.start_datetime} - {reservation.end_datetime})"
                    ),
                    product_barcode_snapshot=str(reservation.id),
                    product_category_snapshot="Servicios",
                )
                session.add(res_item)
    
                balance_after = reservation.total_amount - reservation.paid_amount
                if balance_after < 0:
                    balance_after = Decimal("0.00")
                reservation_context = {
                    "total": _money_to_float(reservation.total_amount),
                    "paid_before": _money_to_float(paid_before),
                    "paid_now": _money_to_float(applied_amount),
                    "paid_after": _money_to_float(reservation.paid_amount),
                    "balance_after": _money_to_float(balance_after),
                    "header": (
                        f"Alquiler {reservation.field_name} "
                        f"({reservation.start_datetime} - {reservation.end_datetime})"
                    ),
                    "products_total": _money_to_float(items_total),
                    "charged_total": sale_total_display,
                }
    
            receipt_items = list(product_snapshot)
            if reservation and reservation_balance > Decimal("0.00"):
                receipt_items.insert(
                    0,
                    {
                        "description": f"Alquiler {reservation.field_name}",
                        "quantity": 1,
                        "unit": "Servicio",
                        "price": reservation_balance_display,
                        "subtotal": reservation_balance_display,
                    },
                )
    
            payment_summary = payment_data.summary or payment_method
            if is_credit:
                credit_lines = [
                    "CONDICION: CREDITO",
                    f"Pago Inicial: {_money_display(_round_money(initial_payment), symbol)}",
                    f"Saldo a Financiar: {_money_display(_round_money(financed_amount), symbol)}",
                    "Plan de Pagos:",
                ]
                if installments_plan:
                    for due_date, amount in installments_plan:
                        credit_lines.append(
                            f"- {due_date.strftime('%Y-%m-%d')}: {_money_display(amount, symbol)}"
                        )
                credit_lines.append("_____________________")
                credit_block = "\n".join(credit_lines)
                if payment_summary:
                    payment_summary = f"{payment_summary}\n{credit_block}"
                else:
                    payment_summary = credit_block
    
            await session.commit()
            return SaleProcessResult(
                sale=new_sale,
                receipt_items=receipt_items,
                sale_total=sale_total,
                sale_total_display=sale_total_display,
                timestamp=timestamp,
                payment_summary=payment_summary,
                reservation_context=reservation_context,
                reservation_balance=reservation_balance,
                reservation_balance_display=reservation_balance_display,
            )
        except Exception as e:
            await session.rollback()
            logger.error("Transacción fallida. Rollback ejecutado.", exc_info=True)
            raise e
