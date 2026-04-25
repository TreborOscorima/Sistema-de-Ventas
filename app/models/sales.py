from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

import reflex as rx
from sqlmodel import Field, Relationship
import sqlalchemy
from sqlalchemy import CheckConstraint, Numeric

from app.enums import PaymentMethodType, ReservationStatus, ReturnReason, SaleStatus, SportType
from app.utils.timezone import utc_now_naive

from ._mixins import TenantMixin

if TYPE_CHECKING:
    from .auth import User
    from .client import Client
    from .inventory import Product, ProductBatch, ProductVariant


class Sale(TenantMixin, rx.Model, table=True):
    """Cabecera de venta."""

    __tablename__ = "sale"

    __table_args__ = (
        sqlalchemy.Index(
            "ix_sale_company_branch_timestamp",
            "company_id",
            "branch_id",
            "timestamp",
        ),
        sqlalchemy.Index(
            "ix_sale_tenant_status_timestamp",
            "company_id",
            "branch_id",
            "status",
            "timestamp",
        ),
        CheckConstraint("total_amount >= 0", name="ck_sale_total_nonneg"),
        # S1-01: idempotencia de ventas — un (company_id, idempotency_key)
        # no-NULL sólo puede corresponder a una Sale. Ventas sin key quedan
        # con NULL (MySQL permite múltiples NULL en UNIQUE), sin constraint.
        sqlalchemy.UniqueConstraint(
            "company_id",
            "idempotency_key",
            name="uq_sale_company_idempotency_key",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}

    timestamp: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False),
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
    # S1-01: token opaco emitido por el frontend para deduplicar doble-click
    # y retries de red. Scope: (company_id, idempotency_key). Ventas legacy o
    # flujos internos sin riesgo de duplicado quedan con NULL.
    idempotency_key: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.String(64),
            nullable=True,
            index=False,
        ),
    )
    # Tipo de comprobante fiscal asociado a esta venta (boleta, factura, nota_venta, etc.)
    # Se persiste para auditoría/histórico; el documento fiscal puede consultarse
    # a través de FiscalDocument.sale_id.
    receipt_type: Optional[str] = Field(default=None, index=False)

    client_id: Optional[int] = Field(
        default=None, foreign_key="client.id", index=True
    )
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)

    client: Optional["Client"] = Relationship(back_populates="sales")
    user: Optional["User"] = Relationship(back_populates="sales")
    items: List["SaleItem"] = Relationship(
        back_populates="sale",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
        },
    )
    payments: List["SalePayment"] = Relationship(
        back_populates="sale",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
        },
    )
    installments: List["SaleInstallment"] = Relationship(
        back_populates="sale",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    returns: List["SaleReturn"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[SaleReturn.original_sale_id]",
            "cascade": "all, delete-orphan",
        },
    )


