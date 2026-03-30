"""add platform_billing_settings table (master SaaS billing credentials)

ID de revision: j4k5l6m7n8o9
Revisa: i3j4k5l6m7n8
Fecha de creacion: 2026-03-30 00:00:00.000000

Adds:
    - platform_billing_settings table (singleton id=1)
      Fields: pe_nubefact_master_url, pe_nubefact_master_token, updated_at
    - Inserts the singleton row (id=1) with NULL values
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision: str = "j4k5l6m7n8o9"
down_revision: Union[str, Sequence[str], None] = "i3j4k5l6m7n8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, name: str) -> bool:
    return name in sa_inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "platform_billing_settings"):
        return

    op.create_table(
        "platform_billing_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pe_nubefact_master_url", sa.String(512), nullable=True),
        sa.Column("pe_nubefact_master_token", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Insertar singleton id=1 con valores NULL
    op.execute(
        "INSERT INTO platform_billing_settings (id, pe_nubefact_master_url, pe_nubefact_master_token, updated_at) "
        "VALUES (1, NULL, NULL, NULL)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "platform_billing_settings"):
        op.drop_table("platform_billing_settings")
