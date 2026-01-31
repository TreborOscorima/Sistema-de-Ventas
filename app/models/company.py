from typing import List, Optional, TYPE_CHECKING
from datetime import datetime

import reflex as rx
from sqlmodel import Field, Relationship
import sqlalchemy
from .auth import UserBranch

if TYPE_CHECKING:
    from .auth import User


class Company(rx.Model, table=True):
    """Empresa (tenant)."""

    name: str = Field(nullable=False, index=True)
    ruc: str = Field(nullable=False, index=True, unique=True)
    is_active: bool = Field(default=True)
    trial_ends_at: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    branches: List["Branch"] = Relationship(back_populates="company")
    users: List["User"] = Relationship(back_populates="company")


class Branch(rx.Model, table=True):
    """Sucursal de empresa."""

    company_id: int = Field(
        default=1,
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    name: str = Field(nullable=False, index=True)
    address: str = Field(default="", nullable=False)

    company: "Company" = Relationship(back_populates="branches")
    users: List["User"] = Relationship(back_populates="branch")
    members: List["User"] = Relationship(
        back_populates="branches",
        link_model=UserBranch,
    )
