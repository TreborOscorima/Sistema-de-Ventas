"""add_purchaseitem_foreign_currency

Agrega 3 columnas nullable a purchaseitem para registrar la moneda
original del proveedor cuando difiere de la moneda de la empresa:
- original_price      : precio en la moneda del proveedor
- exchange_rate       : tipo de cambio utilizado
- original_currency_code : código ISO de la moneda del proveedor

El campo unit_cost y product.purchase_price siguen almacenando SIEMPRE
el precio en moneda local, garantizando consistencia en inventario y reportes.
Los registros existentes quedan con NULL en estas columnas (misma moneda).

Revision: o0p1q2r3
Revisa:   n9o0p1q2
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "o0p1q2r3"
down_revision = "n9o0p1q2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "purchaseitem",
        sa.Column("original_price", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "purchaseitem",
        sa.Column("exchange_rate", sa.Numeric(15, 6), nullable=True),
    )
    op.add_column(
        "purchaseitem",
        sa.Column("original_currency_code", sa.String(10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("purchaseitem", "original_currency_code")
    op.drop_column("purchaseitem", "exchange_rate")
    op.drop_column("purchaseitem", "original_price")
