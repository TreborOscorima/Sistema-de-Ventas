from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, Dict

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CashboxLog, Client, Sale, SaleInstallment
from app.utils.calculations import calculate_total


def _round_money(value: Any) -> Decimal:
    return calculate_total([{"subtotal": value}], key="subtotal")


class CreditService:
    @staticmethod
    async def get_client_status(
        session: AsyncSession, client_id: int
    ) -> Dict[str, Any]:
        client = await session.get(Client, client_id)
        if not client:
            raise ValueError("Cliente no encontrado.")

        pending_installments = (
            await session.exec(
                select(SaleInstallment)
                .join(Sale)
                .where(Sale.client_id == client_id)
                .where(SaleInstallment.status != "paid")
                .order_by(SaleInstallment.due_date)
            )
        ).all()

        return {
            "current_debt": _round_money(client.current_debt),
            "pending_installments": pending_installments,
        }

    @staticmethod
    async def pay_installment(
        session: AsyncSession,
        installment_id: int,
        amount: Decimal,
        payment_method: str,
        user_id: int | None = None,
    ) -> SaleInstallment:
        payment_amount = _round_money(amount)
        if payment_amount <= 0:
            raise ValueError("Monto de pago invalido.")

        method_label = (payment_method or "").strip()
        if not method_label:
            raise ValueError("Metodo de pago requerido.")

        installment = (
            await session.exec(
                select(SaleInstallment)
                .where(SaleInstallment.id == installment_id)
                .with_for_update()
            )
        ).first()
        if not installment:
            raise ValueError("Cuota no encontrada.")

        sale = (
            await session.exec(
                select(Sale)
                .where(Sale.id == installment.sale_id)
                .with_for_update()
            )
        ).first()
        if not sale or sale.client_id is None:
            raise ValueError("Cliente no encontrado.")

        client = (
            await session.exec(
                select(Client)
                .where(Client.id == sale.client_id)
                .with_for_update()
            )
        ).first()
        if not client:
            raise ValueError("Cliente no encontrado.")

        amount_due = Decimal(str(installment.amount or 0))
        paid_amount = Decimal(str(installment.paid_amount or 0))
        pending_amount = _round_money(amount_due - paid_amount)
        if payment_amount > pending_amount:
            raise ValueError("El monto supera el saldo pendiente.")

        new_paid_amount = _round_money(paid_amount + payment_amount)
        if new_paid_amount > amount_due:
            new_paid_amount = amount_due
        installment.paid_amount = new_paid_amount
        if installment.paid_amount >= amount_due:
            installment.status = "paid"
            installment.payment_date = datetime.datetime.now()
        else:
            installment.status = "partial"

        client.current_debt = _round_money(
            client.current_debt - payment_amount
        )
        if client.current_debt < 0:
            client.current_debt = Decimal("0.00")

        client_name = (client.name or "").strip() or f"ID {client.id}"
        notes = (
            f"Cobro Cuota {installment.number} / "
            f"Venta #{installment.sale_id} - Cliente: {client_name}"
        )

        session.add(installment)
        session.add(client)
        session.add(
            CashboxLog(
                action="Cobranza",
                amount=payment_amount,
                payment_method=method_label,
                notes=notes,
                user_id=user_id,
                sale_id=sale.id,
            )
        )

        return installment
