"""Siembra un tenant COMPLETO y válido para las pruebas de carga P2 (escenario
cajero de scripts/ws_load.py): empresa (trial activo) + sucursal + rol superadmin
+ usuario cajero (password conocida) + producto con stock + método de pago +
caja ABIERTA (requisito de confirm_sale).

SÓLO contra un schema de PRUEBA/descartable (nombre con test/staging/loadtest),
NUNCA `sistema_ventas`. Reutiliza los modelos reales para no desincronizar hashing
ni privilegios.

Uso:
    SEED_DB_URL="mysql+aiomysql://app:PASS@127.0.0.1:33306/sistema_loadtest" \
      python scripts/seed_loadtest_tenant.py --user cajero --password "Cajero.2026"

Imprime al final: company_id, branch_id, user_id, product_id (para ws_load.py).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import bcrypt
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.models  # noqa: F401
from app.models import (
    Company, Branch, Role, User, UserBranch, Product, PaymentMethod, CashboxSession,
)


def _safe(db_url: str, unsafe: bool) -> None:
    name = (make_url(db_url).database or "").lower()
    if not unsafe and not any(t in name for t in ("test", "staging", "loadtest")):
        print(f"ERROR: '{name}' no parece BD de prueba. Usá --unsafe si estás seguro.")
        sys.exit(2)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-url", default=os.getenv("SEED_DB_URL", ""))
    ap.add_argument("--user", default="cajero")
    ap.add_argument("--password", default="Cajero.2026")
    ap.add_argument("--products", type=int, default=1,
                    help="Cantidad de productos a sembrar (uno por VU evita lock contention).")
    ap.add_argument("--unsafe", action="store_true")
    args = ap.parse_args()

    db_url = args.db_url or ""
    if not db_url:
        print("ERROR: definí SEED_DB_URL o --db-url.")
        sys.exit(2)
    _safe(db_url, args.unsafe)

    engine = create_async_engine(db_url, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, class_=SQLModelAsyncSession, expire_on_commit=False)
    stamp = uuid.uuid4().hex[:8]
    now = datetime.now()

    async with SessionLocal() as s:
        company = Company(
            name=f"LOADTEST-{stamp}", ruc=f"LT{stamp}00", created_at=now,
            plan_type="trial", trial_ends_at=now + timedelta(days=365),
        )
        s.add(company)
        await s.flush()

        branch = Branch(company_id=company.id, name="LoadTest Branch", address="-")
        s.add(branch)
        await s.flush()

        # Rol "superadmin" => _get_privileges_dict devuelve TODOS los privilegios
        # (incluye create_ventas) sin cablear Permission individuales.
        role = Role(name="superadmin", company_id=company.id)
        s.add(role)
        await s.flush()

        pw_hash = bcrypt.hashpw(args.password.encode(), bcrypt.gensalt()).decode()
        user = User(
            username=args.user, email=f"{args.user}-{stamp}@loadtest.local",
            password_hash=pw_hash, role_id=role.id,
            company_id=company.id, branch_id=branch.id, is_active=True,
        )
        s.add(user)
        await s.flush()
        s.add(UserBranch(user_id=user.id, branch_id=branch.id))

        product_ids: list[int] = []
        for i in range(max(1, args.products)):
            product = Product(
                barcode=f"LT-{stamp}-{i}", description=f"Producto LoadTest {i}",
                category="LoadTest", unit="Unidad", stock=Decimal("500000"),
                purchase_price=Decimal("1.00"), sale_price=Decimal("2.00"),
                company_id=company.id, branch_id=branch.id,
            )
            s.add(product)
            await s.flush()
            product_ids.append(product.id)

        s.add(PaymentMethod(
            company_id=company.id, branch_id=branch.id, name="Efectivo", code="cash",
            method_id="cash", description="Efectivo", kind="cash",
            enabled=True, is_active=True, allows_change=True,
        ))

        # Caja ABIERTA para el cajero (requisito de confirm_sale).
        s.add(CashboxSession(
            company_id=company.id, branch_id=branch.id, user_id=user.id,
            is_open=True, opening_amount=Decimal("100.00"), opening_time=now,
        ))
        await s.commit()

        print("SEED OK")
        print(f"company_id={company.id}")
        print(f"branch_id={branch.id}")
        print(f"user_id={user.id}")
        print(f"products={len(product_ids)} product_ids={product_ids[0]}-{product_ids[-1]}")
        print(f"login_user={args.user}")
        print(f"login_pass={args.password}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
