"""drop legacy company-level uniques after branch-scoped migration

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-02-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Elimina constraints legacy company-level que bloquean multi-sucursal."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    def refresh() -> None:
        nonlocal inspector
        inspector = sa_inspect(bind)

    def has_table(table_name: str) -> bool:
        return inspector.has_table(table_name)

    def has_unique(table_name: str, unique_name: str) -> bool:
        return any(
            (uq.get("name") or "") == unique_name
            for uq in inspector.get_unique_constraints(table_name)
        )

    def has_index(table_name: str, index_name: str) -> bool:
        return any(
            (idx.get("name") or "") == index_name
            for idx in inspector.get_indexes(table_name)
        )

    def drop_unique_or_index(table_name: str, legacy_name: str) -> None:
        if not has_table(table_name):
            return

        # MySQL puede exponer únicos como constraint o como índice único.
        if has_unique(table_name, legacy_name):
            try:
                op.drop_constraint(legacy_name, table_name, type_="unique")
            except Exception:
                pass
            refresh()

        if has_index(table_name, legacy_name):
            op.drop_index(legacy_name, table_name=table_name)
            refresh()

    legacy_company_uniques = [
        ("category", "uq_category_company_name"),
        ("client", "uq_client_company_dni"),
        ("product", "uq_product_company_barcode"),
        ("unit", "uq_unit_company_name"),
        ("paymentmethod", "uq_paymentmethod_company_code"),
        ("paymentmethod", "uq_paymentmethod_company_method_id"),
        ("purchase", "uq_purchase_supplier_doc"),
    ]

    for table_name, legacy_name in legacy_company_uniques:
        drop_unique_or_index(table_name, legacy_name)

    # supplier venía con índice global único por tax_id en versiones anteriores.
    if has_table("supplier"):
        supplier_indexes = {
            idx.get("name"): idx for idx in inspector.get_indexes("supplier")
        }
        idx = supplier_indexes.get("ix_supplier_tax_id")
        if idx and bool(idx.get("unique")):
            op.drop_index("ix_supplier_tax_id", table_name="supplier")
            refresh()
        if not has_index("supplier", "ix_supplier_tax_id"):
            op.create_index("ix_supplier_tax_id", "supplier", ["tax_id"], unique=False)
            refresh()


def downgrade() -> None:
    """No-op: no restaura constraints legacy."""
    pass

