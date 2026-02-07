"""Estado de Cuentas por Cobrar - Gestión de créditos y cobranzas.

Este módulo maneja la vista de cuentas por cobrar:

Funcionalidades principales:
- Listado de clientes deudores
- Detalle de cuotas por cliente
- Registro de pagos de cuotas (parcial o total)
- Historial de pagos
- Exportación de reportes de deuda

Flujo típico:
    1. load_debtors() - Cargar clientes con deuda
    2. select_debtor(client) - Ver detalle de cuotas
    3. open_payment_modal(installment) - Iniciar pago
    4. confirm_installment_payment() - Registrar pago

Permisos requeridos:
- view_cuentas: Ver listado de deudores
- manage_cuentas: Registrar pagos

Clases:
    CuentasState: Estado principal del módulo de cobranzas
"""
import io
from decimal import Decimal
import datetime

import reflex as rx
from sqlmodel import select
from sqlalchemy import func

from app.models import Client, Sale, SaleInstallment
from app.services.credit_service import CreditService
from app.services.alert_service import get_overdue_count
from app.utils.db import get_async_session
from app.utils.timezone import country_today_date, country_today_start
from app.utils.exports import (
    create_excel_workbook,
    style_header_row,
    add_data_rows,
    auto_adjust_column_widths,
    add_company_header,
    add_totals_row_with_formulas,
    add_notes_section,
    CURRENCY_FORMAT,
    THIN_BORDER,
    POSITIVE_FILL,
    NEGATIVE_FILL,
    WARNING_FILL,
)
from .mixin_state import MixinState


