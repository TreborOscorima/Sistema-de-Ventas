from typing import List, Optional, TYPE_CHECKING

import reflex as rx
import sqlalchemy
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from .company import Branch, Company
    from .sales import CashboxLog, CashboxSession, FieldReservation, Sale


class RolePermission(rx.Model, table=True):
    """Tabla intermedia para relacionar roles y permisos."""

    role_id: int = Field(foreign_key="role.id")
    permission_id: int = Field(foreign_key="permission.id")


class Role(rx.Model, table=True):
    """Rol configurable para RBAC."""

    name: str = Field(unique=True, index=True, nullable=False)
    description: str = Field(default="")

    users: List["User"] = Relationship(back_populates="role")
    permissions: List["Permission"] = Relationship(
        back_populates="roles",
        link_model=RolePermission,
    )


class Permission(rx.Model, table=True):
    """Permiso granular asociado a roles."""

    codename: str = Field(unique=True, index=True, nullable=False)
    description: str = Field(default="")

    roles: List["Role"] = Relationship(
        back_populates="permissions",
        link_model=RolePermission,
    )


class UserBranch(rx.Model, table=True):
    """Tabla intermedia para accesos de usuario a sucursales."""

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "user_id",
            "branch_id",
            name="uq_user_branch",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    branch_id: int = Field(foreign_key="branch.id")


class User(rx.Model, table=True):
    """Modelo de usuario con RBAC."""

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "username",
            name="uq_user_company_username",
        ),
    )

    username: str = Field(index=True, nullable=False)
    email: Optional[str] = Field(default=None, index=True, unique=True)
    password_hash: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    must_change_password: bool = Field(default=False)
    token_version: int = Field(default=0)

    company_id: int = Field(
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: Optional[int] = Field(
        default=None,
        foreign_key="branch.id",
        index=True,
    )
    role_id: int = Field(foreign_key="role.id")

    company: "Company" = Relationship(back_populates="users")
    branch: Optional["Branch"] = Relationship(back_populates="users")
    branches: List["Branch"] = Relationship(
        back_populates="members",
        link_model=UserBranch,
    )
    role: "Role" = Relationship(back_populates="users")
    sales: List["Sale"] = Relationship(back_populates="user")
    sessions: List["CashboxSession"] = Relationship(back_populates="user")
    logs: List["CashboxLog"] = Relationship(back_populates="user")
    reservations: List["FieldReservation"] = Relationship(back_populates="user")
