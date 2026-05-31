#!/usr/bin/env python3
"""
fix_orphan_cashbox_logs.py — Limpieza de registros huérfanos de caja.

Problema que corrige:
    Cada restart/deploy del servidor llamaba logout() que cerraba CashboxSession
    en la DB sin escribir un CashboxLog "cierre". Resultado: historial de
    "Aperturas y Cierres" con múltiples aperturas sin su cierre par.

Qué hace:
    Por cada CashboxSession cerrada (is_open=False, closing_time NOT NULL)
    que no tenga un CashboxLog "cierre" correspondiente, inserta uno con:
      - action = "cierre"
      - amount = 0
      - notes = "Cierre retroactivo — sesión cerrada por restart de servidor"
      - timestamp = closing_time de la sesión

Es IDEMPOTENTE: puede ejecutarse múltiples veces sin duplicar registros.

Uso:
    python scripts/fix_orphan_cashbox_logs.py [--dry-run]

    --dry-run   Solo muestra qué corregiría, no escribe nada en la DB.
"""
import sys
import os
import argparse
from datetime import datetime, timezone

# ── Bootstrap del path para importar la app ─────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

from sqlmodel import Session, select, create_engine
from sqlalchemy import text

# rxconfig inicializa la DB_URL leyendo las env vars
import rxconfig  # noqa: F401 — side-effect: setea SQLALCHEMY_POOL_SIZE etc.
from rxconfig import DB_URL

from app.models.sales import CashboxSession, CashboxLog


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def main(dry_run: bool = False) -> None:
    mode = "DRY-RUN (sin cambios)" if dry_run else "REAL"
    print(f"\n{'='*60}")
    print(f"  fix_orphan_cashbox_logs.py  [{mode}]")
    print(f"{'='*60}")

    engine = create_engine(DB_URL, echo=False)

    with Session(engine) as session:
        # ── 1. Encontrar sesiones cerradas sin CashboxLog "cierre" ──────────
        closed_sessions = session.exec(
            select(CashboxSession).where(
                CashboxSession.is_open == False,
                CashboxSession.closing_time != None,
            )
        ).all()

        print(f"\nSesiones cerradas en DB:          {len(closed_sessions)}")

        to_fix = []
        for cs in closed_sessions:
            # Buscar si ya existe un CashboxLog "cierre" dentro de una ventana
            # de ±10 segundos alrededor del closing_time de la sesión
            window_start = cs.opening_time  # desde la apertura
            window_end_ts = cs.closing_time

            existing_cierre = session.exec(
                select(CashboxLog).where(
                    CashboxLog.action == "cierre",
                    CashboxLog.user_id == cs.user_id,
                    CashboxLog.company_id == cs.company_id,
                    CashboxLog.branch_id == cs.branch_id,
                    CashboxLog.timestamp >= window_start,
                    CashboxLog.timestamp <= window_end_ts,
                )
            ).first()

            if not existing_cierre:
                to_fix.append(cs)

        print(f"Sin CashboxLog 'cierre' (huérfanas): {len(to_fix)}")

        if not to_fix:
            print("\n✅ No hay registros huérfanos. La DB está limpia.")
            return

        print(f"\nRegistros a corregir:")
        print(f"  {'ID':>6}  {'company':>8}  {'branch':>6}  {'user':>6}  {'opening_time':<20}  {'closing_time':<20}")
        print(f"  {'-'*6}  {'-'*8}  {'-'*6}  {'-'*6}  {'-'*20}  {'-'*20}")
        for cs in to_fix:
            ot = str(cs.opening_time)[:19] if cs.opening_time else "?"
            ct = str(cs.closing_time)[:19] if cs.closing_time else "?"
            print(f"  {cs.id:>6}  {cs.company_id:>8}  {cs.branch_id:>6}  {cs.user_id:>6}  {ot:<20}  {ct:<20}")

        if dry_run:
            print(f"\n⚠️  DRY-RUN: no se escribió nada. Correr sin --dry-run para aplicar.")
            return

        # ── 2. Insertar CashboxLog "cierre" para cada sesión huérfana ───────
        inserted = 0
        for cs in to_fix:
            cierre_log = CashboxLog(
                company_id=cs.company_id,
                branch_id=cs.branch_id,
                user_id=cs.user_id,
                action="cierre",
                amount=0,
                notes="Cierre retroactivo — sesión cerrada por restart de servidor",
                timestamp=cs.closing_time or utc_now_naive(),
                is_voided=False,
            )
            session.add(cierre_log)
            inserted += 1

        session.commit()
        print(f"\n✅ Insertados {inserted} registros CashboxLog 'cierre'.")
        print("   El historial de Aperturas y Cierres ahora está completo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Limpia aperturas huérfanas de caja")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra qué corregiría, sin escribir en la DB",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
