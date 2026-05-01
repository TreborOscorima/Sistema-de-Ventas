"""Promotion: weekdays_mask + time_from/time_to (banda horaria/día semana).

Permite restringir una promoción a días específicos de la semana y/o a una
ventana horaria del día. Casos de uso típicos:

  * "Sólo fines de semana" → mask = 96 (sábado=32 + domingo=64).
  * "Happy hour 18:00-21:00" → time_from=18:00, time_to=21:00.
  * "Lunes a viernes 9-13" → mask=31, time_from=09:00, time_to=13:00.

Diseño:
  * weekdays_mask: INT NOT NULL DEFAULT 127. 127 = todos los días, mantiene
    el comportamiento previo para promos existentes.
  * time_from / time_to: TIME NULL. Ambas NULL = aplica todo el día.
  * CheckConstraint 0..127 sobre weekdays_mask.

Idempotencia: helpers chequean existencia previa.

Revision ID: u3v4w5x6
Revises: t2u3v4w5
Create Date: 2026-04-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision = "u3v4w5x6"
down_revision = "t2u3v4w5"
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
        checks = insp.get_check_constraints(table)
    except NotImplementedError:
        return False
    return any(c.get("name") == name for c in checks)


# ─── Constantes ──────────────────────────────────────────────────────────────

TABLE = "promotion"
COL_MASK = "weekdays_mask"
COL_FROM = "time_from"
COL_TO = "time_to"
CHECK_MASK = "ck_promotion_weekdays_mask_range"


# ─── upgrade ────────────────────────────────────────────────────────────────


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, TABLE, COL_MASK):
        op.add_column(
            TABLE,
            sa.Column(
                COL_MASK,
                sa.Integer(),
                nullable=False,
                server_default="127",
            ),
        )
    if not _column_exists(conn, TABLE, COL_FROM):
        op.add_column(
            TABLE,
            sa.Column(COL_FROM, sa.Time(), nullable=True),
        )
    if not _column_exists(conn, TABLE, COL_TO):
        op.add_column(
            TABLE,
            sa.Column(COL_TO, sa.Time(), nullable=True),
        )

    if not _check_exists(conn, TABLE, CHECK_MASK):
        op.create_check_constraint(
            CHECK_MASK,
            TABLE,
            "weekdays_mask BETWEEN 0 AND 127",
        )


# ─── downgrade ──────────────────────────────────────────────────────────────


def downgrade() -> None:
    conn = op.get_bind()

    if _check_exists(conn, TABLE, CHECK_MASK):
        op.drop_constraint(CHECK_MASK, TABLE, type_="check")

    if _column_exists(conn, TABLE, COL_TO):
        op.drop_column(TABLE, COL_TO)
    if _column_exists(conn, TABLE, COL_FROM):
        op.drop_column(TABLE, COL_FROM)
    if _column_exists(conn, TABLE, COL_MASK):
        op.drop_column(TABLE, COL_MASK)
