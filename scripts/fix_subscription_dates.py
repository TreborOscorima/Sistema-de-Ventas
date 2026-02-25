"""Script para corregir subscription_ends_at muy cortas en empresas de plan pago."""
import asyncio
import os
from datetime import datetime, timedelta

os.environ.setdefault("AUTH_SECRET_KEY", "k" * 32)

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
