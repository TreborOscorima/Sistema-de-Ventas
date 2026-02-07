"""Add composite indexes for saleitem performance

Revision ID: h1i2j3k4l5
Revises: g7h8i9j0k1
Create Date: 2026-02-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h1i2j3k4l5"
down_revision: Union[str, Sequence[str], None] = "g7h8i9j0k1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_index(inspector, table: str, name: str) -> bool:
    return any(idx["name"] == name for idx in inspector.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_index(inspector, "saleitem", "ix_saleitem_company_branch_sale"):
        op.create_index(
            "ix_saleitem_company_branch_sale",
            "saleitem",
            ["company_id", "branch_id", "sale_id"],
            unique=False,
        )

    if not _has_index(inspector, "saleitem", "ix_saleitem_company_branch_product"):
        op.create_index(
            "ix_saleitem_company_branch_product",
            "saleitem",
            ["company_id", "branch_id", "product_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_index(inspector, "saleitem", "ix_saleitem_company_branch_product"):
        op.drop_index(
            "ix_saleitem_company_branch_product",
            table_name="saleitem",
        )

    if _has_index(inspector, "saleitem", "ix_saleitem_company_branch_sale"):
        op.drop_index(
            "ix_saleitem_company_branch_sale",
            table_name="saleitem",
        )
