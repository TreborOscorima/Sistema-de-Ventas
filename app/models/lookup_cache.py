"""Caché de consultas de documentos fiscales (RUC/DNI/CUIT).

Tabla tenant-agnostic: los datos fiscales son registros públicos
(padrón reducido SUNAT, padrón AFIP) y pueden ser compartidos
entre todos los tenants sin riesgo de filtración de datos.

TTLs:
    - RUC/CUIT: 24 horas (el padrón se actualiza diariamente)
    - DNI: 7 días (nombres casi nunca cambian)
    - Not found: 1 hora (cache negativo corto para permitir reintentos)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import reflex as rx
from sqlalchemy import Column, String, UniqueConstraint
from sqlmodel import Field


class DocumentLookupCache(rx.Model, table=True):
    """Caché de resultados de consulta de documentos fiscales."""

    country: str = Field(sa_column=Column(String(5), nullable=False, index=True))
    doc_type: str = Field(sa_column=Column(String(10), nullable=False))
    doc_number: str = Field(sa_column=Column(String(20), nullable=False, index=True))

    legal_name: str = Field(default="", sa_column=Column(String(255), nullable=False, server_default=""))
    fiscal_address: str = Field(default="", sa_column=Column(String(500), nullable=False, server_default=""))
    status: str = Field(default="", sa_column=Column(String(30), nullable=False, server_default=""))
    condition: str = Field(default="", sa_column=Column(String(30), nullable=False, server_default=""))

    # Argentina: condición IVA del contribuyente consultado
    iva_condition: str = Field(default="", sa_column=Column(String(30), nullable=False, server_default=""))
    iva_condition_code: int = Field(default=0)

    # Respuesta completa para debug/auditoría
    raw_json: Optional[str] = Field(default=None)

    # Timestamp de la consulta externa (para TTL)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("country", "doc_number", name="uq_lookup_cache_country_doc"),
    )
