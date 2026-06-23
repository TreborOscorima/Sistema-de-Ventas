"""add_variant_sale_price

Agrega sale_price (nullable, DECIMAL 10,2) a productvariant.
NULL significa heredar precio del Product padre (comportamiento anterior).
NOT NULL significa precio exclusivo de esa variante.

ID de revision: l7m8n9o0
Revisa: k6l7m8n9
Fecha de creacion: 2026-06-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "l7m8n9o0"
down_revision = "k6l7m8n9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "productvariant",
        sa.Column("sale_price", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("productvariant", "sale_price")
