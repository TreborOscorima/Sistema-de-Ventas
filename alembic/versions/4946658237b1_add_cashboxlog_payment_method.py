"""agregar metodo de pago en cashboxlog

ID de revision: 4946658237b1
Revisa: d92e5d8cb880
Fecha de creacion: 2026-01-03 21:46:31.308187

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# identificadores de revision, usados por Alembic.
revision: str = '4946658237b1'
down_revision: Union[str, Sequence[str], None] = 'd92e5d8cb880'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    # ### comandos autogenerados por Alembic - ajustar si es necesario! ###
    op.add_column('cashboxlog', sa.Column('payment_method', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_index(op.f('ix_cashboxlog_payment_method'), 'cashboxlog', ['payment_method'], unique=False)
    # ### fin de comandos de Alembic ###


def downgrade() -> None:
    """Revertir esquema."""
    # ### comandos autogenerados por Alembic - ajustar si es necesario! ###
    op.drop_index(op.f('ix_cashboxlog_payment_method'), table_name='cashboxlog')
    op.drop_column('cashboxlog', 'payment_method')
    # ### fin de comandos de Alembic ###
