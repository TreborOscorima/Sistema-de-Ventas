"""Layer 1 fix B1-08 — FiscalDocument.original_fiscal_doc_id + UNIQUE fina.

Revision ID: l4a5b6c7
Revises: l3x4y5z6
Create Date: 2026-04-17

Problema:
    La ``UniqueConstraint(company_id, sale_id, receipt_type)`` impedía
    emitir más de una Nota de Crédito sobre la misma venta, bloqueando
    anulaciones parciales sucesivas (caso válido según RG AFIP 1415 y
    reglas SUNAT).

Solución:
    1. Nueva columna ``original_fiscal_doc_id`` (FK self-ref SET NULL)
       para trazar cada NC hacia su comprobante original.
    2. Columna generada ``original_doc_key = COALESCE(original_fiscal_doc_id, 0)``
       que evita el comportamiento MySQL de permitir múltiples NULL en
       UNIQUE. Los docs sin NC (factura/boleta) quedan con key=0 y son
       únicos por (company_id, sale_id, receipt_type). Las NC quedan con
       key=id_del_original y admiten N distintas por venta.
    3. Swap de la UNIQUE antigua por la versión fina que incluye
       ``original_doc_key``.

Idempotencia: verificación previa de columna/constraint en cada paso.
Guardia de datos pre-existentes: si ya hay duplicados (company_id,
sale_id, receipt_type, COALESCE(original_fiscal_doc_id,0)), se aborta
el upgrade con mensaje accionable — no se migra ciegamente.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect


revision: str = "l4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "l3x4y5z6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "fiscaldocument"
LEGACY_UQ = "uq_fiscaldocument_company_sale_type"
NEW_UQ = "uq_fiscaldocument_company_sale_type_original"
NEW_FK = "fk_fiscaldocument_original"


def _has_column(conn, table: str, column: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def _has_constraint(conn, table: str, name: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    names = {uq["name"] for uq in insp.get_unique_constraints(table)}
    names |= {ix["name"] for ix in insp.get_indexes(table)}
    return name in names


def _has_fk(conn, table: str, name: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return name in {fk["name"] for fk in insp.get_foreign_keys(table)}


def upgrade() -> None:
    conn = op.get_bind()

    # 0. Guard: detectar duplicados pre-existentes antes de crear la UNIQUE
    if _has_column(conn, TABLE, "original_fiscal_doc_id"):
        dup_check = conn.execute(sa.text(
            """
            SELECT company_id, sale_id, receipt_type,
                   COALESCE(original_fiscal_doc_id, 0) AS k, COUNT(*) c
            FROM fiscaldocument
            GROUP BY company_id, sale_id, receipt_type,
                     COALESCE(original_fiscal_doc_id, 0)
            HAVING c > 1
            LIMIT 5
            """
        )).fetchall()
        if dup_check:
            raise RuntimeError(
                "Layer 1 B1-08: filas duplicadas por (company_id, sale_id, "
                "receipt_type, original_fiscal_doc_id) — ej.: "
                f"{[tuple(r) for r in dup_check]}. Limpiar antes de migrar."
            )

    # 1. ADD COLUMN original_fiscal_doc_id (FK self-ref)
    if not _has_column(conn, TABLE, "original_fiscal_doc_id"):
        op.add_column(
            TABLE,
            sa.Column(
                "original_fiscal_doc_id",
                sa.Integer(),
                nullable=True,
            ),
        )
    if not _has_fk(conn, TABLE, NEW_FK):
        op.create_foreign_key(
            NEW_FK,
            TABLE,
            TABLE,
            ["original_fiscal_doc_id"],
            ["id"],
            ondelete="SET NULL",
        )
    # Index sobre la FK para joins/lookups de NC → original
    if not _has_constraint(conn, TABLE, "ix_fiscaldocument_original_fiscal_doc_id"):
        op.create_index(
            "ix_fiscaldocument_original_fiscal_doc_id",
            TABLE,
            ["original_fiscal_doc_id"],
        )

    # 2. ADD COLUMN original_doc_key GENERATED STORED (MySQL 5.7+)
    if not _has_column(conn, TABLE, "original_doc_key"):
        op.execute(sa.text(
            "ALTER TABLE fiscaldocument "
            "ADD COLUMN original_doc_key INT NOT NULL "
            "GENERATED ALWAYS AS (COALESCE(original_fiscal_doc_id, 0)) STORED"
        ))

    # 3. Swap de UNIQUE: drop legacy, add new con original_doc_key
    if _has_constraint(conn, TABLE, LEGACY_UQ):
        op.drop_constraint(LEGACY_UQ, TABLE, type_="unique")
    if not _has_constraint(conn, TABLE, NEW_UQ):
        op.create_unique_constraint(
            NEW_UQ,
            TABLE,
            ["company_id", "sale_id", "receipt_type", "original_doc_key"],
        )


def downgrade() -> None:
    conn = op.get_bind()

    # 1. Drop UNIQUE nueva y restaurar legacy
    if _has_constraint(conn, TABLE, NEW_UQ):
        op.drop_constraint(NEW_UQ, TABLE, type_="unique")
    if not _has_constraint(conn, TABLE, LEGACY_UQ):
        op.create_unique_constraint(
            LEGACY_UQ,
            TABLE,
            ["company_id", "sale_id", "receipt_type"],
        )

    # 2. Drop generated column
    if _has_column(conn, TABLE, "original_doc_key"):
        op.drop_column(TABLE, "original_doc_key")

    # 3. Drop FK + columna
    if _has_constraint(conn, TABLE, "ix_fiscaldocument_original_fiscal_doc_id"):
        op.drop_index("ix_fiscaldocument_original_fiscal_doc_id", TABLE)
    if _has_fk(conn, TABLE, NEW_FK):
        op.drop_constraint(NEW_FK, TABLE, type_="foreignkey")
    if _has_column(conn, TABLE, "original_fiscal_doc_id"):
        op.drop_column(TABLE, "original_fiscal_doc_id")
