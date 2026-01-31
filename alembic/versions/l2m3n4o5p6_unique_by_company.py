"""make unique constraints per company for product, client, category

ID de revision: l2m3n4o5p6
Revisa: k1l2m3n4o5
Fecha de creacion: 2026-01-29 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# identificadores de revision, usados por Alembic.
revision: str = "l2m3n4o5p6"
down_revision: Union[str, Sequence[str], None] = "k1l2m3n4o5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    op.drop_index(op.f("ix_product_barcode"), table_name="product")
    op.drop_index(op.f("ix_category_name"), table_name="category")
    op.drop_index(op.f("ix_client_dni"), table_name="client")

    op.create_index(op.f("ix_product_barcode"), "product", ["barcode"], unique=False)
    op.create_index(op.f("ix_category_name"), "category", ["name"], unique=False)
    op.create_index(op.f("ix_client_dni"), "client", ["dni"], unique=False)

    op.create_unique_constraint(
        "uq_product_company_barcode",
        "product",
        ["company_id", "barcode"],
    )
    op.create_unique_constraint(
        "uq_category_company_name",
        "category",
        ["company_id", "name"],
    )
    op.create_unique_constraint(
        "uq_client_company_dni",
        "client",
        ["company_id", "dni"],
    )


def downgrade() -> None:
    """Revertir esquema."""
    op.drop_constraint("uq_client_company_dni", "client", type_="unique")
    op.drop_constraint("uq_category_company_name", "category", type_="unique")
    op.drop_constraint("uq_product_company_barcode", "product", type_="unique")

    op.drop_index(op.f("ix_client_dni"), table_name="client")
    op.drop_index(op.f("ix_category_name"), table_name="category")
    op.drop_index(op.f("ix_product_barcode"), table_name="product")

    op.create_index(op.f("ix_client_dni"), "client", ["dni"], unique=True)
    op.create_index(op.f("ix_category_name"), "category", ["name"], unique=True)
    op.create_index(op.f("ix_product_barcode"), "product", ["barcode"], unique=True)
