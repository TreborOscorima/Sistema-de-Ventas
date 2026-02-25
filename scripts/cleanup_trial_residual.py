"""Script para limpiar trial_ends_at residual en empresas que ya no son trial."""
import asyncio
import os
os.environ.setdefault("AUTH_SECRET_KEY", "k" * 32)

from app.utils.db import AsyncSessionLocal
from app.utils.tenant import tenant_bypass
from app.models.company import Company, PlanType
from sqlalchemy import select


async def main():
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
                return

            for c in companies:
                print(f"  Limpiando {c.name} (plan={c.plan_type}): trial_ends_at={c.trial_ends_at} -> None")
                c.trial_ends_at = None
                session.add(c)

            await session.commit()
            print(f"\n{len(companies)} empresa(s) limpiadas.")


if __name__ == "__main__":
    asyncio.run(main())
