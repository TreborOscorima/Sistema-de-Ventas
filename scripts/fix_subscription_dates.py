"""Script para corregir subscription_ends_at muy cortas en empresas de plan pago.

Uso:
    python scripts/fix_subscription_dates.py --dry-run    # Previsualiza sin mutar
    python scripts/fix_subscription_dates.py --execute    # Ejecuta el commit
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Carga .env desde la raíz del repo antes de importar módulos que consumen secretos.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

if not os.getenv("AUTH_SECRET_KEY"):
    print(
        "ERROR: AUTH_SECRET_KEY no está configurado. "
        "Este script muta datos de facturación — abortando para no operar con un secreto inválido.",
        file=sys.stderr,
    )
    sys.exit(1)

from app.utils.db import AsyncSessionLocal
from app.utils.tenant import tenant_bypass
from app.models.company import Company, PlanType
from sqlalchemy import select


async def main(dry_run: bool) -> int:
    async with AsyncSessionLocal() as session:
        with tenant_bypass():
            now = datetime.now()
            # Empresas con plan pago cuya suscripción vence en menos de 30 días
            threshold = now + timedelta(days=30)
            stmt = (
                select(Company)
                .where(
                    Company.plan_type != PlanType.TRIAL,
                    Company.subscription_ends_at.isnot(None),  # type: ignore
                    Company.subscription_ends_at < threshold,  # type: ignore
                )
                .execution_options(tenant_bypass=True)
            )
            result = await session.execute(stmt)
            companies = result.scalars().all()

            if not companies:
                print("No hay empresas con subscription_ends_at incorrecta.")
                return 0

            mode = "[DRY RUN]" if dry_run else "[EXECUTE]"
            for c in companies:
                new_date = now + timedelta(days=365)
                print(f"  {mode} {c.name}: {c.subscription_ends_at} -> {new_date}")
                if not dry_run:
                    c.subscription_ends_at = new_date
                    session.add(c)

            if dry_run:
                print(
                    f"\n{len(companies)} empresa(s) serían corregidas. "
                    "Re-ejecuta con --execute para aplicar los cambios."
                )
            else:
                await session.commit()
                print(f"\n{len(companies)} empresa(s) corregidas.")
            return len(companies)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Previsualiza sin mutar.")
    group.add_argument("--execute", action="store_true", help="Aplica los cambios (commit).")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(main(dry_run=args.dry_run))
