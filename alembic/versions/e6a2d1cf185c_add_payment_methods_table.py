"""agregar tabla de metodos de pago

ID de revision: e6a2d1cf185c
Revisa: 4946658237b1
Fecha de creacion: 2026-01-04 07:01:08.589880

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# identificadores de revision, usados por Alembic.
revision: str = 'e6a2d1cf185c'
down_revision: Union[str, Sequence[str], None] = '4946658237b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    # ### comandos autogenerados por Alembic - ajustar si es necesario! ###
    # 1. LIMPIEZA DE EMERGENCIA: Borrar filas basura para permitir el índice único
    op.execute("DELETE FROM paymentmethod")
    #op.add_column('cashboxlog', sa.Column('payment_method_id', sa.Integer(), nullable=True))
    #op.create_foreign_key(None, 'cashboxlog', 'paymentmethod', ['payment_method_id'], ['id'])
    op.add_column('paymentmethod', sa.Column('code', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))
    op.add_column('paymentmethod', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('paymentmethod', sa.Column('allows_change', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index(op.f('ix_paymentmethod_code'), 'paymentmethod', ['code'], unique=True)
    op.add_column('salepayment', sa.Column('payment_method_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'salepayment', 'paymentmethod', ['payment_method_id'], ['id'])
    # ### fin de comandos de Alembic ###


def downgrade() -> None:
    """Revertir esquema."""
    # ### comandos autogenerados por Alembic - ajustar si es necesario! ###
    op.drop_constraint(None, 'salepayment', type_='foreignkey')
    op.drop_column('salepayment', 'payment_method_id')
    op.drop_index(op.f('ix_paymentmethod_code'), table_name='paymentmethod')
    op.drop_column('paymentmethod', 'allows_change')
    op.drop_column('paymentmethod', 'is_active')
    op.drop_column('paymentmethod', 'code')
    op.drop_constraint(None, 'cashboxlog', type_='foreignkey')
    op.drop_column('cashboxlog', 'payment_method_id')
    # ### fin de comandos de Alembic ###
