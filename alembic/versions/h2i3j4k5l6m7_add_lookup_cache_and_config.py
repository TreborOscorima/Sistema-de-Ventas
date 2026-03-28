"""add document lookup cache table and billing config fields

ID de revision: h2i3j4k5l6m7
Revisa: g1h2i3j4k5l6
Fecha de creacion: 2026-03-21 00:00:00.000000

Adds:
    - document_lookup_cache table (fiscal document lookup cache)
    - companybillingconfig: emisor_iva_condition, afip_concepto,
      ar_identification_threshold, lookup_api_url, lookup_api_token columns
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# identificadores de revision, usados por Alembic.
revision: str = "h2i3j4k5l6m7"
down_revision: Union[str, Sequence[str], None] = "g1h2i3j4k5l6"
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

    # ── 1. DocumentLookupCache table ─────────────────────────
    if not _table_exists(conn, "document_lookup_cache"):
        op.create_table(
            "document_lookup_cache",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            # Identification
            sa.Column("country", sa.String(5), nullable=False),
            sa.Column("doc_type", sa.String(10), nullable=False),
            sa.Column("doc_number", sa.String(20), nullable=False),
            # Taxpayer data
            sa.Column("legal_name", sa.String(300), server_default="", nullable=False),
            sa.Column("fiscal_address", sa.String(500), server_default="", nullable=False),
            sa.Column("status", sa.String(30), server_default="", nullable=False),
            sa.Column("condition", sa.String(30), server_default="", nullable=False),
            # Argentina-specific
            sa.Column("iva_condition", sa.String(50), server_default="", nullable=False),
            sa.Column("iva_condition_code", sa.Integer(), server_default="0", nullable=False),
            # Raw response
            sa.Column("raw_json", sa.Text(), server_default="{}", nullable=False),
            # Metadata
            sa.Column("fetched_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.Column("not_found", sa.Boolean(), server_default="0", nullable=False),
            # Constraints
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("country", "doc_number", name="uq_lookupcache_country_docnumber"),
        )
        op.create_index("ix_document_lookup_cache_country", "document_lookup_cache", ["country"])
        op.create_index("ix_document_lookup_cache_doc_number", "document_lookup_cache", ["doc_number"])

    # ── 2. New columns on companybillingconfig ───────────────
    if _table_exists(conn, "companybillingconfig"):
        if not _column_exists(conn, "companybillingconfig", "emisor_iva_condition"):
            op.add_column(
                "companybillingconfig",
                sa.Column("emisor_iva_condition", sa.String(20), server_default="RI", nullable=False),
            )
        if not _column_exists(conn, "companybillingconfig", "afip_concepto"):
            op.add_column(
                "companybillingconfig",
                sa.Column("afip_concepto", sa.Integer(), server_default="1", nullable=False),
            )
        if not _column_exists(conn, "companybillingconfig", "ar_identification_threshold"):
            op.add_column(
                "companybillingconfig",
                sa.Column("ar_identification_threshold", sa.Numeric(12, 2), server_default="68782.00", nullable=False),
            )
        if not _column_exists(conn, "companybillingconfig", "lookup_api_url"):
            op.add_column(
                "companybillingconfig",
                sa.Column("lookup_api_url", sa.String(512), server_default="", nullable=False),
            )
        if not _column_exists(conn, "companybillingconfig", "lookup_api_token"):
            op.add_column(
                "companybillingconfig",
                sa.Column("lookup_api_token", sa.Text(), nullable=True),
            )


def downgrade() -> None:
    conn = op.get_bind()

    # Drop new columns from companybillingconfig
    if _table_exists(conn, "companybillingconfig"):
        for col in ("lookup_api_token", "lookup_api_url", "ar_identification_threshold", "afip_concepto", "emisor_iva_condition"):
            if _column_exists(conn, "companybillingconfig", col):
                op.drop_column("companybillingconfig", col)

    # Drop document_lookup_cache table
    if _table_exists(conn, "document_lookup_cache"):
        op.drop_index("ix_document_lookup_cache_doc_number", table_name="document_lookup_cache")
        op.drop_index("ix_document_lookup_cache_country", table_name="document_lookup_cache")
        op.drop_constraint("uq_lookupcache_country_docnumber", "document_lookup_cache", type_="unique")
        op.drop_table("document_lookup_cache")
