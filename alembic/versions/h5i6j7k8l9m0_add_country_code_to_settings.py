"""Add country_code to CompanySettings

Revision ID: h5i6j7k8l9m0
Revises: g4h5i6j7k8l9
Create Date: 2026-01-22 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h5i6j7k8l9m0'
down_revision: Union[str, None] = 'g4h5i6j7k8l9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregar columna country_code a companysettings
    # Por defecto 'PE' (Perú) para instalaciones existentes
    op.add_column(
        'companysettings',
        sa.Column('country_code', sa.String(5), nullable=False, server_default='PE')
    )


def downgrade() -> None:
    op.drop_column('companysettings', 'country_code')
