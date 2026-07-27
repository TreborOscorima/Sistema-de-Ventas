"""
Seed de VOLUMEN para pruebas de performance/escalabilidad (Fase P1 del
``docs/PERF_SCALABILITY_PLAN.md``).

Genera un dataset grande y representativo en una BD de *staging* para poder
correr ``EXPLAIN`` sobre las queries calientes con tablas realmente pobladas
y validar que los índices existentes se usan. NO reemplaza a
``db_seeds.py`` (que siembra datos de lookup por defecto); esto es carga masiva.

Seguridad
---------
- Rechaza correr contra una BD cuyo nombre no contenga 'test' / 'stress' /
  'seed' / 'staging', salvo que se pase ``--unsafe`` (mismo criterio que
  ``scripts/stress_concurrency.py``). NUNCA apuntar a producción.
- Todas las empresas creadas llevan prefijo ``SEEDVOL-`` (name) / ``SEEDVOL``
  (ruc) para que ``scripts/cleanup_stress_data.py`` las pueda borrar después.

Rendimiento
-----------
- Inserta las tablas hijas (product, sale, saleitem, stockmovement) por
  **bulk core insert** en chunks, NO vía ORM/SaleService: a escala de decenas
  de millones de filas el camino ORM es inviable. company_id/branch_id se
  setean explícitamente en cada fila (aislamiento multi-tenant).

Uso
---
    # BD de staging (URL async). Un perfil chico primero:
    SEED_DB_URL="mysql+aiomysql://user:pass@host:3306/sistema_staging" \
    python scripts/seed_volume.py --profile small

    # El objetivo completo de §3 (¡~175M filas — sólo en staging con disco!):
    python scripts/seed_volume.py --db-url "..." --profile full

    # Ajuste fino manual:
    python scripts/seed_volume.py --db-url "..." \
        --companies 50 --products 2000 --sales 50000 \
        --avg-items 4 --stockmovements 100000

Perfiles (valores por defecto por empresa)
------------------------------------------
    smoke  :   2 empresas ×   100 prod ×     500 ventas × ~3 items ×    200 mov
    small  :  10 empresas ×   500 prod ×   2.000 ventas × ~3 items ×  1.000 mov
    medium :  50 empresas × 1.000 prod ×  10.000 ventas × ~4 items × 20.000 mov
    full   : 500 empresas × 2.000 prod ×  50.000 ventas × ~4 items ×100.000 mov  (§3)
"""
from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

# Permite ejecutar el script directamente desde scripts/.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.models  # noqa: F401  (registra todos los modelos en metadata)
from app.enums import PaymentMethodType, SaleStatus
from app.models import Branch, Company, Product, Sale, SaleItem, StockMovement

SEED_PREFIX = "SEEDVOL"

# ── Perfiles: (companies, products, sales, avg_items, stockmovements) ──
PROFILES: dict[str, dict[str, int]] = {
    "smoke": dict(companies=2, products=100, sales=500, avg_items=3, stockmovements=200),
    "small": dict(companies=10, products=500, sales=2_000, avg_items=3, stockmovements=1_000),
    "medium": dict(companies=50, products=1_000, sales=10_000, avg_items=4, stockmovements=20_000),
    "full": dict(companies=500, products=2_000, sales=50_000, avg_items=4, stockmovements=100_000),
}


# ═══════════════════════════════════════════════════════════════════
# Seguridad + utilidades
# ═══════════════════════════════════════════════════════════════════
def _require_db_url(args: argparse.Namespace) -> str:
    db_url = args.db_url or os.getenv("SEED_DB_URL") or os.getenv("STRESS_DB_URL") or ""
    db_url = db_url.strip()
    if not db_url:
        print("ERROR: Defina SEED_DB_URL / STRESS_DB_URL o use --db-url.")
        sys.exit(2)
    return db_url


