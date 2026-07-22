"""Tests del servicio de transferencias de stock entre sucursales."""
from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from datetime import datetime

from sqlmodel import select

from app.models import (
    Branch,
    Company,
    Product,
    ProductBatch,
    ProductVariant,
    StockMovement,
    StockTransfer,
    StockTransferItem,
)
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
            by_type = {m.type: m for m in movs}
            # El kardex nombra la sucursal real (origen "Central", destino "Norte").
            assert "Norte" in by_type["Transferencia Salida"].description
            assert "Central" in by_type["Transferencia Ingreso"].description

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


@pytest_asyncio.fixture
async def company_with_structures(session):
    """Empresa con 2 sucursales, un producto con LOTES y otro con VARIANTES."""
    with tenant_bypass():
        co = Company(
            name="Struct Corp", ruc="88888888888",
            plan_type=PlanType.PROFESSIONAL,
            subscription_status=SubscriptionStatus.ACTIVE,
            max_branches=5,
        )
        session.add(co)
        await session.flush()

        br_o = Branch(name="Central", company_id=co.id)
        br_d = Branch(name="Norte", company_id=co.id)
        session.add_all([br_o, br_d])
        await session.flush()

        # Producto con lotes (product.stock = suma de lotes = 30).
        pb = Product(
            company_id=co.id, branch_id=br_o.id,
            barcode="PROD-BATCH", description="Producto Lote",
            stock=Decimal("30.0000"), unit="Unidad",
            purchase_price=Decimal("2.00"), sale_price=Decimal("4.00"),
        )
        # Producto con variantes (product.stock = suma de variantes = 35).
        pv = Product(
            company_id=co.id, branch_id=br_o.id,
            barcode="PROD-VAR", description="Producto Variante",
            stock=Decimal("35.0000"), unit="Unidad",
            purchase_price=Decimal("3.00"), sale_price=Decimal("6.00"),
        )
        session.add_all([pb, pv])
        await session.flush()

        lote_a = ProductBatch(
            company_id=co.id, branch_id=br_o.id, product_id=pb.id,
            batch_number="LOTE-A", expiration_date=datetime(2026, 1, 1),
            stock=Decimal("10.0000"),
        )
        lote_b = ProductBatch(
            company_id=co.id, branch_id=br_o.id, product_id=pb.id,
            batch_number="LOTE-B", expiration_date=datetime(2027, 1, 1),
            stock=Decimal("20.0000"),
        )
        v1 = ProductVariant(
            company_id=co.id, branch_id=br_o.id, product_id=pv.id,
            sku="SKU-V1", size="M", color="Rojo", stock=Decimal("20.0000"),
        )
        v2 = ProductVariant(
            company_id=co.id, branch_id=br_o.id, product_id=pv.id,
            sku="SKU-V2", size="L", color="Azul", stock=Decimal("15.0000"),
        )
        session.add_all([lote_a, lote_b, v1, v2])
        await session.flush()

        ids = {
            "company_id": co.id, "origin_id": br_o.id, "dest_id": br_d.id,
            "pb_id": pb.id, "pv_id": pv.id, "v1_id": v1.id, "v2_id": v2.id,
        }
        await session.commit()
    return ids


async def _exec(session, ids, items):
    with tenant_bypass():
        transfer = await TransferService.create_transfer(
            session,
            company_id=ids["company_id"],
            origin_branch_id=ids["origin_id"],
            destination_branch_id=ids["dest_id"],
            items=items,
        )
        await session.flush()
        await TransferService.execute_transfer(
            session, transfer_id=transfer.id, company_id=ids["company_id"],
        )
        await session.commit()
    return transfer


