"""Tests del servicio de transferencias de stock entre sucursales."""
from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Branch, Company, Product, StockMovement, StockTransfer, StockTransferItem
from app.models.company import PlanType, SubscriptionStatus
from app.models.inventory import TransferStatus
from app.services.transfer_service import TransferError, TransferService
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


@pytest_asyncio.fixture
async def async_engine():
    register_tenant_listeners()
    _refresh_tenant_models()
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(async_engine):
    async with AsyncSession(async_engine, expire_on_commit=False) as s:
        yield s


@pytest_asyncio.fixture
async def company_with_branches(session):
    """Crea 1 empresa con 2 sucursales y 2 productos en la sucursal origen."""
    with tenant_bypass():
        co = Company(
            name="Test Corp", ruc="99999999999",
            plan_type=PlanType.PROFESSIONAL,
            subscription_status=SubscriptionStatus.ACTIVE,
            max_branches=5,
        )
        session.add(co)
        await session.flush()

        br_origin = Branch(name="Central", company_id=co.id)
        br_dest = Branch(name="Norte", company_id=co.id)
        session.add(br_origin)
        session.add(br_dest)
        await session.flush()

        p1 = Product(
            company_id=co.id, branch_id=br_origin.id,
            barcode="PROD-001", description="Producto Uno",
            stock=Decimal("100.0000"), unit="Unidad",
            purchase_price=Decimal("10.00"), sale_price=Decimal("15.00"),
        )
        p2 = Product(
            company_id=co.id, branch_id=br_origin.id,
            barcode="PROD-002", description="Producto Dos",
            stock=Decimal("50.0000"), unit="Kg",
            purchase_price=Decimal("5.00"), sale_price=Decimal("8.00"),
        )
        session.add_all([p1, p2])
        await session.flush()

        ids = {
            "company_id": co.id,
            "origin_id": br_origin.id,
            "dest_id": br_dest.id,
            "p1_id": p1.id,
            "p2_id": p2.id,
        }
        await session.commit()
    return ids


class TestCreateTransfer:
    @pytest.mark.asyncio
    async def test_create_basic(self, session, company_with_branches):
        ids = company_with_branches
        with tenant_bypass():
            transfer = await TransferService.create_transfer(
                session,
                company_id=ids["company_id"],
                origin_branch_id=ids["origin_id"],
                destination_branch_id=ids["dest_id"],
                items=[{"product_id": ids["p1_id"], "quantity": 10}],
            )
            await session.commit()

        assert transfer.id is not None
        assert transfer.status == TransferStatus.PENDING
        assert transfer.company_id == ids["company_id"]

    @pytest.mark.asyncio
    async def test_same_branch_rejected(self, session, company_with_branches):
        ids = company_with_branches
        with tenant_bypass():
            with pytest.raises(TransferError, match="misma"):
                await TransferService.create_transfer(
                    session,
                    company_id=ids["company_id"],
                    origin_branch_id=ids["origin_id"],
                    destination_branch_id=ids["origin_id"],
                    items=[{"product_id": ids["p1_id"], "quantity": 5}],
                )

    @pytest.mark.asyncio
    async def test_empty_items_rejected(self, session, company_with_branches):
        ids = company_with_branches
        with tenant_bypass():
            with pytest.raises(TransferError, match="al menos un producto"):
                await TransferService.create_transfer(
                    session,
                    company_id=ids["company_id"],
                    origin_branch_id=ids["origin_id"],
                    destination_branch_id=ids["dest_id"],
                    items=[],
                )

    @pytest.mark.asyncio
    async def test_insufficient_stock_rejected(self, session, company_with_branches):
        ids = company_with_branches
        with tenant_bypass():
            with pytest.raises(TransferError, match="Stock insuficiente"):
                await TransferService.create_transfer(
                    session,
                    company_id=ids["company_id"],
                    origin_branch_id=ids["origin_id"],
                    destination_branch_id=ids["dest_id"],
                    items=[{"product_id": ids["p1_id"], "quantity": 999}],
                )


