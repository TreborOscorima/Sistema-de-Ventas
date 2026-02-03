from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

import reflex as rx
from sqlmodel import Field, Relationship
import sqlalchemy
from sqlalchemy import Numeric

from app.enums import SportType

if TYPE_CHECKING:
    from .auth import User
    from .sales import SaleItem


class Product(rx.Model, table=True):
    """Modelo de producto de inventario."""

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "barcode",
            name="uq_product_company_branch_barcode",
        ),
    )

    barcode: str = Field(index=True, nullable=False)
    description: str = Field(nullable=False, index=True)
    category: str = Field(default="General", index=True)
    company_id: int = Field(
        default=1,
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        default=1,
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )
    stock: Decimal = Field(
        default=Decimal("0.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    unit: str = Field(default="Unidad")
    purchase_price: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    sale_price: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    location: Optional[str] = Field(default=None)

    sale_items: List["SaleItem"] = Relationship(back_populates="product")
    variants: List["ProductVariant"] = Relationship(back_populates="product")
    batches: List["ProductBatch"] = Relationship(back_populates="product")
    price_tiers: List["PriceTier"] = Relationship(back_populates="product")
    kit_components: List["ProductKit"] = Relationship(
        back_populates="kit_product",
        sa_relationship_kwargs={"foreign_keys": "[ProductKit.kit_product_id]"},
    )
    part_of_kits: List["ProductKit"] = Relationship(
        back_populates="component_product",
        sa_relationship_kwargs={"foreign_keys": "[ProductKit.component_product_id]"},
    )


class ProductVariant(rx.Model, table=True):
    """Variantes de producto (talla/color)."""

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "sku",
            name="uq_productvariant_company_branch_sku",
        ),
    )

    product_id: int = Field(foreign_key="product.id", index=True)
    sku: str = Field(index=True, nullable=False)
    size: Optional[str] = Field(default=None)
    color: Optional[str] = Field(default=None)
    stock: Decimal = Field(
        default=Decimal("0.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    company_id: int = Field(
        default=1,
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        default=1,
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )

    product: "Product" = Relationship(back_populates="variants")
    batches: List["ProductBatch"] = Relationship(back_populates="product_variant")
    price_tiers: List["PriceTier"] = Relationship(back_populates="product_variant")
    sale_items: List["SaleItem"] = Relationship(back_populates="product_variant")


class ProductBatch(rx.Model, table=True):
    """Lotes con vencimiento (FEFO)."""

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "product_id",
            "product_variant_id",
            "batch_number",
            name="uq_productbatch_company_branch_product_batch",
        ),
    )

    batch_number: str = Field(index=True, nullable=False)
    expiration_date: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )
    stock: Decimal = Field(
        default=Decimal("0.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    product_id: Optional[int] = Field(default=None, foreign_key="product.id")
    product_variant_id: Optional[int] = Field(
        default=None,
        foreign_key="productvariant.id",
    )
    company_id: int = Field(
        default=1,
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        default=1,
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )

    product: Optional["Product"] = Relationship(back_populates="batches")
    product_variant: Optional["ProductVariant"] = Relationship(
        back_populates="batches"
    )
    sale_items: List["SaleItem"] = Relationship(back_populates="product_batch")


class ProductKit(rx.Model, table=True):
    """Definicion de kits (producto compuesto)."""

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "kit_product_id",
            "component_product_id",
            name="uq_productkit_company_branch_component",
        ),
    )

    kit_product_id: int = Field(foreign_key="product.id", index=True)
    component_product_id: int = Field(foreign_key="product.id", index=True)
    quantity: Decimal = Field(
        default=Decimal("1.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    company_id: int = Field(
        default=1,
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        default=1,
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )

    kit_product: "Product" = Relationship(
        back_populates="kit_components",
        sa_relationship_kwargs={"foreign_keys": "[ProductKit.kit_product_id]"},
    )
    component_product: "Product" = Relationship(
        back_populates="part_of_kits",
        sa_relationship_kwargs={"foreign_keys": "[ProductKit.component_product_id]"},
    )


class PriceTier(rx.Model, table=True):
    """Escalas de precios por cantidad."""

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "product_id",
            "product_variant_id",
            "min_quantity",
            name="uq_pricetier_company_branch_product_minqty",
        ),
    )

    min_quantity: int = Field(nullable=False)
    unit_price: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    product_id: Optional[int] = Field(default=None, foreign_key="product.id")
    product_variant_id: Optional[int] = Field(
        default=None,
        foreign_key="productvariant.id",
    )
    company_id: int = Field(
        default=1,
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        default=1,
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )

    product: Optional["Product"] = Relationship(back_populates="price_tiers")
    product_variant: Optional["ProductVariant"] = Relationship(
        back_populates="price_tiers"
    )


class Category(rx.Model, table=True):
    """Categorias de productos."""

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "name",
            name="uq_category_company_branch_name",
        ),
    )

    name: str = Field(index=True, nullable=False)
    company_id: int = Field(
        default=1,
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        default=1,
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )


class StockMovement(rx.Model, table=True):
    """Movimientos de stock (ingresos, ajustes)."""

    timestamp: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )
    type: str = Field(nullable=False)
    quantity: Decimal = Field(
        default=Decimal("0.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    description: str = Field(default="")

    product_id: Optional[int] = Field(default=None, foreign_key="product.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    company_id: int = Field(
        default=1,
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        default=1,
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )

    product: Optional["Product"] = Relationship()
    user: Optional["User"] = Relationship()


class Unit(rx.Model, table=True):
    """Unidades de medida."""

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "name",
            name="uq_unit_company_branch_name",
        ),
    )

    company_id: int = Field(
        default=1,
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        default=1,
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )
    name: str = Field(index=True, nullable=False)
    allows_decimal: bool = Field(default=False)


class FieldPrice(rx.Model, table=True):
    """Precios de alquiler de canchas."""

    sport: SportType = Field(nullable=False)
    name: str = Field(nullable=False)
    company_id: int = Field(
        default=1,
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        default=1,
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )
    price: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
