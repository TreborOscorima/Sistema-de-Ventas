#!/usr/bin/env python3
"""
Backfill: asigna default_supplier_id a productos que no lo tienen,
usando el proveedor de la compra más reciente que incluyó ese producto.

Uso (desde la raíz del proyecto, con el venv activado):
    python scripts/backfill_default_supplier.py
    python scripts/backfill_default_supplier.py --dry-run
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def main(dry_run: bool = False) -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    import rxconfig  # noqa: F401 — construye DB_URL y configura pool

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from app.models.inventory import Product

    engine = create_engine(rxconfig.DB_URL, echo=False)

    with Session(engine) as session:
        # Para cada producto sin default_supplier_id que tiene al menos una compra,
        # obtener el proveedor de la compra más reciente (por issue_date DESC, id DESC).
        # GROUP BY incluye supplier_id para resolver ties entre proveedores distintos;
        # el ORDER BY + lógica Python elige el supplier de la fecha más alta.
        rows = session.execute(
            text("""
                SELECT
                    p.id            AS product_id,
                    pu.supplier_id,
                    MAX(pu.issue_date) AS last_date
                FROM product p
                JOIN purchaseitem pi
                    ON pi.product_id  = p.id
                   AND pi.company_id  = p.company_id
                   AND pi.branch_id   = p.branch_id
                JOIN purchase pu
                    ON pu.id          = pi.purchase_id
                   AND pu.company_id  = pi.company_id
                   AND pu.branch_id   = pi.branch_id
                WHERE p.default_supplier_id IS NULL
                  AND pi.product_id IS NOT NULL
                GROUP BY p.id, pu.supplier_id
                ORDER BY p.id ASC, last_date DESC, pu.supplier_id DESC
            """)
        ).fetchall()

    # Primera aparición de cada product_id = supplier con compra más reciente
    latest: dict[int, tuple[int, str]] = {}
    for row in rows:
        if row.product_id not in latest:
            latest[row.product_id] = (row.supplier_id, str(row.last_date))

    if not latest:
        log.info("No hay productos sin default_supplier_id con compras registradas. Nada que hacer.")
        return

    log.info("Productos a actualizar: %d", len(latest))

    if dry_run:
        log.info("\n[DRY-RUN] Cambios que se aplicarían:")
        for product_id, (supplier_id, last_date) in sorted(latest.items()):
            log.info("  product_id=%-6d → supplier_id=%-4d  (última compra: %s)", product_id, supplier_id, last_date)
        log.info("\nEjecuta sin --dry-run para aplicar los cambios.")
        return

    with Session(engine) as session:
        updated = 0
        for product_id, (supplier_id, _) in latest.items():
            product = session.get(Product, product_id)
            if product is not None and product.default_supplier_id is None:
                product.default_supplier_id = supplier_id
                updated += 1
        session.commit()

    log.info("Completado. Productos actualizados: %d / %d.", updated, len(latest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill default_supplier_id en productos históricos."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra los cambios sin aplicarlos a la base de datos.",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
