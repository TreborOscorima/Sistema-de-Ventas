"""userbranch autoincrement id

ID de revision: c9f1a2b3c4d5
Revisa: b66fcf4607d8
Fecha de creacion: 2026-01-31 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# identificadores de revision, usados por Alembic.
revision: str = "c9f1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "3f8344b116db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    op.execute("ALTER TABLE userbranch MODIFY id INT NOT NULL AUTO_INCREMENT")


def downgrade() -> None:
    """Revertir esquema."""
    op.execute("ALTER TABLE userbranch MODIFY id INT NOT NULL")
