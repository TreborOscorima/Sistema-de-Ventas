"""reservation_deleted_status

Agrega el valor ``deleted`` al enum de ``fieldreservation.status`` para habilitar
el *soft-delete* de reservas (distinto de ``cancelled``): la reserva se marca como
eliminada, se libera el horario y se guarda ``delete_reason``, pero la fila queda
para auditoría y aparece bajo el filtro "Eliminado".

Idempotente y reversible (el downgrade reasigna 'deleted' → 'cancelled' antes de
quitar el valor del enum para no perder filas).

Revision ID: y0z1a2b3
Revises: x9y0z1a2
Create Date: 2026-08-02
"""
from typing import Sequence, Union

from alembic import op


revision: str = "y0z1a2b3"
down_revision: Union[str, Sequence[str], None] = "x9y0z1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ENUM_WITH_DELETED = (
    "ENUM('pending','paid','cancelled','refunded','deleted')"
)
_ENUM_WITHOUT_DELETED = (
    "ENUM('pending','paid','cancelled','refunded')"
)


def upgrade() -> None:
    op.execute(
        f"ALTER TABLE fieldreservation "
        f"MODIFY COLUMN status {_ENUM_WITH_DELETED} NOT NULL"
    )


def downgrade() -> None:
    # Reasignar reservas eliminadas a 'cancelled' antes de quitar el valor del
    # enum, para no romper el MODIFY ni perder registros.
    op.execute(
        "UPDATE fieldreservation SET status='cancelled' WHERE status='deleted'"
    )
    op.execute(
        f"ALTER TABLE fieldreservation "
        f"MODIFY COLUMN status {_ENUM_WITHOUT_DELETED} NOT NULL"
    )
