"""drop_redundant_single_column_company_id_indexes_sweep

Barrido de seguimiento de ``u6v7w8x9``: elimina el resto de índices
single-column ``ix_<tabla>_company_id`` **redundantes** en las tablas
multi-tenant (``TenantMixin`` + las que declaran ``company_id`` a mano).

Motivo (Fase P1, docs/PERF_SCALABILITY_PLAN.md §3 y §9 paso 2): igual que en
``u6v7w8x9`` para ``sale``/``saleitem``/``product``. La FK de ``company_id`` en
estas tablas ya está cubierta por un índice compuesto que **lidera** con
``company_id`` (p.ej. ``ix_purchase_tenant_date``,
``ix_stockmovement_tenant_timestamp``, ``ix_cashboxlog_company_branch_timestamp``,
``ix_companytaxrate_company_active`` …). El single-column es puro overhead de
escritura y habilita el patrón ``index_merge intersect`` que bypasea el
compuesto covering (medido en P1: 105 ms → 0,22 ms al eliminarlo).

La lista se derivó de la BD real (staging construida por migraciones = fiel a
prod), NO de la metadata del modelo: incluye tablas cuyo single está cubierto por
un índice compuesto normal (``ix_purchase_tenant_date`` …) Y tablas cubiertas por
una constraint **UNIQUE** ``(company_id, …)`` (``uq_user_company_email``,
``uq_client_company_branch_dni`` …) que la metadata de ``Table.indexes`` no expone.

Tablas EXCLUIDAS a propósito (el single es el ÚNICO cover de la FK → se mantiene):
``branch``, ``fieldprice``, ``purchaseitem``, ``purchaseorderitem``. También se
excluyen ``sale``/``saleitem``/``product`` (ya tratadas en ``u6v7w8x9``) y
``cashboxsession`` (su compuesto covering no existe aún en prod: se crea y su
single se dropea en la migración siguiente ``w8x9y0z1``).

Seguridad: idéntica a ``u6v7w8x9`` — cada drop se ejecuta SOLO si (a) el índice
existe y (b) existe OTRO índice que lidera con ``company_id``. Idempotente y
reversible. El ``downgrade`` recrea cada índice single-column.

Revision ID: v7w8x9y0
Revises: u6v7w8x9
Create Date: 2026-07-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v7w8x9y0"
down_revision: Union[str, Sequence[str], None] = "u6v7w8x9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (índice single-column a eliminar, tabla). Derivado de la metadata SQLModel:
# tablas con company_id cuyo single-column está cubierto por un índice compuesto
# que lidera con company_id. Ver docs/PERF_SCALABILITY_PLAN.md §9.
REDUNDANT: tuple[tuple[str, str], ...] = (
    # --- cubiertos por índice compuesto normal (ix_*_tenant_*) ---
    ("ix_cashboxlog_company_id", "cashboxlog"),
    ("ix_companytaxrate_company", "companytaxrate"),
    ("ix_fieldreservation_company_id", "fieldreservation"),
    ("ix_fiscaldocument_company_id", "fiscaldocument"),
    ("ix_pricelist_company_id", "pricelist"),
    ("ix_pricelistitem_company_id", "pricelistitem"),
    ("ix_productattribute_company_id", "productattribute"),
    ("ix_productbatch_company_id", "productbatch"),
    ("ix_productvariant_company_id", "productvariant"),
    ("ix_promotion_company_id", "promotion"),
    ("ix_promotion_product_company_id", "promotion_product"),
    ("ix_purchase_company_id", "purchase"),
    ("ix_purchaseorder_company_id", "purchaseorder"),
    ("ix_quotation_company_id", "quotation"),
    ("ix_quotationitem_company_id", "quotationitem"),
    ("ix_saleinstallment_company_id", "saleinstallment"),
    ("ix_salepayment_company_id", "salepayment"),
    ("ix_salereturn_company_id", "salereturn"),
    ("ix_salereturnitem_company_id", "salereturnitem"),
    ("ix_stockmovement_company_id", "stockmovement"),
    # --- cubiertos por constraint UNIQUE (company_id, …) ---
    ("ix_category_company_id", "category"),
    ("ix_client_company_id", "client"),
    ("ix_companybillingconfig_company_id", "companybillingconfig"),
    ("ix_companysettings_company_id", "companysettings"),
    ("ix_paymentmethod_company_id", "paymentmethod"),
    ("ix_pricetier_company_id", "pricetier"),
    ("ix_productkit_company_id", "productkit"),
    ("ix_role_company_id", "role"),
    ("ix_supplier_company_id", "supplier"),
    ("ix_unit_company_id", "unit"),
    ("ix_user_company_id", "user"),
)


def _index_exists(conn, table: str, index: str) -> bool:
    return (
        conn.execute(
            sa.text(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = :t "
                "AND index_name = :i"
            ),
            {"t": table, "i": index},
        ).scalar()
        > 0
    )


def _company_id_covered_by_other(conn, table: str, exclude_index: str) -> bool:
    """True si OTRO índice (≠ exclude_index) lidera con company_id → FK cubierta."""
    return (
        conn.execute(
            sa.text(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = :t "
                "AND seq_in_index = 1 AND column_name = 'company_id' "
                "AND index_name <> :i"
            ),
            {"t": table, "i": exclude_index},
        ).scalar()
        > 0
    )


def upgrade() -> None:
    conn = op.get_bind()
    for index, table in REDUNDANT:
        if not _index_exists(conn, table, index):
            continue
        if not _company_id_covered_by_other(conn, table, index):
            print(
                f"[v7w8x9y0] SKIP {index}: la FK de company_id en '{table}' no "
                "quedaría cubierta por otro índice. No se dropea."
            )
            continue
        op.drop_index(index, table_name=table)


def downgrade() -> None:
    conn = op.get_bind()
    for index, table in REDUNDANT:
        if not _index_exists(conn, table, index):
            op.create_index(index, table, ["company_id"], unique=False)
