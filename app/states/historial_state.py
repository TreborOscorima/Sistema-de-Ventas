import reflex as rx
from typing import List, Dict, Any
import datetime
import json
import logging
import io
from decimal import Decimal
from sqlmodel import select
import sqlalchemy as sa
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
    _history_update_trigger: int = 0

    def _history_union_subquery(self):
        search = (self.history_filter_product or "").strip()
        start_date = None
        end_date = None
        if self.history_filter_start_date:
            try:
                start_date = datetime.datetime.fromisoformat(
                    self.history_filter_start_date
                )
            except ValueError:
                start_date = None
        if self.history_filter_end_date:
            try:
                end_date = datetime.datetime.fromisoformat(self.history_filter_end_date)
                end_date = end_date.replace(hour=23, minute=59, second=59)
            except ValueError:
                end_date = None

        sales_query = (
            select(
                sa.cast(SaleItem.id, sa.String).label("id"),
                Sale.timestamp.label("timestamp"),
                sa.literal("Venta").label("type"),
                SaleItem.product_name_snapshot.label("product_description"),
                SaleItem.quantity.label("quantity"),
                sa.func.coalesce(Product.unit, sa.literal("Global")).label("unit"),
                SaleItem.subtotal.label("total"),
                sa.func.coalesce(Sale.payment_method, sa.literal("-")).label(
                    "payment_method"
                ),
                sa.cast(Sale.payment_details, sa.String).label("payment_details"),
                sa.func.coalesce(UserModel.username, sa.literal("Desconocido")).label(
                    "user"
                ),
                sa.cast(Sale.id, sa.String).label("sale_id"),
                sa.literal("sale").label("source"),
            )
            .select_from(SaleItem)
            .join(Sale)
            .join(Product, isouter=True)
            .join(UserModel, isouter=True)
        )

        stock_query = (
            select(
                sa.cast(StockMovement.id, sa.String).label("id"),
                StockMovement.timestamp.label("timestamp"),
                StockMovement.type.label("type"),
                sa.func.concat(
                    Product.description,
                    sa.literal(" ("),
                    StockMovement.description,
                    sa.literal(")"),
                ).label("product_description"),
                StockMovement.quantity.label("quantity"),
                Product.unit.label("unit"),
                sa.literal(0).label("total"),
                sa.literal("-").label("payment_method"),
                sa.cast(StockMovement.description, sa.String).label("payment_details"),
                sa.func.coalesce(UserModel.username, sa.literal("Desconocido")).label(
                    "user"
                ),
                sa.literal("").label("sale_id"),
                sa.literal("stock").label("source"),
            )
            .select_from(StockMovement)
            .join(Product)
            .join(UserModel, isouter=True)
        )

        log_query = (
            select(
                sa.cast(CashboxLog.id, sa.String).label("id"),
                CashboxLog.timestamp.label("timestamp"),
                CashboxLog.action.label("type"),
                CashboxLog.notes.label("product_description"),
                sa.literal(0).label("quantity"),
                sa.literal("-").label("unit"),
                CashboxLog.amount.label("total"),
                sa.literal("Efectivo").label("payment_method"),
                sa.cast(CashboxLog.notes, sa.String).label("payment_details"),
                sa.func.coalesce(UserModel.username, sa.literal("Desconocido")).label(
                    "user"
                ),
                sa.literal("").label("sale_id"),
                sa.literal("log").label("source"),
            )
            .select_from(CashboxLog)
            .join(UserModel, isouter=True)
        )

        if search:
            like_search = f"%{search}%"
            sales_query = sales_query.where(
                SaleItem.product_name_snapshot.ilike(like_search)
            )
            stock_query = stock_query.where(Product.description.ilike(like_search))

        if start_date:
            sales_query = sales_query.where(Sale.timestamp >= start_date)
            stock_query = stock_query.where(StockMovement.timestamp >= start_date)
            log_query = log_query.where(CashboxLog.timestamp >= start_date)

        if end_date:
            sales_query = sales_query.where(Sale.timestamp <= end_date)
            stock_query = stock_query.where(StockMovement.timestamp <= end_date)
            log_query = log_query.where(CashboxLog.timestamp <= end_date)

        queries = [sales_query, stock_query]
        if not search:
            queries.append(log_query)

        return sa.union_all(*queries).subquery()

    def _history_base_select(self):
        history_union = self._history_union_subquery()
        query = select(*history_union.c)
        if self.history_filter_type != "Todos":
            query = query.where(history_union.c.type == self.history_filter_type)
        query = query.order_by(history_union.c.timestamp.desc())
        return query, history_union

    def _history_row_to_movement(self, row) -> Movement:
        def _value(key: str, default: Any = None):
            if isinstance(row, dict):
                return row.get(key, default)
            if hasattr(row, key):
                return getattr(row, key)
            try:
                return row[key]
            except (KeyError, IndexError, TypeError):
                return default

        timestamp = _value("timestamp")
        movement_type = _value("type") or ""
        source = _value("source") or ""
        if source == "log":
            movement_type = movement_type.capitalize()
        movement_id = f"{source or 'row'}-{_value('id')}"
        payment_details = _value("payment_details")
        if isinstance(payment_details, str):
            stripped = payment_details.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    payment_details = json.loads(stripped)
                except json.JSONDecodeError:
                    pass
        return {
            "id": movement_id,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "",
            "type": movement_type,
            "product_description": _value("product_description") or "",
            "quantity": _value("quantity") or 0,
            "unit": _value("unit") or "-",
            "total": _value("total") or 0,
            "payment_method": _value("payment_method") or "-",
            "payment_details": self._payment_details_text(payment_details),
            "user": _value("user") or "Desconocido",
            "sale_id": _value("sale_id") or "",
        }

    def _fetch_history(self, offset: int | None = None, limit: int | None = None) -> list[Movement]:
        with rx.session() as session:
            query, _ = self._history_base_select()
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            rows = session.execute(query).all()
            return [self._history_row_to_movement(row) for row in rows]

    def _history_total_count(self) -> int:
        with rx.session() as session:
            history_union = self._history_union_subquery()
            count_query = select(sa.func.count()).select_from(history_union)
            if self.history_filter_type != "Todos":
                count_query = count_query.where(history_union.c.type == self.history_filter_type)
            return session.exec(count_query).one()

    @rx.var
    def filtered_history(self) -> list[Movement]:
        if not self.current_user["privileges"]["view_historial"]:
            return []
        
        # Dependency to force update
        _ = self._history_update_trigger
        offset = (self.current_page_history - 1) * self.items_per_page
        return self._fetch_history(offset=offset, limit=self.items_per_page)

    @rx.var
    def paginated_history(self) -> list[Movement]:
        return self.filtered_history

    @rx.var
    def total_pages(self) -> int:
        _ = self._history_update_trigger
        total_items = self._history_total_count()
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
        self._history_update_trigger += 1

    @rx.event
    def reload_history(self):
        self._history_update_trigger += 1
        # print("Reloading history...") # Debug

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
        for movement in self._fetch_history():
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
                self._payment_details_text(movement.get("payment_details", "")),
            ])
            
        add_data_rows(ws, rows, 2)
        auto_adjust_column_widths(ws)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return rx.download(data=output.getvalue(), filename="historial_movimientos.xlsx")

    def _parse_payment_amount(self, text: str, keyword: str) -> Decimal:
        """Extract amount for a keyword from a mixed payment string like 'Efectivo S/ 15.00'."""
        import re
        try:
            # Normalize separators.
            # DB format: "Pagos Mixtos - Efectivo S/ 15.00 / Plin S/ 20.00 / Montos completos."
            
            # Replace " / " (slash with spaces) with a pipe
            text = text.replace(" / ", "|")
            # Replace " - " (dash with spaces) with a pipe
            text = text.replace(" - ", "|")
            # Replace "/" (slash without spaces) just in case
            text = text.replace("/", "|")
            
            parts = text.split("|")
            
            for part in parts:
                part = part.strip()
                # Check for keyword and "S/"
                if keyword.lower() in part.lower() and "S/" in part:
                    try:
                        amount_str = part.split("S/")[1].strip()
                        # Extract number (handle commas and decimals)
                        match = re.search(r"([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)", amount_str)
                        if match:
                            num_str = match.group(1).replace(",", "")
                            return Decimal(num_str)
                    except IndexError:
                        continue
        except Exception:
            pass
        return Decimal("0.00")

    @rx.var
    def payment_stats(self) -> Dict[str, float]:
        # Dependency to force update
        _ = self._history_update_trigger

        stats = {
            "efectivo": Decimal("0.00"),
            "yape": Decimal("0.00"),
            "plin": Decimal("0.00"),
            "tarjeta": Decimal("0.00"),
            "mixto": Decimal("0.00"),
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
                details_raw = sale.payment_details
                details_text = self._payment_details_text(details_raw)
                details_lower = details_text.lower()
                total = sale.total_amount or Decimal("0.00")
                method_kind = ""
                breakdown = None
                if isinstance(details_raw, dict):
                    method_kind = (details_raw.get("method_kind") or "").lower()
                    if isinstance(details_raw.get("breakdown"), list):
                        breakdown = details_raw.get("breakdown")
                
                # Check for Mixed Payment first
                if "mixto" in method or method_kind == "mixed":
                    stats["mixto"] += total
                    if breakdown:
                        for item in breakdown:
                            label = (item.get("label") or "").lower()
                            amount = Decimal(str(item.get("amount", 0) or 0))
                            if "efectivo" in label:
                                stats["efectivo"] += amount
                            elif "yape" in label:
                                stats["yape"] += amount
                            elif "plin" in label:
                                stats["plin"] += amount
                            elif "tarjeta" in label:
                                stats["tarjeta"] += amount
                    else:
                        # Parse breakdown from legacy string
                        stats["efectivo"] += self._parse_payment_amount(details_text, "Efectivo")
                        stats["yape"] += self._parse_payment_amount(details_text, "Yape")
                        stats["plin"] += self._parse_payment_amount(details_text, "Plin")
                        stats["tarjeta"] += self._parse_payment_amount(details_text, "Tarjeta")
                    # Note: We add to both "mixto" (total) and specific methods (parts).
                    continue

                # Single Payment Methods
                if "efectivo" in method:
                    stats["efectivo"] += total
                elif "yape" in method or "yape" in details_lower:
                    stats["yape"] += total
                elif "plin" in method or "plin" in details_lower:
                    stats["plin"] += total
                elif "tarjeta" in method or "tarjeta" in details_lower:
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
            daily_sales = defaultdict(Decimal)
            for sale in sales:
                date_str = sale.timestamp.strftime("%Y-%m-%d")
                daily_sales[date_str] += sale.total_amount or Decimal("0.00")
            
            sorted_days = sorted(daily_sales.keys())[-7:]
            return [
                {"date": day, "total": self._round_currency(daily_sales[day])}
                for day in sorted_days
            ]
