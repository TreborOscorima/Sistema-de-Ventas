"""Script para corregir subscription_ends_at muy cortas en empresas de plan pago."""
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


async def main():
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
                return

            for c in companies:
                new_date = now + timedelta(days=365)
                print(f"  Corrigiendo {c.name}: {c.subscription_ends_at} -> {new_date}")
                c.subscription_ends_at = new_date
                session.add(c)

            await session.commit()
            print(f"\n{len(companies)} empresa(s) corregidas.")


if __name__ == "__main__":
    asyncio.run(main())
