"""Layer 1 — Integrity & Security hardening (auditoría módulo #3).

Revision ID: l1m2n3o4p5q6
Revises: c3d4e5f6a7b8
Create Date: 2026-04-15

Objetivo: cerrar ventanas de leak multi-tenant, enforzar integridad
referencial explícita con ondelete, añadir CHECK constraints core,
convertir enums de Company a persistidos con validación en DB, y
prevenir duplicados de numeración fiscal.

Operaciones:
    1. user.email: DROP UNIQUE global, ADD UNIQUE (company_id, email).
    2. rolepermission: ADD UNIQUE (role_id, permission_id) + FKs CASCADE.
    3. company: CHECK max_branches/max_users >= 1 + enum check en
       plan_type/subscription_status.
    4. productkit: FKs CASCADE + CHECK quantity > 0.
    5. stockmovement: FKs product_id/user_id SET NULL.
    6. purchaseitem: FK purchase_id CASCADE, product_id SET NULL + CHECKs.
    7. purchaseorderitem: FK purchase_order_id CASCADE + CHECKs.
    8. sale: CHECK total_amount >= 0.
    9. salepayment: FK sale_id CASCADE.
   10. saleitem: FK sale_id CASCADE, otros SET NULL + CHECKs.
   11. saleinstallment: FK sale_id CASCADE + CHECKs.
   12. salereturn: FK original_sale_id CASCADE, user_id SET NULL + CHECK.
   13. salereturnitem: ADD company_id/branch_id (backfill desde parent),
       FKs CASCADE/RESTRICT/SET NULL, CHECKs, índice tenant.
   14. fiscaldocument: UNIQUE (company_id, serie, fiscal_number),
       FK sale_id RESTRICT + CHECKs.
   15. client: CHECKs credit_limit/current_debt >= 0.

Idempotencia: cada operación verifica existencia previa. Seguro de
re-ejecutar si falla a mitad (p. ej. por data que viola un CHECK).

Requisitos: MySQL 8.0.16+ (CHECK constraints enforzables).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision: str = "l1m2n3o4p5q6"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ═══════════════════════════════════════════════════════════════════
# Helpers de introspección (idempotencia)
# ═══════════════════════════════════════════════════════════════════
def _has_table(conn, table: str) -> bool:
    return table in sa_inspect(conn).get_table_names()


def _has_column(conn, table: str, col: str) -> bool:
    if not _has_table(conn, table):
        return False
    return col in [c["name"] for c in sa_inspect(conn).get_columns(table)]


def _has_unique(conn, table: str, name: str) -> bool:
    if not _has_table(conn, table):
        return False
    return any(
        uq.get("name") == name for uq in sa_inspect(conn).get_unique_constraints(table)
    )


def _has_index(conn, table: str, name: str) -> bool:
    if not _has_table(conn, table):
        return False
    return any(idx.get("name") == name for idx in sa_inspect(conn).get_indexes(table))


def _has_check(conn, table: str, name: str) -> bool:
    if not _has_table(conn, table):
        return False
    try:
        return any(
            cc.get("name") == name for cc in sa_inspect(conn).get_check_constraints(table)
        )
    except NotImplementedError:
        return False


def _find_fk_name(conn, table: str, column: str) -> str | None:
    """Devuelve el nombre del FK que referencia ``column`` en ``table``.

    MySQL autogenera nombres (``table_ibfk_N``) si no se especifica.
    """
    if not _has_table(conn, table):
        return None
    for fk in sa_inspect(conn).get_foreign_keys(table):
        if column in fk.get("constrained_columns", []):
            return fk.get("name")
    return None


def _drop_fk(conn, table: str, column: str) -> None:
    """Drop del FK que toca ``column``. No-op si no existe."""
    name = _find_fk_name(conn, table, column)
    if name:
        op.drop_constraint(name, table, type_="foreignkey")


def _ensure_fk(
    conn,
    *,
    table: str,
    column: str,
    ref_table: str,
    ref_column: str = "id",
    ondelete: str,
    name: str,
) -> None:
    """Drop del FK existente (cualquier ondelete) y creación con el nuevo
    ``ondelete``. Idempotente: si ya existe un FK con el nombre dado y la
    misma config, se recrea igual — MySQL no permite ``IF NOT EXISTS``
    para FKs, así que siempre drop + add."""
    _drop_fk(conn, table, column)
    op.create_foreign_key(
        name,
        table,
        ref_table,
        [column],
        [ref_column],
        ondelete=ondelete,
    )


# ═══════════════════════════════════════════════════════════════════
# UPGRADE
# ═══════════════════════════════════════════════════════════════════
def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. user.email UNIQUE por (company_id, email) ───────────────
    if _has_table(conn, "user"):
        # Drop índice UNIQUE global previo (nombre auto-generado por SQLAlchemy).
        for uq in sa_inspect(conn).get_unique_constraints("user"):
            cols = uq.get("column_names") or []
            if cols == ["email"]:
                op.drop_constraint(uq["name"], "user", type_="unique")
        # Algunos motores crean index adicional en lugar de constraint.
        for idx in sa_inspect(conn).get_indexes("user"):
            cols = idx.get("column_names") or []
            if cols == ["email"] and idx.get("unique"):
                op.drop_index(idx["name"], table_name="user")
        if not _has_unique(conn, "user", "uq_user_company_email"):
            op.create_unique_constraint(
                "uq_user_company_email", "user", ["company_id", "email"]
            )

    # ── 2. rolepermission UNIQUE + FKs CASCADE ─────────────────────
    if _has_table(conn, "rolepermission"):
        if not _has_unique(conn, "rolepermission", "uq_rolepermission_role_permission"):
            op.create_unique_constraint(
                "uq_rolepermission_role_permission",
                "rolepermission",
                ["role_id", "permission_id"],
            )
        # Asegurar índices en los FKs (muchos motores los crean implícitos, pero
        # forzamos explícito para optimizador).
        if not _has_index(conn, "rolepermission", "ix_rolepermission_role_id"):
            op.create_index(
                "ix_rolepermission_role_id", "rolepermission", ["role_id"]
            )
        if not _has_index(conn, "rolepermission", "ix_rolepermission_permission_id"):
            op.create_index(
                "ix_rolepermission_permission_id",
                "rolepermission",
                ["permission_id"],
            )
        _ensure_fk(
            conn,
            table="rolepermission",
            column="role_id",
            ref_table="role",
            ondelete="CASCADE",
            name="fk_rolepermission_role_id",
        )
        _ensure_fk(
            conn,
            table="rolepermission",
            column="permission_id",
            ref_table="permission",
            ondelete="CASCADE",
            name="fk_rolepermission_permission_id",
        )

    # ── 3. company CHECKs ──────────────────────────────────────────
    if _has_table(conn, "company"):
        if not _has_check(conn, "company", "ck_company_max_branches_min"):
            op.create_check_constraint(
                "ck_company_max_branches_min", "company", "max_branches >= 1"
            )
        if not _has_check(conn, "company", "ck_company_max_users_min"):
            op.create_check_constraint(
                "ck_company_max_users_min", "company", "max_users >= 1"
            )
        # Enum CHECK para plan_type y subscription_status.
        if not _has_check(conn, "company", "ck_company_plan_type_valid"):
            op.create_check_constraint(
                "ck_company_plan_type_valid",
                "company",
                "plan_type IN ('trial','standard','professional','enterprise')",
            )
        if not _has_check(conn, "company", "ck_company_subscription_status_valid"):
            op.create_check_constraint(
                "ck_company_subscription_status_valid",
                "company",
                "subscription_status IN ('active','warning','past_due','suspended')",
            )

    # ── 4. productkit FKs CASCADE + CHECK ──────────────────────────
    if _has_table(conn, "productkit"):
        _ensure_fk(
            conn,
            table="productkit",
            column="kit_product_id",
            ref_table="product",
            ondelete="CASCADE",
            name="fk_productkit_kit_product_id",
        )
        _ensure_fk(
            conn,
            table="productkit",
            column="component_product_id",
            ref_table="product",
            ondelete="CASCADE",
            name="fk_productkit_component_product_id",
        )
        if not _has_check(conn, "productkit", "ck_productkit_quantity_positive"):
            op.create_check_constraint(
                "ck_productkit_quantity_positive", "productkit", "quantity > 0"
            )

    # ── 5. stockmovement FKs SET NULL ──────────────────────────────
    if _has_table(conn, "stockmovement"):
        _ensure_fk(
            conn,
            table="stockmovement",
            column="product_id",
            ref_table="product",
            ondelete="SET NULL",
            name="fk_stockmovement_product_id",
        )
        _ensure_fk(
            conn,
            table="stockmovement",
            column="user_id",
            ref_table="user",
            ondelete="SET NULL",
            name="fk_stockmovement_user_id",
        )

    # ── 6. purchaseitem FKs + CHECKs ───────────────────────────────
    if _has_table(conn, "purchaseitem"):
        _ensure_fk(
            conn,
            table="purchaseitem",
            column="purchase_id",
            ref_table="purchase",
            ondelete="CASCADE",
            name="fk_purchaseitem_purchase_id",
        )
        _ensure_fk(
            conn,
            table="purchaseitem",
            column="product_id",
            ref_table="product",
            ondelete="SET NULL",
            name="fk_purchaseitem_product_id",
        )
        for cname, expr in (
            ("ck_purchaseitem_quantity_positive", "quantity > 0"),
            ("ck_purchaseitem_unit_cost_nonneg", "unit_cost >= 0"),
            ("ck_purchaseitem_subtotal_nonneg", "subtotal >= 0"),
        ):
            if not _has_check(conn, "purchaseitem", cname):
                op.create_check_constraint(cname, "purchaseitem", expr)

    # ── 7. purchaseorderitem FKs + CHECKs ──────────────────────────
    if _has_table(conn, "purchaseorderitem"):
        _ensure_fk(
            conn,
            table="purchaseorderitem",
            column="purchase_order_id",
            ref_table="purchaseorder",
            ondelete="CASCADE",
            name="fk_poitem_purchase_order_id",
        )
        _ensure_fk(
            conn,
            table="purchaseorderitem",
            column="product_id",
            ref_table="product",
            ondelete="SET NULL",
            name="fk_poitem_product_id",
        )
        for cname, expr in (
            ("ck_poitem_suggested_quantity_nonneg", "suggested_quantity >= 0"),
            ("ck_poitem_unit_cost_nonneg", "unit_cost >= 0"),
        ):
            if not _has_check(conn, "purchaseorderitem", cname):
                op.create_check_constraint(cname, "purchaseorderitem", expr)

    # ── 8. sale CHECK ──────────────────────────────────────────────
    if _has_table(conn, "sale") and not _has_check(conn, "sale", "ck_sale_total_nonneg"):
        op.create_check_constraint("ck_sale_total_nonneg", "sale", "total_amount >= 0")

    # ── 9. salepayment FK CASCADE ──────────────────────────────────
    if _has_table(conn, "salepayment"):
        _ensure_fk(
            conn,
            table="salepayment",
            column="sale_id",
            ref_table="sale",
            ondelete="CASCADE",
            name="fk_salepayment_sale_id",
        )

    # ── 10. saleitem FKs + CHECKs ──────────────────────────────────
    if _has_table(conn, "saleitem"):
        _ensure_fk(
            conn,
            table="saleitem",
            column="sale_id",
            ref_table="sale",
            ondelete="CASCADE",
            name="fk_saleitem_sale_id",
        )
        _ensure_fk(
            conn,
            table="saleitem",
            column="product_id",
            ref_table="product",
            ondelete="SET NULL",
            name="fk_saleitem_product_id",
        )
        _ensure_fk(
            conn,
            table="saleitem",
            column="product_variant_id",
            ref_table="productvariant",
            ondelete="SET NULL",
            name="fk_saleitem_product_variant_id",
        )
        _ensure_fk(
            conn,
            table="saleitem",
            column="product_batch_id",
            ref_table="productbatch",
            ondelete="SET NULL",
            name="fk_saleitem_product_batch_id",
        )
        _ensure_fk(
            conn,
            table="saleitem",
            column="kit_product_id",
            ref_table="product",
            ondelete="SET NULL",
            name="fk_saleitem_kit_product_id",
        )
        for cname, expr in (
            ("ck_saleitem_quantity_positive", "quantity > 0"),
            ("ck_saleitem_unit_price_nonneg", "unit_price >= 0"),
            ("ck_saleitem_subtotal_nonneg", "subtotal >= 0"),
        ):
            if not _has_check(conn, "saleitem", cname):
                op.create_check_constraint(cname, "saleitem", expr)

    # ── 11. saleinstallment FK + CHECKs ────────────────────────────
    if _has_table(conn, "saleinstallment"):
        _ensure_fk(
            conn,
            table="saleinstallment",
            column="sale_id",
            ref_table="sale",
            ondelete="CASCADE",
            name="fk_saleinstallment_sale_id",
        )
        for cname, expr in (
            ("ck_installment_number_positive", "number >= 1"),
            ("ck_installment_amount_nonneg", "amount >= 0"),
            ("ck_installment_paid_amount_nonneg", "paid_amount >= 0"),
        ):
            if not _has_check(conn, "saleinstallment", cname):
                op.create_check_constraint(cname, "saleinstallment", expr)

    # ── 12. salereturn FKs + CHECK ─────────────────────────────────
    if _has_table(conn, "salereturn"):
        _ensure_fk(
            conn,
            table="salereturn",
            column="original_sale_id",
            ref_table="sale",
            ondelete="CASCADE",
            name="fk_salereturn_original_sale_id",
        )
        _ensure_fk(
            conn,
            table="salereturn",
            column="user_id",
            ref_table="user",
            ondelete="SET NULL",
            name="fk_salereturn_user_id",
        )
        if not _has_check(conn, "salereturn", "ck_salereturn_refund_nonneg"):
            op.create_check_constraint(
                "ck_salereturn_refund_nonneg",
                "salereturn",
                "refund_amount >= 0",
            )

    # ── 13. salereturnitem: AÑADIR tenant + FKs + índice ───────────
    if _has_table(conn, "salereturnitem"):
        # 13a. columnas tenant nullable temporalmente para backfill.
        if not _has_column(conn, "salereturnitem", "company_id"):
            op.add_column(
                "salereturnitem",
                sa.Column("company_id", sa.Integer(), nullable=True),
            )
        if not _has_column(conn, "salereturnitem", "branch_id"):
            op.add_column(
                "salereturnitem",
                sa.Column("branch_id", sa.Integer(), nullable=True),
            )
        # 13b. backfill desde parent salereturn.
        op.execute(
            """
            UPDATE salereturnitem sri
            JOIN salereturn sr ON sri.sale_return_id = sr.id
            SET sri.company_id = sr.company_id,
                sri.branch_id  = sr.branch_id
            WHERE sri.company_id IS NULL OR sri.branch_id IS NULL
            """
        )
        # 13c. forzar NOT NULL tras backfill.
        op.alter_column(
            "salereturnitem",
            "company_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        op.alter_column(
            "salereturnitem",
            "branch_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        # 13d. FKs tenant + índices.
        if not _has_index(conn, "salereturnitem", "ix_salereturnitem_company_id"):
            op.create_index(
                "ix_salereturnitem_company_id",
                "salereturnitem",
                ["company_id"],
            )
        if not _has_index(conn, "salereturnitem", "ix_salereturnitem_branch_id"):
            op.create_index(
                "ix_salereturnitem_branch_id",
                "salereturnitem",
                ["branch_id"],
            )
        _ensure_fk(
            conn,
            table="salereturnitem",
            column="company_id",
            ref_table="company",
            ondelete="RESTRICT",
            name="fk_salereturnitem_company_id",
        )
        _ensure_fk(
            conn,
            table="salereturnitem",
            column="branch_id",
            ref_table="branch",
            ondelete="RESTRICT",
            name="fk_salereturnitem_branch_id",
        )
        # 13e. resto de FKs con ondelete correcto.
        _ensure_fk(
            conn,
            table="salereturnitem",
            column="sale_return_id",
            ref_table="salereturn",
            ondelete="CASCADE",
            name="fk_salereturnitem_sale_return_id",
        )
        _ensure_fk(
            conn,
            table="salereturnitem",
            column="sale_item_id",
            ref_table="saleitem",
            ondelete="RESTRICT",
            name="fk_salereturnitem_sale_item_id",
        )
        _ensure_fk(
            conn,
            table="salereturnitem",
            column="product_id",
            ref_table="product",
            ondelete="SET NULL",
            name="fk_salereturnitem_product_id",
        )
        _ensure_fk(
            conn,
            table="salereturnitem",
            column="product_variant_id",
            ref_table="productvariant",
            ondelete="SET NULL",
            name="fk_salereturnitem_product_variant_id",
        )
        _ensure_fk(
            conn,
            table="salereturnitem",
            column="product_batch_id",
            ref_table="productbatch",
            ondelete="SET NULL",
            name="fk_salereturnitem_product_batch_id",
        )
        # 13f. índice compuesto tenant para queries POS.
        if not _has_index(conn, "salereturnitem", "ix_salereturnitem_tenant_return"):
            op.create_index(
                "ix_salereturnitem_tenant_return",
                "salereturnitem",
                ["company_id", "branch_id", "sale_return_id"],
            )
        # 13g. CHECKs.
        for cname, expr in (
            ("ck_salereturnitem_quantity_positive", "quantity > 0"),
            ("ck_salereturnitem_refund_nonneg", "refund_subtotal >= 0"),
        ):
            if not _has_check(conn, "salereturnitem", cname):
                op.create_check_constraint(cname, "salereturnitem", expr)

    # ── 14. fiscaldocument UNIQUE + FK RESTRICT + CHECKs ───────────
    if _has_table(conn, "fiscaldocument"):
        if not _has_unique(
            conn, "fiscaldocument", "uq_fiscaldocument_company_serie_number"
        ):
            op.create_unique_constraint(
                "uq_fiscaldocument_company_serie_number",
                "fiscaldocument",
                ["company_id", "serie", "fiscal_number"],
            )
        _ensure_fk(
            conn,
            table="fiscaldocument",
            column="sale_id",
            ref_table="sale",
            ondelete="RESTRICT",
            name="fk_fiscaldocument_sale_id",
        )
        for cname, expr in (
            ("ck_fiscaldoc_taxable_nonneg", "taxable_amount >= 0"),
            ("ck_fiscaldoc_tax_nonneg", "tax_amount >= 0"),
            ("ck_fiscaldoc_total_nonneg", "total_amount >= 0"),
            ("ck_fiscaldoc_retry_nonneg", "retry_count >= 0"),
        ):
            if not _has_check(conn, "fiscaldocument", cname):
                op.create_check_constraint(cname, "fiscaldocument", expr)

    # ── 15. client CHECKs ──────────────────────────────────────────
    if _has_table(conn, "client"):
        for cname, expr in (
            ("ck_client_credit_limit_nonneg", "credit_limit >= 0"),
            ("ck_client_current_debt_nonneg", "current_debt >= 0"),
        ):
            if not _has_check(conn, "client", cname):
                op.create_check_constraint(cname, "client", expr)


# ═══════════════════════════════════════════════════════════════════
# DOWNGRADE — restaura estado previo.
# ═══════════════════════════════════════════════════════════════════
def downgrade() -> None:
    conn = op.get_bind()

    # ── 15. client CHECKs
    for cname in ("ck_client_credit_limit_nonneg", "ck_client_current_debt_nonneg"):
        if _has_check(conn, "client", cname):
            op.drop_constraint(cname, "client", type_="check")

    # ── 14. fiscaldocument
    for cname in (
        "ck_fiscaldoc_taxable_nonneg",
        "ck_fiscaldoc_tax_nonneg",
        "ck_fiscaldoc_total_nonneg",
        "ck_fiscaldoc_retry_nonneg",
    ):
        if _has_check(conn, "fiscaldocument", cname):
            op.drop_constraint(cname, "fiscaldocument", type_="check")
    if _has_unique(conn, "fiscaldocument", "uq_fiscaldocument_company_serie_number"):
        op.drop_constraint(
            "uq_fiscaldocument_company_serie_number",
            "fiscaldocument",
            type_="unique",
        )

    # ── 13. salereturnitem — drop CHECKs, índice, FKs, columnas.
    for cname in (
        "ck_salereturnitem_quantity_positive",
        "ck_salereturnitem_refund_nonneg",
    ):
        if _has_check(conn, "salereturnitem", cname):
            op.drop_constraint(cname, "salereturnitem", type_="check")
    if _has_index(conn, "salereturnitem", "ix_salereturnitem_tenant_return"):
        op.drop_index("ix_salereturnitem_tenant_return", table_name="salereturnitem")
    for fk_name in (
        "fk_salereturnitem_company_id",
        "fk_salereturnitem_branch_id",
    ):
        try:
            op.drop_constraint(fk_name, "salereturnitem", type_="foreignkey")
        except Exception:
            pass
    if _has_index(conn, "salereturnitem", "ix_salereturnitem_company_id"):
        op.drop_index("ix_salereturnitem_company_id", table_name="salereturnitem")
    if _has_index(conn, "salereturnitem", "ix_salereturnitem_branch_id"):
        op.drop_index("ix_salereturnitem_branch_id", table_name="salereturnitem")
    if _has_column(conn, "salereturnitem", "company_id"):
        op.drop_column("salereturnitem", "company_id")
    if _has_column(conn, "salereturnitem", "branch_id"):
        op.drop_column("salereturnitem", "branch_id")

    # ── 12. salereturn
    if _has_check(conn, "salereturn", "ck_salereturn_refund_nonneg"):
        op.drop_constraint("ck_salereturn_refund_nonneg", "salereturn", type_="check")

    # ── 11. saleinstallment
    for cname in (
        "ck_installment_number_positive",
        "ck_installment_amount_nonneg",
        "ck_installment_paid_amount_nonneg",
    ):
        if _has_check(conn, "saleinstallment", cname):
            op.drop_constraint(cname, "saleinstallment", type_="check")

    # ── 10. saleitem
    for cname in (
        "ck_saleitem_quantity_positive",
        "ck_saleitem_unit_price_nonneg",
        "ck_saleitem_subtotal_nonneg",
    ):
        if _has_check(conn, "saleitem", cname):
            op.drop_constraint(cname, "saleitem", type_="check")

    # ── 8. sale
    if _has_check(conn, "sale", "ck_sale_total_nonneg"):
        op.drop_constraint("ck_sale_total_nonneg", "sale", type_="check")

    # ── 7. purchaseorderitem
    for cname in (
        "ck_poitem_suggested_quantity_nonneg",
        "ck_poitem_unit_cost_nonneg",
    ):
        if _has_check(conn, "purchaseorderitem", cname):
            op.drop_constraint(cname, "purchaseorderitem", type_="check")

    # ── 6. purchaseitem
    for cname in (
        "ck_purchaseitem_quantity_positive",
        "ck_purchaseitem_unit_cost_nonneg",
        "ck_purchaseitem_subtotal_nonneg",
    ):
        if _has_check(conn, "purchaseitem", cname):
            op.drop_constraint(cname, "purchaseitem", type_="check")

    # ── 4. productkit
    if _has_check(conn, "productkit", "ck_productkit_quantity_positive"):
        op.drop_constraint(
            "ck_productkit_quantity_positive", "productkit", type_="check"
        )

    # ── 3. company
    for cname in (
        "ck_company_max_branches_min",
        "ck_company_max_users_min",
        "ck_company_plan_type_valid",
        "ck_company_subscription_status_valid",
    ):
        if _has_check(conn, "company", cname):
            op.drop_constraint(cname, "company", type_="check")

    # ── 2. rolepermission
    if _has_unique(conn, "rolepermission", "uq_rolepermission_role_permission"):
        op.drop_constraint(
            "uq_rolepermission_role_permission", "rolepermission", type_="unique"
        )

    # ── 1. user.email
    if _has_unique(conn, "user", "uq_user_company_email"):
        op.drop_constraint("uq_user_company_email", "user", type_="unique")

    # Nota: los cambios de ondelete en FKs NO se revierten — el estado
    # previo usaba ondelete=RESTRICT (default MySQL). Dejar RESTRICT tras
    # un downgrade no introduce riesgo, sólo menor flexibilidad. Si se
    # necesita revertir estrictamente, usar un rollback de schema completo.
