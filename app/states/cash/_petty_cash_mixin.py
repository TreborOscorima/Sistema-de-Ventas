"""Mixin de Caja Chica — gastos menores."""
import reflex as rx
import sqlalchemy
from typing import Any, List
from decimal import Decimal, InvalidOperation

from sqlmodel import select, desc

from app.models import (
    CashboxLog as CashboxLogModel,
    User as UserModel,
)
from app.i18n import MSG
from app.utils.sanitization import sanitize_notes_preserve_spaces
from ..types import CashboxLogEntry


class PettyCashMixin:
    """Gestión de caja chica: alta de gastos, consulta y paginación."""

    cash_active_tab: str = "resumen"
    petty_cash_amount: str = ""  # Este será el Total calculado o manual
    petty_cash_quantity: str = "1"
    petty_cash_unit: str = MSG.FALLBACK_UNIT
    petty_cash_cost: str = ""
    petty_cash_reason: str = ""
    petty_cash_modal_open: bool = False
    petty_cash_current_page: int = 1
    petty_cash_items_per_page: int = 10

    @rx.event
    def set_petty_cash_page(self, page: int):
        if 1 <= page <= self.petty_cash_total_pages:
            self.petty_cash_current_page = page
            self._refresh_cashbox_caches()

    @rx.event
    def prev_petty_cash_page(self):
        if self.petty_cash_current_page > 1:
            self.petty_cash_current_page -= 1
            self._refresh_cashbox_caches()

    @rx.event
    def next_petty_cash_page(self):
        if self.petty_cash_current_page < self.petty_cash_total_pages:
            self.petty_cash_current_page += 1
            self._refresh_cashbox_caches()

    @rx.event
    def open_petty_cash_modal(self):
        self.petty_cash_modal_open = True

    @rx.event
    def close_petty_cash_modal(self):
        self.petty_cash_modal_open = False

    @rx.event
    def set_cash_tab(self, tab: str):
        self.cash_active_tab = tab
        self._refresh_cashbox_caches()

    @rx.event
    def set_petty_cash_amount(self, value: str | int | float):
        self.petty_cash_amount = str(value)

    @rx.event
    def set_petty_cash_quantity(self, value: Any):
        self.petty_cash_quantity = str(value)
        self._calculate_petty_cash_total()

    @rx.event
    def set_petty_cash_unit(self, value: str):
        self.petty_cash_unit = value

    @rx.event
    def set_petty_cash_cost(self, value: Any):
        self.petty_cash_cost = str(value)
        self._calculate_petty_cash_total()

    def _calculate_petty_cash_total(self):
        try:
            qty = Decimal(str(self.petty_cash_quantity)) if self.petty_cash_quantity else Decimal("0")
            cost = Decimal(str(self.petty_cash_cost)) if self.petty_cash_cost else Decimal("0")
            self.petty_cash_amount = str(qty * cost)
        except (ValueError, InvalidOperation):
            pass

    @rx.event
    def set_petty_cash_reason(self, value: str):
        self.petty_cash_reason = sanitize_notes_preserve_spaces(value)

    @rx.event
    def add_petty_cash_movement(self):
        if not self.current_user["privileges"]["manage_cashbox"]:
            return rx.toast(MSG.PERM_CASH, duration=3000)
        block = self._require_active_subscription()
        if block:
            return block
        if not self.cashbox_is_open:
            return rx.toast(MSG.CASH_OPEN_REQUIRED, duration=3000)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast(MSG.VAL_COMPANY_UNDEFINED, duration=3000)

        try:
            amount = float(self.petty_cash_amount)
            if amount <= 0:
                return rx.toast(MSG.VAL_AMOUNT_GT_ZERO, duration=3000)

            quantity = float(self.petty_cash_quantity) if self.petty_cash_quantity else 1.0
            cost = float(self.petty_cash_cost) if self.petty_cash_cost else amount

        except ValueError:
            return rx.toast(MSG.VAL_INVALID_NUMERIC, duration=3000)

        if not self.petty_cash_reason:
            return rx.toast(MSG.VAL_ENTER_REASON, duration=3000)

        user_id = self.current_user.get("id")
        if not user_id:
            return rx.toast(MSG.VAL_USER_NOT_FOUND, duration=3000)

        with rx.session() as session:

            log = CashboxLogModel(
                company_id=company_id,
                branch_id=branch_id,
                user_id=user_id,
                action="gasto_caja_chica",
                amount=amount,
                quantity=quantity,
                unit=self.petty_cash_unit,
                cost=cost,
                notes=self.petty_cash_reason,
                timestamp=self._event_timestamp()
            )
            session.add(log)
            session.commit()

        self.petty_cash_amount = ""
        self.petty_cash_quantity = "1"
        self.petty_cash_cost = ""
        self.petty_cash_unit = MSG.FALLBACK_UNIT
        self.petty_cash_reason = ""
        self.petty_cash_modal_open = False
        self._cashbox_update_trigger += 1
        self._refresh_cashbox_caches()
        return rx.toast(MSG.CASH_MOVEMENT_OK, duration=3000)

    def _petty_cash_query(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return (
                select(CashboxLogModel, UserModel.username)
                .join(UserModel)
                .where(sqlalchemy.false())
            )
        return (
            select(CashboxLogModel, UserModel.username)
            .join(UserModel)
            .where(CashboxLogModel.action == "gasto_caja_chica")
            .where(CashboxLogModel.company_id == company_id)
            .where(CashboxLogModel.branch_id == branch_id)
            .order_by(desc(CashboxLogModel.timestamp))
        )

    def _petty_cash_count(self) -> int:
        statement = (
            select(sqlalchemy.func.count())
            .select_from(CashboxLogModel)
            .where(CashboxLogModel.action == "gasto_caja_chica")
        )
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return 0
        statement = statement.where(CashboxLogModel.company_id == company_id)
        statement = statement.where(CashboxLogModel.branch_id == branch_id)
        with rx.session() as session:
            return session.exec(statement).one()

    def _fetch_petty_cash(
        self, offset: int | None = None, limit: int | None = None
    ) -> List[CashboxLogEntry]:
        with rx.session() as session:
            statement = self._petty_cash_query()
            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)
            results = session.exec(statement).all()

            filtered: List[CashboxLogEntry] = []
            for log, username in results:
                qty = log.quantity or 1.0
                cost = log.cost or log.amount

                # Formatear cantidad: entero si no hay decimales, si no 2 decimales
                fmt_qty = f"{int(qty)}" if qty % 1 == 0 else f"{qty:.2f}"

                entry: CashboxLogEntry = {
                    "id": str(log.id),
                    "action": log.action,
                    "timestamp": self._format_event_timestamp(log.timestamp),
                    "user": username,
                    "opening_amount": 0.0,
                    "closing_total": 0.0,
                    "totals_by_method": [],
                    "notes": log.notes,
                    "amount": log.amount,
                    "quantity": qty,
                    "unit": log.unit or MSG.FALLBACK_UNIT,
                    "cost": cost,
                    "formatted_amount": f"{log.amount:.2f}",
                    "formatted_cost": f"{cost:.2f}",
                    "formatted_quantity": fmt_qty,
                }
                filtered.append(entry)
            return filtered
