"""add multi-vertical fields (ProductAttribute, requires_batch, min_stock_alert, business_vertical)

ID de revision: l6m7n8o9p0q1
Revisa: k5l6m7n8o9p0
Fecha de creacion: 2026-04-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision: str = "l6m7n8o9p0q1"
down_revision: Union[str, Sequence[str], None] = "k5l6m7n8o9p0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, name: str) -> bool:
    insp = sa_inspect(conn)
    return name in insp.get_table_names()


def _column_exists(conn, table: str, column: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return column in [c["name"] for c in insp.get_columns(table)]


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Create productattribute table
    if not _table_exists(conn, "productattribute"):
        op.create_table(
            "productattribute",
            sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False, index=True),
            sa.Column("attribute_name", sa.String(length=100), nullable=False, index=True),
            sa.Column("attribute_value", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("company.id"), nullable=False, index=True),
            sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branch.id"), nullable=False, index=True),
        )
        op.create_unique_constraint(
            "uq_productattribute_product_attr",
            "productattribute",
            ["company_id", "branch_id", "product_id", "attribute_name"],
        )
        op.create_index(
            "ix_productattribute_tenant_product",
            "productattribute",
            ["company_id", "branch_id", "product_id"],
        )
        op.create_index(
            "ix_productattribute_name_value",
            "productattribute",
            ["company_id", "attribute_name", "attribute_value"],
        )

    # 2. Add requires_batch to category
    if not _column_exists(conn, "category", "requires_batch"):
        op.add_column(
            "category",
            sa.Column("requires_batch", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )

    # 3. Add min_stock_alert to product
    if not _column_exists(conn, "product", "min_stock_alert"):
        op.add_column(
            "product",
            sa.Column(
                "min_stock_alert",
                sa.Numeric(precision=10, scale=4),
                nullable=False,
                server_default="5.0000",
            ),
        )

    # 4. Add business_vertical to companysettings
    if not _column_exists(conn, "companysettings", "business_vertical"):
        op.add_column(
            "companysettings",
            sa.Column(
                "business_vertical",
                sa.String(length=30),
                nullable=False,
                server_default="general",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, "companysettings", "business_vertical"):
        op.drop_column("companysettings", "business_vertical")

    if _column_exists(conn, "product", "min_stock_alert"):
        op.drop_column("product", "min_stock_alert")

    if _column_exists(conn, "category", "requires_batch"):
        op.drop_column("category", "requires_batch")

    if _table_exists(conn, "productattribute"):
        op.drop_table("productattribute")
