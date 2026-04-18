from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum

import reflex as rx
from sqlmodel import Field, Relationship
import sqlalchemy
from sqlalchemy import CheckConstraint
from .auth import UserBranch
from app.utils.timezone import utc_now_naive

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

    __tablename__ = "company"

    __table_args__ = (
        CheckConstraint("max_branches >= 1", name="ck_company_max_branches_min"),
        CheckConstraint("max_users >= 1", name="ck_company_max_users_min"),
    )

    name: str = Field(nullable=False, index=True)
    ruc: str = Field(nullable=False, index=True, unique=True)
    is_active: bool = Field(default=True)
    trial_ends_at: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )
    created_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )
    # Persistido como VARCHAR(20) + CHECK IN (...) para validar a nivel DB.
    # native_enum=False evita ENUM nativo de MySQL (inflexible en migraciones).
    plan_type: PlanType = Field(
        default=PlanType.TRIAL,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Enum(
                PlanType,
                native_enum=False,
                length=20,
                validate_strings=True,
                values_callable=lambda enum_cls: [m.value for m in enum_cls],
            ),
            nullable=False,
            server_default=PlanType.TRIAL.value,
        ),
    )
    max_branches: int = Field(default=2)
    max_users: int = Field(default=3)
    has_reservations_module: bool = Field(default=True)
    has_services_module: bool = Field(default=True)
    has_clients_module: bool = Field(default=True)
    has_credits_module: bool = Field(default=True)
    has_electronic_billing: bool = Field(default=False)
    subscription_status: SubscriptionStatus = Field(
        default=SubscriptionStatus.ACTIVE,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Enum(
                SubscriptionStatus,
                native_enum=False,
                length=20,
                validate_strings=True,
                values_callable=lambda enum_cls: [m.value for m in enum_cls],
            ),
            nullable=False,
            server_default=SubscriptionStatus.ACTIVE.value,
        ),
    )
    subscription_ends_at: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    branches: List["Branch"] = Relationship(back_populates="company")
    users: List["User"] = Relationship(back_populates="company")


class Branch(rx.Model, table=True):
    """Sucursal de empresa."""

    __tablename__ = "branch"

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
