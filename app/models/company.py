from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum

import reflex as rx
from sqlmodel import Field, Relationship
import sqlalchemy
from .auth import UserBranch

if TYPE_CHECKING:
    from .auth import User


class PlanType(str, Enum):
    TRIAL = "trial"
    STANDARD = "standard"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    WARNING = "warning"
    PAST_DUE = "past_due"
    SUSPENDED = "suspended"


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
    plan_type: str = Field(
        default=PlanType.TRIAL,
        description="Nivel de suscripción actual",
    )
    max_branches: int = Field(default=2)
    max_users: int = Field(default=3)
    has_reservations_module: bool = Field(default=True)
    has_electronic_billing: bool = Field(default=False)
    subscription_status: str = Field(
        default=SubscriptionStatus.ACTIVE,
        description="Estado calculado de la suscripción",
    )
    subscription_ends_at: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    branches: List["Branch"] = Relationship(back_populates="company")
    users: List["User"] = Relationship(back_populates="company")


class Branch(rx.Model, table=True):
    """Sucursal de empresa."""

    company_id: int = Field(
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
