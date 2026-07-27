"""
EXPLAIN de las queries CALIENTES sobre la BD de staging (Fase P1 del
``docs/PERF_SCALABILITY_PLAN.md``).

Corre ``EXPLAIN`` sobre un set curado de queries representativas (POS,
dashboard, reportes, caja, inventario) contra una BD poblada por
``scripts/seed_volume.py`` y reporta, por query:

    - ``type``  : método de acceso (ALL = full scan → 🔴, ref/range/eq_ref → 🟢)
    - ``key``   : índice elegido por el optimizador (NULL = ninguno → 🔴)
    - ``rows``  : filas estimadas a examinar
    - ``Extra`` : filesort / temporary / etc.

Objetivo: confirmar que los índices existentes se USAN con volumen real y
cazar los pocos huecos (full scans o filesorts en el camino caliente).

Uso
---
    SEED_DB_URL="mysql+pymysql://app:PASS@127.0.0.1:33306/sistema_staging" \
    python scripts/explain_hot_queries.py

    # o URL async (se normaliza a pymysql para EXPLAIN sync):
    python scripts/explain_hot_queries.py --db-url "mysql+aiomysql://..."

    # elegir empresa manualmente (por defecto: la de más ventas):
    python scripts/explain_hot_queries.py --company-id 3
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

# ── Umbrales de alerta ──
BIG_SCAN_ROWS = 5_000  # rows examinadas por encima → señalar aunque use índice


def _resolve_sync_url(raw: str) -> str:
    """Normaliza cualquier driver async a pymysql (EXPLAIN corre sync)."""
    url = make_url(raw)
    if "+aiomysql" in raw or url.drivername.endswith("aiomysql"):
        url = url.set(drivername="mysql+pymysql")
    # render_as_string(hide_password=False): str(url) enmascara la pass como '***'.
    return url.render_as_string(hide_password=False)


def _require_db_url(args: argparse.Namespace) -> str:
    raw = args.db_url or os.getenv("SEED_DB_URL") or os.getenv("STRESS_DB_URL") or ""
    raw = raw.strip()
    if not raw:
        print("ERROR: Defina SEED_DB_URL / STRESS_DB_URL o use --db-url.")
        sys.exit(2)
    return _resolve_sync_url(raw)


def _pick_tenant(conn, company_id: int | None) -> tuple[int, int]:
    """Elige (company_id, branch_id): el pasado, o la empresa con más ventas."""
    if company_id is None:
        row = conn.execute(
            text(
                "SELECT company_id, branch_id, COUNT(*) c FROM sale "
                "GROUP BY company_id, branch_id ORDER BY c DESC LIMIT 1"
            )
        ).first()
        if not row:
            print("ERROR: No hay ventas en la BD. ¿Corrió el seed?")
            sys.exit(2)
        return int(row[0]), int(row[1])
    row = conn.execute(
        text("SELECT branch_id FROM sale WHERE company_id=:c LIMIT 1"),
        {"c": company_id},
    ).first()
    if not row:
        print(f"ERROR: La empresa {company_id} no tiene ventas.")
        sys.exit(2)
    return company_id, int(row[0])


def _hot_queries(cid: int, bid: int) -> list[tuple[str, str, dict]]:
    """(nombre, SQL con :params, params). SQL representativo del camino caliente."""
    now = datetime.now()
    d30 = now - timedelta(days=30)
    p = dict(c=cid, b=bid, d0=d30, d1=now)
    return [
        (
            "POS - producto por barcode (exacto)",
            "SELECT * FROM product WHERE company_id=:c AND branch_id=:b AND barcode=:bc",
            {**p, "bc": f"SV{cid}-000001"},
        ),
        (
            "POS - producto por nombre (prefijo)",
            "SELECT * FROM product WHERE company_id=:c AND branch_id=:b "
            "AND description LIKE :term LIMIT 20",
            {**p, "term": "Producto seed 0001%"},
        ),
        (
            "POS - listado por categoría + activo",
            "SELECT * FROM product WHERE company_id=:c AND branch_id=:b "
            "AND category=:cat AND is_active=1 ORDER BY description LIMIT 50",
            {**p, "cat": "Bebidas"},
        ),
        (
            "Inventario - stock bajo (stock <= min_stock_alert)",
            "SELECT * FROM product WHERE company_id=:c AND branch_id=:b "
            "AND is_active=1 AND stock <= min_stock_alert",
            p,
        ),
        (
            "POS/Historial - ventas por rango + estado (DESC)",
            "SELECT * FROM sale WHERE company_id=:c AND branch_id=:b "
            "AND status='completed' AND timestamp BETWEEN :d0 AND :d1 "
            "ORDER BY timestamp DESC LIMIT 50",
            p,
        ),
        (
            "Dashboard - KPI total+conteo por rango",
            "SELECT COALESCE(SUM(total_amount),0), COUNT(*) FROM sale "
            "WHERE company_id=:c AND branch_id=:b AND status='completed' "
            "AND timestamp BETWEEN :d0 AND :d1",
            p,
        ),
        (
            "Dashboard - top productos (join saleitem×sale)",
            "SELECT si.product_id, SUM(si.quantity) q FROM saleitem si "
            "JOIN sale s ON s.id=si.sale_id "
            "WHERE si.company_id=:c AND si.branch_id=:b "
            "AND s.status='completed' AND s.timestamp BETWEEN :d0 AND :d1 "
            "GROUP BY si.product_id ORDER BY q DESC LIMIT 10",
            p,
        ),
        (
            "Reporte - detalle de una venta (items)",
            "SELECT * FROM saleitem WHERE company_id=:c AND branch_id=:b "
            "AND sale_id=(SELECT id FROM sale WHERE company_id=:c AND branch_id=:b LIMIT 1)",
            p,
        ),
        (
            "Inventario - movimientos por producto (DESC)",
            "SELECT * FROM stockmovement WHERE company_id=:c AND branch_id=:b "
            "AND product_id=(SELECT id FROM product WHERE company_id=:c AND branch_id=:b LIMIT 1) "
            "ORDER BY timestamp DESC LIMIT 50",
            p,
        ),
        (
            "Caja - movimientos por rango",
            "SELECT * FROM cashboxlog WHERE company_id=:c AND branch_id=:b "
            "AND timestamp BETWEEN :d0 AND :d1 ORDER BY timestamp DESC",
            p,
        ),
    ]


def _flag(access_type: str, key: str | None, rows: int) -> str:
    if access_type == "ALL" or key is None:
        return "[X] FULL SCAN"
    if rows and rows > BIG_SCAN_ROWS:
        return "[~] usa indice pero examina muchas filas"
    return "[OK]"


def main() -> None:
    parser = argparse.ArgumentParser(description="EXPLAIN de queries calientes.")
    parser.add_argument("--db-url", default="")
    parser.add_argument("--company-id", type=int, default=None)
    parser.add_argument("--verbose", action="store_true", help="Imprime también EXPLAIN FORMAT=JSON.")
    args = parser.parse_args()

    db_url = _require_db_url(args)
    engine = create_engine(db_url, poolclass=None)

    with engine.connect() as conn:
        cid, bid = _pick_tenant(conn, args.company_id)
        print(f"Tenant analizado: company_id={cid}  branch_id={bid}\n")
        header = f"{'Query':<48} {'type':<8} {'key':<34} {'rows':>10}  veredicto"
        print(header)
        print("-" * len(header))

        alerts: list[str] = []
        for name, sql, params in _hot_queries(cid, bid):
            try:
                row = conn.execute(text("EXPLAIN " + sql), params).mappings().first()
            except Exception as e:  # noqa: BLE001
                print(f"{name:<48} ERROR: {str(e)[:60]}")
                continue
            access_type = (row or {}).get("type") or "?"
            key = (row or {}).get("key")
            rows_est = int((row or {}).get("rows") or 0)
            extra = (row or {}).get("Extra") or ""
            verdict = _flag(access_type, key, rows_est)
            if verdict.startswith(("[X]", "[~]")):
                alerts.append(f"  - {name}: {verdict} (type={access_type}, key={key}, rows~{rows_est}, extra={extra})")
            print(f"{name:<48} {access_type:<8} {str(key):<34} {rows_est:>10}  {verdict}")
            if extra:
                print(f"{'':<48} +- Extra: {extra}")
            if args.verbose:
                js = conn.execute(text("EXPLAIN FORMAT=JSON " + sql), params).scalar()
                print(f"{'':<4}{js}\n")

        print("\n" + "=" * 60)
        if alerts:
            print(f"[!] {len(alerts)} query(s) a revisar:")
            print("\n".join(alerts))
            print("\n-> Candidatas a indice nuevo / reescritura. Documentar en seccion 3 del plan.")
        else:
            print("[OK] Todas las queries calientes usan indice y examinan pocas filas.")

    engine.dispose()


if __name__ == "__main__":
    main()
