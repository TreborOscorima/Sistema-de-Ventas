import datetime
import io
from decimal import Decimal

import reflex as rx
from sqlmodel import select
from sqlalchemy import func

from app.models import Client, Sale, SaleInstallment
from app.services.credit_service import CreditService
from app.utils.db import get_async_session
from app.utils.exports import (
    create_excel_workbook,
    style_header_row,
    add_data_rows,
    auto_adjust_column_widths,
)
from .mixin_state import MixinState


class CuentasState(MixinState):
    debtors: list[dict] = []
    selected_client: dict | None = None
    client_installments: list[SaleInstallment] = []
    show_payment_modal: bool = False
    payment_amount: str = ""
    installment_payment_method: str = "Efectivo"
    selected_installment_id: int | None = None
    total_pagadas: int = 0
    total_pendientes: int = 0
    current_client_pagadas: int = 0
    current_client_pendientes: int = 0

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
        self, installments: list[SaleInstallment]
    ) -> tuple[int, int]:
        paid_count = 0
        pending_count = 0
        for installment in installments:
            status = (installment.status or "").strip().lower()
            if status in {"paid", "completed"}:
                paid_count += 1
            elif status == "pending":
                pending_count += 1
        return paid_count, pending_count

    def _set_current_client_totals(
        self, installments: list[SaleInstallment]
    ) -> None:
        paid_count, pending_count = self._compute_installment_counts(
            installments
        )
        self.current_client_pagadas = paid_count
        self.current_client_pendientes = pending_count

    async def _refresh_installment_totals(self, session) -> None:
        paid_result = await session.exec(
            select(func.count())
            .select_from(SaleInstallment)
            .where(
                func.lower(SaleInstallment.status).in_(
                    ["paid", "completed"]
                )
            )
        )
        pending_result = await session.exec(
            select(func.count())
            .select_from(SaleInstallment)
            .where(func.lower(SaleInstallment.status) == "pending")
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
        today = datetime.date.today()
        for installment in self.client_installments:
            status = (installment.status or "pending").strip().lower()
            if status == "completed":
                status = "paid"
            is_paid = status in {"paid", "completed"}
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
                    is_overdue = due_date.date() < today and not is_paid
                except Exception:
                    is_overdue = False
            rows.append(
                {
                    "id": installment.id,
                    "number": installment.number,
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
            return
        async with get_async_session() as session:
            result = await session.exec(
                select(Client).where(Client.current_debt > 0)
            )
            self.debtors = [
                self._client_snapshot(client) for client in result.all()
            ]
            await self._refresh_installment_totals(session)

    @rx.event
    async def export_cuentas_excel(self, client_id: int | None = None):
        if not self.current_user["privileges"].get("export_data"):
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)
        if not self.current_user["privileges"].get("view_cuentas"):
            return rx.toast("No tiene permisos para ver cuentas.", duration=3000)
        normalized_client_id: int | None = None
        if isinstance(client_id, str):
            normalized_client_id = (
                int(client_id) if client_id.isdigit() else None
            )
        elif isinstance(client_id, int):
            normalized_client_id = client_id

        report_client_name = ""
        async with get_async_session() as session:
            query = (
                select(SaleInstallment, Client)
                .join(Sale, SaleInstallment.sale_id == Sale.id)
                .outerjoin(Client, Sale.client_id == Client.id)
            )
            if normalized_client_id is not None:
                query = query.where(Sale.client_id == normalized_client_id)
                client = await session.get(Client, normalized_client_id)
                if client:
                    report_client_name = client.name or ""
            query = query.order_by(
                SaleInstallment.due_date.desc(),
                SaleInstallment.id.desc(),
            )
            result = await session.exec(query)
            rows = result.all()

        workbook, sheet = create_excel_workbook("Cuentas")

        headers = ["Fecha", "Cliente", "Concepto", "Monto", "Estado"]
        style_header_row(sheet, 1, headers)

        data_rows: list[list[object]] = []
        for installment, client in rows:
            due_date = (
                installment.due_date.strftime("%Y-%m-%d")
                if installment.due_date
                else ""
            )
            client_name = client.name if client else "Sin cliente"
            concept = (
                f"Venta #{installment.sale_id} / Cuota {installment.number}"
            )
            amount = Decimal(str(installment.amount or 0))
            status_label = self._installment_status_label(installment.status)
            data_rows.append(
                [
                    due_date,
                    client_name,
                    concept,
                    self._round_currency(float(amount)),
                    status_label,
                ]
            )

        add_data_rows(sheet, data_rows, 2)
        auto_adjust_column_widths(sheet)

        filename = "Reporte_Cuentas_Global.xlsx"
        if normalized_client_id is not None:
            safe_name = self._sanitize_report_name(
                report_client_name or f"Cliente_{normalized_client_id}"
            )
            filename = f"Reporte_Cliente_{safe_name}.xlsx"

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
            refreshed = await session.get(Client, client_id)
            if refreshed:
                self.selected_client = self._client_snapshot(refreshed)
            else:
                self.selected_client = fallback
            installments = await session.exec(
                select(SaleInstallment)
                .where(SaleInstallment.sale.has(client_id=client_id))
                .order_by(SaleInstallment.due_date)
            )
            self.client_installments = installments.all()
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
            return rx.toast("No tiene permisos para gestionar cuentas.", duration=3000)
        if not self.selected_installment_id:
            return rx.toast("Seleccione una cuota para pagar.", duration=3000)
        try:
            amount = Decimal(str(self.payment_amount or "0"))
        except Exception:
            return rx.toast("Monto invalido.", duration=3000)
        if amount <= 0:
            return rx.toast("El monto debe ser mayor a cero.", duration=3000)

        method_label = (self.installment_payment_method or "").strip()
        if not method_label:
            return rx.toast("Seleccione un metodo de pago.", duration=3000)

        user_id = None
        if isinstance(self.current_user, dict):
            user_id = self.current_user.get("id")

        async with get_async_session() as session:
            try:
                await CreditService.pay_installment(
                    session,
                    self.selected_installment_id,
                    amount,
                    method_label,
                    user_id=user_id,
                )
                await session.commit()
            except Exception as exc:
                await session.rollback()
                return rx.toast(str(exc), duration=3000)

            client_id = None
            if isinstance(self.selected_client, dict):
                client_id = self.selected_client.get("id")
            if isinstance(client_id, str):
                client_id = int(client_id) if client_id.isdigit() else None
            if client_id is not None:
                refreshed = await session.get(Client, client_id)
                if refreshed:
                    self.selected_client = self._client_snapshot(refreshed)
                installments = await session.exec(
                    select(SaleInstallment)
                    .where(
                        SaleInstallment.sale.has(
                            client_id=client_id
                        )
                    )
                    .order_by(SaleInstallment.due_date)
                )
                self.client_installments = installments.all()
                self._set_current_client_totals(self.client_installments)

            debtors_result = await session.exec(
                select(Client).where(Client.current_debt > 0)
            )
            self.debtors = [
                self._client_snapshot(client)
                for client in debtors_result.all()
            ]
            await self._refresh_installment_totals(session)

        self.selected_installment_id = None
        self.payment_amount = ""
        return rx.toast("Pago registrado.", duration=3000)
