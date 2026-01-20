from typing import List, TYPE_CHECKING

import reflex as rx
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
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


class User(rx.Model, table=True):
    """Modelo de usuario con RBAC."""

    username: str = Field(unique=True, index=True, nullable=False)
    password_hash: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    must_change_password: bool = Field(default=False)
    token_version: int = Field(default=0)

    role_id: int = Field(foreign_key="role.id")

    role: "Role" = Relationship(back_populates="users")
    sales: List["Sale"] = Relationship(back_populates="user")
    sessions: List["CashboxSession"] = Relationship(back_populates="user")
    logs: List["CashboxLog"] = Relationship(back_populates="user")
    reservations: List["FieldReservation"] = Relationship(back_populates="user")
