"""Servicio de Créditos y Cobranzas.

Este módulo maneja toda la lógica relacionada con ventas a crédito:

- Consulta de estado crediticio de clientes
- Cobro de cuotas (parcial o total)
- Actualización de deuda del cliente
- Registro de cobranzas en caja

Clases principales:
    CreditService: Servicio estático para operaciones de crédito

Ejemplo de uso::

    from app.services.credit_service import CreditService
    
    async with get_async_session() as session:
        # Consultar estado del cliente
        status = await CreditService.get_client_status(session, client_id=1)
        print(f"Deuda actual: {status['current_debt']}")
        
        # Pagar una cuota
        installment = await CreditService.pay_installment(
            session=session,
            installment_id=5,
            amount=Decimal("50.00"),
            payment_method="Efectivo",
            user_id=1,
        )
        await session.commit()
"""
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
    """Servicio para gestión de créditos y cobranzas.
    
    Proporciona métodos estáticos para consultar y gestionar
    el estado crediticio de clientes y el cobro de cuotas.
    
    Todos los métodos son asíncronos y requieren una sesión de BD.
    Las operaciones de cobro registran automáticamente en CashboxLog.
    """
    
    @staticmethod
    async def get_client_status(
        session: AsyncSession,
        client_id: int,
        company_id: int | None = None,
        branch_id: int | None = None,
    ) -> Dict[str, Any]:
        """Obtiene el estado crediticio de un cliente.
        
        Consulta la deuda actual y las cuotas pendientes de pago
        ordenadas por fecha de vencimiento.
        
        Args:
            session: Sesión async de SQLAlchemy
            client_id: ID del cliente a consultar
            
        Returns:
            Dict con:
                - current_debt: Deuda total actual (Decimal)
                - pending_installments: Lista de SaleInstallment pendientes
                
        Raises:
            ValueError: Si el cliente no existe
        """
        client_query = select(Client).where(Client.id == client_id)
        if company_id:
            client_query = client_query.where(Client.company_id == company_id)
        if branch_id:
            client_query = client_query.where(Client.branch_id == branch_id)
        client = (await session.exec(client_query)).first()
        if not client:
            raise ValueError("Cliente no encontrado.")

        pending_installments = (
            await session.exec(
                select(SaleInstallment)
                .join(Sale)
                .where(Sale.client_id == client_id)
                .where(SaleInstallment.company_id == client.company_id)
                .where(SaleInstallment.branch_id == client.branch_id)
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
        company_id: int | None = None,
        branch_id: int | None = None,
    ) -> SaleInstallment:
        """Registra el pago de una cuota de crédito.
        
        Actualiza el estado de la cuota, reduce la deuda del cliente
        y registra el cobro en el log de caja.
        
        Soporta pagos parciales: si el monto es menor al pendiente,
        la cuota queda en estado 'partial'. Si cubre el total,
        pasa a 'paid'.
        
        Args:
            session: Sesión async de SQLAlchemy (con transacción activa)
            installment_id: ID de la cuota a pagar
            amount: Monto a pagar (Decimal, debe ser > 0)
            payment_method: Etiqueta del método de pago ("Efectivo", "Yape", etc.)
            user_id: ID del usuario que registra el pago (opcional)
            
        Returns:
            SaleInstallment actualizada
            
        Raises:
            ValueError: Si:
                - El monto es <= 0
                - El método de pago está vacío
                - La cuota no existe
                - El monto excede el saldo pendiente
                - El cliente no existe
                
        Note:
            - Usa WITH FOR UPDATE para evitar race conditions
            - Registra automáticamente en CashboxLog con acción "Cobranza"
            - El commit debe manejarse externamente
            
        Example::
        
            installment = await CreditService.pay_installment(
                session=session,
                installment_id=10,
                amount=Decimal("150.00"),
                payment_method="Yape",
                user_id=1,
            )
            if installment.status == "paid":
                print("Cuota pagada completamente")
            else:
                print(f"Pago parcial, pendiente: {installment.amount - installment.paid_amount}")
        """
        payment_amount = _round_money(amount)
        if payment_amount <= 0:
            raise ValueError("Monto de pago invalido.")

        method_label = (payment_method or "").strip()
        if not method_label:
            raise ValueError("Metodo de pago requerido.")

        installment_query = (
            select(SaleInstallment)
            .where(SaleInstallment.id == installment_id)
            .with_for_update()
        )
        if company_id:
            installment_query = installment_query.where(
                SaleInstallment.company_id == company_id
            )
        if branch_id:
            installment_query = installment_query.where(
                SaleInstallment.branch_id == branch_id
            )
        installment = (await session.exec(installment_query)).first()
        if not installment:
            raise ValueError("Cuota no encontrada.")

        sale_query = (
            select(Sale)
            .where(Sale.id == installment.sale_id)
            .with_for_update()
        )
        if company_id:
            sale_query = sale_query.where(Sale.company_id == company_id)
        if branch_id:
            sale_query = sale_query.where(Sale.branch_id == branch_id)
        sale = (await session.exec(sale_query)).first()
        if not sale or sale.client_id is None:
            raise ValueError("Cliente no encontrado.")

        client = (
            await session.exec(
                select(Client)
                .where(Client.id == sale.client_id)
                .where(Client.company_id == sale.company_id)
                .where(Client.branch_id == sale.branch_id)
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
                company_id=sale.company_id,
                branch_id=sale.branch_id,
            )
        )

        return installment
