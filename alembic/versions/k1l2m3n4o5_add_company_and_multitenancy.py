"""add company and branch tables, add company_id columns

ID de revision: k1l2m3n4o5
Revisa: j1k2l3m4n5
Fecha de creacion: 2026-01-29 12:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime, timedelta

from alembic import op
import sqlalchemy as sa
import sqlmodel


# identificadores de revision, usados por Alembic.
revision: str = "k1l2m3n4o5"
down_revision: Union[str, Sequence[str], None] = "j1k2l3m4n5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    op.create_table(
        "company",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("ruc", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_company_name"), "company", ["name"], unique=False)
    op.create_index(op.f("ix_company_ruc"), "company", ["ruc"], unique=True)

    op.create_table(
        "branch",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("address", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_branch_company_id"), "branch", ["company_id"], unique=False)
    op.create_index(op.f("ix_branch_name"), "branch", ["name"], unique=False)

    bind = op.get_bind()
    now = datetime.now()
    trial_ends = now + timedelta(days=15)
    bind.execute(
        sa.text(
            ""
            "INSERT INTO company (id, name, ruc, is_active, trial_ends_at, created_at) "
            "VALUES (:id, :name, :ruc, :is_active, :trial_ends_at, :created_at)"
        ),
        {
            "id": 1,
            "name": "Default Company",
            "ruc": "00000000000",
            "is_active": True,
            "trial_ends_at": trial_ends,
            "created_at": now,
        },
    )

    op.add_column(
        "user",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.create_index(op.f("ix_user_company_id"), "user", ["company_id"], unique=False)
    op.create_foreign_key(
        "fk_user_company_id",
        "user",
        "company",
        ["company_id"],
        ["id"],
    )
    op.alter_column("user", "company_id", server_default=None)

    op.add_column(
        "product",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.create_index(
        op.f("ix_product_company_id"),
        "product",
        ["company_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_product_company_id",
        "product",
        "company",
        ["company_id"],
        ["id"],
    )
    op.alter_column("product", "company_id", server_default=None)

    op.add_column(
        "category",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.create_index(
        op.f("ix_category_company_id"),
        "category",
        ["company_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_category_company_id",
        "category",
        "company",
        ["company_id"],
        ["id"],
    )
    op.alter_column("category", "company_id", server_default=None)

    op.add_column(
        "client",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.create_index(
        op.f("ix_client_company_id"),
        "client",
        ["company_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_client_company_id",
        "client",
        "company",
        ["company_id"],
        ["id"],
    )
    op.alter_column("client", "company_id", server_default=None)

    op.add_column(
        "sale",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.create_index(op.f("ix_sale_company_id"), "sale", ["company_id"], unique=False)
    op.create_foreign_key(
        "fk_sale_company_id",
        "sale",
        "company",
        ["company_id"],
        ["id"],
    )
    op.alter_column("sale", "company_id", server_default=None)

    op.add_column(
        "cashboxsession",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.create_index(
        op.f("ix_cashboxsession_company_id"),
        "cashboxsession",
        ["company_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_cashboxsession_company_id",
        "cashboxsession",
        "company",
        ["company_id"],
        ["id"],
    )
    op.alter_column("cashboxsession", "company_id", server_default=None)

    op.add_column(
        "cashboxlog",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.create_index(
        op.f("ix_cashboxlog_company_id"),
        "cashboxlog",
        ["company_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_cashboxlog_company_id",
        "cashboxlog",
        "company",
        ["company_id"],
        ["id"],
    )
    op.alter_column("cashboxlog", "company_id", server_default=None)


def downgrade() -> None:
    """Revertir esquema."""
    op.drop_constraint("fk_cashboxlog_company_id", "cashboxlog", type_="foreignkey")
    op.drop_index(op.f("ix_cashboxlog_company_id"), table_name="cashboxlog")
    op.drop_column("cashboxlog", "company_id")

    op.drop_constraint("fk_cashboxsession_company_id", "cashboxsession", type_="foreignkey")
    op.drop_index(op.f("ix_cashboxsession_company_id"), table_name="cashboxsession")
    op.drop_column("cashboxsession", "company_id")

    op.drop_constraint("fk_sale_company_id", "sale", type_="foreignkey")
    op.drop_index(op.f("ix_sale_company_id"), table_name="sale")
    op.drop_column("sale", "company_id")

    op.drop_constraint("fk_client_company_id", "client", type_="foreignkey")
    op.drop_index(op.f("ix_client_company_id"), table_name="client")
    op.drop_column("client", "company_id")

    op.drop_constraint("fk_category_company_id", "category", type_="foreignkey")
    op.drop_index(op.f("ix_category_company_id"), table_name="category")
    op.drop_column("category", "company_id")

    op.drop_constraint("fk_product_company_id", "product", type_="foreignkey")
    op.drop_index(op.f("ix_product_company_id"), table_name="product")
    op.drop_column("product", "company_id")

    op.drop_constraint("fk_user_company_id", "user", type_="foreignkey")
    op.drop_index(op.f("ix_user_company_id"), table_name="user")
    op.drop_column("user", "company_id")

    op.drop_index(op.f("ix_branch_name"), table_name="branch")
    op.drop_index(op.f("ix_branch_company_id"), table_name="branch")
    op.drop_table("branch")

    op.drop_index(op.f("ix_company_ruc"), table_name="company")
    op.drop_index(op.f("ix_company_name"), table_name="company")
    op.drop_table("company")
