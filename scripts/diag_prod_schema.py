"""Diagnóstico READ-ONLY del esquema de stock/cantidad en producción.

Imprime el tipo REAL (COLUMN_TYPE de information_schema) de las columnas clave
de stock/cantidad en la BD viva. Sirve para confirmar si la migración
``z1a2b3c4`` (Numeric(10,4) → Numeric(18,4)) efectivamente amplió las columnas
en prod. NO escribe nada: solo lee information_schema.

Uso (dentro del contenedor de la app):
    python /app/scripts/diag_prod_schema.py
"""
import asyncio

from sqlalchemy import text

from app.utils.db import async_engine

# (tabla, columna) que la migración z1a2b3c4 debía ampliar a decimal(18,4).
TARGETS = [
    ("product", "stock"),
    ("product", "min_stock_alert"),
    ("productvariant", "stock"),
    ("productbatch", "stock"),
    ("stockmovement", "quantity"),
    ("saleitem", "quantity"),
]


async def main() -> None:
    conds = " OR ".join(
        f"(TABLE_NAME='{t}' AND COLUMN_NAME='{c}')" for t, c in TARGETS
    )
    sql = (
        "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE "
        "FROM information_schema.COLUMNS "
        f"WHERE TABLE_SCHEMA = DATABASE() AND ({conds}) "
        "ORDER BY TABLE_NAME, COLUMN_NAME"
    )
    async with async_engine.connect() as conn:
        db = (await conn.execute(text("SELECT DATABASE()"))).scalar()
        print(f"[diag] DATABASE()={db}", flush=True)
        rows = (await conn.execute(text(sql))).all()
        widened = 0
        for table, column, col_type in rows:
            is_18 = "18,4" in col_type.replace(" ", "")
            widened += int(is_18)
            flag = "OK-18,4" if is_18 else ">>> AUN 10,4 <<<"
            print(f"[diag] {table}.{column} = {col_type}  {flag}", flush=True)
        print(
            f"[diag] RESUMEN: {widened}/{len(rows)} columnas objetivo en decimal(18,4)",
            flush=True,
        )
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
