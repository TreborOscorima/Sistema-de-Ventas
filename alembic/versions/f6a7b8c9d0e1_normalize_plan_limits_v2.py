"""normalize_plan_limits_v2

Sincroniza max_branches y max_users de empresas existentes con los nuevos
límites por plan: Standard 2/5, Professional 5/10.

ID de revision: f6a7b8c9d0e1
Revisa: e5f6a7b8c9d0
Fecha de creacion: 2026-05-14

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE company
        SET max_branches = 2,
            max_users    = 5
        WHERE plan_type = 'standard'
        """
    )
    op.execute(
        """
        UPDATE company
        SET max_branches = 5,
            max_users    = 10
        WHERE plan_type = 'professional'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE company
        SET max_branches = 3,
            max_users    = 5
        WHERE plan_type = 'standard'
        """
    )
    op.execute(
        """
        UPDATE company
        SET max_branches = 10,
            max_users    = 15
        WHERE plan_type = 'professional'
        """
    )
