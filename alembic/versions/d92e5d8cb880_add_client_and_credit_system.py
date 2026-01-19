"""agregar clientes y sistema de credito

ID de revision: d92e5d8cb880
Revisa: b28929cd6087
Fecha de creacion: 2026-01-03 14:59:30.621413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# identificadores de revision, usados por Alembic.
revision: str = 'd92e5d8cb880'
down_revision: Union[str, Sequence[str], None] = 'b28929cd6087'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    # ### comandos autogenerados por Alembic - ajustar si es necesario! ###
    op.create_table('client',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('dni', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('phone', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('address', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('credit_limit', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('current_debt', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_client_dni'), 'client', ['dni'], unique=True)
    op.create_index(op.f('ix_client_name'), 'client', ['name'], unique=False)
    op.create_table('saleinstallment',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sale_id', sa.Integer(), nullable=False),
    sa.Column('number', sa.Integer(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('due_date', sa.DateTime(), nullable=True),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('paid_amount', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('payment_date', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['sale_id'], ['sale.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('sale', sa.Column('payment_condition', sqlmodel.sql.sqltypes.AutoString(), nullable=False))
    op.add_column('sale', sa.Column('client_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'sale', 'client', ['client_id'], ['id'])
    # ### fin de comandos de Alembic ###


def downgrade() -> None:
    """Revertir esquema."""
    # ### comandos autogenerados por Alembic - ajustar si es necesario! ###
    op.drop_constraint(None, 'sale', type_='foreignkey')
    op.drop_column('sale', 'client_id')
    op.drop_column('sale', 'payment_condition')
    op.drop_table('saleinstallment')
    op.drop_index(op.f('ix_client_name'), table_name='client')
    op.drop_index(op.f('ix_client_dni'), table_name='client')
    op.drop_table('client')
    # ### fin de comandos de Alembic ###
