"""backfill reservation financial logs for legacy data

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f6a7
Create Date: 2026-02-08 13:20:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _safe_decimal(value) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def upgrade() -> None:
    """Backfill legacy reservation payments into accounting tables."""
    if context.is_offline_mode():
        return

    conn = op.get_bind()
    reservations = conn.execute(
        sa.text(
            """
            SELECT
                fr.id,
                fr.company_id,
                fr.branch_id,
                fr.user_id,
                fr.field_name,
                fr.paid_amount,
                fr.status,
                fr.created_at
            FROM fieldreservation fr
            WHERE fr.paid_amount > 0
            ORDER BY fr.id ASC
            """
        )
    ).mappings().all()

    for reservation in reservations:
        reservation_id = int(reservation["id"])
        company_id = int(reservation["company_id"])
        branch_id = int(reservation["branch_id"])
        user_id = reservation.get("user_id")
        amount = _safe_decimal(reservation.get("paid_amount"))
        if amount <= 0:
            continue

        reference_code = f"Reserva {reservation_id}"
        exists = conn.execute(
            sa.text(
                """
                SELECT 1
                FROM salepayment
                WHERE company_id = :company_id
                  AND branch_id = :branch_id
                  AND reference_code = :reference_code
                LIMIT 1
                """
            ),
            {
                "company_id": company_id,
                "branch_id": branch_id,
                "reference_code": reference_code,
            },
        ).first()
        if exists:
            continue

        sale_result = conn.execute(
            sa.text(
                """
                INSERT INTO sale (
                    timestamp,
                    total_amount,
                    status,
                    payment_condition,
                    company_id,
                    branch_id,
                    user_id
                ) VALUES (
                    :timestamp,
                    :total_amount,
                    'completed',
                    'contado',
                    :company_id,
                    :branch_id,
                    :user_id
                )
                """
            ),
            {
                "timestamp": reservation.get("created_at"),
                "total_amount": amount,
                "company_id": company_id,
                "branch_id": branch_id,
                "user_id": user_id,
            },
        )
        sale_id = int(sale_result.lastrowid)

        field_name = (reservation.get("field_name") or "Cancha").strip() or "Cancha"
        entry_type = "Reserva" if str(reservation.get("status") or "").lower() == "paid" else "Adelanto"

        conn.execute(
            sa.text(
                """
                INSERT INTO saleitem (
                    quantity,
                    unit_price,
                    subtotal,
                    product_name_snapshot,
                    product_barcode_snapshot,
                    product_category_snapshot,
                    sale_id,
                    company_id,
                    branch_id
                ) VALUES (
                    1,
                    :amount,
                    :amount,
                    :product_name_snapshot,
                    'RESERVA',
                    'Servicios',
                    :sale_id,
                    :company_id,
                    :branch_id
                )
                """
            ),
            {
                "amount": amount,
                "product_name_snapshot": f"{entry_type} histórica reserva: {field_name}",
                "sale_id": sale_id,
                "company_id": company_id,
                "branch_id": branch_id,
            },
        )

        conn.execute(
            sa.text(
                """
                INSERT INTO salepayment (
                    sale_id,
                    company_id,
                    branch_id,
                    amount,
                    method_type,
                    reference_code,
                    created_at
                ) VALUES (
                    :sale_id,
                    :company_id,
                    :branch_id,
                    :amount,
                    'cash',
                    :reference_code,
                    :created_at
                )
                """
            ),
            {
                "sale_id": sale_id,
                "company_id": company_id,
                "branch_id": branch_id,
                "amount": amount,
                "reference_code": reference_code,
                "created_at": reservation.get("created_at"),
            },
        )

        conn.execute(
            sa.text(
                """
                INSERT INTO cashboxlog (
                    timestamp,
                    action,
                    amount,
                    quantity,
                    unit,
                    cost,
                    payment_method,
                    notes,
                    company_id,
                    branch_id,
                    user_id,
                    sale_id,
                    is_voided
                ) VALUES (
                    :timestamp,
                    :action,
                    :amount,
                    1,
                    'Servicio',
                    0,
                    'Efectivo',
                    :notes,
                    :company_id,
                    :branch_id,
                    :user_id,
                    :sale_id,
                    0
                )
                """
            ),
            {
                "timestamp": reservation.get("created_at"),
                "action": entry_type,
                "amount": amount,
                "notes": f"Backfill histórico reserva {reservation_id}",
                "company_id": company_id,
                "branch_id": branch_id,
                "user_id": user_id,
                "sale_id": sale_id,
            },
        )


def downgrade() -> None:
    """Remove records created by reservation backfill."""
    if context.is_offline_mode():
        return

    conn = op.get_bind()
    sale_ids = conn.execute(
        sa.text(
            """
            SELECT DISTINCT sale_id
            FROM cashboxlog
            WHERE notes LIKE 'Backfill histórico reserva %'
              AND sale_id IS NOT NULL
            """
        )
    ).scalars().all()

    if not sale_ids:
        return

    conn.execute(
        sa.text(
            """
            DELETE FROM cashboxlog
            WHERE notes LIKE 'Backfill histórico reserva %'
              AND sale_id IN :sale_ids
            """
        ).bindparams(sa.bindparam("sale_ids", expanding=True)),
        {"sale_ids": list(sale_ids)},
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM salepayment
            WHERE reference_code LIKE 'Reserva %'
              AND sale_id IN :sale_ids
            """
        ).bindparams(sa.bindparam("sale_ids", expanding=True)),
        {"sale_ids": list(sale_ids)},
    )
    conn.execute(
        sa.text("DELETE FROM saleitem WHERE sale_id IN :sale_ids").bindparams(
            sa.bindparam("sale_ids", expanding=True)
        ),
        {"sale_ids": list(sale_ids)},
    )
    conn.execute(
        sa.text("DELETE FROM sale WHERE id IN :sale_ids").bindparams(
            sa.bindparam("sale_ids", expanding=True)
        ),
        {"sale_ids": list(sale_ids)},
    )
