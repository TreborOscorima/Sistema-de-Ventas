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


def upgrade() -> None:
    """Upgrade schema and data for company-scoped roles."""
    if context.is_offline_mode():
        return
    bind = op.get_bind()

    op.add_column("role", sa.Column("company_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_role_company_id"), "role", ["company_id"], unique=False)
    op.create_foreign_key(
        "fk_role_company_id",
        "role",
        "company",
        ["company_id"],
        ["id"],
    )
    _drop_index_if_exists(op.f("ix_role_name"), "role")
    op.create_index(op.f("ix_role_name"), "role", ["name"], unique=False)

    meta = sa.MetaData()
    role = sa.Table("role", meta, autoload_with=bind)
    user = sa.Table("user", meta, autoload_with=bind)
    role_permission = sa.Table("rolepermission", meta, autoload_with=bind)

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
            inserted = bind.execute(
                sa.insert(role).values(
                    company_id=int(company_id),
                    name=old_role["name"],
                    description=old_role["description"] or "",
                )
            )
            new_role_id = inserted.inserted_primary_key[0]

            if perm_ids:
                bind.execute(
                    sa.insert(role_permission),
                    [
                        {
                            "role_id": int(new_role_id),
                            "permission_id": int(permission_id),
                        }
                        for permission_id in perm_ids
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

    op.create_unique_constraint(
        "uq_role_company_name",
        "role",
        ["company_id", "name"],
    )
    op.alter_column("role", "company_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    """Downgrade to global roles."""
    if context.is_offline_mode():
        return
    bind = op.get_bind()
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
    op.drop_column("role", "company_id")
