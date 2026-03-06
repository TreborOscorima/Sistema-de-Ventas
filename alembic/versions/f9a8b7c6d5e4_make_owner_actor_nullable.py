"""make owner audit actor nullable

ID de revision: f9a8b7c6d5e4
Revisa: cfa77546ed70
Fecha de creacion: 2026-03-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# identificadores de revision, usados por Alembic.
revision: str = "f9a8b7c6d5e4"
down_revision: Union[str, Sequence[str], None] = "cfa77546ed70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ACTOR_FK_NAME = "fk_owner_audit_log_actor_user_id_user"


def _actor_fk_names(insp) -> list[str]:
    names: list[str] = []
    for fk in insp.get_foreign_keys("owner_audit_log"):
        if fk.get("constrained_columns") == ["actor_user_id"] and fk.get("referred_table") == "user":
            if fk.get("name"):
                names.append(fk["name"])
    return names


def upgrade() -> None:
    """Permite auditar acciones owner por email sin requerir user.id interno."""
    bind = op.get_bind()
    insp = sa_inspect(bind)

    if "owner_audit_log" not in insp.get_table_names():
        return

    columns = {col["name"]: col for col in insp.get_columns("owner_audit_log")}
    actor_col = columns.get("actor_user_id")
    if actor_col is None:
        return

    for fk_name in _actor_fk_names(insp):
        op.drop_constraint(fk_name, "owner_audit_log", type_="foreignkey")

    if not bool(actor_col.get("nullable", False)):
        op.alter_column(
            "owner_audit_log",
            "actor_user_id",
            existing_type=sa.Integer(),
            nullable=True,
        )

    insp = sa_inspect(bind)
    if not _actor_fk_names(insp):
        op.create_foreign_key(
            ACTOR_FK_NAME,
            "owner_audit_log",
            "user",
            ["actor_user_id"],
            ["id"],
        )


def downgrade() -> None:
    """Revierte a NOT NULL solo si no existen filas con actor_user_id nulo."""
    bind = op.get_bind()
    insp = sa_inspect(bind)

    if "owner_audit_log" not in insp.get_table_names():
        return

    columns = {col["name"]: col for col in insp.get_columns("owner_audit_log")}
    actor_col = columns.get("actor_user_id")
    if actor_col is None:
        return

    null_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM owner_audit_log WHERE actor_user_id IS NULL")
    ).scalar()
    if int(null_count or 0) > 0:
        raise RuntimeError(
            "No se puede revertir: owner_audit_log contiene filas con actor_user_id NULL."
        )

    for fk_name in _actor_fk_names(insp):
        op.drop_constraint(fk_name, "owner_audit_log", type_="foreignkey")

    if bool(actor_col.get("nullable", False)):
        op.alter_column(
            "owner_audit_log",
            "actor_user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    insp = sa_inspect(bind)
    if not _actor_fk_names(insp):
        op.create_foreign_key(
            ACTOR_FK_NAME,
            "owner_audit_log",
            "user",
            ["actor_user_id"],
            ["id"],
        )
