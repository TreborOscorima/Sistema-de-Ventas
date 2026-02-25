"""add owner_audit_log table and user is_platform_owner

ID de revision: d3e4f5a6b7c8
Revisa: c2d3e4f5a6b7
Fecha de creacion: 2026-02-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# identificadores de revision, usados por Alembic.
revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crear tabla owner_audit_log y campo is_platform_owner en user."""
    bind = op.get_bind()
    insp = sa_inspect(bind)

    # 1. Campo is_platform_owner en user (idempotente)
    existing_cols = [c["name"] for c in insp.get_columns("user")]
    if "is_platform_owner" not in existing_cols:
        op.add_column(
            "user",
            sa.Column(
                "is_platform_owner",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )
        op.alter_column("user", "is_platform_owner", server_default=None)

    # 2. Tabla owner_audit_log (idempotente)
    if "owner_audit_log" not in insp.get_table_names():
        op.create_table(
        "owner_audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("actor_email", sa.String(255), nullable=False),
        sa.Column("target_company_id", sa.Integer(), nullable=False),
        sa.Column("target_company_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("before_snapshot", sa.Text(), nullable=False),
        sa.Column("after_snapshot", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["target_company_id"], ["company.id"]),
    )
        op.create_index("ix_owner_audit_log_actor", "owner_audit_log", ["actor_user_id"])
        op.create_index("ix_owner_audit_log_company", "owner_audit_log", ["target_company_id"])
        op.create_index("ix_owner_audit_log_action", "owner_audit_log", ["action"])
