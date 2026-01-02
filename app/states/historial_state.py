import reflex as rx
from typing import List, Dict, Any
import datetime
import json
import logging
import io
from decimal import Decimal
from sqlmodel import select
import sqlalchemy as sa
from sqlalchemy.orm import selectinload
from app.enums import PaymentMethodType, SaleStatus
from app.models import (
    Sale,
    SaleItem,
    StockMovement,
    Product,
    User as UserModel,
    CashboxLog,
    PaymentMethod,
)
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
                sa.literal("-").label("payment_method"),
                sa.literal("").label("payment_details"),
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

    def _payment_method_key(self, method_type: Any) -> str:
        if isinstance(method_type, PaymentMethodType):
            key = method_type.value
        elif hasattr(method_type, "value"):
            key = str(method_type.value).strip().lower()
        else:
            key = str(method_type or "").strip().lower()
        if key == "card":
            return "credit"
        if key == "wallet":
            return "yape"
        return key

    def _payment_method_label(self, method_key: str) -> str:
        mapping = {
            "cash": "Efectivo",
            "debit": "Tarjeta de Débito",
            "credit": "Tarjeta de Crédito",
            "yape": "Billetera Digital (Yape)",
            "plin": "Billetera Digital (Plin)",
            "transfer": "Transferencia Bancaria",
            "mixed": "Pago Mixto",
            "other": "Otros",
        }
        return mapping.get(method_key, "Otros")

    def _payment_method_abbrev(self, method_key: str) -> str:
        mapping = {
            "cash": "Efe",
            "debit": "Deb",
            "credit": "Cre",
            "yape": "Yap",
            "plin": "Plin",
            "transfer": "Transf",
            "mixed": "Mixto",
            "other": "Otro",
        }
        return mapping.get(method_key, "Otro")

    def _sorted_payment_keys(self, keys: list[str]) -> list[str]:
        order = [
            "cash",
            "debit",
            "credit",
            "yape",
            "plin",
            "transfer",
            "mixed",
            "other",
        ]
        ordered = [key for key in order if key in keys]
        for key in keys:
            if key not in ordered:
                ordered.append(key)
        return ordered

    def _payment_summary_from_payments(self, payments: list[Any]) -> str:
        if not payments:
            return "-"
        totals: dict[str, Decimal] = {}
        for payment in payments:
            key = self._payment_method_key(getattr(payment, "method_type", None))
            if not key:
                continue
            amount = Decimal(str(getattr(payment, "amount", 0) or 0))
            totals[key] = totals.get(key, Decimal("0.00")) + amount
        if not totals:
            return "-"
        parts = []
        for key in self._sorted_payment_keys(list(totals.keys())):
            label = self._payment_method_label(key)
            parts.append(f"{label}: {self._format_currency(totals[key])}")
        return ", ".join(parts)

    def _payment_method_display(self, payments: list[Any]) -> str:
        if not payments:
            return "-"
        keys: list[str] = []
        for payment in payments:
            key = self._payment_method_key(getattr(payment, "method_type", None))
            if key and key not in keys:
                keys.append(key)
        if not keys:
            return "-"
        if len(keys) == 1:
            return self._payment_method_label(keys[0])
        abbrevs = [
            self._payment_method_abbrev(key)
            for key in self._sorted_payment_keys(keys)
        ]
        return f"{self._payment_method_label('mixed')} ({'/'.join(abbrevs)})"

    def _sale_payment_info(self, session, sale_ids: list[int]) -> dict[str, dict[str, str]]:
        if not sale_ids:
            return {}
        sales = session.exec(
            select(Sale)
            .where(Sale.id.in_(sale_ids))
            .options(selectinload(Sale.payments))
        ).all()
        info: dict[str, dict[str, str]] = {}
        for sale in sales:
            payments = sale.payments or []
            info[str(sale.id)] = {
                "payment_method": self._payment_method_display(payments),
                "payment_details": self._payment_summary_from_payments(payments),
            }
        return info

    def _history_row_to_movement(
        self,
        row,
        sale_payment_info: dict[str, dict[str, str]] | None = None,
    ) -> Movement:
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
        sale_id = _value("sale_id") or ""
        payment_method = _value("payment_method") or "-"
        if sale_payment_info and sale_id in sale_payment_info:
            payment_method = sale_payment_info[sale_id].get("payment_method", "-")
            payment_details = sale_payment_info[sale_id].get("payment_details", "")
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
            "payment_method": payment_method or "-",
            "payment_details": self._payment_details_text(payment_details),
            "user": _value("user") or "Desconocido",
            "sale_id": sale_id,
        }

    def _fetch_history(self, offset: int | None = None, limit: int | None = None) -> list[Movement]:
        with rx.session() as session:
            query, _ = self._history_base_select()
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            rows = session.execute(query).all()
            sale_ids: set[int] = set()
            for row in rows:
                sale_id = None
                if isinstance(row, dict):
                    sale_id = row.get("sale_id")
                elif hasattr(row, "sale_id"):
                    sale_id = getattr(row, "sale_id")
                else:
                    try:
                        sale_id = row["sale_id"]
                    except (KeyError, IndexError, TypeError):
                        sale_id = None
                if sale_id:
                    try:
                        sale_ids.add(int(sale_id))
                    except (TypeError, ValueError):
                        continue
            sale_payment_info = self._sale_payment_info(session, list(sale_ids))
            return [
                self._history_row_to_movement(row, sale_payment_info)
                for row in rows
            ]

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
            "debito": Decimal("0.00"),
            "credito": Decimal("0.00"),
            "yape": Decimal("0.00"),
            "plin": Decimal("0.00"),
            "transferencia": Decimal("0.00"),
            "mixto": Decimal("0.00"),
        }

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
                end_date = datetime.datetime.fromisoformat(
                    self.history_filter_end_date
                )
                end_date = end_date.replace(hour=23, minute=59, second=59)
            except ValueError:
                end_date = None

        with rx.session() as session:
            query = (
                select(Sale)
                .where(Sale.status != SaleStatus.cancelled)
                .options(selectinload(Sale.payments))
            )
            if start_date:
                query = query.where(Sale.timestamp >= start_date)
            if end_date:
                query = query.where(Sale.timestamp <= end_date)

            sales = session.exec(query).all()

            for sale in sales:
                payments = sale.payments or []
                method_keys: set[str] = set()
                has_mixed = False
                for payment in payments:
                    key = self._payment_method_key(
                        getattr(payment, "method_type", None)
                    )
                    if not key:
                        continue
                    if key == PaymentMethodType.mixed.value:
                        has_mixed = True
                    method_keys.add(key)

                total = sale.total_amount
                if total is None:
                    total = sum(
                        Decimal(str(getattr(payment, "amount", 0) or 0))
                        for payment in payments
                    )
                total_amount = Decimal(str(total or 0))

                if not method_keys:
                    stats["mixto"] += total_amount
                    continue
                if has_mixed or len(method_keys) > 1:
                    stats["mixto"] += total_amount
                    continue

                key = next(iter(method_keys))
                if key == PaymentMethodType.cash.value:
                    stats["efectivo"] += total_amount
                elif key == PaymentMethodType.debit.value:
                    stats["debito"] += total_amount
                elif key == PaymentMethodType.credit.value:
                    stats["credito"] += total_amount
                elif key == PaymentMethodType.yape.value:
                    stats["yape"] += total_amount
                elif key == PaymentMethodType.plin.value:
                    stats["plin"] += total_amount
                elif key == PaymentMethodType.transfer.value:
                    stats["transferencia"] += total_amount
                else:
                    stats["mixto"] += total_amount

        return {k: self._round_currency(v) for k, v in stats.items()}

    @rx.var
    def dynamic_payment_cards(self) -> list[dict]:
        stats = self.payment_stats
        styles = {
            "cash": {"icon": "coins", "color": "blue"},
            "debit": {"icon": "credit-card", "color": "indigo"},
            "card": {"icon": "credit-card", "color": "indigo"},
            "credit": {"icon": "credit-card", "color": "violet"},
            "yape": {"icon": "qr-code", "color": "pink"},
            "plin": {"icon": "qr-code", "color": "cyan"},
            "transfer": {"icon": "landmark", "color": "orange"},
            "mixed": {"icon": "layers", "color": "amber"},
            "other": {"icon": "circle-help", "color": "gray"},
        }
        stats_key_map = {
            "cash": "efectivo",
            "debit": "debito",
            "card": "credito",
            "credit": "credito",
            "yape": "yape",
            "plin": "plin",
            "wallet": "yape",
            "transfer": "transferencia",
            "mixed": "mixto",
            "other": "mixto",
        }

        with rx.session() as session:
            methods = session.exec(
                select(PaymentMethod).where(PaymentMethod.enabled == True)
            ).all()

        order_alias = {
            "card": "credit",
            "wallet": "yape",
        }
        order_index = {
            "cash": 0,
            "yape": 1,
            "plin": 2,
            "credit": 3,
            "debit": 4,
            "transfer": 5,
            "mixed": 6,
            "other": 7,
        }

        cards: list[dict] = []
        for method in methods:
            kind = (method.kind or method.method_id or "other").strip().lower()
            sort_kind = order_alias.get(kind, kind)
            stats_key = stats_key_map.get(kind, "")
            amount = stats.get(stats_key, 0.0) if stats_key else 0.0
            style = styles.get(kind, styles["other"])
            name = method.name or method.method_id or "Metodo"
            cards.append(
                {
                    "name": name,
                    "amount": amount,
                    "icon": style["icon"],
                    "color": style["color"],
                    "_sort_key": sort_kind,
                }
            )

        def _sorter(card: dict) -> tuple[int, str]:
            name = (card.get("name") or "").strip().lower()
            key = card.get("_sort_key") or ""
            return (order_index.get(key, 99), name)

        cards.sort(key=_sorter)
        for card in cards:
            card.pop("_sort_key", None)
        return cards

    @rx.var
    def total_ventas_efectivo(self) -> float:
        return self.payment_stats["efectivo"]

    @rx.var
    def total_ventas_debito(self) -> float:
        return self.payment_stats["debito"]

    @rx.var
    def total_ventas_credito(self) -> float:
        return self.payment_stats["credito"]

    @rx.var
    def total_ventas_yape(self) -> float:
        return self.payment_stats["yape"]

    @rx.var
    def total_ventas_plin(self) -> float:
        return self.payment_stats["plin"]

    @rx.var
    def total_ventas_tarjeta(self) -> float:
        return self._round_currency(
            self.payment_stats["debito"] + self.payment_stats["credito"]
        )

    @rx.var
    def total_ventas_transferencia(self) -> float:
        return self.payment_stats["transferencia"]

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
            sales = session.exec(
                select(Sale).where(Sale.status != SaleStatus.cancelled)
            ).all()
            daily_sales = defaultdict(Decimal)
            for sale in sales:
                date_str = sale.timestamp.strftime("%Y-%m-%d")
                daily_sales[date_str] += sale.total_amount or Decimal("0.00")
            
            sorted_days = sorted(daily_sales.keys())[-7:]
            return [
                {"date": day, "total": self._round_currency(daily_sales[day])}
                for day in sorted_days
            ]
