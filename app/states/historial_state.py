import reflex as rx
from typing import List, Dict, Any
import datetime
import logging
import io
from .types import Movement, Product
from .mixin_state import MixinState
from app.utils.exports import create_excel_workbook, style_header_row, add_data_rows, auto_adjust_column_widths

class HistorialState(MixinState):
    history: List[Movement] = []
    history_filter_type: str = "Todos"
    history_filter_product: str = ""
    history_filter_start_date: str = ""
    history_filter_end_date: str = ""
    staged_history_filter_type: str = "Todos"
    staged_history_filter_product: str = ""
    staged_history_filter_start_date: str = ""
    staged_history_filter_end_date: str = ""
    current_page_history: int = 1
    items_per_page: int = 10

    @rx.var
    def filtered_history(self) -> list[Movement]:
        if not self.current_user["privileges"]["view_historial"]:
            return []
        movements = self.history
        if self.history_filter_type != "Todos":
            movements = [m for m in movements if m["type"] == self.history_filter_type]
        if self.history_filter_product:
            movements = [
                m
                for m in movements
                if self.history_filter_product.lower()
                in m["product_description"].lower()
            ]
        if self.history_filter_start_date:
            try:
                start_date = datetime.datetime.fromisoformat(
                    self.history_filter_start_date
                )
                movements = [
                    m
                    for m in movements
                    if datetime.datetime.fromisoformat(m["timestamp"].split()[0])
                    >= start_date
                ]
            except ValueError as e:
                logging.exception(f"Error parsing start date: {e}")
        if self.history_filter_end_date:
            try:
                end_date = datetime.datetime.fromisoformat(self.history_filter_end_date)
                movements = [
                    m
                    for m in movements
                    if datetime.datetime.fromisoformat(m["timestamp"].split()[0])
                    <= end_date
                ]
            except ValueError as e:
                logging.exception(f"Error parsing end date: {e}")
        return sorted(movements, key=lambda m: m["timestamp"], reverse=True)

    @rx.var
    def paginated_history(self) -> list[Movement]:
        start_index = (self.current_page_history - 1) * self.items_per_page
        end_index = start_index + self.items_per_page
        return self.filtered_history[start_index:end_index]

    @rx.var
    def total_pages(self) -> int:
        total_items = len(self.filtered_history)
        if total_items == 0:
            return 1
        return (total_items + self.items_per_page - 1) // self.items_per_page

    @rx.event
    def set_history_page(self, page_num: int):
        if 1 <= page_num <= self.total_pages:
            self.current_page_history = page_num

    @rx.event
    def apply_history_filters(self):
        self.history_filter_type = self.staged_history_filter_type
        self.history_filter_product = self.staged_history_filter_product
        self.history_filter_start_date = self.staged_history_filter_start_date
        self.history_filter_end_date = self.staged_history_filter_end_date
        self.current_page_history = 1

    @rx.event
    def reset_history_filters(self):
        self.staged_history_filter_type = "Todos"
        self.staged_history_filter_product = ""
        self.staged_history_filter_start_date = ""
        self.staged_history_filter_end_date = ""
        self.apply_history_filters()

    @rx.event
    def set_staged_history_filter_type(self, value: str):
        self.staged_history_filter_type = value or "Todos"

    @rx.event
    def set_staged_history_filter_product(self, value: str):
        self.staged_history_filter_product = value or ""

    @rx.event
    def set_staged_history_filter_start_date(self, value: str):
        self.staged_history_filter_start_date = value or ""

    @rx.event
    def set_staged_history_filter_end_date(self, value: str):
        self.staged_history_filter_end_date = value or ""

    @rx.event
    def export_to_excel(self):
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)
        
        wb, ws = create_excel_workbook("Historial Movimientos")
        
        headers = [
            "Fecha y Hora",
            "Tipo",
            "Descripcion",
            "Cantidad",
            "Unidad",
            "Total",
            "Metodo de Pago",
            "Detalle Pago",
        ]
        style_header_row(ws, 1, headers)
        
        rows = []
        for movement in self.filtered_history:
            method_display = self._normalize_wallet_label(
                movement.get("payment_method", "")
            )
            rows.append([
                movement["timestamp"],
                movement["type"],
                movement["product_description"],
                movement["quantity"],
                movement["unit"],
                movement["total"],
                method_display,
                movement.get("payment_details", ""),
            ])
            
        add_data_rows(ws, rows, 2)
        auto_adjust_column_widths(ws)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return rx.download(data=output.getvalue(), filename="historial_movimientos.xlsx")

    def _ventas_by_payment(self, match_fn) -> float:
        sales = [m for m in self.history if m["type"] == "Venta"]
        total = 0.0
        for m in sales:
            if match_fn(m):
                total += m["total"]
        return self._round_currency(total)

    @rx.var
    def total_ventas_efectivo(self) -> float:
        return self._ventas_by_payment(
            lambda m: m.get("payment_kind") == "cash"
            or m.get("payment_method", "").lower() == "efectivo"
        )

    @rx.var
    def total_ventas_yape(self) -> float:
        return self._ventas_by_payment(
            lambda m: m.get("payment_method", "").lower()
            == "pago qr / billetera digital"
            and "yape" in m.get("payment_details", "").lower()
            or (
                m.get("payment_kind") == "wallet"
                and "yape" in m.get("payment_details", "").lower()
            )
        )

    @rx.var
    def total_ventas_plin(self) -> float:
        return self._ventas_by_payment(
            lambda m: m.get("payment_method", "").lower()
            == "pago qr / billetera digital"
            and "plin" in m.get("payment_details", "").lower()
            or (
                m.get("payment_kind") == "wallet"
                and "plin" in m.get("payment_details", "").lower()
            )
        )

    @rx.var
    def total_ventas_mixtas(self) -> float:
        return self._ventas_by_payment(
            lambda m: m.get("payment_kind") == "mixed"
            or m.get("payment_method", "").lower() == "pagos mixtos"
        )

    @rx.var
    def productos_mas_vendidos(self) -> list[dict]:
        from collections import Counter

        sales = [m for m in self.history if m["type"] == "Venta"]
        product_counts = Counter((m["product_description"] for m in sales))
        top_products = product_counts.most_common(5)
        return [
            {"description": desc, "cantidad_vendida": qty} for desc, qty in top_products
        ]

    @rx.var
    def productos_stock_bajo(self) -> list[Product]:
        if hasattr(self, "inventory"):
            return sorted(
                [p for p in self.inventory.values() if p["stock"] <= 10],
                key=lambda p: p["stock"],
            )
        return []

    @rx.var
    def sales_by_day(self) -> list[dict]:
        from collections import defaultdict
        
        sales = [m for m in self.history if m["type"] == "Venta"]
        daily_sales = defaultdict(float)
        for m in sales:
            date = m["timestamp"].split(" ")[0]
            daily_sales[date] += m["total"]
        
        sorted_days = sorted(daily_sales.keys())[-7:]
        return [{"date": day, "total": daily_sales[day]} for day in sorted_days]
