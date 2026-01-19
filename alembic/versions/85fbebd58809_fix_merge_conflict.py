"""corregir conflicto de merge

ID de revision: 85fbebd58809
Revisa: 4375e70a546e, f2d3c4b5a6b7
Fecha de creacion: 2026-01-18 17:44:38.315975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# identificadores de revision, usados por Alembic.
revision: str = '85fbebd58809'
down_revision: Union[str, Sequence[str], None] = ('4375e70a546e', 'f2d3c4b5a6b7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    pass


def downgrade() -> None:
    """Revertir esquema."""
    pass
