import reflex as rx
from typing import List, Dict, Any
import datetime
import uuid
import logging
import json
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
)
from .types import CashboxSale, CashboxSession, CashboxLogEntry, Movement
from .mixin_state import MixinState
from app.utils.exports import create_excel_workbook, style_header_row, add_data_rows, auto_adjust_column_widths

class CashState(MixinState):
    # cashbox_sales: List[CashboxSale] = [] # Removed in favor of DB
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
    cashbox_close_summary_totals: Dict[str, float] = {}
    cashbox_close_summary_sales: List[CashboxSale] = []
    cashbox_close_summary_date: str = ""
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
    _cashbox_update_trigger: int = 0
    
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
        self.petty_cash_reason = value

    @rx.event
    def add_petty_cash_movement(self):
        if not self.cashbox_is_open:
            return rx.toast("Debe aperturar la caja para registrar movimientos.", duration=3000)
        
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
            
        username = self.current_user["username"]
        
        with rx.session() as session:
            user = session.exec(select(UserModel).where(UserModel.username == username)).first()
            if not user:
                return rx.toast("Usuario no encontrado.", duration=3000)
                
            log = CashboxLogModel(
                user_id=user.id,
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
        return (
            select(CashboxLogModel, UserModel.username)
            .join(UserModel)
            .where(CashboxLogModel.action == "gasto_caja_chica")
            .order_by(desc(CashboxLogModel.timestamp))
        )

    def _petty_cash_count(self) -> int:
        statement = (
            select(sqlalchemy.func.count())
            .select_from(CashboxLogModel)
            .where(CashboxLogModel.action == "gasto_caja_chica")
        )
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

                # Format quantity: integer if no decimal part, else 2 decimals
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
        # Dependency to force update
        _ = self._cashbox_update_trigger
        
        username = "guest"
        if hasattr(self, "current_user") and self.current_user:
             username = self.current_user["username"]
        
        with rx.session() as session:
            user = session.exec(select(UserModel).where(UserModel.username == username)).first()
            if not user:
                 return {
                    "opening_amount": 0.0,
                    "opening_time": "",
                    "closing_time": "",
                    "is_open": False,
                    "opened_by": username,
                }

            cashbox_session = session.exec(
                select(CashboxSessionModel)
                .where(CashboxSessionModel.user_id == user.id)
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

        username = session_data.get("opened_by")

        with rx.session() as session:
            user = session.exec(select(UserModel).where(UserModel.username == username)).first()
            if not user:
                return opening_amount
            
            # Sumar gastos
            statement = select(sqlalchemy.func.sum(CashboxLogModel.amount)).where(
                CashboxLogModel.user_id == user.id,
                CashboxLogModel.action == "gasto_caja_chica",
                CashboxLogModel.timestamp >= opening_time
            )
            expenses = session.exec(statement).one() or 0.0
            
            return opening_amount - expenses

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

    @rx.event
    def set_cashbox_open_amount_input(self, value: float | str):
        self.cashbox_open_amount_input = str(value or "").strip()

    @rx.event
    def open_cashbox_session(self):
        if not self.current_user["privileges"]["manage_cashbox"]:
            return rx.toast("No tiene permisos para gestionar la caja.", duration=3000)
        username = self.current_user["username"]
        if self.current_user["role"].lower() == "cajero" and not hasattr(self, "token"):
            return rx.toast("Inicie sesión para abrir caja.", duration=3000)
        
        try:
            amount = float(self.cashbox_open_amount_input) if self.cashbox_open_amount_input else 0
        except ValueError:
            amount = 0
        amount = self._round_currency(amount)
        
        if amount < 0:
            return rx.toast("Ingrese un monto válido para la caja inicial.", duration=3000)
            
        with rx.session() as session:
            user = session.exec(select(UserModel).where(UserModel.username == username)).first()
            if not user:
                 return rx.toast("Usuario no encontrado.", duration=3000)

            existing = session.exec(
                select(CashboxSessionModel)
                .where(CashboxSessionModel.user_id == user.id)
                .where(CashboxSessionModel.is_open == True)
            ).first()
            
            if existing:
                 return rx.toast("Ya existe una caja abierta.", duration=3000)

            new_session = CashboxSessionModel(
                user_id=user.id,
                opening_amount=amount,
                opening_time=datetime.datetime.now(),
                is_open=True
            )
            session.add(new_session)
            session.commit()
            session.refresh(new_session)
            
            log = CashboxLogModel(
                user_id=user.id,
                action="apertura",
                amount=amount,
                notes="Apertura de caja",
                timestamp=datetime.datetime.now()
            )
            session.add(log)
            session.commit()
            
        self.cashbox_open_amount_input = ""
        self._cashbox_update_trigger += 1
        return rx.toast("Caja abierta. Jornada iniciada.", duration=3000)

    def _close_cashbox_session(self):
        username = self.current_user["username"]
        
        with rx.session() as session:
            user = session.exec(select(UserModel).where(UserModel.username == username)).first()
            if not user:
                return

            cashbox_session = session.exec(
                select(CashboxSessionModel)
                .where(CashboxSessionModel.user_id == user.id)
                .where(CashboxSessionModel.is_open == True)
            ).first()
            
            if cashbox_session:
                cashbox_session.is_open = False
                cashbox_session.closing_time = datetime.datetime.now()
                session.add(cashbox_session)
                session.commit()
        
        self._cashbox_update_trigger += 1

    def _cashbox_logs_query(self):
        statement = (
            select(CashboxLogModel, UserModel.username)
            .join(UserModel)
            .where(CashboxLogModel.action.in_(["apertura", "cierre"]))
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
        statement = (
            select(sqlalchemy.func.count())
            .select_from(CashboxLogModel)
            .where(CashboxLogModel.action.in_(["apertura", "cierre"]))
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
        query = (
            select(Sale, UserModel)
            .select_from(Sale)
            .join(UserModel, Sale.user_id == UserModel.id, isouter=True)
            .options(selectinload(Sale.items), selectinload(Sale.payments))
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
        query = select(sqlalchemy.func.count(Sale.id)).select_from(Sale)

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
            return method_type.value
        if hasattr(method_type, "value"):
            return str(method_type.value).strip().lower()
        return str(method_type or "").strip().lower()

    def _payment_method_label(self, method_key: str) -> str:
        mapping = {
            "cash": "Efectivo",
            "card": "Tarjeta",
            "wallet": "Billetera",
            "transfer": "Transferencia",
            "mixed": "Mixto",
            "other": "Otros",
        }
        return mapping.get(method_key, "Otros")

    def _payment_method_abbrev(self, method_key: str) -> str:
        mapping = {
            "cash": "Efe",
            "card": "Tar",
            "wallet": "Bil",
            "transfer": "Trans",
            "mixed": "Mix",
            "other": "Otro",
        }
        return mapping.get(method_key, "Otro")

    def _sorted_payment_keys(self, keys: list[str]) -> list[str]:
        order = ["cash", "card", "wallet", "transfer", "mixed", "other"]
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
        return f"Mixto ({'/'.join(abbrevs)})"

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
        sale_dict: CashboxSale = {
            "sale_id": str(sale.id),
            "timestamp": sale.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "user": user.username if user else "Desconocido",
            "payment_method": method_label,
            "payment_label": method_label,
            "payment_details": details_text,
            "total": total_amount,
            "is_deleted": sale.status == SaleStatus.cancelled,
            "delete_reason": sale.delete_reason,
            "items": items,
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
            {"method": method, "amount": self._format_currency(amount)}
            for method, amount in self.cashbox_close_summary_totals.items()
            if amount > 0
        ]

    @rx.var
    def cashbox_close_total_amount(self) -> str:
        total_value = sum(self.cashbox_close_summary_totals.values())
        return self._format_currency(total_value)

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
        day_sales = self._get_day_sales(today)
        if not day_sales:
            return rx.toast("No hay ventas registradas hoy.", duration=3000)
        self.cashbox_close_summary_totals = self._build_cashbox_summary(day_sales)
        self.cashbox_close_summary_sales = day_sales
        self.cashbox_close_summary_date = today
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
        
        wb, ws = create_excel_workbook("Gestion de Caja")
        
        headers = [
            "Fecha y Hora",
            "Usuario",
            "Metodo",
            "Metodo Detallado",
            "Detalle Pago",
            "Total",
            "Productos",
        ]
        style_header_row(ws, 1, headers)
        
        rows = []
        for sale in sales:
            if sale.get("is_deleted"):
                continue
            method_raw = self._normalize_wallet_label(sale.get("payment_method", ""))
            method_label = self._normalize_wallet_label(
                sale.get("payment_label", sale.get("payment_method", ""))
            )
            details = ", ".join(
                f"{item['description']} (x{item['quantity']})" for item in sale["items"]
            )
            rows.append([
                sale["timestamp"],
                sale["user"],
                method_raw,
                method_label,
                self._payment_details_text(sale.get("payment_details", "")),
                sale["total"],
                details,
            ])
            
        add_data_rows(ws, rows, 2)
        auto_adjust_column_widths(ws)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return rx.download(data=output.getvalue(), filename="gestion_caja.xlsx")

    @rx.event
    def export_cashbox_sessions(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)
        logs = self._fetch_cashbox_logs()
        if not logs:
            return rx.toast("No hay aperturas o cierres para exportar.", duration=3000)
        
        wb, ws = create_excel_workbook("Aperturas y Cierres")
        
        headers = [
            "Fecha y Hora",
            "Accion",
            "Usuario",
            "Monto Apertura",
            "Monto Cierre",
            "Totales por Metodo",
            "Notas",
        ]
        style_header_row(ws, 1, headers)
        
        rows = []
        for log in logs:
            totals_detail = ", ".join(
                f"{item.get('method', '')}: {self._round_currency(item.get('amount', 0))}"
                for item in log.get("totals_by_method", [])
                if item.get("amount", 0)
            )
            rows.append([
                log.get("timestamp", ""),
                (log.get("action") or "").capitalize(),
                log.get("user", ""),
                self._round_currency(log.get("opening_amount", 0)),
                self._round_currency(log.get("closing_total", 0)),
                totals_detail or "",
                log.get("notes", ""),
            ])
            
        add_data_rows(ws, rows, 2)
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
        
        wb, ws = create_excel_workbook("Caja Chica")
        
        headers = [
            "Fecha y Hora",
            "Usuario",
            "Motivo",
            "Cantidad",
            "Unidad",
            "Costo Unitario",
            "Total",
        ]
        style_header_row(ws, 1, headers)
        
        rows = []
        for item in movements:
            rows.append([
                item.get("timestamp", ""),
                item.get("user", ""),
                item.get("notes", ""),
                item.get("formatted_quantity", ""),
                item.get("unit", ""),
                item.get("formatted_cost", ""),
                item.get("formatted_amount", ""),
            ])
            
        add_data_rows(ws, rows, 2)
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
            
        with rx.session() as session:
            log = session.exec(select(CashboxLogModel).where(CashboxLogModel.id == int(log_id))).first()
            if not log:
                return rx.toast("Registro de caja no encontrado.", duration=3000)
            
            # Get username via user_id
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
        self.sale_delete_reason = value

    @rx.event
    def delete_sale(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        if not self.current_user["privileges"]["delete_sales"]:
            return rx.toast("No tiene permisos para eliminar ventas.", duration=3000)
        sale_id = self.sale_to_delete
        reason = self.sale_delete_reason.strip()
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
                
            sale_db = session.exec(select(Sale).where(Sale.id == sale_db_id)).first()
            
            if not sale_db:
                return rx.toast("Venta no encontrada en BD.", duration=3000)
            
            # Mark as cancelled in DB
            sale_db.status = SaleStatus.cancelled
            sale_db.delete_reason = reason
            session.add(sale_db)
            
            # Restore stock
            for item in sale_db.items:
                if item.product_id:
                    product = session.exec(select(Product).where(Product.id == item.product_id)).first()
                    if product:
                        product.stock += item.quantity
                        session.add(product)
                        
                        # Log stock movement
                        movement = StockMovement(
                            product_id=product.id,
                            user_id=self.current_user.get("id"),
                            type="Devolucion Venta",
                            quantity=item.quantity,
                            description=f"Venta anulada #{sale_db.id}: {reason}",
                            timestamp=datetime.datetime.now()
                        )
                        session.add(movement)
            session.commit()
        
        self._cashbox_update_trigger += 1
        self.close_sale_delete_modal()
        return rx.toast("Venta eliminada correctamente.", duration=3000)

    @rx.event
    def reprint_sale_receipt(self, sale_id: str):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para ver comprobantes.", duration=3000)
        
        sale_data = None
        with rx.session() as session:
            try:
                sale_db_id = int(sale_id)
                sale = session.exec(
                    select(Sale)
                    .where(Sale.id == sale_db_id)
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
        
        # Funciones auxiliares para formato de texto plano
        def center(text, width=42):
            return text.center(width)
        
        def line(width=42):
            return "-" * width
        
        def row(left, right, width=42):
            spaces = width - len(left) - len(right)
            return left + " " * max(spaces, 1) + right

        company = self._company_settings_snapshot()
        company_name = (company.get("company_name") or "").strip()
        ruc = (company.get("ruc") or "").strip()
        address = (company.get("address") or "").strip()
        phone = (company.get("phone") or "").strip()
        footer_message = (company.get("footer_message") or "").strip()
        address_lines = self._wrap_receipt_lines(address, 42)
        
        items = sale_data.get("items", [])
        payment_summary = self._payment_details_text(
            sale_data.get("payment_details")
        ) or sale_data.get("payment_method", "")
        
        # Construir recibo línea por línea
        receipt_lines = [""]
        if company_name:
            receipt_lines.append(center(company_name))
            receipt_lines.append("")
        if ruc:
            receipt_lines.append(center(f"RUC: {ruc}"))
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
            receipt_lines.append(item.get('description', ''))
            receipt_lines.append(f"{item.get('quantity', 0)} {item.get('unit', '')} x {self._format_currency(item.get('price', 0))}    {self._format_currency(item.get('subtotal', 0))}")
            receipt_lines.append("")
            receipt_lines.append(line())
        
        # Total y método de pago
        receipt_lines.extend([
            "",
            row("TOTAL A PAGAR:", self._format_currency(sale_data.get('total', 0))),
            "",
            f"Metodo de Pago: {payment_summary}",
            "",
            line(),
            "",
        ])
        if footer_message:
            receipt_lines.append(center(footer_message))
        receipt_lines.extend([" ", " ", " "])
        
        receipt_text = chr(10).join(receipt_lines)
        
        html_content = f"""<html>
<head>
<meta charset='utf-8'/>
<title>Comprobante de Pago</title>
<style>
@page {{ size: 80mm auto; margin: 0; }}
body {{ margin: 0; padding: 2mm; }}
pre {{ font-family: monospace; font-size: 12px; margin: 0; white-space: pre-wrap; }}
</style>
</head>
<body>
<pre>{receipt_text}</pre>
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
        date = self.cashbox_close_summary_date or datetime.datetime.now().strftime(
            "%Y-%m-%d"
        )
        day_sales = self.cashbox_close_summary_sales or self._get_day_sales(date)
        if not day_sales:
            return rx.toast("No hay ventas registradas hoy.", duration=3000)
        summary = self.cashbox_close_summary_totals or self._build_cashbox_summary(
            day_sales
        )
        closing_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        totals_list = [
            {"method": method, "amount": self._round_currency(amount)}
            for method, amount in summary.items()
            if amount > 0
        ]
        closing_total = self._round_currency(sum(summary.values()))
        
        with rx.session() as session:
            user = session.exec(select(UserModel).where(UserModel.username == self.current_user["username"])).first()
            if user:
                # Close session
                cashbox_session = session.exec(
                    select(CashboxSessionModel)
                    .where(CashboxSessionModel.user_id == user.id)
                    .where(CashboxSessionModel.is_open == True)
                ).first()
                
                if cashbox_session:
                    cashbox_session.is_open = False
                    cashbox_session.closing_time = datetime.datetime.now()
                    cashbox_session.closing_amount = closing_total
                    session.add(cashbox_session)
                
                # Create Log
                log = CashboxLogModel(
                    user_id=user.id,
                    action="cierre",
                    amount=closing_total,
                    notes=f"Cierre de caja {date}",
                    timestamp=datetime.datetime.now()
                )
                session.add(log)
                session.commit()
        
        # Funciones auxiliares para formato de texto plano
        def center(text, width=42):
            return text.center(width)
        
        def line(width=42):
            return "-" * width
        
        def row(left, right, width=42):
            spaces = width - len(left) - len(right)
            return left + " " * max(spaces, 1) + right
        
        # Construir recibo línea por línea
        company = self._company_settings_snapshot()
        company_name = (company.get("company_name") or "").strip()
        ruc = (company.get("ruc") or "").strip()
        address = (company.get("address") or "").strip()
        phone = (company.get("phone") or "").strip()
        address_lines = self._wrap_receipt_lines(address, 42)

        receipt_lines = [""]
        if company_name:
            receipt_lines.append(center(company_name))
            receipt_lines.append("")
        if ruc:
            receipt_lines.append(center(f"RUC: {ruc}"))
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
                "TOTALES POR METODO",
                "",
            ]
        )
        
        # Agregar totales por método
        for method, amount in summary.items():
            if amount > 0:
                receipt_lines.append(row(f"{method}:", self._format_currency(amount)))
                receipt_lines.append("")
        
        receipt_lines.append(row("TOTAL CIERRE:", self._format_currency(closing_total)))
        receipt_lines.append("")
        receipt_lines.append(line())
        receipt_lines.append("")
        receipt_lines.append("DETALLE DE VENTAS")
        receipt_lines.append("")
        
        # Agregar detalle de ventas con método de pago completo
        for sale in day_sales:
            method_label = sale.get("payment_label", sale.get("payment_method", ""))
            payment_detail = self._payment_details_text(sale.get("payment_details", ""))
            receipt_lines.append(f"{sale['timestamp']}")
            receipt_lines.append(f"Usuario: {sale['user']}")
            receipt_lines.append(f"Metodo: {method_label}")
            if payment_detail and payment_detail != method_label:
                # Truncar si es muy largo
                if len(payment_detail) > 40:
                    payment_detail = payment_detail[:37] + "..."
                receipt_lines.append(f"Detalle: {payment_detail}")
            receipt_lines.append(row("Total:", self._format_currency(sale['total'])))
            receipt_lines.append(line())
        
        receipt_lines.extend([
            "",
            center("FIN DEL REPORTE"),
            " ",
            " ",
            " ",
        ])
        
        receipt_text = chr(10).join(receipt_lines)
        
        html_content = f"""<html>
<head>
<meta charset='utf-8'/>
<title>Resumen de Caja</title>
<style>
@page {{ size: 80mm auto; margin: 0; }}
body {{ margin: 0; padding: 2mm; }}
pre {{ font-family: monospace; font-size: 12px; margin: 0; white-space: pre-wrap; }}
</style>
</head>
<body>
<pre>{receipt_text}</pre>
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
        with rx.session() as session:
            try:
                target_date = datetime.datetime.strptime(date, "%Y-%m-%d")
                start_dt = target_date.replace(hour=0, minute=0, second=0)
                end_dt = target_date.replace(hour=23, minute=59, second=59)

                sales = session.exec(
                    select(Sale, UserModel)
                    .join(UserModel, isouter=True)
                    .where(Sale.timestamp >= start_dt)
                    .where(Sale.timestamp <= end_dt)
                    .where(Sale.status != SaleStatus.cancelled)
                    .options(selectinload(Sale.payments), selectinload(Sale.items))
                ).all()

                result = []
                for sale, user in sales:
                    payments = sale.payments or []
                    payment_label = self._payment_method_display(payments)
                    payment_details_str = self._payment_summary_from_payments(payments)
                    breakdown_from_payments = self._payment_breakdown_from_payments(
                        payments
                    )
                    payment_kind = self._payment_kind_from_payments(payments)
                    if not breakdown_from_payments:
                        fallback_label = payment_label if payment_label != "-" else "Otros"
                        breakdown_from_payments = [
                            {"label": fallback_label, "amount": sale.total_amount}
                        ]

                    sale_dict = {
                        "sale_id": str(sale.id),
                        "timestamp": sale.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "user": user.username if user else "Desconocido",
                        "payment_method": payment_label,
                        "payment_label": payment_label,
                        "payment_details": payment_details_str,
                        "total": sale.total_amount,
                        "is_deleted": sale.status == SaleStatus.cancelled,
                        "payment_breakdown": breakdown_from_payments,
                        "payment_kind": payment_kind,
                    }
                    result.append(sale_dict)
                return result
            except ValueError:
                return []

    def _build_cashbox_summary(self, sales: list[CashboxSale]) -> dict[str, float]:
        summary: dict[str, float] = {}
        for sale in sales:
            breakdown = sale.get("payment_breakdown") if isinstance(sale, dict) else []
            if breakdown:
                for item in breakdown:
                    method_label = self._normalize_wallet_label(
                        item.get("label") or sale.get("payment_label") or sale.get("payment_method", "Otros")
                    )
                    amount = self._round_currency(item.get("amount", 0))
                    summary[method_label] = self._round_currency(
                        summary.get(method_label, 0) + amount
                    )
            else:
                category = self._payment_category(
                    self._normalize_wallet_label(sale.get("payment_method", "")),
                    sale.get("payment_kind", ""),
                )
                if category not in summary:
                    summary[category] = 0.0
                summary[category] = self._round_currency(summary[category] + sale["total"])
        return summary

    def _reset_cashbox_close_summary(self):
        self.cashbox_close_modal_open = False
        self.cashbox_close_summary_totals = {}
        self.cashbox_close_summary_sales = []
        self.cashbox_close_summary_date = ""

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
        
        description = (
            f"Adelanto {reservation['field_name']} "
            f"({reservation['start_datetime']} - {reservation['end_datetime']})"
        )
        
        with rx.session() as session:
            timestamp = datetime.datetime.now()
            # Create Sale for advance
            new_sale = Sale(
                timestamp=timestamp,
                total_amount=amount,
                user_id=self.current_user.get("id"),
                status=SaleStatus.completed,
            )
            session.add(new_sale)
            session.flush()

            session.add(
                SalePayment(
                    sale_id=new_sale.id,
                    amount=amount,
                    method_type=PaymentMethodType.cash,
                    reference_code=None,
                    created_at=timestamp,
                )
            )
            
            # Create SaleItem (Service)
            sale_item = SaleItem(
                sale_id=new_sale.id,
                product_id=None,
                quantity=1,
                unit_price=amount,
                subtotal=amount,
                product_name_snapshot=description,
                product_barcode_snapshot=str(reservation["id"])
            )
            session.add(sale_item)
            session.commit()