class TestTransferBatches:
    @pytest.mark.asyncio
    async def test_fefo_deduction_and_dest_batch_creation(self, session, company_with_structures):
        ids = company_with_structures
        # Transferir 15: FEFO toma 10 de LOTE-A (vence antes) + 5 de LOTE-B.
        await _exec(session, ids, [{"product_id": ids["pb_id"], "quantity": 15}])

        with tenant_bypass():
            o_batches = (await session.exec(
                select(ProductBatch).where(
                    ProductBatch.branch_id == ids["origin_id"],
                    ProductBatch.product_id == ids["pb_id"],
                )
            )).all()
            by_num = {b.batch_number: b for b in o_batches}
            assert by_num["LOTE-A"].stock == Decimal("0.0000")
            assert by_num["LOTE-B"].stock == Decimal("15.0000")

            o_prod = (await session.exec(
                select(Product).where(Product.id == ids["pb_id"])
            )).first()
            assert o_prod.stock == Decimal("15.0000")  # sigue = suma de lotes

            # Destino: producto nuevo + lotes con MISMO número y vencimiento.
            d_prod = (await session.exec(
                select(Product).where(
                    Product.branch_id == ids["dest_id"],
                    Product.barcode == "PROD-BATCH",
                )
            )).first()
            assert d_prod is not None
            d_batches = (await session.exec(
                select(ProductBatch).where(
                    ProductBatch.branch_id == ids["dest_id"],
                    ProductBatch.product_id == d_prod.id,
                )
            )).all()
            d_by_num = {b.batch_number: b for b in d_batches}
            assert d_by_num["LOTE-A"].stock == Decimal("10.0000")
            assert d_by_num["LOTE-A"].expiration_date == datetime(2026, 1, 1)
            assert d_by_num["LOTE-B"].stock == Decimal("5.0000")
            assert d_prod.stock == Decimal("15.0000")

    @pytest.mark.asyncio
    async def test_batch_invariant_preserved(self, session, company_with_structures):
        """product.stock siempre == suma de lotes en ambas sucursales."""
        ids = company_with_structures
        await _exec(session, ids, [{"product_id": ids["pb_id"], "quantity": 12}])
        with tenant_bypass():
            for branch in (ids["origin_id"], ids["dest_id"]):
                prod = (await session.exec(
                    select(Product).where(
                        Product.branch_id == branch, Product.barcode == "PROD-BATCH",
                    )
                )).first()
                if not prod:
                    continue
                total = (await session.exec(
                    select(ProductBatch).where(
                        ProductBatch.branch_id == branch,
                        ProductBatch.product_id == prod.id,
                    )
                )).all()
                assert prod.stock == sum((b.stock for b in total), Decimal("0"))


class TestTransferVariants:
    @pytest.mark.asyncio
    async def test_variant_transfer_moves_specific_variant(self, session, company_with_structures):
        ids = company_with_structures
        # Transferir 8 de la variante V1 (talla M).
        await _exec(session, ids, [
            {"product_id": ids["pv_id"], "quantity": 8, "variant_id": ids["v1_id"]},
        ])

        with tenant_bypass():
            v1 = (await session.exec(
                select(ProductVariant).where(ProductVariant.id == ids["v1_id"])
            )).first()
            v2 = (await session.exec(
                select(ProductVariant).where(ProductVariant.id == ids["v2_id"])
            )).first()
            assert v1.stock == Decimal("12.0000")   # 20 - 8
            assert v2.stock == Decimal("15.0000")   # intacta

            o_prod = (await session.exec(
                select(Product).where(Product.id == ids["pv_id"])
            )).first()
            assert o_prod.stock == Decimal("27.0000")  # 12 + 15 (agregado)

            # Destino: producto + variante SKU-V1 clonada con stock 8.
            d_prod = (await session.exec(
                select(Product).where(
                    Product.branch_id == ids["dest_id"], Product.barcode == "PROD-VAR",
                )
            )).first()
            assert d_prod is not None
            d_var = (await session.exec(
                select(ProductVariant).where(
                    ProductVariant.branch_id == ids["dest_id"],
                    ProductVariant.sku == "SKU-V1",
                )
            )).first()
            assert d_var is not None
            assert d_var.size == "M" and d_var.color == "Rojo"
            assert d_var.stock == Decimal("8.0000")
            assert d_prod.stock == Decimal("8.0000")   # agregado = suma variantes destino

    @pytest.mark.asyncio
    async def test_variant_insufficient_stock_rejected(self, session, company_with_structures):
        ids = company_with_structures
        with tenant_bypass():
            with pytest.raises(TransferError, match="Stock insuficiente"):
                await TransferService.create_transfer(
                    session,
                    company_id=ids["company_id"],
                    origin_branch_id=ids["origin_id"],
                    destination_branch_id=ids["dest_id"],
                    items=[{"product_id": ids["pv_id"], "quantity": 999, "variant_id": ids["v1_id"]}],
                )

    @pytest.mark.asyncio
    async def test_variant_second_transfer_consolidates(self, session, company_with_structures):
        """Dos transferencias de la misma variante consolidan en destino (no duplican)."""
        ids = company_with_structures
        await _exec(session, ids, [
            {"product_id": ids["pv_id"], "quantity": 5, "variant_id": ids["v1_id"]},
        ])
        await _exec(session, ids, [
            {"product_id": ids["pv_id"], "quantity": 3, "variant_id": ids["v1_id"]},
        ])
        with tenant_bypass():
            d_vars = (await session.exec(
                select(ProductVariant).where(
                    ProductVariant.branch_id == ids["dest_id"],
                    ProductVariant.sku == "SKU-V1",
                )
            )).all()
            assert len(d_vars) == 1                    # una sola variante
            assert d_vars[0].stock == Decimal("8.0000")  # 5 + 3


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
