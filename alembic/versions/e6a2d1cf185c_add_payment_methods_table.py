"""agregar tabla de metodos de pago

ID de revision: e6a2d1cf185c
Revisa: 4946658237b1
Fecha de creacion: 2026-01-04 07:01:08.589880

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# identificadores de revision, usados por Alembic.
revision: str = 'e6a2d1cf185c'
down_revision: Union[str, Sequence[str], None] = '4946658237b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema de métodos de pago de forma idempotente."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    def _has_table(table_name: str) -> bool:
        return inspector.has_table(table_name)

    def _has_column(table_name: str, column_name: str) -> bool:
        return any(col["name"] == column_name for col in inspector.get_columns(table_name))

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))

    def _has_fk(table_name: str, constrained_cols: list[str], referred_table: str) -> bool:
        for fk in inspector.get_foreign_keys(table_name):
            if fk.get("referred_table") != referred_table:
                continue
            if fk.get("constrained_columns") == constrained_cols:
                return True
        return False

    if not _has_table("paymentmethod"):
        return

    if not _has_column("cashboxlog", "payment_method_id"):
        op.add_column("cashboxlog", sa.Column("payment_method_id", sa.Integer(), nullable=True))
        inspector = sa_inspect(bind)
    if _has_column("cashboxlog", "payment_method_id") and not _has_fk(
        "cashboxlog", ["payment_method_id"], "paymentmethod"
    ):
        op.create_foreign_key(
            "fk_cashboxlog_payment_method_id",
            "cashboxlog",
            "paymentmethod",
            ["payment_method_id"],
            ["id"],
        )

    if not _has_column("paymentmethod", "code"):
        op.add_column(
            "paymentmethod",
            sa.Column("code", sa.String(length=255), nullable=False, server_default=sa.text("''")),
        )
        inspector = sa_inspect(bind)
    if not _has_column("paymentmethod", "is_active"):
        op.add_column(
            "paymentmethod",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        inspector = sa_inspect(bind)
    if not _has_column("paymentmethod", "allows_change"):
        op.add_column(
            "paymentmethod",
            sa.Column("allows_change", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        inspector = sa_inspect(bind)

    # Preservar datos legacy: asegurar códigos válidos y únicos antes del índice.
    if _has_column("paymentmethod", "code"):
        if _has_column("paymentmethod", "method_id"):
            op.execute(
                """
                UPDATE paymentmethod
                SET code = COALESCE(
                    NULLIF(TRIM(code), ''),
                    NULLIF(TRIM(method_id), ''),
                    CONCAT('legacy-', id)
                )
                WHERE code IS NULL OR TRIM(code) = ''
                """
            )
        else:
            op.execute(
                """
                UPDATE paymentmethod
                SET code = COALESCE(
                    NULLIF(TRIM(code), ''),
                    CONCAT('legacy-', id)
                )
                WHERE code IS NULL OR TRIM(code) = ''
                """
            )

        op.execute(
            """
            UPDATE paymentmethod pm
            JOIN (
                SELECT code, MIN(id) AS keep_id
                FROM paymentmethod
                WHERE code IS NOT NULL AND TRIM(code) <> ''
                GROUP BY code
                HAVING COUNT(*) > 1
            ) dup ON pm.code = dup.code AND pm.id <> dup.keep_id
            SET pm.code = CONCAT(pm.code, '-', pm.id)
            """
        )

    if _has_column("paymentmethod", "code") and not _has_index("paymentmethod", op.f("ix_paymentmethod_code")):
        op.create_index(op.f("ix_paymentmethod_code"), "paymentmethod", ["code"], unique=True)

    if not _has_column("salepayment", "payment_method_id"):
        op.add_column("salepayment", sa.Column("payment_method_id", sa.Integer(), nullable=True))
        inspector = sa_inspect(bind)
    if _has_column("salepayment", "payment_method_id") and not _has_fk(
        "salepayment", ["payment_method_id"], "paymentmethod"
    ):
        op.create_foreign_key(
            "fk_salepayment_payment_method_id",
            "salepayment",
            "paymentmethod",
            ["payment_method_id"],
            ["id"],
        )

    # Quitar defaults temporales para dejar el esquema como espera el modelo.
    if _has_column("paymentmethod", "code"):
        op.alter_column("paymentmethod", "code", server_default=None)
    if _has_column("paymentmethod", "is_active"):
        op.alter_column("paymentmethod", "is_active", server_default=None)
    if _has_column("paymentmethod", "allows_change"):
        op.alter_column("paymentmethod", "allows_change", server_default=None)


def downgrade() -> None:
    """Revertir esquema."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    def _has_table(table_name: str) -> bool:
        return inspector.has_table(table_name)

    def _has_column(table_name: str, column_name: str) -> bool:
        return any(col["name"] == column_name for col in inspector.get_columns(table_name))

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))

    if _has_table("salepayment") and _has_column("salepayment", "payment_method_id"):
        try:
            op.drop_constraint("fk_salepayment_payment_method_id", "salepayment", type_="foreignkey")
        except Exception:
            pass
        op.drop_column("salepayment", "payment_method_id")

    if _has_table("paymentmethod") and _has_index("paymentmethod", op.f("ix_paymentmethod_code")):
        op.drop_index(op.f("ix_paymentmethod_code"), table_name="paymentmethod")
    if _has_table("paymentmethod") and _has_column("paymentmethod", "allows_change"):
        op.drop_column("paymentmethod", "allows_change")
    if _has_table("paymentmethod") and _has_column("paymentmethod", "is_active"):
        op.drop_column("paymentmethod", "is_active")
    if _has_table("paymentmethod") and _has_column("paymentmethod", "code"):
        op.drop_column("paymentmethod", "code")

    if _has_table("cashboxlog") and _has_column("cashboxlog", "payment_method_id"):
        try:
            op.drop_constraint("fk_cashboxlog_payment_method_id", "cashboxlog", type_="foreignkey")
        except Exception:
            pass
        op.drop_column("cashboxlog", "payment_method_id")
