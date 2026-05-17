#!/usr/bin/env python3
"""
Backfill: asigna payment_method_id a registros históricos de SalePayment
que corresponden a reservas pagadas con un método 'other' (ej: Mercado Pago)
pero quedaron con payment_method_id=NULL porque el bug fue corregido después.

Estrategia:
  SalePayment (method_type='other', payment_method_id=NULL)
      → JOIN CashboxLog via sale_id  (almacena payment_method como string)
      → JOIN PaymentMethod via LOWER(name) = LOWER(cl.payment_method) y kind='other'
      → UPDATE SalePayment.payment_method_id

Todos los flujos de reserva (services_state.py y _close_mixin.py) crean un
CashboxLog con sale_id y payment_method string en la misma transacción, por lo
que la cadena de JOIN es siempre válida para registros de reservas.

Uso (desde la raíz del proyecto, con el venv activado):
    python scripts/backfill_reservation_payment_method_ids.py --dry-run
    python scripts/backfill_reservation_payment_method_ids.py
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
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

    engine = create_engine(rxconfig.DB_URL, echo=False)

    # ── 1. Detectar candidatos via JOIN CashboxLog → PaymentMethod ──────────
    with Session(engine) as session:
        rows = session.execute(
            text("""
                SELECT
                    sp.id                       AS sp_id,
                    sp.company_id,
                    sp.branch_id,
                    TRIM(cl.payment_method)     AS cl_method,
                    pm.id                       AS pm_id,
                    pm.name                     AS pm_name
                FROM salepayment sp
                JOIN cashboxlog cl
                    ON  cl.sale_id    = sp.sale_id
                    AND cl.company_id = sp.company_id
                    AND cl.branch_id  = sp.branch_id
                    AND cl.payment_method IS NOT NULL
                    AND TRIM(cl.payment_method) != ''
                JOIN paymentmethod pm
                    ON  pm.company_id           = sp.company_id
                    AND pm.branch_id            = sp.branch_id
                    AND LOWER(TRIM(pm.name))    = LOWER(TRIM(cl.payment_method))
                    AND pm.kind                 = 'other'
                WHERE sp.method_type       = 'other'
                  AND sp.payment_method_id IS NULL
            """)
        ).fetchall()

    # ── 2. Construir mapeo sp_id → (pm_id, pm_name); warn si ambiguo ────────
    mapping: dict[int, tuple[int, str]] = {}
    conflicts: set[int] = set()

    for row in rows:
        sp_id = row.sp_id
        if sp_id in conflicts:
            continue
        if sp_id in mapping:
            existing_pm_id, existing_pm_name = mapping[sp_id]
            if existing_pm_id != row.pm_id:
                log.warning(
                    "salepayment.id=%d: coincidencias múltiples (%r vs %r) — se omite.",
                    sp_id, existing_pm_name, row.pm_name,
                )
                conflicts.add(sp_id)
                del mapping[sp_id]
        else:
            mapping[sp_id] = (row.pm_id, row.pm_name)

    # ── 3. Resumen ───────────────────────────────────────────────────────────
    if not mapping:
        log.info("No hay registros históricos que corregir.")
        if conflicts:
            log.info("Omitidos por ambigüedad: %d (revisar manualmente).", len(conflicts))
        return

    by_method: dict[str, list[int]] = defaultdict(list)
    for sp_id, (_, pm_name) in mapping.items():
        by_method[pm_name].append(sp_id)

    log.info("SalePayment a actualizar: %d", len(mapping))
    for pm_name, ids in sorted(by_method.items()):
        log.info("  %4d registro(s) → %s", len(ids), pm_name)
    if conflicts:
        log.info("Omitidos por ambigüedad: %d (revisar manualmente).", len(conflicts))

    if dry_run:
        log.info("\n[DRY-RUN] Detalle de cambios que se aplicarían:")
        for sp_id, (pm_id, pm_name) in sorted(mapping.items()):
            log.info(
                "  salepayment.id=%-6d → payment_method_id=%-4d (%s)",
                sp_id, pm_id, pm_name,
            )
        log.info("\nEjecuta sin --dry-run para aplicar los cambios.")
        return

    # ── 4. Aplicar backfill ──────────────────────────────────────────────────
    with Session(engine) as session:
        updated = 0
        for sp_id, (pm_id, _) in mapping.items():
            result = session.execute(
                text(
                    "UPDATE salepayment "
                    "SET payment_method_id = :pm_id "
                    "WHERE id = :sp_id AND payment_method_id IS NULL"
                ),
                {"pm_id": pm_id, "sp_id": sp_id},
            )
            updated += result.rowcount
        session.commit()

    log.info("Completado. SalePayment actualizados: %d / %d.", updated, len(mapping))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill payment_method_id en SalePayment históricos de reservas."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra los cambios sin aplicarlos a la base de datos.",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
