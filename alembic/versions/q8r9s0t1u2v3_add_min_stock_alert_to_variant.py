"""add min_stock_alert column to productvariant (nullable, inherits from product when null)

ID de revision: q8r9s0t1u2v3
Revisa: 1714b338ecb6
Fecha de creacion: 2026-04-08 00:00:00.000000

Permite umbral de alerta de stock bajo por variante (talla/color), independiente
del Product padre. Si la columna queda NULL, se hereda Product.min_stock_alert.

Caso de uso: una talla XL con stock 0 debe disparar alerta aunque el producto
raiz tenga stock total elevado en otras tallas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision: str = "q8r9s0t1u2v3"
down_revision: Union[str, Sequence[str], None] = "1714b338ecb6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return column in [c["name"] for c in insp.get_columns(table)]


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, "productvariant", "min_stock_alert"):
        op.add_column(
            "productvariant",
            sa.Column(
                "min_stock_alert",
                sa.Numeric(precision=10, scale=4),
                nullable=True,
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, "productvariant", "min_stock_alert"):
        op.drop_column("productvariant", "min_stock_alert")
