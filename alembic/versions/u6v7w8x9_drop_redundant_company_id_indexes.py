"""drop_redundant_single_column_company_id_indexes

Elimina los índices single-column ``ix_sale_company_id`` /
``ix_saleitem_company_id`` / ``ix_product_company_id``.

Motivo (Fase P1, docs/PERF_SCALABILITY_PLAN.md §3): son **redundantes** — la FK
de ``company_id`` ya está cubierta por índices compuestos que lideran con
``company_id`` (p.ej. ``ix_sale_tenant_status_timestamp``,
``ix_saleitem_company_branch_sale``, ``ix_product_tenant_category``). Su
presencia inducía al optimizador a elegir ``index_merge intersect`` de índices
single-column, bypasseando el compuesto covering: escaneaba todo el historial
del tenant + ``filesort`` en vez de ir directo por el compuesto.

Medido en staging (150 empresas / 225k ventas, EXPLAIN ANALYZE real): la query
del listado de ventas del POS pasó de **105 ms a 0,22 ms (~480x)** al eliminar
``ix_sale_company_id``. Continúa el trabajo de ``l2m3n4o5p6q7``.

Seguridad: cada drop se ejecuta SOLO si (a) el índice existe y (b) existe OTRO
índice que lidera con ``company_id`` para seguir cubriendo la FK. Si no está
cubierto, se omite con warning (nunca deja la FK sin índice).

Revision ID: u6v7w8x9
Revises: t5u6v7w8
Create Date: 2026-07-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "u6v7w8x9"
down_revision: Union[str, Sequence[str], None] = "t5u6v7w8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (índice single-column a eliminar, tabla)
REDUNDANT: tuple[tuple[str, str], ...] = (
    ("ix_sale_company_id", "sale"),
    ("ix_saleitem_company_id", "saleitem"),
    ("ix_product_company_id", "product"),
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
                f"[u6v7w8x9] SKIP {index}: la FK de company_id en '{table}' no "
                "quedaría cubierta por otro índice. No se dropea."
            )
            continue
        op.drop_index(index, table_name=table)


def downgrade() -> None:
    conn = op.get_bind()
    for index, table in REDUNDANT:
        if not _index_exists(conn, table, index):
            op.create_index(index, table, ["company_id"], unique=False)
