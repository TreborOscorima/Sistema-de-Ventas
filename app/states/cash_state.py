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
from app.models import CashboxSession as CashboxSessionModel, CashboxLog as CashboxLogModel, User as UserModel, Sale, SaleItem, StockMovement, Product
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
    cashbox_items_per_page: int = 10
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

    @rx.var
    def petty_cash_movements(self) -> List[CashboxLogEntry]:
        _ = self._cashbox_update_trigger
        with rx.session() as session:
            statement = (
                select(CashboxLogModel, UserModel.username)
                .join(UserModel)
                .where(CashboxLogModel.action == "gasto_caja_chica")
                .order_by(desc(CashboxLogModel.timestamp))
            )
            
            results = session.exec(statement).all()
            
            filtered = []
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
                    "formatted_quantity": fmt_qty
                }
                filtered.append(entry)
            return filtered

    @rx.var
    def paginated_petty_cash_movements(self) -> List[CashboxLogEntry]:
        start_index = (self.petty_cash_current_page - 1) * self.petty_cash_items_per_page
        end_index = start_index + self.petty_cash_items_per_page
        return self.petty_cash_movements[start_index:end_index]

    @rx.var
    def petty_cash_total_pages(self) -> int:
        total = len(self.petty_cash_movements)
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

    @rx.var
    def filtered_cashbox_logs(self) -> list[CashboxLogEntry]:
        if not self.current_user["privileges"]["view_cashbox"]:
            return []
            
        with rx.session() as session:
            statement = (
                select(CashboxLogModel, UserModel.username)
                .join(UserModel)
                .where(CashboxLogModel.action.in_(["apertura", "cierre"]))
                .order_by(desc(CashboxLogModel.timestamp))
            )
            
            results = session.exec(statement).all()
            
            filtered = []
            start_date = None
            end_date = None
            
            if self.cashbox_log_filter_start_date:
                try:
                    start_date = datetime.datetime.strptime(self.cashbox_log_filter_start_date, "%Y-%m-%d").date()
                except: pass
            
            if self.cashbox_log_filter_end_date:
                try:
                    end_date = datetime.datetime.strptime(self.cashbox_log_filter_end_date, "%Y-%m-%d").date()
                except: pass

            for log, username in results:
                log_date = log.timestamp.date()
                
                if start_date and log_date < start_date:
                    continue
                if end_date and log_date > end_date:
                    continue
                
                entry: CashboxLogEntry = {
                    "id": str(log.id),
                    "action": log.action,
                    "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "user": username,
                    "opening_amount": log.amount if log.action == "apertura" else 0.0,
                    "closing_total": log.amount if log.action == "cierre" else 0.0,
                    "totals_by_method": [],
                    "notes": log.notes,
                    "amount": log.amount
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

    @rx.event
    def reset_cashbox_log_filters(self):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        self.cashbox_log_filter_start_date = ""
        self.cashbox_log_filter_end_date = ""
        self.cashbox_log_staged_start_date = ""
        self.cashbox_log_staged_end_date = ""

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
        total_pages = (
            (len(self.filtered_cashbox_sales) + self.cashbox_items_per_page - 1)
            // self.cashbox_items_per_page
        )
        total_pages = total_pages or 1
        if self.cashbox_current_page < total_pages:
            self.cashbox_current_page += 1

    @rx.var
    def filtered_cashbox_sales(self) -> list[CashboxSale]:
        _ = self._cashbox_update_trigger  # Forzar recálculo cuando cambia
        if not self.current_user["privileges"]["view_cashbox"]:
            return []
        
        with rx.session() as session:
            query = select(Sale, UserModel).join(UserModel, isouter=True).order_by(desc(Sale.timestamp))
            
            if self.cashbox_filter_start_date:
                try:
                    start_date = datetime.datetime.strptime(self.cashbox_filter_start_date, "%Y-%m-%d")
                    query = query.where(Sale.timestamp >= start_date)
                except ValueError: pass
            
            if self.cashbox_filter_end_date:
                try:
                    end_date = datetime.datetime.strptime(self.cashbox_filter_end_date, "%Y-%m-%d")
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                    query = query.where(Sale.timestamp <= end_date)
                except ValueError: pass
                
            sales_results = session.exec(query).all()
            
            final_sales = []
            for sale, user in sales_results:
                # Check for advance sale
                is_advance = "adelanto" in (sale.payment_details or "").lower()
                if not self.show_cashbox_advances and is_advance:
                    continue
                
                sale_dict = {
                    "sale_id": str(sale.id),
                    "timestamp": sale.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "user": user.username if user else "Desconocido",
                    "payment_method": sale.payment_method,
                    "payment_details": sale.payment_details,
                    "total": sale.total_amount,
                    "is_deleted": sale.is_deleted,
                    "delete_reason": sale.delete_reason,
                }
                
                items = sale.items
                if not items:
                    final_sales.append(sale_dict)
                else:
                    for item in items:
                        item_sale = sale_dict.copy()
                        item_sale["items"] = [{
                            "description": item.product_name_snapshot,
                            "quantity": item.quantity,
                            "unit": "Unidad", 
                            "price": item.unit_price,
                            "sale_price": item.unit_price,
                            "subtotal": item.subtotal
                        }]
                        item_sale["service_total"] = item.subtotal
                        item_sale["total"] = item.subtotal
                        final_sales.append(item_sale)
                        
            return final_sales

    @rx.var
    def paginated_cashbox_sales(self) -> list[CashboxSale]:
        start_index = (self.cashbox_current_page - 1) * self.cashbox_items_per_page
        end_index = start_index + self.cashbox_items_per_page
        return self.filtered_cashbox_sales[start_index:end_index]

    @rx.var
    def cashbox_total_pages(self) -> int:
        total = len(self.filtered_cashbox_sales)
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
        
        sales = self.filtered_cashbox_sales
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
                sale["payment_details"],
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
        logs = self.filtered_cashbox_logs
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
            
            # Mark as deleted in DB
            sale_db.is_deleted = True
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
                sale = session.exec(select(Sale).where(Sale.id == sale_db_id)).first()
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
                        "payment_details": sale.payment_details,
                        "payment_method": sale.payment_method,
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
        
        items = sale_data.get("items", [])
        payment_summary = sale_data.get("payment_details") or sale_data.get(
            "payment_method", ""
        )
        
        # Construir recibo línea por línea
        receipt_lines = [
            "",
            center("LUXETY SPORT S.A.C."),
            "",
            center("RUC: 20601348676"),
            "",
            center("AV. ALFONSO UGARTE NRO. 096"),
            center("LIMA-LIMA"),
            "",
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
            center("GRACIAS POR SU PREFERENCIA"),
            " ",
            " ",
            " ",
        ])
        
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
        receipt_lines = [
            "",
            center("LUXETY SPORT S.A.C."),
            "",
            center("RUC: 20601348676"),
            "",
            center("AV. ALFONSO UGARTE NRO. 096"),
            center("LIMA-LIMA"),
            "",
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
            payment_detail = sale.get("payment_details", "")
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
                    .where(Sale.is_deleted == False)
                ).all()
                
                result = []
                for sale, user in sales:
                    # Crear payment_label descriptivo basado en payment_details
                    payment_label = sale.payment_method or ""
                    payment_details_str = sale.payment_details or ""
                    
                    # Determinar el label descriptivo
                    if "Mixto" in payment_details_str or "Pagos Mixtos" in payment_details_str:
                        payment_label = "Pagos Mixtos"
                    elif "Yape" in payment_details_str:
                        payment_label = "Billetera Digital / QR - Yape"
                    elif "Plin" in payment_details_str:
                        payment_label = "Billetera Digital / QR - Plin"
                    elif "Billetera" in payment_details_str or "QR" in payment_details_str:
                        payment_label = "Billetera Digital / QR"
                    elif "Tarjeta" in payment_details_str:
                        if "Debito" in payment_details_str or "Débito" in payment_details_str:
                            payment_label = "Tarjeta de Débito"
                        elif "Credito" in payment_details_str or "Crédito" in payment_details_str:
                            payment_label = "Tarjeta de Crédito"
                        else:
                            payment_label = "Tarjeta"
                    elif "Efectivo" in payment_details_str:
                        payment_label = "Efectivo"
                    
                    sale_dict = {
                        "sale_id": str(sale.id),
                        "timestamp": sale.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "user": user.username if user else "Desconocido",
                        "payment_method": sale.payment_method,
                        "payment_label": payment_label,
                        "payment_details": payment_details_str,
                        "total": sale.total_amount,
                        "is_deleted": sale.is_deleted,
                        "payment_breakdown": [{"label": payment_label, "amount": sale.total_amount}]
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
        details = (sale.get("payment_details") or "").lower()
        description = " ".join(item.get("description", "") for item in sale.get("items", []))
        return (
            "adelanto" in label
            or "adelanto" in details
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
            # Create Sale for advance
            new_sale = Sale(
                total_amount=amount,
                payment_method="Efectivo",
                payment_details=f"Adelanto registrado al crear la reserva. Monto {self._format_currency(amount)} | {description}",
                user_id=self.current_user.get("id"),
                is_deleted=False
            )
            session.add(new_sale)
            session.flush()
            
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
