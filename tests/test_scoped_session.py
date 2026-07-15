"""Tests del helper scoped_session / async_scoped_session."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Branch, Company, Product
from app.models.company import PlanType, SubscriptionStatus
from app.states.mixin_state import MixinState, ScopedCtx
from app.utils.tenant import (
    _refresh_tenant_models,
    register_tenant_listeners,
    set_tenant_context,
    tenant_bypass,
)


@pytest.fixture(autouse=True)
def _clean_tenant():
    yield
    set_tenant_context(None, None)


def _make_mixin(company_id: int | None, branch_id: int | None) -> MixinState:
    """Crea un MixinState fake con current_user simulado."""
    m = object.__new__(MixinState)
    m.current_user = {"company_id": company_id, "branch_id": branch_id}
    m.selected_branch_id = branch_id
    return m


class TestScopedSessionSync:
    def test_yields_scoped_ctx(self):
        m = _make_mixin(1, 2)
        with m.scoped_session() as ctx:
            assert isinstance(ctx, ScopedCtx)
            assert ctx.company_id == 1
            assert ctx.branch_id == 2
            assert ctx.session is not None

    def test_raises_without_company(self):
        m = _make_mixin(None, 2)
        with pytest.raises(ValueError, match="empresa/sucursal"):
            with m.scoped_session():
                pass

    def test_raises_without_branch(self):
        m = _make_mixin(1, None)
        with pytest.raises(ValueError, match="empresa/sucursal"):
            with m.scoped_session():
                pass

    def test_ctx_is_frozen(self):
        m = _make_mixin(1, 2)
        with m.scoped_session() as ctx:
            with pytest.raises(AttributeError):
                ctx.company_id = 999


class TestAsyncScopedSession:
    @pytest.mark.asyncio
    async def test_yields_async_scoped_ctx(self):
        register_tenant_listeners()
        _refresh_tenant_models()
        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        m = _make_mixin(1, 2)

        with patch("app.utils.db.AsyncSessionLocal") as mock_factory:
            async_session = AsyncSession(engine, expire_on_commit=False)

            class FakeCtxMgr:
                async def __aenter__(self_):
                    return async_session
                async def __aexit__(self_, *args):
                    await async_session.close()

            mock_factory.return_value = FakeCtxMgr()

            async with m.async_scoped_session() as ctx:
                assert isinstance(ctx, ScopedCtx)
                assert ctx.company_id == 1
                assert ctx.branch_id == 2

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_raises_without_tenant(self):
        m = _make_mixin(None, None)
        with pytest.raises(ValueError, match="empresa/sucursal"):
            async with m.async_scoped_session():
                pass


class TestScopedSessionIntegration:
    def test_query_with_scoped_ctx(self):
        """Verifica que se puede hacer query real usando ctx.company_id/branch_id."""
        m = _make_mixin(1, 1)
        with m.scoped_session() as ctx:
            result = ctx.session.exec(
                select(Product).where(
                    Product.company_id == ctx.company_id,
                    Product.branch_id == ctx.branch_id,
                )
            ).all()
            assert isinstance(result, list)
