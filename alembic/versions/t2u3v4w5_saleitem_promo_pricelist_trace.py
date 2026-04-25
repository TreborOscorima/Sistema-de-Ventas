"""Trazabilidad en SaleItem: applied_promotion_id + applied_price_list_id.

Permite reportar qué venta consumió qué promoción / qué lista de precios
sin tener que reconstruir desde el unit_price grabado.

Diseño:
  * Ambas columnas son ``INT NULL``: ventas existentes (legacy) quedan en NULL.
  * FK con ``ondelete=SET NULL``: si la promo o lista son borradas, el
    SaleItem conserva su precio histórico y simplemente pierde la referencia.
  * Índice por columna para queries de reporte ("ventas con promo X").

Idempotencia: la migración verifica columnas/FKs/índices antes de crear y
restaura el estado previo en downgrade sin pérdida de datos.

Revision ID: t2u3v4w5
Revises: s1t2u3v4w5x6
Create Date: 2026-04-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision = "t2u3v4w5"
down_revision = "s1t2u3v4w5x6"
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


def _fk_exists(conn, table: str, fk_name: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return any(fk["name"] == fk_name for fk in insp.get_foreign_keys(table))


# ─── Constantes de nombrado ──────────────────────────────────────────────────

TABLE = "saleitem"

COL_PROMO = "applied_promotion_id"
COL_PL = "applied_price_list_id"

IX_PROMO = "ix_saleitem_applied_promotion_id"
IX_PL = "ix_saleitem_applied_price_list_id"

FK_PROMO = "fk_saleitem_applied_promotion_id"
FK_PL = "fk_saleitem_applied_price_list_id"


# ─── upgrade ────────────────────────────────────────────────────────────────


def upgrade() -> None:
    conn = op.get_bind()

    # 1. applied_promotion_id (columna + FK + índice)
    if not _column_exists(conn, TABLE, COL_PROMO):
        op.add_column(
            TABLE,
            sa.Column(COL_PROMO, sa.Integer(), nullable=True),
        )
    if not _fk_exists(conn, TABLE, FK_PROMO):
        op.create_foreign_key(
            FK_PROMO,
            TABLE,
            "promotion",
            [COL_PROMO],
            ["id"],
            ondelete="SET NULL",
        )
    if not _index_exists(conn, TABLE, IX_PROMO):
        op.create_index(IX_PROMO, TABLE, [COL_PROMO])

    # 2. applied_price_list_id (columna + FK + índice)
    if not _column_exists(conn, TABLE, COL_PL):
        op.add_column(
            TABLE,
            sa.Column(COL_PL, sa.Integer(), nullable=True),
        )
    if not _fk_exists(conn, TABLE, FK_PL):
        op.create_foreign_key(
            FK_PL,
            TABLE,
            "pricelist",
            [COL_PL],
            ["id"],
            ondelete="SET NULL",
        )
    if not _index_exists(conn, TABLE, IX_PL):
        op.create_index(IX_PL, TABLE, [COL_PL])


# ─── downgrade ──────────────────────────────────────────────────────────────


def downgrade() -> None:
    conn = op.get_bind()

    if _index_exists(conn, TABLE, IX_PL):
        op.drop_index(IX_PL, table_name=TABLE)
    if _fk_exists(conn, TABLE, FK_PL):
        op.drop_constraint(FK_PL, TABLE, type_="foreignkey")
    if _column_exists(conn, TABLE, COL_PL):
        op.drop_column(TABLE, COL_PL)

    if _index_exists(conn, TABLE, IX_PROMO):
        op.drop_index(IX_PROMO, table_name=TABLE)
    if _fk_exists(conn, TABLE, FK_PROMO):
        op.drop_constraint(FK_PROMO, TABLE, type_="foreignkey")
    if _column_exists(conn, TABLE, COL_PROMO):
        op.drop_column(TABLE, COL_PROMO)
