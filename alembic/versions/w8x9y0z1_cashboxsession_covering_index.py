"""add_missing_cashboxsession_covering_index_and_drop_redundant_single

Fase P1 (docs/PERF_SCALABILITY_PLAN.md §9 — barrido). Corrige un **drift
modelo↔BD**: el modelo ``CashboxSession`` declara el índice compuesto
``ix_cashboxsession_tenant_user_open`` (``company_id, branch_id, user_id,
is_open``) pero **ninguna migración lo creó en prod**. En su lugar la tabla sólo
tiene los dos single-column del ``TenantMixin`` (``company_id`` + ``branch_id``),
que reproducen la patología ``index_merge intersect`` de P1 — pero aquí NO se
puede arreglar sólo dropeando (no hay compuesto de respaldo).

La query caliente (app/states/cash/_close_mixin.py: buscar la sesión abierta del
cajero) filtra exactamente ``company_id AND branch_id AND user_id AND is_open``.
Sin el compuesto hace un scan por tenant. Este migración:

1. CREA ``ix_cashboxsession_tenant_user_open`` (covering de esa query).
2. DROPEA el single ``ix_cashboxsession_company_id`` (ahora redundante: el nuevo
   compuesto lidera con ``company_id`` y cubre la FK). Mismo guard que
   ``u6v7w8x9``/``v7w8x9y0``: sólo si queda cubierto por otro índice.

Idempotente y reversible.

Revision ID: w8x9y0z1
Revises: v7w8x9y0
Create Date: 2026-07-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "w8x9y0z1"
down_revision: Union[str, Sequence[str], None] = "v7w8x9y0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "cashboxsession"
COMPOSITE = "ix_cashboxsession_tenant_user_open"
COMPOSITE_COLS = ["company_id", "branch_id", "user_id", "is_open"]
SINGLE = "ix_cashboxsession_company_id"


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
    # 1. crear el compuesto covering (si no existe ya)
    if not _index_exists(conn, TABLE, COMPOSITE):
        op.create_index(COMPOSITE, TABLE, COMPOSITE_COLS, unique=False)
    # 2. dropear el single, ahora cubierto por el compuesto recién creado
    if _index_exists(conn, TABLE, SINGLE):
        if _company_id_covered_by_other(conn, TABLE, SINGLE):
            op.drop_index(SINGLE, table_name=TABLE)
        else:
            print(
                f"[w8x9y0z1] SKIP {SINGLE}: la FK de company_id en '{TABLE}' no "
                "quedaría cubierta. No se dropea."
            )


def downgrade() -> None:
    conn = op.get_bind()
    # recrear el single antes de quitar el compuesto (mantener la FK cubierta)
    if not _index_exists(conn, TABLE, SINGLE):
        op.create_index(SINGLE, TABLE, ["company_id"], unique=False)
    if _index_exists(conn, TABLE, COMPOSITE):
        op.drop_index(COMPOSITE, table_name=TABLE)
