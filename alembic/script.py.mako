"""${message}

ID de revision: ${up_revision}
Revisa: ${down_revision | comma,n}
Fecha de creacion: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# identificadores de revision, usados por Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Actualizar esquema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Revertir esquema."""
    ${downgrades if downgrades else "pass"}
