from typing import List, Optional, TYPE_CHECKING
from decimal import Decimal

import reflex as rx
from sqlmodel import Field, Relationship
import sqlalchemy
from sqlalchemy import Numeric

if TYPE_CHECKING:
    from .sales import Sale


class Client(rx.Model, table=True):
    """Cliente para ventas a credito."""

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "dni",
            name="uq_client_company_branch_dni",
        ),
    )

    name: str = Field(index=True, nullable=False)
    dni: str = Field(index=True, nullable=False)
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
    phone: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None)
    credit_limit: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    current_debt: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )

    sales: List["Sale"] = Relationship(back_populates="client")
