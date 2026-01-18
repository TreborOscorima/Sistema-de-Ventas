"""fix merge conflict

Revision ID: 85fbebd58809
Revises: 4375e70a546e, f2d3c4b5a6b7
Create Date: 2026-01-18 17:44:38.315975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85fbebd58809'
down_revision: Union[str, Sequence[str], None] = ('4375e70a546e', 'f2d3c4b5a6b7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