class SalePayment(TenantMixin, rx.Model, table=True):
    """Transaccion de pago asociada a una venta."""

    __tablename__ = "salepayment"

    __table_args__ = (
        sqlalchemy.Index(
            "ix_salepayment_tenant_sale",
            "company_id",
            "branch_id",
            "sale_id",
        ),
    )

    # CASCADE para que la baja lógica de Sale (ORM) + hard-delete SQL
    # siempre eliminen el detalle de pagos.
    sale_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("sale.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
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


class SaleItem(TenantMixin, rx.Model, table=True):
    """Detalle de venta."""

    __tablename__ = "saleitem"

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
        CheckConstraint("quantity > 0", name="ck_saleitem_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_saleitem_unit_price_nonneg"),
        CheckConstraint("subtotal >= 0", name="ck_saleitem_subtotal_nonneg"),
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

    # Kit traceability: si este ítem fue parte de un kit explosionado.
    # SET NULL: conservamos el ítem aunque el producto-kit desaparezca.
    kit_product_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("product.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    kit_product_name: str = Field(default="")

    # CASCADE con Sale para mantener sincronía con `cascade="all, delete-orphan"` ORM.
    sale_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("sale.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    # SET NULL: conservamos snapshots (name/barcode/category) aunque se borren los refs.
    product_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("product.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    product_variant_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("productvariant.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    product_batch_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("productbatch.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Trazabilidad de descuentos aplicados sobre el precio base.
    # SET NULL: conservamos el SaleItem (con su precio histórico) aunque la
    # promo o lista sean borradas; la trazabilidad se pierde graciosamente.
    applied_promotion_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("promotion.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    applied_price_list_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("pricelist.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    sale: Optional["Sale"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(
        back_populates="sale_items",
        sa_relationship_kwargs={"foreign_keys": "[SaleItem.product_id]"},
    )
    product_variant: Optional["ProductVariant"] = Relationship(
        back_populates="sale_items"
    )
    product_batch: Optional["ProductBatch"] = Relationship(
        back_populates="sale_items"
    )


class SaleInstallment(TenantMixin, rx.Model, table=True):
    """Cuotas de una venta a credito."""

    __tablename__ = "saleinstallment"

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
        CheckConstraint("number >= 1", name="ck_installment_number_positive"),
        CheckConstraint("amount >= 0", name="ck_installment_amount_nonneg"),
        CheckConstraint(
            "paid_amount >= 0", name="ck_installment_paid_amount_nonneg"
        ),
    )

    # CASCADE: cuotas desaparecen al borrar la venta.
    sale_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("sale.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
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


class CashboxSession(TenantMixin, rx.Model, table=True):
    """Sesion de caja (apertura/cierre)."""

    __tablename__ = "cashboxsession"

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
    counted_amount: Optional[Decimal] = Field(
        default=None,
        sa_column=sqlalchemy.Column(Numeric(10, 2), nullable=True),
    )
    denomination_detail: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.Text, nullable=True),
    )
    is_open: bool = Field(default=True)

    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

    user: Optional["User"] = Relationship(back_populates="sessions")


class CashboxLog(TenantMixin, rx.Model, table=True):
    """Log de movimientos de caja."""

    __tablename__ = "cashboxlog"

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
            sqlalchemy.DateTime(timezone=False),
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

    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

    user: Optional["User"] = Relationship(back_populates="logs")


class FieldReservation(TenantMixin, rx.Model, table=True):
    """Reserva de canchas deportivas."""

    __tablename__ = "fieldreservation"

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
            sqlalchemy.DateTime(timezone=False),
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

    cancellation_reason: Optional[str] = Field(default=None)
    delete_reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    user: Optional["User"] = Relationship(back_populates="reservations")


class PaymentMethod(TenantMixin, rx.Model, table=True):
    """Metodos de pago configurables."""

    __tablename__ = "paymentmethod"

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

    __tablename__ = "currency"

    code: str = Field(unique=True, index=True, nullable=False)
    name: str = Field(nullable=False)
    symbol: str = Field(nullable=False)


class CompanySettings(TenantMixin, rx.Model, table=True):
    """Configuracion de datos de empresa (singleton).

    Almacena la configuración global del negocio incluyendo
    país de operación, moneda y datos fiscales.
    """

    __tablename__ = "companysettings"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            name="uq_companysettings_company_branch",
        ),
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


class SaleReturn(TenantMixin, rx.Model, table=True):
    """Devolución total o parcial de una venta."""

    __tablename__ = "salereturn"

    __table_args__ = (
        sqlalchemy.Index(
            "ix_salereturn_tenant_sale",
            "company_id",
            "branch_id",
            "original_sale_id",
        ),
        CheckConstraint(
            "refund_amount >= 0", name="ck_salereturn_refund_nonneg"
        ),
        # R1-03: dedup idempotente por tenant. MySQL permite N NULL en UNIQUE,
        # así que devoluciones legacy/internas sin token coexisten sin choque.
        sqlalchemy.UniqueConstraint(
            "company_id",
            "idempotency_key",
            name="uq_salereturn_company_idempotency_key",
        ),
    )

    timestamp: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )
    # R1-03: token opaco emitido por el frontend para deduplicar doble-click
    # y retries de red al confirmar una devolución. Scope: (company_id, key).
    idempotency_key: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.String(64),
            nullable=True,
            index=False,
        ),
    )
    # CASCADE: la devolución se borra si desaparece la venta original (rarísimo
    # pero mantiene integridad referencial en casos de hard-delete).
    original_sale_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("sale.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    reason: str = Field(default=ReturnReason.other, max_length=50, nullable=False)
    notes: str = Field(default="")
    refund_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    user_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    items: List["SaleReturnItem"] = Relationship(
        back_populates="sale_return",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class SaleReturnItem(TenantMixin, rx.Model, table=True):
    """Ítem individual devuelto, vinculado al SaleItem original.

    Incluye ``company_id``/``branch_id`` denormalizados desde el parent
    ``SaleReturn`` para que el listener multi-tenant lo filtre directamente
    sin requerir JOIN — previene leaks cross-tenant en queries directos.
    """

    __tablename__ = "salereturnitem"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0", name="ck_salereturnitem_quantity_positive"
        ),
        CheckConstraint(
            "refund_subtotal >= 0", name="ck_salereturnitem_refund_nonneg"
        ),
        sqlalchemy.Index(
            "ix_salereturnitem_tenant_return",
            "company_id",
            "branch_id",
            "sale_return_id",
        ),
    )

    # CASCADE con el parent SaleReturn (alineado con cascade ORM).
    sale_return_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("salereturn.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    # RESTRICT explícito: si alguien intenta borrar el SaleItem original,
    # la devolución referente debe bloquearlo (trazabilidad fiscal).
    sale_item_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("saleitem.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    quantity: Decimal = Field(
        default=Decimal("0.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    refund_subtotal: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    product_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("product.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    product_variant_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("productvariant.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    product_batch_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("productbatch.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    sale_return: Optional[SaleReturn] = Relationship(back_populates="items")
