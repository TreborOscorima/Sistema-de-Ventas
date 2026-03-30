"""Modelo de caché para consultas de documentos fiscales (RUC/CUIT/DNI).

Los datos fiscales son registros públicos, por lo que la caché es
tenant-agnostic (compartida entre todas las empresas).

TTLs sugeridos:
    - RUC/CUIT: 24 horas (el padrón se actualiza diariamente).
    - DNI: 7 días (nombres casi nunca cambian).
    - Not found: 1 hora (cache negativo corto para permitir reintentos).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import reflex as rx
import sqlalchemy
from sqlalchemy import Text, UniqueConstraint
from sqlmodel import Field

from app.utils.timezone import utc_now_naive


class DocumentLookupCache(rx.Model, table=True):
    """Cache de resultados de consulta a APIs fiscales externas."""

    __tablename__ = "document_lookup_cache"

    __table_args__ = (
        UniqueConstraint(
            "country",
            "doc_number",
            name="uq_lookupcache_country_docnumber",
        ),
    )

    # ── Identificación del documento ──────────────────────────
    country: str = Field(
        max_length=5,
        index=True,
        description="Código ISO país: 'PE' (Perú) o 'AR' (Argentina).",
    )
    doc_type: str = Field(
        max_length=10,
        description="Tipo de documento: 'RUC', 'DNI', 'CUIT'.",
    )
    doc_number: str = Field(
        max_length=20,
        index=True,
        description="Número de documento fiscal consultado.",
    )

    # ── Datos del contribuyente ───────────────────────────────
    legal_name: str = Field(
        default="",
        max_length=300,
        description="Razón social o nombre completo.",
    )
    fiscal_address: str = Field(
        default="",
        max_length=500,
        description="Domicilio fiscal registrado.",
    )
    status: str = Field(
        default="",
        max_length=30,
        description="Estado del contribuyente: 'ACTIVO', 'BAJA', etc.",
    )
    condition: str = Field(
        default="",
        max_length=30,
        description="Condición tributaria PE: 'HABIDO', 'NO HABIDO'.",
    )

    # ── Campos específicos Argentina ──────────────────────────
    iva_condition: str = Field(
        default="",
        max_length=50,
        description="Condición IVA AR: 'RI', 'monotributo', 'exento'.",
    )
    iva_condition_code: int = Field(
        default=0,
        description="Código numérico condición IVA AR: 1=RI, 4=exento, 6=monotributo.",
    )

    # ── Respuesta cruda ───────────────────────────────────────
    # TEXT no admite DEFAULT en MySQL → nullable=True; el default Python "{}" aplica en app layer.
    raw_json: Optional[str] = Field(
        default="{}",
        sa_column=sqlalchemy.Column(Text, nullable=True),
        description="Respuesta completa de la API fiscal serializada como JSON.",
    )

    # ── Metadatos ─────────────────────────────────────────────
    fetched_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False),
            server_default=sqlalchemy.func.now(),
        ),
        description="Momento UTC en que se obtuvo la respuesta.",
    )
    not_found: bool = Field(
        default=False,
        description="True si el documento no fue encontrado en la API fiscal.",
    )
