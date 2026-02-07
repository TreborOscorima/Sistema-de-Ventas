from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

import reflex as rx
from sqlmodel import Field, Relationship
import sqlalchemy
from sqlalchemy import Numeric

if TYPE_CHECKING:
    from .auth import User
    from .inventory import Product


class Supplier(rx.Model, table=True):
    """Proveedor de compras."""

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "tax_id",
            name="uq_supplier_company_branch_tax_id",
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
    name: str = Field(nullable=False, index=True)
    tax_id: str = Field(nullable=False, index=True)
    email: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    purchases: List["Purchase"] = Relationship(back_populates="supplier")


class Purchase(rx.Model, table=True):
    """Documento de compra (boleta/factura)."""

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
    )

    doc_type: str = Field(nullable=False, index=True)
    series: str = Field(default="", index=True, nullable=False)
    number: str = Field(nullable=False, index=True)
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
    supplier_id: int = Field(foreign_key="supplier.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    supplier: "Supplier" = Relationship(back_populates="purchases")
    items: List["PurchaseItem"] = Relationship(back_populates="purchase")
    user: Optional["User"] = Relationship()


class PurchaseItem(rx.Model, table=True):
    """Detalle de compra."""

    purchase_id: int = Field(foreign_key="purchase.id", index=True)
    product_id: Optional[int] = Field(
        default=None, foreign_key="product.id", index=True
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
