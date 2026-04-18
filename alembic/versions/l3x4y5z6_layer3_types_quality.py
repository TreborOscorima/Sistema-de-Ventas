"""Layer 3 — Types/Code quality: drop de server_default duplicados.

Revision ID: l3x4y5z6
Revises: l2m3n4o5p6q7
Create Date: 2026-04-16

Contexto:
    Cinco columnas DATETIME definían simultáneamente ``default_factory=utc_now_naive``
    (Python-side) y ``server_default=func.now()`` (DB-side). El ORM siempre
    envía el valor Python en el INSERT, por lo que el DEFAULT de DB nunca
    se activaba en la práctica. La duplicación confundía la "source of truth"
    y provocaba drift entre snapshot Python (UTC naive) y NOW() de MySQL
    (timezone del servidor) ante eventuales INSERTs fuera del ORM.

Resolución:
    - Modelos: eliminado ``server_default`` — Python queda como única fuente.
    - DB: esta migración elimina el DEFAULT residual para alinear el schema
      y evitar que ``alembic autogenerate`` detecte diferencias.

Columnas afectadas:
    1. companybillingconfig.created_at
    2. fiscaldocument.created_at
    3. document_lookup_cache.fetched_at
    4. owner_audit_log.created_at
    5. sale.timestamp

Idempotencia: cada ALTER verifica previamente la existencia de tabla+columna.
Reversibilidad: downgrade restaura ``DEFAULT CURRENT_TIMESTAMP`` (equivalente
a ``func.now()`` en MySQL).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect as sa_inspect


revision: str = "l3x4y5z6"
down_revision: Union[str, Sequence[str], None] = "l2m3n4o5p6q7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ═══════════════════════════════════════════════════════════════════
# Tuplas (tabla, columna, nullable) para drop/restore idempotente
# ═══════════════════════════════════════════════════════════════════
COLUMNS: tuple[tuple[str, str, bool], ...] = (
    ("companybillingconfig", "created_at", False),
    ("fiscaldocument", "created_at", False),
    ("document_lookup_cache", "fetched_at", False),
    ("owner_audit_log", "created_at", False),
    ("sale", "timestamp", False),
)


def _has_column(conn, table: str, column: str) -> bool:
    inspector = sa_inspect(conn)
    if table not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    """DROP DEFAULT en columnas con doble fuente de verdad.

    MySQL exige reemitir el tipo completo al alterar; usamos DATETIME
    explícito y ``server_default=None`` para remover el default sin
    tocar nullability ni el tipo subyacente.
    """
    import sqlalchemy as sa

    conn = op.get_bind()
    for table, column, nullable in COLUMNS:
        if not _has_column(conn, table, column):
            continue
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=False),
            existing_nullable=nullable,
            server_default=None,
        )


def downgrade() -> None:
    """Restaurar ``CURRENT_TIMESTAMP`` como DEFAULT en DB."""
    import sqlalchemy as sa

    conn = op.get_bind()
    for table, column, nullable in COLUMNS:
        if not _has_column(conn, table, column):
            continue
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=False),
            existing_nullable=nullable,
            server_default=sa.func.now(),
        )
