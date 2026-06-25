"""add purchaseitem batch_number and variant_id

Revision ID: p1q2r3s4
Revises: o0p1q2r3
Create Date: 2026-06-24

"""
from alembic import op
import sqlalchemy as sa

revision = "p1q2r3s4"
down_revision = "o0p1q2r3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "purchaseitem",
        sa.Column("batch_number", sa.String(60), nullable=True),
    )
    op.add_column(
        "purchaseitem",
        sa.Column(
            "variant_id",
            sa.Integer,
            sa.ForeignKey("productvariant.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("purchaseitem", "variant_id")
    op.drop_column("purchaseitem", "batch_number")
