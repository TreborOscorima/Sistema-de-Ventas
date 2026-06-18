"""add fulltext index on client.name for POS search

Revision ID: f1g2h3i4
Revises: e1f2a3b4
Create Date: 2026-06-18
"""
from alembic import op

revision = 'f1g2h3i4'
down_revision = 'e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ft_client_name', 'client', ['name'], mysql_prefix='FULLTEXT')


def downgrade():
    op.drop_index('ft_client_name', table_name='client')
