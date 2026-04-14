"""Add Product.is_active and Client.email

Revision ID: 9fa5710a7a62
Revises: 5cb0f4e0b921
Create Date: 2026-04-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '9fa5710a7a62'
down_revision: Union[str, Sequence[str], None] = '5cb0f4e0b921'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Product.is_active — default True para todos los productos existentes
    op.add_column(
        'product',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
    )
    op.create_index('ix_product_is_active', 'product', ['is_active'])

    # Client.email
    op.add_column(
        'client',
        sa.Column('email', sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('client', 'email')
    op.drop_index('ix_product_is_active', table_name='product')
    op.drop_column('product', 'is_active')
