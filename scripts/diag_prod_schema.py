"""Diagnóstico READ-ONLY del esquema de stock/cantidad en producción.

Imprime el tipo REAL (COLUMN_TYPE de information_schema) de las columnas clave
de stock/cantidad en la BD viva. Sirve para confirmar si la migración
``z1a2b3c4`` (Numeric(10,4) → Numeric(18,4)) efectivamente amplió las columnas
en prod. NO escribe nada: solo lee information_schema.

Uso (dentro del contenedor de la app):
    python /app/scripts/diag_prod_schema.py
"""
import asyncio
import os

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
            "ORDER BY p.branch_id ASC, p.purchase_price * p.stock DESC "
            "LIMIT 60"
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

        # Unidades con decimales por empresa/sucursal: confirma si el auto-seed
        # (kg/g/l/ml/m/cm) corrió. Si una empresa no las tiene, hay que sembrar.
        units_sql = text(
            "SELECT company_id, branch_id, "
            "  GROUP_CONCAT(name ORDER BY name SEPARATOR ',') AS decimales "
            "FROM unit WHERE allows_decimal = 1 "
            "GROUP BY company_id, branch_id ORDER BY company_id, branch_id"
        )
        units = (await conn.execute(units_sql)).all()
        print("[diag] --- Unidades DECIMALES por sucursal ---", flush=True)
        for cid, bid, names in units:
            print(f"[diag] unidades emp={cid} suc={bid}: {names}", flush=True)

        # AUDITORÍA de unidades: productos con stock fraccionario (parte decimal
        # != 0) cuya unidad NO permite decimales -> candidatos a "unidad mal
        # importada" (deberían ser kg/ml/L). Muestra el desajuste sin tocar nada.
        audit_sql = text(
            "SELECT p.company_id, p.branch_id, p.barcode, p.description, "
            "       p.unit, p.stock, "
            "       COALESCE(u.allows_decimal, 0) AS unit_allows_decimal "
            "FROM product p "
            "LEFT JOIN unit u "
            "  ON u.name = p.unit AND u.company_id = p.company_id "
            "     AND u.branch_id = p.branch_id "
            "WHERE p.is_active = 1 AND p.stock <> TRUNCATE(p.stock, 0) "
            "ORDER BY p.company_id, p.branch_id, p.description "
            "LIMIT 100"
        )
        audit = (await conn.execute(audit_sql)).all()
        n_mismatch = sum(1 for r in audit if not r[6])
        print(
            f"[diag] === AUDITORÍA unidades: {len(audit)} productos con stock "
            f"decimal; {n_mismatch} con unidad ENTERA (posible unidad mal puesta) ===",
            flush=True,
        )
        for cid, bid, bc, desc, unit, stock, allows in audit:
            flag = "" if allows else "  <<< unidad entera con stock decimal"
            print(
                f"[diag] audit emp={cid} suc={bid} '{desc}' cod={bc} "
                f"unit={unit} allows_dec={int(allows)} stock={stock}{flag}",
                flush=True,
            )

        # Historial de un producto puntual (si se pasa DIAG_BARCODE): stock por
        # sucursal + últimos movimientos de kardex. Sirve para explicar por qué
        # un producto quedó en cierto stock.
        barcode = (os.environ.get("DIAG_BARCODE") or "").strip()
        if barcode:
            print(f"[diag] === HISTORIAL producto cod={barcode} ===", flush=True)
            stock_rows = (await conn.execute(
                text(
                    "SELECT p.id, p.company_id, p.branch_id, p.description, "
                    "       p.unit, p.stock, p.is_active "
                    "FROM product p WHERE p.barcode = :bc "
                    "ORDER BY p.company_id, p.branch_id"
                ).bindparams(bc=barcode)
            )).all()
            for pid, cid, bid, desc, unit, stock, active in stock_rows:
                print(
                    f"[diag] prod id={pid} emp={cid} suc={bid} '{desc}' unit={unit} "
                    f"stock={stock} activo={active}",
                    flush=True,
                )
            mov_rows = (await conn.execute(
                text(
                    "SELECT sm.branch_id, sm.type, sm.quantity, sm.description, "
                    "       sm.timestamp "
                    "FROM stockmovement sm JOIN product p ON p.id = sm.product_id "
                    "WHERE p.barcode = :bc "
                    "ORDER BY sm.timestamp DESC, sm.id DESC LIMIT 20"
                ).bindparams(bc=barcode)
            )).all()
            print(f"[diag] movimientos (últimos {len(mov_rows)}):", flush=True)
            for bid, mtype, qty, mdesc, ts in mov_rows:
                print(
                    f"[diag] mov suc={bid} {ts} tipo='{mtype}' cant={qty} :: {mdesc}",
                    flush=True,
                )
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
