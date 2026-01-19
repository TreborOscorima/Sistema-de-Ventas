"""Actualizacion masiva produccion

ID de revision: 4375e70a546e
Revisa: c41b78cb00e8
Fecha de creacion: 2026-01-13 10:30:50.496225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# identificadores de revision, usados por Alembic.
revision: str = '4375e70a546e'
down_revision: Union[str, Sequence[str], None] = 'c41b78cb00e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    # ### comandos autogenerados por Alembic - ajustar si es necesario! ###
    pass
    # ### fin de comandos de Alembic ###


def downgrade() -> None:
    """Revertir esquema."""
    # ### comandos autogenerados por Alembic - ajustar si es necesario! ###
    pass
    # ### fin de comandos de Alembic ###
