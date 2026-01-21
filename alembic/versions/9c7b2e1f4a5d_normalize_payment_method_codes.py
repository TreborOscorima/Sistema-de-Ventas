"""normalizar codigos de metodos de pago

ID de revision: 9c7b2e1f4a5d
Revisa: 6b1a9c2d3e4f
Fecha de creacion: 2026-02-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# identificadores de revision, usados por Alembic.
revision: str = "9c7b2e1f4a5d"
down_revision: Union[str, Sequence[str], None] = "6b1a9c2d3e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _method_exists(conn, method_id: str) -> bool:
    row = conn.execute(
        sa.text(
            "SELECT 1 FROM paymentmethod WHERE method_id = :method_id LIMIT 1"
        ),
        {"method_id": method_id},
    ).first()
    return row is not None


def _code_exists(conn, code: str) -> bool:
    row = conn.execute(
        sa.text("SELECT 1 FROM paymentmethod WHERE code = :code LIMIT 1"),
        {"code": code},
    ).first()
    return row is not None


def _rename_method(conn, old_id: str, new_id: str) -> None:
    if _method_exists(conn, new_id) or _code_exists(conn, new_id):
        return
    conn.execute(
        sa.text(
            """
            UPDATE paymentmethod
            SET method_id = :new_id,
                code = :new_code
            WHERE method_id = :old_id
            """
        ),
        {"new_id": new_id, "new_code": new_id, "old_id": old_id},
    )


def _align_code(conn, method_id: str, code: str) -> None:
    conn.execute(
        sa.text(
            """
            UPDATE paymentmethod
            SET code = :code
            WHERE method_id = :method_id AND code != :code
            """
        ),
        {"method_id": method_id, "code": code},
    )


def upgrade() -> None:
    conn = op.get_bind()
    _rename_method(conn, "debit", "debit_card")
    _rename_method(conn, "credit", "credit_card")
    _align_code(conn, "debit_card", "debit_card")
    _align_code(conn, "credit_card", "credit_card")


def downgrade() -> None:
    conn = op.get_bind()
    _rename_method(conn, "debit_card", "debit")
    _rename_method(conn, "credit_card", "credit")
    _align_code(conn, "debit", "debit")
    _align_code(conn, "credit", "credit")
