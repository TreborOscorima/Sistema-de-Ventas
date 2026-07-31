"""user_receipt_print_preference

Agrega preferencia de impresión POR USUARIO (autoservicio del cajero) a la tabla
``user``. Permite que cada cajero de una misma sucursal imprima en el tamaño de
SU propia impresora (58 / 80 / A4 / ancho custom en mm) sin afectar a los demás.

Columnas:
  - ``receipt_paper``  VARCHAR(10) NULL  → '58' | '80' | 'a4' | '<mm>' | NULL(=hereda)
  - ``receipt_width``  INT NULL          → override opcional de ancho en caracteres

NULL en ambas = el usuario hereda la configuración de la sucursal. La cascada de
resolución en runtime es: usuario → sucursal → default (80).

Idempotente y reversible.

Revision ID: x9y0z1a2
Revises: w8x9y0z1
Create Date: 2026-07-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x9y0z1a2"
down_revision: Union[str, Sequence[str], None] = "w8x9y0z1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "user"


def _column_exists(conn, table: str, column: str) -> bool:
    return (
        conn.execute(
            sa.text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = :t "
                "AND column_name = :c"
            ),
            {"t": table, "c": column},
        ).scalar()
        > 0
    )


def upgrade() -> None:
    conn = op.get_bind()
    if not _column_exists(conn, TABLE, "receipt_paper"):
        op.add_column(
            TABLE,
            sa.Column("receipt_paper", sa.String(length=10), nullable=True),
        )
    if not _column_exists(conn, TABLE, "receipt_width"):
        op.add_column(
            TABLE,
            sa.Column("receipt_width", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, TABLE, "receipt_width"):
        op.drop_column(TABLE, "receipt_width")
    if _column_exists(conn, TABLE, "receipt_paper"):
        op.drop_column(TABLE, "receipt_paper")
