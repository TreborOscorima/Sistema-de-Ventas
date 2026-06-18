"""SC-3/4/5 — FK ondelete explícito en userbranch, user, pricetier, productattribute

Revision ID: h3i4j5k6
Revises: g2h3i4j5
Create Date: 2026-06-18

Operaciones:
  1. userbranch.user_id   → user.id          CASCADE
  2. userbranch.branch_id → branch.id        CASCADE
  3. user.role_id         → role.id          RESTRICT
  4. pricetier.product_id → product.id       CASCADE
  5. pricetier.product_variant_id → productvariant.id  CASCADE
  6. productattribute.product_id  → product.id         CASCADE

Sin ondelete previo el comportamiento era RESTRICT implícito en MySQL.
CASCADE en tablas hijas de producto evita errores 1451 al eliminar productos.
RESTRICT en user.role_id previene borrado accidental de roles con usuarios asignados.

Idempotente: drop del FK existente (sea cual sea el nombre auto-generado por
MySQL) y recreación con el ondelete deseado.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect as sa_inspect


revision: str = "h3i4j5k6"
down_revision: Union[str, Sequence[str], None] = "g2h3i4j5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn, table: str) -> bool:
    return table in sa_inspect(conn).get_table_names()


def _find_fk_name(conn, table: str, column: str) -> str | None:
    if not _has_table(conn, table):
        return None
    for fk in sa_inspect(conn).get_foreign_keys(table):
        if column in fk.get("constrained_columns", []):
            return fk.get("name")
    return None


def _ensure_fk(conn, *, table: str, column: str, ref_table: str,
               ref_column: str = "id", ondelete: str, name: str) -> None:
    existing = _find_fk_name(conn, table, column)
    if existing:
        op.drop_constraint(existing, table, type_="foreignkey")
    op.create_foreign_key(name, table, ref_table, [column], [ref_column], ondelete=ondelete)


def upgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, "userbranch"):
        _ensure_fk(conn, table="userbranch", column="user_id",
                   ref_table="user", ondelete="CASCADE",
                   name="fk_userbranch_user_id_user")
        _ensure_fk(conn, table="userbranch", column="branch_id",
                   ref_table="branch", ondelete="CASCADE",
                   name="fk_userbranch_branch_id_branch")

    if _has_table(conn, "user"):
        _ensure_fk(conn, table="user", column="role_id",
                   ref_table="role", ondelete="RESTRICT",
                   name="fk_user_role_id_role")

    if _has_table(conn, "pricetier"):
        _ensure_fk(conn, table="pricetier", column="product_id",
                   ref_table="product", ondelete="CASCADE",
                   name="fk_pricetier_product_id_product")
        _ensure_fk(conn, table="pricetier", column="product_variant_id",
                   ref_table="productvariant", ondelete="CASCADE",
                   name="fk_pricetier_product_variant_id_productvariant")

    if _has_table(conn, "productattribute"):
        _ensure_fk(conn, table="productattribute", column="product_id",
                   ref_table="product", ondelete="CASCADE",
                   name="fk_productattribute_product_id_product")


def downgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, "userbranch"):
        _ensure_fk(conn, table="userbranch", column="user_id",
                   ref_table="user", ondelete="NO ACTION",
                   name="fk_userbranch_user_id_user")
        _ensure_fk(conn, table="userbranch", column="branch_id",
                   ref_table="branch", ondelete="NO ACTION",
                   name="fk_userbranch_branch_id_branch")

    if _has_table(conn, "user"):
        _ensure_fk(conn, table="user", column="role_id",
                   ref_table="role", ondelete="NO ACTION",
                   name="fk_user_role_id_role")

    if _has_table(conn, "pricetier"):
        _ensure_fk(conn, table="pricetier", column="product_id",
                   ref_table="product", ondelete="NO ACTION",
                   name="fk_pricetier_product_id_product")
        _ensure_fk(conn, table="pricetier", column="product_variant_id",
                   ref_table="productvariant", ondelete="NO ACTION",
                   name="fk_pricetier_product_variant_id_productvariant")

    if _has_table(conn, "productattribute"):
        _ensure_fk(conn, table="productattribute", column="product_id",
                   ref_table="product", ondelete="NO ACTION",
                   name="fk_productattribute_product_id_product")
