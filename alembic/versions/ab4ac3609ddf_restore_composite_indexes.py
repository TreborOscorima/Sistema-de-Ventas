"""restore composite indexes

ID de revision: ab4ac3609ddf
Revisa: 41f4cbde7e0e
Fecha de creacion: 2026-02-07 11:54:13.259942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# identificadores de revision, usados por Alembic.
revision: str = 'ab4ac3609ddf'
down_revision: Union[str, Sequence[str], None] = '41f4cbde7e0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    op.create_index(
        "ix_cashboxlog_company_branch_timestamp",
        "cashboxlog",
        ["company_id", "branch_id", "timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_sale_company_branch_timestamp",
        "sale",
        ["company_id", "branch_id", "timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_fieldreservation_company_branch_sport_start",
        "fieldreservation",
        ["company_id", "branch_id", "sport", "start_datetime"],
        unique=False,
    )
    op.create_index(
        "ix_saleitem_company_branch_product",
        "saleitem",
        ["company_id", "branch_id", "product_id"],
        unique=False,
    )
    op.create_index(
        "ix_saleitem_company_branch_sale",
        "saleitem",
        ["company_id", "branch_id", "sale_id"],
        unique=False,
    )


def downgrade() -> None:
    """Revertir esquema."""
    op.drop_index(
        "ix_saleitem_company_branch_sale",
        table_name="saleitem",
    )
    op.drop_index(
        "ix_saleitem_company_branch_product",
        table_name="saleitem",
    )
    op.drop_index(
        "ix_fieldreservation_company_branch_sport_start",
        table_name="fieldreservation",
    )
    op.drop_index(
        "ix_sale_company_branch_timestamp",
        table_name="sale",
    )
    op.drop_index(
        "ix_cashboxlog_company_branch_timestamp",
        table_name="cashboxlog",
    )
