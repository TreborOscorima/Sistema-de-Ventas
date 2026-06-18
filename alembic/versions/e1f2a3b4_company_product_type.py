"""Agregar product_type a Company para soporte TUWAYKIFOOD.

Revision ID: e1f2a3b4
Revises: a1b2c3d4
Create Date: 2026-06-17

Motivo:
    TUWAYKIFOOD es un producto SaaS independiente para restaurantes.
    El campo product_type en Company distingue entre clientes del
    Sistema de Ventas ("ventas") y clientes de TUWAYKIFOOD ("food"),
    permitiendo que el Owner Admin gestione ambos productos desde un
    único panel de administración.

    Default "ventas" para todas las empresas existentes (sin impacto).

    Nota de migración: el upgrade es idempotente — verifica si la columna
    ya existe antes de agregarla, para soportar ambientes que aplicaron
    la versión anterior de esta migración (b2c3d4e5).
"""

import sqlalchemy as sa
from alembic import op


revision = "e1f2a3b4"
down_revision = "a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("company")]

    if "product_type" not in columns:
        op.add_column(
            "company",
            sa.Column(
                "product_type",
                sa.Enum(
                    "ventas",
                    "food",
                    name="producttype",
                    native_enum=False,
                    length=20,
                ),
                nullable=False,
                server_default="ventas",
            ),
        )

    indexes = [idx["name"] for idx in inspector.get_indexes("company")]
    if "ix_company_product_type" not in indexes:
        op.create_index(
            "ix_company_product_type",
            "company",
            ["product_type"],
        )


def downgrade() -> None:
    op.drop_index("ix_company_product_type", table_name="company")
    op.drop_column("company", "product_type")
