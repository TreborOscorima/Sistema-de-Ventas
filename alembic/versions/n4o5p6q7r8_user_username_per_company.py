"""make username unique per company

ID de revision: n4o5p6q7r8
Revisa: m3n4o5p6q7
Fecha de creacion: 2026-01-30 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# identificadores de revision, usados por Alembic.
revision: str = "n4o5p6q7r8"
down_revision: Union[str, Sequence[str], None] = "m3n4o5p6q7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    op.drop_index(op.f("ix_user_username"), table_name="user")
    op.create_index(op.f("ix_user_username"), "user", ["username"], unique=False)
    op.create_unique_constraint(
        "uq_user_company_username",
        "user",
        ["company_id", "username"],
    )


def downgrade() -> None:
    """Revertir esquema."""
    op.drop_constraint("uq_user_company_username", "user", type_="unique")
    op.drop_index(op.f("ix_user_username"), table_name="user")
    op.create_index(op.f("ix_user_username"), "user", ["username"], unique=True)
