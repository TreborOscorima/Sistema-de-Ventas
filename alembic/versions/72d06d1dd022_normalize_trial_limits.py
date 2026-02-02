"""normalize_trial_limits

ID de revision: 72d06d1dd022
Revisa: 860d23acfa63
Fecha de creacion: 2026-01-31 22:50:07.121768

"""
from typing import Sequence, Union

from alembic import op


# identificadores de revision, usados por Alembic.
revision: str = '72d06d1dd022'
down_revision: Union[str, Sequence[str], None] = '860d23acfa63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    op.execute(
        """
        UPDATE company
        SET max_branches = 2,
            max_users = 3,
            has_reservations_module = 1,
            has_electronic_billing = 0
        WHERE plan_type = 'trial'
          AND max_branches = 1
          AND max_users = 2
        """
    )


def downgrade() -> None:
    """Revertir esquema."""
    op.execute(
        """
        UPDATE company
        SET max_branches = 1,
            max_users = 2
        WHERE plan_type = 'trial'
          AND max_branches = 2
          AND max_users = 3
          AND has_reservations_module = 1
          AND has_electronic_billing = 0
        """
    )
