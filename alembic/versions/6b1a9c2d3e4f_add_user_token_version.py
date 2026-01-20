"""add token_version to user

ID de revision: 6b1a9c2d3e4f
Revisa: ed7b3c1a9f20
Fecha de creacion: 2026-02-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# identificadores de revision, usados por Alembic.
revision: str = "6b1a9c2d3e4f"
down_revision: Union[str, Sequence[str], None] = "3e2f9c1a7b5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    op.add_column(
        "user",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.alter_column("user", "token_version", server_default=None)


def downgrade() -> None:
    """Revertir esquema."""
    op.drop_column("user", "token_version")