class TestExecuteTransfer:
    @pytest.mark.asyncio
    async def test_execute_decrements_origin(self, session, company_with_branches):
        ids = company_with_branches
        with tenant_bypass():
            transfer = await TransferService.create_transfer(
                session,
                company_id=ids["company_id"],
                origin_branch_id=ids["origin_id"],
                destination_branch_id=ids["dest_id"],
                items=[{"product_id": ids["p1_id"], "quantity": 25}],
            )
            await session.flush()

            result = await TransferService.execute_transfer(
                session,
                transfer_id=transfer.id,
                company_id=ids["company_id"],
            )
            await session.commit()

        assert result.status == TransferStatus.COMPLETED
        assert result.completed_at is not None

        with tenant_bypass():
            from sqlmodel import select
            origin_prod = (await session.exec(
                select(Product).where(
                    Product.id == ids["p1_id"],
                    Product.branch_id == ids["origin_id"],
                )
            )).first()
            assert origin_prod.stock == Decimal("75.0000")

    @pytest.mark.asyncio
    async def test_execute_creates_dest_product(self, session, company_with_branches):
        ids = company_with_branches
        with tenant_bypass():
            transfer = await TransferService.create_transfer(
                session,
                company_id=ids["company_id"],
                origin_branch_id=ids["origin_id"],
                destination_branch_id=ids["dest_id"],
                items=[{"product_id": ids["p1_id"], "quantity": 10}],
            )
            await session.flush()

            await TransferService.execute_transfer(
                session,
                transfer_id=transfer.id,
                company_id=ids["company_id"],
            )
            await session.commit()

        with tenant_bypass():
            from sqlmodel import select
            dest_prod = (await session.exec(
                select(Product).where(
                    Product.company_id == ids["company_id"],
                    Product.branch_id == ids["dest_id"],
                    Product.barcode == "PROD-001",
                )
            )).first()
            assert dest_prod is not None
            assert dest_prod.stock == Decimal("10")
            assert dest_prod.description == "Producto Uno"

    @pytest.mark.asyncio
    async def test_execute_generates_movements(self, session, company_with_branches):
        ids = company_with_branches
        with tenant_bypass():
            transfer = await TransferService.create_transfer(
                session,
                company_id=ids["company_id"],
                origin_branch_id=ids["origin_id"],
                destination_branch_id=ids["dest_id"],
                items=[{"product_id": ids["p1_id"], "quantity": 5}],
            )
            await session.flush()

            await TransferService.execute_transfer(
                session,
                transfer_id=transfer.id,
                company_id=ids["company_id"],
            )
            await session.commit()

        with tenant_bypass():
            from sqlmodel import select
            movs = (await session.exec(
                select(StockMovement).where(
                    StockMovement.company_id == ids["company_id"],
                )
            )).all()
            types = {m.type for m in movs}
            assert "Transferencia Salida" in types
            assert "Transferencia Ingreso" in types
            assert len(movs) == 2

    @pytest.mark.asyncio
    async def test_double_execute_rejected(self, session, company_with_branches):
        ids = company_with_branches
        with tenant_bypass():
            transfer = await TransferService.create_transfer(
                session,
                company_id=ids["company_id"],
                origin_branch_id=ids["origin_id"],
                destination_branch_id=ids["dest_id"],
                items=[{"product_id": ids["p1_id"], "quantity": 5}],
            )
            await session.flush()

            await TransferService.execute_transfer(
                session,
                transfer_id=transfer.id,
                company_id=ids["company_id"],
            )
            await session.flush()

            with pytest.raises(TransferError, match="ya está en estado"):
                await TransferService.execute_transfer(
                    session,
                    transfer_id=transfer.id,
                    company_id=ids["company_id"],
                )

    @pytest.mark.asyncio
    async def test_multi_item_transfer(self, session, company_with_branches):
        ids = company_with_branches
        with tenant_bypass():
            transfer = await TransferService.create_transfer(
                session,
                company_id=ids["company_id"],
                origin_branch_id=ids["origin_id"],
                destination_branch_id=ids["dest_id"],
                items=[
                    {"product_id": ids["p1_id"], "quantity": 20},
                    {"product_id": ids["p2_id"], "quantity": 15},
                ],
            )
            await session.flush()

            await TransferService.execute_transfer(
                session,
                transfer_id=transfer.id,
                company_id=ids["company_id"],
            )
            await session.commit()

        with tenant_bypass():
            from sqlmodel import select
            p1 = (await session.exec(
                select(Product).where(Product.id == ids["p1_id"])
            )).first()
            assert p1.stock == Decimal("80.0000")

            p2 = (await session.exec(
                select(Product).where(Product.id == ids["p2_id"])
            )).first()
            assert p2.stock == Decimal("35.0000")


class TestCancelTransfer:
    @pytest.mark.asyncio
    async def test_cancel_pending(self, session, company_with_branches):
        ids = company_with_branches
        with tenant_bypass():
            transfer = await TransferService.create_transfer(
                session,
                company_id=ids["company_id"],
                origin_branch_id=ids["origin_id"],
                destination_branch_id=ids["dest_id"],
                items=[{"product_id": ids["p1_id"], "quantity": 5}],
            )
            await session.flush()

            result = await TransferService.cancel_transfer(
                session,
                transfer_id=transfer.id,
                company_id=ids["company_id"],
            )

        assert result.status == TransferStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_completed_rejected(self, session, company_with_branches):
        ids = company_with_branches
        with tenant_bypass():
            transfer = await TransferService.create_transfer(
                session,
                company_id=ids["company_id"],
                origin_branch_id=ids["origin_id"],
                destination_branch_id=ids["dest_id"],
                items=[{"product_id": ids["p1_id"], "quantity": 5}],
            )
            await session.flush()

            await TransferService.execute_transfer(
                session,
                transfer_id=transfer.id,
                company_id=ids["company_id"],
            )
            await session.flush()

            with pytest.raises(TransferError, match="pendientes"):
                await TransferService.cancel_transfer(
                    session,
                    transfer_id=transfer.id,
                    company_id=ids["company_id"],
                )
