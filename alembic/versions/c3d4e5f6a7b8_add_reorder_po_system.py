"""Add automatic reorder PO system: default_supplier_id on product + purchaseorder/purchaseorderitem tables.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-15

Agrega:
- Product.default_supplier_id (FK nullable a Supplier) para reposición automática
- Tabla PurchaseOrder (órdenes de compra sugeridas/enviadas, distintas de Purchase fiscal)
- Tabla PurchaseOrderItem (líneas sugeridas con stock actual/mínimo para auditoría)

Idempotente: verifica existencia antes de crear columnas o tablas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return column in [c["name"] for c in insp.get_columns(table)]


def _table_exists(conn, table: str) -> bool:
    insp = sa_inspect(conn)
    return table in insp.get_table_names()


def _index_exists(conn, table: str, index: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return index in [i["name"] for i in insp.get_indexes(table)]


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Product.default_supplier_id
    if not _column_exists(conn, "product", "default_supplier_id"):
        op.add_column(
            "product",
            sa.Column(
                "default_supplier_id",
                sa.Integer(),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            "fk_product_default_supplier_id",
            "product",
            "supplier",
            ["default_supplier_id"],
            ["id"],
        )
        op.create_index(
            "ix_product_default_supplier_id",
            "product",
            ["default_supplier_id"],
        )

    # 2) PurchaseOrder
    if not _table_exists(conn, "purchaseorder"):
        op.create_table(
            "purchaseorder",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("company.id"), nullable=False, index=True),
            sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branch.id"), nullable=False, index=True),
            sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("supplier.id"), nullable=False, index=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft", index=True),
            sa.Column("total_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("auto_generated", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("converted_purchase_id", sa.Integer(), sa.ForeignKey("purchase.id"), nullable=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        )
        op.create_index(
            "ix_purchaseorder_tenant_status",
            "purchaseorder",
            ["company_id", "branch_id", "status"],
        )
        op.create_index(
            "ix_purchaseorder_supplier",
            "purchaseorder",
            ["supplier_id"],
        )

    # 3) PurchaseOrderItem
    if not _table_exists(conn, "purchaseorderitem"):
        op.create_table(
            "purchaseorderitem",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("purchase_order_id", sa.Integer(), sa.ForeignKey("purchaseorder.id"), nullable=False, index=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=True, index=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("company.id"), nullable=False, index=True),
            sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branch.id"), nullable=False, index=True),
            sa.Column("description_snapshot", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("barcode_snapshot", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("current_stock", sa.Numeric(10, 4), nullable=False, server_default="0.0000"),
            sa.Column("min_stock_alert", sa.Numeric(10, 4), nullable=False, server_default="0.0000"),
            sa.Column("suggested_quantity", sa.Numeric(10, 4), nullable=False, server_default="0.0000"),
            sa.Column("unit", sa.String(length=20), nullable=False, server_default="Unidad"),
            sa.Column("unit_cost", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
            sa.Column("subtotal", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        )
        op.create_index(
            "ix_poitem_order",
            "purchaseorderitem",
            ["purchase_order_id"],
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _table_exists(conn, "purchaseorderitem"):
        op.drop_index("ix_poitem_order", table_name="purchaseorderitem")
        op.drop_table("purchaseorderitem")

    if _table_exists(conn, "purchaseorder"):
        op.drop_index("ix_purchaseorder_supplier", table_name="purchaseorder")
        op.drop_index("ix_purchaseorder_tenant_status", table_name="purchaseorder")
        op.drop_table("purchaseorder")

    if _column_exists(conn, "product", "default_supplier_id"):
        if _index_exists(conn, "product", "ix_product_default_supplier_id"):
            op.drop_index("ix_product_default_supplier_id", table_name="product")
        op.drop_constraint("fk_product_default_supplier_id", "product", type_="foreignkey")
        op.drop_column("product", "default_supplier_id")
