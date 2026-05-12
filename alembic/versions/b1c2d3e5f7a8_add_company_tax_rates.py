"""Agregar tabla companytaxrate y campo show_tax_on_receipt.

Revision ID: b1c2d3e5f7a8
Revises: a9b0c1d2
Create Date: 2026-05-11
"""

import sqlalchemy as sa
from alembic import op

revision = "b1c2d3e5f7a8"
down_revision = "a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companytaxrate",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("tax_name", sa.String(20), nullable=False),
        sa.Column("label", sa.String(50), nullable=False),
        sa.Column("rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("display_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_companytaxrate_company", "companytaxrate", ["company_id"])
    op.create_index(
        "ix_companytaxrate_company_active",
        "companytaxrate",
        ["company_id", "is_active"],
    )

    op.add_column(
        "companysettings",
        sa.Column(
            "show_tax_on_receipt",
            sa.Boolean(),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    op.drop_column("companysettings", "show_tax_on_receipt")
    op.drop_index("ix_companytaxrate_company_active", table_name="companytaxrate")
    op.drop_index("ix_companytaxrate_company", table_name="companytaxrate")
    op.drop_table("companytaxrate")
