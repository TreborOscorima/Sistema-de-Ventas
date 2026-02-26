"""scope roles by company for tenant-safe rbac

Revision ID: b1c2d3e4f6a7
Revises: ab4ac3609ddf
Create Date: 2026-02-08 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f6a7"
down_revision: Union[str, Sequence[str], None] = "ab4ac3609ddf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_names = {idx.get("name") for idx in inspector.get_indexes(table_name)}
    if index_name in index_names:
        op.drop_index(index_name, table_name=table_name)


def _drop_constraint_if_exists(table_name: str, constraint_name: str, constraint_type: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if constraint_type == "unique":
        names = {c.get("name") for c in inspector.get_unique_constraints(table_name)}
    elif constraint_type == "foreignkey":
        names = {c.get("name") for c in inspector.get_foreign_keys(table_name)}
    else:
        names = set()
    if constraint_name in names:
        op.drop_constraint(constraint_name, table_name, type_=constraint_type)


def _get_index(table_name: str, index_name: str) -> dict | None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for idx in inspector.get_indexes(table_name):
        if idx.get("name") == index_name:
            return idx
    return None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col.get("name") == column_name for col in inspector.get_columns(table_name))


def _column_nullable(table_name: str, column_name: str) -> bool | None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for col in inspector.get_columns(table_name):
        if col.get("name") == column_name:
            return bool(col.get("nullable", True))
    return None


def _has_unique(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    names = {c.get("name") for c in inspector.get_unique_constraints(table_name)}
    return constraint_name in names


def _has_fk(table_name: str, constrained_columns: list[str], referred_table: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys(table_name):
        if fk.get("referred_table") != referred_table:
            continue
        if fk.get("constrained_columns") == constrained_columns:
            return True
    return False


def upgrade() -> None:
    """Upgrade schema and data for company-scoped roles."""
    if context.is_offline_mode():
        return
    bind = op.get_bind()

    if not _has_column("role", "company_id"):
        op.add_column("role", sa.Column("company_id", sa.Integer(), nullable=True))
    if _get_index("role", op.f("ix_role_company_id")) is None:
        op.create_index(op.f("ix_role_company_id"), "role", ["company_id"], unique=False)
    if not _has_fk("role", ["company_id"], "company"):
        op.create_foreign_key(
            "fk_role_company_id",
            "role",
            "company",
            ["company_id"],
            ["id"],
        )

    role_name_idx = _get_index("role", op.f("ix_role_name"))
    if role_name_idx is not None and role_name_idx.get("unique"):
        _drop_index_if_exists(op.f("ix_role_name"), "role")
        role_name_idx = None
    if role_name_idx is None:
        op.create_index(op.f("ix_role_name"), "role", ["name"], unique=False)

    meta = sa.MetaData()
    role = sa.Table("role", meta, autoload_with=bind)
    user = sa.Table("user", meta, autoload_with=bind)
    role_permission = sa.Table("rolepermission", meta, autoload_with=bind)

    if "company_id" in role.c:
        old_roles = bind.execute(
            sa.select(role.c.id, role.c.name, role.c.description)
            .where(role.c.company_id.is_(None))
        ).mappings().all()
    else:
        old_roles = bind.execute(
            sa.select(role.c.id, role.c.name, role.c.description)
        ).mappings().all()

    for old_role in old_roles:
        company_ids = bind.execute(
            sa.select(sa.distinct(user.c.company_id))
            .where(user.c.role_id == old_role["id"])
            .where(user.c.company_id.isnot(None))
        ).scalars().all()

        if not company_ids:
            continue

        perm_ids = bind.execute(
            sa.select(role_permission.c.permission_id)
            .where(role_permission.c.role_id == old_role["id"])
        ).scalars().all()

        for company_id in company_ids:
            existing_role_id = bind.execute(
                sa.select(role.c.id)
                .where(role.c.company_id == int(company_id))
                .where(role.c.name == old_role["name"])
                .limit(1)
            ).scalar_one_or_none()
            if existing_role_id is not None:
                new_role_id = int(existing_role_id)
            else:
                inserted = bind.execute(
                    sa.insert(role).values(
                        company_id=int(company_id),
                        name=old_role["name"],
                        description=old_role["description"] or "",
                    )
                )
                new_role_id = int(inserted.inserted_primary_key[0])

            if perm_ids:
                existing_perm_ids = set(
                    bind.execute(
                        sa.select(role_permission.c.permission_id)
                        .where(role_permission.c.role_id == int(new_role_id))
                    ).scalars().all()
                )
                missing_perm_ids = [
                    int(permission_id)
                    for permission_id in perm_ids
                    if int(permission_id) not in existing_perm_ids
                ]
                if missing_perm_ids:
                    bind.execute(
                        sa.insert(role_permission),
                        [
                            {
                                "role_id": int(new_role_id),
                                "permission_id": permission_id,
                            }
                            for permission_id in missing_perm_ids
                        ],
                    )

            bind.execute(
                sa.update(user)
                .where(user.c.role_id == old_role["id"])
                .where(user.c.company_id == int(company_id))
                .values(role_id=int(new_role_id))
            )

    old_role_ids = [int(row["id"]) for row in old_roles]
    if old_role_ids:
        bind.execute(
            sa.delete(role_permission).where(role_permission.c.role_id.in_(old_role_ids))
        )
        bind.execute(sa.delete(role).where(role.c.id.in_(old_role_ids)))

    if not _has_unique("role", "uq_role_company_name"):
        op.create_unique_constraint(
            "uq_role_company_name",
            "role",
            ["company_id", "name"],
        )

    if _column_nullable("role", "company_id") is True:
        # MySQL exige soltar temporalmente FKs que referencian la columna a alterar.
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        dropped_fk_names: list[str] = []
        for fk in inspector.get_foreign_keys("role"):
            if fk.get("referred_table") != "company":
                continue
            if fk.get("constrained_columns") != ["company_id"]:
                continue
            fk_name = fk.get("name")
            if fk_name:
                op.drop_constraint(fk_name, "role", type_="foreignkey")
                dropped_fk_names.append(fk_name)

        op.alter_column("role", "company_id", existing_type=sa.Integer(), nullable=False)

        if not _has_fk("role", ["company_id"], "company"):
            op.create_foreign_key(
                dropped_fk_names[0] if dropped_fk_names else "fk_role_company_id",
                "role",
                "company",
                ["company_id"],
                ["id"],
            )


def downgrade() -> None:
    """Downgrade to global roles."""
    if context.is_offline_mode():
        return
    bind = op.get_bind()

    if _column_nullable("role", "company_id") is False:
        op.alter_column("role", "company_id", existing_type=sa.Integer(), nullable=True)
    _drop_constraint_if_exists("role", "uq_role_company_name", "unique")

    meta = sa.MetaData()
    role = sa.Table("role", meta, autoload_with=bind)
    user = sa.Table("user", meta, autoload_with=bind)
    role_permission = sa.Table("rolepermission", meta, autoload_with=bind)

    company_roles = bind.execute(
        sa.select(role.c.id, role.c.name, role.c.description, role.c.company_id)
    ).mappings().all()

    global_role_by_name: dict[str, int] = {}

    for current_role in company_roles:
        role_name = str(current_role["name"] or "").strip()
        if not role_name:
            continue

        global_role_id = global_role_by_name.get(role_name)
        if global_role_id is None:
            inserted = bind.execute(
                sa.insert(role).values(
                    company_id=None,
                    name=role_name,
                    description=current_role["description"] or "",
                )
            )
            global_role_id = int(inserted.inserted_primary_key[0])
            global_role_by_name[role_name] = global_role_id

        bind.execute(
            sa.update(user)
            .where(user.c.role_id == current_role["id"])
            .values(role_id=global_role_id)
        )

        perm_ids = bind.execute(
            sa.select(role_permission.c.permission_id)
            .where(role_permission.c.role_id == current_role["id"])
        ).scalars().all()

        existing_perm_ids = set(
            bind.execute(
                sa.select(role_permission.c.permission_id)
                .where(role_permission.c.role_id == global_role_id)
            ).scalars().all()
        )

        missing_perm_ids = [int(pid) for pid in perm_ids if int(pid) not in existing_perm_ids]
        if missing_perm_ids:
            bind.execute(
                sa.insert(role_permission),
                [
                    {"role_id": global_role_id, "permission_id": permission_id}
                    for permission_id in missing_perm_ids
                ],
            )

    company_role_ids = [int(row["id"]) for row in company_roles]
    if company_role_ids:
        bind.execute(
            sa.delete(role_permission).where(role_permission.c.role_id.in_(company_role_ids))
        )
        bind.execute(sa.delete(role).where(role.c.id.in_(company_role_ids)))

    _drop_constraint_if_exists("role", "fk_role_company_id", "foreignkey")
    _drop_index_if_exists(op.f("ix_role_company_id"), "role")
    _drop_index_if_exists(op.f("ix_role_name"), "role")
    op.create_index(op.f("ix_role_name"), "role", ["name"], unique=True)
    if _has_column("role", "company_id"):
        op.drop_column("role", "company_id")
