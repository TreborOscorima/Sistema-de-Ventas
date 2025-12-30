from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.models import FieldReservation, Product, Sale, SaleItem, Unit
from app.schemas.sale_schemas import PaymentInfoDTO, SaleItemDTO
from app.utils.calculations import calculate_subtotal, calculate_total

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


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(val) for key, val in value.items()}
    return value


class SaleService:
    @staticmethod
    def process_sale(
        session: Session,
        user_id: int | None,
        items: list[SaleItemDTO],
        payment_data: PaymentInfoDTO,
        reservation_id: str | None = None,
    ) -> SaleProcessResult:
        payment_method = (payment_data.method or "").strip()
        if not payment_method:
            raise ValueError("Seleccione un metodo de pago.")

        reservation = None
        reservation_balance = Decimal("0.00")
        if reservation_id:
            reservation = session.exec(
                select(FieldReservation).where(FieldReservation.id == reservation_id)
            ).first()
            if reservation and reservation.status in ["cancelado", "eliminado"]:
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

        units = session.exec(select(Unit)).all()
        decimal_units = {u.name.strip().lower(): u.allows_decimal for u in units}

        product_snapshot: list[Dict[str, Any]] = []
        decimal_snapshot: list[Dict[str, Any]] = []
        for item in items:
            description = (item.description or "").strip()
            if not description:
                raise ValueError("Producto sin descripcion.")
            unit = (item.unit or "").strip()
            allows_decimal = decimal_units.get(unit.lower(), False)
            quantity_receipt = _quantity_for_receipt(item.quantity, allows_decimal)
            quantity_db = _round_quantity(item.quantity, allows_decimal)
            price = _round_money(item.price)
            if quantity_db <= 0 or price <= 0:
                raise ValueError(f"Cantidad o precio invalido para {description}.")
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
            product = session.exec(
                select(Product)
                .where(Product.description == item["description"])
                .with_for_update()
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
        payment_details = _serialize_value(payment_data.to_dict())
        sale_total_display = _money_to_float(sale_total)
        payment_details["total"] = sale_total_display

        new_sale = Sale(
            timestamp=timestamp,
            total_amount=sale_total,
            payment_method=payment_method,
            payment_details=payment_details,
            user_id=user_id,
            is_deleted=False,
        )
        session.add(new_sale)
        session.flush()

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
                reservation.status = "pagado"
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
