import reflex as rx
import sqlalchemy
from typing import Any, List
from sqlmodel import select, desc
from sqlalchemy.orm import selectinload
from app.enums import PaymentMethodType, SaleStatus
from app.utils.payment import payment_method_label as _canonical_payment_method_label
from app.models import CashboxLog as CashboxLogModel, User as UserModel, Sale, SaleItem
from app.i18n import MSG
from ..types import CashboxSale, CashboxLogEntry


class HistoryMixin:
    """Mixin with history/listing-related methods for the cash state."""

    @rx.event
    def toggle_cashbox_sale_detail(self, sale_id: str):
        value = str(sale_id or "").strip()
        if not value:
            return
        if self.expanded_cashbox_sale_id == value:
            self.expanded_cashbox_sale_id = ""
        else:
            self.expanded_cashbox_sale_id = value

    def _cashbox_logs_query(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return (
                select(CashboxLogModel, UserModel.username)
                .join(UserModel)
                .where(sqlalchemy.false())
            )
        statement = (
            select(CashboxLogModel, UserModel.username)
            .join(UserModel)
            .where(CashboxLogModel.action.in_(["apertura", "cierre"]))
            .where(CashboxLogModel.company_id == company_id)
            .where(CashboxLogModel.branch_id == branch_id)
            .order_by(desc(CashboxLogModel.timestamp))
        )
        return self._apply_local_day_filters(
            statement,
            CashboxLogModel.timestamp,
            self.cashbox_log_filter_start_date,
            self.cashbox_log_filter_end_date,
        )

    def _cashbox_logs_count(self) -> int:
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return 0
        statement = (
            select(sqlalchemy.func.count())
            .select_from(CashboxLogModel)
            .where(CashboxLogModel.action.in_(["apertura", "cierre"]))
            .where(CashboxLogModel.company_id == company_id)
            .where(CashboxLogModel.branch_id == branch_id)
        )
        statement = self._apply_local_day_filters(
            statement,
            CashboxLogModel.timestamp,
            self.cashbox_log_filter_start_date,
            self.cashbox_log_filter_end_date,
        )

        with rx.session() as session:
            return session.exec(statement).one()

    def _fetch_cashbox_logs(
        self, offset: int | None = None, limit: int | None = None
    ) -> list[CashboxLogEntry]:
        with rx.session() as session:
            statement = self._cashbox_logs_query()
            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)
            results = session.exec(statement).all()

            filtered: list[CashboxLogEntry] = []
            for log, username in results:
                entry: CashboxLogEntry = {
                    "id": str(log.id),
                    "action": log.action,
                    "timestamp": self._format_event_timestamp(log.timestamp),
                    "user": username,
                    "opening_amount": log.amount if log.action == "apertura" else 0.0,
                    "closing_total": log.amount if log.action == "cierre" else 0.0,
                    "totals_by_method": [],
                    "notes": log.notes,
                    "amount": log.amount,
                }
                filtered.append(entry)

            return filtered

    @rx.event
    def set_cashbox_staged_start_date(self, value: str):
        denial = self._cashbox_guard()
        if denial:
            return denial
        self.cashbox_staged_start_date = value or ""

    @rx.event
    def set_cashbox_staged_end_date(self, value: str):
        denial = self._cashbox_guard()
        if denial:
            return denial
        self.cashbox_staged_end_date = value or ""

    @rx.event
    def apply_cashbox_filters(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        self.cashbox_filter_start_date = self.cashbox_staged_start_date
        self.cashbox_filter_end_date = self.cashbox_staged_end_date
        self.cashbox_current_page = 1
        self._refresh_cashbox_caches()

    @rx.event
    def reset_cashbox_filters(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        self.cashbox_filter_start_date = ""
        self.cashbox_filter_end_date = ""
        self.cashbox_staged_start_date = ""
        self.cashbox_staged_end_date = ""
        self.cashbox_current_page = 1
        self._refresh_cashbox_caches()

    @rx.event
    def set_cashbox_log_staged_start_date(self, value: str):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast(MSG.PERM_CASH_MGMT, duration=3000)
        self.cashbox_log_staged_start_date = value or ""

    @rx.event
    def set_cashbox_log_staged_end_date(self, value: str):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast(MSG.PERM_CASH_MGMT, duration=3000)
        self.cashbox_log_staged_end_date = value or ""

    @rx.event
    def apply_cashbox_log_filters(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast(MSG.PERM_CASH_MGMT, duration=3000)
        self.cashbox_log_filter_start_date = self.cashbox_log_staged_start_date
        self.cashbox_log_filter_end_date = self.cashbox_log_staged_end_date
        self.cashbox_log_current_page = 1
        self._refresh_cashbox_caches()

    @rx.event
    def reset_cashbox_log_filters(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast(MSG.PERM_CASH_MGMT, duration=3000)
        self.cashbox_log_filter_start_date = ""
        self.cashbox_log_filter_end_date = ""
        self.cashbox_log_staged_start_date = ""
        self.cashbox_log_staged_end_date = ""
        self.cashbox_log_current_page = 1
        self._refresh_cashbox_caches()

    @rx.event
    def set_cashbox_log_page(self, page: int):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast(MSG.PERM_CASH_MGMT, duration=3000)
        if 1 <= page <= self.cashbox_log_total_pages:
            self.cashbox_log_current_page = page
            self._refresh_cashbox_caches()

    @rx.event
    def prev_cashbox_log_page(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast(MSG.PERM_CASH_MGMT, duration=3000)
        if self.cashbox_log_current_page > 1:
            self.cashbox_log_current_page -= 1
            self._refresh_cashbox_caches()

    @rx.event
    def next_cashbox_log_page(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast(MSG.PERM_CASH_MGMT, duration=3000)
        if self.cashbox_log_current_page < self.cashbox_log_total_pages:
            self.cashbox_log_current_page += 1
            self._refresh_cashbox_caches()

    @rx.event
    def set_cashbox_page(self, page: int):
        denial = self._cashbox_guard()
        if denial:
            return denial
        if 1 <= page <= self.cashbox_total_pages:
            self.cashbox_current_page = page
            self._refresh_cashbox_caches()

    @rx.event
    def set_show_cashbox_advances(self, value: bool | str):
        denial = self._cashbox_guard()
        if denial:
            return denial
        if isinstance(value, str):
            value = value.lower() in ["true", "1", "on", "yes"]
        self.show_cashbox_advances = bool(value)
        self.cashbox_current_page = 1
        self._refresh_cashbox_caches()

    @rx.event
    def prev_cashbox_page(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        if self.cashbox_current_page > 1:
            self.cashbox_current_page -= 1
            self._refresh_cashbox_caches()

    @rx.event
    def next_cashbox_page(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        total_pages = self.cashbox_total_pages
        if self.cashbox_current_page < total_pages:
            self.cashbox_current_page += 1
            self._refresh_cashbox_caches()

    def _cashbox_sales_query(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return (
                select(Sale, UserModel)
                .select_from(Sale)
                .join(UserModel, Sale.user_id == UserModel.id, isouter=True)
                .where(sqlalchemy.false())
            )
        query = (
            select(Sale, UserModel)
            .select_from(Sale)
            .join(UserModel, Sale.user_id == UserModel.id, isouter=True)
            .options(
                selectinload(Sale.items),
                selectinload(Sale.payments),
                selectinload(Sale.installments),
            )
            .where(Sale.company_id == company_id)
            .where(Sale.branch_id == branch_id)
            .order_by(desc(Sale.timestamp))
        )
        query = self._apply_local_day_filters(
            query,
            Sale.timestamp,
            self.cashbox_filter_start_date,
            self.cashbox_filter_end_date,
        )

        if not self.show_cashbox_advances:
            advance_exists = (
                sqlalchemy.exists()
                .where(SaleItem.sale_id == Sale.id)
                .where(
                    sqlalchemy.func.lower(
                        sqlalchemy.func.coalesce(SaleItem.product_name_snapshot, "")
                    ).like("%adelanto%")
                )
            )
            query = query.where(~advance_exists)

        return query

    def _cashbox_sales_count(self) -> int:
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return 0
        query = (
            select(sqlalchemy.func.count(Sale.id))
            .select_from(Sale)
            .where(Sale.company_id == company_id)
            .where(Sale.branch_id == branch_id)
        )
        query = self._apply_local_day_filters(
            query,
            Sale.timestamp,
            self.cashbox_filter_start_date,
            self.cashbox_filter_end_date,
        )

        if not self.show_cashbox_advances:
            advance_exists = (
                sqlalchemy.exists()
                .where(SaleItem.sale_id == Sale.id)
                .where(
                    sqlalchemy.func.lower(
                        sqlalchemy.func.coalesce(SaleItem.product_name_snapshot, "")
                    ).like("%adelanto%")
                )
            )
            query = query.where(~advance_exists)

        with rx.session() as session:
            return session.exec(query).one()

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
        return _canonical_payment_method_label(method_key)

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
        totals: dict[str, float] = {}
        for payment in payments:
            key = self._payment_method_key(getattr(payment, "method_type", None))
            if not key:
                continue
            amount = float(getattr(payment, "amount", 0) or 0)
            totals[key] = totals.get(key, 0.0) + amount
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

    def _payment_breakdown_from_payments(self, payments: list[Any]) -> list[dict[str, float]]:
        if not payments:
            return []
        totals: dict[str, float] = {}
        for payment in payments:
            key = self._payment_method_key(getattr(payment, "method_type", None))
            if not key:
                continue
            amount = float(getattr(payment, "amount", 0) or 0)
            totals[key] = totals.get(key, 0.0) + amount
        breakdown = []
        for key in self._sorted_payment_keys(list(totals.keys())):
            label = self._payment_method_label(key)
            breakdown.append({"label": label, "amount": self._round_currency(totals[key])})
        return breakdown

    def _payment_kind_from_payments(self, payments: list[Any]) -> str:
        keys = {
            self._payment_method_key(getattr(payment, "method_type", None))
            for payment in payments
        }
        keys.discard("")
        if len(keys) > 1:
            return "mixed"
        if len(keys) == 1:
            return next(iter(keys))
        return ""

    def _cashbox_sale_row(self, sale: Sale, user: UserModel | None) -> CashboxSale:
        payments = sale.payments or []
        details_text = self._payment_summary_from_payments(payments)
        method_label = self._payment_method_display(payments)
        payment_breakdown = self._payment_breakdown_from_payments(payments)
        payment_kind = self._payment_kind_from_payments(payments)
        paid_total = sum(
            float(getattr(payment, "amount", 0) or 0) for payment in payments
        )
        installments_paid = sum(
            float(getattr(installment, "paid_amount", 0) or 0)
            for installment in sale.installments or []
        )
        total_paid = paid_total + installments_paid
        paid_total = self._round_currency(paid_total)
        total_paid = self._round_currency(total_paid)
        if (sale.payment_condition or "").strip().lower() == "credito":
            if paid_total > 0:
                method_label = "Crédito c/ Inicial"
                if not details_text or details_text == "-":
                    details_text = f"Inicial: {self._format_currency(paid_total)}"
            else:
                method_label = "Crédito"
                details_text = "Crédito/Fiado"
        items: list[dict] = []
        items_total = 0
        for item in sale.items or []:
            items.append(
                {
                    "description": item.product_name_snapshot,
                    "quantity": item.quantity,
                    "unit": MSG.FALLBACK_UNIT,
                    "price": item.unit_price,
                    "sale_price": item.unit_price,
                    "subtotal": item.subtotal,
                }
            )
            items_total += item.subtotal or 0
        total_amount = sale.total_amount if sale.total_amount is not None else items_total
        preview_limit = 2
        hidden_count = max(len(items) - preview_limit, 0)
        sale_dict: CashboxSale = {
            "sale_id": str(sale.id),
            "timestamp": self._format_event_timestamp(sale.timestamp),
            "user": user.username if user else MSG.FALLBACK_UNKNOWN,
            "payment_method": method_label,
            "payment_label": method_label,
            "payment_details": details_text,
            "payment_condition": sale.payment_condition,
            "is_credit": (sale.payment_condition or "").strip().lower() == "credito",
            "amount_paid": total_paid,
            "amount": paid_total,
            "total": total_amount,
            "is_deleted": sale.status == SaleStatus.cancelled,
            "delete_reason": sale.delete_reason,
            "items": items,
            "items_preview": items[:preview_limit],
            "items_hidden_count": hidden_count,
            "service_total": total_amount,
            "payment_breakdown": payment_breakdown,
            "payment_kind": payment_kind,
        }
        return sale_dict

    def _fetch_cashbox_sales(
        self, offset: int | None = None, limit: int | None = None
    ) -> list[CashboxSale]:
        with rx.session() as session:
            query = self._cashbox_sales_query()
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            sales_results = session.exec(query).all()
            return [
                self._cashbox_sale_row(sale, user)
                for sale, user in sales_results
            ]
