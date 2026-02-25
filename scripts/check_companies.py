"""Script rápido para verificar estado de empresas en BD."""
import asyncio
import os
os.environ.setdefault("AUTH_SECRET_KEY", "k" * 32)

from app.utils.db import AsyncSessionLocal
from app.utils.tenant import tenant_bypass
from app.services.owner_service import OwnerService


async def main():
    async with AsyncSessionLocal() as session:
        with tenant_bypass():
            items, total = await OwnerService.list_companies(session, page=1, per_page=20)
            print(f"Total empresas: {total}")
            for c in items:
                name = c.get("name")
                plan = c.get("plan_type")
                status = c.get("subscription_status")
                eff = c.get("effective_status")
                sub_ends = c.get("subscription_ends_at")
                trial_ends = c.get("trial_ends_at")
                res = c.get("has_reservations_module")
                bill = c.get("has_electronic_billing")
                print(
                    f"  [{c.get('id')}] {name}\n"
                    f"      plan={plan} | status={status} | effective={eff}\n"
                    f"      sub_ends={sub_ends} | trial_ends={trial_ends}\n"
                    f"      reservas={res} | billing={bill}"
                )


if __name__ == "__main__":
    asyncio.run(main())
