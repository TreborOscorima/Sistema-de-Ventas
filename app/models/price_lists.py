"""Modelos de Listas de Precios múltiples.

Permite definir listas de precios nominadas (Mayorista, Minorista, VIP, etc.)
y asignarlas por cliente. Al crear una venta para un cliente con lista
asignada, el sistema resuelve automáticamente el precio de esa lista.

Jerarquía de resolución de precio en la venta:
  1. PriceListItem (precio de lista del cliente) — mayor prioridad
  2. PriceTier (precio por volumen)
  3. Product.sale_price — precio base
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
    from .inventory import Product, ProductVariant
    from .client import Client


class PriceList(TenantMixin, rx.Model, table=True):
    """Lista de precios nominada (ej: Mayorista, VIP, Distribuidores)."""

    __tablename__ = "pricelist"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "name",
            name="uq_pricelist_company_branch_name",
        ),
        sqlalchemy.Index(
            "ix_pricelist_tenant_active",
            "company_id",
            "branch_id",
            "is_active",
        ),
    )

    name: str = Field(nullable=False, max_length=100, index=True)
    description: Optional[str] = Field(default=None, max_length=500)

    # Sólo una lista puede ser la predeterminada por empresa+sucursal
    is_default: bool = Field(
        default=False,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Boolean,
            nullable=False,
            server_default=sqlalchemy.text("0"),
            index=True,
        ),
    )
    is_active: bool = Field(
        default=True,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Boolean,
            nullable=False,
            server_default=sqlalchemy.text("1"),
            index=True,
        ),
    )

    currency_code: str = Field(default="PEN", max_length=10)

    created_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    items: List["PriceListItem"] = Relationship(
        back_populates="price_list",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
        },
    )
    clients: List["Client"] = Relationship(
        back_populates="price_list",
        sa_relationship_kwargs={"lazy": "select"},
    )


class PriceListItem(TenantMixin, rx.Model, table=True):
    """Precio override de un producto/variante dentro de una lista."""

    __tablename__ = "pricelistitem"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "price_list_id",
            "product_id",
            "product_variant_id",
            name="uq_pricelistitem_list_product_variant",
        ),
        sqlalchemy.Index(
            "ix_pricelistitem_tenant_list",
            "company_id",
            "branch_id",
            "price_list_id",
        ),
        sqlalchemy.Index(
            "ix_pricelistitem_tenant_product",
            "company_id",
            "branch_id",
            "product_id",
        ),
        CheckConstraint("unit_price >= 0", name="ck_pricelistitem_price_nonneg"),
    )

    price_list_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("pricelist.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    product_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("product.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    product_variant_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("productvariant.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )

    unit_price: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2), nullable=False),
    )

    created_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    price_list: Optional["PriceList"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship()
    product_variant: Optional["ProductVariant"] = Relationship()
