"""add ix_cashboxlog_company_branch_action index

Revision ID: g2h3i4j5
Revises: f1g2h3i4
Create Date: 2026-06-18
"""
from alembic import op

revision = 'g2h3i4j5'
down_revision = 'f1g2h3i4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'ix_cashboxlog_company_branch_action',
        'cashboxlog',
        ['company_id', 'branch_id', 'action'],
    )


def downgrade():
    op.drop_index('ix_cashboxlog_company_branch_action', table_name='cashboxlog')
