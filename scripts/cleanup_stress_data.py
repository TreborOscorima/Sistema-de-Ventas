"""
Limpia registros de stress (empresas STRESS-*) en la BD actual.

Uso:
  python scripts/cleanup_stress_data.py
"""
from __future__ import annotations

import os
import re
from urllib.parse import quote_plus

import asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _load_env(path: str) -> None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), _strip_quotes(value.strip()))
    except FileNotFoundError:
        pass


def _build_db_url() -> str:
    _load_env(".env")
    user = quote_plus(os.environ["DB_USER"])
    password = quote_plus(os.environ["DB_PASSWORD"])
    host = os.environ["DB_HOST"]
    port = os.environ.get("DB_PORT", "3306")
    db = os.environ["DB_NAME"]
    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{db}"


async def main() -> None:
    db_url = _build_db_url()
    url = make_url(db_url)
    schema = url.database
    if not schema:
        raise RuntimeError("No se pudo determinar el schema de la BD.")

    engine = create_async_engine(db_url, pool_pre_ping=True)

    async with engine.connect() as conn:
        # Encontrar empresas STRESS-*
        stress_ids = (
            await conn.execute(
                text(
                    "SELECT id FROM company "
                    "WHERE name LIKE 'STRESS-%' OR ruc LIKE 'STRESS%'"
                )
            )
        ).scalars().all()

        if not stress_ids:
            print("No hay empresas STRESS-* para limpiar.")
            await engine.dispose()
            return

        branch_ids = (
            await conn.execute(
                text(
                    "SELECT id FROM branch WHERE company_id IN :company_ids"
                ),
                {"company_ids": tuple(stress_ids)},
            )
        ).scalars().all()

        # Listar tablas con company_id/branch_id
        columns = (
            await conn.execute(
                text(
                    "SELECT table_name, column_name "
                    "FROM information_schema.columns "
                    "WHERE table_schema = :schema "
                    "AND column_name IN ('company_id', 'branch_id')"
                ),
                {"schema": schema},
            )
        ).all()

        tables: dict[str, set[str]] = {}
        for table_name, column_name in columns:
            if not re.fullmatch(r"[A-Za-z0-9_]+", table_name or ""):
                continue
            tables.setdefault(table_name, set()).add(column_name)

        # Excluir tablas que no deben tocarse
        tables.pop("alembic_version", None)

        # Desactivar checks FK para limpieza segura
        await conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        try:
            for table, cols in tables.items():
                if table in {"company", "branch"}:
                    continue
                if "company_id" in cols and stress_ids:
                    await conn.execute(
                        text(f"DELETE FROM `{table}` WHERE company_id IN :company_ids"),
                        {"company_ids": tuple(stress_ids)},
                    )
                elif "branch_id" in cols and branch_ids:
                    await conn.execute(
                        text(f"DELETE FROM `{table}` WHERE branch_id IN :branch_ids"),
                        {"branch_ids": tuple(branch_ids)},
                    )

            if branch_ids:
                await conn.execute(
                    text("DELETE FROM branch WHERE id IN :branch_ids"),
                    {"branch_ids": tuple(branch_ids)},
                )
            await conn.execute(
                text("DELETE FROM company WHERE id IN :company_ids"),
                {"company_ids": tuple(stress_ids)},
            )
            await conn.commit()
        finally:
            await conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")

    await engine.dispose()
    print(f"Limpieza completada. Empresas eliminadas: {len(stress_ids)}")


if __name__ == "__main__":
    asyncio.run(main())
