"""Mixin de Caja Chica — gastos e ingresos menores."""
import re
import reflex as rx
import sqlalchemy
from typing import Any, List
from decimal import Decimal, InvalidOperation
from datetime import datetime

from sqlmodel import select, desc

from app.models import (
    CashboxLog as CashboxLogModel,
    User as UserModel,
)
from app.i18n import MSG
from app.utils.formatting import fmt_input_num, fmt_price
from app.utils.sanitization import sanitize_notes_preserve_spaces
from ..types import CashboxLogEntry

_PETTY_CASH_ACTIONS = ["gasto_caja_chica", "ingreso_caja_chica"]

PETTY_CASH_CATEGORIES = [
    "Limpieza",
    "Mantenimiento",
    "Viáticos",
    "Alimentación",
    "Transporte",
    "Material de Oficina",
    "Servicios",
    "Reposición de Caja",
    "Devolución",
    "Otro",
]


class PettyCashMixin:
    """Gestión de caja chica: alta de movimientos, consulta, filtros y paginación."""

    cash_active_tab: str = "resumen"
    petty_cash_amount: str = ""
    petty_cash_quantity: str = "1"

    # ── Edición de movimiento existente ────────────────────────────────
    petty_cash_edit_modal_open: bool = False
    petty_cash_edit_id: str = ""
    petty_cash_edit_type: str = "egreso"
    petty_cash_edit_category: str = "Otro"
    petty_cash_edit_reason: str = ""
    petty_cash_edit_quantity: str = "1"
    petty_cash_edit_unit: str = "Unidad"
    petty_cash_edit_cost: str = ""
    petty_cash_edit_amount: str = ""
    petty_cash_unit: str = MSG.FALLBACK_UNIT
    petty_cash_cost: str = ""
    petty_cash_reason: str = ""
    petty_cash_type: str = "egreso"        # "egreso" | "ingreso"
    petty_cash_category: str = "Otro"
    petty_cash_modal_open: bool = False
    petty_cash_current_page: int = 1
    petty_cash_items_per_page: int = 10

    # Filtros de la tabla
    petty_cash_filter_type: str = ""          # "" | "egreso" | "ingreso"
    petty_cash_filter_date_from: str = ""     # YYYY-MM-DD
    petty_cash_filter_date_to: str = ""       # YYYY-MM-DD

    # ── Paginación ──────────────────────────────────────────────────────────
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

    # ── Modal ────────────────────────────────────────────────────────────────
    @rx.event
    def open_petty_cash_modal(self):
        self.petty_cash_modal_open = True
        self.petty_cash_type = "egreso"
        self.petty_cash_category = "Otro"
        self.petty_cash_amount = ""
        self.petty_cash_quantity = "1"
        self.petty_cash_cost = ""
        self.petty_cash_unit = MSG.FALLBACK_UNIT
        self.petty_cash_reason = ""

    @rx.event
    def close_petty_cash_modal(self):
        self.petty_cash_modal_open = False
        self.petty_cash_amount = ""
        self.petty_cash_quantity = "1"
        self.petty_cash_cost = ""
        self.petty_cash_unit = MSG.FALLBACK_UNIT
        self.petty_cash_reason = ""
        self.petty_cash_type = "egreso"
        self.petty_cash_category = "Otro"

    @rx.event
    def set_cash_tab(self, tab: str):
        self.cash_active_tab = tab
        self._refresh_cashbox_caches()

    # ── Setters de campos del modal ──────────────────────────────────────────
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

    @rx.event
    def set_petty_cash_reason(self, value: str):
        self.petty_cash_reason = sanitize_notes_preserve_spaces(value)

    @rx.event
    def set_petty_cash_type(self, value: str):
        self.petty_cash_type = value
        self.petty_cash_category = "Otro"

    @rx.event
    def set_petty_cash_category(self, value: str):
        self.petty_cash_category = value

    # ── Setters de filtros ───────────────────────────────────────────────────
    @rx.event
    def set_petty_cash_filter_type(self, value: str):
        self.petty_cash_filter_type = value
        self.petty_cash_current_page = 1
        self._refresh_cashbox_caches()

    @rx.event
    def set_petty_cash_filter_date_from(self, value: str):
        self.petty_cash_filter_date_from = value
        self.petty_cash_current_page = 1
        self._refresh_cashbox_caches()

    @rx.event
    def set_petty_cash_filter_date_to(self, value: str):
        self.petty_cash_filter_date_to = value
        self.petty_cash_current_page = 1
        self._refresh_cashbox_caches()

    @rx.event
    def clear_petty_cash_filters(self):
        self.petty_cash_filter_type = ""
        self.petty_cash_filter_date_from = ""
        self.petty_cash_filter_date_to = ""
        self.petty_cash_current_page = 1
        self._refresh_cashbox_caches()

    # ── Event handlers de edición ────────────────────────────────────────
    @rx.event
    def open_petty_cash_edit_modal(self, item_id: str):
        if not self.current_user["privileges"]["manage_cashbox"]:
            return rx.toast(MSG.PERM_CASH, duration=3000)
        company_id = self._company_id()
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            log = session.exec(
                select(CashboxLogModel)
                .where(CashboxLogModel.id == int(item_id))
                .where(CashboxLogModel.company_id == company_id)
            ).first()
            if not log:
                return rx.toast("Registro no encontrado", duration=3000)

            raw_notes = log.notes or ""
            cat_match = re.match(r'^\[(.+?)\]\s*', raw_notes)
            if cat_match:
                category = cat_match.group(1)
                display_notes = raw_notes[cat_match.end():]
            else:
                category = "Otro"
                display_notes = raw_notes

            qty = log.quantity or 1.0
            cost = log.cost or log.amount

            self.petty_cash_edit_id = item_id
            self.petty_cash_edit_type = "ingreso" if log.action == "ingreso_caja_chica" else "egreso"
            self.petty_cash_edit_category = category
            self.petty_cash_edit_reason = display_notes
            self.petty_cash_edit_quantity = fmt_input_num(qty)
            self.petty_cash_edit_unit = log.unit or MSG.FALLBACK_UNIT
            self.petty_cash_edit_cost = fmt_price(cost)
            self.petty_cash_edit_amount = fmt_price(log.amount)
            self.petty_cash_edit_modal_open = True

    @rx.event
    def close_petty_cash_edit_modal(self):
        self.petty_cash_edit_modal_open = False
        self.petty_cash_edit_id = ""

    @rx.event
    def set_petty_cash_edit_reason(self, value: str):
        self.petty_cash_edit_reason = sanitize_notes_preserve_spaces(value)

    @rx.event
    def set_petty_cash_edit_category(self, value: str):
        self.petty_cash_edit_category = value

    @rx.event
    def set_petty_cash_edit_quantity(self, value: Any):
        self.petty_cash_edit_quantity = str(value)
        self._calculate_petty_cash_edit_total()

    @rx.event
    def set_petty_cash_edit_unit(self, value: str):
        self.petty_cash_edit_unit = value

    @rx.event
    def set_petty_cash_edit_cost(self, value: Any):
        self.petty_cash_edit_cost = str(value)
        self._calculate_petty_cash_edit_total()

    def _calculate_petty_cash_edit_total(self):
        try:
            qty = Decimal(str(self.petty_cash_edit_quantity)) if self.petty_cash_edit_quantity else Decimal("0")
            cost = Decimal(str(self.petty_cash_edit_cost)) if self.petty_cash_edit_cost else Decimal("0")
            self.petty_cash_edit_amount = fmt_price(qty * cost)
        except (ValueError, InvalidOperation):
            pass

    @rx.event
    def save_petty_cash_edit(self):
        if not self.current_user["privileges"]["manage_cashbox"]:
            return rx.toast(MSG.PERM_CASH, duration=3000)
        if not self.petty_cash_edit_reason.strip():
            return rx.toast(MSG.VAL_ENTER_REASON, duration=3000)

        try:
            amount = float(self.petty_cash_edit_amount)
            if amount <= 0:
                return rx.toast(MSG.VAL_AMOUNT_GT_ZERO, duration=3000)
            quantity = float(self.petty_cash_edit_quantity) if self.petty_cash_edit_quantity else 1.0
            cost = float(self.petty_cash_edit_cost) if self.petty_cash_edit_cost else amount
        except ValueError:
            return rx.toast(MSG.VAL_INVALID_NUMERIC, duration=3000)

        cat = self.petty_cash_edit_category
        notes_text = (
            f"[{cat}] {self.petty_cash_edit_reason}"
            if cat and cat != "Otro"
            else self.petty_cash_edit_reason
        )

        company_id = self._company_id()
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            log = session.exec(
                select(CashboxLogModel)
                .where(CashboxLogModel.id == int(self.petty_cash_edit_id))
                .where(CashboxLogModel.company_id == company_id)
            ).first()
            if not log:
                return rx.toast("Registro no encontrado", duration=3000)

            log.notes = notes_text
            log.quantity = quantity
            log.unit = self.petty_cash_edit_unit
            log.cost = cost
            log.amount = amount
            session.commit()

        self.petty_cash_edit_modal_open = False
        self.petty_cash_edit_id = ""
        self._cashbox_update_trigger += 1
        self._refresh_cashbox_caches()
        return rx.toast("Movimiento actualizado correctamente.", duration=3000)

    @rx.var(cache=True)
    def petty_cash_filter_active(self) -> bool:
        return bool(
            self.petty_cash_filter_type
            or self.petty_cash_filter_date_from
            or self.petty_cash_filter_date_to
        )

    # ── Cálculo interno ──────────────────────────────────────────────────────
    def _calculate_petty_cash_total(self):
        try:
            qty = Decimal(str(self.petty_cash_quantity)) if self.petty_cash_quantity else Decimal("0")
            cost = Decimal(str(self.petty_cash_cost)) if self.petty_cash_cost else Decimal("0")
            self.petty_cash_amount = fmt_price(qty * cost)
        except (ValueError, InvalidOperation):
            pass

    # ── Alta de movimiento ───────────────────────────────────────────────────
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

        action = "ingreso_caja_chica" if self.petty_cash_type == "ingreso" else "gasto_caja_chica"
        cat = self.petty_cash_category
        notes_text = (
            f"[{cat}] {self.petty_cash_reason}"
            if cat and cat != "Otro"
            else self.petty_cash_reason
        )

        with rx.session() as session:
            session.info["tenant_bypass"] = True
            log = CashboxLogModel(
                company_id=company_id,
                branch_id=branch_id,
                user_id=user_id,
                action=action,
                amount=amount,
                quantity=quantity,
                unit=self.petty_cash_unit,
                cost=cost,
                notes=notes_text,
                timestamp=self._event_timestamp()
            )
            session.add(log)
            session.commit()

        self.petty_cash_amount = ""
        self.petty_cash_quantity = "1"
        self.petty_cash_cost = ""
        self.petty_cash_unit = MSG.FALLBACK_UNIT
        self.petty_cash_reason = ""
        self.petty_cash_type = "egreso"
        self.petty_cash_category = "Otro"
        self.petty_cash_modal_open = False
        self._cashbox_update_trigger += 1
        self._refresh_cashbox_caches()
        return rx.toast(MSG.CASH_MOVEMENT_OK, duration=3000)

    # ── Consultas con filtros ────────────────────────────────────────────────
    def _petty_cash_actions(self) -> list[str]:
        if self.petty_cash_filter_type == "egreso":
            return ["gasto_caja_chica"]
        if self.petty_cash_filter_type == "ingreso":
            return ["ingreso_caja_chica"]
        return _PETTY_CASH_ACTIONS

    def _apply_petty_cash_date_filters(self, statement):
        if self.petty_cash_filter_date_from:
            try:
                dt_from = datetime.strptime(self.petty_cash_filter_date_from, "%Y-%m-%d")
                statement = statement.where(CashboxLogModel.timestamp >= dt_from)
            except ValueError:
                pass
        if self.petty_cash_filter_date_to:
            try:
                dt_to = datetime.strptime(self.petty_cash_filter_date_to, "%Y-%m-%d")
                dt_to = dt_to.replace(hour=23, minute=59, second=59)
                statement = statement.where(CashboxLogModel.timestamp <= dt_to)
            except ValueError:
                pass
        return statement

    def _petty_cash_query(self):
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
            .where(CashboxLogModel.action.in_(self._petty_cash_actions()))
            .where(CashboxLogModel.company_id == company_id)
            .where(CashboxLogModel.branch_id == branch_id)
        )
        statement = self._apply_petty_cash_date_filters(statement)
        return statement.order_by(desc(CashboxLogModel.timestamp))

    def _petty_cash_count(self) -> int:
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return 0
        statement = (
            select(sqlalchemy.func.count())
            .select_from(CashboxLogModel)
            .where(CashboxLogModel.action.in_(self._petty_cash_actions()))
            .where(CashboxLogModel.company_id == company_id)
            .where(CashboxLogModel.branch_id == branch_id)
        )
        statement = self._apply_petty_cash_date_filters(statement)
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            return session.exec(statement).one()

    def _fetch_petty_cash(
        self, offset: int | None = None, limit: int | None = None
    ) -> List[CashboxLogEntry]:
        with rx.session() as session:
            session.info["tenant_bypass"] = True
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

                fmt_qty = fmt_input_num(qty)

                raw_notes = log.notes or ""
                cat_match = re.match(r'^\[(.+?)\]\s*', raw_notes)
                if cat_match:
                    category = cat_match.group(1)
                    display_notes = raw_notes[cat_match.end():]
                else:
                    category = ""
                    display_notes = raw_notes

                movement_type = "ingreso" if log.action == "ingreso_caja_chica" else "egreso"

                entry: CashboxLogEntry = {
                    "id": str(log.id),
                    "action": log.action,
                    "timestamp": self._format_event_timestamp(log.timestamp),
                    "user": username,
                    "opening_amount": 0.0,
                    "closing_total": 0.0,
                    "totals_by_method": [],
                    "notes": display_notes,
                    "amount": log.amount,
                    "quantity": qty,
                    "unit": log.unit or MSG.FALLBACK_UNIT,
                    "cost": cost,
                    "formatted_amount": f"{log.amount:.2f}",
                    "formatted_cost": f"{cost:.2f}",
                    "formatted_quantity": fmt_qty,
                    "category": category,
                    "movement_type": movement_type,
                }
                filtered.append(entry)
            return filtered

    def _fetch_all_petty_cash_filtered(self) -> List[CashboxLogEntry]:
        """Obtiene todos los movimientos filtrados sin paginación (para exportar)."""
        return self._fetch_petty_cash()
