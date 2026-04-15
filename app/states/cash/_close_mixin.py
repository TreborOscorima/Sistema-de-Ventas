"""Mixin de Cierre de Caja — modal, denominación, cierre del día, helpers."""
import reflex as rx
import datetime
import re
import html
import json
import logging
import sqlalchemy
from typing import Any, List
from decimal import Decimal

from sqlmodel import select, desc

from app.enums import SaleStatus
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
from ..types import CashboxSale

logger = logging.getLogger(__name__)


class CloseMixin:
    """Modal de cierre, arqueo por denominación, cierre del día y helpers."""

    # ── Computed vars para cierre ────────────────────────────────

    @rx.var(cache=True)
    def cashbox_close_totals(self) -> list[dict[str, str]]:
        if not self.current_user["privileges"]["view_cashbox"]:
            return []
        return [
            {
                "method": item.get("method", MSG.FALLBACK_NOT_SPECIFIED),
                "count": str(int(item.get("count", 0))),
                "total": self._format_currency(item.get("total", 0)),
            }
            for item in self.summary_by_method
            if item.get("total", 0) > 0
        ]

    @rx.var(cache=True)
    def cashbox_close_total_amount(self) -> str:
        total_value = self.cashbox_close_expected_total
        if total_value == 0 and self.summary_by_method:
            total_value = sum(item.get("total", 0) for item in self.summary_by_method)
        return self._format_currency(total_value)

    @rx.var(cache=True)
    def cashbox_close_opening_amount_display(self) -> str:
        return self._format_currency(self.cashbox_close_opening_amount)

    @rx.var(cache=True)
    def cashbox_close_income_total_display(self) -> str:
        return self._format_currency(self.cashbox_close_income_total)

    @rx.var(cache=True)
    def cashbox_close_expense_total_display(self) -> str:
        return self._format_currency(self.cashbox_close_expense_total)

    @rx.var(cache=True)
    def cashbox_close_expected_total_display(self) -> str:
        return self._format_currency(self.cashbox_close_expected_total)

    @rx.var(cache=True)
    def cashbox_close_counted_total_display(self) -> str:
        return self._format_currency(self.cashbox_close_counted_total)

    @rx.var(cache=True)
    def cashbox_close_discrepancy(self) -> float:
        return self._round_currency(
            self.cashbox_close_counted_total - self.cashbox_close_expected_total
        )

    @rx.var(cache=True)
    def cashbox_close_discrepancy_display(self) -> str:
        diff = self.cashbox_close_discrepancy
        sign = "+" if diff > 0 else ""
        return f"{sign}{self._format_currency(diff)}"

    @rx.var(cache=True)
    def cashbox_close_discrepancy_color(self) -> str:
        diff = self.cashbox_close_discrepancy
        if diff == 0:
            return "text-green-600"
        return "text-red-600"

    @rx.var(cache=True)
    def cashbox_close_has_counted(self) -> bool:
        """True si el cajero ingresó al menos una denominación."""
        return any(v > 0 for v in self.denomination_counts.values())

    @rx.var(cache=True)
    def cashbox_denominations_config(self) -> list[dict]:
        """Denominaciones del país actual para la UI."""
        from app.utils.db_seeds import get_country_config
        country = getattr(self, "selected_country_code", "PE")
        config = get_country_config(country)
        return config.get("denominations", [])

    @rx.var(cache=True)
    def denomination_rows(self) -> list[dict]:
        """Filas de denominación con cantidad y subtotal para la UI."""
        rows = []
        for denom in self.cashbox_denominations_config:
            key = str(denom["value"])
            count = self.denomination_counts.get(key, 0)
            subtotal = self._round_currency(denom["value"] * count)
            rows.append({
                "value": denom["value"],
                "label": denom["label"],
                "type": denom["type"],
                "key": key,
                "count": count,
                "subtotal": self._format_currency(subtotal),
            })
        return rows

    @rx.event
    def set_denomination_count(self, key: str, value: str):
        """Actualiza la cantidad de una denominación y recalcula el total."""
        try:
            count = int(value) if value else 0
            if count < 0:
                count = 0
        except (ValueError, TypeError):
            count = 0
        self.denomination_counts[key] = count
        # Recalcular total contado
        total = 0.0
        for denom in self.cashbox_denominations_config:
            k = str(denom["value"])
            c = self.denomination_counts.get(k, 0)
            total += denom["value"] * c
        self.cashbox_close_counted_total = self._round_currency(total)

    @rx.event
    def clear_denomination_counts(self):
        """Limpia todos los conteos de denominación."""
        self.denomination_counts = {}
        self.cashbox_close_counted_total = 0.0

    @rx.var(cache=True)
    def cashbox_close_sales(self) -> list[CashboxSale]:
        if not self.current_user["privileges"]["view_cashbox"]:
            return []
        return self.cashbox_close_summary_sales

    # ── Open / close modal ───────────────────────────────────────

    @rx.event
    def open_cashbox_close_modal(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        # Abrir el modal inmediatamente para feedback visual rápido
        self.cashbox_close_modal_open = True
        self.cashbox_close_summary_sales = []
        self.summary_by_method = []
        yield
        # Ahora calcular los datos pesados (5-6 DB queries)
        today = self._current_local_date_str()
        breakdown = self._build_cashbox_close_breakdown(today)
        day_sales = self._get_day_sales(today)
        summary = breakdown["summary"]
        if not day_sales and not summary and breakdown["opening_amount"] == 0:
            self.cashbox_close_modal_open = False
            yield rx.toast(MSG.CASH_NO_MOVEMENTS_TODAY, duration=3000)
            return
        self.summary_by_method = summary
        self.cashbox_close_summary_sales = day_sales
        self.cashbox_close_summary_date = today
        self.cashbox_close_opening_amount = breakdown["opening_amount"]
        self.cashbox_close_income_total = breakdown["income_total"]
        self.cashbox_close_expense_total = breakdown["expense_total"]
        self.cashbox_close_expected_total = breakdown["expected_total"]

    @rx.event
    def close_cashbox_close_modal(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        self._reset_cashbox_close_summary()

    # ── Close day ────────────────────────────────────────────────

    @rx.event
    def close_cashbox_day(self):
        if not self.current_user["privileges"]["manage_cashbox"]:
            return rx.toast(MSG.PERM_CASH, duration=3000)
        denial = self._cashbox_guard()
        if denial:
            return denial
        block = self._require_active_subscription()
        if block:
            return block
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast(MSG.VAL_COMPANY_UNDEFINED, duration=3000)
        date = self.cashbox_close_summary_date or self._current_local_date_str()
        breakdown = self._build_cashbox_close_breakdown(date)
        summary = breakdown["summary"]
        day_sales = self.cashbox_close_summary_sales or self._get_day_sales(date)
        if (
            not day_sales
            and not summary
            and breakdown["opening_amount"] == 0
        ):
            return rx.toast(MSG.CASH_NO_MOVEMENTS_TODAY, duration=3000)
        closing_timestamp = self._display_now().strftime("%Y-%m-%d %H:%M:%S")
        totals_list = [
            {
                "method": item.get("method", MSG.FALLBACK_NOT_SPECIFIED),
                "amount": self._round_currency(item.get("total", 0)),
            }
            for item in summary
            if item.get("total", 0) > 0
        ]
        opening_amount = breakdown["opening_amount"]
        income_total = breakdown["income_total"]
        expense_total = breakdown["expense_total"]
        closing_total = breakdown["expected_total"]

        # Arqueo por denominación
        counted_amount = None
        denomination_json = None
        discrepancy = 0.0
        has_counted = self.cashbox_close_has_counted
        if has_counted:
            counted_amount = Decimal(str(self.cashbox_close_counted_total))
            discrepancy = self._round_currency(
                self.cashbox_close_counted_total - closing_total
            )
            denom_detail = []
            for denom in self.cashbox_denominations_config:
                key = str(denom["value"])
                count = self.denomination_counts.get(key, 0)
                if count > 0:
                    denom_detail.append({
                        "label": denom["label"],
                        "value": denom["value"],
                        "count": count,
                        "subtotal": self._round_currency(denom["value"] * count),
                    })
            denomination_json = json.dumps(denom_detail, ensure_ascii=False)

        user_id = self.current_user.get("id")
        if user_id:
            with rx.session() as session:
                try:
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
                        cashbox_session.closing_time = self._event_timestamp()
                        cashbox_session.closing_amount = closing_total
                        if has_counted:
                            cashbox_session.counted_amount = counted_amount
                            cashbox_session.denomination_detail = denomination_json
                        session.add(cashbox_session)

                    # Crear log
                    close_notes = f"Cierre de caja {date}"
                    if has_counted:
                        close_notes += f" | Contado: {self._format_currency(self.cashbox_close_counted_total)}"
                        if discrepancy != 0:
                            sign = "+" if discrepancy > 0 else ""
                            close_notes += f" | Diferencia: {sign}{self._format_currency(discrepancy)}"
                    log = CashboxLogModel(
                        company_id=company_id,
                        branch_id=branch_id,
                        user_id=user_id,
                        action="cierre",
                        amount=closing_total,
                        notes=close_notes,
                        timestamp=self._event_timestamp()
                    )
                    session.add(log)
                    session.commit()
                except Exception:
                    session.rollback()
                    logger.exception("Error al cerrar caja para usuario %s", user_id)
                    return rx.toast(
                        "Error al cerrar la caja. Intente nuevamente.",
                        duration=4000,
                    )

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
                method = item.get("method", MSG.FALLBACK_NOT_SPECIFIED)
                receipt_lines.append(
                    row(f"{method}:", self._format_currency(amount))
                )
                receipt_lines.append("")

        receipt_lines.append(
            row("TOTAL CIERRE:", self._format_currency(closing_total))
        )
        receipt_lines.append("")

        # Sección de arqueo por denominación
        if has_counted:
            receipt_lines.append(line())
            receipt_lines.append("")
            receipt_lines.append("ARQUEO DE EFECTIVO")
            receipt_lines.append("")
            denom_detail = json.loads(denomination_json) if denomination_json else []
            for d in denom_detail:
                label = d["label"]
                count = d["count"]
                subtotal = d["subtotal"]
                receipt_lines.append(
                    row(f"{label} x{count}:", self._format_currency(subtotal))
                )
            receipt_lines.append("")
            receipt_lines.append(
                row("Total contado:", self._format_currency(self.cashbox_close_counted_total))
            )
            receipt_lines.append(
                row("Saldo esperado:", self._format_currency(closing_total))
            )
            sign = "+" if discrepancy > 0 else ""
            receipt_lines.append(
                row("Diferencia:", f"{sign}{self._format_currency(discrepancy)}")
            )
            receipt_lines.append("")

        receipt_lines.append(line())
        receipt_lines.append("")
        receipt_lines.append("DETALLE DE INGRESOS")
        receipt_lines.append("")

        # Agregar detalle de ventas con método de pago completo
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

    # ── Day sales helpers ────────────────────────────────────────

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

    def _build_cashbox_summary(self, date: str) -> list[dict]:
        start_date, end_date, session_info = self._cashbox_time_range(date)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return []
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

    def _reset_cashbox_close_summary(self):
        self.cashbox_close_modal_open = False
        self.summary_by_method = []
        self.cashbox_close_summary_sales = []
        self.cashbox_close_summary_date = ""
        self.cashbox_close_opening_amount = 0.0
        self.cashbox_close_income_total = 0.0
        self.cashbox_close_expense_total = 0.0
        self.cashbox_close_expected_total = 0.0
        self.denomination_counts = {}
        self.cashbox_close_counted_total = 0.0

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
        from app.enums import PaymentMethodType
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
            timestamp = self._event_timestamp()
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
