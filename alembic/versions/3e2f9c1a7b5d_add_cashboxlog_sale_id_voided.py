"""agregar sale_id e is_voided en cashboxlog

ID de revision: 3e2f9c1a7b5d
Revisa: b7c8d9e0f1a2
Fecha de creacion: 2026-02-02 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# identificadores de revision, usados por Alembic.
revision: str = "3e2f9c1a7b5d"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    op.add_column(
        "cashboxlog",
        sa.Column("sale_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "cashboxlog",
        sa.Column(
            "is_voided",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        op.f("ix_cashboxlog_sale_id"),
        "cashboxlog",
        ["sale_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cashboxlog_is_voided"),
        "cashboxlog",
        ["is_voided"],
        unique=False,
    )
    op.create_foreign_key(
        None,
        "cashboxlog",
        "sale",
        ["sale_id"],
        ["id"],
    )
    op.alter_column("cashboxlog", "is_voided", server_default=None)


def downgrade() -> None:
    """Revertir esquema."""
    op.drop_constraint(None, "cashboxlog", type_="foreignkey")
    op.drop_index(op.f("ix_cashboxlog_is_voided"), table_name="cashboxlog")
    op.drop_index(op.f("ix_cashboxlog_sale_id"), table_name="cashboxlog")
    op.drop_column("cashboxlog", "is_voided")
    op.drop_column("cashboxlog", "sale_id")
