"""Migrar cashboxsession.denomination_detail de TEXT a JSON.

Revision ID: a1b2c3d4
Revises: a0b1c2d3
Create Date: 2026-06-06

Problema:
    ``CashboxSession.denomination_detail`` almacenaba la lista de
    denominaciones como JSON serializado en TEXT. El modelo Python usaba
    ``json.dumps`` al escribir y ``json.loads`` al leer, acoplando la
    serialización manualmente.

Solución:
    Cambiar la columna a tipo JSON nativo de MySQL. SQLAlchemy/SQLModel
    maneja la serialización automáticamente y el valor leído ya es ``list``.
    Los datos existentes en TEXT son JSON válido: MySQL los acepta sin
    transformación en el ALTER TABLE.

Idempotencia: verifica el tipo actual antes de alterar; downgrade revierte
a TEXT (los datos JSON son válidos en TEXT).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect, text


revision: str = "a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "cashboxsession"
COLUMN = "denomination_detail"


def _column_type(conn, table: str, column: str) -> str | None:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return None
    for col in insp.get_columns(table):
        if col["name"] == column:
            return type(col["type"]).__name__.upper()
    return None


def upgrade() -> None:
    conn = op.get_bind()
    col_type = _column_type(conn, TABLE, COLUMN)
    if col_type is not None and col_type != "JSON":
        op.alter_column(
            TABLE,
            COLUMN,
            type_=sa.JSON(),
            existing_type=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    conn = op.get_bind()
    col_type = _column_type(conn, TABLE, COLUMN)
    if col_type is not None and col_type == "JSON":
        op.alter_column(
            TABLE,
            COLUMN,
            type_=sa.Text(),
            existing_type=sa.JSON(),
            existing_nullable=True,
        )
