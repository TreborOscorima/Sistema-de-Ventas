"""Estado de Caja - Gestión de sesiones y movimientos de caja.

Este módulo maneja toda la lógica relacionada con la caja registradora:

Funcionalidades principales:
- Apertura y cierre de sesiones de caja
- Registro de movimientos (ventas, gastos, cobranzas)
- Historial de ventas del día con filtros
- Caja chica (gastos menores)
- Anulación de ventas con restauración de stock
- Exportación de reportes (Excel, PDF)
- Resumen por método de pago

Flujo típico:
    1. open_cashbox_session() - Aperturar caja con monto inicial
    2. Registrar ventas/cobranzas durante el día
    3. open_cashbox_close_modal() - Ver resumen del día
    4. close_cashbox_day() - Cerrar caja

Clases:
    CashState: Estado principal con toda la lógica de caja
"""
import reflex as rx
from typing import List, Dict, Any
import datetime
import uuid
import logging
import json
import html
import io
import sqlalchemy
from io import BytesIO
from sqlmodel import select, desc
from sqlalchemy.orm import selectinload
from app.enums import PaymentMethodType, SaleStatus
from app.models import (
    CashboxSession as CashboxSessionModel,
    CashboxLog as CashboxLogModel,
    User as UserModel,
    Sale,
    SaleItem,
    SalePayment,
    StockMovement,
    Product,
    ProductVariant,
    ProductBatch,
)
from app.utils.sanitization import (
    sanitize_notes,
    sanitize_reason,
    sanitize_reason_preserve_spaces,
    sanitize_notes_preserve_spaces,
)
from .types import CashboxSale, CashboxSession, CashboxLogEntry, Movement
from .mixin_state import MixinState
from app.utils.exports import (
    create_excel_workbook,
    style_header_row,
    add_data_rows,
    auto_adjust_column_widths,
    apply_wrap_text,
    create_pdf_report,
    add_company_header,
    add_totals_row_with_formulas,
    add_notes_section,
    CURRENCY_FORMAT,
    THIN_BORDER,
    POSITIVE_FILL,
    NEGATIVE_FILL,
    WARNING_FILL,
)
from app.constants import CASHBOX_INCOME_ACTIONS, CASHBOX_EXPENSE_ACTIONS


