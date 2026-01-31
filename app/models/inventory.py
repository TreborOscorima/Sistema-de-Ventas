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

    sale_items: List["SaleItem"] = Relationship(back_populates="product")


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
