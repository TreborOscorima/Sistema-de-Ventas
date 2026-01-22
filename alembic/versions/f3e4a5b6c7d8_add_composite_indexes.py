"""Add additional composite indexes for performance

Revision ID: f3e4a5b6c7d8
Revises: a5b6c7d8e9f0
Create Date: 2026-01-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f3e4a5b6c7d8'
down_revision: Union[str, None] = 'a5b6c7d8e9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nota: ix_saleinstallment_sale_status ya existe en migración a5b6c7d8e9f0
    
    # Índice compuesto para consultas de cuotas vencidas
    # Usado en: check_overdue_alerts, reportes de morosidad
    op.create_index(
        'ix_saleinstallment_duedate_status',
        'saleinstallment',
        ['due_date', 'status'],
        unique=False
    )
    
    # Índice para consultas de logs de caja por fecha y acción
    # Usado en: reportes de caja, historial
    op.create_index(
        'ix_cashboxlog_timestamp_action',
        'cashboxlog',
        ['timestamp', 'action'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_cashboxlog_timestamp_action', table_name='cashboxlog')
    op.drop_index('ix_saleinstallment_duedate_status', table_name='saleinstallment')
