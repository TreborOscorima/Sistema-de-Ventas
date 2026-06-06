"""SaleInstallment.idempotency_key + UNIQUE (company_id, key).

Revision ID: a0b1c2d3
Revises: d2e3f4a5b6c7
Create Date: 2026-06-06

Problema:
    ``pay_installment`` no tenía guardia de idempotencia. Un doble-click del
    operador en la UI de cobranzas, un retry de red o un timeout podían
    registrar DOS cobros para la misma cuota.

Solución:
    1. Nueva columna ``idempotency_key VARCHAR(64) NULL`` en ``saleinstallment``.
    2. ``UniqueConstraint(company_id, idempotency_key)``: MySQL permite
       múltiples NULL en UNIQUE — cuotas legacy sin token coexisten.
    3. El servicio detectará el conflicto pre-flush y elevará
       ``DuplicatePaymentError`` con el ``installment_id`` original.

Idempotencia de la propia migración: verifica columna/constraint antes de
crear; downgrade restaura estado previo sin perder datos.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect


revision: str = "a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "saleinstallment"
COLUMN = "idempotency_key"
UQ_NAME = "uq_saleinstallment_company_idempotency_key"


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


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, TABLE, COLUMN):
        op.add_column(
            TABLE,
            sa.Column(COLUMN, sa.String(length=64), nullable=True),
        )

    if not _has_constraint(conn, TABLE, UQ_NAME):
        op.create_unique_constraint(
            UQ_NAME,
            TABLE,
            ["company_id", COLUMN],
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_constraint(conn, TABLE, UQ_NAME):
        op.drop_constraint(UQ_NAME, TABLE, type_="unique")

    if _has_column(conn, TABLE, COLUMN):
        op.drop_column(TABLE, COLUMN)
