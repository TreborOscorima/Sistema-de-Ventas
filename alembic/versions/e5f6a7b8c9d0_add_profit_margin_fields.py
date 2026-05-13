"""Agregar márgenes de ganancia porcentual.

Agrega:
  * companysettings.default_profit_margin  — margen global por empresa/sucursal
  * product.custom_profit_margin           — override opcional por producto

NULL en ambos campos significa "sin margen configurado / hereda nivel superior".
No modifica ningún valor de sale_price existente.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c0
Create Date: 2026-05-12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c0"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, "companysettings", "default_profit_margin"):
        op.add_column(
            "companysettings",
            sa.Column("default_profit_margin", sa.Numeric(5, 2), nullable=True),
        )

    if not _has_column(conn, "product", "custom_profit_margin"):
        op.add_column(
            "product",
            sa.Column("custom_profit_margin", sa.Numeric(5, 2), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_column(conn, "product", "custom_profit_margin"):
        op.drop_column("product", "custom_profit_margin")

    if _has_column(conn, "companysettings", "default_profit_margin"):
        op.drop_column("companysettings", "default_profit_margin")
