"""Promotion: tabla promotion_product para scope multi-producto.

Permite que una Promotion con scope=PRODUCT aplique a varios SKUs.
El motor de pricing cae al campo legacy ``promotion.product_id`` si no
existen filas aquí para esa promo (backward-compat sin backfill).

Revision ID: y7z8a9b0
Revises: x6y7z8a9
Create Date: 2026-05-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision = "y7z8a9b0"
down_revision = "x6y7z8a9"
branch_labels = None
depends_on = None

TABLE = "promotion_product"


def _table_exists(conn, table: str) -> bool:
    return table in sa_inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, TABLE):
        return

    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "promotion_id",
            sa.Integer,
            sa.ForeignKey("promotion.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer,
            sa.ForeignKey("product.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("promotion_id", "product_id", name="uq_promotion_product_pair"),
    )
    op.create_index("ix_promotion_product_promo", TABLE, ["promotion_id"])


def downgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, TABLE):
        return
    op.drop_index("ix_promotion_product_promo", TABLE)
    op.drop_table(TABLE)
