"""j5k6l7m8_str_max_length_constraints

Agrega max_length explícito a campos str sin límite definido.
Todos los campos pasan de AutoString (VARCHAR sin longitud → MySQL usa 255 implícito)
a VARCHAR con longitud explícita validada tanto a nivel ORM como DB.

NOTA DE PRODUCCIÓN: Esta migración ESTRECHA las columnas. MySQL verificará que
ningún valor existente supere el nuevo límite. Si algún valor lo supera, la migración
fallará sin modificar datos. Ejecutar ANTES: verificar longitudes con
  SELECT MAX(LENGTH(campo)) FROM tabla;

ID de revision: 4d9eff719ff6
Revisa: i4j5k6l7
Fecha de creacion: 2026-06-18 15:11:05.095107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# identificadores de revision, usados por Alembic.
revision: str = '4d9eff719ff6'
down_revision: Union[str, Sequence[str], None] = 'i4j5k6l7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Aplica max_length explícito a campos str relevantes."""
    # ── auth.role ────────────────────────────────────────────────────────────
    op.alter_column('role', 'name',
                    existing_type=sa.String(255), type_=sa.String(150),
                    existing_nullable=False)
    op.alter_column('role', 'description',
                    existing_type=sa.String(255), type_=sa.String(500),
                    existing_nullable=True)

    # ── auth.permission ──────────────────────────────────────────────────────
    op.alter_column('permission', 'codename',
                    existing_type=sa.String(255), type_=sa.String(100),
                    existing_nullable=False)
    op.alter_column('permission', 'description',
                    existing_type=sa.String(255), type_=sa.String(500),
                    existing_nullable=True)

    # ── auth.user ────────────────────────────────────────────────────────────
    op.alter_column('user', 'username',
                    existing_type=sa.String(255), type_=sa.String(150),
                    existing_nullable=False)

    # ── company.company ──────────────────────────────────────────────────────
    op.alter_column('company', 'name',
                    existing_type=sa.String(255), type_=sa.String(200),
                    existing_nullable=False)
    op.alter_column('company', 'ruc',
                    existing_type=sa.String(255), type_=sa.String(30),
                    existing_nullable=False)

    # ── company.branch ───────────────────────────────────────────────────────
    op.alter_column('branch', 'name',
                    existing_type=sa.String(255), type_=sa.String(150),
                    existing_nullable=False)
    op.alter_column('branch', 'address',
                    existing_type=sa.String(255), type_=sa.String(500),
                    existing_nullable=True)

    # ── client.client ────────────────────────────────────────────────────────
    op.alter_column('client', 'name',
                    existing_type=sa.String(255), type_=sa.String(200),
                    existing_nullable=False)
    op.alter_column('client', 'dni',
                    existing_type=sa.String(255), type_=sa.String(30),
                    existing_nullable=False)

    # ── purchases.supplier ───────────────────────────────────────────────────
    op.alter_column('supplier', 'name',
                    existing_type=sa.String(255), type_=sa.String(200),
                    existing_nullable=False)
    op.alter_column('supplier', 'tax_id',
                    existing_type=sa.String(255), type_=sa.String(30),
                    existing_nullable=False)

    # ── inventory.product ────────────────────────────────────────────────────
    op.alter_column('product', 'barcode',
                    existing_type=sa.String(255), type_=sa.String(100),
                    existing_nullable=False)
    op.alter_column('product', 'description',
                    existing_type=sa.String(255), type_=sa.String(500),
                    existing_nullable=False)
    op.alter_column('product', 'category',
                    existing_type=sa.String(255), type_=sa.String(100),
                    existing_nullable=False)

    # ── inventory.productcategory ────────────────────────────────────────────
    op.alter_column('productcategory', 'name',
                    existing_type=sa.String(255), type_=sa.String(100),
                    existing_nullable=False)

    # ── inventory.unittype ───────────────────────────────────────────────────
    op.alter_column('unittype', 'name',
                    existing_type=sa.String(255), type_=sa.String(100),
                    existing_nullable=False)

    # ── sales.cashboxlog ─────────────────────────────────────────────────────
    op.alter_column('cashboxlog', 'action',
                    existing_type=sa.String(255), type_=sa.String(100),
                    existing_nullable=False)

    # ── sales.currency ───────────────────────────────────────────────────────
    op.alter_column('currency', 'code',
                    existing_type=sa.String(255), type_=sa.String(10),
                    existing_nullable=False)
    op.alter_column('currency', 'name',
                    existing_type=sa.String(255), type_=sa.String(100),
                    existing_nullable=False)
    op.alter_column('currency', 'symbol',
                    existing_type=sa.String(255), type_=sa.String(10),
                    existing_nullable=False)


def downgrade() -> None:
    """Revierte a VARCHAR(255) sin límite explícito."""
    tables_cols = [
        ('role', 'name'), ('role', 'description'),
        ('permission', 'codename'), ('permission', 'description'),
        ('user', 'username'),
        ('company', 'name'), ('company', 'ruc'),
        ('branch', 'name'), ('branch', 'address'),
        ('client', 'name'), ('client', 'dni'),
        ('supplier', 'name'), ('supplier', 'tax_id'),
        ('product', 'barcode'), ('product', 'description'), ('product', 'category'),
        ('productcategory', 'name'),
        ('unittype', 'name'),
        ('cashboxlog', 'action'),
        ('currency', 'code'), ('currency', 'name'), ('currency', 'symbol'),
    ]
    for table, col in tables_cols:
        op.alter_column(table, col,
                        existing_type=sa.String(255), type_=sa.String(255),
                        existing_nullable=False)
