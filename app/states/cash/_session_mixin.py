import reflex as rx
import datetime
import re
import sqlalchemy
from typing import Any, List
from decimal import Decimal, InvalidOperation
from sqlmodel import select, desc

from app.enums import PaymentMethodType, SaleStatus
from app.models import (
    CashboxSession as CashboxSessionModel,
    CashboxLog as CashboxLogModel,
    User as UserModel,
    Sale,
    SaleItem,
    SalePayment,
)
from app.constants import CASHBOX_INCOME_ACTIONS, CASHBOX_EXPENSE_ACTIONS
from app.i18n import MSG
from app.utils.tenant import set_tenant_context
from ..types import CashboxSale, CashboxSession, CashboxLogEntry


class SessionMixin:
    """Mixin para la gestión de sesiones de caja (apertura, cierre, consultas)."""

    # ── Time helpers ─────────────────────────────────────────────

    def _event_timestamp(self) -> datetime.datetime:
        return self._utc_now()

    def _format_event_timestamp(
        self,
        value: datetime.datetime | None,
        fmt: str = "%Y-%m-%d %H:%M:%S",
    ) -> str:
        return self._format_company_datetime(value, fmt)

    def _current_local_date_str(self) -> str:
        return self._display_now().strftime("%Y-%m-%d")

    def _current_local_display_date(self) -> str:
        return self._display_now().strftime("%d/%m/%Y")

    def _apply_local_day_filters(
        self,
        statement,
        column,
        start_value: str,
        end_value: str,
    ):
        if start_value:
            try:
                start_dt, _ = self._company_day_bounds_utc_naive(start_value)
                statement = statement.where(column >= start_dt)
            except ValueError:
                pass
        if end_value:
            try:
                _, end_dt = self._company_day_bounds_utc_naive(end_value)
                statement = statement.where(column <= end_dt)
            except ValueError:
                pass
        return statement

    # ── Session data loading ─────────────────────────────────────

    def _empty_cashbox_session_data(self) -> CashboxSession:
        username = "guest"
        if hasattr(self, "current_user") and self.current_user:
            username = self.current_user.get("username", "guest")
        return {
            "opening_amount": 0.0,
            "opening_time": "",
            "closing_time": "",
            "is_open": False,
            "opened_by": username,
        }

    def _load_current_cashbox_session_data(self) -> CashboxSession:
        session_data = self._empty_cashbox_session_data()
        user_id = self.current_user.get("id") if hasattr(self, "current_user") else None
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not user_id or not company_id or not branch_id:
            return session_data

        with rx.session() as session:
            cashbox_session = session.exec(
                select(CashboxSessionModel)
                .where(CashboxSessionModel.user_id == user_id)
                .where(CashboxSessionModel.company_id == company_id)
                .where(CashboxSessionModel.branch_id == branch_id)
                .where(CashboxSessionModel.is_open == True)
            ).first()

        if not cashbox_session:
            return session_data

        session_data["opening_amount"] = float(cashbox_session.opening_amount or 0)
        session_data["opening_time"] = self._format_event_timestamp(
            cashbox_session.opening_time
        )
        session_data["closing_time"] = ""
        session_data["is_open"] = True
        return session_data

    def _compute_cashbox_opening_amount(self, session_data: CashboxSession) -> float:
        if not session_data.get("is_open"):
            return 0.0

        opening_amount = float(session_data.get("opening_amount", 0) or 0)
        user_id = self.current_user.get("id") if hasattr(self, "current_user") else None
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not user_id or not company_id or not branch_id:
            return opening_amount

        opening_time = None
        with rx.session() as session:
            cashbox_session = session.exec(
                select(CashboxSessionModel)
                .where(CashboxSessionModel.user_id == user_id)
                .where(CashboxSessionModel.company_id == company_id)
                .where(CashboxSessionModel.branch_id == branch_id)
                .where(CashboxSessionModel.is_open == True)
            ).first()
            if cashbox_session:
                opening_time = cashbox_session.opening_time

        if not opening_time:
            return opening_amount

        with rx.session() as session:
            expenses = session.exec(
                select(sqlalchemy.func.sum(CashboxLogModel.amount)).where(
                    CashboxLogModel.user_id == user_id,
                    CashboxLogModel.action == "gasto_caja_chica",
                    CashboxLogModel.timestamp >= opening_time,
                    CashboxLogModel.company_id == company_id,
                    CashboxLogModel.branch_id == branch_id,
                )
            ).one()
        return opening_amount - float(expenses or 0)

    def _refresh_cashbox_caches(self):
        session_data = self._load_current_cashbox_session_data()
        self.current_cashbox_session = session_data
        self.cashbox_is_open_cached = bool(session_data.get("is_open"))
        self.cashbox_opening_amount = self._compute_cashbox_opening_amount(
            session_data
        )

        if not self.current_user["privileges"]["view_cashbox"]:
            self.petty_cash_movements = []
            self.petty_cash_total_pages = 1
            self.filtered_cashbox_logs = []
            self.cashbox_log_total_pages = 1
            self.filtered_cashbox_sales = []
            self.cashbox_total_pages = 1
            return

        petty_total = int(self._petty_cash_count() or 0)
        petty_total_pages = (
            1
            if petty_total == 0
            else (petty_total + self.petty_cash_items_per_page - 1)
            // self.petty_cash_items_per_page
        )
        petty_page = min(max(self.petty_cash_current_page, 1), petty_total_pages)
        if petty_page != self.petty_cash_current_page:
            self.petty_cash_current_page = petty_page
        petty_offset = (petty_page - 1) * max(self.petty_cash_items_per_page, 1)
        self.petty_cash_movements = self._fetch_petty_cash(
            offset=petty_offset,
            limit=max(self.petty_cash_items_per_page, 1),
        )
        self.petty_cash_total_pages = petty_total_pages

        log_total = int(self._cashbox_logs_count() or 0)
        log_total_pages = (
            1
            if log_total == 0
            else (log_total + self.cashbox_log_items_per_page - 1)
            // self.cashbox_log_items_per_page
        )
        log_page = min(max(self.cashbox_log_current_page, 1), log_total_pages)
        if log_page != self.cashbox_log_current_page:
            self.cashbox_log_current_page = log_page
        log_offset = (log_page - 1) * max(self.cashbox_log_items_per_page, 1)
        self.filtered_cashbox_logs = self._fetch_cashbox_logs(
            offset=log_offset,
            limit=max(self.cashbox_log_items_per_page, 1),
        )
        self.cashbox_log_total_pages = log_total_pages

        sales_total = int(self._cashbox_sales_count() or 0)
        sales_total_pages = (
            1
            if sales_total == 0
            else (sales_total + self.cashbox_items_per_page - 1)
            // self.cashbox_items_per_page
        )
        sales_page = min(max(self.cashbox_current_page, 1), sales_total_pages)
        if sales_page != self.cashbox_current_page:
            self.cashbox_current_page = sales_page
        sales_offset = (sales_page - 1) * max(self.cashbox_items_per_page, 1)
        self.filtered_cashbox_sales = self._fetch_cashbox_sales(
            offset=sales_offset,
            limit=max(self.cashbox_items_per_page, 1),
        )
        self.cashbox_total_pages = sales_total_pages

    @rx.event
    def refresh_cashbox_data(self):
        self._refresh_cashbox_caches()

    @rx.var(cache=True)
    def cashbox_opening_amount_display(self) -> str:
        return f"{self.cashbox_opening_amount:.2f}"

    @rx.var(cache=True)
    def cashbox_is_open(self) -> bool:
        return bool(self.current_cashbox_session.get("is_open"))

    @rx.var(cache=True)
    def cashbox_opening_time(self) -> str:
        return self.current_cashbox_session.get("opening_time", "")

    def _require_cashbox_open(self):
        if not self.cashbox_is_open:
            return rx.toast(MSG.CASH_OPEN_REQUIRED_OP, duration=3000)
        return None

    def _cashbox_guard(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast(MSG.PERM_CASH_MGMT, duration=3000)
        if not self.cashbox_is_open:
            return rx.toast(
                MSG.CASH_OPEN_REQUIRED_MGMT,
                duration=3000,
            )
        return None

    def _cashbox_time_range(
        self, date: str
    ) -> tuple[datetime.datetime, datetime.datetime, dict[str, Any] | None]:
        session_info = self._active_cashbox_session_info()
        if session_info:
            start_dt = session_info.get("opening_time") or self._event_timestamp()
            end_dt = session_info.get("closing_time") or self._event_timestamp()
            return start_dt, end_dt, session_info
        try:
            start_dt, end_dt = self._company_day_bounds_utc_naive(date)
        except ValueError:
            start_dt, end_dt = self._company_day_bounds_utc_naive(None)
        return start_dt, end_dt, None

    def _cashbox_range_for_log(
        self,
        log: CashboxLogModel,
    ) -> tuple[datetime.datetime, datetime.datetime, int | None, str, datetime.datetime]:
        """Obtiene rango de tiempo para un cierre historico basado en el log."""
        timestamp = log.timestamp or self._event_timestamp()
        report_date = self._format_company_datetime(timestamp, "%Y-%m-%d")
        start_dt, end_dt = self._company_day_bounds_utc_naive(report_date)
        user_id = log.user_id
        company_id = log.company_id
        branch_id = log.branch_id
        set_tenant_context(company_id, branch_id)
        if user_id:
            window_start = timestamp - datetime.timedelta(hours=4)
            window_end = timestamp + datetime.timedelta(hours=4)
            with rx.session() as session:
                sessions = session.exec(
                    select(CashboxSessionModel)
                    .where(CashboxSessionModel.company_id == company_id)
                    .where(CashboxSessionModel.branch_id == branch_id)
                    .where(CashboxSessionModel.user_id == user_id)
                    .where(CashboxSessionModel.closing_time.is_not(None))
                    .where(CashboxSessionModel.closing_time >= window_start)
                    .where(CashboxSessionModel.closing_time <= window_end)
                    .execution_options(
                        tenant_company_id=company_id,
                        tenant_branch_id=branch_id,
                    )
                ).all()
            if sessions:
                closest = min(
                    sessions,
                    key=lambda item: abs(
                        (item.closing_time or timestamp) - timestamp
                    ).total_seconds(),
                )
                start_dt = closest.opening_time or start_dt
                end_dt = closest.closing_time or timestamp
        return start_dt, end_dt, user_id, report_date, timestamp

    def _cashbox_opening_amount_for_range(
        self,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
        company_id: int,
        branch_id: int,
        user_id: int | None = None,
    ) -> float:
        with rx.session() as session:
            statement = (
                select(CashboxLogModel)
                .where(CashboxLogModel.action == "apertura")
                .where(CashboxLogModel.is_voided == False)
                .where(CashboxLogModel.timestamp >= start_dt)
                .where(CashboxLogModel.timestamp <= end_dt)
                .where(CashboxLogModel.company_id == company_id)
                .where(CashboxLogModel.branch_id == branch_id)
                .order_by(CashboxLogModel.timestamp.asc())
            )
            if user_id:
                statement = statement.where(CashboxLogModel.user_id == user_id)
            log = session.exec(statement).first()
            if log:
                return float(log.amount or 0)
        return 0.0

    def _cashbox_expense_total_for_range(
        self,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
        company_id: int,
        branch_id: int,
        user_id: int | None = None,
    ) -> float:
        with rx.session() as session:
            statement = (
                select(sqlalchemy.func.sum(CashboxLogModel.amount))
                .where(CashboxLogModel.action.in_(CASHBOX_EXPENSE_ACTIONS))
                .where(CashboxLogModel.is_voided == False)
                .where(CashboxLogModel.timestamp >= start_dt)
                .where(CashboxLogModel.timestamp <= end_dt)
                .where(CashboxLogModel.company_id == company_id)
                .where(CashboxLogModel.branch_id == branch_id)
            )
            if user_id:
                statement = statement.where(CashboxLogModel.user_id == user_id)
            total = session.exec(statement).one()
        return self._round_currency(total or 0)

    def _build_cashbox_summary_for_range(
        self,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
        company_id: int,
        branch_id: int,
        user_id: int | None = None,
    ) -> list[dict]:
        method_col = sqlalchemy.func.coalesce(
            CashboxLogModel.payment_method, MSG.FALLBACK_NOT_SPECIFIED
        )
        statement = (
            select(
                method_col,
                sqlalchemy.func.count(CashboxLogModel.id),
                sqlalchemy.func.sum(CashboxLogModel.amount),
            )
            .where(CashboxLogModel.amount > 0)
            .where(CashboxLogModel.action.in_(CASHBOX_INCOME_ACTIONS))
            .where(CashboxLogModel.is_voided == False)
            .where(CashboxLogModel.timestamp >= start_dt)
            .where(CashboxLogModel.timestamp <= end_dt)
            .where(CashboxLogModel.company_id == company_id)
            .where(CashboxLogModel.branch_id == branch_id)
            .group_by(method_col)
        )
        if user_id:
            statement = statement.where(CashboxLogModel.user_id == user_id)
        with rx.session() as session:
            results = session.exec(statement).all()
        summary: list[dict] = []
        for method, count, amount in results:
            label = (method or MSG.FALLBACK_NOT_SPECIFIED).strip() or MSG.FALLBACK_NOT_SPECIFIED
            summary.append(
                {
                    "method": label,
                    "count": int(count or 0),
                    "total": self._round_currency(amount or 0),
                }
            )
        summary.sort(key=lambda item: item.get("total", 0), reverse=True)
        return summary

    def _get_sales_for_range(
        self,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
        company_id: int,
        branch_id: int,
        user_id: int | None = None,
    ) -> list[CashboxSale]:
        with rx.session() as session:
            statement = (
                select(CashboxLogModel, UserModel.username)
                .join(UserModel, isouter=True)
                .where(CashboxLogModel.amount > 0)
                .where(CashboxLogModel.action.in_(CASHBOX_INCOME_ACTIONS))
                .where(CashboxLogModel.is_voided == False)
                .where(CashboxLogModel.timestamp >= start_dt)
                .where(CashboxLogModel.timestamp <= end_dt)
                .where(CashboxLogModel.company_id == company_id)
                .where(CashboxLogModel.branch_id == branch_id)
                .order_by(desc(CashboxLogModel.timestamp))
            )
            if user_id:
                statement = statement.where(CashboxLogModel.user_id == user_id)
            logs = session.exec(statement).all()

            result: list[CashboxSale] = []
            for log, username in logs:
                method_label = (log.payment_method or MSG.FALLBACK_NOT_SPECIFIED).strip() or MSG.FALLBACK_NOT_SPECIFIED
                payment_detail = log.notes or ""
                concept = payment_detail.strip()
                if concept:
                    concept = re.sub(r"#\d+", "", concept)
                    concept = re.sub(r"\s{2,}", " ", concept)
                    concept = concept.strip()
                    concept = re.sub(r"^[\s:;-]+", "", concept)
                if not concept:
                    action_label = (log.action or "").replace("_", " ").strip().title()
                    concept = action_label or method_label
                timestamp = log.timestamp
                time_label = ""
                if timestamp:
                    time_label = self._format_event_timestamp(timestamp, "%H:%M")
                result.append(
                    {
                        "sale_id": str(log.id),
                        "timestamp": self._format_event_timestamp(log.timestamp),
                        "time": time_label,
                        "user": username or MSG.FALLBACK_UNKNOWN,
                        "payment_method": method_label,
                        "payment_label": method_label,
                        "payment_details": payment_detail,
                        "concept": concept,
                        "amount": self._round_currency(log.amount or 0),
                        "total": log.amount,
                        "is_deleted": False,
                        "payment_breakdown": [
                            {
                                "label": method_label,
                                "amount": self._round_currency(log.amount or 0),
                            }
                        ],
                        "payment_kind": "",
                    }
                )
            return result

    def _cashbox_opening_amount_value(self, date: str) -> float:
        session_info = self._active_cashbox_session_info()
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return 0.0
        if session_info:
            with rx.session() as session:
                cashbox_session = session.exec(
                    select(CashboxSessionModel)
                    .where(CashboxSessionModel.user_id == session_info["user_id"])
                    .where(CashboxSessionModel.company_id == company_id)
                    .where(CashboxSessionModel.branch_id == branch_id)
                    .where(CashboxSessionModel.is_open == True)
                ).first()
                if cashbox_session:
                    return float(cashbox_session.opening_amount or 0)
        start_dt, end_dt, session_info = self._cashbox_time_range(date)
        with rx.session() as session:
            statement = (
                select(CashboxLogModel)
                .where(CashboxLogModel.action == "apertura")
                .where(CashboxLogModel.is_voided == False)
                .where(CashboxLogModel.timestamp >= start_dt)
                .where(CashboxLogModel.timestamp <= end_dt)
                .where(CashboxLogModel.company_id == company_id)
                .where(CashboxLogModel.branch_id == branch_id)
                .order_by(CashboxLogModel.timestamp.asc())
            )
            if session_info:
                statement = statement.where(
                    CashboxLogModel.user_id == session_info["user_id"]
                )
            log = session.exec(statement).first()
            if log:
                return float(log.amount or 0)
        return 0.0

    def _cashbox_expense_total(self, date: str) -> float:
        start_dt, end_dt, session_info = self._cashbox_time_range(date)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return 0.0
        with rx.session() as session:
            statement = (
                select(sqlalchemy.func.sum(CashboxLogModel.amount))
                .where(CashboxLogModel.action.in_(CASHBOX_EXPENSE_ACTIONS))
                .where(CashboxLogModel.is_voided == False)
                .where(CashboxLogModel.timestamp >= start_dt)
                .where(CashboxLogModel.timestamp <= end_dt)
                .where(CashboxLogModel.company_id == company_id)
                .where(CashboxLogModel.branch_id == branch_id)
            )
            if session_info:
                statement = statement.where(
                    CashboxLogModel.user_id == session_info["user_id"]
                )
            total = session.exec(statement).one()
        return self._round_currency(total or 0)

    def _build_cashbox_close_breakdown(self, date: str) -> dict[str, Any]:
        summary = self._build_cashbox_summary(date)
        opening_amount = self._cashbox_opening_amount_value(date)
        income_total = self._round_currency(
            sum(item.get("total", 0) for item in summary)
        )
        expense_total = self._cashbox_expense_total(date)
        expected_total = self._round_currency(
            opening_amount + income_total - expense_total
        )
        return {
            "summary": summary,
            "opening_amount": self._round_currency(opening_amount),
            "income_total": income_total,
            "expense_total": expense_total,
            "expected_total": expected_total,
        }

    def _active_cashbox_session_info(self) -> dict[str, Any] | None:
        if not hasattr(self, "current_user") or not self.current_user:
            return None
        user_id = self.current_user.get("id")
        if not user_id:
            return None
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return None
        with rx.session() as session:
            cashbox_session = session.exec(
                select(CashboxSessionModel)
                .where(CashboxSessionModel.user_id == user_id)
                .where(CashboxSessionModel.company_id == company_id)
                .where(CashboxSessionModel.branch_id == branch_id)
                .where(CashboxSessionModel.is_open == True)
            ).first()
            if not cashbox_session:
                return None
            return {
                "user_id": user_id,
                "opening_time": cashbox_session.opening_time,
                "closing_time": cashbox_session.closing_time,
            }

    @rx.event
    def refresh_cashbox_status(self):
        self._refresh_cashbox_status_light()

    def _refresh_cashbox_status_light(self):
        """Carga solo is_open + monto de apertura (2 queries).
        Para data completa (logs, ventas, gastos) usar _refresh_cashbox_caches().
        """
        session_data = self._load_current_cashbox_session_data()
        self.current_cashbox_session = session_data
        self.cashbox_is_open_cached = bool(session_data.get("is_open"))
        self.cashbox_opening_amount = self._compute_cashbox_opening_amount(
            session_data
        )

    @rx.event
    def set_cashbox_open_amount_input(self, value: float | str):
        self.cashbox_open_amount_input = str(value or "").strip()

    @rx.event
    def handle_cashbox_form_submit(self, form_data: dict):
        """Procesa el formulario de apertura de caja (evita corte de digitos)."""
        amount_str = str(form_data.get("amount", "0") or "0").strip()
        self.cashbox_open_amount_input = amount_str
        return self.open_cashbox_session()

    @rx.event
    def open_cashbox_session(self):
        if not self.current_user["privileges"]["manage_cashbox"]:
            return rx.toast(MSG.PERM_CASH, duration=3000)
        block = self._require_active_subscription()
        if block:
            return block
        user_id = self.current_user.get("id")
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast(MSG.VAL_COMPANY_UNDEFINED, duration=3000)
        if self.current_user["role"].lower() == "cajero" and not hasattr(self, "token"):
            return rx.toast(MSG.VAL_SESSION_REQUIRED, duration=3000)

        try:
            amount = Decimal(str(self.cashbox_open_amount_input)) if self.cashbox_open_amount_input else Decimal("0")
        except (ValueError, InvalidOperation):
            amount = Decimal("0")
        amount = self._round_currency(amount)

        if amount < 0:
            return rx.toast(MSG.CASH_INVALID_INITIAL, duration=3000)

        if not user_id:
            return rx.toast(MSG.VAL_USER_NOT_FOUND, duration=3000)
        with rx.session() as session:
            existing = session.exec(
                select(CashboxSessionModel)
                .where(CashboxSessionModel.user_id == user_id)
                .where(CashboxSessionModel.company_id == company_id)
                .where(CashboxSessionModel.branch_id == branch_id)
                .where(CashboxSessionModel.is_open == True)
            ).first()

            if existing:
                 return rx.toast(MSG.CASH_ALREADY_OPEN, duration=3000)

            new_session = CashboxSessionModel(
                company_id=company_id,
                branch_id=branch_id,
                user_id=user_id,
                opening_amount=amount,
                opening_time=self._event_timestamp(),
                is_open=True
            )
            session.add(new_session)
            session.flush()
            session.refresh(new_session)

            log = CashboxLogModel(
                company_id=company_id,
                branch_id=branch_id,
                user_id=user_id,
                action="apertura",
                amount=amount,
                notes="Apertura de caja",
                timestamp=self._event_timestamp()
            )
            session.add(log)
            session.commit()  # Atomico: sesion + log en una sola transaccion

        self.cashbox_open_amount_input = ""
        self._cashbox_update_trigger += 1
        self._refresh_cashbox_caches()
        return rx.toast(MSG.CASH_OPENED, duration=3000)

    def _close_cashbox_session(self):
        user_id = self.current_user.get("id")

        if not user_id:
            return
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return

        with rx.session() as session:
            cashbox_session = session.exec(
                select(CashboxSessionModel)
                .where(CashboxSessionModel.user_id == user_id)
                .where(CashboxSessionModel.company_id == company_id)
                .where(CashboxSessionModel.branch_id == branch_id)
                .where(CashboxSessionModel.is_open == True)
            ).first()

            if cashbox_session:
                cashbox_session.is_open = False
                cashbox_session.closing_time = self._event_timestamp()
                session.add(cashbox_session)
                session.commit()
        self._cashbox_update_trigger += 1
        self._refresh_cashbox_caches()
