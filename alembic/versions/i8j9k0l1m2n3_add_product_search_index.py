"""Add product search composite index

Revision ID: i8j9k0l1m2n3
Revises: h5i6j7k8l9m0
Create Date: 2026-01-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'i8j9k0l1m2n3'
down_revision: Union[str, None] = 'h5i6j7k8l9m0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Índice compuesto para búsquedas frecuentes de productos
    # Optimiza queries con WHERE description LIKE '%x%' OR barcode LIKE '%x%'
    # Nota: LIKE '%x%' no usa índices B-tree eficientemente, pero
    # el índice ayuda cuando se combina con otros filtros
    op.create_index(
        'ix_product_search',
        'product',
        ['category', 'description'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_product_search', table_name='product')
