"""Agregar max_units_per_transaction a promotion.

Revision ID: c2d3e4f5a7b9
Revises: b1c2d3e5f7a8
Create Date: 2026-05-12
"""

import sqlalchemy as sa
from alembic import op

revision = "c2d3e4f5a7b9"
down_revision = "b1c2d3e5f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "promotion",
        sa.Column("max_units_per_transaction", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_promotion_max_units_per_tx_pos",
        "promotion",
        "max_units_per_transaction IS NULL OR max_units_per_transaction >= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_promotion_max_units_per_tx_pos", "promotion", type_="check"
    )
    op.drop_column("promotion", "max_units_per_transaction")
