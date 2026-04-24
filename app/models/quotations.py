"""Modelos de Presupuestos / Cotizaciones.

Un Quotation es un documento pre-venta que puede ser convertido a Sale
una vez aceptado por el cliente. Soporta línea de descuento por ítem,
fecha de vencimiento y trazabilidad al Sale de origen.
"""
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
    from .client import Client
    from .auth import User
    from .sales import Sale
    from .inventory import Product, ProductVariant


class QuotationStatus(str):
    """Estados posibles de un presupuesto."""
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONVERTED = "converted"


class Quotation(TenantMixin, rx.Model, table=True):
    """Cabecera de presupuesto/cotización."""

    __tablename__ = "quotation"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "idempotency_key",
            name="uq_quotation_company_idempotency_key",
        ),
        sqlalchemy.Index(
            "ix_quotation_tenant_status_created",
            "company_id",
            "branch_id",
            "status",
            "created_at",
        ),
        sqlalchemy.Index(
            "ix_quotation_tenant_client",
            "company_id",
            "branch_id",
            "client_id",
        ),
        CheckConstraint("total_amount >= 0", name="ck_quotation_total_nonneg"),
    )

    created_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False), index=True
        ),
    )
    status: str = Field(default=QuotationStatus.DRAFT, max_length=20, index=True)

    # Validez del presupuesto en días (default 15)
    validity_days: int = Field(default=15)
    expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False), nullable=True),
    )

    total_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )

    notes: Optional[str] = Field(default=None, sa_column=sqlalchemy.Column(sqlalchemy.Text))

    # Descuento global (porcentaje sobre el total, adicional a descuentos por línea)
    discount_percentage: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(5, 2), nullable=False, server_default="0.00"),
    )

    # Referencia al Sale cuando se convierte
    converted_sale_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("sale.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # Token de idempotencia para prevenir duplicados desde el frontend
    idempotency_key: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.String(64), nullable=True
        ),
    )

    client_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("client.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    user_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    client: Optional["Client"] = Relationship()
    user: Optional["User"] = Relationship()
    converted_sale: Optional["Sale"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Quotation.converted_sale_id]"}
    )
    items: List["QuotationItem"] = Relationship(
        back_populates="quotation",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
        },
    )


class QuotationItem(TenantMixin, rx.Model, table=True):
    """Ítem de presupuesto con snapshot y descuento por línea."""

    __tablename__ = "quotationitem"

    __table_args__ = (
        sqlalchemy.Index(
            "ix_quotationitem_tenant_quotation",
            "company_id",
            "branch_id",
            "quotation_id",
        ),
        CheckConstraint("quantity > 0", name="ck_quotationitem_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_quotationitem_unit_price_nonneg"),
        CheckConstraint("subtotal >= 0", name="ck_quotationitem_subtotal_nonneg"),
        CheckConstraint(
            "discount_percentage >= 0 AND discount_percentage <= 100",
            name="ck_quotationitem_discount_range",
        ),
    )

    quotation_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("quotation.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
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
    # Descuento a nivel de línea (%)
    discount_percentage: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(5, 2), nullable=False, server_default="0.00"),
    )
    subtotal: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )

    # Snapshots: preservan datos si el producto es eliminado
    product_name_snapshot: str = Field(default="", max_length=255)
    product_barcode_snapshot: str = Field(default="", max_length=100)
    product_category_snapshot: str = Field(default="", max_length=100)

    product_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("product.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
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

    quotation: Optional["Quotation"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship()
    product_variant: Optional["ProductVariant"] = Relationship()