class CuentasState(MixinState):
    """Estado de gestión de cuentas por cobrar.
    
    Permite visualizar deudores, sus cuotas pendientes y
    registrar pagos parciales o totales.
    
    Attributes:
        debtors: Lista de clientes con deuda activa
        selected_client: Cliente seleccionado para ver detalle
        client_installments: Cuotas del cliente seleccionado
        show_payment_modal: Estado del modal de pago
        payment_amount: Monto a pagar (input string)
        installment_payment_method: Método de pago seleccionado
        selected_installment_id: ID de cuota a pagar
    """
    debtors: list[dict] = []
    selected_client: dict | None = None
    client_installments: list[dict] = []
    show_payment_modal: bool = False
    payment_amount: str = ""
    installment_payment_method: str = "Efectivo"
    selected_installment_id: int | None = None
    total_pagadas: int = 0
    total_pendientes: int = 0
    current_client_pagadas: int = 0
    current_client_pendientes: int = 0
    filter_mode: str = "all"
    view_mode: str = "clients"
    overdue_installments_count: int = 0
    installments_rows: list[dict] = []
    debtors_page: int = 1
    debtors_items_per_page: int = 10
    installments_page: int = 1
    installments_items_per_page: int = 10

    def _company_time_context(self) -> tuple[str, str | None]:
        settings = self._company_settings_snapshot()
        code = (
            settings.get("country_code")
            or getattr(self, "selected_country_code", None)
            or "PE"
        )
        timezone = settings.get("timezone")
        timezone_value = str(timezone).strip() if timezone else None
        return str(code), timezone_value

    def _country_code(self) -> str:
        code, _timezone = self._company_time_context()
        return code

    def _country_today(self) -> datetime.date:
        code, timezone = self._company_time_context()
        return country_today_date(code, timezone=timezone)

    def _country_today_start(self) -> datetime.datetime:
        code, timezone = self._company_time_context()
        return country_today_start(code, timezone=timezone)

    def _query_filter_mode(self) -> str | None:
        query = ""
        try:
            query = getattr(self.router.url, "query", "") or ""
        except Exception:
            query = ""
        if not query:
            try:
                router = getattr(self, "router", None)
                raw_url = str(getattr(router, "url", ""))
                if "?" in raw_url:
                    query = raw_url.split("?", 1)[1]
            except Exception:
                query = ""
        if not query:
            return None
        from urllib.parse import parse_qs

        params = parse_qs(query.lstrip("?"))
        value = (params.get("filter") or params.get("mode") or [""])[0]
        value = (value or "").strip().lower()
        if value in {"all", "paid", "pending", "overdue"}:
            return value
        if value in {"vencidas", "vencida"}:
            return "overdue"
        return None

    def _installment_status_label(self, status: str) -> str:
        value = (status or "").strip().lower()
        mapping = {
            "paid": "Pagado",
            "completed": "Pagado",
            "partial": "Parcial",
            "pending": "Pendiente",
        }
        if value in mapping:
            return mapping[value]
        return value.capitalize() if value else "Pendiente"

    def _installment_snapshot(self, installment: SaleInstallment) -> dict:
        return {
            "id": installment.id,
            "number": installment.number,
            "status": installment.status,
            "amount": installment.amount,
            "paid_amount": installment.paid_amount,
            "due_date": installment.due_date,
            "payment_date": installment.payment_date,
        }

    def _client_snapshot(self, client: Client) -> dict:
        current_debt = client.current_debt
        if current_debt is None:
            current_debt = Decimal("0.00")
        return {
            "id": client.id,
            "name": client.name,
            "dni": client.dni,
            "phone": client.phone,
            "current_debt": current_debt,
        }

    def _sanitize_report_name(self, value: str) -> str:
        cleaned = "".join(
            char
            for char in (value or "").strip()
            if char.isalnum() or char in {" ", "_", "-"}
        )
        cleaned = cleaned.replace(" ", "_").strip("_")
        return cleaned or "Cliente"

    def _compute_installment_counts(
        self, installments: list[dict]
    ) -> tuple[int, int]:
        paid_count = 0
        pending_count = 0
        for installment in installments:
            status = (installment.get("status") or "").strip().lower()
            if status in {"paid", "completed"}:
                paid_count += 1
            elif status == "pending":
                pending_count += 1
        return paid_count, pending_count

    def _set_current_client_totals(
        self, installments: list[dict]
    ) -> None:
        paid_count, pending_count = self._compute_installment_counts(
            installments
        )
        self.current_client_pagadas = paid_count
        self.current_client_pendientes = pending_count

    async def _refresh_installment_totals(self, session) -> None:
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.total_pagadas = 0
            self.total_pendientes = 0
            return
        paid_result = await session.exec(
            select(func.count())
            .select_from(SaleInstallment)
            .where(
                func.lower(SaleInstallment.status).in_(
                    ["paid", "completed"]
                )
            )
            .where(SaleInstallment.company_id == company_id)
            .where(SaleInstallment.branch_id == branch_id)
        )
        pending_result = await session.exec(
            select(func.count())
            .select_from(SaleInstallment)
            .where(func.lower(SaleInstallment.status) == "pending")
            .where(SaleInstallment.company_id == company_id)
            .where(SaleInstallment.branch_id == branch_id)
        )
        self.total_pagadas = int(paid_result.one() or 0)
        self.total_pendientes = int(pending_result.one() or 0)

    @rx.var
    def selected_client_id(self) -> int | None:
        if isinstance(self.selected_client, dict):
            client_id = self.selected_client.get("id")
        else:
            client_id = None
        if isinstance(client_id, str):
            return int(client_id) if client_id.isdigit() else None
        if isinstance(client_id, int):
            return client_id
        return None

    @rx.var
    def client_installments_view(self) -> list[dict]:
        rows: list[dict] = []
        today = self._country_today()
        for installment in self.client_installments:
            status = (installment.get("status") or "pending").strip().lower()
            if status == "completed":
                status = "paid"
            is_paid = status in {"paid", "completed"}
            amount = Decimal(str(installment.get("amount") or 0))
            paid_amount = Decimal(str(installment.get("paid_amount") or 0))
            pending_amount = amount - paid_amount
            if pending_amount < 0:
                pending_amount = Decimal("0")
            due_date = installment.get("due_date")
            due_date_display = (
                due_date.strftime("%Y-%m-%d") if due_date else ""
            )
            is_overdue = False
            if due_date:
                try:
                    is_overdue = due_date.date() < today and not is_paid
                except Exception:
                    is_overdue = False
            rows.append(
                {
                    "id": installment.get("id"),
                    "number": installment.get("number"),
                    "due_date": due_date_display,
                    "amount": amount,
                    "paid_amount": paid_amount,
                    "pending_amount": pending_amount,
                    "has_pending": pending_amount > 0,
                    "status": status,
                    "status_label": self._installment_status_label(status),
                    "is_overdue": is_overdue,
                    "is_paid": is_paid,
                }
            )
        return rows

    @rx.event
    async def load_debtors(self):
        if not self.current_user["privileges"].get("view_cuentas"):
            self.debtors = []
            self.total_pagadas = 0
            self.total_pendientes = 0
            self.installments_rows = []
            self.overdue_installments_count = 0
            return
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.debtors = []
            self.total_pagadas = 0
            self.total_pendientes = 0
            self.installments_rows = []
            self.overdue_installments_count = 0
            return
        route_filter = self._query_filter_mode()
        if route_filter:
            self.filter_mode = route_filter
        else:
            self.filter_mode = "all"
        # Siempre iniciar en la vista de clientes
        self.view_mode = "clients"
        self.debtors_page = 1
        self.installments_page = 1
        country_code, timezone = self._company_time_context()
        async with get_async_session() as session:
            result = await session.exec(
                select(Client)
                .where(Client.current_debt > 0)
                .where(Client.company_id == company_id)
                .where(Client.branch_id == branch_id)
            )
            self.debtors = [
                self._client_snapshot(client) for client in result.all()
            ]
            await self._refresh_installment_totals(session)
            self.overdue_installments_count = await get_overdue_count(
                session,
                company_id=company_id,
                branch_id=branch_id,
                country_code=country_code,
                timezone=timezone,
            )
            await self._load_installments(session)

    @rx.event(background=True)
    async def load_debtors_background(self):
        """Carga deudores en segundo plano para entrada rápida."""
        async with self:
            await self.load_debtors()

    async def _load_installments(self, session) -> None:
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.installments_rows = []
            return
        today_start = self._country_today_start()

        query = (
            select(SaleInstallment, Client)
            .join(Sale, SaleInstallment.sale_id == Sale.id)
            .outerjoin(Client, Sale.client_id == Client.id)
            .where(SaleInstallment.company_id == company_id)
            .where(SaleInstallment.branch_id == branch_id)
            .where(Sale.company_id == company_id)
            .where(Sale.branch_id == branch_id)
        )

        mode = (self.filter_mode or "all").strip().lower()
        if mode == "paid":
            query = query.where(
                func.lower(SaleInstallment.status).in_(["paid", "completed"])
            )
        elif mode == "pending":
            query = query.where(
                func.lower(SaleInstallment.status).in_(["pending", "partial"])
            )
        elif mode == "overdue":
            query = query.where(
                func.lower(SaleInstallment.status).in_(["pending", "partial"])
            ).where(SaleInstallment.due_date < today_start)

        query = query.order_by(
            SaleInstallment.due_date.desc(),
            SaleInstallment.id.desc(),
        )

        result = await session.exec(query)
        rows = []
        today_date = self._country_today()
        for installment, client in result.all():
            status_raw = (installment.status or "pending").strip().lower()
            if status_raw == "completed":
                status_raw = "paid"
            is_paid = status_raw in {"paid", "completed"}
            amount = Decimal(str(installment.amount or 0))
            paid_amount = Decimal(str(installment.paid_amount or 0))
            pending_amount = amount - paid_amount
            if pending_amount < 0:
                pending_amount = Decimal("0")
            due_date = installment.due_date
            due_date_display = (
                due_date.strftime("%Y-%m-%d") if due_date else ""
            )
            is_overdue = False
            if due_date:
                try:
                    is_overdue = due_date.date() < today_date and not is_paid
                except Exception:
                    is_overdue = False
            client_payload = None
            if client:
                client_payload = {
                    "id": client.id,
                    "name": client.name,
                    "dni": client.dni,
                    "phone": client.phone,
                    "current_debt": client.current_debt,
                }
            rows.append(
                {
                    "id": installment.id,
                    "client": client_payload,
                    "client_name": client.name if client else "Cliente no registrado",
                    "client_dni": client.dni if client else "-",
                    "due_date": due_date_display,
                    "amount": float(amount),
                    "paid_amount": float(paid_amount),
                    "pending_amount": float(pending_amount),
                    "has_pending": pending_amount > 0,
                    "status": status_raw,
                    "status_label": self._installment_status_label(status_raw),
                    "is_overdue": is_overdue,
                    "is_paid": is_paid,
                }
            )
        self.installments_rows = rows

    @rx.event
    async def load_installments(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.installments_rows = []
            return
        async with get_async_session() as session:
            await self._load_installments(session)

    @rx.event
    async def set_filter_overdue(self):
        return await self.set_filter_mode("overdue")

    @rx.event
    async def set_filter_mode(self, mode: str):
        normalized = (mode or "").strip().lower()
        if normalized not in {"all", "paid", "pending", "overdue"}:
            normalized = "all"
        self.filter_mode = normalized
        self.view_mode = "installments"
        self.installments_page = 1
        await self.load_installments()
        return rx.call_script(self._update_filter_url_script())

    @rx.event
    async def set_filter_paid(self):
        return await self.set_filter_mode("paid")

    @rx.event
    async def set_filter_pending(self):
        return await self.set_filter_mode("pending")

    @rx.event
    async def set_filter_all(self):
        return await self.set_filter_mode("all")

    @rx.event
    def set_view_mode(self, mode: str):
        normalized = (mode or "").strip().lower()
        if normalized in {"clients", "installments"}:
            self.view_mode = normalized
            if normalized == "clients":
                self.debtors_page = 1
            else:
                self.installments_page = 1
            if normalized == "installments":
                return rx.call_script(self._update_filter_url_script())

    def _update_filter_url_script(self) -> str:
        mode = (self.filter_mode or "all").strip().lower()
        return (
            "(() => {"
            "const url = new URL(window.location.href);"
            f"url.searchParams.set('filter', '{mode}');"
            "window.history.replaceState(null, '', url.toString());"
            "})()"
        )

    @rx.var
    def debtors_total_pages(self) -> int:
        total_items = len(self.debtors or [])
        if total_items == 0:
            return 1
        per_page = max(self.debtors_items_per_page, 1)
        return (total_items + per_page - 1) // per_page

    @rx.var
    def paginated_debtors(self) -> list[dict]:
        total_pages = self.debtors_total_pages
        page = min(max(self.debtors_page, 1), total_pages)
        per_page = max(self.debtors_items_per_page, 1)
        offset = (page - 1) * per_page
        return (self.debtors or [])[offset : offset + per_page]

    @rx.var
    def installments_total_pages(self) -> int:
        total_items = len(self.installments_rows or [])
        if total_items == 0:
            return 1
        per_page = max(self.installments_items_per_page, 1)
        return (total_items + per_page - 1) // per_page

    @rx.var
    def paginated_installments_rows(self) -> list[dict]:
        total_pages = self.installments_total_pages
        page = min(max(self.installments_page, 1), total_pages)
        per_page = max(self.installments_items_per_page, 1)
        offset = (page - 1) * per_page
        return (self.installments_rows or [])[offset : offset + per_page]

    @rx.event
    def next_debtors_page(self):
        if self.debtors_page < self.debtors_total_pages:
            self.debtors_page += 1

    @rx.event
    def prev_debtors_page(self):
        if self.debtors_page > 1:
            self.debtors_page -= 1

    @rx.event
    def next_installments_page(self):
        if self.installments_page < self.installments_total_pages:
            self.installments_page += 1

    @rx.event
    def prev_installments_page(self):
        if self.installments_page > 1:
            self.installments_page -= 1

    @rx.event
    async def export_cuentas_excel(self, client_id: int | None = None):
        if not self.current_user["privileges"].get("export_data"):
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)
        if not self.current_user["privileges"].get("view_cuentas"):
            return rx.toast("No tiene permisos para ver cuentas.", duration=3000)
        currency_label = self._currency_symbol_clean()
        currency_format = self._currency_excel_format()
        normalized_client_id: int | None = None
        if isinstance(client_id, str):
            normalized_client_id = (
                int(client_id) if client_id.isdigit() else None
            )
        elif isinstance(client_id, int):
            normalized_client_id = client_id

        report_client_name = ""
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        async with get_async_session() as session:
            query = (
                select(SaleInstallment, Client)
                .join(Sale, SaleInstallment.sale_id == Sale.id)
                .outerjoin(Client, Sale.client_id == Client.id)
                .where(Sale.company_id == company_id)
                .where(Sale.branch_id == branch_id)
                .where(SaleInstallment.company_id == company_id)
                .where(SaleInstallment.branch_id == branch_id)
            )
            if normalized_client_id is not None:
                query = query.where(Sale.client_id == normalized_client_id)
                client = await session.exec(
                    select(Client)
                    .where(Client.id == normalized_client_id)
                    .where(Client.company_id == company_id)
                    .where(Client.branch_id == branch_id)
                )
                client = client.first()
                if client:
                    report_client_name = client.name or ""
            query = query.order_by(
                SaleInstallment.due_date.desc(),
                SaleInstallment.id.desc(),
            )
            result = await session.exec(query)
            rows = result.all()

        company_name = getattr(self, "company_name", "") or "EMPRESA"
        today = datetime.datetime.now().strftime("%d/%m/%Y")
        period_label = f"Corte: {today}"

        total_installments = len(rows)
        total_amount = Decimal("0")
        total_paid = Decimal("0")
        total_pending = Decimal("0")
        paid_count = 0
        pending_count = 0
        overdue_count = 0
        for installment, _ in rows:
            amount = Decimal(str(installment.amount or 0))
            paid_amount = Decimal(str(installment.paid_amount or 0))
            pending_amount = amount - paid_amount
            total_amount += amount
            total_paid += paid_amount
            total_pending += pending_amount
            status_label = self._installment_status_label(installment.status).lower()
            if "pagad" in status_label:
                paid_count += 1
            elif "vencid" in status_label:
                overdue_count += 1
            else:
                pending_count += 1
        
        workbook, sheet = create_excel_workbook("Cuentas por Cobrar")
        
        # Título según si es global o por cliente
        title = f"ESTADO DE CUENTA - {report_client_name.upper()}" if report_client_name else "CUENTAS POR COBRAR - REPORTE GLOBAL"
        
        # Encabezado profesional
        row = add_company_header(sheet, company_name, title, period_label, columns=7)

        row += 1
        sheet.cell(row=row, column=1, value="RESUMEN DE CARTERA")
        row += 1
        sheet.cell(row=row, column=1, value="Cuotas registradas:")
        sheet.cell(row=row, column=2, value=total_installments)
        row += 1
        sheet.cell(row=row, column=1, value="Cuotas pagadas:")
        sheet.cell(row=row, column=2, value=paid_count)
        row += 1
        sheet.cell(row=row, column=1, value="Cuotas pendientes:")
        sheet.cell(row=row, column=2, value=pending_count)
        row += 1
        sheet.cell(row=row, column=1, value="Cuotas vencidas:")
        sheet.cell(row=row, column=2, value=overdue_count)
        row += 1
        sheet.cell(row=row, column=1, value=f"Total comprometido ({currency_label}):")
        sheet.cell(row=row, column=2, value=float(total_amount)).number_format = currency_format
        row += 1
        sheet.cell(row=row, column=1, value=f"Total cobrado ({currency_label}):")
        sheet.cell(row=row, column=2, value=float(total_paid)).number_format = currency_format
        row += 1
        sheet.cell(row=row, column=1, value=f"Saldo pendiente ({currency_label}):")
        sheet.cell(row=row, column=2, value=float(total_pending)).number_format = currency_format
        row += 2

        headers = [
            "Fecha Vencimiento",
            "Cliente",
            "Concepto",
            f"Monto Cuota ({currency_label})",
            f"Monto Pagado ({currency_label})",
            f"Saldo Pendiente ({currency_label})",
            "Estado",
        ]
        style_header_row(sheet, row, headers)
        data_start = row + 1
        row += 1

        for installment, client in rows:
            due_date = (
                installment.due_date.strftime("%d/%m/%Y")
                if installment.due_date
                else "Sin fecha"
            )
            client_name = client.name if client else "Cliente no registrado"
            concept = (
                f"Venta #{installment.sale_id} - Cuota {installment.number}"
            )
            amount = float(Decimal(str(installment.amount or 0)))
            paid_amount = float(Decimal(str(installment.paid_amount or 0)))
            status_label = self._installment_status_label(installment.status)
            
            sheet.cell(row=row, column=1, value=due_date)
            sheet.cell(row=row, column=2, value=client_name)
            sheet.cell(row=row, column=3, value=concept)
            sheet.cell(row=row, column=4, value=amount).number_format = currency_format
            sheet.cell(row=row, column=5, value=paid_amount).number_format = currency_format
            # Saldo = Fórmula: Monto - Pagado
            sheet.cell(row=row, column=6, value=f"=D{row}-E{row}").number_format = currency_format
            sheet.cell(row=row, column=7, value=status_label)
            
            # Color según estado
            status_cell = sheet.cell(row=row, column=7)
            status_lower = status_label.lower()
            if "pagad" in status_lower:
                status_cell.fill = POSITIVE_FILL
            elif "vencid" in status_lower:
                status_cell.fill = NEGATIVE_FILL
            elif "pendiente" in status_lower:
                status_cell.fill = WARNING_FILL
            
            for col in range(1, 8):
                sheet.cell(row=row, column=col).border = THIN_BORDER
            row += 1

        # Fila de totales
        totals_row = row
        add_totals_row_with_formulas(sheet, totals_row, data_start, [
            {"type": "label", "value": "TOTALES"},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "sum", "col_letter": "D", "number_format": currency_format},
            {"type": "sum", "col_letter": "E", "number_format": currency_format},
            {"type": "sum", "col_letter": "F", "number_format": currency_format},
            {"type": "text", "value": ""},
        ])
        
        # Notas explicativas
        add_notes_section(sheet, totals_row, [
            "Monto Cuota: Valor original de la cuota a pagar.",
            "Monto Pagado: Dinero recibido hasta la fecha.",
            "Saldo Pendiente = Monto Cuota - Monto Pagado (fórmula verificable).",
            "Pagada: Cuota completamente saldada.",
            "Pendiente: Cuota vigente, aún no vencida.",
            "Vencida: Cuota pasó su fecha de vencimiento sin pagarse.",
        ], columns=7)
        
        auto_adjust_column_widths(sheet)

        filename = "Reporte_Cuentas_Global.xlsx"
        if normalized_client_id is not None:
            safe_name = self._sanitize_report_name(
                report_client_name or f"Cliente_{normalized_client_id}"
            )
            filename = f"Estado_Cuenta_{safe_name}.xlsx"

        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return rx.download(data=output.getvalue(), filename=filename)

    @rx.event
    async def open_detail(self, client: dict | Client):
        if not self.current_user["privileges"].get("view_cuentas"):
            return rx.toast("No tiene permisos para ver cuentas.", duration=3000)
        if not client:
            return
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return
        client_id = None
        fallback: dict | None = None
        if isinstance(client, dict):
            client_id = client.get("id")
            fallback = dict(client)
        else:
            client_id = getattr(client, "id", None)
            if client_id is not None:
                fallback = self._client_snapshot(client)
        if isinstance(client_id, str):
            client_id = int(client_id) if client_id.isdigit() else None
        if client_id is None:
            return

        async with get_async_session() as session:
            refreshed = await session.exec(
                select(Client)
                .where(Client.id == client_id)
                .where(Client.company_id == company_id)
                .where(Client.branch_id == branch_id)
            )
            refreshed = refreshed.first()
            if refreshed:
                self.selected_client = self._client_snapshot(refreshed)
            else:
                self.selected_client = fallback
            installments = await session.exec(
                select(SaleInstallment)
                .where(SaleInstallment.sale.has(client_id=client_id))
                .where(SaleInstallment.company_id == company_id)
                .where(SaleInstallment.branch_id == branch_id)
                .order_by(SaleInstallment.due_date)
            )
            self.client_installments = [
                self._installment_snapshot(installment)
                for installment in installments.all()
            ]
            self._set_current_client_totals(self.client_installments)
        self.payment_amount = ""
        self.selected_installment_id = None
        self.show_payment_modal = True

    @rx.event
    def close_detail(self):
        self.show_payment_modal = False
        self.selected_client = None
        self.client_installments = []
        self.selected_installment_id = None
        self.payment_amount = ""
        self.current_client_pagadas = 0
        self.current_client_pendientes = 0

    @rx.event
    def prepare_payment(self, installment_id: int, amount: Decimal):
        self.selected_installment_id = installment_id
        try:
            value = Decimal(str(amount or "0"))
        except Exception:
            value = Decimal("0")
        if value < 0:
            value = Decimal("0")
        self.payment_amount = f"{value:.2f}"

    @rx.event
    def set_payment_amount(self, value: float | str):
        self.payment_amount = str(value or "").strip()

    @rx.event
    def set_installment_payment_method(self, value: str):
        self.installment_payment_method = value or "Efectivo"

    @rx.event
    def clear_payment_selection(self):
        self.selected_installment_id = None
        self.payment_amount = ""

    @rx.event
    async def submit_payment(self):
        if not self.current_user["privileges"].get("manage_cuentas"):
            self.add_notification(
                "No tiene permisos para gestionar cuentas.", "error"
            )
            return
        block = self._require_active_subscription()
        if block:
            if isinstance(block, list):
                for action in block:
                    yield action
            else:
                yield block
            return
        if not self.selected_installment_id:
            self.add_notification("Seleccione una cuota para pagar.", "error")
            return
        try:
            amount = Decimal(str(self.payment_amount or "0"))
        except Exception:
            self.add_notification("Monto invalido.", "error")
            return
        if amount <= 0:
            self.add_notification(
                "El monto debe ser mayor a cero.", "error"
            )
            return

        method_label = (self.installment_payment_method or "").strip()
        if not method_label:
            self.add_notification(
                "Seleccione un metodo de pago.", "error"
            )
            return

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.add_notification("Empresa no definida.", "error")
            return

        user_id = None
        if isinstance(self.current_user, dict):
            user_id = self.current_user.get("id")

        self.is_loading = True
        yield

        try:
            async with get_async_session() as session:
                try:
                    await CreditService.pay_installment(
                        session,
                        self.selected_installment_id,
                        amount,
                        method_label,
                        user_id=user_id,
                        company_id=company_id,
                        branch_id=branch_id,
                    )
                    await session.commit()
                except Exception as exc:
                    await session.rollback()
                    self.add_notification(str(exc), "error")
                    return

                client_id = None
                if isinstance(self.selected_client, dict):
                    client_id = self.selected_client.get("id")
                if isinstance(client_id, str):
                    client_id = int(client_id) if client_id.isdigit() else None
                if client_id is not None:
                    refreshed = await session.exec(
                        select(Client)
                        .where(Client.id == client_id)
                        .where(Client.company_id == company_id)
                        .where(Client.branch_id == branch_id)
                    )
                    refreshed = refreshed.first()
                    if refreshed:
                        self.selected_client = self._client_snapshot(refreshed)
                    installments = await session.exec(
                        select(SaleInstallment)
                        .where(
                            SaleInstallment.sale.has(
                                client_id=client_id
                            )
                        )
                        .where(SaleInstallment.company_id == company_id)
                        .where(SaleInstallment.branch_id == branch_id)
                        .order_by(SaleInstallment.due_date)
                    )
                    self.client_installments = [
                        self._installment_snapshot(installment)
                        for installment in installments.all()
                    ]
                    self._set_current_client_totals(self.client_installments)

                debtors_result = await session.exec(
                    select(Client)
                    .where(Client.current_debt > 0)
                    .where(Client.company_id == company_id)
                    .where(Client.branch_id == branch_id)
                )
                self.debtors = [
                    self._client_snapshot(client)
                    for client in debtors_result.all()
                ]
                await self._refresh_installment_totals(session)
                await self._load_installments(session)
        finally:
            self.is_loading = False

        self.selected_installment_id = None
        self.payment_amount = ""
        self.add_notification("Pago registrado.", "success")
        return
