"""Layer 2 — Performance: índices covering + drop de redundantes.

Revision ID: l2m3n4o5p6q7
Revises: l1m2n3o4p5q6
Create Date: 2026-04-16

Objetivo: reducir write amplification y mejorar latencia del query
más caliente del POS (listado de ventas completadas por sucursal).

Operaciones:
    1. CREATE ix_sale_tenant_status_timestamp (company_id, branch_id,
       status, timestamp) — covering para el listado POS que ordena
       por fecha filtrando por estado y tenant.
    2. DROP 8 índices redundantes:
         - ix_role_name (cubierto por uq_role_company_name).
         - ix_purchase_doc_type / ix_purchase_series / ix_purchase_number
           (cubiertos por uq_purchase_company_branch_supplier_doc).
         - ix_fieldreservation_start_datetime
           (cubierto por ix_fieldreservation_company_branch_sport_start).
         - ix_cashboxlog_timestamp
           (cubierto por ix_cashboxlog_company_branch_timestamp).
         - ix_stockmovement_timestamp
           (cubierto por ix_stockmovement_tenant_timestamp).
         - ix_category_name (cubierto por uq_category_company_branch_name).

Idempotencia: cada operación verifica existencia previa.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect as sa_inspect


revision: str = "l2m3n4o5p6q7"
down_revision: Union[str, Sequence[str], None] = "l1m2n3o4p5q6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ═══════════════════════════════════════════════════════════════════
# Helpers de introspección (idempotencia)
# ═══════════════════════════════════════════════════════════════════
def _has_table(conn, table: str) -> bool:
    return table in sa_inspect(conn).get_table_names()


def _has_index(conn, table: str, name: str) -> bool:
    if not _has_table(conn, table):
        return False
    return any(idx.get("name") == name for idx in sa_inspect(conn).get_indexes(table))


# Tabla -> lista de índices single-column a eliminar (redundantes con
# composites/uniques ya existentes).
REDUNDANT_INDEXES: tuple[tuple[str, str], ...] = (
    ("role", "ix_role_name"),
    ("purchase", "ix_purchase_doc_type"),
    ("purchase", "ix_purchase_series"),
    ("purchase", "ix_purchase_number"),
    ("fieldreservation", "ix_fieldreservation_start_datetime"),
    ("cashboxlog", "ix_cashboxlog_timestamp"),
    ("stockmovement", "ix_stockmovement_timestamp"),
    ("category", "ix_category_name"),
)


# ═══════════════════════════════════════════════════════════════════
# UPGRADE
# ═══════════════════════════════════════════════════════════════════
def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. CREATE covering index en sale (POS hot path) ────────────
    if _has_table(conn, "sale") and not _has_index(
        conn, "sale", "ix_sale_tenant_status_timestamp"
    ):
        op.create_index(
            "ix_sale_tenant_status_timestamp",
            "sale",
            ["company_id", "branch_id", "status", "timestamp"],
        )

    # ── 2. DROP índices redundantes ────────────────────────────────
    for table, idx_name in REDUNDANT_INDEXES:
        if _has_index(conn, table, idx_name):
            op.drop_index(idx_name, table_name=table)


# ═══════════════════════════════════════════════════════════════════
# DOWNGRADE — restaura los índices eliminados y drop del covering.
# ═══════════════════════════════════════════════════════════════════
def downgrade() -> None:
    conn = op.get_bind()

    # Restaurar single-column indexes.
    restore_map: tuple[tuple[str, str, list[str]], ...] = (
        ("role", "ix_role_name", ["name"]),
        ("purchase", "ix_purchase_doc_type", ["doc_type"]),
        ("purchase", "ix_purchase_series", ["series"]),
        ("purchase", "ix_purchase_number", ["number"]),
        ("fieldreservation", "ix_fieldreservation_start_datetime", ["start_datetime"]),
        ("cashboxlog", "ix_cashboxlog_timestamp", ["timestamp"]),
        ("stockmovement", "ix_stockmovement_timestamp", ["timestamp"]),
        ("category", "ix_category_name", ["name"]),
    )
    for table, idx_name, cols in restore_map:
        if _has_table(conn, table) and not _has_index(conn, table, idx_name):
            op.create_index(idx_name, table, cols)

    # Drop del covering nuevo.
    if _has_index(conn, "sale", "ix_sale_tenant_status_timestamp"):
        op.drop_index("ix_sale_tenant_status_timestamp", table_name="sale")
