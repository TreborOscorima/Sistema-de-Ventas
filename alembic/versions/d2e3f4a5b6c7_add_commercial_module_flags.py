"""Agrega flags de módulos comerciales a la tabla company.

Añade 4 columnas booleanas:
  has_presupuestos_module   → habilitado en Professional/Enterprise/Trial, no en Standard
  has_promociones_module    → ídem
  has_listas_precios_module → ídem
  has_etiquetas_module      → ídem

Todas con DEFAULT TRUE para no romper empresas existentes (serán ajustadas
manualmente desde el backoffice de owner según el plan contratado).

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-05-15
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("company") as batch_op:
        batch_op.add_column(
            sa.Column(
                "has_presupuestos_module",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "has_promociones_module",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "has_listas_precios_module",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "has_etiquetas_module",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("company") as batch_op:
        batch_op.drop_column("has_etiquetas_module")
        batch_op.drop_column("has_listas_precios_module")
        batch_op.drop_column("has_promociones_module")
        batch_op.drop_column("has_presupuestos_module")
