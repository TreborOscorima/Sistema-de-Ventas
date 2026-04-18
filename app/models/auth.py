from typing import List, Optional, TYPE_CHECKING

import reflex as rx
import sqlalchemy
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from .company import Branch, Company
    from .sales import CashboxLog, CashboxSession, FieldReservation, Sale


class RolePermission(rx.Model, table=True):
    """Tabla intermedia para relacionar roles y permisos.

    Se mantiene ``id`` sintético inyectado por ``rx.Model``, pero el
    UNIQUE compuesto ``(role_id, permission_id)`` previene asignaciones
    duplicadas que inflarían el vínculo RBAC.
    """

    __tablename__ = "rolepermission"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_rolepermission_role_permission",
        ),
    )

    role_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("role.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    permission_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("permission.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )


class Role(rx.Model, table=True):
    """Rol configurable para RBAC."""

    __tablename__ = "role"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "name",
            name="uq_role_company_name",
        ),
    )

    company_id: int = Field(
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    name: str = Field(nullable=False)
    description: str = Field(default="")

    company: "Company" = Relationship()
    users: List["User"] = Relationship(back_populates="role")
    permissions: List["Permission"] = Relationship(
        back_populates="roles",
        link_model=RolePermission,
    )


class Permission(rx.Model, table=True):
    """Permiso granular asociado a roles."""

    __tablename__ = "permission"

    codename: str = Field(unique=True, index=True, nullable=False)
    description: str = Field(default="")

    roles: List["Role"] = Relationship(
        back_populates="permissions",
        link_model=RolePermission,
    )


class UserBranch(rx.Model, table=True):
    """Tabla intermedia para accesos de usuario a sucursales."""

    __tablename__ = "userbranch"

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

    __tablename__ = "user"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "username",
            name="uq_user_company_username",
        ),
        sqlalchemy.UniqueConstraint(
            "company_id",
            "email",
            name="uq_user_company_email",
        ),
    )

    username: str = Field(index=True, nullable=False)
    # Unicidad por (company_id, email) — un mismo email puede administrar
    # distintas empresas (owner contable, etc.). Ver migración Layer 1.
    email: Optional[str] = Field(default=None, index=True)
    password_hash: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    must_change_password: bool = Field(default=False)
    token_version: int = Field(default=0)
    is_platform_owner: bool = Field(default=False, description="Owner de la plataforma SaaS")

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
