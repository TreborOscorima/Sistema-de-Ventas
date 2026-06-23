"""productkit_component_variant

Agrega component_variant_id (nullable) a productkit y actualiza el
UNIQUE constraint para permitir distintas variantes del mismo componente.

ID de revision: k6l7m8n9
Revisa: 4d9eff719ff6
Fecha de creacion: 2026-06-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "k6l7m8n9"
down_revision = "4d9eff719ff6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Agregar columna nullable
    op.add_column(
        "productkit",
        sa.Column(
            "component_variant_id",
            sa.Integer(),
            sa.ForeignKey("productvariant.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # 2. Reemplazar UNIQUE constraint para incluir la variante
    op.drop_constraint(
        "uq_productkit_company_branch_component",
        "productkit",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_productkit_company_branch_component_variant",
        "productkit",
        ["company_id", "branch_id", "kit_product_id", "component_product_id", "component_variant_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_productkit_company_branch_component_variant",
        "productkit",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_productkit_company_branch_component",
        "productkit",
        ["company_id", "branch_id", "kit_product_id", "component_product_id"],
    )
    op.drop_column("productkit", "component_variant_id")
