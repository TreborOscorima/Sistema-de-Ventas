"""agregar indices de rendimiento (correccion)

ID de revision: c41b78cb00e8
Revisa: e6a2d1cf185c
Fecha de creacion: 2026-01-04 08:15:25.971435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# identificadores de revision, usados por Alembic.
revision: str = 'c41b78cb00e8'
down_revision: Union[str, Sequence[str], None] = 'e6a2d1cf185c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    # ### comandos autogenerados por Alembic - ajustar si es necesario! ###
    op.create_index(op.f('ix_cashboxlog_action'), 'cashboxlog', ['action'], unique=False)
    op.create_index(op.f('ix_cashboxlog_payment_method_id'), 'cashboxlog', ['payment_method_id'], unique=False)
    op.create_index(op.f('ix_cashboxlog_timestamp'), 'cashboxlog', ['timestamp'], unique=False)
    op.create_index(op.f('ix_product_description'), 'product', ['description'], unique=False)
    op.create_index(op.f('ix_sale_client_id'), 'sale', ['client_id'], unique=False)
    op.create_index(op.f('ix_sale_timestamp'), 'sale', ['timestamp'], unique=False)
    # ### fin de comandos de Alembic ###


def downgrade() -> None:
    """Revertir esquema."""
    # ### comandos autogenerados por Alembic - ajustar si es necesario! ###
    op.drop_index(op.f('ix_sale_timestamp'), table_name='sale')
    op.drop_index(op.f('ix_sale_client_id'), table_name='sale')
    op.drop_index(op.f('ix_product_description'), table_name='product')
    op.drop_index(op.f('ix_cashboxlog_timestamp'), table_name='cashboxlog')
    op.drop_index(op.f('ix_cashboxlog_payment_method_id'), table_name='cashboxlog')
    op.drop_index(op.f('ix_cashboxlog_action'), table_name='cashboxlog')
    # ### fin de comandos de Alembic ###
