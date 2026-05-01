"""Promotion: coupon_code (códigos canjeables manualmente en el POS).

Las promos con ``coupon_code`` no se aplican automáticamente: el cliente debe
ingresar el código en el carrito. Las promos con ``coupon_code IS NULL``
mantienen el comportamiento previo (automáticas, evaluadas por scope/vigencia).

Diseño:
  * coupon_code: VARCHAR(40) NULL. Se normaliza a mayúsculas en el state.
  * UNIQUE (company_id, coupon_code) — MySQL trata NULL como distinto, así que
    múltiples promos automáticas conviven sin chocar.
  * Índice por coupon_code para lookup directo.

Idempotencia: helpers chequean existencia previa antes de crear.

Revision ID: v4w5x6y7
Revises: u3v4w5x6
Create Date: 2026-04-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision = "v4w5x6y7"
down_revision = "u3v4w5x6"
branch_labels = None
depends_on = None


# ─── Helpers idempotentes ────────────────────────────────────────────────────


def _column_exists(conn, table: str, column: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return column in [c["name"] for c in insp.get_columns(table)]


def _index_exists(conn, table: str, index_name: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return any(idx["name"] == index_name for idx in insp.get_indexes(table))


def _unique_exists(conn, table: str, name: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return any(uc.get("name") == name for uc in insp.get_unique_constraints(table))


# ─── Constantes ──────────────────────────────────────────────────────────────

TABLE = "promotion"
COL = "coupon_code"
IX = "ix_promotion_coupon_code"
UQ = "uq_promotion_company_coupon_code"


# ─── upgrade ────────────────────────────────────────────────────────────────


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, TABLE, COL):
        op.add_column(
            TABLE,
            sa.Column(COL, sa.String(length=40), nullable=True),
        )
    if not _index_exists(conn, TABLE, IX):
        op.create_index(IX, TABLE, [COL])
    if not _unique_exists(conn, TABLE, UQ):
        op.create_unique_constraint(UQ, TABLE, ["company_id", COL])


# ─── downgrade ──────────────────────────────────────────────────────────────


def downgrade() -> None:
    conn = op.get_bind()

    if _unique_exists(conn, TABLE, UQ):
        op.drop_constraint(UQ, TABLE, type_="unique")
    if _index_exists(conn, TABLE, IX):
        op.drop_index(IX, table_name=TABLE)
    if _column_exists(conn, TABLE, COL):
        op.drop_column(TABLE, COL)
