"""agregar campo must_change_password en usuario

ID de revision: ed7b3c1a9f20
Revisa: 85fbebd58809
Fecha de creacion: 2026-02-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# identificadores de revision, usados por Alembic.
revision: str = "ed7b3c1a9f20"
down_revision: Union[str, Sequence[str], None] = "85fbebd58809"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    op.add_column(
        "user",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("user", "must_change_password", server_default=None)


def downgrade() -> None:
    """Revertir esquema."""
    op.drop_column("user", "must_change_password")
