"""Add timezone to CompanySettings

Revision ID: i6j7k8l9m0n1
Revises: h5i6j7k8l9m0
Create Date: 2026-02-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "i6j7k8l9m0n1"
down_revision: Union[str, None] = "h5i6j7k8l9m0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "companysettings",
        sa.Column("timezone", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("companysettings", "timezone")
