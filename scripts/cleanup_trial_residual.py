"""Script para limpiar trial_ends_at residual en empresas que ya no son trial.

Uso:
    python scripts/cleanup_trial_residual.py --dry-run    # Previsualiza sin mutar
    python scripts/cleanup_trial_residual.py --execute    # Ejecuta el commit
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Carga .env desde la raíz del repo antes de importar módulos que consumen secretos.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

if not os.getenv("AUTH_SECRET_KEY"):
    print(
        "ERROR: AUTH_SECRET_KEY no está configurado. "
        "Este script muta estado de empresas — abortando para no operar con un secreto inválido.",
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
            stmt = select(Company).where(
                Company.plan_type != PlanType.TRIAL,
                Company.trial_ends_at.isnot(None),  # type: ignore
            ).execution_options(tenant_bypass=True)
            result = await session.execute(stmt)
            companies = result.scalars().all()

            if not companies:
                print("No hay empresas con trial_ends_at residual.")
                return 0

            mode = "[DRY RUN]" if dry_run else "[EXECUTE]"
            for c in companies:
                print(
                    f"  {mode} {c.name} (plan={c.plan_type}): "
                    f"trial_ends_at={c.trial_ends_at} -> None"
                )
                if not dry_run:
                    c.trial_ends_at = None
                    session.add(c)

            if dry_run:
                print(
                    f"\n{len(companies)} empresa(s) serían limpiadas. "
                    "Re-ejecuta con --execute para aplicar los cambios."
                )
            else:
                await session.commit()
                print(f"\n{len(companies)} empresa(s) limpiadas.")
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
