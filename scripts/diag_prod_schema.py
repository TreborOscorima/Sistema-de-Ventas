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

        # Productos activos con stock residual (>0): para explicar cards como
        # "Stock Bajo" / "Valor Inventario" tras una transferencia de "todo el
        # stock". Reporta el stock del padre vs la SUMA de sus variantes — si
        # difieren, el padre tiene un agregado fantasma que "agregar todo" no
        # mueve (solo mueve variantes con stock > 0).
        residual_sql = text(
            "SELECT p.company_id, p.branch_id, p.barcode, p.description, "
            "       p.unit, p.stock AS parent_stock, p.min_stock_alert, "
            "       p.purchase_price, "
            "       (SELECT COUNT(*) FROM productvariant v "
            "          WHERE v.product_id = p.id AND v.branch_id = p.branch_id) AS n_variants, "
            "       (SELECT COALESCE(SUM(v.stock),0) FROM productvariant v "
            "          WHERE v.product_id = p.id AND v.branch_id = p.branch_id) AS variants_sum "
            "FROM product p "
            "WHERE p.is_active = 1 AND p.stock > 0 "
            "ORDER BY p.purchase_price * p.stock DESC "
            "LIMIT 25"
        )
        # Resumen por sucursal: cuántos productos activos con stock>0 y valor
        # total. Revela cuál es el origen (pocos/1 residual) vs el destino.
        branch_summary_sql = text(
            "SELECT p.company_id, p.branch_id, "
            "       COUNT(*) AS n_con_stock, "
            "       SUM(p.purchase_price * p.stock) AS valor "
            "FROM product p "
            "WHERE p.is_active = 1 AND p.stock > 0 "
            "GROUP BY p.company_id, p.branch_id "
            "ORDER BY p.company_id, p.branch_id"
        )
        summ = (await conn.execute(branch_summary_sql)).all()
        print("[diag] --- RESUMEN por sucursal (activos con stock>0) ---", flush=True)
        for cid, bid, n, val in summ:
            print(f"[diag] sucursal emp={cid} suc={bid}: {n} productos con stock, valor={val}", flush=True)

        residuals = (await conn.execute(residual_sql)).all()
        print(f"[diag] PRODUCTOS ACTIVOS CON STOCK>0 (top 25 por valor): {len(residuals)}", flush=True)
        for r in residuals:
            (cid, bid, bc, desc, unit, pstock, minalert, pprice,
             nvar, vsum) = r
            drift = ""
            if nvar and str(pstock) != str(vsum):
                drift = f"  <<< DRIFT padre={pstock} != sum_variantes={vsum} >>>"
            print(
                f"[diag] resid emp={cid} suc={bid} '{desc}' cod={bc} unit={unit} "
                f"stock={pstock} min={minalert} pcompra={pprice} "
                f"variantes={nvar}{drift}",
                flush=True,
            )
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
