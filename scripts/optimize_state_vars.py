"""
Script para eliminar duplicación de datos en el delta WebSocket de Reflex.

Problema: Cada lista/dict se envía 2-3 veces al frontend porque:
  1. `xxx_cache` (var pública) → se serializa en el delta
  2. `@rx.var def xxx(): return self.xxx_cache` → se recalcula y se incluye también
  3. (a veces) `@rx.var def paginated_xxx(): return self.xxx` → tercera copia

Solución: renombrar `xxx_cache` → `xxx` y eliminar el @rx.var pass-through.
El frontend ya usa `State.xxx` (el nombre del @rx.var), así que sigue funcionando.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ──────────────────────────────────────────────────────────────────
# Configuración por archivo: lista de (cache_var, computed_var_name)
# ──────────────────────────────────────────────────────────────────

FILES_CONFIG = {
    "app/states/cash_state.py": {
        "renames": [
            ("petty_cash_movements_cache", "petty_cash_movements"),
            ("petty_cash_total_pages_cache", "petty_cash_total_pages"),
            ("current_cashbox_session_cache", "current_cashbox_session"),
            ("cashbox_opening_amount_cache", "cashbox_opening_amount"),
            ("filtered_cashbox_logs_cache", "filtered_cashbox_logs"),
            ("cashbox_log_total_pages_cache", "cashbox_log_total_pages"),
            ("filtered_cashbox_sales_cache", "filtered_cashbox_sales"),
            ("cashbox_total_pages_cache", "cashbox_total_pages"),
        ],
        "delete_proxies": [
            "petty_cash_movements",
            "petty_cash_total_pages",
            "current_cashbox_session",
            "cashbox_opening_amount",
            "filtered_cashbox_logs",
            "cashbox_log_total_pages",
            "filtered_cashbox_sales",
            "cashbox_total_pages",
            # secondary proxies:
            "paginated_petty_cash_movements",
            "paginated_cashbox_logs",
            "paginated_cashbox_sales",
        ],
    },
    "app/states/historial_state.py": {
        "renames": [
            ("filtered_history_cache", "filtered_history"),
            ("total_pages_cache", "total_pages"),
            ("report_method_summary_cache", "report_method_summary"),
            ("report_detail_rows_cache", "report_detail_rows"),
            ("report_closing_rows_cache", "report_closing_rows"),
            ("payment_stats_cache", "payment_stats"),
            ("total_credit_cache", "total_credit"),
            ("credit_outstanding_cache", "credit_outstanding"),
            ("dynamic_payment_cards_cache", "dynamic_payment_cards"),
            ("productos_mas_vendidos_cache", "productos_mas_vendidos"),
            ("productos_stock_bajo_cache", "productos_stock_bajo"),
            ("sales_by_day_cache", "sales_by_day"),
        ],
        "delete_proxies": [
            "filtered_history",
            "total_pages",
            "report_method_summary",
            "report_detail_rows",
            "report_closing_rows",
            "payment_stats",
            "total_credit",
            "credit_outstanding",
            "dynamic_payment_cards",
            "productos_mas_vendidos",
            "productos_stock_bajo",
            "sales_by_day",
            # secondary:
            "paginated_history",
        ],
    },
    "app/states/inventory_state.py": {
        "renames": [
            ("inventory_list_cache", "inventory_list"),
            ("inventory_total_pages_cache", "inventory_total_pages"),
            ("inventory_total_products_cache", "inventory_total_products"),
            ("inventory_in_stock_count_cache", "inventory_in_stock_count"),
            ("inventory_low_stock_count_cache", "inventory_low_stock_count"),
            ("inventory_out_of_stock_count_cache", "inventory_out_of_stock_count"),
        ],
        "delete_proxies": [
            "inventory_list",
            "inventory_total_pages",
            "inventory_total_products",
            "inventory_in_stock_count",
            "inventory_low_stock_count",
            "inventory_out_of_stock_count",
            # secondary:
            "inventory_paginated_list",
        ],
    },
    "app/states/purchases_state.py": {
        "renames": [
            ("purchase_records_cache", "purchase_records"),
            ("purchase_total_pages_cache", "purchase_total_pages"),
        ],
        "delete_proxies": [
            "purchase_records",
            "purchase_total_pages",
        ],
    },
}


def delete_rx_var_proxy(content: str, func_name: str) -> str:
    """Elimina un @rx.var(cache=True) function completo (decorador + def + body)."""
    # Pattern matches:
    #   @rx.var(cache=True)
    #   def func_name(self) -> ReturnType:
    #       return self.something
    #   (optional blank line)
    pattern = (
        r'\n    @rx\.var\(cache=True\)\n'
        r'    def ' + re.escape(func_name) + r'\(self\)[^:]*:\n'
        r'(?:        [^\n]*\n)+'
        r'(?:\n(?=    [@\w]|\n|\Z))?'
    )
    new_content = re.sub(pattern, '\n', content)
    if new_content == content:
        # Try alternate pattern (could be at start of methods section, different indentation)
        pattern2 = (
            r'    @rx\.var\(cache=True\)\n'
            r'    def ' + re.escape(func_name) + r'\(self\)[^:]*:\n'
            r'(?:        [^\n]*\n)+'
        )
        new_content = re.sub(pattern2, '', content)
    if new_content == content:
        print(f"  ⚠ No se encontró @rx.var proxy: {func_name}", file=sys.stderr)
    else:
        print(f"  ✓ Eliminado @rx.var proxy: {func_name}")
    return new_content


def process_file(rel_path: str, config: dict) -> tuple[int, int]:
    """Procesa un archivo: elimina proxies y renombra cache vars."""
    filepath = ROOT / rel_path
    if not filepath.exists():
        print(f"❌ Archivo no encontrado: {filepath}", file=sys.stderr)
        return 0, 0

    content = filepath.read_text(encoding="utf-8")
    original = content

    print(f"\n{'='*60}")
    print(f"Procesando: {rel_path}")
    print(f"{'='*60}")

    # Paso 1: Eliminar @rx.var pass-through proxies
    proxies_deleted = 0
    for proxy_name in config["delete_proxies"]:
        old_len = len(content)
        content = delete_rx_var_proxy(content, proxy_name)
        if len(content) != old_len:
            proxies_deleted += 1

    # Paso 2: Renombrar xxx_cache → xxx
    renames_done = 0
    for old_name, new_name in config["renames"]:
        count = content.count(old_name)
        if count > 0:
            content = content.replace(old_name, new_name)
            renames_done += count
            print(f"  ✓ Renombrado '{old_name}' → '{new_name}' ({count} ocurrencias)")
        else:
            print(f"  ⚠ No se encontró '{old_name}'", file=sys.stderr)

    if content != original:
        filepath.write_text(content, encoding="utf-8")
        print(f"\n  📝 Archivo guardado. Proxies eliminados: {proxies_deleted}, Renames: {renames_done}")
    else:
        print(f"\n  ℹ Sin cambios")

    return proxies_deleted, renames_done


def main():
    total_proxies = 0
    total_renames = 0
    for rel_path, config in FILES_CONFIG.items():
        p, r = process_file(rel_path, config)
        total_proxies += p
        total_renames += r

    print(f"\n{'='*60}")
    print(f"RESUMEN: {total_proxies} proxies eliminados, {total_renames} renames aplicados")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
