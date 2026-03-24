"""add electronic billing tables and fiscal fields

ID de revision: g1h2i3j4k5l6
Revisa: f9a8b7c6d5e4
Fecha de creacion: 2026-03-20 00:00:00.000000

Adds:
    - companybillingconfig table (billing configuration per company)
    - fiscaldocument table (fiscal document per sale)
    - product.tax_included, product.tax_rate, product.tax_category columns
    - sale.receipt_type column
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# identificadores de revision, usados por Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, Sequence[str], None] = "f9a8b7c6d5e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, name: str) -> bool:
    insp = sa_inspect(conn)
    return name in insp.get_table_names()


def _column_exists(conn, table: str, column: str) -> bool:
    insp = sa_inspect(conn)
    if table not in insp.get_table_names():
        return False
    columns = [c["name"] for c in insp.get_columns(table)]
    return column in columns


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. CompanyBillingConfig table ──────────────────────────
    if not _table_exists(conn, "companybillingconfig"):
        op.create_table(
            "companybillingconfig",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            # Identification
            sa.Column("country", sa.String(5), server_default="PE", nullable=False),
            sa.Column("environment", sa.String(20), server_default="sandbox", nullable=False),
            sa.Column("tax_id", sa.String(20), server_default="", nullable=False),
            sa.Column("tax_id_type", sa.String(10), server_default="RUC", nullable=False),
            sa.Column("business_name", sa.String(255), server_default="", nullable=False),
            sa.Column("business_address", sa.String(255), server_default="", nullable=False),
            # Certificates (encrypted)
            sa.Column("encrypted_certificate", sa.Text(), nullable=True),
            sa.Column("encrypted_private_key", sa.Text(), nullable=True),
            # Nubefact (Peru)
            sa.Column("nubefact_url", sa.String(512), nullable=True),
            sa.Column("nubefact_token", sa.Text(), nullable=True),
            # AFIP (Argentina)
            sa.Column("afip_punto_venta", sa.Integer(), server_default="1", nullable=False),
            # Series / Numbering
            sa.Column("serie_factura", sa.String(10), server_default="F001", nullable=False),
            sa.Column("serie_boleta", sa.String(10), server_default="B001", nullable=False),
            sa.Column("current_sequence_factura", sa.Integer(), server_default="0", nullable=False),
            sa.Column("current_sequence_boleta", sa.Integer(), server_default="0", nullable=False),
            # Monthly quota
            sa.Column("current_billing_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("billing_count_reset_date", sa.DateTime(timezone=False), nullable=True),
            sa.Column("max_billing_limit", sa.Integer(), server_default="500", nullable=False),
            # State
            sa.Column("is_active", sa.Boolean(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
            # Constraints
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["company_id"], ["company.id"], name="fk_billingconfig_company"),
            sa.UniqueConstraint("company_id", name="uq_companybillingconfig_company"),
        )
        op.create_index("ix_companybillingconfig_company_id", "companybillingconfig", ["company_id"])

    # ── 2. FiscalDocument table ────────────────────────────────
    if not _table_exists(conn, "fiscaldocument"):
        op.create_table(
            "fiscaldocument",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            # Tenant
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("branch_id", sa.Integer(), nullable=False),
            # Sale link
            sa.Column("sale_id", sa.Integer(), nullable=False),
            # Type & numbering
            sa.Column("receipt_type", sa.String(20), server_default="boleta", nullable=False),
            sa.Column("serie", sa.String(10), server_default="", nullable=False),
            sa.Column("fiscal_number", sa.Integer(), nullable=True),
            sa.Column("full_number", sa.String(30), nullable=True),
            # Status
            sa.Column("fiscal_status", sa.String(20), server_default="pending", nullable=False),
            # Fiscal response
            sa.Column("cae_cdr", sa.Text(), nullable=True),
            sa.Column("fiscal_errors", sa.Text(), nullable=True),
            sa.Column("qr_data", sa.Text(), nullable=True),
            sa.Column("hash_code", sa.String(100), nullable=True),
            # XML audit trail
            sa.Column("xml_request", sa.Text(), nullable=True),
            sa.Column("xml_response", sa.Text(), nullable=True),
            # Retries
            sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
            # Timestamps
            sa.Column("sent_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("authorized_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            # Buyer snapshot
            sa.Column("buyer_doc_type", sa.String(5), nullable=True),
            sa.Column("buyer_doc_number", sa.String(20), nullable=True),
            sa.Column("buyer_name", sa.String(255), nullable=True),
            # Fiscal amounts
            sa.Column("taxable_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
            sa.Column("tax_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
            sa.Column("total_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
            # Constraints
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["company_id"], ["company.id"], name="fk_fiscaldoc_company"),
            sa.ForeignKeyConstraint(["branch_id"], ["branch.id"], name="fk_fiscaldoc_branch"),
            sa.ForeignKeyConstraint(["sale_id"], ["sale.id"], name="fk_fiscaldoc_sale"),
            sa.UniqueConstraint("company_id", "sale_id", name="uq_fiscaldocument_company_sale"),
        )
        op.create_index("ix_fiscaldocument_company_id", "fiscaldocument", ["company_id"])
        op.create_index("ix_fiscaldocument_branch_id", "fiscaldocument", ["branch_id"])
        op.create_index("ix_fiscaldocument_sale_id", "fiscaldocument", ["sale_id"])
        op.create_index("ix_fiscaldocument_receipt_type", "fiscaldocument", ["receipt_type"])
        op.create_index("ix_fiscaldocument_fiscal_status", "fiscaldocument", ["fiscal_status"])
        op.create_index("ix_fiscaldocument_tenant_status", "fiscaldocument", ["company_id", "fiscal_status"])
        op.create_index("ix_fiscaldocument_tenant_sent", "fiscaldocument", ["company_id", "sent_at"])

    # ── 3. Product fiscal columns ──────────────────────────────
    if not _column_exists(conn, "product", "tax_included"):
        op.add_column(
            "product",
            sa.Column("tax_included", sa.Boolean(), server_default="1", nullable=False),
        )
    if not _column_exists(conn, "product", "tax_rate"):
        op.add_column(
            "product",
            sa.Column("tax_rate", sa.Numeric(5, 2), server_default="18.00", nullable=False),
        )
    if not _column_exists(conn, "product", "tax_category"):
        op.add_column(
            "product",
            sa.Column("tax_category", sa.String(20), server_default="gravado", nullable=False),
        )

    # ── 4. Sale receipt_type column ────────────────────────────
    if not _column_exists(conn, "sale", "receipt_type"):
        op.add_column(
            "sale",
            sa.Column("receipt_type", sa.String(20), nullable=True),
        )
        op.create_index("ix_sale_receipt_type", "sale", ["receipt_type"])


def downgrade() -> None:
    conn = op.get_bind()

    # Drop sale.receipt_type
    if _column_exists(conn, "sale", "receipt_type"):
        op.drop_index("ix_sale_receipt_type", table_name="sale")
        op.drop_column("sale", "receipt_type")

    # Drop product fiscal columns
    for col in ("tax_category", "tax_rate", "tax_included"):
        if _column_exists(conn, "product", col):
            op.drop_column("product", col)

    # Drop fiscaldocument
    if _table_exists(conn, "fiscaldocument"):
        op.drop_table("fiscaldocument")

    # Drop companybillingconfig
    if _table_exists(conn, "companybillingconfig"):
        op.drop_table("companybillingconfig")
