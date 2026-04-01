from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

import reflex as rx
from sqlmodel import Field, Relationship
import sqlalchemy
from sqlalchemy import Numeric

from app.enums import PaymentMethodType, ReservationStatus, SaleStatus, SportType
from app.utils.timezone import utc_now_naive

if TYPE_CHECKING:
    from .auth import User
    from .client import Client
    from .inventory import Product, ProductBatch, ProductVariant


class Sale(rx.Model, table=True):
    """Cabecera de venta."""

    __table_args__ = (
        sqlalchemy.Index(
            "ix_sale_company_branch_timestamp",
            "company_id",
            "branch_id",
            "timestamp",
        ),
    )

    timestamp: datetime = Field(
        default_factory=utc_now_naive,
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

    status: SaleStatus = Field(default=SaleStatus.completed, index=True)
    delete_reason: Optional[str] = Field(default=None)
    payment_condition: str = Field(default="contado")
    # Tipo de comprobante fiscal asociado a esta venta (boleta, factura, nota_venta, etc.)
    # Se persiste para auditoría/histórico; el documento fiscal puede consultarse
    # a través de FiscalDocument.sale_id.
    receipt_type: Optional[str] = Field(default=None, index=False)

    company_id: int = Field(
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )
    client_id: Optional[int] = Field(
        default=None, foreign_key="client.id", index=True
    )
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)

    client: Optional["Client"] = Relationship(back_populates="sales")
    user: Optional["User"] = Relationship(back_populates="sales")
    items: List["SaleItem"] = Relationship(back_populates="sale")
    payments: List["SalePayment"] = Relationship(back_populates="sale")
    installments: List["SaleInstallment"] = Relationship(back_populates="sale")


class SalePayment(rx.Model, table=True):
    """Transaccion de pago asociada a una venta."""

    __table_args__ = (
        sqlalchemy.Index(
            "ix_salepayment_tenant_sale",
            "company_id",
            "branch_id",
            "sale_id",
        ),
    )

    sale_id: int = Field(foreign_key="sale.id", index=True)
    company_id: int = Field(
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )
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
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    sale: Optional["Sale"] = Relationship(back_populates="payments")


class SaleItem(rx.Model, table=True):
    """Detalle de venta."""

    __table_args__ = (
        sqlalchemy.Index(
            "ix_saleitem_company_branch_sale",
            "company_id",
            "branch_id",
            "sale_id",
        ),
        sqlalchemy.Index(
            "ix_saleitem_company_branch_product",
            "company_id",
            "branch_id",
            "product_id",
        ),
    )

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
    product_category_snapshot: str = Field(default="")

    sale_id: int = Field(foreign_key="sale.id")
    product_id: Optional[int] = Field(default=None, foreign_key="product.id")
    product_variant_id: Optional[int] = Field(
        default=None,
        foreign_key="productvariant.id",
    )
    product_batch_id: Optional[int] = Field(
        default=None,
        foreign_key="productbatch.id",
    )
    company_id: int = Field(
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )

    sale: Optional["Sale"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(back_populates="sale_items")
    product_variant: Optional["ProductVariant"] = Relationship(
        back_populates="sale_items"
    )
    product_batch: Optional["ProductBatch"] = Relationship(
        back_populates="sale_items"
    )


class SaleInstallment(rx.Model, table=True):
    """Cuotas de una venta a credito."""

    __table_args__ = (
        sqlalchemy.Index(
            "ix_saleinstallment_sale_status",
            "sale_id",
            "status",
        ),
        sqlalchemy.Index(
            "ix_saleinstallment_duedate_status",
            "due_date",
            "status",
        ),
        sqlalchemy.Index(
            "ix_saleinstallment_tenant_status",
            "company_id",
            "branch_id",
            "status",
        ),
    )

    sale_id: int = Field(foreign_key="sale.id")
    company_id: int = Field(
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )
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

    __table_args__ = (
        sqlalchemy.Index(
            "ix_cashboxsession_tenant_user_open",
            "company_id",
            "branch_id",
            "user_id",
            "is_open",
        ),
    )

    opening_time: datetime = Field(
        default_factory=utc_now_naive,
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

    company_id: int = Field(
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

    user: Optional["User"] = Relationship(back_populates="sessions")


class CashboxLog(rx.Model, table=True):
    """Log de movimientos de caja."""

    __table_args__ = (
        sqlalchemy.Index(
            "ix_cashboxlog_company_branch_timestamp",
            "company_id",
            "branch_id",
            "timestamp",
        ),
        sqlalchemy.Index(
            "ix_cashboxlog_timestamp_action",
            "timestamp",
            "action",
        ),
    )

    timestamp: datetime = Field(
        default_factory=utc_now_naive,
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
    sale_id: Optional[int] = Field(
        default=None, foreign_key="sale.id", index=True
    )
    is_voided: bool = Field(default=False, index=True)

    company_id: int = Field(
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

    user: Optional["User"] = Relationship(back_populates="logs")


class FieldReservation(rx.Model, table=True):
    """Reserva de canchas deportivas."""

    __table_args__ = (
        sqlalchemy.Index(
            "ix_fieldreservation_company_branch_sport_start",
            "company_id",
            "branch_id",
            "sport",
            "start_datetime",
        ),
        sqlalchemy.Index(
            "ix_fieldreservation_tenant_status",
            "company_id",
            "branch_id",
            "status",
        ),
    )

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
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False), index=True
        ),
    )

    total_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    paid_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    status: ReservationStatus = Field(default=ReservationStatus.pending, index=True)

    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    company_id: int = Field(
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )

    cancellation_reason: Optional[str] = Field(default=None)
    delete_reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    user: Optional["User"] = Relationship(back_populates="reservations")


class PaymentMethod(rx.Model, table=True):
    """Metodos de pago configurables."""

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "code",
            name="uq_paymentmethod_company_branch_code",
        ),
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "method_id",
            name="uq_paymentmethod_company_branch_method_id",
        ),
    )

    company_id: int = Field(
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )
    name: str = Field(nullable=False)
    code: str = Field(index=True, nullable=False)
    is_active: bool = Field(default=True)
    allows_change: bool = Field(default=False)

    method_id: str = Field(index=True, nullable=False)
    description: str = Field(default="")
    kind: PaymentMethodType = Field(default=PaymentMethodType.other)
    enabled: bool = Field(default=True)


class Currency(rx.Model, table=True):
    """Monedas disponibles."""

    code: str = Field(unique=True, index=True, nullable=False)
    name: str = Field(nullable=False)
    symbol: str = Field(nullable=False)


class CompanySettings(rx.Model, table=True):
    """Configuracion de datos de empresa (singleton).

    Almacena la configuración global del negocio incluyendo
    país de operación, moneda y datos fiscales.
    """

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            name="uq_companysettings_company_branch",
        ),
    )

    company_id: int = Field(
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )
    company_name: str = Field(default="", nullable=False)
    ruc: str = Field(default="", nullable=False)
    address: str = Field(default="", nullable=False)
    phone: Optional[str] = Field(default=None)
    footer_message: Optional[str] = Field(default=None)
    receipt_paper: str = Field(default="80", max_length=10, nullable=False)
    receipt_width: Optional[int] = Field(default=None)
    default_currency_code: str = Field(default="PEN", max_length=10, nullable=False)
    country_code: str = Field(default="PE", max_length=5, nullable=False)
    timezone: Optional[str] = Field(default=None, max_length=64)
    business_vertical: str = Field(
        default="general",
        max_length=30,
        description="Rubro del negocio: general, bodega, ferreteria, farmacia, ropa, jugueteria, restaurante",
    )
