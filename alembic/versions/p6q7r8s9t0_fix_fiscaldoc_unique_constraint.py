"""Corrige restriccion unica en fiscaldocument para soportar Notas de Credito.

Problema: La restriccion anterior ``uq_fiscaldocument_company_sale``
(company_id, sale_id) impedia que una misma venta tuviera tanto
un comprobante (factura/boleta) COMO una nota de credito asociada.

Solucion: Reemplazar la restriccion por ``uq_fiscaldocument_company_sale_type``
(company_id, sale_id, receipt_type) — permitiendo multiples documentos
fiscales del mismo tipo distinto para la misma venta.

ID de revision: p6q7r8s9t0
Revisa: h2i3j4k5l6m7
Fecha de creacion: 2026-03-22 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect as sa_inspect


# identificadores de revision, usados por Alembic.
revision: str = "p6q7r8s9t0"
down_revision: Union[str, Sequence[str], None] = "h2i3j4k5l6m7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _constraint_exists(conn, table: str, constraint_name: str) -> bool:
    """Verifica si una restriccion unique existe en la tabla."""
    insp = sa_inspect(conn)
    try:
        unique_constraints = insp.get_unique_constraints(table)
        return any(uc["name"] == constraint_name for uc in unique_constraints)
    except Exception:
        return False


def upgrade() -> None:
    conn = op.get_bind()

    # Eliminar la restriccion vieja (company_id, sale_id)
    if _constraint_exists(conn, "fiscaldocument", "uq_fiscaldocument_company_sale"):
        op.drop_constraint(
            "uq_fiscaldocument_company_sale",
            "fiscaldocument",
            type_="unique",
        )

    # Crear la nueva restriccion (company_id, sale_id, receipt_type)
    if not _constraint_exists(conn, "fiscaldocument", "uq_fiscaldocument_company_sale_type"):
        op.create_unique_constraint(
            "uq_fiscaldocument_company_sale_type",
            "fiscaldocument",
            ["company_id", "sale_id", "receipt_type"],
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Eliminar la restriccion nueva
    if _constraint_exists(conn, "fiscaldocument", "uq_fiscaldocument_company_sale_type"):
        op.drop_constraint(
            "uq_fiscaldocument_company_sale_type",
            "fiscaldocument",
            type_="unique",
        )

    # Restaurar la restriccion original
    if not _constraint_exists(conn, "fiscaldocument", "uq_fiscaldocument_company_sale"):
        op.create_unique_constraint(
            "uq_fiscaldocument_company_sale",
            "fiscaldocument",
            ["company_id", "sale_id"],
        )
