import reflex as rx
from typing import Dict, Any
import datetime
import io
import unicodedata
from decimal import Decimal
from sqlmodel import select
import sqlalchemy as sa
from sqlalchemy.orm import selectinload
from app.enums import PaymentMethodType, SaleStatus
from app.models import (
    Sale,
    SaleItem,
    Product,
    CashboxLog,
    PaymentMethod,
)
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
    sale_detail_modal_open: bool = False
    selected_sale_id: str = ""
    selected_sale_summary: dict = {}
    selected_sale_items: list[SaleItem] = []

    def _history_date_range(self) -> tuple[datetime.datetime | None, datetime.datetime | None]:
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
        return start_date, end_date

    def _apply_sales_filters(self, query):
        start_date, end_date = self._history_date_range()
        if start_date:
            query = query.where(Sale.timestamp >= start_date)
        if end_date:
            query = query.where(Sale.timestamp <= end_date)

        if self.history_filter_type not in {"Todos", "Venta"}:
            query = query.where(sa.false())

        search = (self.history_filter_product or "").strip()
        if search:
            like_search = f"%{search}%"
            sale_ids = (
                select(SaleItem.sale_id)
                .where(SaleItem.product_name_snapshot.ilike(like_search))
                .distinct()
            )
            query = query.where(Sale.id.in_(sale_ids))
        return query

    def _sales_query(self):
        query = (
            select(Sale)
            .where(Sale.status != SaleStatus.cancelled)
            .options(
                selectinload(Sale.payments),
                selectinload(Sale.items),
                selectinload(Sale.user),
                selectinload(Sale.client),
            )
        )
        query = self._apply_sales_filters(query)
        return query.order_by(Sale.timestamp.desc())

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

    def _credit_sale_payment_label(
        self, sale: Sale, payments: list[Any]
    ) -> str | None:
        condition = (sale.payment_condition or "").strip().lower()
        if condition != "credito":
            return None
        paid_total = sum(
            Decimal(str(getattr(payment, "amount", 0) or 0))
            for payment in payments
        )
        if paid_total > 0:
            return "Crédito c/ Inicial"
        return "Crédito"

    def _sale_payment_method_label(
        self, sale: Sale, payments: list[Any], fallback: str
    ) -> str:
        explicit = (getattr(sale, "payment_method", "") or "").strip()
        credit_label = self._credit_sale_payment_label(sale, payments)
        if credit_label:
            if explicit and explicit not in {"-", "No especificado"}:
                normalized = explicit.lower()
                if normalized.startswith("credito") or normalized.startswith("crédito"):
                    return explicit
            return credit_label
        if explicit and explicit not in {"-", "No especificado"}:
            return explicit
        return fallback

    def _normalize_credit_label(self, label: str) -> str:
        normalized = unicodedata.normalize("NFKD", label or "")
        normalized = "".join(
            ch for ch in normalized if not unicodedata.combining(ch)
        )
        normalized = "".join(
            ch for ch in normalized if ch.isalpha() or ch.isspace()
        )
        return normalized.lower().strip()

    def _is_credit_label(self, label: str) -> bool:
        normalized = self._normalize_credit_label(label)
        return (
            "credito" in normalized
            or "creito" in normalized
            or "crdito" in normalized
        )

    def _sale_log_payment_info(
        self, session, sale_ids: list[int]
    ) -> dict[int, dict[str, str]]:
        if not sale_ids:
            return {}
        conditions = [
            CashboxLog.notes.like(f"%Venta%{sale_id}%") for sale_id in sale_ids
        ]
        if not conditions:
            return {}
        logs = session.exec(
            select(CashboxLog)
            .where(CashboxLog.action.in_(["Venta", "Inicial Credito"]))
            .where(sa.or_(*conditions))
        ).all()
        info: dict[int, dict[str, str]] = {}
        import re
        for log in logs:
            notes = log.notes or ""
            match = re.search(r"Venta[^0-9]*(\d+)", notes, re.IGNORECASE)
            if not match:
                continue
            try:
                sale_id = int(match.group(1))
            except ValueError:
                continue
            if sale_id not in sale_ids:
                continue
            if sale_id in info:
                continue
            info[sale_id] = {
                "payment_method": (log.payment_method or "No especificado").strip()
                or "No especificado",
                "payment_details": notes,
            }
        return info

    def _fetch_sales_history(
        self, offset: int | None = None, limit: int | None = None
    ) -> list[dict]:
        with rx.session() as session:
            query = self._sales_query()
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            sales = session.exec(query).all()
            sale_ids = [sale.id for sale in sales if sale and sale.id is not None]
            log_payment_info = self._sale_log_payment_info(session, sale_ids)

            rows: list[dict] = []
            for sale in sales:
                payments = sale.payments or []
                payment_method = self._payment_method_display(payments)
                payment_details = self._payment_summary_from_payments(payments)
                if payment_method.strip() in {"", "-"}:
                    payment_method = "No especificado"
                payment_method = self._sale_payment_method_label(
                    sale, payments, payment_method
                )
                fallback = log_payment_info.get(sale.id)
                if fallback and payment_method == "No especificado":
                    payment_method = fallback.get("payment_method", payment_method)
                    payment_details = fallback.get("payment_details", payment_details)
                client_name = (
                    sale.client.name if sale.client else "Sin cliente"
                )
                user_name = sale.user.username if sale.user else "Desconocido"
                total_amount = self._round_currency(float(sale.total_amount or 0))
                rows.append(
                    {
                        "sale_id": str(sale.id),
                        "timestamp": sale.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        if sale.timestamp
                        else "",
                        "client_name": client_name,
                        "total": total_amount,
                        "payment_method": payment_method,
                        "payment_details": self._payment_details_text(payment_details),
                        "user": user_name,
                    }
                )
            return rows

    def _sales_total_count(self) -> int:
        with rx.session() as session:
            count_query = (
                select(sa.func.count())
                .select_from(Sale)
                .where(Sale.status != SaleStatus.cancelled)
            )
            count_query = self._apply_sales_filters(count_query)
            return session.exec(count_query).one()

    @rx.var
    def filtered_history(self) -> list[dict]:
        if not self.current_user["privileges"]["view_historial"]:
            return []
        
        # Dependency to force update
        _ = self._history_update_trigger
        offset = (self.current_page_history - 1) * self.items_per_page
        return self._fetch_sales_history(offset=offset, limit=self.items_per_page)

    @rx.var
    def paginated_history(self) -> list[dict]:
        return self.filtered_history

    @rx.var
    def total_pages(self) -> int:
        _ = self._history_update_trigger
        total_items = self._sales_total_count()
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
    def open_sale_detail(self, sale_id: str):
        if not sale_id:
            return rx.toast("Venta no encontrada.", duration=3000)
        try:
            sale_db_id = int(sale_id)
        except ValueError:
            return rx.toast("Venta no encontrada.", duration=3000)
        with rx.session() as session:
            sale = session.exec(
                select(Sale)
                .where(Sale.id == sale_db_id)
                .options(
                    selectinload(Sale.items),
                    selectinload(Sale.payments),
                    selectinload(Sale.user),
                    selectinload(Sale.client),
                )
            ).first()
            if not sale:
                return rx.toast("Venta no encontrada.", duration=3000)
            payments = sale.payments or []
            payment_method = self._payment_method_display(payments)
            payment_details = self._payment_summary_from_payments(payments)
            if payment_method.strip() in {"", "-"}:
                payment_method = "No especificado"
            payment_method = self._sale_payment_method_label(
                sale, payments, payment_method
            )
            if payment_method == "No especificado":
                log_info = self._sale_log_payment_info(session, [sale.id]).get(
                    sale.id, {}
                )
                if log_info:
                    payment_method = log_info.get("payment_method", payment_method)
                    payment_details = log_info.get(
                        "payment_details", payment_details
                    )
            self.selected_sale_items = sale.items or []
            self.selected_sale_id = str(sale.id)
            self.selected_sale_summary = {
                "sale_id": str(sale.id),
                "timestamp": sale.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                if sale.timestamp
                else "",
                "client_name": sale.client.name if sale.client else "Sin cliente",
                "user": sale.user.username if sale.user else "Desconocido",
                "payment_method": payment_method,
                "payment_details": self._payment_details_text(payment_details),
                "total": self._round_currency(float(sale.total_amount or 0)),
            }
        self.sale_detail_modal_open = True

    @rx.event
    def close_sale_detail(self):
        self.sale_detail_modal_open = False
        self.selected_sale_id = ""
        self.selected_sale_summary = {}
        self.selected_sale_items = []

    @rx.event
    def set_sale_detail_modal_open(self, open_state: bool):
        if open_state:
            self.sale_detail_modal_open = True
        else:
            self.close_sale_detail()

    @rx.var
    def selected_sale_items_view(self) -> list[dict]:
        items = self.selected_sale_items or []
        return [
            {
                "description": item.product_name_snapshot,
                "quantity": float(item.quantity or 0),
                "unit_price": self._round_currency(float(item.unit_price or 0)),
                "subtotal": self._round_currency(float(item.subtotal or 0)),
            }
            for item in items
        ]

    @rx.event
    def export_to_excel(self):
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)
        
        wb, ws = create_excel_workbook("Historial Movimientos")
        
        headers = [
            "ID Venta",
            "Fecha",
            "Cliente",
            "Productos Vendidos",
            "Total",
            "Método Pago",
            "Usuario",
            "Notas",
        ]
        style_header_row(ws, 1, headers)

        def _format_quantity(value: Any) -> str:
            qty = Decimal(str(value or 0))
            text = format(qty.normalize(), "f")
            if "." in text:
                text = text.rstrip("0").rstrip(".")
            return text or "0"

        with rx.session() as session:
            query = (
                select(Sale)
                .where(Sale.status != SaleStatus.cancelled)
                .options(
                    selectinload(Sale.items),
                    selectinload(Sale.payments),
                    selectinload(Sale.user),
                    selectinload(Sale.client),
                )
            )
            query = self._apply_sales_filters(query).order_by(
                Sale.timestamp.desc()
            )
            sales = session.exec(query).all()
            sale_ids = [sale.id for sale in sales if sale and sale.id is not None]
            log_payment_info = self._sale_log_payment_info(session, sale_ids)

            rows = []
            invalid_labels = {"", "-", "no especificado"}
            for sale in sales:
                payments = sale.payments or []
                payment_method = self._payment_method_display(payments)
                payment_details = self._payment_summary_from_payments(payments)
                if payment_method.strip() in {"", "-"}:
                    payment_method = "No especificado"
                payment_method = self._sale_payment_method_label(
                    sale, payments, payment_method
                )
                fallback = log_payment_info.get(sale.id)
                if fallback and payment_method == "No especificado":
                    payment_method = fallback.get("payment_method", payment_method)
                    payment_details = fallback.get(
                        "payment_details", payment_details
                    )
                payment_type = (
                    getattr(sale, "payment_type", "") or ""
                ).strip().lower()
                payment_condition = (sale.payment_condition or "").strip().lower()
                is_credit = (
                    bool(getattr(sale, "is_credit", False))
                    or payment_type == "credit"
                    or payment_condition in {"credito", "credit"}
                )
                if is_credit:
                    payment_method = "Venta a Crédito / Fiado"
                    amount_paid = getattr(sale, "amount_paid", None)
                    if amount_paid is None:
                        amount_paid = sum(
                            Decimal(str(getattr(payment, "amount", 0) or 0))
                            for payment in payments
                        )
                    amount_paid_value = Decimal(str(amount_paid or 0))
                    if amount_paid_value > 0:
                        payment_details = (
                            f"Crédito (Adelanto: {self._format_currency(amount_paid_value)})"
                        )
                    else:
                        payment_details = "Crédito (Pendiente de Pago)"
                else:
                    if (payment_method or "").strip().lower() in invalid_labels:
                        payment_method = "Metodo no registrado"
                    if (payment_details or "").strip().lower() in invalid_labels:
                        if (payment_method or "").strip().lower() not in invalid_labels:
                            payment_details = f"Pago en {payment_method}"
                        else:
                            payment_details = "Pago registrado"

                items = sale.items or []
                item_parts = []
                for item in items:
                    name = (item.product_name_snapshot or "").strip() or "Producto"
                    quantity = _format_quantity(item.quantity)
                    price_display = self._format_currency(item.unit_price or 0)
                    item_parts.append(f"{name} (x{quantity}) - {price_display}")
                products_summary = ", ".join(item_parts) if item_parts else "-"

                client_name = sale.client.name if sale.client else "Sin cliente"
                user_name = sale.user.username if sale.user else "Desconocido"
                total_amount = self._round_currency(float(sale.total_amount or 0))

                rows.append([
                    str(sale.id),
                    sale.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    if sale.timestamp
                    else "",
                    client_name,
                    products_summary,
                    total_amount,
                    self._normalize_wallet_label(payment_method),
                    user_name,
                    self._payment_details_text(payment_details),
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
    def total_credit(self) -> float:
        _ = self._history_update_trigger
        total_credit = Decimal("0.00")
        start_date, end_date = self._history_date_range()

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
                payment_method = self._payment_method_display(payments)
                if payment_method.strip() in {"", "-"}:
                    payment_method = "No especificado"
                payment_method = self._sale_payment_method_label(
                    sale, payments, payment_method
                )
                if self._is_credit_label(payment_method):
                    total_credit += Decimal(str(sale.total_amount or 0))

        return self._round_currency(total_credit)

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
