from typing import List, Optional, TYPE_CHECKING
from decimal import Decimal

from sqlmodel import Field, Relationship, SQLModel
import sqlalchemy
from sqlalchemy import CheckConstraint, Numeric

from ._mixins import TenantMixin

if TYPE_CHECKING:
    from .sales import Sale
    from .price_lists import PriceList


class Client(TenantMixin, SQLModel, table=True):
    """Cliente para ventas a credito."""

    __tablename__ = "client"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "dni",
            name="uq_client_company_branch_dni",
        ),
        CheckConstraint("credit_limit >= 0", name="ck_client_credit_limit_nonneg"),
        CheckConstraint("current_debt >= 0", name="ck_client_current_debt_nonneg"),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, nullable=False, max_length=200)
    dni: str = Field(index=True, nullable=False, max_length=30)
    phone: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None, max_length=255)
    address: Optional[str] = Field(default=None)
    # Segmento comercial: nuevo | regular | vip | mayorista
    segment: Optional[str] = Field(default=None, max_length=20)
    credit_limit: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    current_debt: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )

    # Lista de precios asignada al cliente: resuelve precio automáticamente en venta.
    # NULL = usar precio base del producto.
    price_list_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("pricelist.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    sales: List["Sale"] = Relationship(back_populates="client")
    price_list: Optional["PriceList"] = Relationship(
        back_populates="clients",
        sa_relationship_kwargs={"foreign_keys": "[Client.price_list_id]"},
    )
