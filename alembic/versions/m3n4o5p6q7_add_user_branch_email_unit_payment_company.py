"""add user email/branch, add company_id to unit/paymentmethod

ID de revision: m3n4o5p6q7
Revisa: l2m3n4o5p6
Fecha de creacion: 2026-01-29 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# identificadores de revision, usados por Alembic.
revision: str = "m3n4o5p6q7"
down_revision: Union[str, Sequence[str], None] = "l2m3n4o5p6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    op.add_column(
        "user",
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)

    op.add_column("user", sa.Column("branch_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_user_branch_id"), "user", ["branch_id"], unique=False)
    op.create_foreign_key(
        "fk_user_branch_id",
        "user",
        "branch",
        ["branch_id"],
        ["id"],
    )

    op.add_column(
        "unit",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.create_index(op.f("ix_unit_company_id"), "unit", ["company_id"], unique=False)
    op.create_foreign_key(
        "fk_unit_company_id",
        "unit",
        "company",
        ["company_id"],
        ["id"],
    )
    op.alter_column("unit", "company_id", server_default=None)

    op.drop_index(op.f("ix_unit_name"), table_name="unit")
    op.create_index(op.f("ix_unit_name"), "unit", ["name"], unique=False)
    op.create_unique_constraint(
        "uq_unit_company_name",
        "unit",
        ["company_id", "name"],
    )

    op.add_column(
        "paymentmethod",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.create_index(
        op.f("ix_paymentmethod_company_id"),
        "paymentmethod",
        ["company_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_paymentmethod_company_id",
        "paymentmethod",
        "company",
        ["company_id"],
        ["id"],
    )
    op.alter_column("paymentmethod", "company_id", server_default=None)

    op.drop_index(op.f("ix_paymentmethod_code"), table_name="paymentmethod")
    op.drop_index(op.f("ix_paymentmethod_method_id"), table_name="paymentmethod")
    op.create_index(
        op.f("ix_paymentmethod_code"),
        "paymentmethod",
        ["code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_paymentmethod_method_id"),
        "paymentmethod",
        ["method_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_paymentmethod_company_code",
        "paymentmethod",
        ["company_id", "code"],
    )
    op.create_unique_constraint(
        "uq_paymentmethod_company_method_id",
        "paymentmethod",
        ["company_id", "method_id"],
    )


def downgrade() -> None:
    """Revertir esquema."""
    op.drop_constraint(
        "uq_paymentmethod_company_method_id", "paymentmethod", type_="unique"
    )
    op.drop_constraint(
        "uq_paymentmethod_company_code", "paymentmethod", type_="unique"
    )
    op.drop_index(op.f("ix_paymentmethod_method_id"), table_name="paymentmethod")
    op.drop_index(op.f("ix_paymentmethod_code"), table_name="paymentmethod")
    op.create_index(
        op.f("ix_paymentmethod_method_id"),
        "paymentmethod",
        ["method_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_paymentmethod_code"),
        "paymentmethod",
        ["code"],
        unique=True,
    )
    op.drop_constraint(
        "fk_paymentmethod_company_id", "paymentmethod", type_="foreignkey"
    )
    op.drop_index(op.f("ix_paymentmethod_company_id"), table_name="paymentmethod")
    op.drop_column("paymentmethod", "company_id")

    op.drop_constraint("uq_unit_company_name", "unit", type_="unique")
    op.drop_index(op.f("ix_unit_name"), table_name="unit")
    op.create_index(op.f("ix_unit_name"), "unit", ["name"], unique=True)
    op.drop_constraint("fk_unit_company_id", "unit", type_="foreignkey")
    op.drop_index(op.f("ix_unit_company_id"), table_name="unit")
    op.drop_column("unit", "company_id")

    op.drop_constraint("fk_user_branch_id", "user", type_="foreignkey")
    op.drop_index(op.f("ix_user_branch_id"), table_name="user")
    op.drop_column("user", "branch_id")

    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_column("user", "email")
