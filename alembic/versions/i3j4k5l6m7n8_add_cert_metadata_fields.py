"""add certificate metadata fields to companybillingconfig

ID de revision: i3j4k5l6m7n8
Revisa: h2i3j4k5l6m7
Fecha de creacion: 2026-03-28 00:00:00.000000

Adds:
    - companybillingconfig: cert_subject, cert_issuer,
      cert_not_before, cert_not_after columns
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# identificadores de revision, usados por Alembic.
revision: str = "i3j4k5l6m7n8"
down_revision: Union[str, Sequence[str], None] = "h2i3j4k5l6m7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    insp = sa_inspect(conn)
    columns = [c["name"] for c in insp.get_columns(table)]
    return column in columns


def upgrade() -> None:
    conn = op.get_bind()
    table = "companybillingconfig"

    new_cols = [
        ("cert_subject", sa.String(500), True),
        ("cert_issuer", sa.String(500), True),
        ("cert_not_before", sa.DateTime(), True),
        ("cert_not_after", sa.DateTime(), True),
    ]

    for col_name, col_type, nullable in new_cols:
        if not _column_exists(conn, table, col_name):
            op.add_column(
                table,
                sa.Column(col_name, col_type, nullable=nullable),
            )


def downgrade() -> None:
    for col_name in ("cert_not_after", "cert_not_before", "cert_issuer", "cert_subject"):
        op.drop_column("companybillingconfig", col_name)
