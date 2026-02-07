"""
Stress tests de concurrencia para Ventas y Reservas.

Requisitos:
  - Usar una BD de pruebas (nombre con 'test' o 'stress'), o pasar --unsafe.
  - Definir STRESS_DB_URL (Async SQLAlchemy URL).

Ejemplo:
  STRESS_DB_URL="mysql+aiomysql://user:pass@localhost:3306/sistema_test" \
  python scripts/stress_concurrency.py --concurrency 20 --attempts 50
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

import app.models  # noqa: F401
from app.enums import ReservationStatus, PaymentMethodType
from app.models import (
    Company,
    Branch,
    Product,
    ProductBatch,
    FieldReservation,
    PaymentMethod,
)
from app.schemas.sale_schemas import SaleItemDTO, PaymentInfoDTO
from app.services.sale_service import SaleService, StockError
from app.utils.tenant import set_tenant_context


def _require_db_url(args: argparse.Namespace) -> str:
    db_url = args.db_url or os.getenv("STRESS_DB_URL", "").strip()
    if not db_url:
        print("ERROR: Defina STRESS_DB_URL o use --db-url.")
        sys.exit(2)
    return db_url


def _safe_db_check(db_url: str, unsafe: bool) -> None:
    try:
        url = make_url(db_url)
        db_name = (url.database or "").lower()
    except Exception:
        db_name = ""
    if unsafe:
        return
    if not any(token in db_name for token in ("test", "stress")):
        print(
            "ERROR: La BD no parece de prueba. "
            "Use --unsafe solo si realmente es seguro."
        )
        sys.exit(2)


async def _create_schema(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def _create_tenant(session) -> tuple[int, int]:
    now = datetime.now()
    stamp = uuid.uuid4().hex[:8]
    company = Company(
        name=f"STRESS-{stamp}",
        ruc=f"STRESS{stamp}X",
        created_at=now,
        plan_type="trial",
    )
    session.add(company)
    await session.flush()
    branch = Branch(company_id=company.id, name="Stress Branch", address="")
    session.add(branch)
    await session.flush()
    await session.commit()
    return company.id, branch.id


async def _create_product(
    session,
    company_id: int,
    branch_id: int,
    stock: Decimal,
    with_batch: bool,
) -> tuple[int, int | None]:
    product = Product(
        barcode=f"STRESS-{uuid.uuid4().hex[:8]}",
        description="Producto Stress",
        category="Stress",
        unit="Unidad",
        stock=stock,
        purchase_price=Decimal("1.00"),
        sale_price=Decimal("2.00"),
        company_id=company_id,
        branch_id=branch_id,
    )
    session.add(product)
    await session.flush()
    batch_id = None
    if with_batch:
        batch = ProductBatch(
            batch_number=f"STRESS-B-{uuid.uuid4().hex[:6]}",
            expiration_date=None,
            stock=stock,
            product_id=product.id,
            product_variant_id=None,
            company_id=company_id,
            branch_id=branch_id,
        )
        session.add(batch)
        await session.flush()
        batch_id = batch.id
    await session.commit()
    return product.id, batch_id


async def _ensure_payment_methods(
    session,
    company_id: int,
    branch_id: int,
) -> None:
    set_tenant_context(company_id, branch_id)
    existing_codes = (
        await session.exec(
            select(PaymentMethod.code).where(
                PaymentMethod.company_id == company_id,
                PaymentMethod.branch_id == branch_id,
            )
        )
    ).all()
    existing = {str(code).strip().lower() for code in existing_codes if code}
    candidates = [
        ("Efectivo", "cash", PaymentMethodType.cash),
        ("Tarjeta Débito", "debit_card", PaymentMethodType.debit),
        ("Tarjeta Crédito", "credit_card", PaymentMethodType.credit),
        ("Yape", "yape", PaymentMethodType.yape),
        ("Plin", "plin", PaymentMethodType.plin),
        ("Transferencia", "transfer", PaymentMethodType.transfer),
    ]
    created = False
    for name, code, kind in candidates:
        if code in existing:
            continue
        session.add(
            PaymentMethod(
                company_id=company_id,
                branch_id=branch_id,
                name=name,
                code=code,
                method_id=code,
                description=name,
                kind=kind,
                enabled=True,
                is_active=True,
                allows_change=False,
            )
        )
        created = True
    if created:
        await session.commit()


async def _run_sale_attempt(
    SessionLocal,
    company_id: int,
    branch_id: int,
    product_id: int,
    quantity: Decimal,
) -> tuple[bool, str | None]:
    async with SessionLocal() as session:
        try:
            set_tenant_context(company_id, branch_id)
            item = SaleItemDTO(
                description="Producto Stress",
                quantity=quantity,
                unit="Unidad",
                price=Decimal("2.00"),
                product_id=product_id,
            )
            payment = PaymentInfoDTO(
                method="Efectivo",
                method_kind="cash",
                cash={"amount": Decimal("2.00") * quantity},
            )
            await SaleService.process_sale(
                session=session,
                user_id=None,
                company_id=company_id,
                branch_id=branch_id,
                items=[item],
                payment_data=payment,
            )
            await session.commit()
            return True, None
        except StockError as e:
            await session.rollback()
            return False, str(e)
        except Exception as e:
            await session.rollback()
            return False, f"ERROR: {e}"


async def _stress_sales(
    SessionLocal,
    company_id: int,
    branch_id: int,
    product_id: int,
    attempts: int,
    concurrency: int,
    quantity: Decimal,
) -> None:
    semaphore = asyncio.Semaphore(concurrency)

    async def worker():
        async with semaphore:
            return await _run_sale_attempt(
                SessionLocal, company_id, branch_id, product_id, quantity
            )

    results = await asyncio.gather(*[worker() for _ in range(attempts)])
    success = sum(1 for ok, _ in results if ok)
    failures = sum(1 for ok, msg in results if not ok and msg and "Stock" in msg)
    errors = [msg for ok, msg in results if not ok and msg and "ERROR" in msg]

    async with SessionLocal() as session:
        set_tenant_context(company_id, branch_id)
        product = (
            await session.exec(
                select(Product)
                .where(Product.id == product_id)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
            )
        ).first()
        final_stock = Decimal(str(product.stock or 0)) if product else Decimal("0")

    print(
        f"[Ventas] Intentos={attempts} Exitos={success} "
        f"StockFinal={final_stock}"
    )
    if errors:
        raise RuntimeError(f"Errores inesperados: {errors[:3]}")
    if final_stock < 0:
        raise RuntimeError("Stock negativo detectado.")


async def _reservation_attempt(
    SessionLocal,
    company_id: int,
    branch_id: int,
    slot_start: datetime,
    slot_end: datetime,
) -> bool:
    async with SessionLocal() as session:
        set_tenant_context(company_id, branch_id)
        try:
            dialect = session.get_bind().dialect.name
            lock_key = f"reservation:{company_id}:{branch_id}:futbol:{slot_start.date()}"
            if dialect in {"mysql", "mariadb"}:
                lock_stmt = text("SELECT GET_LOCK(:key, :timeout)").bindparams(
                    key=lock_key, timeout=5
                )
                result = await session.exec(lock_stmt)
                acquired = result.one()
                acquired = acquired[0] if isinstance(acquired, (tuple, list)) else acquired
                if not acquired:
                    await session.rollback()
                    return False

            conflict = (
                await session.exec(
                    select(FieldReservation.id)
                    .where(FieldReservation.sport == "futbol")
                    .where(FieldReservation.status != ReservationStatus.cancelled)
                    .where(FieldReservation.start_datetime < slot_end)
                    .where(FieldReservation.end_datetime > slot_start)
                    .where(FieldReservation.company_id == company_id)
                    .where(FieldReservation.branch_id == branch_id)
                    .with_for_update()
                    .limit(1)
                )
            ).first()
            if conflict:
                await session.rollback()
                return False

            reservation = FieldReservation(
                client_name="Stress",
                client_dni=None,
                client_phone=None,
                sport="futbol",
                field_name="Cancha Stress",
                start_datetime=slot_start,
                end_datetime=slot_end,
                total_amount=Decimal("10.00"),
                paid_amount=Decimal("0.00"),
                status=ReservationStatus.pending,
                company_id=company_id,
                branch_id=branch_id,
                user_id=None,
            )
            session.add(reservation)
            await session.commit()
            return True
        finally:
            try:
                release_stmt = text("SELECT RELEASE_LOCK(:key)").bindparams(key=lock_key)
                await session.exec(release_stmt)
            except Exception:
                pass


async def _stress_reservations(
    SessionLocal,
    company_id: int,
    branch_id: int,
    attempts: int,
    concurrency: int,
) -> None:
    semaphore = asyncio.Semaphore(concurrency)
    slot_start = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    slot_end = slot_start + timedelta(hours=1)

    async def worker():
        async with semaphore:
            return await _reservation_attempt(
                SessionLocal, company_id, branch_id, slot_start, slot_end
            )

    results = await asyncio.gather(*[worker() for _ in range(attempts)])
    success = sum(1 for ok in results if ok)

    async with SessionLocal() as session:
        set_tenant_context(company_id, branch_id)
        count = (
            await session.exec(
                select(FieldReservation.id)
                .where(FieldReservation.start_datetime == slot_start)
                .where(FieldReservation.end_datetime == slot_end)
                .where(FieldReservation.company_id == company_id)
                .where(FieldReservation.branch_id == branch_id)
            )
        ).all()
        total = len(count)

    print(f"[Reservas] Intentos={attempts} Exitos={success} TotalEnBD={total}")
    if total > 1:
        raise RuntimeError("Double booking detectado.")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default="", help="Async DB URL")
    parser.add_argument("--attempts", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--quantity", type=str, default="1")
    parser.add_argument("--with-batches", action="store_true")
    parser.add_argument("--unsafe", action="store_true")
    parser.add_argument("--skip-create", action="store_true")
    args = parser.parse_args()

    db_url = _require_db_url(args)
    _safe_db_check(db_url, args.unsafe)

    engine = create_async_engine(db_url, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(
        engine, class_=SQLModelAsyncSession, expire_on_commit=False
    )

    if not args.skip_create:
        await _create_schema(engine)

    async with SessionLocal() as session:
        company_id, branch_id = await _create_tenant(session)
        await _ensure_payment_methods(session, company_id, branch_id)
        stock = Decimal("25.00")
        product_id, _ = await _create_product(
            session,
            company_id,
            branch_id,
            stock,
            with_batch=args.with_batches,
        )

    quantity = Decimal(args.quantity)
    await _stress_sales(
        SessionLocal,
        company_id,
        branch_id,
        product_id,
        attempts=args.attempts,
        concurrency=args.concurrency,
        quantity=quantity,
    )

    await _stress_reservations(
        SessionLocal,
        company_id,
        branch_id,
        attempts=args.attempts,
        concurrency=args.concurrency,
    )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
