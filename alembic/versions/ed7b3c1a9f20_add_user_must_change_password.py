"""add_user_must_change_password

Revision ID: ed7b3c1a9f20
Revises: 85fbebd58809
Create Date: 2026-02-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ed7b3c1a9f20"
down_revision: Union[str, Sequence[str], None] = "85fbebd58809"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("user", "must_change_password", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "must_change_password")
