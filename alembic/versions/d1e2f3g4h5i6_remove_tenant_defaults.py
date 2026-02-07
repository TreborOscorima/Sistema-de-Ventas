"""remove tenant defaults

ID de revision: d1e2f3g4h5i6
Revisa: c9fbab12ed1a
Fecha de creacion: 2026-02-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# identificadores de revision, usados por Alembic.
revision: str = "d1e2f3g4h5i6"
down_revision: Union[str, Sequence[str], None] = "c9fbab12ed1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_COLUMNS: dict[str, dict[str, bool]] = {
    "branch": {"company_id": False},
    "cashboxlog": {"company_id": False, "branch_id": False},
    "cashboxsession": {"company_id": False, "branch_id": False},
    "category": {"company_id": False, "branch_id": False},
    "client": {"company_id": False, "branch_id": False},
    "companysettings": {"company_id": False, "branch_id": False},
    "fieldprice": {"company_id": False, "branch_id": False},
    "fieldreservation": {"company_id": False, "branch_id": False},
    "paymentmethod": {"company_id": False, "branch_id": False},
    "pricetier": {"company_id": False, "branch_id": False},
    "product": {"company_id": False, "branch_id": False},
    "productbatch": {"company_id": False, "branch_id": False},
    "productkit": {"company_id": False, "branch_id": False},
    "productvariant": {"company_id": False, "branch_id": False},
    "purchase": {"company_id": False, "branch_id": False},
    "purchaseitem": {"company_id": False, "branch_id": False},
    "sale": {"company_id": False, "branch_id": False},
    "saleinstallment": {"company_id": False, "branch_id": False},
    "saleitem": {"company_id": False, "branch_id": False},
    "salepayment": {"company_id": False, "branch_id": False},
    "stockmovement": {"company_id": False, "branch_id": False},
    "supplier": {"company_id": False, "branch_id": False},
    "unit": {"company_id": False, "branch_id": False},
    "user": {"company_id": False, "branch_id": True},
}


def _alter_defaults(server_default) -> None:
    for table_name, columns in TENANT_COLUMNS.items():
        for column_name, is_nullable in columns.items():
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.Integer(),
                existing_nullable=is_nullable,
                server_default=server_default,
            )


def upgrade() -> None:
    """Actualizar esquema."""
    _alter_defaults(server_default=None)


def downgrade() -> None:
    """Revertir esquema."""
    for table_name, columns in TENANT_COLUMNS.items():
        for column_name, is_nullable in columns.items():
            default_value = None
            if column_name != "branch_id" or table_name != "user":
                default_value = sa.text("1")
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.Integer(),
                existing_nullable=is_nullable,
                server_default=default_value,
            )
