"""add_company_receipt_settings

Revision ID: a1b2c3d4e5f6
Revises: ed7b3c1a9f20
Create Date: 2026-02-01 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "ed7b3c1a9f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "companysettings",
        sa.Column(
            "receipt_paper",
            sa.String(length=10),
            nullable=False,
            server_default="80",
        ),
    )
    op.add_column(
        "companysettings",
        sa.Column("receipt_width", sa.Integer(), nullable=True),
    )
    op.alter_column("companysettings", "receipt_paper", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("companysettings", "receipt_width")
    op.drop_column("companysettings", "receipt_paper")
