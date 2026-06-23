"""nullable_product_sale_price

Hace product.sale_price nullable.
NULL = sin precio explícito, el precio efectivo se calcula desde el margen global.
NOT NULL = precio explícito guardado por el usuario.

Convierte sale_price = 0.00 a NULL cuando purchase_price > 0 (productos sin precio
configurado que usarán el margen global desde ahora).

Revision: m8n9o0p1
Revisa:   l7m8n9o0
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "m8n9o0p1"
down_revision = "l7m8n9o0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Quitar DEFAULT 0 y hacer la columna nullable
    op.alter_column(
        "product",
        "sale_price",
        existing_type=sa.Numeric(10, 2),
        nullable=True,
        server_default=None,
    )
    # 2. Productos con sale_price = 0 y purchase_price > 0 → NULL
    #    (nunca tuvieron precio configurado, ahora usarán el margen global)
    op.execute(
        "UPDATE product SET sale_price = NULL "
        "WHERE sale_price = 0.00 AND purchase_price > 0"
    )


def downgrade() -> None:
    # Restaurar 0.00 donde sea NULL antes de volver a NOT NULL
    op.execute("UPDATE product SET sale_price = 0.00 WHERE sale_price IS NULL")
    op.alter_column(
        "product",
        "sale_price",
        existing_type=sa.Numeric(10, 2),
        nullable=False,
        server_default=sa.text("0.00"),
    )
