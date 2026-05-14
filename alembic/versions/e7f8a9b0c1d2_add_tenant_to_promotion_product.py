"""add_tenant_to_promotion_product

Agrega company_id y branch_id (NOT NULL + FK) a promotion_product
para aislar correctamente las asociaciones promo↔producto por sucursal.
Los valores se obtienen del JOIN con la tabla promotion.

ID de revision: e7f8a9b0c1d2
Revisa: f6a7b8c9d0e1
Fecha de creacion: 2026-05-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(bind) -> set:
    insp = sa.inspect(bind)
    return {c["name"] for c in insp.get_columns("promotion_product")}


def _existing_indexes(bind) -> set:
    insp = sa.inspect(bind)
    return {idx["name"] for idx in insp.get_indexes("promotion_product")}


def _existing_fks(bind) -> set:
    insp = sa.inspect(bind)
    return {fk["name"] for fk in insp.get_foreign_keys("promotion_product")}


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Agregar columnas solo si no existen (DDL puede haber corrido parcialmente)
    cols = _existing_columns(bind)
    if "company_id" not in cols:
        op.add_column(
            "promotion_product",
            sa.Column("company_id", sa.Integer(), nullable=True),
        )
    if "branch_id" not in cols:
        op.add_column(
            "promotion_product",
            sa.Column("branch_id", sa.Integer(), nullable=True),
        )

    # 2. Poblar desde promotion donde aún sean NULL
    op.execute(
        """
        UPDATE promotion_product pp
        JOIN promotion p ON pp.promotion_id = p.id
        SET pp.company_id = p.company_id,
            pp.branch_id  = p.branch_id
        WHERE pp.company_id IS NULL
           OR pp.branch_id  IS NULL
        """
    )

    # 3. Hacer NOT NULL (MODIFY COLUMN requiere tipo en MySQL)
    op.execute(
        """
        ALTER TABLE promotion_product
            MODIFY COLUMN company_id INT NOT NULL,
            MODIFY COLUMN branch_id  INT NOT NULL
        """
    )

    # 4. FK constraints (solo si no existen)
    fks = _existing_fks(bind)
    if "fk_promotion_product_company" not in fks:
        op.create_foreign_key(
            "fk_promotion_product_company",
            "promotion_product",
            "company",
            ["company_id"],
            ["id"],
        )
    if "fk_promotion_product_branch" not in fks:
        op.create_foreign_key(
            "fk_promotion_product_branch",
            "promotion_product",
            "branch",
            ["branch_id"],
            ["id"],
        )

    # 5. Índices (solo si no existen)
    idxs = _existing_indexes(bind)
    if "ix_promotion_product_company_id" not in idxs:
        op.create_index(
            "ix_promotion_product_company_id", "promotion_product", ["company_id"]
        )
    if "ix_promotion_product_branch_id" not in idxs:
        op.create_index(
            "ix_promotion_product_branch_id", "promotion_product", ["branch_id"]
        )
    if "ix_promotion_product_company_branch" not in idxs:
        op.create_index(
            "ix_promotion_product_company_branch",
            "promotion_product",
            ["company_id", "branch_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    idxs = _existing_indexes(bind)
    fks = _existing_fks(bind)
    cols = _existing_columns(bind)

    for idx in ("ix_promotion_product_company_branch",
                "ix_promotion_product_branch_id",
                "ix_promotion_product_company_id"):
        if idx in idxs:
            op.drop_index(idx, "promotion_product")

    for fk in ("fk_promotion_product_branch", "fk_promotion_product_company"):
        if fk in fks:
            op.drop_constraint(fk, "promotion_product", type_="foreignkey")

    for col in ("branch_id", "company_id"):
        if col in cols:
            op.drop_column("promotion_product", col)
