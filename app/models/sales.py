from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

import reflex as rx
from sqlmodel import Field, Relationship
import sqlalchemy
from sqlalchemy import Numeric

from app.enums import PaymentMethodType, ReservationStatus, SaleStatus, SportType

if TYPE_CHECKING:
    from .auth import User
    from .client import Client
    from .inventory import Product


class Sale(rx.Model, table=True):
    """Cabecera de venta."""

    timestamp: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False),
            server_default=sqlalchemy.func.now(),
            index=True,
        ),
    )
    total_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )

    status: SaleStatus = Field(default=SaleStatus.completed)
    delete_reason: Optional[str] = Field(default=None)
    payment_condition: str = Field(default="contado")

    client_id: Optional[int] = Field(
        default=None, foreign_key="client.id", index=True
    )
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

    client: Optional["Client"] = Relationship(back_populates="sales")
    user: Optional["User"] = Relationship(back_populates="sales")
    items: List["SaleItem"] = Relationship(back_populates="sale")
    payments: List["SalePayment"] = Relationship(back_populates="sale")
    installments: List["SaleInstallment"] = Relationship(back_populates="sale")


class SalePayment(rx.Model, table=True):
    """Transaccion de pago asociada a una venta."""

    sale_id: int = Field(foreign_key="sale.id")
    amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    method_type: PaymentMethodType = Field(nullable=False)
    reference_code: Optional[str] = Field(default=None)
    payment_method_id: Optional[int] = Field(
        default=None, foreign_key="paymentmethod.id"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    sale: Optional["Sale"] = Relationship(back_populates="payments")


class SaleItem(rx.Model, table=True):
    """Detalle de venta."""

    quantity: Decimal = Field(
        default=Decimal("1.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    unit_price: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    subtotal: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )

    product_name_snapshot: str = Field(default="")
    product_barcode_snapshot: str = Field(default="")

    sale_id: int = Field(foreign_key="sale.id")
    product_id: Optional[int] = Field(default=None, foreign_key="product.id")

    sale: Optional["Sale"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(back_populates="sale_items")


class SaleInstallment(rx.Model, table=True):
    """Cuotas de una venta a credito."""

    sale_id: int = Field(foreign_key="sale.id")
    number: int = Field(nullable=False)
    amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    due_date: datetime = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False), index=True
        ),
    )
    status: str = Field(default="pending", index=True)
    paid_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    payment_date: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    sale: Optional["Sale"] = Relationship(back_populates="installments")


class CashboxSession(rx.Model, table=True):
    """Sesion de caja (apertura/cierre)."""

    opening_time: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )
    closing_time: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )
    opening_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    closing_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    is_open: bool = Field(default=True)

    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

    user: Optional["User"] = Relationship(back_populates="sessions")


class CashboxLog(rx.Model, table=True):
    """Log de movimientos de caja."""

    timestamp: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False), index=True
        ),
    )
    action: str = Field(nullable=False, index=True)
    amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    quantity: Decimal = Field(
        default=Decimal("1.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    unit: str = Field(default="Unidad")
    cost: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    payment_method: Optional[str] = Field(default="Efectivo", index=True)
    payment_method_id: Optional[int] = Field(
        default=None, foreign_key="paymentmethod.id", index=True
    )
    notes: str = Field(default="")

    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

    user: Optional["User"] = Relationship(back_populates="logs")


class FieldReservation(rx.Model, table=True):
    """Reserva de canchas deportivas."""

    client_name: str = Field(nullable=False)
    client_dni: Optional[str] = Field(default=None)
    client_phone: Optional[str] = Field(default=None)

    sport: SportType = Field(default=SportType.futbol)
    field_name: str = Field(nullable=False)

    start_datetime: datetime = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False), index=True
        ),
    )
    end_datetime: datetime = Field(
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    total_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    paid_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    status: ReservationStatus = Field(default=ReservationStatus.pending)

    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

    cancellation_reason: Optional[str] = Field(default=None)
    delete_reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    user: Optional["User"] = Relationship(back_populates="reservations")


class PaymentMethod(rx.Model, table=True):
    """Metodos de pago configurables."""

    name: str = Field(nullable=False)
    code: str = Field(unique=True, index=True, nullable=False)
    is_active: bool = Field(default=True)
    allows_change: bool = Field(default=False)

    method_id: str = Field(unique=True, index=True, nullable=False)
    description: str = Field(default="")
    kind: PaymentMethodType = Field(default=PaymentMethodType.other)
    enabled: bool = Field(default=True)


class Currency(rx.Model, table=True):
    """Monedas disponibles."""

    code: str = Field(unique=True, index=True, nullable=False)
    name: str = Field(nullable=False)
    symbol: str = Field(nullable=False)


class CompanySettings(rx.Model, table=True):
    """Configuracion de datos de empresa (singleton)."""

    company_name: str = Field(default="", nullable=False)
    ruc: str = Field(default="", nullable=False)
    address: str = Field(default="", nullable=False)
    phone: Optional[str] = Field(default=None)
    footer_message: Optional[str] = Field(default=None)
    receipt_paper: str = Field(default="80", nullable=False)
    receipt_width: Optional[int] = Field(default=None)
