"""Agregar campo consumer_defense_legend a CompanySettings (leyenda global).

Default company-wide de la leyenda de Defensa del Consumidor (Argentina).
Aplica a todas las sucursales; cada sucursal puede overridear con
Branch.consumer_defense_legend. La resolución en el recibo es:
override de sucursal -> global (este campo) -> vacío.

Revision ID: s4t5u6v7
Revises: r3s4t5u6
Create Date: 2026-07-25
"""

import sqlalchemy as sa
from alembic import op

revision = "s4t5u6v7"
down_revision = "r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "companysettings",
        sa.Column(
            "consumer_defense_legend",
            sa.String(500),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("companysettings", "consumer_defense_legend")
