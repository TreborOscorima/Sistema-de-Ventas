"""Add composite indexes for analytics performance

Revision ID: g7h8i9j0k1
Revises: d1e2f3g4h5i6
Create Date: 2026-02-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g7h8i9j0k1"
down_revision: Union[str, Sequence[str], None] = "d1e2f3g4h5i6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_index(inspector, table: str, name: str) -> bool:
    return any(idx["name"] == name for idx in inspector.get_indexes(table))


def upgrade() -> None:
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_index(inspector, "sale", "ix_sale_company_branch_timestamp"):
        op.create_index(
            "ix_sale_company_branch_timestamp",
            "sale",
            ["company_id", "branch_id", "timestamp"],
            unique=False,
        )

    if not _has_index(inspector, "cashboxlog", "ix_cashboxlog_company_branch_timestamp"):
        op.create_index(
            "ix_cashboxlog_company_branch_timestamp",
            "cashboxlog",
            ["company_id", "branch_id", "timestamp"],
            unique=False,
        )

    if not _has_index(
        inspector, "fieldreservation", "ix_fieldreservation_company_branch_sport_start"
    ):
        op.create_index(
            "ix_fieldreservation_company_branch_sport_start",
            "fieldreservation",
            ["company_id", "branch_id", "sport", "start_datetime"],
            unique=False,
        )


def downgrade() -> None:
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_index(inspector, "fieldreservation", "ix_fieldreservation_company_branch_sport_start"):
        op.drop_index(
            "ix_fieldreservation_company_branch_sport_start",
            table_name="fieldreservation",
        )

    if _has_index(inspector, "cashboxlog", "ix_cashboxlog_company_branch_timestamp"):
        op.drop_index(
            "ix_cashboxlog_company_branch_timestamp",
            table_name="cashboxlog",
        )

    if _has_index(inspector, "sale", "ix_sale_company_branch_timestamp"):
        op.drop_index(
            "ix_sale_company_branch_timestamp",
            table_name="sale",
        )
