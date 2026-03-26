"""add document_lookup_cache table

ID de revision: 29fda6e1a809
Revisa: p6q7r8s9t0
Fecha de creacion: 2026-03-25 22:09:23.704158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# identificadores de revision, usados por Alembic.
revision: str = '29fda6e1a809'
down_revision: Union[str, Sequence[str], None] = 'p6q7r8s9t0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    # Verificar si la tabla antigua existe y eliminarla
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'documentlookupcache' in existing_tables:
        op.drop_table('documentlookupcache')

    # Crear la nueva tabla con nombre correcto (snake_case)
    if 'document_lookup_cache' not in existing_tables:
        op.create_table('document_lookup_cache',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('country', sa.String(length=5), nullable=False),
            sa.Column('doc_type', sa.String(length=10), nullable=False),
            sa.Column('doc_number', sa.String(length=20), nullable=False),
            sa.Column('legal_name', sa.String(length=300), nullable=False, server_default=''),
            sa.Column('fiscal_address', sa.String(length=500), nullable=False, server_default=''),
            sa.Column('status', sa.String(length=30), nullable=False, server_default=''),
            sa.Column('condition', sa.String(length=30), nullable=False, server_default=''),
            sa.Column('iva_condition', sa.String(length=50), nullable=False, server_default=''),
            sa.Column('iva_condition_code', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('raw_json', sa.Text(), nullable=False),
            sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.Column('not_found', sa.Boolean(), nullable=False, server_default='0'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('country', 'doc_number', name='uq_lookupcache_country_docnumber'),
        )
        op.create_index('ix_document_lookup_cache_country', 'document_lookup_cache', ['country'])
        op.create_index('ix_document_lookup_cache_doc_number', 'document_lookup_cache', ['doc_number'])


def downgrade() -> None:
    """Revertir esquema."""
    op.drop_index('ix_document_lookup_cache_doc_number', table_name='document_lookup_cache')
    op.drop_index('ix_document_lookup_cache_country', table_name='document_lookup_cache')
    op.drop_table('document_lookup_cache')
