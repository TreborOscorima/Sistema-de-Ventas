"""Normalizar category.name a mayúsculas.

Revision ID: z8a9b0c1
Revises: y7z8a9b0
Create Date: 2026-05-02
"""

from alembic import op

revision = "z8a9b0c1"
down_revision = "y7z8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE category SET name = UPPER(name)")


def downgrade() -> None:
    pass
