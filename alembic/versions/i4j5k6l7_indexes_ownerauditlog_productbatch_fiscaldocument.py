"""indexes: OwnerAuditLog.created_at, ProductBatch FEFO, FiscalDocument tenant_branch

Revision ID: i4j5k6l7
Revises: h3i4j5k6
Create Date: 2026-06-18
"""
from alembic import op

revision = "i4j5k6l7"
down_revision = "h3i4j5k6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # OwnerAuditLog — índice simple para queries por fecha
    op.create_index(
        "ix_owner_audit_log_created_at",
        "owner_audit_log",
        ["created_at"],
    )

    # ProductBatch — índice FEFO: (company_id, branch_id, expiration_date)
    op.create_index(
        "ix_productbatch_fefo",
        "productbatch",
        ["company_id", "branch_id", "expiration_date"],
    )

    # FiscalDocument — índice compuesto tenant para queries por branch
    op.create_index(
        "ix_fiscaldocument_tenant_branch",
        "fiscaldocument",
        ["company_id", "branch_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_fiscaldocument_tenant_branch", table_name="fiscaldocument")
    op.drop_index("ix_productbatch_fefo", table_name="productbatch")
    op.drop_index("ix_owner_audit_log_created_at", table_name="owner_audit_log")
