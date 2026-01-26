"""add suppliers and purchase documents

Revision ID: j1k2l3m4n5
Revises: i8j9k0l1m2n3
Create Date: 2026-01-23 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'j1k2l3m4n5'
down_revision: Union[str, None] = 'i8j9k0l1m2n3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    op.create_table(
        'supplier',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('tax_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('phone', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('address', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_supplier_name'), 'supplier', ['name'], unique=False)
    op.create_index(op.f('ix_supplier_tax_id'), 'supplier', ['tax_id'], unique=True)

    op.create_table(
        'purchase',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doc_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('series', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('number', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('issue_date', sa.DateTime(), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency_code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['supplier.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_doc_type'), 'purchase', ['doc_type'], unique=False)
    op.create_index(op.f('ix_purchase_series'), 'purchase', ['series'], unique=False)
    op.create_index(op.f('ix_purchase_number'), 'purchase', ['number'], unique=False)
    op.create_index(op.f('ix_purchase_issue_date'), 'purchase', ['issue_date'], unique=False)
    op.create_index(op.f('ix_purchase_supplier_id'), 'purchase', ['supplier_id'], unique=False)
    op.create_index(op.f('ix_purchase_currency_code'), 'purchase', ['currency_code'], unique=False)
    op.create_unique_constraint(
        'uq_purchase_supplier_doc',
        'purchase',
        ['supplier_id', 'doc_type', 'series', 'number'],
    )

    op.create_table(
        'purchaseitem',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('purchase_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('description_snapshot', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('barcode_snapshot', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('category_snapshot', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('unit', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('unit_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], ),
        sa.ForeignKeyConstraint(['purchase_id'], ['purchase.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchaseitem_purchase_id'), 'purchaseitem', ['purchase_id'], unique=False)
    op.create_index(op.f('ix_purchaseitem_product_id'), 'purchaseitem', ['product_id'], unique=False)


def downgrade() -> None:
    """Revertir esquema."""
    op.drop_index(op.f('ix_purchaseitem_product_id'), table_name='purchaseitem')
    op.drop_index(op.f('ix_purchaseitem_purchase_id'), table_name='purchaseitem')
    op.drop_table('purchaseitem')
    op.drop_constraint('uq_purchase_supplier_doc', 'purchase', type_='unique')
    op.drop_index(op.f('ix_purchase_currency_code'), table_name='purchase')
    op.drop_index(op.f('ix_purchase_supplier_id'), table_name='purchase')
    op.drop_index(op.f('ix_purchase_issue_date'), table_name='purchase')
    op.drop_index(op.f('ix_purchase_number'), table_name='purchase')
    op.drop_index(op.f('ix_purchase_series'), table_name='purchase')
    op.drop_index(op.f('ix_purchase_doc_type'), table_name='purchase')
    op.drop_table('purchase')
    op.drop_index(op.f('ix_supplier_tax_id'), table_name='supplier')
    op.drop_index(op.f('ix_supplier_name'), table_name='supplier')
    op.drop_table('supplier')