def _safe_db_check(db_url: str, unsafe: bool) -> None:
    try:
        db_name = (make_url(db_url).database or "").lower()
    except Exception:
        db_name = ""
    if unsafe:
        print("[!] --unsafe: se omite el chequeo de BD de prueba.")
        return
    if not any(tok in db_name for tok in ("test", "stress", "seed", "staging")):
        print(
            f"ERROR: La BD '{db_name}' no parece de prueba/staging. "
            "Renómbrela o use --unsafe SÓLO si está 100% seguro (NUNCA en prod)."
        )
        sys.exit(2)


def _chunks(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


async def _bulk_insert(SessionLocal, table, rows: list[dict], chunk: int) -> None:
    """Inserta ``rows`` en ``table`` por lotes, un commit por lote."""
    if not rows:
        return
    for batch in _chunks(rows, chunk):
        async with SessionLocal() as session:
            await session.exec(insert(table).values(batch))  # type: ignore[arg-type]
            await session.commit()


async def _fetch_ids(SessionLocal, model, company_id: int, branch_id: int) -> list[int]:
    async with SessionLocal() as session:
        result = await session.exec(
            select(model.id)
            .where(model.company_id == company_id)
            .where(model.branch_id == branch_id)
            .order_by(model.id)
        )
        # .all() puede devolver Row (1 col) o escalares según el driver → coercer a int.
        def _scalar(r):
            try:
                return int(r[0])
            except (TypeError, KeyError, IndexError):
                return int(r)
        return [_scalar(r) for r in result.all()]


# ═══════════════════════════════════════════════════════════════════
# Generación por empresa
# ═══════════════════════════════════════════════════════════════════
async def _create_company(SessionLocal, idx: int) -> tuple[int, int]:
    stamp = uuid.uuid4().hex[:8]
    async with SessionLocal() as session:
        company = Company(
            name=f"{SEED_PREFIX}-{idx:04d}-{stamp}",
            ruc=f"{SEED_PREFIX}{idx:04d}{stamp}",
            plan_type="professional",
            max_branches=-1,
            max_users=-1,
        )
        session.add(company)
        await session.flush()
        branch = Branch(
            company_id=company.id,
            name="Casa Central",
            address="Seed staging",
            is_main=True,
        )
        session.add(branch)
        await session.flush()
        await session.commit()
        return company.id, branch.id


def _gen_products(company_id: int, branch_id: int, n: int, rng: random.Random) -> list[dict]:
    cats = ["Bebidas", "Almacen", "Limpieza", "Perfumeria", "Fiambres", "Panaderia", "General"]
    rows = []
    for i in range(n):
        purchase = Decimal(rng.randrange(50, 5000)) / Decimal("100")
        sale = (purchase * Decimal("1.35")).quantize(Decimal("0.01"))
        rows.append(
            dict(
                company_id=company_id,
                branch_id=branch_id,
                barcode=f"SV{company_id}-{i:06d}",
                description=f"Producto seed {i:06d}",
                category=rng.choice(cats),
                stock=Decimal(rng.randrange(0, 5000)) / Decimal("10"),
                unit="Unidad",
                purchase_price=purchase,
                sale_price=sale,
                is_active=True,
                tax_rate=Decimal("18.00"),
            )
        )
    return rows


def _gen_stockmovements(
    company_id: int, branch_id: int, n: int, product_ids: list[int],
    base: datetime, rng: random.Random,
) -> list[dict]:
    types = ["ingreso", "ajuste", "merma", "venta"]
    rows = []
    for _ in range(n):
        rows.append(
            dict(
                company_id=company_id,
                branch_id=branch_id,
                timestamp=base - timedelta(minutes=rng.randrange(0, 525_600)),
                type=rng.choice(types),
                quantity=Decimal(rng.randrange(1, 200)),
                description="seed",
                product_id=rng.choice(product_ids) if product_ids else None,
            )
        )
    return rows


# Distribución realista de estados (aprox. retail): la mayoría completadas,
# una cola de canceladas/pendientes/devueltas. Suma 1.0.
_STATUS_WEIGHTS: tuple[tuple[SaleStatus, float], ...] = (
    (SaleStatus.completed, 0.90),
    (SaleStatus.cancelled, 0.05),
    (SaleStatus.pending, 0.03),
    (SaleStatus.returned, 0.02),
)


def _pick_status(rng: random.Random) -> SaleStatus:
    r = rng.random()
    acc = 0.0
    for status, w in _STATUS_WEIGHTS:
        acc += w
        if r <= acc:
            return status
    return SaleStatus.completed


def _recent_biased_ts(base: datetime, rng: random.Random, days_span: int = 365) -> datetime:
    """Timestamp sesgado a fechas recientes (mímica de tráfico real: más venta hoy)."""
    days_ago = int(days_span * (rng.random() ** 1.7))  # exponente >1 => masa cerca de 0
    minutes = rng.randrange(0, 1440)
    return base - timedelta(days=days_ago, minutes=minutes)


def _gen_sales_and_items(
    company_id: int, branch_id: int, n_sales: int, avg_items: int,
    product_prices: list[tuple[int, Decimal]], base: datetime, rng: random.Random,
) -> tuple[list[dict], list[list[dict]]]:
    """Devuelve (filas de sale, lista-por-venta de filas de saleitem-sin-sale_id).

    Los saleitems no tienen ``sale_id`` todavía: se completa tras insertar las
    ventas y recuperar sus ids en orden (auto-increment ascendente == orden de
    inserción). ``total_amount`` de cada venta = suma de subtotales de sus ítems.
    Estado con distribución realista (~90% completed) y timestamps sesgados a reciente.
    """
    sales: list[dict] = []
    items_per_sale: list[list[dict]] = []
    for _ in range(n_sales):
        k = max(1, int(rng.gauss(avg_items, 1)))
        ts = _recent_biased_ts(base, rng)
        sale_items: list[dict] = []
        total = Decimal("0.00")
        for _ in range(k):
            product_id, unit_price = rng.choice(product_prices)
            qty = Decimal(rng.randrange(1, 6))
            subtotal = (qty * unit_price).quantize(Decimal("0.01"))
            total += subtotal
            sale_items.append(
                dict(
                    company_id=company_id,
                    branch_id=branch_id,
                    product_id=product_id,
                    quantity=qty,
                    unit_price=unit_price,
                    unit_price_base=unit_price,
                    subtotal=subtotal,
                    product_name_snapshot=f"Producto seed {product_id}",
                )
            )
        sales.append(
            dict(
                company_id=company_id,
                branch_id=branch_id,
                timestamp=ts,
                total_amount=total,
                status=_pick_status(rng),
                payment_condition="contado",
            )
        )
        items_per_sale.append(sale_items)
    return sales, items_per_sale


async def _seed_company(SessionLocal, idx: int, cfg: dict, chunk: int, rng: random.Random) -> dict:
    base = datetime.now()
    company_id, branch_id = await _create_company(SessionLocal, idx)

    # 1. Productos
    products = _gen_products(company_id, branch_id, cfg["products"], rng)
    await _bulk_insert(SessionLocal, Product.__table__, products, chunk)
    product_ids = await _fetch_ids(SessionLocal, Product, company_id, branch_id)
    # (id, sale_price) para armar ítems con precios coherentes.
    price_by_id = {pid: products[i]["sale_price"] for i, pid in enumerate(product_ids)}
    product_prices = list(price_by_id.items())

    # 2. Movimientos de stock
    movements = _gen_stockmovements(
        company_id, branch_id, cfg["stockmovements"], product_ids, base, rng
    )
    await _bulk_insert(SessionLocal, StockMovement.__table__, movements, chunk)

    # 3. Ventas
    sales, items_per_sale = _gen_sales_and_items(
        company_id, branch_id, cfg["sales"], cfg["avg_items"], product_prices, base, rng
    )
    await _bulk_insert(SessionLocal, Sale.__table__, sales, chunk)
    sale_ids = await _fetch_ids(SessionLocal, Sale, company_id, branch_id)

    # 4. SaleItems (alineados por índice con los sale_ids recién creados)
    all_items: list[dict] = []
    for sale_id, sale_items in zip(sale_ids, items_per_sale):
        for it in sale_items:
            it["sale_id"] = sale_id
            all_items.append(it)
    await _bulk_insert(SessionLocal, SaleItem.__table__, all_items, chunk)

    return dict(
        company_id=company_id,
        products=len(products),
        stockmovements=len(movements),
        sales=len(sales),
        saleitems=len(all_items),
    )


# ═══════════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════════
async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed de volumen para pruebas de performance.")
    parser.add_argument("--db-url", default="", help="Async DB URL (o SEED_DB_URL/STRESS_DB_URL).")
    parser.add_argument("--profile", choices=list(PROFILES), default="small")
    parser.add_argument("--companies", type=int, help="Override: nº de empresas.")
    parser.add_argument("--products", type=int, help="Override: productos por empresa.")
    parser.add_argument("--sales", type=int, help="Override: ventas por empresa.")
    parser.add_argument("--avg-items", type=int, help="Override: ítems promedio por venta.")
    parser.add_argument("--stockmovements", type=int, help="Override: movimientos por empresa.")
    parser.add_argument("--chunk-size", type=int, default=5_000, help="Filas por lote de insert.")
    parser.add_argument("--seed", type=int, default=1234, help="Semilla RNG (reproducibilidad).")
    parser.add_argument("--skip-schema", action="store_true", help="No crear tablas (ya existen).")
    parser.add_argument("--unsafe", action="store_true")
    args = parser.parse_args()

    cfg = dict(PROFILES[args.profile])
    for key in ("companies", "products", "sales", "avg_items", "stockmovements"):
        val = getattr(args, key.replace("-", "_"))
        if val is not None:
            cfg[key] = val

    db_url = _require_db_url(args)
    _safe_db_check(db_url, args.unsafe)

    total_rows = cfg["companies"] * (
        cfg["products"] + cfg["stockmovements"]
        + cfg["sales"] + cfg["sales"] * cfg["avg_items"]
    )
    print(
        f"Perfil={args.profile}  empresas={cfg['companies']}  "
        f"prod/emp={cfg['products']}  ventas/emp={cfg['sales']}  "
        f"items~{cfg['avg_items']}  mov/emp={cfg['stockmovements']}"
    )
    print(f"Filas estimadas a insertar: ~{total_rows:,}")

    engine = create_async_engine(db_url, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(
        engine, class_=SQLModelAsyncSession, expire_on_commit=False
    )

    if not args.skip_schema:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    rng = random.Random(args.seed)
    started = time.perf_counter()
    totals = dict(products=0, stockmovements=0, sales=0, saleitems=0)
    for idx in range(1, cfg["companies"] + 1):
        c0 = time.perf_counter()
        res = await _seed_company(SessionLocal, idx, cfg, args.chunk_size, rng)
        for k in totals:
            totals[k] += res[k]
        print(
            f"  [{idx}/{cfg['companies']}] company_id={res['company_id']}  "
            f"prod={res['products']} mov={res['stockmovements']} "
            f"ventas={res['sales']} items={res['saleitems']}  "
            f"({time.perf_counter() - c0:.1f}s)"
        )

    await engine.dispose()
    elapsed = time.perf_counter() - started
    grand = sum(totals.values()) + cfg["companies"] * 2  # +company/branch
    print(
        f"\n[OK] Seed completo en {elapsed:.1f}s. "
        f"products={totals['products']:,} sales={totals['sales']:,} "
        f"saleitems={totals['saleitems']:,} stockmovements={totals['stockmovements']:,} "
        f"(~{grand:,} filas). Prefijo de limpieza: {SEED_PREFIX}-*"
    )
    print("Para borrar: python scripts/cleanup_stress_data.py")


if __name__ == "__main__":
    asyncio.run(main())
