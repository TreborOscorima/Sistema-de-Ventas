"""add_credit_and_reservation_indexes

Revision ID: f2d3c4b5a6b7
Revises: c41b78cb00e8
Create Date: 2026-01-18 19:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2d3c4b5a6b7"
down_revision: Union[str, Sequence[str], None] = "c41b78cb00e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        op.f("ix_saleinstallment_status"),
        "saleinstallment",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_saleinstallment_due_date"),
        "saleinstallment",
        ["due_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fieldreservation_start_datetime"),
        "fieldreservation",
        ["start_datetime"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_fieldreservation_start_datetime"),
        table_name="fieldreservation",
    )
    op.drop_index(
        op.f("ix_saleinstallment_due_date"),
        table_name="saleinstallment",
    )
    op.drop_index(
        op.f("ix_saleinstallment_status"),
        table_name="saleinstallment",
    )
