"""Agregar campo segment a client.

Revision ID: a9b0c1d2
Revises: z8a9b0c1
Create Date: 2026-05-02
"""

import sqlalchemy as sa
from alembic import op

revision = "a9b0c1d2"
down_revision = "z8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "client",
        sa.Column("segment", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("client", "segment")