class CashState(MixinState):
    """Estado de gestión de caja registradora.
    
    Maneja sesiones de caja, movimientos, reportes y exportaciones.
    Requiere permisos 'view_cashbox' y 'manage_cashbox' según la operación.
    
    Attributes:
        cashbox_filter_start_date: Filtro de fecha inicio para ventas
        cashbox_filter_end_date: Filtro de fecha fin para ventas
        cashbox_current_page: Página actual de paginación
        show_cashbox_advances: Mostrar adelantos en listado
        sale_delete_modal_open: Estado del modal de anulación
        cashbox_close_modal_open: Estado del modal de cierre
        cash_active_tab: Tab activo (resumen/historial/caja_chica)
        petty_cash_*: Campos para gastos de caja chica
    """
    # cashbox_sales: List[CashboxSale] = [] # Eliminado a favor de la BD
    cashbox_filter_start_date: str = ""
    cashbox_filter_end_date: str = ""
    cashbox_staged_start_date: str = ""
    cashbox_staged_end_date: str = ""
    cashbox_current_page: int = 1
    cashbox_items_per_page: int = 5
    show_cashbox_advances: bool = True
    sale_delete_modal_open: bool = False
    sale_to_delete: str = ""
    sale_delete_reason: str = ""
    cashbox_close_modal_open: bool = False
    summary_by_method: list[dict] = []
    cashbox_close_summary_sales: List[CashboxSale] = []
    cashbox_close_summary_date: str = ""
    cashbox_close_opening_amount: float = 0.0
    cashbox_close_income_total: float = 0.0
    cashbox_close_expense_total: float = 0.0
    cashbox_close_expected_total: float = 0.0
    cashbox_sessions: Dict[str, CashboxSession] = {}
    cashbox_open_amount_input: str = "0"
    cashbox_logs: List[CashboxLogEntry] = []
    cashbox_log_filter_start_date: str = ""
    cashbox_log_filter_end_date: str = ""
    cashbox_log_staged_start_date: str = ""
    cashbox_log_staged_end_date: str = ""
    cashbox_log_current_page: int = 1
    cashbox_log_items_per_page: int = 10
    cashbox_log_modal_open: bool = False
    cashbox_log_selected: CashboxLogEntry | None = None
    expanded_cashbox_sale_id: str = ""
    _cashbox_update_trigger: int = 0
    cashbox_is_open_cached: bool = False

    @rx.event
    def toggle_cashbox_sale_detail(self, sale_id: str):
        value = str(sale_id or "").strip()
        if not value:
            return
        if self.expanded_cashbox_sale_id == value:
            self.expanded_cashbox_sale_id = ""
        else:
            self.expanded_cashbox_sale_id = value
    
    cash_active_tab: str = "resumen"
    petty_cash_amount: str = "" # Este será el Total calculado o manual
    petty_cash_quantity: str = "1"
    petty_cash_unit: str = "Unidad"
    petty_cash_cost: str = ""
    petty_cash_reason: str = ""
    petty_cash_modal_open: bool = False
    petty_cash_current_page: int = 1
    petty_cash_items_per_page: int = 10

    @rx.event
    def set_petty_cash_page(self, page: int):
        if 1 <= page <= self.petty_cash_total_pages:
            self.petty_cash_current_page = page

    @rx.event
    def prev_petty_cash_page(self):
        if self.petty_cash_current_page > 1:
            self.petty_cash_current_page -= 1

    @rx.event
    def next_petty_cash_page(self):
        if self.petty_cash_current_page < self.petty_cash_total_pages:
            self.petty_cash_current_page += 1

    @rx.event
    def open_petty_cash_modal(self):
        self.petty_cash_modal_open = True

    @rx.event
    def close_petty_cash_modal(self):
        self.petty_cash_modal_open = False

    @rx.event
    def set_cash_tab(self, tab: str):
        self.cash_active_tab = tab

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
            qty = float(self.petty_cash_quantity) if self.petty_cash_quantity else 0
            cost = float(self.petty_cash_cost) if self.petty_cash_cost else 0
            self.petty_cash_amount = str(qty * cost)
        except ValueError:
            pass

    @rx.event
    def set_petty_cash_reason(self, value: str):
        self.petty_cash_reason = sanitize_notes_preserve_spaces(value)

    @rx.event
    def add_petty_cash_movement(self):
        if not self.current_user["privileges"]["manage_cashbox"]:
            return rx.toast("No tiene permisos para gestionar la caja.", duration=3000)
        block = self._require_active_subscription()
        if block:
            return block
        if not self.cashbox_is_open:
            return rx.toast("Debe aperturar la caja para registrar movimientos.", duration=3000)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        
        try:
            amount = float(self.petty_cash_amount)
            if amount <= 0:
                return rx.toast("El monto total debe ser mayor a 0.", duration=3000)
            
            quantity = float(self.petty_cash_quantity) if self.petty_cash_quantity else 1.0
            cost = float(self.petty_cash_cost) if self.petty_cash_cost else amount
            
        except ValueError:
            return rx.toast("Valores numéricos inválidos.", duration=3000)
            
        if not self.petty_cash_reason:
            return rx.toast("Ingrese un motivo.", duration=3000)
            
        user_id = self.current_user.get("id")
        if not user_id:
            return rx.toast("Usuario no encontrado.", duration=3000)
        
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
                timestamp=datetime.datetime.now()
            )
            session.add(log)
            session.commit()
            
        self.petty_cash_amount = ""
        self.petty_cash_quantity = "1"
        self.petty_cash_cost = ""
        self.petty_cash_unit = "Unidad"
        self.petty_cash_reason = ""
        self.petty_cash_modal_open = False
        self._cashbox_update_trigger += 1
        return rx.toast("Movimiento registrado correctamente.", duration=3000)

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
                    "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "user": username,
                    "opening_amount": 0.0,
                    "closing_total": 0.0,
                    "totals_by_method": [],
                    "notes": log.notes,
                    "amount": log.amount,
                    "quantity": qty,
                    "unit": log.unit or "Unidad",
                    "cost": cost,
                    "formatted_amount": f"{log.amount:.2f}",
                    "formatted_cost": f"{cost:.2f}",
                    "formatted_quantity": fmt_qty,
                }
                filtered.append(entry)
            return filtered

    @rx.var
    def petty_cash_movements(self) -> List[CashboxLogEntry]:
        _ = self._cashbox_update_trigger
        page = max(self.petty_cash_current_page, 1)
        per_page = max(self.petty_cash_items_per_page, 1)
        offset = (page - 1) * per_page
        return self._fetch_petty_cash(offset=offset, limit=per_page)

    @rx.var
    def paginated_petty_cash_movements(self) -> List[CashboxLogEntry]:
        return self.petty_cash_movements

    @rx.var
    def petty_cash_total_pages(self) -> int:
        _ = self._cashbox_update_trigger
        total = self._petty_cash_count()
        if total == 0:
            return 1
        return (total + self.petty_cash_items_per_page - 1) // self.petty_cash_items_per_page

    @rx.var
    def cashbox_opening_amount_display(self) -> str:
        return f"{self.cashbox_opening_amount:.2f}"

    @rx.var
    def current_cashbox_session(self) -> CashboxSession:
        # Dependencia para forzar actualizacion
        _ = self._cashbox_update_trigger
        
        username = "guest"
        user_id = None
        if hasattr(self, "current_user") and self.current_user:
             username = self.current_user.get("username", "guest")
             user_id = self.current_user.get("id")
        
        if not user_id:
            return {
                "opening_amount": 0.0,
                "opening_time": "",
                "closing_time": "",
                "is_open": False,
                "opened_by": username,
            }
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return {
                "opening_amount": 0.0,
                "opening_time": "",
                "closing_time": "",
                "is_open": False,
                "opened_by": username,
            }

        with rx.session() as session:
            cashbox_session = session.exec(
                select(CashboxSessionModel)
                .where(CashboxSessionModel.user_id == user_id)
                .where(CashboxSessionModel.company_id == company_id)
                .where(CashboxSessionModel.branch_id == branch_id)
                .where(CashboxSessionModel.is_open == True)
            ).first()
            
            if cashbox_session:
                return {
                    "opening_amount": cashbox_session.opening_amount,
                    "opening_time": cashbox_session.opening_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "closing_time": "",
                    "is_open": True,
                    "opened_by": username,
                }
            
            return {
                "opening_amount": 0.0,
                "opening_time": "",
                "closing_time": "",
                "is_open": False,
                "opened_by": username,
            }

    @rx.var
    def cashbox_is_open(self) -> bool:
        return bool(self.current_cashbox_session.get("is_open"))

    @rx.var
    def cashbox_opening_amount(self) -> float:
        session_data = self.current_cashbox_session
        if not session_data.get("is_open"):
             return 0.0
        
        opening_amount = float(session_data.get("opening_amount", 0))
        opening_time_str = session_data.get("opening_time")
        if not opening_time_str:
            return opening_amount

        try:
            opening_time = datetime.datetime.strptime(opening_time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return opening_amount

        user_id = self.current_user.get("id")
        if not user_id:
            return opening_amount

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return opening_amount

        with rx.session() as session:
            # Sumar gastos
            statement = select(sqlalchemy.func.sum(CashboxLogModel.amount)).where(
                CashboxLogModel.user_id == user_id,
                CashboxLogModel.action == "gasto_caja_chica",
                CashboxLogModel.timestamp >= opening_time,
                CashboxLogModel.company_id == company_id,
                CashboxLogModel.branch_id == branch_id,
            )
            expenses = session.exec(statement).one()
            expenses_value = float(expenses or 0)
            return opening_amount - expenses_value

    @rx.var
    def cashbox_opening_time(self) -> str:
        return self.current_cashbox_session.get("opening_time", "")

    def _require_cashbox_open(self):
        if not self.cashbox_is_open:
            return rx.toast("Debe aperturar la caja para operar.", duration=3000)
        return None

    def _cashbox_guard(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        if not self.cashbox_is_open:
            return rx.toast(
                "Debe aperturar la caja para operar la gestion de caja.",
                duration=3000,
            )
        return None

    def _cashbox_time_range(
        self, date: str
    ) -> tuple[datetime.datetime, datetime.datetime, dict[str, Any] | None]:
        session_info = self._active_cashbox_session_info()
        if session_info:
            start_dt = session_info.get("opening_time") or datetime.datetime.now()
            end_dt = session_info.get("closing_time") or datetime.datetime.now()
            return start_dt, end_dt, session_info
        try:
            target_date = datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            target_date = datetime.datetime.now()
        start_dt = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = target_date.replace(hour=23, minute=59, second=59, microsecond=0)
        return start_dt, end_dt, None

    def _cashbox_range_for_log(
        self,
        log: CashboxLogModel,
    ) -> tuple[datetime.datetime, datetime.datetime, int | None, str, datetime.datetime]:
        """Obtiene rango de tiempo para un cierre histórico basado en el log."""
        timestamp = log.timestamp or datetime.datetime.now()
        report_date = timestamp.strftime("%Y-%m-%d")
        start_dt = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = timestamp.replace(hour=23, minute=59, second=59, microsecond=0)
        user_id = log.user_id
        company_id = log.company_id
        branch_id = log.branch_id
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
        return self._round_currency(float(total or 0))

    def _build_cashbox_summary_for_range(
        self,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
        company_id: int,
        branch_id: int,
        user_id: int | None = None,
    ) -> list[dict]:
        method_col = sqlalchemy.func.coalesce(
            CashboxLogModel.payment_method, "No especificado"
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
            label = (method or "No especificado").strip() or "No especificado"
            summary.append(
                {
                    "method": label,
                    "count": int(count or 0),
                    "total": self._round_currency(float(amount or 0)),
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

            import re

            result: list[CashboxSale] = []
            for log, username in logs:
                method_label = (log.payment_method or "No especificado").strip() or "No especificado"
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
                    time_label = timestamp.strftime("%H:%M")
                result.append(
                    {
                        "sale_id": str(log.id),
                        "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "time": time_label,
                        "user": username or "Desconocido",
                        "payment_method": method_label,
                        "payment_label": method_label,
                        "payment_details": payment_detail,
                        "concept": concept,
                        "amount": self._round_currency(float(log.amount or 0)),
                        "total": log.amount,
                        "is_deleted": False,
                        "payment_breakdown": [
                            {
                                "label": method_label,
                                "amount": self._round_currency(float(log.amount or 0)),
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
        return self._round_currency(float(total or 0))

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
        user_id = self.current_user.get("id") if hasattr(self, "current_user") else None
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not user_id or not company_id or not branch_id:
            self.cashbox_is_open_cached = False
            return
        with rx.session() as session:
            opened = session.exec(
                select(CashboxSessionModel.id)
                .where(CashboxSessionModel.user_id == user_id)
                .where(CashboxSessionModel.company_id == company_id)
                .where(CashboxSessionModel.branch_id == branch_id)
                .where(CashboxSessionModel.is_open == True)
                .limit(1)
            ).first()
        self.cashbox_is_open_cached = opened is not None

    @rx.event
    def set_cashbox_open_amount_input(self, value: float | str):
        self.cashbox_open_amount_input = str(value or "").strip()

    @rx.event
    def open_cashbox_session(self):
        if not self.current_user["privileges"]["manage_cashbox"]:
            return rx.toast("No tiene permisos para gestionar la caja.", duration=3000)
        block = self._require_active_subscription()
        if block:
            return block
        user_id = self.current_user.get("id")
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        if self.current_user["role"].lower() == "cajero" and not hasattr(self, "token"):
            return rx.toast("Inicie sesión para abrir caja.", duration=3000)
        
        try:
            amount = float(self.cashbox_open_amount_input) if self.cashbox_open_amount_input else 0
        except ValueError:
            amount = 0
        amount = self._round_currency(amount)
        
        if amount < 0:
            return rx.toast("Ingrese un monto válido para la caja inicial.", duration=3000)
            
        if not user_id:
            return rx.toast("Usuario no encontrado.", duration=3000)
        with rx.session() as session:
            existing = session.exec(
                select(CashboxSessionModel)
                .where(CashboxSessionModel.user_id == user_id)
                .where(CashboxSessionModel.company_id == company_id)
                .where(CashboxSessionModel.branch_id == branch_id)
                .where(CashboxSessionModel.is_open == True)
            ).first()
            
            if existing:
                 return rx.toast("Ya existe una caja abierta.", duration=3000)

            new_session = CashboxSessionModel(
                company_id=company_id,
                branch_id=branch_id,
                user_id=user_id,
                opening_amount=amount,
                opening_time=datetime.datetime.now(),
                is_open=True
            )
            session.add(new_session)
            session.commit()
            session.refresh(new_session)
            
            log = CashboxLogModel(
                company_id=company_id,
                branch_id=branch_id,
                user_id=user_id,
                action="apertura",
                amount=amount,
                notes="Apertura de caja",
                timestamp=datetime.datetime.now()
            )
            session.add(log)
            session.commit()
            
        self.cashbox_open_amount_input = ""
        self._cashbox_update_trigger += 1
        self.cashbox_is_open_cached = True
        return rx.toast("Caja abierta. Jornada iniciada.", duration=3000)

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
                cashbox_session.closing_time = datetime.datetime.now()
                session.add(cashbox_session)
                session.commit()
        self.cashbox_is_open_cached = False
        
        self._cashbox_update_trigger += 1

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

        if self.cashbox_log_filter_start_date:
            try:
                start_date = datetime.datetime.strptime(
                    self.cashbox_log_filter_start_date, "%Y-%m-%d"
                )
                statement = statement.where(CashboxLogModel.timestamp >= start_date)
            except ValueError:
                pass

        if self.cashbox_log_filter_end_date:
            try:
                end_date = datetime.datetime.strptime(
                    self.cashbox_log_filter_end_date, "%Y-%m-%d"
                )
                end_date = end_date.replace(hour=23, minute=59, second=59)
                statement = statement.where(CashboxLogModel.timestamp <= end_date)
            except ValueError:
                pass

        return statement

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

        if self.cashbox_log_filter_start_date:
            try:
                start_date = datetime.datetime.strptime(
                    self.cashbox_log_filter_start_date, "%Y-%m-%d"
                )
                statement = statement.where(CashboxLogModel.timestamp >= start_date)
            except ValueError:
                pass

        if self.cashbox_log_filter_end_date:
            try:
                end_date = datetime.datetime.strptime(
                    self.cashbox_log_filter_end_date, "%Y-%m-%d"
                )
                end_date = end_date.replace(hour=23, minute=59, second=59)
                statement = statement.where(CashboxLogModel.timestamp <= end_date)
            except ValueError:
                pass

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
                    "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "user": username,
                    "opening_amount": log.amount if log.action == "apertura" else 0.0,
                    "closing_total": log.amount if log.action == "cierre" else 0.0,
                    "totals_by_method": [],
                    "notes": log.notes,
                    "amount": log.amount,
                }
                filtered.append(entry)

            return filtered

    @rx.var
    def filtered_cashbox_logs(self) -> list[CashboxLogEntry]:
        _ = self._cashbox_update_trigger
        if not self.current_user["privileges"]["view_cashbox"]:
            return []
        page = max(self.cashbox_log_current_page, 1)
        per_page = max(self.cashbox_log_items_per_page, 1)
        offset = (page - 1) * per_page
        return self._fetch_cashbox_logs(offset=offset, limit=per_page)

    @rx.var
    def paginated_cashbox_logs(self) -> list[CashboxLogEntry]:
        return self.filtered_cashbox_logs

    @rx.var
    def cashbox_log_total_pages(self) -> int:
        _ = self._cashbox_update_trigger
        total = self._cashbox_logs_count()
        if total == 0:
            return 1
        return (total + self.cashbox_log_items_per_page - 1) // self.cashbox_log_items_per_page

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

    @rx.event
    def set_cashbox_log_staged_start_date(self, value: str):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        self.cashbox_log_staged_start_date = value or ""

    @rx.event
    def set_cashbox_log_staged_end_date(self, value: str):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        self.cashbox_log_staged_end_date = value or ""

    @rx.event
    def apply_cashbox_log_filters(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        self.cashbox_log_filter_start_date = self.cashbox_log_staged_start_date
        self.cashbox_log_filter_end_date = self.cashbox_log_staged_end_date
        self.cashbox_log_current_page = 1

    @rx.event
    def reset_cashbox_log_filters(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        self.cashbox_log_filter_start_date = ""
        self.cashbox_log_filter_end_date = ""
        self.cashbox_log_staged_start_date = ""
        self.cashbox_log_staged_end_date = ""
        self.cashbox_log_current_page = 1

    @rx.event
    def set_cashbox_log_page(self, page: int):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        if 1 <= page <= self.cashbox_log_total_pages:
            self.cashbox_log_current_page = page

    @rx.event
    def prev_cashbox_log_page(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        if self.cashbox_log_current_page > 1:
            self.cashbox_log_current_page -= 1

    @rx.event
    def next_cashbox_log_page(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        if self.cashbox_log_current_page < self.cashbox_log_total_pages:
            self.cashbox_log_current_page += 1

    @rx.event
    def set_cashbox_page(self, page: int):
        denial = self._cashbox_guard()
        if denial:
            return denial
        if 1 <= page <= self.cashbox_total_pages:
            self.cashbox_current_page = page

    @rx.event
    def set_show_cashbox_advances(self, value: bool | str):
        denial = self._cashbox_guard()
        if denial:
            return denial
        if isinstance(value, str):
            value = value.lower() in ["true", "1", "on", "yes"]
        self.show_cashbox_advances = bool(value)

    @rx.event
    def prev_cashbox_page(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        if self.cashbox_current_page > 1:
            self.cashbox_current_page -= 1

    @rx.event
    def next_cashbox_page(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        total_pages = self.cashbox_total_pages
        if self.cashbox_current_page < total_pages:
            self.cashbox_current_page += 1

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

        if self.cashbox_filter_start_date:
            try:
                start_date = datetime.datetime.strptime(
                    self.cashbox_filter_start_date, "%Y-%m-%d"
                )
                query = query.where(Sale.timestamp >= start_date)
            except ValueError:
                pass

        if self.cashbox_filter_end_date:
            try:
                end_date = datetime.datetime.strptime(
                    self.cashbox_filter_end_date, "%Y-%m-%d"
                )
                end_date = end_date.replace(hour=23, minute=59, second=59)
                query = query.where(Sale.timestamp <= end_date)
            except ValueError:
                pass

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

        if self.cashbox_filter_start_date:
            try:
                start_date = datetime.datetime.strptime(
                    self.cashbox_filter_start_date, "%Y-%m-%d"
                )
                query = query.where(Sale.timestamp >= start_date)
            except ValueError:
                pass

        if self.cashbox_filter_end_date:
            try:
                end_date = datetime.datetime.strptime(
                    self.cashbox_filter_end_date, "%Y-%m-%d"
                )
                end_date = end_date.replace(hour=23, minute=59, second=59)
                query = query.where(Sale.timestamp <= end_date)
            except ValueError:
                pass

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
        items: list[dict] = []
        items_total = 0
        for item in sale.items or []:
            items.append(
                {
                    "description": item.product_name_snapshot,
                    "quantity": item.quantity,
                    "unit": "Unidad",
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
            "timestamp": sale.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "user": user.username if user else "Desconocido",
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

    @rx.var
    def filtered_cashbox_sales(self) -> list[CashboxSale]:
        _ = self._cashbox_update_trigger
        if not self.current_user["privileges"]["view_cashbox"]:
            return []
        page = max(self.cashbox_current_page, 1)
        per_page = max(self.cashbox_items_per_page, 1)
        offset = (page - 1) * per_page
        return self._fetch_cashbox_sales(offset=offset, limit=per_page)

    @rx.var
    def paginated_cashbox_sales(self) -> list[CashboxSale]:
        return self.filtered_cashbox_sales

    @rx.var
    def cashbox_total_pages(self) -> int:
        _ = self._cashbox_update_trigger
        total = self._cashbox_sales_count()
        if total == 0:
            return 1
        return (total + self.cashbox_items_per_page - 1) // self.cashbox_items_per_page

    @rx.var
    def cashbox_close_totals(self) -> list[dict[str, str]]:
        if not self.current_user["privileges"]["view_cashbox"]:
            return []
        return [
            {
                "method": item.get("method", "No especificado"),
                "count": str(int(item.get("count", 0))),
                "total": self._format_currency(item.get("total", 0)),
            }
            for item in self.summary_by_method
            if item.get("total", 0) > 0
        ]

    @rx.var
    def cashbox_close_total_amount(self) -> str:
        total_value = self.cashbox_close_expected_total
        if total_value == 0 and self.summary_by_method:
            total_value = sum(item.get("total", 0) for item in self.summary_by_method)
        return self._format_currency(total_value)

    @rx.var
    def cashbox_close_opening_amount_display(self) -> str:
        return self._format_currency(self.cashbox_close_opening_amount)

    @rx.var
    def cashbox_close_income_total_display(self) -> str:
        return self._format_currency(self.cashbox_close_income_total)

    @rx.var
    def cashbox_close_expense_total_display(self) -> str:
        return self._format_currency(self.cashbox_close_expense_total)

    @rx.var
    def cashbox_close_expected_total_display(self) -> str:
        return self._format_currency(self.cashbox_close_expected_total)

    @rx.var
    def cashbox_close_sales(self) -> list[CashboxSale]:
        if not self.current_user["privileges"]["view_cashbox"]:
            return []
        return self.cashbox_close_summary_sales

    @rx.event
    def open_cashbox_close_modal(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        breakdown = self._build_cashbox_close_breakdown(today)
        day_sales = self._get_day_sales(today)
        summary = breakdown["summary"]
        if not day_sales and not summary and breakdown["opening_amount"] == 0:
            return rx.toast("No hay movimientos de caja hoy.", duration=3000)
        self.summary_by_method = summary
        self.cashbox_close_summary_sales = day_sales
        self.cashbox_close_summary_date = today
        self.cashbox_close_opening_amount = breakdown["opening_amount"]
        self.cashbox_close_income_total = breakdown["income_total"]
        self.cashbox_close_expense_total = breakdown["expense_total"]
        self.cashbox_close_expected_total = breakdown["expected_total"]
        self.cashbox_close_modal_open = True

    @rx.event
    def close_cashbox_close_modal(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        self._reset_cashbox_close_summary()

    @rx.event
    def export_cashbox_report(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)

        sales = self._fetch_cashbox_sales()
        if not sales:
            return rx.toast("No hay ventas para exportar.", duration=3000)

        currency_label = self._currency_symbol_clean()
        currency_format = self._currency_excel_format()
        # Obtener nombre de empresa
        company_name = getattr(self, "company_name", "") or "EMPRESA"
        today = datetime.datetime.now().strftime("%d/%m/%Y")
        period_start = self.cashbox_filter_start_date or "Inicio"
        period_end = self.cashbox_filter_end_date or "Actual"
        period_label = f"Período: {period_start} a {period_end}"

        total_operations = 0
        total_facturado = 0.0
        total_cobrado = 0.0
        total_pendiente = 0.0
        credit_operations = 0

        for sale in sales:
            if sale.get("is_deleted"):
                continue
            total_operations += 1
            total_amount = float(sale.get("total", 0) or 0)
            paid_amount = float(sale.get("amount", 0) or 0)
            payment_condition = (sale.get("payment_condition") or "").strip().lower()
            payment_type = (sale.get("payment_type") or "").strip().lower()
            is_credit = (
                bool(sale.get("is_credit"))
                or payment_type == "credit"
                or payment_condition in {"credito", "credit"}
            )
            if is_credit:
                credit_operations += 1
            total_facturado += total_amount
            total_cobrado += paid_amount
            total_pendiente += max(total_amount - paid_amount, 0)

        wb, ws = create_excel_workbook("Resumen de Caja")
        
        # Agregar encabezado profesional
        row = add_company_header(
            ws,
            company_name,
            "RESUMEN DE GESTIÓN DE CAJA",
            period_label,
            columns=8,
        )

        row += 1
        ws.cell(row=row, column=1, value="RESUMEN EJECUTIVO")
        row += 1
        ws.cell(row=row, column=1, value="Fecha de corte:")
        ws.cell(row=row, column=2, value=today)
        row += 1
        ws.cell(row=row, column=1, value="Operaciones registradas:")
        ws.cell(row=row, column=2, value=total_operations)
        row += 1
        ws.cell(row=row, column=1, value="Operaciones a crédito:")
        ws.cell(row=row, column=2, value=credit_operations)
        row += 1
        ws.cell(row=row, column=1, value=f"Total facturado ({currency_label}):")
        ws.cell(row=row, column=2, value=total_facturado).number_format = currency_format
        row += 1
        ws.cell(row=row, column=1, value=f"Total cobrado ({currency_label}):")
        ws.cell(row=row, column=2, value=total_cobrado).number_format = currency_format
        row += 1
        ws.cell(row=row, column=1, value=f"Saldo pendiente ({currency_label}):")
        ws.cell(row=row, column=2, value=total_pendiente).number_format = currency_format

        row += 2
        
        headers = [
            "Fecha y Hora",
            "Vendedor",
            "Método de Pago",
            "Detalle del Método",
            "Referencia/Descripción",
            f"Monto Total ({currency_label})",
            f"Monto Cobrado ({currency_label})",
            "Productos Vendidos",
        ]
        style_header_row(ws, row, headers)
        data_start = row + 1
        row += 1
        
        invalid_labels = {"", "-", "no especificado"}
        for sale in sales:
            if sale.get("is_deleted"):
                continue
            payment_condition = (sale.get("payment_condition") or "").strip().lower()
            payment_type = (sale.get("payment_type") or "").strip().lower()
            is_credit = (
                bool(sale.get("is_credit"))
                or payment_type == "credit"
                or payment_condition in {"credito", "credit"}
            )
            method_raw = self._normalize_wallet_label(sale.get("payment_method", ""))
            method_label = self._normalize_wallet_label(
                sale.get("payment_label", sale.get("payment_method", ""))
            )
            payment_details = self._payment_details_text(
                sale.get("payment_details", "")
            ).strip()
            if is_credit:
                method_raw = "Venta a Crédito / Fiado"
                method_label = method_raw
                amount_paid = sale.get("amount_paid")
                if amount_paid is None:
                    amount_paid = sale.get("amount", 0)
                try:
                    amount_paid_value = float(amount_paid or 0)
                except (TypeError, ValueError):
                    amount_paid_value = 0.0
                try:
                    total_amount_value = float(sale.get("total", 0) or 0)
                except (TypeError, ValueError):
                    total_amount_value = 0.0
                if total_amount_value > 0 and amount_paid_value >= total_amount_value:
                    payment_details = "Crédito (Completado)"
                elif amount_paid_value > 0:
                    payment_details = (
                        f"Crédito (Adelanto: {self._format_currency(amount_paid_value)})"
                    )
                else:
                    payment_details = "Crédito (Pendiente Total)"
            else:
                if (method_raw or "").strip().lower() in invalid_labels:
                    if (method_label or "").strip().lower() not in invalid_labels:
                        method_raw = method_label
                    else:
                        method_raw = "No especificado"
                if (method_label or "").strip().lower() in invalid_labels:
                    if (method_raw or "").strip().lower() not in invalid_labels:
                        method_label = method_raw
                    else:
                        method_label = "No especificado"
                if (payment_details or "").strip().lower() in invalid_labels:
                    if (method_label or "").strip().lower() not in invalid_labels:
                        payment_details = f"Pago en {method_label}"
                    else:
                        payment_details = "Pago registrado"
            item_parts = []
            for item in sale.get("items", []):
                name = (item.get("description") or "").strip() or "Producto"
                quantity = item.get("quantity", 0)
                unit_price = item.get("price")
                if unit_price is None:
                    unit_price = item.get("sale_price")
                if unit_price is None:
                    unit_price = item.get("subtotal")
                price_display = self._format_currency(unit_price or 0)
                item_parts.append(f"{name} (x{quantity}) - {price_display}")
            details = "\n".join(item_parts) if item_parts else "Sin detalle"
            
            ws.cell(row=row, column=1, value=sale["timestamp"])
            ws.cell(row=row, column=2, value=sale["user"])
            ws.cell(row=row, column=3, value=method_raw)
            ws.cell(row=row, column=4, value=method_label)
            ws.cell(row=row, column=5, value=payment_details)
            ws.cell(row=row, column=6, value=float(sale["total"] or 0)).number_format = currency_format
            ws.cell(row=row, column=7, value=float(sale.get("amount", 0) or 0)).number_format = currency_format
            ws.cell(row=row, column=8, value=details)
            
            for col in range(1, 9):
                ws.cell(row=row, column=col).border = THIN_BORDER
            row += 1

        if row > data_start:
            apply_wrap_text(ws, [8], data_start, row - 1)
        
        # Fila de totales con fórmulas
        totals_row = row
        add_totals_row_with_formulas(ws, totals_row, data_start, [
            {"type": "label", "value": "TOTALES"},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "sum", "col_letter": "F", "number_format": currency_format},
            {"type": "sum", "col_letter": "G", "number_format": currency_format},
            {"type": "text", "value": ""},
        ])
        
        # Notas explicativas
        add_notes_section(ws, totals_row, [
            "Monto Total: Precio total de la venta según productos.",
            "Monto Cobrado: Dinero efectivamente recibido (puede diferir en ventas a crédito).",
            "Crédito (Completado): El cliente pagó la totalidad del crédito.",
            "Crédito (Adelanto): El cliente realizó un pago parcial.",
            "Crédito (Pendiente Total): No se ha recibido ningún pago aún.",
        ], columns=8)
        
        auto_adjust_column_widths(ws)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return rx.download(data=output.getvalue(), filename="resumen_gestion_caja.xlsx")

    @rx.event
    def export_cashbox_close_pdf(self):
        if not (
            self.current_user["privileges"]["view_cashbox"]
            and self.current_user["privileges"]["export_data"]
        ):
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)

        report_date = self.cashbox_close_summary_date or datetime.datetime.now().strftime(
            "%Y-%m-%d"
        )
        breakdown = self._build_cashbox_close_breakdown(report_date)
        summary = breakdown["summary"]
        day_sales = self.cashbox_close_summary_sales or self._get_day_sales(report_date)

        if not summary and not day_sales and breakdown["opening_amount"] == 0:
            return rx.toast("No hay movimientos de caja para exportar.", duration=3000)

        info_dict = {
            "Fecha Cierre": report_date,
            "Responsable": self.current_user["username"],
        }
        total_value = 0.0
        for item in summary:
            total = item.get("total", 0) or 0
            if total <= 0:
                continue
            method = (item.get("method", "No especificado") or "").strip() or "No especificado"
            info_dict[f"Total {method}"] = self._format_currency(total)
            total_value += float(total)

        info_dict["Apertura"] = self._format_currency(breakdown["opening_amount"])
        info_dict["Ingresos reales"] = self._format_currency(breakdown["income_total"])
        info_dict["Egresos caja chica"] = self._format_currency(breakdown["expense_total"])
        info_dict["Saldo esperado"] = self._format_currency(breakdown["expected_total"])

        def _format_time(timestamp: str) -> str:
            if not timestamp:
                return ""
            if " " in timestamp:
                return timestamp.split(" ", 1)[1]
            try:
                parsed = datetime.datetime.fromisoformat(timestamp)
                return parsed.strftime("%H:%M:%S")
            except ValueError:
                return timestamp

        def _format_amount(value: Any) -> str:
            try:
                amount = float(value or 0)
            except (TypeError, ValueError):
                amount = 0.0
            return self._format_currency(amount)

        headers = ["N°", "Hora", "Operación", "Método", "Referencia", "Monto"]
        data = []
        import re
        sales_rows = [sale for sale in day_sales if not sale.get("is_deleted")]
        seq = len(sales_rows)
        for sale in sales_rows:
            if sale.get("is_deleted"):
                continue
            operation_raw = sale.get("action") or sale.get("type") or "Venta"
            operation = str(operation_raw).replace("_", " ").strip().title() or "Venta"
            method_raw = sale.get("payment_label") or sale.get("payment_method") or ""
            method_label = (
                self._normalize_wallet_label(method_raw) if method_raw else "No especificado"
            )
            reference = self._payment_details_text(sale.get("payment_details", ""))
            reference_clean = re.sub(r"#\s*\d+", "", reference or "").strip()
            if not reference_clean:
                reference_clean = reference
            amount = sale.get("total")
            if amount is None:
                amount = sale.get("amount", 0)
            data.append(
                [
                    seq,
                    _format_time(sale.get("timestamp", "")),
                    operation,
                    method_label,
                    reference_clean,
                    _format_amount(amount),
                ]
            )
            seq -= 1

        info_dict["column_widths"] = [0.06, 0.12, 0.16, 0.18, 0.36, 0.12]
        info_dict["wrap_columns"] = [4]

        output = io.BytesIO()
        create_pdf_report(
            output,
            "Reporte de Cierre de Caja",
            data,
            headers,
            info_dict,
        )

        return rx.download(data=output.getvalue(), filename="cierre_caja.pdf")

    @rx.event
    def export_cashbox_close_pdf_for_log(self, log_id: str):
        if not (
            self.current_user["privileges"]["view_cashbox"]
            and self.current_user["privileges"]["export_data"]
        ):
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)
        try:
            log_id_int = int(log_id)
        except (TypeError, ValueError):
            return rx.toast("Registro de cierre no valido.", duration=3000)
        with rx.session() as session:
            log = session.exec(
                select(CashboxLogModel)
                .where(CashboxLogModel.id == log_id_int)
            ).first()
        if not log or (log.action or "").lower() != "cierre":
            return rx.toast("El registro seleccionado no es un cierre.", duration=3000)

        start_dt, end_dt, user_id, report_date, closing_timestamp = self._cashbox_range_for_log(log)
        company_id = log.company_id
        branch_id = log.branch_id
        responsable = ""
        if user_id:
            with rx.session() as session:
                user = session.exec(
                    select(UserModel).where(UserModel.id == user_id)
                ).first()
                if user:
                    responsable = user.username or ""
        if not responsable:
            responsable = self.current_user.get("username") or ""

        summary = self._build_cashbox_summary_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )
        opening_amount = self._cashbox_opening_amount_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )
        expense_total = self._cashbox_expense_total_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )
        income_total = self._round_currency(sum(item.get("total", 0) for item in summary))
        expected_total = self._round_currency(opening_amount + income_total - expense_total)
        day_sales = self._get_sales_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )

        if not summary and not day_sales and opening_amount == 0:
            return rx.toast("No hay movimientos de caja para exportar.", duration=3000)

        info_dict = {
            "Fecha Cierre": report_date,
            "Responsable": responsable,
        }
        for item in summary:
            total = item.get("total", 0) or 0
            if total <= 0:
                continue
            method = (item.get("method", "No especificado") or "").strip() or "No especificado"
            info_dict[f"Total {method}"] = self._format_currency(total)
        info_dict["Apertura"] = self._format_currency(opening_amount)
        info_dict["Ingresos reales"] = self._format_currency(income_total)
        info_dict["Egresos caja chica"] = self._format_currency(expense_total)
        info_dict["Saldo esperado"] = self._format_currency(expected_total)

        def _format_time(timestamp: str) -> str:
            if not timestamp:
                return ""
            if " " in timestamp:
                return timestamp.split(" ", 1)[1]
            try:
                parsed = datetime.datetime.fromisoformat(timestamp)
                return parsed.strftime("%H:%M:%S")
            except ValueError:
                return timestamp

        def _format_amount(value: Any) -> str:
            try:
                amount = float(value or 0)
            except (TypeError, ValueError):
                amount = 0.0
            return self._format_currency(amount)

        headers = ["N°", "Hora", "Operación", "Método", "Referencia", "Monto"]
        data = []
        import re
        sales_rows = [sale for sale in day_sales if not sale.get("is_deleted")]
        seq = len(sales_rows)
        for sale in sales_rows:
            operation_raw = sale.get("action") or sale.get("type") or "Venta"
            operation = str(operation_raw).replace("_", " ").strip().title() or "Venta"
            method_raw = sale.get("payment_label") or sale.get("payment_method") or ""
            method_label = (
                self._normalize_wallet_label(method_raw) if method_raw else "No especificado"
            )
            reference = self._payment_details_text(sale.get("payment_details", ""))
            reference_clean = re.sub(r"#\s*\d+", "", reference or "").strip()
            if not reference_clean:
                reference_clean = reference
            amount = sale.get("total")
            if amount is None:
                amount = sale.get("amount", 0)
            data.append(
                [
                    seq,
                    _format_time(sale.get("timestamp", "")),
                    operation,
                    method_label,
                    reference_clean,
                    _format_amount(amount),
                ]
            )
            seq -= 1

        info_dict["column_widths"] = [0.06, 0.12, 0.16, 0.18, 0.36, 0.12]
        info_dict["wrap_columns"] = [4]

        output = io.BytesIO()
        create_pdf_report(
            output,
            "Reporte de Cierre de Caja",
            data,
            headers,
            info_dict,
        )

        return rx.download(data=output.getvalue(), filename="cierre_caja.pdf")

    @rx.event
    def print_cashbox_close_summary_for_log(self, log_id: str):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        try:
            log_id_int = int(log_id)
        except (TypeError, ValueError):
            return rx.toast("Registro de cierre no valido.", duration=3000)
        with rx.session() as session:
            log = session.exec(
                select(CashboxLogModel)
                .where(CashboxLogModel.id == log_id_int)
            ).first()
        if not log or (log.action or "").lower() != "cierre":
            return rx.toast("El registro seleccionado no es un cierre.", duration=3000)

        start_dt, end_dt, user_id, report_date, closing_timestamp = self._cashbox_range_for_log(log)
        company_id = log.company_id
        branch_id = log.branch_id
        responsable = ""
        if user_id:
            with rx.session() as session:
                user = session.exec(
                    select(UserModel).where(UserModel.id == user_id)
                ).first()
                if user:
                    responsable = user.username or ""
        if not responsable:
            responsable = self.current_user.get("username") or ""

        summary = self._build_cashbox_summary_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )
        opening_amount = self._cashbox_opening_amount_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )
        expense_total = self._cashbox_expense_total_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )
        income_total = self._round_currency(sum(item.get("total", 0) for item in summary))
        expected_total = self._round_currency(opening_amount + income_total - expense_total)
        day_sales = self._get_sales_for_range(
            start_dt, end_dt, company_id, branch_id, user_id
        )

        if not summary and not day_sales and opening_amount == 0:
            return rx.toast("No hay movimientos de caja para imprimir.", duration=3000)

        totals_list = [
            {
                "method": item.get("method", "No especificado"),
                "amount": self._round_currency(item.get("total", 0)),
            }
            for item in summary
            if item.get("total", 0) > 0
        ]

        receipt_width = self._receipt_width()
        paper_width_mm = self._receipt_paper_mm()

        def center(text, width=receipt_width):
            return text.center(width)

        def line(width=receipt_width):
            return "-" * width

        def row(left, right, width=receipt_width):
            spaces = width - len(left) - len(right)
            return left + " " * max(spaces, 1) + right

        company = self._company_settings_snapshot()
        company_name = (company.get("company_name") or "").strip()
        ruc = (company.get("ruc") or "").strip()
        tax_id_label = company.get("tax_id_label", "RUC")
        address = (company.get("address") or "").strip()
        phone = (company.get("phone") or "").strip()
        address_lines = self._wrap_receipt_lines(address, receipt_width)

        receipt_lines = [""]
        if company_name:
            for name_line in self._wrap_receipt_lines(company_name, receipt_width):
                receipt_lines.append(center(name_line))
            receipt_lines.append("")
        if ruc:
            receipt_lines.append(center(f"{tax_id_label}: {ruc}"))
            receipt_lines.append("")
        for addr_line in address_lines:
            receipt_lines.append(center(addr_line))
        if address_lines:
            receipt_lines.append("")
        if phone:
            receipt_lines.append(center(f"Tel: {phone}"))
            receipt_lines.append("")
        receipt_lines.extend(
            [
                line(),
                center("RESUMEN DIARIO DE CAJA"),
                line(),
                "",
                f"Fecha: {report_date}",
                "",
                f"Responsable: {responsable}",
                "",
                f"Cierre: {closing_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                line(),
                "",
                "RESUMEN DE CAJA",
                "",
                row("Apertura:", self._format_currency(opening_amount)),
                row("Ingresos:", self._format_currency(income_total)),
                row("Egresos:", self._format_currency(expense_total)),
                row("Saldo esperado:", self._format_currency(expected_total)),
                "",
                line(),
                "",
                "INGRESOS POR METODO",
                "",
            ]
        )

        for item in totals_list:
            amount = item.get("amount", 0)
            if amount > 0:
                method = item.get("method", "No especificado")
                receipt_lines.append(
                    row(f"{method}:", self._format_currency(amount))
                )
                receipt_lines.append("")

        receipt_lines.append(
            row("TOTAL CIERRE:", self._format_currency(expected_total))
        )
        receipt_lines.append("")
        receipt_lines.append(line())
        receipt_lines.append("")
        receipt_lines.append("DETALLE DE INGRESOS")
        receipt_lines.append("")

        import re
        sales_rows = [sale for sale in day_sales if not sale.get("is_deleted")]
        seq = len(sales_rows)
        for sale in sales_rows:
            method_label = sale.get("payment_label", sale.get("payment_method", ""))
            payment_detail = self._payment_details_text(sale.get("payment_details", ""))
            payment_detail = re.sub(r"#\s*\d+", "", payment_detail or "").strip()
            receipt_lines.append(f"{sale['timestamp']}")
            receipt_lines.extend(
                self._wrap_receipt_label_value(
                    "Correlativo", f"#{seq}", receipt_width
                )
            )
            receipt_lines.extend(
                self._wrap_receipt_label_value(
                    "Usuario", sale["user"], receipt_width
                )
            )
            receipt_lines.extend(
                self._wrap_receipt_label_value(
                    "Metodo", method_label, receipt_width
                )
            )
            if payment_detail and payment_detail != method_label:
                receipt_lines.extend(
                    self._wrap_receipt_label_value(
                        "Detalle", payment_detail, receipt_width
                    )
                )
            receipt_lines.append(row("Total:", self._format_currency(sale['total'])))
            receipt_lines.append(line())
            seq -= 1

        receipt_lines.extend(
            [
                "",
                center("FIN DEL REPORTE"),
                " ",
                " ",
                " ",
            ]
        )

        receipt_text = chr(10).join(receipt_lines)
        safe_receipt_text = html.escape(receipt_text)

        html_content = f"""<html>
<head>
<meta charset='utf-8'/>
<title>Resumen de Caja</title>
<style>
@page {{ size: {paper_width_mm}mm auto; margin: 0; }}
body {{ margin: 0; padding: 2mm; }}
pre {{ font-family: monospace; font-size: 12px; margin: 0; white-space: pre-wrap; word-break: break-word; }}
</style>
</head>
<body>
<pre>{safe_receipt_text}</pre>
</body>
</html>"""

        script = f"""
        const cashboxWindow = window.open('', '_blank');
        cashboxWindow.document.write({json.dumps(html_content)});
        cashboxWindow.document.close();
        cashboxWindow.focus();
        cashboxWindow.print();
        """
        return rx.call_script(script)

    @rx.event
    def export_cashbox_sessions(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)
        logs = self._fetch_cashbox_logs()
        if not logs:
            return rx.toast("No hay aperturas o cierres para exportar.", duration=3000)

        currency_label = self._currency_symbol_clean()
        currency_format = self._currency_excel_format()
        company_name = getattr(self, "company_name", "") or "EMPRESA"
        today = datetime.datetime.now().strftime("%d/%m/%Y")
        period_start = self.cashbox_log_filter_start_date or "Inicio"
        period_end = self.cashbox_log_filter_end_date or "Actual"
        period_label = f"Período: {period_start} a {period_end}"

        opening_count = 0
        closing_count = 0
        opening_total = 0.0
        closing_total = 0.0
        for log in logs:
            action = (log.get("action") or "").strip().lower()
            opening_amount = float(log.get("opening_amount", 0) or 0)
            closing_amount = float(log.get("closing_total", 0) or 0)
            if action == "apertura":
                opening_count += 1
                opening_total += opening_amount
            elif action == "cierre":
                closing_count += 1
                closing_total += closing_amount
        
        wb, ws = create_excel_workbook("Aperturas y Cierres")
        
        # Encabezado profesional
        row = add_company_header(
            ws,
            company_name,
            "REGISTRO DE APERTURAS Y CIERRES DE CAJA",
            period_label,
            columns=7,
        )

        row += 1
        ws.cell(row=row, column=1, value="RESUMEN DE OPERACIONES")
        row += 1
        ws.cell(row=row, column=1, value="Fecha de corte:")
        ws.cell(row=row, column=2, value=today)
        row += 1
        ws.cell(row=row, column=1, value="Cantidad de aperturas:")
        ws.cell(row=row, column=2, value=opening_count)
        row += 1
        ws.cell(row=row, column=1, value="Cantidad de cierres:")
        ws.cell(row=row, column=2, value=closing_count)
        row += 1
        ws.cell(row=row, column=1, value=f"Total aperturas ({currency_label}):")
        ws.cell(row=row, column=2, value=opening_total).number_format = currency_format
        row += 1
        ws.cell(row=row, column=1, value=f"Total cierres ({currency_label}):")
        ws.cell(row=row, column=2, value=closing_total).number_format = currency_format
        row += 2
        
        headers = [
            "Fecha y Hora",
            "Tipo de Operación",
            "Responsable",
            f"Monto Apertura ({currency_label})",
            f"Monto Cierre ({currency_label})",
            "Desglose por Método",
            "Observaciones",
        ]
        style_header_row(ws, row, headers)
        data_start = row + 1
        row += 1
        
        total_aperturas = 0.0
        total_cierres = 0.0
        
        for log in logs:
            action = (log.get("action") or "").lower()
            action_display = (
                "Apertura de Caja"
                if action == "apertura"
                else "Cierre de Caja"
                if action == "cierre"
                else str(action).replace("_", " ").strip().title()
            )
            
            opening_amount = float(log.get("opening_amount", 0) or 0)
            closing_amount = float(log.get("closing_total", 0) or 0)
            
            if action == "apertura":
                total_aperturas += opening_amount
            elif action == "cierre":
                total_cierres += closing_amount
            
            totals_detail = ", ".join(
                f"{item.get('method', 'Otro')}: {self._format_currency(item.get('amount', 0))}"
                for item in log.get("totals_by_method", [])
                if item.get("amount", 0)
            ) or "Sin desglose"
            
            ws.cell(row=row, column=1, value=log.get("timestamp", ""))
            ws.cell(row=row, column=2, value=action_display)
            ws.cell(row=row, column=3, value=log.get("user", "Desconocido"))
            ws.cell(row=row, column=4, value=opening_amount).number_format = currency_format
            ws.cell(row=row, column=5, value=closing_amount).number_format = currency_format
            ws.cell(row=row, column=6, value=totals_detail)
            ws.cell(row=row, column=7, value=log.get("notes", "") or "Sin observaciones")
            
            for col in range(1, 8):
                ws.cell(row=row, column=col).border = THIN_BORDER
            row += 1
        
        # Fila de totales
        totals_row = row
        add_totals_row_with_formulas(ws, totals_row, data_start, [
            {"type": "label", "value": "TOTALES"},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "sum", "col_letter": "D", "number_format": currency_format},
            {"type": "sum", "col_letter": "E", "number_format": currency_format},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
        ])
        
        # Notas explicativas
        add_notes_section(ws, totals_row, [
            "Apertura de Caja: Monto inicial con el que se inicia la jornada.",
            "Cierre de Caja: Monto total contado al finalizar la jornada.",
            "Desglose por Método: Distribución del dinero según forma de pago (solo en cierres).",
            "La diferencia entre Cierres y Aperturas debe coincidir con las ventas del día.",
        ], columns=7)
        
        auto_adjust_column_widths(ws)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return rx.download(
            data=output.getvalue(), filename="aperturas_cierres_caja.xlsx"
        )

    @rx.event
    def export_petty_cash_report(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)

        movements = self.petty_cash_movements
        if not movements:
            return rx.toast("No hay movimientos para exportar.", duration=3000)

        currency_label = self._currency_symbol_clean()
        currency_format = self._currency_excel_format()
        company_name = getattr(self, "company_name", "") or "EMPRESA"
        today = datetime.datetime.now().strftime("%d/%m/%Y")

        def _parse_numeric(value: Any) -> float:
            if value is None:
                return 0.0
            raw = str(value)
            # Extrae el primer número del string, ignorando símbolos
            import re
            match = re.search(r"([0-9]+(?:[.,][0-9]{3})*(?:[.,][0-9]+)?)", raw)
            if not match:
                return 0.0
            num = match.group(1)
            if "," in num and "." in num:
                num = num.replace(",", "")
            elif "," in num and "." not in num:
                num = num.replace(",", ".")
            try:
                return float(num)
            except ValueError:
                return 0.0

        total_movements = len(movements)
        total_units = sum(
            _parse_numeric(item.get("formatted_quantity", "0"))
            for item in movements
        )
        total_expense = sum(
            _parse_numeric(item.get("formatted_total", "0"))
            for item in movements
        )

        wb, ws = create_excel_workbook("Caja Chica")
        
        # Encabezado profesional
        row = add_company_header(
            ws,
            company_name,
            "MOVIMIENTOS DE CAJA CHICA",
            f"Corte: {today}",
            columns=7,
        )

        row += 1
        ws.cell(row=row, column=1, value="RESUMEN DE EGRESOS")
        row += 1
        ws.cell(row=row, column=1, value="Movimientos registrados:")
        ws.cell(row=row, column=2, value=total_movements)
        row += 1
        ws.cell(row=row, column=1, value="Unidades egresadas:")
        ws.cell(row=row, column=2, value=total_units)
        row += 1
        ws.cell(row=row, column=1, value=f"Total egresado ({currency_label}):")
        ws.cell(row=row, column=2, value=total_expense).number_format = currency_format
        row += 2

        headers = [
            "Fecha y Hora",
            "Responsable",
            "Concepto/Motivo",
            "Cantidad",
            "Unidad",
            f"Costo Unitario ({currency_label})",
            f"Total Egreso ({currency_label})",
        ]
        style_header_row(ws, row, headers)
        data_start = row + 1
        row += 1

        for item in movements:
            # Extraer valores numéricos para las fórmulas
            quantity = _parse_numeric(item.get("formatted_quantity", "0"))
            cost = _parse_numeric(item.get("formatted_cost", "0"))
            
            ws.cell(row=row, column=1, value=item.get("timestamp", ""))
            ws.cell(row=row, column=2, value=item.get("user", "Desconocido"))
            ws.cell(row=row, column=3, value=item.get("notes", "") or "Sin motivo especificado")
            ws.cell(row=row, column=4, value=quantity)
            ws.cell(row=row, column=5, value=item.get("unit", "Unid."))
            ws.cell(row=row, column=6, value=cost).number_format = currency_format
            # Total = Fórmula: Cantidad × Costo Unitario
            ws.cell(row=row, column=7, value=f"=D{row}*F{row}").number_format = currency_format
            
            for col in range(1, 8):
                ws.cell(row=row, column=col).border = THIN_BORDER
            row += 1
        
        # Fila de totales
        totals_row = row
        add_totals_row_with_formulas(ws, totals_row, data_start, [
            {"type": "label", "value": "TOTAL EGRESOS"},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "sum", "col_letter": "D"},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "sum", "col_letter": "G", "number_format": currency_format},
        ])
        
        # Notas explicativas
        add_notes_section(ws, totals_row, [
            "Caja Chica: Fondo destinado a gastos menores del día a día.",
            "Cada movimiento representa un egreso (salida de dinero).",
            "Total Egreso = Cantidad × Costo Unitario (fórmula verificable).",
            "Este monto se descuenta del efectivo al momento del cierre de caja.",
        ], columns=7)
        
        auto_adjust_column_widths(ws)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return rx.download(
            data=output.getvalue(), filename="movimientos_caja_chica.xlsx"
        )

    @rx.event
    def show_cashbox_log(self, log_id: str):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        with rx.session() as session:
            log = session.exec(
                select(CashboxLogModel)
                .where(CashboxLogModel.id == int(log_id))
                .where(CashboxLogModel.company_id == company_id)
                .where(CashboxLogModel.branch_id == branch_id)
            ).first()
            if not log:
                return rx.toast("Registro de caja no encontrado.", duration=3000)
            
            # Obtener username via user_id
            user = session.get(UserModel, log.user_id)
            username = user.username if user else "Unknown"
            
            self.cashbox_log_selected = {
                "id": str(log.id),
                "action": log.action,
                "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "user": username,
                "opening_amount": log.amount if log.action == "apertura" else 0.0,
                "closing_total": log.amount if log.action == "cierre" else 0.0,
                "totals_by_method": [],
                "notes": log.notes or "",
                "amount": log.amount or 0.0,
                "quantity": 0.0,
                "unit": "",
                "cost": 0.0,
                "formatted_amount": self._format_currency(log.amount or 0),
                "formatted_cost": "",
                "formatted_quantity": "",
            }
            self.cashbox_log_modal_open = True

    @rx.event
    def close_cashbox_log_modal(self):
        self.cashbox_log_modal_open = False
        self.cashbox_log_selected = None

    @rx.event
    def open_sale_delete_modal(self, sale_id: str):
        denial = self._cashbox_guard()
        if denial:
            return denial
        self.sale_to_delete = sale_id
        self.sale_delete_reason = ""
        self.sale_delete_modal_open = True

    @rx.event
    def close_sale_delete_modal(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        self.sale_delete_modal_open = False
        self.sale_to_delete = ""
        self.sale_delete_reason = ""

    @rx.event
    def set_sale_delete_reason(self, value: str):
        denial = self._cashbox_guard()
        if denial:
            return denial
        self.sale_delete_reason = sanitize_reason_preserve_spaces(value)

    @rx.event
    def delete_sale(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        if not self.current_user["privileges"]["delete_sales"]:
            return rx.toast("No tiene permisos para eliminar ventas.", duration=3000)
        block = self._require_active_subscription()
        if block:
            return block
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        sale_id = self.sale_to_delete
        reason = sanitize_reason(self.sale_delete_reason).strip()
        if not sale_id:
            return rx.toast("Seleccione una venta a eliminar.", duration=3000)
        if not reason:
            return rx.toast(
                "Ingrese el motivo de la eliminación de la venta.", duration=3000
            )
        
        with rx.session() as session:
            try:
                sale_db_id = int(sale_id)
            except ValueError:
                return rx.toast("ID de venta inválido.", duration=3000)
                
            sale_db = session.exec(
                select(Sale)
                .where(Sale.id == sale_db_id)
                .where(Sale.company_id == company_id)
                .where(Sale.branch_id == branch_id)
            ).first()
            
            if not sale_db:
                return rx.toast("Venta no encontrada en BD.", duration=3000)
            if sale_db.status == SaleStatus.cancelled:
                return rx.toast("La venta ya fue anulada.", duration=3000)
            
            # Marcar como cancelado en BD
            sale_db.status = SaleStatus.cancelled
            sale_db.delete_reason = reason
            session.add(sale_db)

            logs = session.exec(
                select(CashboxLogModel)
                .where(CashboxLogModel.sale_id == sale_db_id)
                .where(CashboxLogModel.company_id == company_id)
                .where(CashboxLogModel.branch_id == branch_id)
            ).all()
            for log in logs:
                if log.is_voided:
                    continue
                log.is_voided = True
                if reason:
                    suffix = f" | ANULADA: {reason}"
                    if suffix not in (log.notes or ""):
                        log.notes = f"{log.notes or ''}{suffix}".strip()
                session.add(log)
            
            # Restaurar stock
            products_recalc_variants: set[int] = set()
            products_recalc_batches: set[int] = set()
            variants_recalc_batches: set[int] = set()
            for item in sale_db.items:
                quantity = item.quantity or 0
                if quantity <= 0:
                    continue

                if item.product_variant_id:
                    variant = session.exec(
                        select(ProductVariant)
                        .where(ProductVariant.id == item.product_variant_id)
                        .where(ProductVariant.company_id == company_id)
                        .where(ProductVariant.branch_id == branch_id)
                        .with_for_update()
                    ).first()
                    if variant:
                        if item.product_batch_id:
                            batch = session.exec(
                                select(ProductBatch)
                                .where(ProductBatch.id == item.product_batch_id)
                                .where(ProductBatch.company_id == company_id)
                                .where(ProductBatch.branch_id == branch_id)
                                .with_for_update()
                            ).first()
                            if batch:
                                batch.stock = (batch.stock or 0) + quantity
                                session.add(batch)
                                variants_recalc_batches.add(variant.id)
                                products_recalc_variants.add(variant.product_id)
                            else:
                                variant.stock = (variant.stock or 0) + quantity
                                session.add(variant)
                                products_recalc_variants.add(variant.product_id)
                        else:
                            variant.stock = (variant.stock or 0) + quantity
                            session.add(variant)
                            products_recalc_variants.add(variant.product_id)
                elif item.product_id:
                    product = session.exec(
                        select(Product)
                        .where(Product.id == item.product_id)
                        .where(Product.company_id == company_id)
                        .where(Product.branch_id == branch_id)
                        .with_for_update()
                    ).first()
                    if product:
                        if item.product_batch_id:
                            batch = session.exec(
                                select(ProductBatch)
                                .where(ProductBatch.id == item.product_batch_id)
                                .where(ProductBatch.company_id == company_id)
                                .where(ProductBatch.branch_id == branch_id)
                                .with_for_update()
                            ).first()
                            if batch:
                                batch.stock = (batch.stock or 0) + quantity
                                session.add(batch)
                                products_recalc_batches.add(product.id)
                            else:
                                product.stock = (product.stock or 0) + quantity
                                session.add(product)
                        else:
                            product.stock = (product.stock or 0) + quantity
                            session.add(product)

                # Registrar movimiento de stock
                movement = StockMovement(
                    product_id=item.product_id,
                    user_id=self.current_user.get("id"),
                    type="Devolucion Venta",
                    quantity=quantity,
                    description=f"Venta anulada #{sale_db.id}: {reason}",
                    timestamp=datetime.datetime.now(),
                    company_id=company_id,
                    branch_id=branch_id,
                )
                session.add(movement)

            if variants_recalc_batches:
                for variant_id in variants_recalc_batches:
                    total_query = (
                        select(sqlalchemy.func.coalesce(sqlalchemy.func.sum(ProductBatch.stock), 0))
                        .where(ProductBatch.product_variant_id == variant_id)
                        .where(ProductBatch.company_id == company_id)
                        .where(ProductBatch.branch_id == branch_id)
                    )
                    total_row = session.exec(total_query).first()
                    if total_row is None:
                        total_stock = 0
                    elif isinstance(total_row, tuple):
                        total_stock = total_row[0]
                    else:
                        total_stock = total_row
                    variant_row = session.exec(
                        select(ProductVariant)
                        .where(ProductVariant.id == variant_id)
                        .where(ProductVariant.company_id == company_id)
                        .where(ProductVariant.branch_id == branch_id)
                    ).first()
                    if variant_row:
                        variant_row.stock = total_stock
                        session.add(variant_row)
                        products_recalc_variants.add(variant_row.product_id)

            if products_recalc_variants:
                for product_id in products_recalc_variants:
                    total_query = (
                        select(sqlalchemy.func.coalesce(sqlalchemy.func.sum(ProductVariant.stock), 0))
                        .where(ProductVariant.product_id == product_id)
                        .where(ProductVariant.company_id == company_id)
                        .where(ProductVariant.branch_id == branch_id)
                    )
                    total_row = session.exec(total_query).first()
                    if total_row is None:
                        total_stock = 0
                    elif isinstance(total_row, tuple):
                        total_stock = total_row[0]
                    else:
                        total_stock = total_row
                    product_row = session.exec(
                        select(Product)
                        .where(Product.id == product_id)
                        .where(Product.company_id == company_id)
                        .where(Product.branch_id == branch_id)
                    ).first()
                    if product_row:
                        product_row.stock = total_stock
                        session.add(product_row)

            if products_recalc_batches:
                for product_id in (
                    products_recalc_batches - products_recalc_variants
                ):
                    total_query = (
                        select(sqlalchemy.func.coalesce(sqlalchemy.func.sum(ProductBatch.stock), 0))
                        .where(ProductBatch.product_id == product_id)
                        .where(ProductBatch.product_variant_id.is_(None))
                        .where(ProductBatch.company_id == company_id)
                        .where(ProductBatch.branch_id == branch_id)
                    )
                    total_row = session.exec(total_query).first()
                    if total_row is None:
                        total_stock = 0
                    elif isinstance(total_row, tuple):
                        total_stock = total_row[0]
                    else:
                        total_stock = total_row
                    product_row = session.exec(
                        select(Product)
                        .where(Product.id == product_id)
                        .where(Product.company_id == company_id)
                        .where(Product.branch_id == branch_id)
                    ).first()
                    if product_row:
                        product_row.stock = total_stock
                        session.add(product_row)
            session.commit()
        
        self._cashbox_update_trigger += 1
        self.close_sale_delete_modal()
        return rx.toast("Venta eliminada correctamente.", duration=3000)

    @rx.event
    def reprint_sale_receipt(self, sale_id: str):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para ver comprobantes.", duration=3000)
        
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        sale_data = None
        with rx.session() as session:
            try:
                sale_db_id = int(sale_id)
                sale = session.exec(
                    select(Sale)
                    .where(Sale.id == sale_db_id)
                    .where(Sale.company_id == company_id)
                    .where(Sale.branch_id == branch_id)
                    .options(
                        selectinload(Sale.items),
                        selectinload(Sale.payments),
                        selectinload(Sale.user),
                    )
                ).first()
                if sale:
                    items_data = []
                    for item in sale.items:
                        items_data.append({
                            "description": item.product_name_snapshot,
                            "quantity": item.quantity,
                            "unit": "Unidad",
                            "price": item.unit_price,
                            "subtotal": item.subtotal
                        })
                    
                    sale_data = {
                        "timestamp": sale.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "total": sale.total_amount,
                        "payment_details": self._payment_summary_from_payments(
                            sale.payments or []
                        ),
                        "payment_method": self._payment_method_display(
                            sale.payments or []
                        ),
                        "items": items_data,
                        "user": sale.user.username if sale.user else "Desconocido"
                    }
            except ValueError:
                pass
        
        if not sale_data:
            return rx.toast("Venta no encontrada.", duration=3000)
        
        receipt_width = self._receipt_width()
        paper_width_mm = self._receipt_paper_mm()

        # Funciones auxiliares para formato de texto plano
        def center(text, width=receipt_width):
            return text.center(width)
        
        def line(width=receipt_width):
            return "-" * width
        
        def row(left, right, width=receipt_width):
            spaces = width - len(left) - len(right)
            return left + " " * max(spaces, 1) + right

        company = self._company_settings_snapshot()
        company_name = (company.get("company_name") or "").strip()
        ruc = (company.get("ruc") or "").strip()
        tax_id_label = company.get("tax_id_label", "RUC")  # Dinámico por país
        address = (company.get("address") or "").strip()
        phone = (company.get("phone") or "").strip()
        footer_message = (company.get("footer_message") or "").strip()
        address_lines = self._wrap_receipt_lines(address, receipt_width)
        
        items = sale_data.get("items", [])
        payment_summary = self._payment_details_text(
            sale_data.get("payment_details")
        ) or sale_data.get("payment_method", "")
        
        # Construir recibo línea por línea
        receipt_lines = [""]
        if company_name:
            for name_line in self._wrap_receipt_lines(company_name, receipt_width):
                receipt_lines.append(center(name_line))
            receipt_lines.append("")
        if ruc:
            receipt_lines.append(center(f"{tax_id_label}: {ruc}"))
            receipt_lines.append("")
        for addr_line in address_lines:
            receipt_lines.append(center(addr_line))
        if address_lines:
            receipt_lines.append("")
        if phone:
            receipt_lines.append(center(f"Tel: {phone}"))
            receipt_lines.append("")
        receipt_lines.extend(
            [
                line(),
                center("COMPROBANTE DE PAGO"),
                line(),
                "",
                f"Fecha: {sale_data.get('timestamp', '')}",
                "",
                f"Atendido por: {sale_data.get('user', 'Desconocido')}",
                "",
                line(),
            ]
        )
        
        # Agregar ítems
        for item in items:
            receipt_lines.append("")
            description = item.get("description", "")
            for desc_line in self._wrap_receipt_lines(description, receipt_width):
                receipt_lines.append(desc_line)
            left_text = (
                f"{item.get('quantity', 0)} {item.get('unit', '')} x "
                f"{self._format_currency(item.get('price', 0))}"
            )
            right_text = self._format_currency(item.get("subtotal", 0))
            available = max(receipt_width - len(right_text) - 1, 1)
            left_lines = self._wrap_receipt_lines(left_text, available)
            if left_lines:
                for line_part in left_lines[:-1]:
                    receipt_lines.append(line_part)
                receipt_lines.append(row(left_lines[-1], right_text, receipt_width))
            else:
                receipt_lines.append(row("", right_text, receipt_width))
            receipt_lines.append("")
            receipt_lines.append(line())
        
        # Total y método de pago
        receipt_lines.append("")
        receipt_lines.append(
            row("TOTAL A PAGAR:", self._format_currency(sale_data.get("total", 0)))
        )
        receipt_lines.append("")
        receipt_lines.extend(
            self._wrap_receipt_label_value(
                "Metodo de Pago", payment_summary, receipt_width
            )
        )
        receipt_lines.append("")
        receipt_lines.append(line())
        receipt_lines.append("")
        if footer_message:
            for footer_line in self._wrap_receipt_lines(footer_message, receipt_width):
                receipt_lines.append(center(footer_line))
        receipt_lines.extend([" ", " ", " "])
        
        receipt_text = chr(10).join(receipt_lines)
        safe_receipt_text = html.escape(receipt_text)
        
        html_content = f"""<html>
<head>
<meta charset='utf-8'/>
<title>Comprobante de Pago</title>
<style>
@page {{ size: {paper_width_mm}mm auto; margin: 0; }}
body {{ margin: 0; padding: 2mm; }}
pre {{ font-family: monospace; font-size: 12px; margin: 0; white-space: pre-wrap; word-break: break-word; }}
</style>
</head>
<body>
<pre>{safe_receipt_text}</pre>
</body>
</html>"""
        
        script = f"""
        const receiptWindow = window.open('', '_blank');
        receiptWindow.document.write({json.dumps(html_content)});
        receiptWindow.document.close();
        receiptWindow.focus();
        receiptWindow.print();
        """
        return rx.call_script(script)

    @rx.event
    def close_cashbox_day(self):
        if not self.current_user["privileges"]["manage_cashbox"]:
            return rx.toast("No tiene permisos para gestionar la caja.", duration=3000)
        denial = self._cashbox_guard()
        if denial:
            return denial
        block = self._require_active_subscription()
        if block:
            return block
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        date = self.cashbox_close_summary_date or datetime.datetime.now().strftime(
            "%Y-%m-%d"
        )
        breakdown = self._build_cashbox_close_breakdown(date)
        summary = breakdown["summary"]
        day_sales = self.cashbox_close_summary_sales or self._get_day_sales(date)
        if (
            not day_sales
            and not summary
            and breakdown["opening_amount"] == 0
        ):
            return rx.toast("No hay movimientos de caja hoy.", duration=3000)
        closing_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        totals_list = [
            {
                "method": item.get("method", "No especificado"),
                "amount": self._round_currency(item.get("total", 0)),
            }
            for item in summary
            if item.get("total", 0) > 0
        ]
        opening_amount = breakdown["opening_amount"]
        income_total = breakdown["income_total"]
        expense_total = breakdown["expense_total"]
        closing_total = breakdown["expected_total"]
        
        user_id = self.current_user.get("id")
        if user_id:
            with rx.session() as session:
                # Cerrar sesion
                cashbox_session = session.exec(
                    select(CashboxSessionModel)
                    .where(CashboxSessionModel.user_id == user_id)
                    .where(CashboxSessionModel.company_id == company_id)
                    .where(CashboxSessionModel.branch_id == branch_id)
                    .where(CashboxSessionModel.is_open == True)
                ).first()
                
                if cashbox_session:
                    cashbox_session.is_open = False
                    cashbox_session.closing_time = datetime.datetime.now()
                    cashbox_session.closing_amount = closing_total
                    session.add(cashbox_session)
                
                # Crear log
                log = CashboxLogModel(
                    company_id=company_id,
                    branch_id=branch_id,
                    user_id=user_id,
                    action="cierre",
                    amount=closing_total,
                    notes=f"Cierre de caja {date}",
                    timestamp=datetime.datetime.now()
                )
                session.add(log)
                session.commit()
        
        receipt_width = self._receipt_width()
        paper_width_mm = self._receipt_paper_mm()

        # Funciones auxiliares para formato de texto plano
        def center(text, width=receipt_width):
            return text.center(width)
        
        def line(width=receipt_width):
            return "-" * width
        
        def row(left, right, width=receipt_width):
            spaces = width - len(left) - len(right)
            return left + " " * max(spaces, 1) + right
        
        # Construir recibo línea por línea
        company = self._company_settings_snapshot()
        company_name = (company.get("company_name") or "").strip()
        ruc = (company.get("ruc") or "").strip()
        tax_id_label = company.get("tax_id_label", "RUC")  # Dinámico por país
        address = (company.get("address") or "").strip()
        phone = (company.get("phone") or "").strip()
        address_lines = self._wrap_receipt_lines(address, receipt_width)

        receipt_lines = [""]
        if company_name:
            for name_line in self._wrap_receipt_lines(company_name, receipt_width):
                receipt_lines.append(center(name_line))
            receipt_lines.append("")
        if ruc:
            receipt_lines.append(center(f"{tax_id_label}: {ruc}"))
            receipt_lines.append("")
        for addr_line in address_lines:
            receipt_lines.append(center(addr_line))
        if address_lines:
            receipt_lines.append("")
        if phone:
            receipt_lines.append(center(f"Tel: {phone}"))
            receipt_lines.append("")
        receipt_lines.extend(
            [
                line(),
                center("RESUMEN DIARIO DE CAJA"),
                line(),
                "",
                f"Fecha: {date}",
                "",
                f"Responsable: {self.current_user['username']}",
                "",
                f"Cierre: {closing_timestamp}",
                "",
                line(),
                "",
                "RESUMEN DE CAJA",
                "",
                row("Apertura:", self._format_currency(opening_amount)),
                row("Ingresos:", self._format_currency(income_total)),
                row("Egresos:", self._format_currency(expense_total)),
                row("Saldo esperado:", self._format_currency(closing_total)),
                "",
                line(),
                "",
                "INGRESOS POR METODO",
                "",
            ]
        )
        
        # Agregar totales por método
        for item in summary:
            amount = item.get("total", 0)
            if amount > 0:
                method = item.get("method", "No especificado")
                receipt_lines.append(
                    row(f"{method}:", self._format_currency(amount))
                )
                receipt_lines.append("")
        
        receipt_lines.append(
            row("TOTAL CIERRE:", self._format_currency(closing_total))
        )
        receipt_lines.append("")
        receipt_lines.append(line())
        receipt_lines.append("")
        receipt_lines.append("DETALLE DE INGRESOS")
        receipt_lines.append("")
        
        # Agregar detalle de ventas con método de pago completo
        import re
        sales_rows = [sale for sale in day_sales if not sale.get("is_deleted")]
        seq = len(sales_rows)
        for sale in sales_rows:
            method_label = sale.get("payment_label", sale.get("payment_method", ""))
            payment_detail = self._payment_details_text(sale.get("payment_details", ""))
            payment_detail = re.sub(r"#\s*\d+", "", payment_detail or "").strip()
            receipt_lines.append(f"{sale['timestamp']}")
            receipt_lines.extend(
                self._wrap_receipt_label_value(
                    "Correlativo", f"#{seq}", receipt_width
                )
            )
            receipt_lines.extend(
                self._wrap_receipt_label_value(
                    "Usuario", sale["user"], receipt_width
                )
            )
            receipt_lines.extend(
                self._wrap_receipt_label_value(
                    "Metodo", method_label, receipt_width
                )
            )
            if payment_detail and payment_detail != method_label:
                receipt_lines.extend(
                    self._wrap_receipt_label_value(
                        "Detalle", payment_detail, receipt_width
                    )
                )
            receipt_lines.append(row("Total:", self._format_currency(sale['total'])))
            receipt_lines.append(line())
            seq -= 1
        
        receipt_lines.extend([
            "",
            center("FIN DEL REPORTE"),
            " ",
            " ",
            " ",
        ])
        
        receipt_text = chr(10).join(receipt_lines)
        safe_receipt_text = html.escape(receipt_text)
        
        html_content = f"""<html>
<head>
<meta charset='utf-8'/>
<title>Resumen de Caja</title>
<style>
@page {{ size: {paper_width_mm}mm auto; margin: 0; }}
body {{ margin: 0; padding: 2mm; }}
pre {{ font-family: monospace; font-size: 12px; margin: 0; white-space: pre-wrap; word-break: break-word; }}
</style>
</head>
<body>
<pre>{safe_receipt_text}</pre>
</body>
</html>"""
        
        script = f"""
        const cashboxWindow = window.open('', '_blank');
        cashboxWindow.document.write({json.dumps(html_content)});
        cashboxWindow.document.close();
        cashboxWindow.focus();
        cashboxWindow.print();
        """
        self._close_cashbox_session()
        self._reset_cashbox_close_summary()
        return rx.call_script(script)

    def _get_day_sales(self, date: str) -> list[CashboxSale]:
        start_dt, end_dt, session_info = self._cashbox_time_range(date)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return []

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
            if session_info:
                statement = statement.where(
                    CashboxLogModel.user_id == session_info["user_id"]
                )
            logs = session.exec(statement).all()

            import re

            result: list[CashboxSale] = []
            for log, username in logs:
                method_label = (log.payment_method or "No especificado").strip() or "No especificado"
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
                    time_label = timestamp.strftime("%H:%M")
                result.append(
                    {
                        "sale_id": str(log.id),
                        "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "time": time_label,
                        "user": username or "Desconocido",
                        "payment_method": method_label,
                        "payment_label": method_label,
                        "payment_details": payment_detail,
                        "concept": concept,
                        "amount": self._round_currency(float(log.amount or 0)),
                        "total": log.amount,
                        "is_deleted": False,
                        "payment_breakdown": [
                            {
                                "label": method_label,
                                "amount": self._round_currency(float(log.amount or 0)),
                            }
                        ],
                        "payment_kind": "",
                    }
                )
            return result

    def _build_cashbox_summary(self, date: str) -> list[dict]:
        start_date, end_date, session_info = self._cashbox_time_range(date)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return []
        method_col = sqlalchemy.func.coalesce(
            CashboxLogModel.payment_method, "No especificado"
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
            .where(CashboxLogModel.timestamp >= start_date)
            .where(CashboxLogModel.timestamp <= end_date)
            .where(CashboxLogModel.company_id == company_id)
            .where(CashboxLogModel.branch_id == branch_id)
        )
        if session_info:
            statement = statement.where(
                CashboxLogModel.user_id == session_info["user_id"]
            )
        statement = (
            statement
            .group_by(method_col)
        )
        summary: list[dict] = []
        with rx.session() as session:
            results = session.exec(statement).all()
        for method, count, amount in results:
            label = (method or "No especificado").strip() or "No especificado"
            summary.append(
                {
                    "method": label,
                    "count": int(count or 0),
                    "total": self._round_currency(float(amount or 0)),
                }
            )
        summary.sort(key=lambda item: item.get("total", 0), reverse=True)
        return summary

    def _reset_cashbox_close_summary(self):
        self.cashbox_close_modal_open = False
        self.summary_by_method = []
        self.cashbox_close_summary_sales = []
        self.cashbox_close_summary_date = ""
        self.cashbox_close_opening_amount = 0.0
        self.cashbox_close_income_total = 0.0
        self.cashbox_close_expense_total = 0.0
        self.cashbox_close_expected_total = 0.0

    def _sale_date(self, sale: CashboxSale):
        try:
            return datetime.datetime.strptime(
                sale["timestamp"], "%Y-%m-%d %H:%M:%S"
            ).date()
        except ValueError:
            return None

    def _is_advance_sale(self, sale: CashboxSale) -> bool:
        if sale.get("is_deleted"):
            return False
        if sale.get("is_advance"):
            return True
        label = (sale.get("payment_label") or "").lower()
        description = " ".join(item.get("description", "") for item in sale.get("items", []))
        return (
            "adelanto" in label
            or "adelanto" in description.lower()
        )

    def _register_reservation_advance_in_cashbox(
        self, reservation: Any, advance_amount: float
    ):
        amount = self._round_currency(advance_amount)
        if amount <= 0:
            return
        if not self.cashbox_is_open:
            return
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return
        
        description = (
            f"Adelanto {reservation['field_name']} "
            f"({reservation['start_datetime']} - {reservation['end_datetime']})"
        )
        status_value = str(reservation.get("status", "")).strip().lower()
        total_amount = float(reservation.get("total_amount", 0) or 0)
        paid_amount = float(reservation.get("paid_amount", amount) or 0)
        is_paid = status_value in {"pagado", "paid"} or paid_amount >= total_amount
        action_label = "Reserva" if is_paid else "Adelanto"
        payment_label = (getattr(self, "payment_method", "") or "").strip()
        if not payment_label:
            method_kind = (getattr(self, "payment_method_kind", "") or "cash").lower()
            payment_label = self._payment_method_label(method_kind)
        
        with rx.session() as session:
            timestamp = datetime.datetime.now()
            # Crear venta por adelanto
            new_sale = Sale(
                timestamp=timestamp,
                total_amount=amount,
                company_id=company_id,
                branch_id=branch_id,
                user_id=self.current_user.get("id"),
                status=SaleStatus.completed,
            )
            session.add(new_sale)
            session.flush()

            allocations = []
            if hasattr(self, "_build_reservation_payments"):
                allocations = self._build_reservation_payments(amount)
            if not allocations:
                allocations = [(PaymentMethodType.cash, amount)]
            for method_type, method_amount in allocations:
                if method_amount <= 0:
                    continue
                session.add(
                    SalePayment(
                        sale_id=new_sale.id,
                        company_id=company_id,
                        amount=method_amount,
                        method_type=method_type,
                        reference_code=None,
                        created_at=timestamp,
                        branch_id=branch_id,
                    )
                )
            
            # Crear SaleItem (Servicio)
            sale_item = SaleItem(
                sale_id=new_sale.id,
                product_id=None,
                quantity=1,
                unit_price=amount,
                subtotal=amount,
                product_name_snapshot=description,
                product_barcode_snapshot=str(reservation["id"]),
                product_category_snapshot="Servicios",
                company_id=company_id,
                branch_id=branch_id,
            )
            session.add(sale_item)
            session.add(
                CashboxLogModel(
                    company_id=company_id,
                    branch_id=branch_id,
                    user_id=self.current_user.get("id"),
                    action=action_label,
                    amount=amount,
                    payment_method=payment_label,
                    notes=description,
                    timestamp=timestamp,
                    sale_id=new_sale.id,
                )
            )
            session.commit()
