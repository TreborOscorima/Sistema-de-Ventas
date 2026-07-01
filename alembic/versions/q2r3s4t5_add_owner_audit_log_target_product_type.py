"""add owner_audit_log.target_product_type, drop company FK on target_company_id

Revision ID: q2r3s4t5
Revises: p1q2r3s4
Create Date: 2026-07-01

"""
from alembic import op
import sqlalchemy as sa

revision = "q2r3s4t5"
down_revision = "p1q2r3s4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "owner_audit_log",
        sa.Column("target_product_type", sa.String(20), nullable=False, server_default="ventas"),
    )
    op.create_index(
        "ix_owner_audit_log_product_type", "owner_audit_log", ["target_product_type"],
    )
    # Las empresas Food viven en food_db (base completamente separada) -- sus ids
    # no existen en la tabla company de esta base. target_product_type ya
    # desambigua el namespace, así que la FK ya no puede exigirse a nivel DB.
    op.drop_constraint(
        "owner_audit_log_ibfk_2", "owner_audit_log", type_="foreignkey",
    )


def downgrade() -> None:
    op.create_foreign_key(
        "owner_audit_log_ibfk_2", "owner_audit_log", "company",
        ["target_company_id"], ["id"],
    )
    op.drop_index("ix_owner_audit_log_product_type", table_name="owner_audit_log")
    op.drop_column("owner_audit_log", "target_product_type")
