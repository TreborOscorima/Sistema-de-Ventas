"""SaleItem: unit_price_base (snapshot del precio pre-promo).

Permite que los reportes calculen el descuento otorgado por línea sin tener
que recomputar PriceList/Tier históricos (que pueden haber cambiado tras la
venta o ya no existir). Para filas pre-migración se back-fillea con
``unit_price`` → descuento implícito = 0 (no había contexto para distinguir).

Diseño:
  * NUMERIC(10, 2) NOT NULL DEFAULT 0.
  * Back-fill: ``UPDATE saleitem SET unit_price_base = unit_price WHERE
    unit_price_base = 0`` para no marcar como descuento histórico falso a
    ítems vendidos antes de tener el snapshot.

Idempotencia: helpers chequean existencia previa.

Revision ID: x6y7z8a9
Revises: w5x6y7z8
Create Date: 2026-04-27
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision = "x6y7z8a9"
down_revision = "w5x6y7z8"
branch_labels = None
depends_on = None


def _column_exists(conn, table: str, column: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return column in [c["name"] for c in insp.get_columns(table)]


TABLE = "saleitem"
COL = "unit_price_base"


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, TABLE, COL):
        op.add_column(
            TABLE,
            sa.Column(
                COL,
                sa.Numeric(10, 2),
                nullable=False,
                server_default="0.00",
            ),
        )
        # Back-fill: las filas existentes obtienen unit_price como base, lo que
        # implica descuento_histórico = 0 (no podemos reconstruir el descuento
        # real porque no se persistió en su momento). El reporte mostrará "—"
        # o 0 para esas líneas.
        op.execute(
            f"UPDATE {TABLE} SET {COL} = unit_price WHERE {COL} = 0"
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, TABLE, COL):
        op.drop_column(TABLE, COL)
