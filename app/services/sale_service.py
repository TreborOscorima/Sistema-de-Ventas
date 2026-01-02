from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

from sqlmodel import select

from app.enums import PaymentMethodType, ReservationStatus, SaleStatus
from app.models import FieldReservation, Product, Sale, SaleItem, SalePayment, Unit
from app.schemas.sale_schemas import PaymentInfoDTO, SaleItemDTO
from app.utils.calculations import calculate_subtotal, calculate_total
from app.utils.db import get_async_session

QTY_DECIMAL_QUANT = Decimal("0.0001")
QTY_DISPLAY_QUANT = Decimal("0.01")
QTY_INTEGER_QUANT = Decimal("1")


class StockError(ValueError):
    pass


@dataclass
class SaleProcessResult:
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
    return Decimal(str(value or 0))


def _round_money(value: Any) -> Decimal:
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


class SaleService:
    @staticmethod
    async def process_sale(
        user_id: int | None,
        items: list[SaleItemDTO],
        payment_data: PaymentInfoDTO,
        reservation_id: str | None = None,
    ) -> SaleProcessResult:
        payment_method = (payment_data.method or "").strip()
        if not payment_method:
            raise ValueError("Seleccione un metodo de pago.")

        async with get_async_session() as session:
            try:
                reservation = None
                reservation_balance = Decimal("0.00")
                if reservation_id:
                    reservation = (
                        await session.exec(
                            select(FieldReservation).where(
                                FieldReservation.id == reservation_id
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

                units = (await session.exec(select(Unit))).all()
                decimal_units = {
                    u.name.strip().lower(): u.allows_decimal for u in units
                }

                product_snapshot: list[Dict[str, Any]] = []
                decimal_snapshot: list[Dict[str, Any]] = []
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
                    price = _round_money(item.price)
                    if quantity_db <= 0 or price <= 0:
                        raise ValueError(
                            f"Cantidad o precio invalido para {description}."
                        )
                    subtotal = calculate_subtotal(quantity_db, price)
                    product_snapshot.append(
                        {
                            "description": description,
                            "quantity": quantity_receipt,
                            "unit": unit,
                            "price": _money_to_float(price),
                            "subtotal": _money_to_float(subtotal),
                        }
                    )
                    decimal_snapshot.append(
                        {
                            "description": description,
                            "quantity": quantity_db,
                            "unit": unit,
                            "price": price,
                            "subtotal": subtotal,
                            "barcode": item.barcode or "",
                        }
                    )

                locked_products: list[tuple[Dict[str, Any], Product]] = []
                for item in decimal_snapshot:
                    product = (
                        await session.exec(
                            select(Product)
                            .where(Product.description == item["description"])
                            .with_for_update()
                        )
                    ).first()
                    if not product:
                        raise StockError(
                            f"Producto {item['description']} no encontrado en inventario."
                        )
                    if product.stock < item["quantity"]:
                        raise StockError(
                            f"Stock insuficiente para {item['description']}."
                        )
                    locked_products.append((item, product))

                items_total = calculate_total(decimal_snapshot)
                sale_total = _round_money(items_total + reservation_balance)
                if sale_total <= Decimal("0.00"):
                    raise ValueError("No hay importe para cobrar.")

                kind = (payment_data.method_kind or "other").lower()
                if kind == "cash":
                    cash_amount = _to_decimal(payment_data.cash.amount)
                    if cash_amount <= 0 or cash_amount < sale_total:
                        message = (
                            payment_data.cash.message
                            or "Ingrese un monto valido en efectivo."
                        )
                        raise ValueError(message)
                elif kind == "mixed":
                    total_paid = (
                        _to_decimal(payment_data.mixed.cash)
                        + _to_decimal(payment_data.mixed.card)
                        + _to_decimal(payment_data.mixed.wallet)
                    )
                    if total_paid <= 0 or total_paid < sale_total:
                        message = (
                            payment_data.mixed.message
                            or "Complete los montos del pago mixto."
                        )
                        raise ValueError(message)

                timestamp = datetime.datetime.now()
                sale_total_display = _money_to_float(sale_total)

                new_sale = Sale(
                    timestamp=timestamp,
                    total_amount=sale_total,
                    status=SaleStatus.completed,
                    user_id=user_id,
                )
                session.add(new_sale)
                await session.flush()

                for method_type, amount in _build_sale_payments(
                    payment_data, sale_total
                ):
                    if amount <= 0:
                        continue
                    session.add(
                        SalePayment(
                            sale_id=new_sale.id,
                            amount=amount,
                            method_type=method_type,
                            reference_code=None,
                            created_at=timestamp,
                        )
                    )

                for item, product in locked_products:
                    new_stock = product.stock - item["quantity"]
                    if new_stock < 0:
                        new_stock = Decimal("0.00")
                    allows_decimal = decimal_units.get(
                        (product.unit or "").strip().lower(), False
                    )
                    product.stock = _round_quantity(new_stock, allows_decimal)
                    session.add(product)

                    sale_item = SaleItem(
                        sale_id=new_sale.id,
                        product_id=product.id,
                        quantity=item["quantity"],
                        unit_price=item["price"],
                        subtotal=item["subtotal"],
                        product_name_snapshot=product.description,
                        product_barcode_snapshot=product.barcode,
                    )
                    session.add(sale_item)

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
                        quantity=Decimal("1.0000"),
                        unit_price=applied_amount,
                        subtotal=applied_amount,
                        product_name_snapshot=(
                            f"Alquiler {reservation.field_name} "
                            f"({reservation.start_datetime} - {reservation.end_datetime})"
                        ),
                        product_barcode_snapshot=str(reservation.id),
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
                await session.commit()
            except Exception:
                await session.rollback()
                raise

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
