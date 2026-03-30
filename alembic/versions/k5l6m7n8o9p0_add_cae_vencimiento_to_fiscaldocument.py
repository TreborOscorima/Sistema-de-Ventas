"""add cae_vencimiento to fiscal_document (AFIP CAE expiration date)

ID de revision: k5l6m7n8o9p0
Revisa: j4k5l6m7n8o9
Fecha de creacion: 2026-03-30 00:00:00.000000

Adds:
    - fiscal_document.cae_vencimiento VARCHAR(10) NULL
      Stores CAE expiration date (YYYYMMDD format) for AFIP/Argentina documents.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision: str = "k5l6m7n8o9p0"
down_revision: Union[str, Sequence[str], None] = "j4k5l6m7n8o9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return column in [c["name"] for c in insp.get_columns(table)]


def upgrade() -> None:
    conn = op.get_bind()
    if not _column_exists(conn, "fiscal_document", "cae_vencimiento"):
        op.add_column(
            "fiscal_document",
            sa.Column("cae_vencimiento", sa.String(10), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "fiscal_document", "cae_vencimiento"):
        op.drop_column("fiscal_document", "cae_vencimiento")
