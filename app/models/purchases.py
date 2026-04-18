from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

import reflex as rx
from sqlmodel import Field, Relationship
import sqlalchemy
from sqlalchemy import CheckConstraint, Numeric
from app.utils.timezone import utc_now_naive

from ._mixins import TenantMixin

if TYPE_CHECKING:
    from .auth import User
    from .inventory import Product


class Supplier(TenantMixin, rx.Model, table=True):
    """Proveedor de compras."""

    __tablename__ = "supplier"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "tax_id",
            name="uq_supplier_company_branch_tax_id",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}

    name: str = Field(nullable=False, index=True)
    tax_id: str = Field(nullable=False, index=True)
    email: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    purchases: List["Purchase"] = Relationship(back_populates="supplier")


class Purchase(TenantMixin, rx.Model, table=True):
    """Documento de compra (boleta/factura)."""

    __tablename__ = "purchase"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "supplier_id",
            "doc_type",
            "series",
            "number",
            name="uq_purchase_company_branch_supplier_doc",
        ),
        sqlalchemy.Index(
            "ix_purchase_issue_date",
            "issue_date",
        ),
        sqlalchemy.Index(
            "ix_purchase_tenant_date",
            "company_id",
            "branch_id",
            "issue_date",
        ),
        sqlalchemy.Index(
            "ix_purchase_tenant_supplier",
            "company_id",
            "branch_id",
            "supplier_id",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}

    doc_type: str = Field(nullable=False)
    series: str = Field(default="", nullable=False)
    number: str = Field(nullable=False)
    issue_date: datetime = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False),
            nullable=False,
        ),
    )
    total_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    currency_code: str = Field(default="PEN", index=True, nullable=False)
    notes: str = Field(default="", nullable=False)

    supplier_id: int = Field(foreign_key="supplier.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    supplier: "Supplier" = Relationship(back_populates="purchases")
    items: List["PurchaseItem"] = Relationship(
        back_populates="purchase",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    user: Optional["User"] = Relationship()


class PurchaseItem(TenantMixin, rx.Model, table=True):
    """Detalle de compra."""

    __tablename__ = "purchaseitem"

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_purchaseitem_quantity_positive"),
        CheckConstraint("unit_cost >= 0", name="ck_purchaseitem_unit_cost_nonneg"),
        CheckConstraint("subtotal >= 0", name="ck_purchaseitem_subtotal_nonneg"),
    )

    # CASCADE: al borrar la Purchase parent, sus items se van con ella.
    purchase_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("purchase.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    # SET NULL: preservamos el histórico aun si se borra el producto.
    product_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("product.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    description_snapshot: str = Field(default="")
    barcode_snapshot: str = Field(default="")
    category_snapshot: str = Field(default="")

    quantity: Decimal = Field(
        default=Decimal("0.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    unit: str = Field(default="Unidad")
    unit_cost: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    subtotal: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )

    purchase: "Purchase" = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship()


class PurchaseOrderStatus:
    """Estados posibles de una orden de compra sugerida/emitida.

    draft: generada automáticamente desde alertas de stock bajo, editable.
    sent: enviada al proveedor (no modificable en cantidades).
    received: recibida y convertida en Purchase real.
    cancelled: descartada manualmente.
    """
    DRAFT = "draft"
    SENT = "sent"
    RECEIVED = "received"
    CANCELLED = "cancelled"

    ALL = (DRAFT, SENT, RECEIVED, CANCELLED)


class PurchaseOrder(TenantMixin, rx.Model, table=True):
    """Orden de compra sugerida o enviada al proveedor.

    Distinta de Purchase (que representa el documento fiscal ya recibido).
    Una PurchaseOrder en estado 'received' se convierte en Purchase real.
    """

    __tablename__ = "purchaseorder"

    __table_args__ = (
        sqlalchemy.Index(
            "ix_purchaseorder_tenant_status",
            "company_id",
            "branch_id",
            "status",
        ),
        sqlalchemy.Index(
            "ix_purchaseorder_supplier",
            "supplier_id",
        ),
    )

    supplier_id: int = Field(foreign_key="supplier.id", index=True, nullable=False)
    status: str = Field(
        default=PurchaseOrderStatus.DRAFT,
        max_length=20,
        nullable=False,
        index=True,
    )
    total_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    notes: Optional[str] = Field(default=None, nullable=True)
    auto_generated: bool = Field(default=False, nullable=False)
    # Si es 'received', referencia a la Purchase que la materializó.
    converted_purchase_id: Optional[int] = Field(
        default=None,
        foreign_key="purchase.id",
        index=True,
    )
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )
    updated_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    supplier: "Supplier" = Relationship()
    items: List["PurchaseOrderItem"] = Relationship(
        back_populates="purchase_order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class PurchaseOrderItem(TenantMixin, rx.Model, table=True):
    """Ítem individual sugerido dentro de una PurchaseOrder."""

    __tablename__ = "purchaseorderitem"

    __table_args__ = (
        sqlalchemy.Index(
            "ix_poitem_order",
            "purchase_order_id",
        ),
        CheckConstraint(
            "suggested_quantity >= 0",
            name="ck_poitem_suggested_quantity_nonneg",
        ),
        CheckConstraint("unit_cost >= 0", name="ck_poitem_unit_cost_nonneg"),
    )

    # CASCADE: los ítems sugeridos mueren con la orden padre.
    purchase_order_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("purchaseorder.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    product_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("product.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    description_snapshot: str = Field(default="")
    barcode_snapshot: str = Field(default="")
    current_stock: Decimal = Field(
        default=Decimal("0.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    min_stock_alert: Decimal = Field(
        default=Decimal("0.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    suggested_quantity: Decimal = Field(
        default=Decimal("0.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    unit: str = Field(default="Unidad")
    unit_cost: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    subtotal: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )

    purchase_order: "PurchaseOrder" = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship()
