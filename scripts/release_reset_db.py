from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Permite ejecutar el script directamente desde scripts/.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.backup_db import create_backup


@dataclass
class TableCount:
    table: str
    rows: int


# Tablas de datos operativos/tenant a limpiar para lanzamiento.
# No incluye `alembic_version` ni catálogos globales (`currency`, `permission`).
PURGE_TABLES = [
    "userbranch",
    "rolepermission",
    "cashboxlog",
    "cashboxsession",
    "saleinstallment",
    "saleitem",
    "salepayment",
    "sale",
    "fieldreservation",
    "productbatch",
    "productkit",
    "productvariant",
    "pricetier",
    "stockmovement",
    "product",
    "purchaseitem",
    "purchase",
    "supplier",
    "client",
    "paymentmethod",
    "fieldprice",
    "unit",
    "category",
    "companysettings",
    "user",
    "role",
    "branch",
    "company",
]


def _db_url() -> str:
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME")
    if not user or db_name is None:
        raise RuntimeError("Faltan DB_USER o DB_NAME en entorno.")
    return f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db_name}"


def _existing_tables(conn) -> set[str]:
    rows = conn.execute(text("SHOW TABLES")).fetchall()
    return {str(row[0]).strip().lower() for row in rows}


def _count_rows(conn, table: str) -> int:
    value = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one()
    return int(value or 0)


def _collect_counts(conn, tables: list[str]) -> list[TableCount]:
    counts: list[TableCount] = []
    for table in tables:
        counts.append(TableCount(table=table, rows=_count_rows(conn, table)))
    return counts


def _print_counts(title: str, counts: list[TableCount]) -> None:
    print(f"\n== {title} ==")
    total_rows = 0
    for item in counts:
        total_rows += item.rows
        print(f"{item.table}: {item.rows}")
    print(f"TOTAL_ROWS={total_rows}")


def _purge_tables(conn, tables: list[str]) -> None:
    conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    try:
        for table in tables:
            conn.execute(text(f"TRUNCATE TABLE `{table}`"))
    finally:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Limpia datos operativos de la DB para lanzamiento, "
            "manteniendo migraciones y catálogos globales."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Ejecuta limpieza real. Sin este flag, solo muestra preview.",
    )
    parser.add_argument(
        "--confirm",
        default="",
        help="Confirmación explícita. Debe ser exactamente: CLEAN_RELEASE_DB",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="No generar backup automático antes de limpiar.",
    )
    parser.add_argument(
        "--wipe-permissions",
        action="store_true",
        help="También limpia la tabla global `permission`.",
    )
    args = parser.parse_args()

    load_dotenv(".env")
    db_name = os.getenv("DB_NAME", "")
    print(f"DB objetivo: {db_name}")

    url = _db_url()
    engine = create_engine(url)
    with engine.begin() as conn:
        existing = _existing_tables(conn)

        purge_tables = [table for table in PURGE_TABLES if table in existing]
        if args.wipe_permissions and "permission" in existing:
            purge_tables = purge_tables + ["permission"]

        missing_tables = sorted(set(PURGE_TABLES) - set(purge_tables))
        if missing_tables:
            print(f"Advertencia: tablas no encontradas y omitidas: {', '.join(missing_tables)}")

        before_counts = _collect_counts(conn, purge_tables)
        _print_counts("Preview antes de limpieza", before_counts)

        if not args.execute:
            print("\nDRY-RUN: no se realizaron cambios.")
            print("Para ejecutar limpieza real usa:")
            print(
                "python scripts/release_reset_db.py --execute "
                "--confirm CLEAN_RELEASE_DB"
            )
            return 0

    # Fuera de la transacción de preview, validar confirmación.
    if args.confirm != "CLEAN_RELEASE_DB":
        print(
            "ERROR: confirmación inválida. Usa --confirm CLEAN_RELEASE_DB para ejecutar.",
            file=sys.stderr,
        )
        return 2

    if not args.skip_backup:
        backup = create_backup(compress=True, keep=10)
        if backup is None:
            print("ERROR: no se pudo generar backup previo.", file=sys.stderr)
            return 3
        print(f"Backup previo generado: {backup.name}")

    with engine.begin() as conn:
        _purge_tables(conn, purge_tables)
        after_counts = _collect_counts(conn, purge_tables)
        _print_counts("Estado después de limpieza", after_counts)

    leftovers = [item for item in after_counts if item.rows > 0]
    if leftovers:
        print("ERROR: quedaron filas en tablas limpiadas.", file=sys.stderr)
        return 4

    print("\nLimpieza de release completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
