"""Promotion: min_cart_amount (umbral de subtotal del carrito).

Permite condicionar el disparo de la promo al subtotal del carrito (sumatoria
de ``qty × base_price`` antes de aplicar promociones). 0 = sin umbral, que es
el comportamiento histórico para no romper promos pre-migración.

Diseño:
  * NUMERIC(12, 2) NOT NULL DEFAULT 0.
  * CHECK ``min_cart_amount >= 0`` para evitar valores corruptos.
  * No requiere índice: el filtro se resuelve en Python tras el SELECT por
    tenant/scope, donde el cardinality ya está acotado por los índices
    existentes.

Idempotencia: helpers chequean existencia previa.

Revision ID: w5x6y7z8
Revises: v4w5x6y7
Create Date: 2026-04-27
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision = "w5x6y7z8"
down_revision = "v4w5x6y7"
branch_labels = None
depends_on = None


# ─── Helpers idempotentes ────────────────────────────────────────────────────


def _column_exists(conn, table: str, column: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return column in [c["name"] for c in insp.get_columns(table)]


def _check_exists(conn, table: str, name: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    try:
        return any(c.get("name") == name for c in insp.get_check_constraints(table))
    except NotImplementedError:
        return False


# ─── Constantes ──────────────────────────────────────────────────────────────

TABLE = "promotion"
COL = "min_cart_amount"
CK = "ck_promotion_min_cart_amount_nonneg"


# ─── upgrade ────────────────────────────────────────────────────────────────


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, TABLE, COL):
        op.add_column(
            TABLE,
            sa.Column(
                COL,
                sa.Numeric(12, 2),
                nullable=False,
                server_default="0.00",
            ),
        )

    if not _check_exists(conn, TABLE, CK):
        op.create_check_constraint(CK, TABLE, f"{COL} >= 0")


# ─── downgrade ──────────────────────────────────────────────────────────────


def downgrade() -> None:
    conn = op.get_bind()

    if _check_exists(conn, TABLE, CK):
        op.drop_constraint(CK, TABLE, type_="check")
    if _column_exists(conn, TABLE, COL):
        op.drop_column(TABLE, COL)
