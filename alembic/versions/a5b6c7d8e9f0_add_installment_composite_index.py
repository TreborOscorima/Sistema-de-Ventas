"""Add composite index on SaleInstallment(sale_id, status).

Este índice optimiza las consultas frecuentes que filtran cuotas
por venta y estado, como:
- Obtener cuotas pendientes de una venta
- Verificar si una venta tiene cuotas vencidas
- Calcular deuda por venta

Revision ID: a5b6c7d8e9f0
Revises: 9c7b2e1f4a5d
Create Date: 2025-01-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5b6c7d8e9f0'
down_revision: Union[str, None] = '9c7b2e1f4a5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agregar índice compuesto para consultas de cuotas por venta y estado."""
    # Crear índice compuesto en (sale_id, status) para optimizar
    # consultas frecuentes como: WHERE sale_id = ? AND status = 'pending'
    op.create_index(
        'ix_saleinstallment_sale_status',
        'saleinstallment',
        ['sale_id', 'status'],
        unique=False
    )


def downgrade() -> None:
    """Eliminar índice compuesto."""
    op.drop_index('ix_saleinstallment_sale_status', table_name='saleinstallment')
