from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.enums import PaymentMethodType
from app.models import PaymentMethod

DEFAULT_PAYMENT_METHODS = [
    {
        "name": "Efectivo",
        "code": "cash",
        "method_id": "cash",
        "description": "Billetes, Monedas",
        "kind": PaymentMethodType.cash,
        "allows_change": True,
    },
    {
        "name": "Yape",
        "code": "yape",
        "method_id": "yape",
        "description": "Pago con Yape",
        "kind": PaymentMethodType.yape,
        "allows_change": False,
    },
    {
        "name": "Plin",
        "code": "plin",
        "method_id": "plin",
        "description": "Pago con Plin",
        "kind": PaymentMethodType.plin,
        "allows_change": False,
    },
    {
        "name": "Transferencia",
        "code": "transfer",
        "method_id": "transfer",
        "description": "Transferencia",
        "kind": PaymentMethodType.transfer,
        "allows_change": False,
    },
    {
        "name": "Tarjeta de Credito",
        "code": "credit_card",
        "method_id": "credit_card",
        "description": "Pago con tarjeta credito",
        "kind": PaymentMethodType.credit,
        "allows_change": False,
    },
    {
        "name": "Tarjeta de Debito",
        "code": "debit_card",
        "method_id": "debit_card",
        "description": "Pago con tarjeta debito",
        "kind": PaymentMethodType.debit,
        "allows_change": False,
    },
    {
        "name": "Credito / Fiado",
        "code": "credit_sale",
        "method_id": "credit_sale",
        "description": "Venta al credito",
        "kind": PaymentMethodType.credit,
        "allows_change": False,
    },
]


async def init_payment_methods(session: AsyncSession) -> None:
    existing = (await session.exec(select(PaymentMethod).limit(1))).first()
    if existing:
        return

    session.add_all(
        [
            PaymentMethod(
                name=data["name"],
                code=data["code"],
                is_active=True,
                allows_change=data["allows_change"],
                method_id=data["method_id"],
                description=data["description"],
                kind=data["kind"],
                enabled=True,
            )
            for data in DEFAULT_PAYMENT_METHODS
        ]
    )
    await session.commit()
