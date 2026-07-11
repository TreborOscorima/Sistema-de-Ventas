"""Verificación de restore de backup MySQL.

Crea una DB temporal, restaura el último backup, compara row counts de TODAS
las tablas contra la DB de origen, y limpia la DB temporal al finalizar.

Soporta dos modos:
  - Local: usa binario `mysql` del sistema (default).
  - Docker: usa `docker exec` contra el contenedor MySQL (--docker).

Uso:
    python scripts/backup_restore_verify.py
    python scripts/backup_restore_verify.py --docker
    python scripts/backup_restore_verify.py --source-db sistema_ventas
    python scripts/backup_restore_verify.py --backup-file backups/specific_backup.sql.gz
"""
from __future__ import annotations

import argparse
import gzip
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.backup_db import resolve_mysql_binary


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
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{database}"
    )


def _latest_backup(source_db: str) -> Path:
    backup_dir = ROOT_DIR / "backups"
    files = sorted(
        backup_dir.glob(f"{source_db}*.sql*"),
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
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )


def _drop_db(db_name: str) -> None:
    engine = create_engine(_db_url("mysql"))
    with engine.begin() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS `{db_name}`"))


def _restore_local(backup_file: Path, target_db: str) -> None:
    mysql_exe = resolve_mysql_binary("mysql")
    if not mysql_exe:
        raise RuntimeError(
            "mysql no encontrado en PATH ni en rutas comunes de instalación."
        )

    host = _env("DB_HOST")
    port = os.getenv("DB_PORT", "3306")
    user = _env("DB_USER")
    password = os.getenv("DB_PASSWORD", "")

    cmd = [mysql_exe, f"--host={host}", f"--port={port}", f"--user={user}", target_db]
    env = os.environ.copy()
    if password:
        env["MYSQL_PWD"] = password

    if backup_file.suffix == ".gz":
        with gzip.open(backup_file, "rb") as f:
            payload = f.read()
    else:
        payload = backup_file.read_bytes()

    result = subprocess.run(
        cmd, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Restore falló ({result.returncode}): "
            f"{result.stderr.decode('utf-8', errors='ignore')}"
        )


def _restore_docker(backup_file: Path, target_db: str, container: str) -> None:
    if backup_file.suffix == ".gz":
        with gzip.open(backup_file, "rb") as f:
            payload = f.read()
    else:
        payload = backup_file.read_bytes()

    cmd = [
        "docker", "exec", "-i", container,
        "sh", "-c",
        f'MYSQL_PWD="${{MYSQL_ROOT_PASSWORD}}" mysql -u root {target_db}',
    ]
    result = subprocess.run(
        cmd, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Docker restore falló ({result.returncode}): "
            f"{result.stderr.decode('utf-8', errors='ignore')}"
        )


def _discover_tables(database: str) -> list[str]:
    engine = create_engine(_db_url(database))
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    engine.dispose()
    return sorted(tables)


def _table_count(engine, table_name: str) -> int:
    with engine.begin() as conn:
        value = conn.execute(
            text(f"SELECT COUNT(*) FROM `{table_name}`")
        ).scalar_one()
    return int(value or 0)


def _compare_counts(
    source_db: str, restore_db: str, tables: list[str],
) -> list[tuple[str, int, int, bool]]:
    source_engine = create_engine(_db_url(source_db))
    restore_engine = create_engine(_db_url(restore_db))
    rows: list[tuple[str, int, int, bool]] = []
    for table in tables:
        try:
            src = _table_count(source_engine, table)
            rst = _table_count(restore_engine, table)
            rows.append((table, src, rst, src == rst))
        except Exception as e:
            print(f"  WARN: no se pudo comparar '{table}': {e}")
    source_engine.dispose()
    restore_engine.dispose()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verificar restore de backup MySQL"
    )
    parser.add_argument(
        "--source-db", default="",
        help="DB origen (default: DB_NAME de .env)",
    )
    parser.add_argument(
        "--backup-file", default="",
        help="Archivo de backup específico (default: el más reciente)",
    )
    parser.add_argument(
        "--docker", action="store_true",
        help="Restaurar vía docker exec en vez de mysql local",
    )
    parser.add_argument(
        "--container", default="tuwayki_mysql",
        help="Nombre del contenedor MySQL para modo --docker",
    )
    parser.add_argument(
        "--no-cleanup", action="store_true",
        help="No eliminar la DB temporal al finalizar (para inspección)",
    )
    args = parser.parse_args()

    load_dotenv(ROOT_DIR / ".env")
    source_db = args.source_db or _env("DB_NAME")
    backup_file = (
        Path(args.backup_file) if args.backup_file else _latest_backup(source_db)
    )
    if not backup_file.exists():
        print(f"ERROR: archivo no encontrado: {backup_file}", file=sys.stderr)
        return 1

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    restore_db = f"{source_db}_restore_verify_{ts}"

    print("== Backup Restore Verify ==")
    print(f"  source_db   = {source_db}")
    print(f"  backup_file = {backup_file.name} ({backup_file.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"  restore_db  = {restore_db}")
    print(f"  mode        = {'docker' if args.docker else 'local'}")
    print()

    try:
        print("[1/4] Creando DB temporal...")
        _create_db(restore_db)

        print("[2/4] Restaurando backup...")
        if args.docker:
            _restore_docker(backup_file, restore_db, args.container)
        else:
            _restore_local(backup_file, restore_db)

        print("[3/4] Descubriendo tablas y comparando row counts...")
        tables = _discover_tables(source_db)
        if not tables:
            print("  WARN: no se encontraron tablas en la DB origen.")
            return 1

        rows = _compare_counts(source_db, restore_db, tables)
        ok = all(match for *_, match in rows)

        print()
        print(f"  {'Tabla':<35} {'Origen':>8} {'Restore':>8} {'Match':>6}")
        print(f"  {'-'*35} {'-'*8} {'-'*8} {'-'*6}")
        for table, src, rst, match in rows:
            mark = "OK" if match else "FAIL"
            print(f"  {table:<35} {src:>8} {rst:>8} {mark:>6}")

        print()
        print(f"  Tablas verificadas: {len(rows)}/{len(tables)}")
        mismatches = [t for t, s, r, m in rows if not m]
        if mismatches:
            print(f"  DISCREPANCIAS: {', '.join(mismatches)}")
        print(f"  Resultado: {'PASS' if ok else 'FAIL'}")

        return 0 if ok else 1

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    finally:
        if not args.no_cleanup:
            print()
            print("[4/4] Limpiando DB temporal...")
            try:
                _drop_db(restore_db)
                print(f"  DB '{restore_db}' eliminada.")
            except Exception as e:
                print(f"  WARN: no se pudo eliminar DB temporal: {e}")
        else:
            print(f"\n  DB temporal '{restore_db}' conservada para inspección.")


if __name__ == "__main__":
    raise SystemExit(main())
