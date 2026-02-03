"""add inventory vertical models

Revision ID: f1a2b3c4d5e6
Revises: 7ec2b7d14481
Create Date: 2026-02-02 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# identificadores de revision, usados por Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "7ec2b7d14481"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    op.add_column(
        "product",
        sa.Column("location", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )

    op.create_table(
        "productvariant",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("size", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("color", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("stock", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branch.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_productvariant_product_id"),
        "productvariant",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_productvariant_sku"),
        "productvariant",
        ["sku"],
        unique=False,
    )
    op.create_index(
        op.f("ix_productvariant_company_id"),
        "productvariant",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_productvariant_branch_id"),
        "productvariant",
        ["branch_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_productvariant_company_branch_sku",
        "productvariant",
        ["company_id", "branch_id", "sku"],
    )

    op.create_table(
        "productbatch",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_number", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("expiration_date", sa.DateTime(), nullable=True),
        sa.Column("stock", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_variant_id", sa.Integer(), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branch.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["product_variant_id"], ["productvariant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_productbatch_batch_number"),
        "productbatch",
        ["batch_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_productbatch_company_id"),
        "productbatch",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_productbatch_branch_id"),
        "productbatch",
        ["branch_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_productbatch_company_branch_product_batch",
        "productbatch",
        ["company_id", "branch_id", "product_id", "product_variant_id", "batch_number"],
    )

    op.create_table(
        "productkit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kit_product_id", sa.Integer(), nullable=False),
        sa.Column("component_product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branch.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["kit_product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["component_product_id"], ["product.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_productkit_kit_product_id"),
        "productkit",
        ["kit_product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_productkit_component_product_id"),
        "productkit",
        ["component_product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_productkit_company_id"),
        "productkit",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_productkit_branch_id"),
        "productkit",
        ["branch_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_productkit_company_branch_component",
        "productkit",
        ["company_id", "branch_id", "kit_product_id", "component_product_id"],
    )

    op.create_table(
        "pricetier",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("min_quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_variant_id", sa.Integer(), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branch.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["product_variant_id"], ["productvariant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pricetier_company_id"),
        "pricetier",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pricetier_branch_id"),
        "pricetier",
        ["branch_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_pricetier_company_branch_product_minqty",
        "pricetier",
        ["company_id", "branch_id", "product_id", "product_variant_id", "min_quantity"],
    )

    op.add_column(
        "saleitem",
        sa.Column("product_variant_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "saleitem",
        sa.Column("product_batch_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_saleitem_product_variant_id",
        "saleitem",
        "productvariant",
        ["product_variant_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_saleitem_product_batch_id",
        "saleitem",
        "productbatch",
        ["product_batch_id"],
        ["id"],
    )


def downgrade() -> None:
    """Revertir esquema."""
    op.drop_constraint(
        "fk_saleitem_product_batch_id",
        "saleitem",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_saleitem_product_variant_id",
        "saleitem",
        type_="foreignkey",
    )
    op.drop_column("saleitem", "product_batch_id")
    op.drop_column("saleitem", "product_variant_id")

    op.drop_constraint(
        "uq_pricetier_company_branch_product_minqty",
        "pricetier",
        type_="unique",
    )
    op.drop_index(op.f("ix_pricetier_branch_id"), table_name="pricetier")
    op.drop_index(op.f("ix_pricetier_company_id"), table_name="pricetier")
    op.drop_table("pricetier")

    op.drop_constraint(
        "uq_productkit_company_branch_component",
        "productkit",
        type_="unique",
    )
    op.drop_index(op.f("ix_productkit_branch_id"), table_name="productkit")
    op.drop_index(op.f("ix_productkit_company_id"), table_name="productkit")
    op.drop_index(
        op.f("ix_productkit_component_product_id"),
        table_name="productkit",
    )
    op.drop_index(
        op.f("ix_productkit_kit_product_id"),
        table_name="productkit",
    )
    op.drop_table("productkit")

    op.drop_constraint(
        "uq_productbatch_company_branch_product_batch",
        "productbatch",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_productbatch_branch_id"),
        table_name="productbatch",
    )
    op.drop_index(
        op.f("ix_productbatch_company_id"),
        table_name="productbatch",
    )
    op.drop_index(
        op.f("ix_productbatch_batch_number"),
        table_name="productbatch",
    )
    op.drop_table("productbatch")

    op.drop_constraint(
        "uq_productvariant_company_branch_sku",
        "productvariant",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_productvariant_branch_id"),
        table_name="productvariant",
    )
    op.drop_index(
        op.f("ix_productvariant_company_id"),
        table_name="productvariant",
    )
    op.drop_index(
        op.f("ix_productvariant_sku"),
        table_name="productvariant",
    )
    op.drop_index(
        op.f("ix_productvariant_product_id"),
        table_name="productvariant",
    )
    op.drop_table("productvariant")

    op.drop_column("product", "location")
