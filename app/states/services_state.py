import reflex as rx
from typing import List, Dict, Any
import datetime
import uuid
import logging
import math
import calendar
import io
from sqlmodel import select
from app.models import SaleItem, FieldReservation as FieldReservationModel, FieldPrice as FieldPriceModel
from .types import FieldReservation, ServiceLogEntry, ReservationReceipt, FieldPrice
from .mixin_state import MixinState
from app.utils.dates import get_today_str, get_current_week_str, get_current_month_str
from app.utils.exports import create_excel_workbook, style_header_row, add_data_rows, auto_adjust_column_widths

TODAY_STR = get_today_str()
CURRENT_WEEK_STR = get_current_week_str()
CURRENT_MONTH_STR = get_current_month_str()

class ServicesState(MixinState):
    service_active_tab: str = "campo"

    @rx.event
    def set_service_tab(self, tab: str):
        self.service_active_tab = tab

    field_rental_sport: str = "futbol"
    schedule_view_mode: str = "dia"
    schedule_selected_date: str = TODAY_STR
    schedule_selected_week: str = CURRENT_WEEK_STR
    schedule_selected_month: str = CURRENT_MONTH_STR
    schedule_selected_slots: List[Dict[str, str]] = []
    reservation_form: Dict[str, str] = {
        "client_name": "",
        "dni": "",
        "phone": "",
        "field_name": "",
        "sport_label": "",
        "selected_price_id": "",
        "date": TODAY_STR,
        "start_time": "00:00",
        "end_time": "01:00",
        "advance_amount": "0",
        "total_amount": "0",
        "status": "pendiente",
    }
    service_reservations: List[FieldReservation] = []
    service_admin_log: List[ServiceLogEntry] = []
    reservation_payment_id: str = ""

    def load_reservations(self):
        with rx.session() as session:
            reservations = session.exec(select(FieldReservationModel).order_by(FieldReservationModel.start_datetime.desc())).all()
            self.service_reservations = [
                {
                    "id": str(r.id),
                    "client_name": r.client_name,
                    "dni": r.client_dni or "",
                    "phone": r.client_phone or "",
                    "sport": r.sport,
                    "sport_label": self._sport_label(r.sport),
                    "field_name": r.field_name,
                    "start_datetime": r.start_datetime.strftime("%Y-%m-%d %H:%M"),
                    "end_datetime": r.end_datetime.strftime("%Y-%m-%d %H:%M"),
                    "advance_amount": r.paid_amount, # In the model paid_amount tracks what has been paid
                    "total_amount": r.total_amount,
                    "paid_amount": r.paid_amount,
                    "status": r.status,
                    "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                    "cancellation_reason": r.cancellation_reason or "",
                    "delete_reason": r.delete_reason or "",
                }
                for r in reservations
            ]
    
    @rx.var
    def reservation_selected_for_payment(self) -> FieldReservation | None:
        if not self.reservation_payment_id:
            return None
        return next(
            (r for r in self.service_reservations if r["id"] == self.reservation_payment_id),
            None,
        )

    @rx.var
    def selected_reservation_balance(self) -> float:
        if not self.reservation_selected_for_payment:
            return 0.0
        return float(self.reservation_selected_for_payment["total_amount"]) - float(self.reservation_selected_for_payment["advance_amount"])

    reservation_payment_amount: str = ""
    reservation_cancel_selection: str = ""
    reservation_cancel_reason: str = ""
    reservation_modal_open: bool = False
    reservation_modal_mode: str = "new"
    reservation_modal_reservation_id: str = ""
    reservation_search: str = ""
    reservation_filter_status: str = "todos"
    reservation_filter_start_date: str = ""
    reservation_filter_end_date: str = ""
    reservation_staged_search: str = ""
    reservation_staged_status: str = "todos"
    reservation_staged_start_date: str = ""
    reservation_staged_end_date: str = ""
    reservation_payment_routed: bool = False
    last_reservation_receipt: ReservationReceipt | None = None
    
    def set_reservation_staged_search(self, value: str):
        self.reservation_staged_search = value

    def set_reservation_staged_status(self, value: str):
        self.reservation_staged_status = value

    def set_reservation_staged_start_date(self, value: str):
        self.reservation_staged_start_date = value

    def set_reservation_staged_end_date(self, value: str):
        self.reservation_staged_end_date = value

    reservation_delete_modal_open: bool = False
    reservation_delete_selection: str = ""
    reservation_delete_reason: str = ""

    def apply_reservation_filters(self):
        self.reservation_search = self.reservation_staged_search
        self.reservation_filter_status = self.reservation_staged_status
        self.reservation_filter_start_date = self.reservation_staged_start_date
        self.reservation_filter_end_date = self.reservation_staged_end_date

    def reset_reservation_filters(self):
        self.reservation_staged_search = ""
        self.reservation_staged_status = "todos"
        self.reservation_staged_start_date = ""
        self.reservation_staged_end_date = ""
        self.apply_reservation_filters()

    def export_reservations_excel(self):
        data = self.service_reservations_for_sport
        
        if not data:
            return rx.toast("No hay datos para exportar.", duration=3000)
            
        wb, ws = create_excel_workbook("Reservas")
        
        headers = ["Fecha", "Hora Inicio", "Hora Fin", "Cliente", "DNI", "Telefono", "Deporte", "Campo", "Estado", "Monto Total", "Pagado", "Saldo"]
        style_header_row(ws, 1, headers)
        
        rows = []
        for r in data:
            try:
                start_date, start_time = r["start_datetime"].split(" ")
                _, end_time = r["end_datetime"].split(" ")
            except ValueError:
                start_date = r["start_datetime"]
                start_time = ""
                end_time = ""
                
            balance = float(r["total_amount"]) - float(r["paid_amount"])
            
            rows.append([
                start_date,
                start_time,
                end_time,
                r["client_name"],
                r["dni"],
                r["phone"],
                r.get("sport_label", r["sport"]),
                r["field_name"],
                r["status"],
                float(r["total_amount"]),
                float(r["paid_amount"]),
                balance
            ])
            
        add_data_rows(ws, rows, 2)
        auto_adjust_column_widths(ws)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return rx.download(
            data=output.getvalue(), 
            filename=f"reservas_{self.field_rental_sport}_{TODAY_STR}.xlsx"
        )

    field_prices: List[FieldPrice] = []

    def load_field_prices(self):
        with rx.session() as session:
            prices = session.exec(select(FieldPriceModel)).all()
            self.field_prices = [
                {
                    "id": str(p.id),
                    "sport": p.sport,
                    "name": p.name,
                    "price": p.price
                }
                for p in prices
            ]

    new_field_price_sport: str = "Futbol"
    new_field_price_name: str = ""
    new_field_price_amount: str = ""
    editing_field_price_id: str = ""

    def set_new_field_price_sport(self, value: str):
        self.new_field_price_sport = value

    def set_new_field_price_name(self, value: str):
        self.new_field_price_name = value

    def set_new_field_price_amount(self, value: Any):
        self.new_field_price_amount = str(value)

    def add_field_price(self):
        if self.new_field_price_name and self.new_field_price_amount:
            try:
                price = float(self.new_field_price_amount)
                with rx.session() as session:
                    new_price = FieldPriceModel(
                        sport=self.new_field_price_sport,
                        name=self.new_field_price_name,
                        price=price
                    )
                    session.add(new_price)
                    session.commit()
                
                self.new_field_price_name = ""
                self.new_field_price_amount = ""
                self.load_field_prices()
            except ValueError:
                return rx.toast("El precio debe ser un número válido.", duration=3000)

    def update_field_price(self):
        if not self.editing_field_price_id:
            return
        
        try:
            price_val = float(self.new_field_price_amount)
            with rx.session() as session:
                price = session.exec(select(FieldPriceModel).where(FieldPriceModel.id == int(self.editing_field_price_id))).first()
                if price:
                    price.name = self.new_field_price_name
                    price.price = price_val
                    price.sport = self.new_field_price_sport
                    session.add(price)
                    session.commit()
            
            # Reset editing state
            self.editing_field_price_id = ""
            self.new_field_price_name = ""
            self.new_field_price_amount = ""
            self.load_field_prices()
        except ValueError:
            return rx.toast("El precio debe ser un número válido.", duration=3000)

    def update_field_price_amount(self, price_id: str, value: str):
        try:
            val = float(value)
            with rx.session() as session:
                price = session.exec(select(FieldPriceModel).where(FieldPriceModel.id == int(price_id))).first()
                if price:
                    price.price = val
                    session.add(price)
                    session.commit()
            self.load_field_prices()
        except ValueError:
            pass

    def edit_field_price(self, price_id: str):
        with rx.session() as session:
            price = session.exec(select(FieldPriceModel).where(FieldPriceModel.id == int(price_id))).first()
            if price:
                self.editing_field_price_id = str(price.id)
                self.new_field_price_name = price.name
                self.new_field_price_amount = str(price.price)
                self.new_field_price_sport = price.sport

    def remove_field_price(self, price_id: str):
        with rx.session() as session:
            price = session.exec(select(FieldPriceModel).where(FieldPriceModel.id == int(price_id))).first()
            if price:
                session.delete(price)
                session.commit()
        
        if self.editing_field_price_id == price_id:
            self.editing_field_price_id = ""
            self.new_field_price_name = ""
            self.new_field_price_amount = ""
        self.load_field_prices()

    def select_reservation_field_price(self, price_id: str):
        self.reservation_form["selected_price_id"] = price_id
        # Buscar en todos los precios configurados para obtener los detalles
        price = next((p for p in self.field_prices if p["id"] == price_id), None)
        if price:
            self.reservation_form["total_amount"] = str(price["price"])
            self.reservation_form["field_name"] = price["name"]
            self.reservation_form["sport_label"] = self._sport_label(price["sport"])
            # Actualizar el deporte activo si el precio seleccionado pertenece a otro deporte
            price_sport_lower = price["sport"].lower()
            current_sport_lower = self.field_rental_sport.lower()
            
            if "futbol" in price_sport_lower and "futbol" not in current_sport_lower:
                 self.field_rental_sport = "futbol"
            elif "voley" in price_sport_lower and "voley" not in current_sport_lower:
                 self.field_rental_sport = "voley"

    @rx.var
    def reservation_delete_button_disabled(self) -> bool:
        return not self.reservation_delete_selection or not self.reservation_delete_reason

    @rx.var
    def reservation_selected_for_delete(self) -> FieldReservation | None:
        if not self.reservation_delete_selection:
            return None
        return next(
            (r for r in self.service_reservations if r["id"] == self.reservation_delete_selection),
            None,
        )

    @rx.var
    def service_reservations_for_sport(self) -> list[FieldReservation]:
        reservations = [
            r for r in self.service_reservations
            if r["sport"] == self.field_rental_sport
        ]
        
        # Filter by status
        if self.reservation_filter_status != "todos":
            reservations = [r for r in reservations if r["status"] == self.reservation_filter_status]
            
        # Filter by search (client name, field name)
        if self.reservation_search:
            search = self.reservation_search.lower()
            reservations = [
                r for r in reservations
                if search in r["client_name"].lower() or search in r["field_name"].lower()
            ]
            
        # Filter by date range
        if self.reservation_filter_start_date:
            reservations = [
                r for r in reservations
                if r["start_datetime"].split(" ")[0] >= self.reservation_filter_start_date
            ]
            
        if self.reservation_filter_end_date:
            reservations = [
                r for r in reservations
                if r["start_datetime"].split(" ")[0] <= self.reservation_filter_end_date
            ]
            
        return reservations

    @rx.var
    def field_prices_for_current_sport(self) -> list[FieldPrice]:
        if hasattr(self, "field_prices"):
            return [
                p for p in self.field_prices 
                if self.field_rental_sport.lower() in p["sport"].lower()
            ]
        return []

    @rx.var
    def modal_reservation(self) -> FieldReservation | None:
        if not self.reservation_modal_reservation_id:
            return None
        return self._find_reservation_by_id(self.reservation_modal_reservation_id)

    @rx.var
    def schedule_week_days(self) -> list[dict[str, str]]:
        if not self.schedule_selected_week:
            return []
        try:
            year_str, week_str = self.schedule_selected_week.split("-W")
            base_date = datetime.datetime.strptime(
                f"{year_str}-W{week_str}-1", "%G-W%V-%u"
            )
            day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
            days = []
            for offset in range(7):
                day = base_date + datetime.timedelta(days=offset)
                days.append(
                    {
                        "label": f"{day_names[offset]} {day.strftime('%d/%m')}",
                        "date": day.strftime("%Y-%m-%d"),
                    }
                )
            return days
        except ValueError:
            return []

    @rx.var
    def schedule_month_days(self) -> list[dict[str, str]]:
        if not self.schedule_selected_month:
            return []
        try:
            year, month = self.schedule_selected_month.split("-")
            year_int = int(year)
            month_int = int(month)
            _, days_in_month = calendar.monthrange(year_int, month_int)
            return [
                {
                    "label": f"{day:02d}",
                    "date": f"{year_int:04d}-{month_int:02d}-{day:02d}",
                }
                for day in range(1, days_in_month + 1)
            ]
        except (ValueError, IndexError):
            return []

    @rx.var
    def schedule_selected_slots_count(self) -> int:
        return len(self.schedule_selected_slots)

    @rx.var
    def schedule_selection_valid(self) -> bool:
        return self._selection_range() is not None

    @rx.var
    def schedule_selection_label(self) -> str:
        if not self.schedule_selected_slots:
            return "Sin horarios seleccionados"
        slots = self._sorted_selected_slots()
        start = slots[0]["start"]
        end = slots[-1]["end"]
        hours = len(slots)
        if not self._selection_range():
            return f"{start} - {end} (seleccion no consecutiva)"
        suffix = "hora" if hours == 1 else "horas"
        return f"{start} - {end} ({hours} {suffix})"

    @rx.var
    def schedule_slots(self) -> list[dict]:
        date_str = (
            self.schedule_selected_date
            or self.reservation_form.get("date", "")
            or TODAY_STR
        )
        slots: list[dict] = []
        for hour in range(24):
            start = f"{hour:02d}:00"
            end = "23:59" if hour == 23 else f"{hour + 1:02d}:00"
            reserved = self._slot_has_conflict(
                date_str, start, end, self.field_rental_sport
            )
            is_selected = any(
                selected.get("start") == start for selected in self.schedule_selected_slots
            )
            slots.append(
                {
                    "start": start,
                    "end": end,
                    "reserved": reserved,
                    "selected": is_selected,
                }
            )
        return slots

    @rx.event
    def set_service_active_tab(self, tab: str):
        self.service_active_tab = tab

    @rx.event
    def set_field_rental_sport(self, sport: str):
        normalized = (sport or "").lower()
        if normalized not in ["futbol", "voley"]:
            return
        self.field_rental_sport = normalized
        self.reservation_payment_id = ""
        self.reservation_payment_amount = ""
        self.reservation_cancel_selection = ""
        self.reservation_modal_open = False
        self.reservation_modal_mode = "new"
        self.reservation_modal_reservation_id = ""
        self.schedule_selected_date = TODAY_STR
        self.schedule_selected_week = CURRENT_WEEK_STR
        self.schedule_selected_month = CURRENT_MONTH_STR
        self._clear_schedule_selection()
        self.reservation_form = self._reservation_default_form()

    @rx.event
    def set_schedule_view(self, view: str):
        normalized = (view or "").lower()
        if normalized in ["dia", "semana", "mes"]:
            self.schedule_view_mode = normalized

    @rx.event
    def set_schedule_date(self, date: str):
        self.schedule_selected_date = date or ""
        self.update_reservation_form("date", date)
        self._clear_schedule_selection()

    @rx.event
    def set_schedule_week(self, week: str):
        self.schedule_selected_week = week or ""
        self._clear_schedule_selection()

    @rx.event
    def set_schedule_month(self, month: str):
        self.schedule_selected_month = month or ""
        self._clear_schedule_selection()

    @rx.event
    def select_week_day(self, offset: int):
        if not self.schedule_selected_week:
            return rx.toast("Seleccione una semana primero.", duration=2500)
        try:
            year_str, week_str = self.schedule_selected_week.split("-W")
            base_date = datetime.datetime.strptime(
                f"{year_str}-W{week_str}-1", "%G-W%V-%u"
            )
            target = base_date + datetime.timedelta(days=int(offset))
            date_str = target.strftime("%Y-%m-%d")
            self.schedule_selected_date = date_str
            self.update_reservation_form("date", date_str)
            self._clear_schedule_selection()
        except ValueError:
            return rx.toast("Semana invalida.", duration=2500)

    @rx.event
    def select_month_day(self, date: str):
        if not date:
            return
        try:
            parsed = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            self.schedule_selected_month = parsed.strftime("%Y-%m")
            self.schedule_selected_date = parsed.strftime("%Y-%m-%d")
            self.update_reservation_form("date", self.schedule_selected_date)
            self._clear_schedule_selection()
        except ValueError:
            return rx.toast("Dia invalido para el mes seleccionado.", duration=2500)

    @rx.event
    def select_time_slot(self, start_time: str):
        if not start_time:
            return
        try:
            hour_int = int(str(start_time).split(":")[0])
        except ValueError:
            return
        if hour_int < 0 or hour_int > 23:
            return
        start = f"{hour_int:02d}:00"
        end = "23:59" if hour_int == 23 else f"{hour_int + 1:02d}:00"
        date_str = self.schedule_selected_date or self.reservation_form.get("date", "")
        if not date_str:
            date_str = TODAY_STR
        if self._slot_has_conflict(date_str, start, end, self.field_rental_sport):
            return rx.toast("Este horario ya esta reservado. Elige otro.", duration=3000)
        self.reservation_form["start_time"] = start
        self.reservation_form["end_time"] = end
        self.reservation_form["date"] = date_str
        self.schedule_selected_date = date_str
        self.reservation_modal_open = True
        self.reservation_modal_mode = "new"
        self.reservation_modal_reservation_id = ""

    @rx.event
    def toggle_schedule_slot(self, start_time: str, end_time: str):
        if not start_time or not end_time:
            return
        date_str = (
            self.schedule_selected_date or self.reservation_form.get("date", "") or TODAY_STR
        )
        if self._slot_has_conflict(date_str, start_time, end_time, self.field_rental_sport):
            return rx.toast("Este horario ya esta reservado. Elige otro.", duration=3000)
        exists = any(slot.get("start") == start_time for slot in self.schedule_selected_slots)
        if exists:
            self.schedule_selected_slots = [
                slot for slot in self.schedule_selected_slots if slot.get("start") != start_time
            ]
        else:
            self.schedule_selected_slots.append({"start": start_time, "end": end_time})
            self.schedule_selected_slots = self._sorted_selected_slots()
        self.schedule_selected_date = date_str
        self.reservation_form["date"] = date_str
        if self.schedule_selected_slots:
            sorted_slots = self._sorted_selected_slots()
            self.reservation_form["start_time"] = sorted_slots[0]["start"]
            self.reservation_form["end_time"] = sorted_slots[-1]["end"]
            contiguous = self._selection_range()
            if contiguous:
                self.reservation_form["start_time"], self.reservation_form["end_time"] = contiguous
        self._apply_selected_price_total()

    @rx.event
    def clear_schedule_selection(self):
        self._clear_schedule_selection()

    @rx.event
    def open_selected_slots_modal(self):
        date_str = self.schedule_selected_date or TODAY_STR
        selection = self._selection_range()
        if not self.schedule_selected_slots:
            return rx.toast("Selecciona al menos un horario.", duration=2500)
        if not selection:
            return rx.toast("Selecciona horarios consecutivos para la misma reserva.", duration=3000)
        start_time, end_time = selection
        if self._slot_has_conflict(date_str, start_time, end_time, self.field_rental_sport):
            return rx.toast("El rango seleccionado tiene un cruce con otra reserva.", duration=3000)
        # Limpia el formulario antes de preparar una nueva reserva
        self.reservation_form = self._reservation_default_form()
        self.schedule_selected_date = date_str
        self.reservation_form["date"] = date_str
        self.reservation_form["start_time"] = start_time
        self.reservation_form["end_time"] = end_time
        self.reservation_form["sport_label"] = self._sport_label(self.field_rental_sport)
        self.reservation_form["selected_price_id"] = ""
        self.reservation_modal_mode = "new"
        self.reservation_modal_reservation_id = ""
        self.reservation_modal_open = True

    @rx.event
    def open_reservation_modal(self, start_time: str, end_time: str):
        date_str = self.schedule_selected_date or self.reservation_form.get("date", "") or TODAY_STR
        # Prepara un formulario limpio antes de decidir modo
        self.reservation_form = self._reservation_default_form()
        self.schedule_selected_date = date_str
        self.reservation_form["date"] = date_str
        self.reservation_form["start_time"] = start_time
        self.reservation_form["end_time"] = end_time
        self.reservation_form["sport_label"] = self._sport_label(self.field_rental_sport)
        self.reservation_form["selected_price_id"] = ""
        existing = None
        for reservation in self.service_reservations:
            if reservation.get("status") in ["cancelado", "eliminado"]:
                continue
            if reservation.get("sport") != self.field_rental_sport:
                continue
            if reservation.get("start_datetime", "").endswith(start_time) and reservation.get("start_datetime", "").startswith(date_str):
                existing = reservation
                break
        if existing:
            self.reservation_modal_mode = "view"
            self.reservation_modal_reservation_id = existing["id"]
            self.reservation_cancel_selection = existing["id"]
            self.reservation_cancel_reason = ""
        else:
            self.reservation_modal_mode = "new"
            self.reservation_modal_reservation_id = ""
        # Preselecciona el deporte actual en el selector si existe precio
        current_prices = self.field_prices_for_current_sport
        if current_prices:
            self.select_reservation_field_price(current_prices[0]["id"])
        self.reservation_modal_open = True

    @rx.event
    def close_reservation_modal(self):
        self.reservation_modal_open = False
        # Limpia modo y formulario para evitar que datos de vista anterior se mantengan
        self.reservation_modal_mode = "new"
        self.reservation_modal_reservation_id = ""
        self.reservation_form = self._reservation_default_form()

    @rx.event
    def cancel_reservation_from_modal(self):
        if not self.reservation_modal_reservation_id:
            return rx.toast("No hay reserva seleccionada.", duration=2500)
        self.reservation_cancel_selection = self.reservation_modal_reservation_id
        if not self.reservation_cancel_reason:
            self.reservation_cancel_reason = "Cancelado desde planificador."
        return self.cancel_reservation()

    @rx.event
    def pay_reservation_from_modal(self):
        if not self.reservation_modal_reservation_id:
            return rx.toast("Selecciona una reserva primero.", duration=2500)
        self.select_reservation_for_payment(self.reservation_modal_reservation_id)
        return self.pay_reservation_balance()

    @rx.event
    def print_reservation_receipt(self):
        reservation = self.modal_reservation
        if not reservation:
            return rx.toast("No hay reserva seleccionada.", duration=2500)
        if reservation["status"] != "pagado":
            return rx.toast("Solo puedes imprimir cuando la reserva esta pagada.", duration=3000)
        self._set_last_reservation_receipt(reservation)
        return rx.toast("Comprobante generado para impresion.", duration=2500)

    @rx.event
    def update_reservation_form(self, field: str, value: str):
        if field not in self.reservation_form:
            return
        self.reservation_form[field] = value or ""
        if field in ["start_time", "end_time"]:
            self._apply_selected_price_total()

    @rx.event
    def create_field_reservation(self):
        if not self.current_user["privileges"]["manage_reservations"]:
            return rx.toast("No tiene permisos para gestionar reservas.", duration=3000)
        form = self.reservation_form
        name = form.get("client_name", "").strip()
        dni = form.get("dni", "").strip()
        phone = form.get("phone", "").strip()
        field_name = form.get("field_name", "").strip() or f"Campo {self._sport_label(self.field_rental_sport)}"
        date = form.get("date", "").strip()
        start_time = form.get("start_time", "").strip()
        end_time = form.get("end_time", "").strip()
        total_amount = self._safe_amount(form.get("total_amount", "0"))
        advance_amount = self._safe_amount(form.get("advance_amount", "0"))
        status = (form.get("status", "pendiente") or "pendiente").lower()
        if not name or not date or not start_time or not end_time:
            return rx.toast("Complete los datos obligatorios de la reserva.", duration=3000)
        if total_amount <= 0:
            return rx.toast("Ingrese el monto total de la reserva.", duration=3000)
        try:
            start_dt = datetime.datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end_dt = datetime.datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
            if end_dt <= start_dt:
                return rx.toast("La hora fin debe ser mayor a la hora inicio.", duration=3000)
        except ValueError:
            return rx.toast("Formato de fecha u hora invalido.", duration=3000)
        if self._slot_has_conflict(date, start_time, end_time, self.field_rental_sport):
            return rx.toast("El horario seleccionado ya esta reservado.", duration=3000)
        paid_amount = min(advance_amount, total_amount)
        if status not in ["pendiente", "pagado"]:
            status = "pendiente"
        if paid_amount >= total_amount:
            status = "pagado"
        elif status == "pagado":
            paid_amount = total_amount
        
        with rx.session() as session:
            new_reservation = FieldReservationModel(
                client_name=name,
                client_dni=dni,
                client_phone=phone,
                sport=self.field_rental_sport,
                field_name=field_name,
                start_datetime=start_dt,
                end_datetime=end_dt,
                total_amount=total_amount,
                paid_amount=paid_amount,
                status=status,
                user_id=self.current_user["id"] if self.current_user and "id" in self.current_user else None
            )
            session.add(new_reservation)
            session.commit()
            session.refresh(new_reservation)
            
            reservation: FieldReservation = {
                "id": str(new_reservation.id),
                "client_name": new_reservation.client_name,
                "dni": new_reservation.client_dni or "",
                "phone": new_reservation.client_phone or "",
                "sport": new_reservation.sport,
                "sport_label": form.get("sport_label", self._sport_label(new_reservation.sport)),
                "field_name": new_reservation.field_name,
                "start_datetime": new_reservation.start_datetime.strftime("%Y-%m-%d %H:%M"),
                "end_datetime": new_reservation.end_datetime.strftime("%Y-%m-%d %H:%M"),
                "advance_amount": new_reservation.paid_amount,
                "total_amount": new_reservation.total_amount,
                "paid_amount": new_reservation.paid_amount,
                "status": new_reservation.status,
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "cancellation_reason": "",
                "delete_reason": "",
            }
        
        self.load_reservations()
        self._log_service_action(reservation, "reserva", 0, notes="Reserva creada", status=reservation["status"])
        
        # Usar paid_amount en lugar de advance_amount para asegurar que se registre si se marca como Pagado
        if paid_amount > 0:
            self._log_service_action(
                reservation,
                "adelanto",
                paid_amount,
                notes="Pago registrado al crear la reserva",
                status=reservation["status"],
            )
            if hasattr(self, "_register_reservation_advance_in_cashbox"):
                self._register_reservation_advance_in_cashbox(reservation, paid_amount)
                
        # No preseleccionar pago en Venta hasta que el usuario lo solicite
        self.reservation_payment_id = ""
        self.reservation_payment_amount = ""
        self.reservation_cancel_selection = ""
        self._set_last_reservation_receipt(reservation)
        self._clear_schedule_selection()
        self.reservation_form = self._reservation_default_form()
        self.reservation_modal_open = False
        
        # Si hubo pago, intentar imprimir comprobante de venta
        if paid_amount > 0:
            return self.print_reservation_receipt(reservation["id"])
        
        # Si no hubo pago, imprimir constancia de reserva
        return self.print_reservation_receipt(reservation["id"])

    @rx.event
    def select_reservation_for_payment(self, reservation_id: str):
        self.reservation_payment_id = reservation_id or ""
        reservation = self._find_reservation_by_id(self.reservation_payment_id)
        if reservation:
            balance = max(reservation["total_amount"] - reservation["paid_amount"], 0)
            self.reservation_payment_amount = f"{balance:.2f}" if balance > 0 else ""

    @rx.event
    def go_to_sale_for_reservation(self, reservation_id: str):
        reservation = self._find_reservation_by_id(reservation_id)
        if not reservation:
            return rx.toast("Reserva no encontrada.", duration=3000)
        if reservation["status"] in ["cancelado", "eliminado"]:
            return rx.toast("No se puede cobrar una reserva cancelada o eliminada.", duration=3000)
        self.select_reservation_for_payment(reservation_id)
        self.reservation_payment_routed = True
        # Redirigir usando set_page ya que es una SPA
        if hasattr(self, "set_page"):
            self.set_page("Venta")

    @rx.event
    def print_reservation_receipt(self, reservation_id: str):
        # Always use the Reservation Proof format for reservations
        reservation = self._find_reservation_by_id(reservation_id)
        
        if not reservation:
            # Fallback: Try fetching from DB if not in memory list
            with rx.session() as session:
                r = session.exec(select(FieldReservationModel).where(FieldReservationModel.id == reservation_id)).first()
                if r:
                    reservation = {
                        "id": str(r.id),
                        "client_name": r.client_name,
                        "dni": r.client_dni or "",
                        "phone": r.client_phone or "",
                        "sport": r.sport,
                        "field_name": r.field_name,
                        "start_datetime": r.start_datetime.strftime("%Y-%m-%d %H:%M"),
                        "end_datetime": r.end_datetime.strftime("%Y-%m-%d %H:%M"),
                        "total_amount": r.total_amount,
                        "paid_amount": r.paid_amount,
                        "status": r.status,
                    }

        if reservation:
            return self._print_reservation_proof(reservation)
            
        return rx.toast("Reserva no encontrada.", duration=3000)

    def _print_reservation_proof(self, reservation: FieldReservation):
        import json
        
        html_content = f"""
        <html>
            <head>
                <meta charset='utf-8' />
                <title>Constancia de Reserva</title>
                <style>
                    @page {{
                        size: 80mm auto;
                        margin: 1mm;
                    }}
                    body {{
                        font-family: monospace;
                        font-size: 10px;
                        width: 100%;
                        margin: 0;
                        padding: 0;
                        background-color: #fff;
                        color: #000;
                    }}
                    .receipt-container {{
                        width: 100%;
                        margin: 0 auto;
                        padding: 2mm 0;
                    }}
                    .header-company {{
                        text-align: center;
                        font-weight: bold;
                        font-size: 12px;
                        margin-bottom: 5px;
                        text-transform: uppercase;
                    }}
                    .header-info {{
                        text-align: center;
                        font-size: 10px;
                        margin-bottom: 2px;
                    }}
                    h1 {{
                        text-align: center;
                        font-size: 12px;
                        font-weight: bold;
                        margin: 5px 0;
                        text-transform: uppercase;
                    }}
                    .section {{
                        font-size: 10px;
                        margin-bottom: 2px;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 5px 0;
                    }}
                    td {{
                        font-size: 10px;
                        padding: 2px 0;
                        vertical-align: top;
                    }}
                    .data-table td, .details-table td {{
                        padding: 8px 0;
                    }}
                    .text-center {{ text-align: center; }}
                    .text-right {{ text-align: right; }}
                    .text-left {{ text-align: left; }}
                    .dashed-line {{
                        border-top: 1px dashed #000;
                        margin: 5px 0;
                        width: 100%;
                    }}
                    .status {{
                        text-align: center;
                        font-weight: bold;
                        margin: 10px 0;
                        font-size: 12px;
                    }}
                    .footer {{
                        text-align: center;
                        font-size: 10px;
                        margin-top: 10px;
                    }}
                </style>
            </head>
            <body>
                <div class="receipt-container">
                    <div class="header-company">LUXETY SPORT S.A.C</div>
                    <div class="header-info">RUC: 20601348676</div>
                    <div class="header-info">AV. ALFONSO UGARTE NRO. 096 LIMA- LIMA</div>
                    <div class="dashed-line"></div>
                    <h1>CONSTANCIA DE RESERVA</h1>
                    <div class="section">Fecha Emision: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
                    <div class="dashed-line"></div>
                    <table class="data-table">
                        <tr><td class="text-left">Cliente:</td><td class="text-right">{reservation['client_name']}</td></tr>
                        <tr><td class="text-left">DNI:</td><td class="text-right">{reservation.get('dni') or '-'}</td></tr>
                        <tr><td class="text-left">Campo:</td><td class="text-right">{reservation['field_name']}</td></tr>
                        <tr><td class="text-left">Inicio:</td><td class="text-right">{reservation['start_datetime']}</td></tr>
                        <tr><td class="text-left">Fin:</td><td class="text-right">{reservation['end_datetime']}</td></tr>
                    </table>
                    <div class="dashed-line"></div>
                    <table class="details-table">
                        <tr><td class="text-left">TOTAL</td><td class="text-right">S/ {float(reservation['total_amount']):.2f}</td></tr>
                        <tr><td class="text-left">A CUENTA</td><td class="text-right">S/ {float(reservation['paid_amount']):.2f}</td></tr>
                        <tr><td class="text-left" style='font-weight:bold;'>SALDO</td><td class="text-right" style='font-weight:bold;'>S/ {max(float(reservation['total_amount']) - float(reservation['paid_amount']), 0):.2f}</td></tr>
                    </table>
                    <div class="status">ESTADO: {reservation['status'].upper()}</div>
                    <div class="dashed-line"></div>
                    <div class="footer">Gracias por su preferencia</div>
                </div>
            </body>
        </html>
        """
        script = f"""
        const receiptWindow = window.open('', '_blank');
        receiptWindow.document.write({json.dumps(html_content)});
        receiptWindow.document.close();
        receiptWindow.focus();
        receiptWindow.print();
        """
        return rx.call_script(script)

    @rx.event
    def set_reservation_payment_amount(self, value: str):
        self.reservation_payment_amount = value or ""

    @rx.event
    def view_reservation_details(self, reservation_id: str):
        reservation = self._find_reservation_by_id(reservation_id)
        if not reservation:
            return rx.toast("Reserva no encontrada.", duration=3000)
        # Llena el formulario con los datos de la reserva para mostrar en el modal.
        try:
            date_part, start_time = reservation.get("start_datetime", "").split(" ")
            _, end_time = reservation.get("end_datetime", "").split(" ")
        except ValueError:
            date_part = reservation.get("start_datetime", "").split(" ")[0] if reservation.get("start_datetime") else TODAY_STR
            start_time = reservation.get("start_datetime", "").split(" ")[1] if " " in reservation.get("start_datetime", "") else ""
            end_time = reservation.get("end_datetime", "").split(" ")[1] if " " in reservation.get("end_datetime", "") else ""
        self.reservation_form = {
            "client_name": reservation.get("client_name", ""),
            "dni": reservation.get("dni", ""),
            "phone": reservation.get("phone", ""),
            "field_name": reservation.get("field_name", ""),
            "sport_label": reservation.get("sport_label", self._sport_label(reservation.get("sport", ""))),
            "selected_price_id": reservation.get("selected_price_id", ""),
            "date": date_part or self.schedule_selected_date or TODAY_STR,
            "start_time": start_time,
            "end_time": end_time,
            "advance_amount": str(reservation.get("advance_amount", 0)),
            "total_amount": str(reservation.get("total_amount", 0)),
            "status": reservation.get("status", "pendiente"),
        }
        self.reservation_modal_reservation_id = reservation_id
        self.reservation_modal_mode = "view"
        self.reservation_cancel_selection = reservation_id
        self.reservation_cancel_reason = ""
        self.reservation_modal_open = True

    @rx.event
    def apply_reservation_payment(self):
        reservation = self._find_reservation_by_id(self.reservation_payment_id)
        if not reservation:
            return rx.toast("Seleccione una reserva para registrar el pago.", duration=3000)
        if reservation["status"] in ["cancelado", "eliminado"]:
            return rx.toast("No se pueden registrar pagos en una reserva cancelada o eliminada.", duration=3000)
        amount = self._safe_amount(self.reservation_payment_amount)
        if amount <= 0:
            return rx.toast("Ingrese un monto valido.", duration=3000)
        balance = max(reservation["total_amount"] - reservation["paid_amount"], 0)
        if balance <= 0:
            self.reservation_payment_amount = ""
            return rx.toast("La reserva ya esta pagada.", duration=3000)
        applied_amount = min(amount, balance)
        reservation["paid_amount"] = self._round_currency(
            reservation["paid_amount"] + applied_amount
        )
        self._update_reservation_status(reservation)
        entry_type = "pago" if reservation["paid_amount"] >= reservation["total_amount"] else "adelanto"
        notes = "Pago completado" if entry_type == "pago" else "Pago parcial registrado"
        self._log_service_action(
            reservation,
            entry_type,
            applied_amount,
            notes=notes,
            status=reservation["status"],
        )
        self.reservation_payment_amount = ""
        self._set_last_reservation_receipt(reservation)
        return rx.toast("Pago registrado correctamente.", duration=3000)

    @rx.event
    def pay_reservation_with_payment_method(self):
        reservation = self._find_reservation_by_id(self.reservation_payment_id)
        if not reservation:
            return rx.toast("Seleccione una reserva desde Servicios -> Pagar.", duration=3000)
        if reservation["status"] in ["cancelado", "eliminado"]:
            return rx.toast("No se puede cobrar una reserva cancelada o eliminada.", duration=3000)
        balance = max(reservation["total_amount"] - reservation["paid_amount"], 0)
        if balance <= 0:
            return rx.toast("La reserva ya esta pagada.", duration=3000)
        if not self.payment_method:
            return rx.toast("Seleccione un metodo de pago.", duration=3000)

        # Validaciones segun metodo elegido, usando el saldo como total objetivo.
        if self.payment_method_kind == "cash":
            self._update_cash_feedback(total_override=balance)
            if self.payment_cash_status not in ["exact", "change"]:
                message = self.payment_cash_message or "Ingrese un monto valido en efectivo."
                return rx.toast(message, duration=3000)
        if self.payment_method_kind == "mixed":
            self._update_mixed_message(total_override=balance)
            if self.payment_mixed_status not in ["exact", "change"]:
                message = self.payment_mixed_message or "Complete los montos del pago mixto."
                return rx.toast(message, duration=3000)

        applied_amount = balance
        reservation["paid_amount"] = self._round_currency(reservation["paid_amount"] + applied_amount)
        self._update_reservation_status(reservation)
        entry_type = "pago" if reservation["paid_amount"] >= reservation["total_amount"] else "adelanto"
        payment_summary = self._generate_payment_summary()
        self._log_service_action(
            reservation,
            entry_type,
            applied_amount,
            notes=payment_summary,
            status=reservation["status"],
        )
        self.reservation_payment_amount = ""
        self._set_last_reservation_receipt(reservation)
        # Limpia montos de la UI de metodo de pago.
        self.payment_cash_amount = 0
        self.payment_cash_message = ""
        self.payment_cash_status = "neutral"
        self.payment_mixed_cash = 0
        self.payment_mixed_card = 0
        self.payment_mixed_wallet = 0
        self.payment_mixed_message = ""
        self.payment_mixed_status = "neutral"
        return rx.toast("Pago registrado con metodo de pago.", duration=3000)

    @rx.event
    def pay_reservation_balance(self):
        reservation = self._find_reservation_by_id(self.reservation_payment_id)
        if not reservation:
            return rx.toast("Seleccione una reserva para pagar el saldo.", duration=3000)
        if reservation["status"] in ["cancelado", "eliminado"]:
            return rx.toast("No se pueden registrar pagos en una reserva cancelada o eliminada.", duration=3000)
        balance = max(reservation["total_amount"] - reservation["paid_amount"], 0)
        if balance <= 0:
            return rx.toast("La reserva ya esta pagada.", duration=3000)
        self.reservation_payment_amount = f"{balance:.2f}"
        return self.apply_reservation_payment()

    @rx.event
    def select_reservation_to_cancel(self, reservation_id: str):
        self.reservation_cancel_selection = reservation_id or ""

    @rx.event
    def set_reservation_cancel_reason(self, reason: str):
        self.reservation_cancel_reason = reason or ""

    @rx.event
    def start_reservation_delete(self, reservation_id: str):
        if not self.current_user["privileges"]["manage_reservations"]:
            return rx.toast("No tiene permisos para eliminar reservas.", duration=3000)
        reservation = self._find_reservation_by_id(reservation_id)
        if not reservation:
            return rx.toast("Reserva no encontrada.", duration=3000)
        if reservation["status"] == "eliminado":
            return rx.toast("La reserva ya esta eliminada.", duration=3000)
        self.reservation_delete_selection = reservation_id
        self.reservation_delete_reason = ""
        self.reservation_delete_modal_open = True

    @rx.event
    def set_reservation_delete_reason(self, reason: str):
        self.reservation_delete_reason = reason or ""

    @rx.event
    def close_reservation_delete_modal(self):
        self.reservation_delete_modal_open = False
        self.reservation_delete_selection = ""
        self.reservation_delete_reason = ""

    @rx.event
    def set_reservation_delete_modal_open(self, open_state: bool):
        """Control the delete modal open state (Radix on_open_change compatibility)."""
        if open_state:
            self.reservation_delete_modal_open = True
        else:
            self.close_reservation_delete_modal()

    @rx.event
    def confirm_reservation_delete(self):
        with rx.session() as session:
            reservation_model = session.exec(
                select(FieldReservationModel).where(FieldReservationModel.id == self.reservation_delete_selection)
            ).first()
            
            if not reservation_model:
                self.close_reservation_delete_modal()
                return rx.toast("Reserva no encontrada.", duration=3000)
            
            reason = (self.reservation_delete_reason or "").strip()
            if not reason:
                return rx.toast("Ingresa un sustento para eliminar la reserva.", duration=3000)
            
            if reservation_model.status == "eliminado":
                self.close_reservation_delete_modal()
                return rx.toast("La reserva ya esta eliminada.", duration=3000)
            
            reservation_model.status = "eliminado"
            reservation_model.delete_reason = reason
            reservation_model.cancellation_reason = reservation_model.cancellation_reason or reason
            
            session.add(reservation_model)
            session.commit()
            session.refresh(reservation_model)
            
            reservation_dict = {
                "id": str(reservation_model.id),
                "client_name": reservation_model.client_name,
                "status": reservation_model.status
            }
            
            self._log_service_action(
                reservation_dict,
                "eliminacion",
                0,
                notes=reason,
                status="eliminado",
            )

        self.load_reservations()
        self.reservation_payment_id = ""
        self.reservation_payment_amount = ""
        self.reservation_cancel_selection = ""
        self.reservation_cancel_reason = ""
        self.close_reservation_delete_modal()
        return rx.toast("Reserva eliminada.", duration=3000)

    @rx.event
    def cancel_reservation(self):
        if not self.current_user["privileges"]["manage_reservations"]:
            return rx.toast("No tiene permisos para cancelar reservas.", duration=3000)
        
        with rx.session() as session:
            reservation_model = session.exec(
                select(FieldReservationModel).where(FieldReservationModel.id == self.reservation_cancel_selection)
            ).first()
            
            if not reservation_model:
                return rx.toast("Reserva no encontrada.", duration=3000)
            
            if reservation_model.status in ["cancelado", "eliminado"]:
                return rx.toast("La reserva ya esta cancelada o eliminada.", duration=3000)
            
            reason = (self.reservation_cancel_reason or "").strip()
            if not reason:
                return rx.toast("Ingrese el motivo de la cancelacion.", duration=3000)
            
            reservation_model.status = "cancelado"
            reservation_model.cancellation_reason = reason
            session.add(reservation_model)
            session.commit()
            session.refresh(reservation_model)
            
            # Create a dict representation for logging
            reservation_dict = {
                "id": str(reservation_model.id),
                "client_name": reservation_model.client_name,
                "status": reservation_model.status
            }
            
            self._log_service_action(
                reservation_dict,
                "cancelacion",
                0,
                notes=reason,
                status="cancelado",
            )

        self.load_reservations()
        self.reservation_payment_id = ""
        self.reservation_payment_amount = ""
        self.reservation_cancel_selection = ""
        self.reservation_cancel_reason = ""
        self.reservation_modal_open = False
        return rx.toast("Reserva cancelada.", duration=3000)

    def _sorted_selected_slots(self) -> list[dict[str, str]]:
        return sorted(
            self.schedule_selected_slots, key=lambda slot: slot.get("start", "")
        )

    def _hours_for_current_selection(self) -> int:
        selection = self._selection_range()
        if self.schedule_selected_slots and selection:
            return max(len(self.schedule_selected_slots), 1)
        start = self.reservation_form.get("start_time", "00:00")
        end = self.reservation_form.get("end_time", "00:00")
        try:
            start_dt = datetime.datetime.strptime(start, "%H:%M")
            end_dt = datetime.datetime.strptime(end, "%H:%M")
        except ValueError:
            return 1
        minutes = int((end_dt - start_dt).total_seconds() / 60)
        if minutes <= 0:
            return 1
        return max(1, math.ceil(minutes / 60))

    def _selection_range(self) -> tuple[str, str] | None:
        slots = self._sorted_selected_slots()
        if not slots:
            return None
        start = slots[0]["start"]
        end = slots[0]["end"]
        for slot in slots[1:]:
            if slot.get("start") != end:
                return None
            end = slot.get("end", end)
        return start, end

    def _clear_schedule_selection(self):
        self.schedule_selected_slots = []

    def _apply_price_total(self, price: FieldPrice):
        hours = self._hours_for_current_selection()
        total = self._round_currency((price.get("price") or 0) * hours)
        self.reservation_form["total_amount"] = f"{total:.2f}"

    def _apply_selected_price_total(self):
        price_id = self.reservation_form.get("selected_price_id", "")
        if hasattr(self, "field_prices"):
            target = next((p for p in self.field_prices if p["id"] == price_id), None)
            if not target:
                return
            self._apply_price_total(target)

    def _slot_has_conflict(
        self, date_str: str, start_time: str, end_time: str, sport: str
    ) -> bool:
        try:
            slot_start = datetime.datetime.strptime(
                f"{date_str} {start_time}", "%Y-%m-%d %H:%M"
            )
            slot_end = datetime.datetime.strptime(
                f"{date_str} {end_time}", "%Y-%m-%d %H:%M"
            )
        except ValueError:
            return False
        for reservation in self.service_reservations:
            if reservation.get("status") in ["cancelado", "eliminado"]:
                continue
            if reservation.get("sport") != sport:
                continue
            if not reservation.get("start_datetime") or not reservation.get("end_datetime"):
                continue
            try:
                res_start = datetime.datetime.strptime(
                    reservation["start_datetime"], "%Y-%m-%d %H:%M"
                )
                res_end = datetime.datetime.strptime(
                    reservation["end_datetime"], "%Y-%m-%d %H:%M"
                )
            except ValueError:
                continue
            if res_start.date().strftime("%Y-%m-%d") != date_str:
                continue
            if slot_start < res_end and slot_end > res_start:
                return True
        return False

    def _log_service_action(
        self,
        reservation: FieldReservation,
        action: str,
        amount: float,
        notes: str = "",
        status: str = "",
    ):
        self.service_admin_log.append(
            {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user": self.current_user["username"],
                "action": action,
                "reservation_id": reservation["id"],
                "client_name": reservation["client_name"],
                "amount": amount,
                "notes": notes,
                "status_snapshot": status,
            }
        )

    def _set_last_reservation_receipt(self, reservation: FieldReservation):
        balance = max(reservation["total_amount"] - reservation["paid_amount"], 0)
        start_time = reservation["start_datetime"].split(" ")[1] if " " in reservation["start_datetime"] else ""
        end_time = reservation["end_datetime"].split(" ")[1] if " " in reservation["end_datetime"] else ""
        
        self.last_reservation_receipt = {
            "cliente": reservation["client_name"],
            "deporte": reservation.get("sport_label", reservation["sport"]),
            "campo": reservation["field_name"],
            "horario": f"{reservation['start_datetime'].split(' ')[0]} {start_time} - {end_time}",
            "monto_adelanto": f"{reservation['paid_amount']:.2f}",
            "monto_total": f"{reservation['total_amount']:.2f}",
            "saldo": f"{balance:.2f}",
            "estado": reservation["status"],
        }

    def _reservation_default_form(self) -> Dict[str, str]:
        return {
            "client_name": "",
            "dni": "",
            "phone": "",
            "field_name": "",
            "sport_label": self._sport_label(self.field_rental_sport),
            "selected_price_id": "",
            "date": self.schedule_selected_date or TODAY_STR,
            "start_time": "00:00",
            "end_time": "01:00",
            "advance_amount": "0",
            "total_amount": "0",
            "status": "pendiente",
        }

    def _find_reservation_by_id(self, res_id: str) -> FieldReservation | None:
        return next((r for r in self.service_reservations if r["id"] == res_id), None)

    def _sport_label(self, sport: str) -> str:
        sport_lower = sport.lower()
        if "futbol" in sport_lower:
            return "Futbol"
        if "voley" in sport_lower:
            return "Voley"
        return sport.capitalize()

    def _safe_amount(self, value: str) -> float:
        try:
            return float(value)
        except ValueError:
            return 0.0

    def _update_reservation_status(self, reservation: FieldReservation):
        if reservation["paid_amount"] >= reservation["total_amount"]:
            reservation["status"] = "pagado"
        else:
            reservation["status"] = "pendiente"
