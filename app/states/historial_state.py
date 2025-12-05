import reflex as rx
from typing import List, Dict, Any
import datetime
import logging
import io
from sqlmodel import select, or_
from sqlalchemy.orm import selectinload
from app.models import Sale, SaleItem, StockMovement, Product, User as UserModel, CashboxLog
from .types import Movement
from .mixin_state import MixinState
from app.utils.exports import create_excel_workbook, style_header_row, add_data_rows, auto_adjust_column_widths

class HistorialState(MixinState):
    # history: List[Movement] = [] # Removed in favor of DB
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
        
        movements = []
        
        with rx.session() as session:
            # 1. Fetch Sales
            sales_query = select(Sale, UserModel).join(UserModel, isouter=True).options(
                selectinload(Sale.items).selectinload(SaleItem.product)
            )
            
            if self.history_filter_start_date:
                try:
                    start_date = datetime.datetime.fromisoformat(self.history_filter_start_date)
                    sales_query = sales_query.where(Sale.timestamp >= start_date)
                except ValueError: pass
            if self.history_filter_end_date:
                try:
                    end_date = datetime.datetime.fromisoformat(self.history_filter_end_date)
                    # Add one day to include the end date fully if it's just a date
                    # But input is usually date string.
                    # Assuming format YYYY-MM-DD
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                    sales_query = sales_query.where(Sale.timestamp <= end_date)
                except ValueError: pass
                
            sales_results = session.exec(sales_query).all()
            
            for sale, user in sales_results:
                # Eager load items if possible, or just access them (lazy load)
                sale_items = sale.items
                
                # Filter by product
                if self.history_filter_product:
                    sale_items = [i for i in sale_items if self.history_filter_product.lower() in i.product_name_snapshot.lower()]
                    if not sale_items:
                        continue
                
                for item in sale_items:
                    unit = "Global"
                    if item.product:
                        unit = item.product.unit
                    
                    movements.append({
                        "id": f"{sale.id}-{item.id}",
                        "timestamp": sale.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "type": "Venta",
                        "product_description": item.product_name_snapshot,
                        "quantity": item.quantity,
                        "unit": unit,
                        "total": item.subtotal,
                        "payment_method": sale.payment_method,
                        "payment_details": sale.payment_details,
                        "user": user.username if user else "Desconocido",
                        "sale_id": str(sale.id)
                    })

            # 2. Fetch Stock Movements
            stock_query = select(StockMovement, Product, UserModel).join(Product).join(UserModel, isouter=True)
            
            if self.history_filter_start_date:
                try:
                    start_date = datetime.datetime.fromisoformat(self.history_filter_start_date)
                    stock_query = stock_query.where(StockMovement.timestamp >= start_date)
                except ValueError: pass
            if self.history_filter_end_date:
                try:
                    end_date = datetime.datetime.fromisoformat(self.history_filter_end_date)
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                    stock_query = stock_query.where(StockMovement.timestamp <= end_date)
                except ValueError: pass
            
            if self.history_filter_product:
                stock_query = stock_query.where(Product.description.ilike(f"%{self.history_filter_product}%"))
                
            stock_results = session.exec(stock_query).all()
            
            for mov, prod, user in stock_results:
                movements.append({
                    "id": str(mov.id),
                    "timestamp": mov.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "type": mov.type,
                    "product_description": f"{prod.description} ({mov.description})",
                    "quantity": mov.quantity,
                    "unit": prod.unit,
                    "total": 0,
                    "payment_method": "-",
                    "payment_details": mov.description,
                    "user": user.username if user else "Desconocido",
                    "sale_id": ""
                })

            # 3. Fetch Cashbox Logs
            # Only if no product filter is active, as logs don't have products
            if not self.history_filter_product:
                log_query = select(CashboxLog, UserModel).join(UserModel, isouter=True)
                if self.history_filter_start_date:
                    try:
                        start_date = datetime.datetime.fromisoformat(self.history_filter_start_date)
                        log_query = log_query.where(CashboxLog.timestamp >= start_date)
                    except ValueError: pass
                if self.history_filter_end_date:
                    try:
                        end_date = datetime.datetime.fromisoformat(self.history_filter_end_date)
                        end_date = end_date.replace(hour=23, minute=59, second=59)
                        log_query = log_query.where(CashboxLog.timestamp <= end_date)
                    except ValueError: pass
                
                log_results = session.exec(log_query).all()
                for log, user in log_results:
                    movements.append({
                        "id": str(log.id),
                        "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "type": log.action.capitalize(),
                        "product_description": log.notes,
                        "quantity": 0,
                        "unit": "-",
                        "total": log.amount,
                        "payment_method": "Efectivo",
                        "payment_details": log.notes,
                        "user": user.username if user else "Desconocido",
                        "sale_id": ""
                    })

        # Filter by type if needed
        if self.history_filter_type != "Todos":
            movements = [m for m in movements if m["type"] == self.history_filter_type]
            
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

    def _parse_payment_amount(self, text: str, keyword: str) -> float:
        """Extract amount for a keyword from a mixed payment string like 'Efectivo S/ 15.00'."""
        import re
        # Regex to find "Keyword S/ 123.45" or "Keyword (Type) S/ 123.45"
        # We look for the keyword, optional text, "S/", then the number.
        # Example: "Plin S/ 20.00" -> matches "Plin"
        try:
            # Case insensitive search for keyword followed by S/ and number
            # We assume the format generated in venta_state.py: f"{label} {self._format_currency(amount)}"
            # _format_currency uses "S/ {:,.2f}"
            
            # Simple approach: split by "/" or " - " and look for keyword
            parts = re.split(r'[:/|]|\s-\s', text)
            for part in parts:
                if keyword.lower() in part.lower() and "S/" in part:
                    # Extract number
                    num_part = part.split("S/")[1].strip()
                    # Remove commas if any (though format_currency might add them)
                    num_part = num_part.replace(",", "")
                    # Extract first valid float
                    match = re.search(r"([0-9]+\.?[0-9]*)", num_part)
                    if match:
                        return float(match.group(1))
        except Exception:
            pass
        return 0.0

    @rx.var
    def payment_stats(self) -> Dict[str, float]:
        stats = {
            "efectivo": 0.0,
            "yape": 0.0,
            "plin": 0.0,
            "tarjeta": 0.0,
            "mixto": 0.0
        }
        
        with rx.session() as session:
            # Apply same date filters as history list for consistency
            query = select(Sale).where(Sale.is_deleted == False)
            
            if self.history_filter_start_date:
                try:
                    start_date = datetime.datetime.fromisoformat(self.history_filter_start_date)
                    query = query.where(Sale.timestamp >= start_date)
                except ValueError: pass
            if self.history_filter_end_date:
                try:
                    end_date = datetime.datetime.fromisoformat(self.history_filter_end_date)
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                    query = query.where(Sale.timestamp <= end_date)
                except ValueError: pass
                
            sales = session.exec(query).all()
            
            for sale in sales:
                method = (sale.payment_method or "").lower()
                details = (sale.payment_details or "")
                total = sale.total_amount
                
                # Check for Mixed Payment first
                if "mixto" in method:
                    stats["mixto"] += total
                    # Parse breakdown
                    stats["efectivo"] += self._parse_payment_amount(details, "Efectivo")
                    stats["yape"] += self._parse_payment_amount(details, "Yape")
                    stats["plin"] += self._parse_payment_amount(details, "Plin")
                    stats["tarjeta"] += self._parse_payment_amount(details, "Tarjeta")
                    # Note: We add to both "mixto" (total) and specific methods (parts).
                    continue

                # Single Payment Methods
                if "efectivo" in method:
                    stats["efectivo"] += total
                elif "yape" in method or "yape" in details.lower():
                    stats["yape"] += total
                elif "plin" in method or "plin" in details.lower():
                    stats["plin"] += total
                elif "tarjeta" in method or "tarjeta" in details.lower():
                    stats["tarjeta"] += total
                else:
                    # Fallback for generic "Billetera" if not caught above
                    if "billetera" in method:
                        # If details specify provider, we might have caught it. If not, where does it go?
                        # For now, if it's not Yape/Plin, maybe it's another wallet.
                        pass

        return {k: self._round_currency(v) for k, v in stats.items()}

    @rx.var
    def total_ventas_efectivo(self) -> float:
        return self.payment_stats["efectivo"]

    @rx.var
    def total_ventas_yape(self) -> float:
        return self.payment_stats["yape"]

    @rx.var
    def total_ventas_plin(self) -> float:
        return self.payment_stats["plin"]

    @rx.var
    def total_ventas_tarjeta(self) -> float:
        return self.payment_stats["tarjeta"]

    @rx.var
    def total_ventas_mixtas(self) -> float:
        return self.payment_stats["mixto"]

    @rx.var
    def productos_mas_vendidos(self) -> list[dict]:
        import sqlalchemy
        from sqlmodel import desc
        with rx.session() as session:
            statement = select(
                SaleItem.product_name_snapshot, 
                sqlalchemy.func.sum(SaleItem.quantity).label("total_qty")
            ).group_by(SaleItem.product_name_snapshot).order_by(desc("total_qty")).limit(5)
            
            results = session.exec(statement).all()
            return [
                {"description": name, "cantidad_vendida": qty} for name, qty in results
            ]

    @rx.var
    def productos_stock_bajo(self) -> list[Dict]:
        with rx.session() as session:
            products = session.exec(select(Product).where(Product.stock <= 10).order_by(Product.stock)).all()
            return [
                {
                    "barcode": p.barcode,
                    "description": p.description,
                    "stock": p.stock,
                    "unit": p.unit
                }
                for p in products
            ]

    @rx.var
    def sales_by_day(self) -> list[dict]:
        from collections import defaultdict
        with rx.session() as session:
            sales = session.exec(select(Sale).where(Sale.is_deleted == False)).all()
            daily_sales = defaultdict(float)
            for sale in sales:
                date_str = sale.timestamp.strftime("%Y-%m-%d")
                daily_sales[date_str] += sale.total_amount
            
            sorted_days = sorted(daily_sales.keys())[-7:]
            return [{"date": day, "total": daily_sales[day]} for day in sorted_days]
