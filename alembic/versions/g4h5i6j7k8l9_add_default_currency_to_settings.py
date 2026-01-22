"""Add default_currency_code to CompanySettings

Revision ID: g4h5i6j7k8l9
Revises: f3e4a5b6c7d8
Create Date: 2026-01-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g4h5i6j7k8l9'
down_revision: Union[str, None] = 'f3e4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregar columna default_currency_code a companysettings
    # Default 'PEN' para instalaciones existentes (Perú)
    op.add_column(
        'companysettings',
        sa.Column('default_currency_code', sa.String(10), nullable=False, server_default='PEN')
    )


def downgrade() -> None:
    op.drop_column('companysettings', 'default_currency_code')
