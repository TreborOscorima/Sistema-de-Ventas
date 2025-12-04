import reflex as rx
from typing import List, Dict, Any
import datetime
import uuid
import logging
import json
import io
from io import BytesIO
from .types import CashboxSale, CashboxSession, CashboxLogEntry, Movement
from .mixin_state import MixinState
from app.utils.exports import create_excel_workbook, style_header_row, add_data_rows, auto_adjust_column_widths

class CashState(MixinState):
    cashbox_sales: List[CashboxSale] = []
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

    def _get_or_create_cashbox_session(self, username: str) -> CashboxSession:
        key = (username or "").strip().lower()
        if key not in self.cashbox_sessions:
            self.cashbox_sessions[key] = {
                "opening_amount": 0.0,
                "opening_time": "",
                "closing_time": "",
                "is_open": False,
                "opened_by": key,
            }
        return self.cashbox_sessions[key]

    @rx.var
    def current_cashbox_session(self) -> CashboxSession:
        if hasattr(self, "current_user"):
            return self._get_or_create_cashbox_session(self.current_user["username"])
        return self._get_or_create_cashbox_session("guest")

    @rx.var
    def cashbox_is_open(self) -> bool:
        return bool(self.current_cashbox_session.get("is_open"))

    @rx.var
    def cashbox_opening_amount(self) -> float:
        return float(self.current_cashbox_session.get("opening_amount", 0))

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
        
        if amount <= 0:
            return rx.toast("Ingrese un monto válido para la caja inicial.", duration=3000)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session = self._get_or_create_cashbox_session(username)
        session["opening_amount"] = amount
        session["opening_time"] = timestamp
        session["closing_time"] = ""
        session["is_open"] = True
        session["opened_by"] = username
        self.cashbox_sessions[username.lower()] = session
        self.cashbox_open_amount_input = ""
        self.cashbox_logs.append(
            {
                "id": str(uuid.uuid4()),
                "action": "apertura",
                "timestamp": timestamp,
                "user": username,
                "opening_amount": amount,
                "closing_total": 0.0,
                "totals_by_method": [],
                "notes": "Apertura de caja",
            }
        )
        if hasattr(self, "history"):
            self.history.append(
                {
                    "id": str(uuid.uuid4()),
                    "timestamp": timestamp,
                    "type": "Apertura de Caja",
                    "product_description": "Caja inicial",
                    "quantity": 0,
                    "unit": "-",
                    "total": amount,
                    "payment_method": "Caja",
                    "payment_details": f"Caja inicial de {username}",
                    "user": username,
                    "sale_id": "",
                }
            )
        return rx.toast("Caja abierta. Jornada iniciada.", duration=3000)

    def _close_cashbox_session(self):
        username = self.current_user["username"]
        session = self._get_or_create_cashbox_session(username)
        session["is_open"] = False
        session["closing_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cashbox_sessions[username.lower()] = session

    @rx.var
    def filtered_cashbox_logs(self) -> list[CashboxLogEntry]:
        if not self.current_user["privileges"]["view_cashbox"]:
            return []
        logs = sorted(
            self.cashbox_logs, key=lambda entry: entry.get("timestamp", ""), reverse=True
        )
        start_date = None
        end_date = None
        if self.cashbox_log_filter_start_date:
            try:
                start_date = datetime.datetime.strptime(
                    self.cashbox_log_filter_start_date, "%Y-%m-%d"
                ).date()
            except Exception as e:
                logging.exception(f"Error parsing cashbox log start date: {e}")
        if self.cashbox_log_filter_end_date:
            try:
                end_date = datetime.datetime.strptime(
                    self.cashbox_log_filter_end_date, "%Y-%m-%d"
                ).date()
            except Exception as e:
                logging.exception(f"Error parsing cashbox log end date: {e}")
        filtered: list[CashboxLogEntry] = []
        for log in logs:
            timestamp = log.get("timestamp", "")
            try:
                log_date = datetime.datetime.strptime(
                    timestamp.split(" ")[0], "%Y-%m-%d"
                ).date()
            except Exception:
                continue
            if start_date and log_date < start_date:
                continue
            if end_date and log_date > end_date:
                continue
            filtered.append(log)
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
        if not self.current_user["privileges"]["view_cashbox"]:
            return []
        sales = sorted(
            self.cashbox_sales, key=lambda s: s["timestamp"], reverse=True
        )
        if not self.show_cashbox_advances:
            sales = [sale for sale in sales if not self._is_advance_sale(sale)]
        if self.cashbox_filter_start_date:
            try:
                start_date = datetime.datetime.strptime(
                    self.cashbox_filter_start_date, "%Y-%m-%d"
                ).date()
                sales = [
                    sale
                    for sale in sales
                    if self._sale_date(sale) and self._sale_date(sale) >= start_date
                ]
            except ValueError as e:
                logging.exception(f"Error parsing cashbox start date: {e}")
        if self.cashbox_filter_end_date:
            try:
                end_date = datetime.datetime.strptime(
                    self.cashbox_filter_end_date, "%Y-%m-%d"
                ).date()
                sales = [
                    sale
                    for sale in sales
                    if self._sale_date(sale) and self._sale_date(sale) <= end_date
                ]
            except ValueError as e:
                logging.exception(f"Error parsing cashbox end date: {e}")
        
        for sale in sales:
            self._ensure_sale_payment_fields(sale)

        final_sales = []
        for sale in sales:
            items = sale.get("items", [])
            if not items:
                final_sales.append(sale)
                continue

            for item in items:
                item_sale = sale.copy()
                item_sale["items"] = [item]
                item_total = self._round_currency(item.get("subtotal", 0))
                item_sale["service_total"] = item_total
                item_sale["total"] = item_total
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
        if not self.cashbox_sales:
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
        for sale in self.filtered_cashbox_sales:
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
    def show_cashbox_log(self, log_id: str):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para Gestion de Caja.", duration=3000)
        entry = next((log for log in self.cashbox_logs if log["id"] == log_id), None)
        if not entry:
            return rx.toast("Registro de caja no encontrado.", duration=3000)
        self.cashbox_log_selected = entry
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
        sale = next((s for s in self.cashbox_sales if s["sale_id"] == sale_id), None)
        if not sale:
            return rx.toast("Venta no encontrada.", duration=3000)
        if sale.get("is_deleted"):
            return rx.toast("Esta venta ya fue eliminada.", duration=3000)
        
        if hasattr(self, "inventory"):
            for item in sale["items"]:
                product_id = item["description"].lower().strip()
                if product_id in self.inventory:
                    self.inventory[product_id]["stock"] += item["quantity"]
        
        if hasattr(self, "history"):
            self.history = [m for m in self.history if m.get("sale_id") != sale_id]
            self.history.append(
                {
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "Venta Eliminada",
                    "product_description": f"Venta anulada ({sale_id})",
                    "quantity": 0,
                    "unit": "-",
                    "total": -sale["total"],
                    "payment_method": "Anulado",
                    "payment_details": reason,
                    "user": self.current_user["username"],
                    "sale_id": sale_id,
                }
            )
        sale["is_deleted"] = True
        sale["delete_reason"] = reason
        self.close_sale_delete_modal()
        return rx.toast("Venta eliminada correctamente.", duration=3000)

    @rx.event
    def reprint_sale_receipt(self, sale_id: str):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast("No tiene permisos para ver comprobantes.", duration=3000)
        
        sale = next((s for s in self.cashbox_sales if s["sale_id"] == sale_id), None)
        if not sale:
            return rx.toast("Venta no encontrada.", duration=3000)
        items = sale.get("items", [])
        rows = "".join(
            f"<tr><td colspan='2'><strong>{item.get('description', '')}</strong></td></tr>"
            f"<tr><td>{item.get('quantity', 0)} {item.get('unit', '')} x {self._format_currency(item.get('price', 0))}</td><td style='text-align:right;'>{self._format_currency(item.get('subtotal', 0))}</td></tr>"
            for item in items
        )
        payment_summary = sale.get("payment_details") or sale.get(
            "payment_method", ""
        )
        html_content = f"""
        <html>
            <head>
                <meta charset='utf-8' />
                <title>Comprobante de Pago</title>
                <style>
                    @page {{
                        size: 58mm auto;
                        margin: 2mm;
                    }}
                    body {{
                        font-family: 'Courier New', monospace;
                        width: 56mm;
                        margin: 0 auto;
                        font-size: 11px;
                    }}
                    h1 {{
                        text-align: center;
                        font-size: 14px;
                        margin: 0 0 6px 0;
                    }}
                    .section {{
                        margin-bottom: 6px;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                    }}
                    td {{
                        padding: 2px 0;
                        text-align: left;
                    }}
                    td:last-child {{
                        text-align: right;
                    }}
                    hr {{
                        border: 0;
                        border-top: 1px dashed #000;
                        margin: 6px 0;
                    }}
                </style>
            </head>
            <body>
                <h1>Comprobante de Pago</h1>
                <div class="section"><strong>Fecha:</strong> {sale.get('timestamp', '')}</div>
                <div class="section"><strong>Usuario:</strong> {sale.get('user', '')}</div>
                <hr />
                <table>
                    {rows}
                </table>
                <hr />
                <div class="section"><strong>Total General:</strong> {self._format_currency(sale.get('service_total', sale.get('total', 0)))} </div>
                <div class="section"><strong>Metodo de Pago:</strong> {payment_summary}</div>
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
        self.cashbox_logs.append(
            {
                "id": str(uuid.uuid4()),
                "action": "cierre",
                "timestamp": closing_timestamp,
                "user": self.current_user["username"],
                "opening_amount": self.cashbox_opening_amount,
                "closing_total": closing_total,
                "totals_by_method": totals_list,
                "notes": f"Cierre de caja {date}",
            }
        )
        summary_rows = "".join(
            f"<tr><td>{method}</td><td>{self._format_currency(amount)}</td></tr>"
            for method, amount in summary.items()
            if amount > 0
        )
        grand_total_row = f"<tr><td><strong>Total cierre</strong></td><td><strong>{self._format_currency(closing_total)}</strong></td></tr>"
        detail_rows = "".join(
            (
                lambda method_label, breakdown_text: f"<tr><td>{sale['timestamp']}</td><td>{sale['user']}</td><td>{method_label}{('<br><small>' + breakdown_text + '</small>') if breakdown_text else ''}</td><td>{self._format_currency(sale['total'])}</td></tr>"
            )(
                sale.get("payment_label", sale.get("payment_method", "")),
                " / ".join(
                    f"{item.get('label', '')}: {self._format_currency(item.get('amount', 0))}"
                    for item in sale.get("payment_breakdown", [])
                    if item.get("amount", 0)
                ),
            )
            for sale in day_sales
        )
        html_content = f"""
        <html>
            <head>
                <meta charset='utf-8' />
                <title>Resumen de Caja</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 24px; }}
                    h1 {{ text-align: center; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f3f4f6; }}
                </style>
            </head>
            <body>
                <h1>Resumen Diario de Caja</h1>
                <p><strong>Fecha:</strong> {date}</p>
                <p><strong>Responsable:</strong> {self.current_user['username']}</p>
                <h2>Totales por método</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Método</th>
                            <th>Monto</th>
                        </tr>
                    </thead>
                    <tbody>
                        {summary_rows}
                        {grand_total_row}
                    </tbody>
                </table>
                <h2>Detalle de ventas</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Fecha y Hora</th>
                            <th>Usuario</th>
                            <th>Método</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {detail_rows}
                    </tbody>
                </table>
            </body>
        </html>
        """
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
        day_sales = [
            sale
            for sale in self.cashbox_sales
            if sale["timestamp"].startswith(date) and not sale.get("is_deleted")
        ]
        for sale in day_sales:
            self._ensure_sale_payment_fields(sale)
        return day_sales

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
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sale_id = str(uuid.uuid4())
        description = (
            f"Adelanto {reservation['field_name']} "
            f"({reservation['start_datetime']} - {reservation['end_datetime']})"
        )
        self.cashbox_sales.append(
            {
                "sale_id": sale_id,
                "timestamp": timestamp,
                "user": self.current_user["username"],
                "payment_method": "Efectivo",
                "payment_kind": "cash",
                "payment_label": "Efectivo (Adelanto)",
                "payment_breakdown": [{"label": "Efectivo", "amount": amount}],
                "payment_details": f"Adelanto registrado al crear la reserva. Monto {self._format_currency(amount)}",
                "total": amount,
                "service_total": amount,
                "items": [
                    {
                        "temp_id": reservation["id"],
                        "barcode": reservation["id"],
                        "description": description,
                        "category": "Servicios",
                        "quantity": 1,
                        "unit": "Servicio",
                        "price": amount,
                        "sale_price": amount,
                        "subtotal": amount,
                    }
                ],
                "is_deleted": False,
                "delete_reason": "",
                "is_advance": True,
            }
        )
