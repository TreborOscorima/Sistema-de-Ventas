"""Agregar campo consumer_defense_legend a Branch.

Leyenda obligatoria de defensa del consumidor por jurisdicción
(requerida en Argentina por leyes provinciales: CABA Ley 3896,
PBA Ley 13.987, San Juan Ley 7984, etc.).

Revision ID: r3s4t5u6
Revises: q2r3s4t5
Create Date: 2026-07-11
"""

import sqlalchemy as sa
from alembic import op

revision = "r3s4t5u6"
down_revision = "q2r3s4t5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "branch",
        sa.Column(
            "consumer_defense_legend",
            sa.String(500),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("branch", "consumer_defense_legend")
