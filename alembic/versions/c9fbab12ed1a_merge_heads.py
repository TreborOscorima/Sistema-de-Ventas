"""merge heads

ID de revision: c9fbab12ed1a
Revisa: f1a2b3c4d5e6, i6j7k8l9m0n1
Fecha de creacion: 2026-02-05 22:36:43.482252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# identificadores de revision, usados por Alembic.
revision: str = 'c9fbab12ed1a'
down_revision: Union[str, Sequence[str], None] = ('f1a2b3c4d5e6', 'i6j7k8l9m0n1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    pass


def downgrade() -> None:
    """Revertir esquema."""
    pass
