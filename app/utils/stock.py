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

    # ── Fase 1: Recalcular variantes desde batches ──
    if variants_from_batches:
        for variant_id in variants_from_batches:
            total_stock = _extract_total(session.exec(
                select(func.coalesce(func.sum(ProductBatch.stock), 0))
                .where(ProductBatch.product_variant_id == variant_id)
                .where(ProductBatch.company_id == company_id)
                .where(ProductBatch.branch_id == branch_id)
            ).first())
            variant_row = session.exec(
                select(ProductVariant)
                .where(ProductVariant.id == variant_id)
                .where(ProductVariant.company_id == company_id)
                .where(ProductVariant.branch_id == branch_id)
            ).first()
            if variant_row:
                variant_row.stock = total_stock
                session.add(variant_row)
                products_from_variants.add(variant_row.product_id)

    # ── Fase 2: Recalcular productos desde variantes ──
    if products_from_variants:
        for product_id in products_from_variants:
            total_stock = _extract_total(session.exec(
                select(func.coalesce(func.sum(ProductVariant.stock), 0))
                .where(ProductVariant.product_id == product_id)
                .where(ProductVariant.company_id == company_id)
                .where(ProductVariant.branch_id == branch_id)
            ).first())
            product = session.exec(
                select(Product)
                .where(Product.id == product_id)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
            ).first()
            if product:
                if normalize_fn:
                    product.stock = normalize_fn(total_stock, product)
                else:
                    product.stock = total_stock
                session.add(product)
                updated_products.add(product_id)

    # ── Fase 3: Recalcular productos desde batches directos ──
    remaining = products_from_batches - products_from_variants
    if remaining:
        for product_id in remaining:
            total_stock = _extract_total(session.exec(
                select(func.coalesce(func.sum(ProductBatch.stock), 0))
                .where(ProductBatch.product_id == product_id)
                .where(ProductBatch.product_variant_id.is_(None))
                .where(ProductBatch.company_id == company_id)
                .where(ProductBatch.branch_id == branch_id)
            ).first())
            product = session.exec(
                select(Product)
                .where(Product.id == product_id)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
            ).first()
            if product:
                if normalize_fn:
                    product.stock = normalize_fn(total_stock, product)
                else:
                    product.stock = total_stock
                session.add(product)
                updated_products.add(product_id)

    return updated_products
