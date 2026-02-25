"""add has_services_module, has_clients_module, has_credits_module to company

ID de revision: e4f5a6b7c8d9
Revisa: d3e4f5a6b7c8
Fecha de creacion: 2026-02-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# identificadores de revision, usados por Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agregar flags de módulos: has_services_module, has_clients_module, has_credits_module."""
    bind = op.get_bind()
    insp = sa_inspect(bind)
    columns = [col["name"] for col in insp.get_columns("company")]

    if "has_services_module" not in columns:
        op.add_column(
            "company",
            sa.Column("has_services_module", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        )

    if "has_clients_module" not in columns:
        op.add_column(
            "company",
            sa.Column("has_clients_module", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        )

    if "has_credits_module" not in columns:
        op.add_column(
            "company",
            sa.Column("has_credits_module", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        )


def downgrade() -> None:
    """Eliminar flags de módulos agregados."""
    bind = op.get_bind()
    insp = sa_inspect(bind)
    columns = [col["name"] for col in insp.get_columns("company")]

    if "has_credits_module" in columns:
        op.drop_column("company", "has_credits_module")
    if "has_clients_module" in columns:
        op.drop_column("company", "has_clients_module")
    if "has_services_module" in columns:
        op.drop_column("company", "has_services_module")
