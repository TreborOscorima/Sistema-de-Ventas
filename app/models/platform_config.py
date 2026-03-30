"""Configuración global de la plataforma SaaS (singleton).

Este modelo almacena credenciales y parámetros a nivel plataforma,
compartidos por todas las empresas tenants. La tabla siempre tendrá
exactamente una fila (id=1), gestionada por el Owner.

Master billing credentials:
    - PE (Perú): Una sola cuenta Nubefact "integrador" cubre todas las
      empresas peruanas del SaaS. El Owner configura una vez; las empresas
      solo necesitan su RUC para emitir comprobantes.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
import reflex as rx
import sqlalchemy
from sqlalchemy import Text
from sqlmodel import Field
from app.utils.timezone import utc_now_naive


PLATFORM_CONFIG_ID = 1  # Singleton — siempre id=1


class PlatformBillingSettings(rx.Model, table=True):
    """Configuración global de billing a nivel SaaS (singleton, id=1).

    Modelo master: el Owner configura UNA vez las credenciales del
    proveedor de facturación. Todas las empresas del mismo país
    usan estas credenciales compartidas automáticamente.
    """

    __tablename__ = "platform_billing_settings"

    # ── PE — Nubefact Integrador Master ──────────────────────────
    pe_nubefact_master_url: Optional[str] = Field(
        default=None,
        max_length=512,
        description=(
            "URL maestra del endpoint Nubefact Integrador para todas las "
            "empresas PE. Ej: https://api.nubefact.com/api/v1/{ruta_integrador}"
        ),
    )
    pe_nubefact_master_token: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(Text, nullable=True),
        description="API token maestro de Nubefact, encriptado con Fernet.",
    )

    # ── Metadatos ─────────────────────────────────────────────────
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False), nullable=True
        ),
        description="Última actualización de configuración por el Owner.",
    )
