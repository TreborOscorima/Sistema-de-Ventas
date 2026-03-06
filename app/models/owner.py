"""
Modelos para el Backoffice de Owners (plataforma SaaS).
"""

from datetime import datetime
from typing import Optional

import reflex as rx
import sqlalchemy
from sqlmodel import Field


class OwnerAuditLog(rx.Model, table=True):
    """Registro de auditoría para acciones de owner sobre empresas."""

    __tablename__ = "owner_audit_log"
    __table_args__ = (
        sqlalchemy.Index("ix_owner_audit_log_actor", "actor_user_id"),
        sqlalchemy.Index("ix_owner_audit_log_company", "target_company_id"),
        sqlalchemy.Index("ix_owner_audit_log_action", "action"),
    )

    actor_user_id: Optional[int] = Field(
        foreign_key="user.id",
        default=None,
        nullable=True,
        description="Usuario owner que ejecutó la acción si existe en la tabla user",
    )
    actor_email: str = Field(
        nullable=False,
        description="Email del actor al momento de la acción",
    )
    target_company_id: int = Field(
        foreign_key="company.id",
        nullable=False,
        description="Empresa objetivo de la acción",
    )
    target_company_name: str = Field(
        default="",
        description="Nombre de la empresa al momento de la acción",
    )
    action: str = Field(
        max_length=100,
        nullable=False,
        description="Tipo de acción: change_plan, activate, suspend, reactivate, extend_trial, adjust_limits",
    )
    before_snapshot: str = Field(
        default="{}",
        sa_column=sqlalchemy.Column(sqlalchemy.Text, nullable=False),
        description="JSON con estado previo de los campos afectados",
    )
    after_snapshot: str = Field(
        default="{}",
        sa_column=sqlalchemy.Column(sqlalchemy.Text, nullable=False),
        description="JSON con estado posterior de los campos afectados",
    )
    reason: str = Field(
        default="",
        sa_column=sqlalchemy.Column(sqlalchemy.Text, nullable=False),
        description="Motivo obligatorio proporcionado por el owner",
    )
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,
        description="Dirección IP del actor si está disponible",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False),
            nullable=False,
            server_default=sqlalchemy.func.now(),
        ),
        description="Fecha y hora de la acción",
    )
