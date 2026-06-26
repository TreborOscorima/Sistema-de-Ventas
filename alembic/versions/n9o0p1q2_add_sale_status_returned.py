"""add_sale_status_returned

Agrega el valor 'returned' al ENUM status de la tabla sale,
necesario para marcar ventas totalmente devueltas.

Revision: n9o0p1q2
Revisa:   m8n9o0p1
"""
from __future__ import annotations

from alembic import op

revision = "n9o0p1q2"
down_revision = "m8n9o0p1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE sale MODIFY COLUMN status "
        "ENUM('pending','completed','cancelled','returned') NOT NULL"
    )


def downgrade() -> None:
    # Convertir ventas 'returned' a 'completed' antes de quitar el valor
    op.execute(
        "UPDATE sale SET status = 'completed' WHERE status = 'returned'"
    )
    op.execute(
        "ALTER TABLE sale MODIFY COLUMN status "
        "ENUM('pending','completed','cancelled') NOT NULL"
    )
