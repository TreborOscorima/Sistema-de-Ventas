"""Tests de métricas de plataforma del Owner (MRR, churn y conversión por ventana)."""
from __future__ import annotations

from datetime import timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Company
from app.models.company import PlanType, ProductType, SubscriptionStatus
from app.models.owner import OwnerAuditLog
from app.services.owner_service import OwnerService
from app.utils.timezone import utc_now_naive


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(async_engine):
    async with AsyncSession(async_engine, expire_on_commit=False) as s:
        yield s


def _company(name, ruc, plan, status=SubscriptionStatus.ACTIVE):
    return Company(
        name=name, ruc=ruc, plan_type=plan, subscription_status=status,
        product_type=ProductType.VENTAS, max_users=5, max_branches=2,
    )


def _audit(company_id, action, before_plan, after_plan, days_ago):
    import json
    return OwnerAuditLog(
        actor_email="owner@test.com",
        target_company_id=company_id,
        target_company_name="X",
        target_product_type="ventas",
        action=action,
        before_snapshot=json.dumps({"plan_type": before_plan}),
        after_snapshot=json.dumps({"plan_type": after_plan}),
        reason="test",
        created_at=utc_now_naive() - timedelta(days=days_ago),
    )


@pytest_asyncio.fixture
async def seeded(session):
    """3 pagantes activos (2 Standard + 1 Professional) y 2 trials activos."""
    companies = [
        _company("Std A", "20000000001", PlanType.STANDARD),
        _company("Std B", "20000000002", PlanType.STANDARD),
        _company("Pro C", "20000000003", PlanType.PROFESSIONAL),
        _company("Trial D", "20000000004", PlanType.TRIAL),
        _company("Trial E", "20000000005", PlanType.TRIAL),
    ]
    session.add_all(companies)
    await session.flush()

    session.add_all([
        # Conversión real trial→pago dentro de la ventana.
        _audit(companies[3].id, "change_plan", "trial", "standard", days_ago=5),
        # Trial vencido sin convertir dentro de la ventana.
        _audit(companies[4].id, "sync_expired_trial", "trial", "trial", days_ago=10),
        # Cliente de pago dado de baja dentro de la ventana (churn real).
        _audit(companies[2].id, "suspend", "professional", "professional", days_ago=3),
        # Baja de un pagante FUERA de la ventana (60 días) → no debe contar.
        _audit(companies[0].id, "suspend", "standard", "standard", days_ago=60),
    ])
    await session.commit()
    return companies


class TestPlatformMetrics:
    @pytest.mark.asyncio
    async def test_mrr_and_paying(self, session, seeded):
        m = await OwnerService.get_platform_metrics(session)
        # 2 Standard ($35) + 1 Professional ($55) = 125
        assert m["mrr"] == 125.0
        assert m["arr"] == 1500.0
        assert m["total_paying"] == 3

    @pytest.mark.asyncio
    async def test_churn_windowed(self, session, seeded):
        m = await OwnerService.get_platform_metrics(session)
        # 1 pagante churneado en ventana / (3 pagantes actuales + 1) = 25%
        # La baja de hace 60 días queda EXCLUIDA.
        assert m["churned_paying_window"] == 1
        assert m["churn_window_days"] == 30
        assert m["churn_rate"] == 25.0

    @pytest.mark.asyncio
    async def test_trial_conversion_windowed(self, session, seeded):
        m = await OwnerService.get_platform_metrics(session)
        # 1 convertido / (1 convertido + 1 vencido) = 50%
        assert m["trial_converted_window"] == 1
        assert m["trial_decided_window"] == 2
        assert m["trial_conversion"] == 50.0

    @pytest.mark.asyncio
    async def test_no_events_yields_zero(self, session):
        # Sin auditoría: churn y conversión = 0 (no hubo eventos en la ventana).
        session.add(_company("Solo", "20000000009", PlanType.STANDARD))
        await session.commit()
        m = await OwnerService.get_platform_metrics(session)
        assert m["churn_rate"] == 0.0
        assert m["trial_conversion"] == 0.0
        assert m["mrr"] == 35.0
