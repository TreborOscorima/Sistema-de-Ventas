"""Agrega módulos: Presupuestos, Ofertas/Promociones, Listas de Precios y Etiquetas.

Cambios:
  - Tabla pricelist         : Listas de precios nominadas
  - Tabla pricelistitem     : Ítems de precio override por producto/variante
  - Columna client.price_list_id : FK a pricelist
  - Tabla quotation         : Cabecera de presupuesto/cotización
  - Tabla quotationitem     : Ítems de presupuesto con descuento por línea
  - Tabla promotion         : Motor de ofertas y descuentos automáticos
  - Columna product.sale_price_updated_at : Timestamp de último cambio de precio

Revision ID: s1t2u3v4w5x6
Revises: n6c7d8e9
Create Date: 2026-04-23
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision = "s1t2u3v4w5x6"
down_revision = "n6c7d8e9"
branch_labels = None
depends_on = None


# ─── Helpers idempotentes ────────────────────────────────────────────────────

def _table_exists(conn, table: str) -> bool:
    return table in sa_inspect(conn).get_table_names()


def _column_exists(conn, table: str, column: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return column in [c["name"] for c in insp.get_columns(table)]


def _index_exists(conn, table: str, index_name: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return any(idx["name"] == index_name for idx in insp.get_indexes(table))


def _fk_exists(conn, table: str, fk_name: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    return any(fk["name"] == fk_name for fk in insp.get_foreign_keys(table))


def _constraint_exists(conn, table: str, constraint_name: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    try:
        ucs = insp.get_unique_constraints(table)
        if any(uc["name"] == constraint_name for uc in ucs):
            return True
    except Exception:
        pass
    try:
        cks = insp.get_check_constraints(table)
        return any(ck["name"] == constraint_name for ck in cks)
    except Exception:
        return False


# ─── upgrade ────────────────────────────────────────────────────────────────

def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. pricelist ──────────────────────────────────────────────────────
    if not _table_exists(conn, "pricelist"):
        op.create_table(
            "pricelist",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("company_id", sa.Integer, sa.ForeignKey("company.id"), nullable=False, index=True),
            sa.Column("branch_id", sa.Integer, sa.ForeignKey("branch.id"), nullable=False, index=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.text("0")),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
            sa.Column("currency_code", sa.String(10), nullable=False, server_default="PEN"),
            sa.Column("created_at", sa.DateTime, nullable=False),
            sa.UniqueConstraint("company_id", "branch_id", "name", name="uq_pricelist_company_branch_name"),
        )
        op.create_index("ix_pricelist_tenant_active", "pricelist", ["company_id", "branch_id", "is_active"])

    # ── 2. pricelistitem ──────────────────────────────────────────────────
    if not _table_exists(conn, "pricelistitem"):
        op.create_table(
            "pricelistitem",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("company_id", sa.Integer, sa.ForeignKey("company.id"), nullable=False, index=True),
            sa.Column("branch_id", sa.Integer, sa.ForeignKey("branch.id"), nullable=False, index=True),
            sa.Column("price_list_id", sa.Integer, sa.ForeignKey("pricelist.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id", ondelete="CASCADE"), nullable=True),
            sa.Column("product_variant_id", sa.Integer, sa.ForeignKey("productvariant.id", ondelete="CASCADE"), nullable=True),
            sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
            sa.Column("created_at", sa.DateTime, nullable=False),
            sa.UniqueConstraint(
                "company_id", "branch_id", "price_list_id", "product_id", "product_variant_id",
                name="uq_pricelistitem_list_product_variant",
            ),
            sa.CheckConstraint("unit_price >= 0", name="ck_pricelistitem_price_nonneg"),
        )
        op.create_index("ix_pricelistitem_tenant_list", "pricelistitem", ["company_id", "branch_id", "price_list_id"])
        op.create_index("ix_pricelistitem_tenant_product", "pricelistitem", ["company_id", "branch_id", "product_id"])

    # ── 3. client.price_list_id ───────────────────────────────────────────
    if not _column_exists(conn, "client", "price_list_id"):
        op.add_column(
            "client",
            sa.Column(
                "price_list_id",
                sa.Integer,
                sa.ForeignKey("pricelist.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        if not _index_exists(conn, "client", "ix_client_price_list_id"):
            op.create_index("ix_client_price_list_id", "client", ["price_list_id"])

    # ── 4. product.sale_price_updated_at ─────────────────────────────────
    if not _column_exists(conn, "product", "sale_price_updated_at"):
        op.add_column(
            "product",
            sa.Column(
                "sale_price_updated_at",
                sa.DateTime,
                nullable=True,
            ),
        )
        if not _index_exists(conn, "product", "ix_product_sale_price_updated_at"):
            op.create_index(
                "ix_product_sale_price_updated_at",
                "product",
                ["sale_price_updated_at"],
            )

    # ── 5. quotation ──────────────────────────────────────────────────────
    if not _table_exists(conn, "quotation"):
        op.create_table(
            "quotation",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("company_id", sa.Integer, sa.ForeignKey("company.id"), nullable=False, index=True),
            sa.Column("branch_id", sa.Integer, sa.ForeignKey("branch.id"), nullable=False, index=True),
            sa.Column("created_at", sa.DateTime, nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("validity_days", sa.Integer, nullable=False, server_default="15"),
            sa.Column("expires_at", sa.DateTime, nullable=True),
            sa.Column("total_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
            sa.Column("discount_percentage", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
            sa.Column("notes", sa.Text, nullable=True),
            sa.Column("idempotency_key", sa.String(64), nullable=True),
            sa.Column("converted_sale_id", sa.Integer, sa.ForeignKey("sale.id", ondelete="SET NULL"), nullable=True),
            sa.Column("client_id", sa.Integer, sa.ForeignKey("client.id", ondelete="SET NULL"), nullable=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint("company_id", "idempotency_key", name="uq_quotation_company_idempotency_key"),
            sa.CheckConstraint("total_amount >= 0", name="ck_quotation_total_nonneg"),
        )
        op.create_index(
            "ix_quotation_tenant_status_created",
            "quotation",
            ["company_id", "branch_id", "status", "created_at"],
        )
        op.create_index("ix_quotation_tenant_client", "quotation", ["company_id", "branch_id", "client_id"])
        op.create_index("ix_quotation_converted_sale", "quotation", ["converted_sale_id"])

    # ── 6. quotationitem ──────────────────────────────────────────────────
    if not _table_exists(conn, "quotationitem"):
        op.create_table(
            "quotationitem",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("company_id", sa.Integer, sa.ForeignKey("company.id"), nullable=False, index=True),
            sa.Column("branch_id", sa.Integer, sa.ForeignKey("branch.id"), nullable=False, index=True),
            sa.Column("quotation_id", sa.Integer, sa.ForeignKey("quotation.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id", ondelete="SET NULL"), nullable=True),
            sa.Column("product_variant_id", sa.Integer, sa.ForeignKey("productvariant.id", ondelete="SET NULL"), nullable=True),
            sa.Column("quantity", sa.Numeric(10, 4), nullable=False, server_default="1.0000"),
            sa.Column("unit_price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
            sa.Column("discount_percentage", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
            sa.Column("subtotal", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
            sa.Column("product_name_snapshot", sa.String(255), nullable=False, server_default=""),
            sa.Column("product_barcode_snapshot", sa.String(100), nullable=False, server_default=""),
            sa.Column("product_category_snapshot", sa.String(100), nullable=False, server_default=""),
            sa.CheckConstraint("quantity > 0", name="ck_quotationitem_quantity_positive"),
            sa.CheckConstraint("unit_price >= 0", name="ck_quotationitem_unit_price_nonneg"),
            sa.CheckConstraint("subtotal >= 0", name="ck_quotationitem_subtotal_nonneg"),
            sa.CheckConstraint(
                "discount_percentage >= 0 AND discount_percentage <= 100",
                name="ck_quotationitem_discount_range",
            ),
        )
        op.create_index(
            "ix_quotationitem_tenant_quotation",
            "quotationitem",
            ["company_id", "branch_id", "quotation_id"],
        )

    # ── 7. promotion ──────────────────────────────────────────────────────
    if not _table_exists(conn, "promotion"):
        op.create_table(
            "promotion",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("company_id", sa.Integer, sa.ForeignKey("company.id"), nullable=False, index=True),
            sa.Column("branch_id", sa.Integer, sa.ForeignKey("branch.id"), nullable=False, index=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("promotion_type", sa.String(20), nullable=False, server_default="percentage"),
            sa.Column("scope", sa.String(20), nullable=False, server_default="all"),
            sa.Column("discount_value", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
            sa.Column("min_quantity", sa.Integer, nullable=False, server_default="1"),
            sa.Column("free_quantity", sa.Integer, nullable=False, server_default="0"),
            sa.Column("starts_at", sa.DateTime, nullable=False),
            sa.Column("ends_at", sa.DateTime, nullable=False),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
            sa.Column("max_uses", sa.Integer, nullable=True),
            sa.Column("current_uses", sa.Integer, nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime, nullable=False),
            sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id", ondelete="SET NULL"), nullable=True),
            sa.Column("category", sa.String(100), nullable=True),
            sa.Column("created_by_user_id", sa.Integer, sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
            sa.CheckConstraint("discount_value >= 0", name="ck_promotion_discount_nonneg"),
            sa.CheckConstraint("starts_at <= ends_at", name="ck_promotion_dates_order"),
            sa.CheckConstraint("min_quantity >= 1", name="ck_promotion_min_qty_positive"),
        )
        op.create_index(
            "ix_promotion_tenant_active",
            "promotion",
            ["company_id", "branch_id", "is_active", "starts_at", "ends_at"],
        )
        op.create_index("ix_promotion_tenant_product", "promotion", ["company_id", "branch_id", "product_id"])


# ─── downgrade ───────────────────────────────────────────────────────────────

def downgrade() -> None:
    conn = op.get_bind()

    if _table_exists(conn, "promotion"):
        op.drop_table("promotion")

    if _table_exists(conn, "quotationitem"):
        op.drop_table("quotationitem")

    if _table_exists(conn, "quotation"):
        op.drop_table("quotation")

    if _column_exists(conn, "product", "sale_price_updated_at"):
        op.drop_column("product", "sale_price_updated_at")

    if _column_exists(conn, "client", "price_list_id"):
        op.drop_column("client", "price_list_id")

    if _table_exists(conn, "pricelistitem"):
        op.drop_table("pricelistitem")

    if _table_exists(conn, "pricelist"):
        op.drop_table("pricelist")
