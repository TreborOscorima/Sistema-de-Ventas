import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict

import reflex as rx
from sqlmodel import select

from app.models import FieldReservation, Product, Sale, SaleItem, User
from .mixin_state import MixinState
from .venta import CartMixin, PaymentMixin, ReceiptMixin


class VentaState(MixinState, CartMixin, PaymentMixin, ReceiptMixin):
    sale_form_key: int = 0

    @rx.event
    def confirm_sale(self):
        if not self.current_user["privileges"]["create_ventas"]:
            return rx.toast("No tiene permisos para crear ventas.", duration=3000)

        if hasattr(self, "_require_cashbox_open"):
            denial = self._require_cashbox_open()
            if denial:
                return denial

        def _to_decimal(value: Any) -> Decimal:
            return Decimal(str(value or 0))

        def _round_money(value: Any) -> Decimal:
            return _to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        def _round_quantity(value: Any, unit: str) -> Decimal:
            quant = Decimal("0.0001") if self._unit_allows_decimal(unit) else Decimal("1")
            return _to_decimal(value).quantize(quant, rounding=ROUND_HALF_UP)

        with rx.session() as session:
            reservation = None
            if hasattr(self, "reservation_payment_id") and self.reservation_payment_id:
                # Fix: Handle string UUIDs correctly
                reservation = session.exec(
                    select(FieldReservation).where(
                        FieldReservation.id == self.reservation_payment_id
                    )
                ).first()

            if reservation and reservation.status in ["cancelado", "eliminado"]:
                return rx.toast(
                    "No se puede cobrar una reserva cancelada o eliminada.",
                    duration=3000,
                )

            reservation_balance = Decimal("0.00")
            if reservation:
                raw_balance = reservation.total_amount - reservation.paid_amount
                if raw_balance < 0:
                    raw_balance = Decimal("0.00")
                reservation_balance = _round_money(raw_balance)
            reservation_balance_display = self._round_currency(reservation_balance)

            if not self.new_sale_items and reservation_balance <= Decimal("0.00"):
                if reservation:
                    return rx.toast("La reserva ya esta pagada.", duration=3000)
                return rx.toast("No hay productos en la venta.", duration=3000)
            if not self.payment_method:
                return rx.toast("Seleccione un metodo de pago.", duration=3000)

            product_snapshot: list[Dict[str, Any]] = []
            for item in self.new_sale_items:
                snapshot_item = item.copy()
                self._apply_item_rounding(snapshot_item)
                product_snapshot.append(snapshot_item)

            decimal_snapshot: list[Dict[str, Any]] = []
            for item in product_snapshot:
                quantity = _round_quantity(item.get("quantity", 0), item.get("unit", ""))
                price = _round_money(item.get("price", 0))
                subtotal = _round_money(quantity * price)
                decimal_snapshot.append(
                    {
                        **item,
                        "quantity": quantity,
                        "price": price,
                        "subtotal": subtotal,
                    }
                )

            locked_products: list[tuple[Dict[str, Any], Product]] = []
            for item in decimal_snapshot:
                description = (item.get("description") or "").strip()
                product = session.exec(
                    select(Product)
                    .where(Product.description == description)
                    .with_for_update()
                ).first()
                if not product:
                    return rx.toast(
                        f"Producto {item['description']} no encontrado en inventario.",
                        duration=3000,
                    )
                if product.stock < item["quantity"]:
                    return rx.toast(
                        f"Stock insuficiente para {item['description']}.", duration=3000
                    )
                locked_products.append((item, product))

            sale_total = _round_money(
                sum((item["subtotal"] for item in decimal_snapshot), Decimal("0.00"))
                + reservation_balance
            )
            sale_total_display = self._round_currency(sale_total)
            if sale_total <= Decimal("0.00"):
                return rx.toast("No hay importe para cobrar.", duration=3000)

            self._refresh_payment_feedback(total_override=sale_total_display)
            if self.payment_method_kind == "cash":
                if self.payment_cash_status not in ["exact", "change"]:
                    message = (
                        self.payment_cash_message
                        or "Ingrese un monto valido en efectivo."
                    )
                    return rx.toast(message, duration=3000)
            if self.payment_method_kind == "mixed":
                if self.payment_mixed_status not in ["exact", "change"]:
                    message = (
                        self.payment_mixed_message
                        or "Complete los montos del pago mixto."
                    )
                    return rx.toast(message, duration=3000)

            timestamp = datetime.datetime.now()
            payment_summary = self._generate_payment_summary()
            payment_label, payment_breakdown = self._payment_label_and_breakdown(
                sale_total_display
            )

            # Create Sale
            user_id = None
            user_obj = session.exec(
                select(User).where(User.username == self.current_user["username"])
            ).first()
            if user_obj:
                user_id = user_obj.id

            payment_data = {
                "summary": payment_summary,
                "method": self.payment_method,
                "method_kind": self.payment_method_kind,
                "label": payment_label,
                "breakdown": payment_breakdown,
                "total": sale_total_display,
                "cash": {
                    "amount": self._round_currency(self.payment_cash_amount),
                    "message": self.payment_cash_message,
                    "status": self.payment_cash_status,
                },
                "card": {"type": self.payment_card_type},
                "wallet": {
                    "provider": self.payment_wallet_provider or self.payment_wallet_choice,
                    "choice": self.payment_wallet_choice,
                },
                "mixed": {
                    "cash": self._round_currency(self.payment_mixed_cash),
                    "card": self._round_currency(self.payment_mixed_card),
                    "wallet": self._round_currency(self.payment_mixed_wallet),
                    "non_cash_kind": self.payment_mixed_non_cash_kind,
                    "notes": self.payment_mixed_notes,
                    "message": self.payment_mixed_message,
                    "status": self.payment_mixed_status,
                },
            }

            new_sale = Sale(
                timestamp=timestamp,
                total_amount=sale_total,
                payment_method=self.payment_method,
                payment_details=payment_data,
                user_id=user_id,
                is_deleted=False,
            )
            session.add(new_sale)
            session.flush()  # Get ID

            # Process Products
            for item, product in locked_products:
                # Update stock
                new_stock = product.stock - item["quantity"]
                if new_stock < 0:
                    new_stock = Decimal("0.00")
                product.stock = _round_quantity(new_stock, product.unit)
                session.add(product)

                # Create SaleItem
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

            # Process Reservation Payment
            if reservation_balance > Decimal("0.00"):
                applied_amount = reservation_balance
                paid_before = reservation.paid_amount
                reservation.paid_amount = _round_money(
                    reservation.paid_amount + applied_amount
                )

                if reservation.paid_amount >= reservation.total_amount:
                    reservation.status = "pagado"

                session.add(reservation)

                # Create SaleItem for reservation (no product_id)
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
                self.last_sale_reservation_context = {
                    "total": self._round_currency(reservation.total_amount),
                    "paid_before": self._round_currency(paid_before),
                    "paid_now": self._round_currency(applied_amount),
                    "paid_after": self._round_currency(reservation.paid_amount),
                    "balance_after": self._round_currency(balance_after),
                    "header": (
                        f"Alquiler {reservation.field_name} "
                        f"({reservation.start_datetime} - {reservation.end_datetime})"
                    ),
                    "products_total": self._round_currency(
                        sum(
                            (item["subtotal"] for item in decimal_snapshot),
                            Decimal("0.00"),
                        )
                    ),
                    "charged_total": sale_total_display,
                }
            else:
                self.last_sale_reservation_context = None

            session.commit()

            # Prepare receipt data (in memory for display)
            self.last_sale_receipt = product_snapshot
            if reservation_balance > Decimal("0.00"):
                self.last_sale_receipt.insert(
                    0,
                    {
                        "description": f"Alquiler {reservation.field_name}",
                        "quantity": 1,
                        "unit": "Servicio",
                        "price": reservation_balance_display,
                        "subtotal": reservation_balance_display,
                    },
                )

            self.last_sale_total = sale_total_display
            self.last_sale_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            self.last_payment_summary = payment_summary
            self.sale_receipt_ready = True
            self.new_sale_items = []
            self._reset_sale_form()
            self._reset_payment_fields()
            self._refresh_payment_feedback()

            # Trigger updates in other states
            if hasattr(self, "reload_history"):
                self.reload_history()
            if hasattr(self, "_cashbox_update_trigger"):
                self._cashbox_update_trigger += 1

            return rx.toast("Venta confirmada.", duration=3000)
