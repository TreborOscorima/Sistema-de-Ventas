"""Utilidades compartidas para recalculación de stock.

Este módulo centraliza la lógica de recalculación de totales de stock
para evitar duplicación entre cash_state (anulación de ventas) e
inventory_state (ajuste de inventario).

Patrón de recalculación de stock (3 fases):
    1. Variantes con batches: stock = SUM(batches.stock)
    2. Productos con variantes: stock = SUM(variants.stock)
    3. Productos con batches directos (sin variantes): stock = SUM(batches.stock)

Uso::

    from app.utils.stock import recalculate_stock_totals

    recalculate_stock_totals(
        session=session,
        company_id=company_id,
        branch_id=branch_id,
        variants_from_batches={variant_id_1, variant_id_2},
        products_from_variants={product_id_1},
        products_from_batches={product_id_2},
    )
"""
from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import func
from sqlmodel import select

from app.models import Product, ProductBatch, ProductVariant


def _extract_total(row: Any) -> Any:
    """Extrae valor escalar de un resultado de SUM/COALESCE.

    Maneja los 4 formatos posibles: None, empty tuple, tuple, o valor escalar.
    """
    if row is None:
        return 0
    if isinstance(row, tuple):
        return row[0] or 0 if row else 0
    return row or 0


def recalculate_stock_totals(
    session,
    company_id: int,
    branch_id: int,
    variants_from_batches: set[int] | None = None,
    products_from_variants: set[int] | None = None,
    products_from_batches: set[int] | None = None,
    normalize_fn: Callable | None = None,
) -> set[int]:
    """Recalcula totales de stock en las 3 fases estándar.

    Args:
        session: Sesión de SQLAlchemy/SQLModel (sync)
        company_id: ID de la empresa (tenant)
        branch_id: ID de la sucursal (tenant)
        variants_from_batches: IDs de variantes cuyo stock debe
            recalcularse a partir de sus batches
        products_from_variants: IDs de productos cuyo stock debe
            recalcularse a partir de sus variantes
        products_from_batches: IDs de productos cuyo stock debe
            recalcularse a partir de batches directos (sin variante)
        normalize_fn: Función opcional para normalizar stock
            (ej. redondeo según unidad). Recibe (total_stock, product)
            y retorna el valor normalizado.

    Returns:
        Set de product IDs que fueron actualizados (para invalidar caches).
    """
    variants_from_batches = variants_from_batches or set()
    products_from_variants = products_from_variants or set()
    products_from_batches = products_from_batches or set()
    updated_products: set[int] = set()

    # ── Fase 1: Recalcular variantes desde batches (bulk) ──
    if variants_from_batches:
        ids = list(variants_from_batches)
        sums_f1 = {
            row[0]: (row[1] or 0)
            for row in session.exec(
                select(
                    ProductBatch.product_variant_id,
                    func.coalesce(func.sum(ProductBatch.stock), 0),
                )
                .where(ProductBatch.product_variant_id.in_(ids))
                .where(ProductBatch.company_id == company_id)
                .where(ProductBatch.branch_id == branch_id)
                .group_by(ProductBatch.product_variant_id)
            ).all()
        }
        variants_map = {
            v.id: v
            for v in session.exec(
                select(ProductVariant)
                .where(ProductVariant.id.in_(ids))
                .where(ProductVariant.company_id == company_id)
                .where(ProductVariant.branch_id == branch_id)
            ).all()
        }
        for vid in variants_from_batches:
            v = variants_map.get(vid)
            if v:
                v.stock = sums_f1.get(vid, 0)
                session.add(v)
                products_from_variants.add(v.product_id)

    # ── Fase 2: Recalcular productos desde variantes (bulk) ──
    if products_from_variants:
        ids = list(products_from_variants)
        sums_f2 = {
            row[0]: (row[1] or 0)
            for row in session.exec(
                select(
                    ProductVariant.product_id,
                    func.coalesce(func.sum(ProductVariant.stock), 0),
                )
                .where(ProductVariant.product_id.in_(ids))
                .where(ProductVariant.company_id == company_id)
                .where(ProductVariant.branch_id == branch_id)
                .group_by(ProductVariant.product_id)
            ).all()
        }
        products_map = {
            p.id: p
            for p in session.exec(
                select(Product)
                .where(Product.id.in_(ids))
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
            ).all()
        }
        for pid in products_from_variants:
            p = products_map.get(pid)
            if p:
                total = sums_f2.get(pid, 0)
                p.stock = normalize_fn(total, p) if normalize_fn else total
                session.add(p)
                updated_products.add(pid)

    # ── Fase 3: Recalcular productos desde batches directos (bulk) ──
    remaining = products_from_batches - products_from_variants
    if remaining:
        ids = list(remaining)
        sums_f3 = {
            row[0]: (row[1] or 0)
            for row in session.exec(
                select(
                    ProductBatch.product_id,
                    func.coalesce(func.sum(ProductBatch.stock), 0),
                )
                .where(ProductBatch.product_id.in_(ids))
                .where(ProductBatch.product_variant_id.is_(None))
                .where(ProductBatch.company_id == company_id)
                .where(ProductBatch.branch_id == branch_id)
                .group_by(ProductBatch.product_id)
            ).all()
        }
        products_map3 = {
            p.id: p
            for p in session.exec(
                select(Product)
                .where(Product.id.in_(ids))
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
            ).all()
        }
        for pid in remaining:
            p = products_map3.get(pid)
            if p:
                total = sums_f3.get(pid, 0)
                p.stock = normalize_fn(total, p) if normalize_fn else total
                session.add(p)
                updated_products.add(pid)

    return updated_products
