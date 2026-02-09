from __future__ import annotations

import argparse
import gzip
import os
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Permite ejecutar el script directamente desde scripts/.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Variable requerida faltante: {name}")
    return value


def _db_url(database: str) -> str:
    user = _env("DB_USER")
    password = os.getenv("DB_PASSWORD", "")
    host = _env("DB_HOST")
    port = os.getenv("DB_PORT", "3306")
    return (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database}"
    )


def _latest_backup(source_db: str) -> Path:
    backup_dir = ROOT_DIR / "backups"
    files = sorted(
        backup_dir.glob(f"{source_db}_backup_*.sql*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise RuntimeError(f"No se encontró backup para base '{source_db}'.")
    return files[0]


def _create_db(db_name: str) -> None:
    engine = create_engine(_db_url("mysql"))
    with engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )


def _restore_backup_to_db(backup_file: Path, target_db: str) -> None:
    mysql_exe = Path(r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe")
    if not mysql_exe.exists():
        raise RuntimeError(
            "mysql.exe no encontrado en ruta esperada: "
            r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
        )

    host = _env("DB_HOST")
    port = os.getenv("DB_PORT", "3306")
    user = _env("DB_USER")
    password = os.getenv("DB_PASSWORD", "")

    cmd = [
        str(mysql_exe),
        f"--host={host}",
        f"--port={port}",
        f"--user={user}",
        target_db,
    ]
    env = os.environ.copy()
    if password:
        env["MYSQL_PWD"] = password

    payload: bytes
    if backup_file.suffix == ".gz":
        with gzip.open(backup_file, "rb") as f:
            payload = f.read()
    else:
        payload = backup_file.read_bytes()

    result = subprocess.run(
        cmd,
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Restore falló ({result.returncode}): "
            f"{result.stderr.decode('utf-8', errors='ignore')}"
        )


def _table_count(engine, table_name: str) -> int:
    with engine.begin() as conn:
        value = conn.execute(
            text(f"SELECT COUNT(*) FROM `{table_name}`")
        ).scalar_one()
    return int(value or 0)


def _compare_counts(source_db: str, restore_db: str, tables: list[str]) -> list[tuple[str, int, int, bool]]:
    source_engine = create_engine(_db_url(source_db))
    restore_engine = create_engine(_db_url(restore_db))
    rows: list[tuple[str, int, int, bool]] = []
    for table in tables:
        source_count = _table_count(source_engine, table)
        restore_count = _table_count(restore_engine, table)
        rows.append((table, source_count, restore_count, source_count == restore_count))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-db",
        default="",
        help="DB origen (default: DB_NAME de .env)",
    )
    args = parser.parse_args()

    load_dotenv(".env")
    source_db = args.source_db or _env("DB_NAME")
    backup_file = _latest_backup(source_db)
    restore_db = f"{source_db}_restore_verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    _create_db(restore_db)
    _restore_backup_to_db(backup_file, restore_db)

    tables = [
        "company",
        "branch",
        "role",
        "user",
        "sale",
        "saleitem",
        "salepayment",
        "fieldreservation",
        "cashboxlog",
    ]
    rows = _compare_counts(source_db, restore_db, tables)
    ok = all(match for *_rest, match in rows)

    print("== Backup Restore Verify ==")
    print(f"source_db={source_db}")
    print(f"backup_file={backup_file.name}")
    print(f"restore_db={restore_db}")
    for table, source_count, restore_count, match in rows:
        print(
            f"{table}: source={source_count} restore={restore_count} match={match}"
        )
    print(f"result={'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
