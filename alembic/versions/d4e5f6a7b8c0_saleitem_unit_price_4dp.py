"""SaleItem: unit_price y unit_price_base a NUMERIC(10,4).

Permite representar precios intermedios sin pérdida de precisión:
  * BUY_X_GET_Y con precio no divisible por tamaño de grupo
    (ej. $5.50 en grupos de 3 → $3.6667/u → subtotal exacto $11.00)
  * Descuentos porcentuales sobre precios impares

Con NUMERIC(10,2) el motor redondeaba el precio por-unidad ANTES de multiplicar
por la cantidad, generando un artefacto de $0.01 en el subtotal.

Revision ID: d4e5f6a7b8c0
Revises: c2d3e4f5a7b9
Create Date: 2026-05-12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision = "d4e5f6a7b8c0"
down_revision = "c2d3e4f5a7b9"
branch_labels = None
depends_on = None


def _col_type(conn, table: str, column: str) -> str | None:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return None
    for c in insp.get_columns(table):
        if c["name"] == column:
            return str(c["type"])
    return None


TABLE = "saleitem"


def upgrade() -> None:
    conn = op.get_bind()

    for col in ("unit_price", "unit_price_base"):
        col_type = _col_type(conn, TABLE, col)
        if col_type is None:
            continue
        if "10, 4" not in col_type and "10,4" not in col_type:
            op.alter_column(
                TABLE,
                col,
                existing_type=sa.Numeric(10, 2),
                type_=sa.Numeric(10, 4),
                existing_nullable=(col == "unit_price_base"),
                nullable=(col != "unit_price"),
                existing_server_default="0.00",
                server_default="0.0000",
            )


def downgrade() -> None:
    conn = op.get_bind()

    for col in ("unit_price", "unit_price_base"):
        col_type = _col_type(conn, TABLE, col)
        if col_type is None:
            continue
        if "10, 4" in col_type or "10,4" in col_type:
            op.alter_column(
                TABLE,
                col,
                existing_type=sa.Numeric(10, 4),
                type_=sa.Numeric(10, 2),
                existing_nullable=(col == "unit_price_base"),
                nullable=(col != "unit_price"),
                existing_server_default="0.0000",
                server_default="0.00",
            )
