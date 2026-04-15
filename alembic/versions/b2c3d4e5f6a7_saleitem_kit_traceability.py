"""Add SaleItem.kit_product_id and kit_product_name for kit traceability

Revision ID: b2c3d4e5f6a7
Revises: 9fa5710a7a62
Create Date: 2026-04-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = '9fa5710a7a62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'saleitem',
        sa.Column('kit_product_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'saleitem',
        sa.Column('kit_product_name', sa.String(length=255), server_default='', nullable=False),
    )
    op.create_foreign_key(
        'fk_saleitem_kit_product_id',
        'saleitem',
        'product',
        ['kit_product_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_saleitem_kit_product_id', 'saleitem', type_='foreignkey')
    op.drop_column('saleitem', 'kit_product_name')
    op.drop_column('saleitem', 'kit_product_id')
