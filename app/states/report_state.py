"""
Estado para la gestión de reportes contables y financieros.

Proporciona funcionalidades para generar reportes profesionales
para evaluaciones administrativas, contables y financieras.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import reflex as rx
from sqlmodel import select, func
from sqlalchemy import exists

from app.constants import MAX_REPORT_ROWS
from app.enums import SaleStatus
from app.models import Sale, SaleItem, CashboxLog, SaleInstallment, Product, ProductVariant
from app.services.report_service import (
    generate_sales_report,
    generate_inventory_report,
    generate_receivables_report,
    generate_cashbox_report,
    generate_promotions_report,
    generate_price_lists_report,
)
from .mixin_state import MixinState

logger = logging.getLogger(__name__)


class _ReportTooLargeError(Exception):
    """Lanzado cuando el rango de datos supera MAX_REPORT_ROWS."""


def _run_report_sync(params: dict):
    """Ejecuta la generación del reporte en un hilo separado (no bloquea el event loop).

    Abre su propia sesión sync y llama a la función de report_service correspondiente.
    Devuelve (bytes_del_excel, nombre_archivo).
    """
    report_type = params["report_type"]
    company_id = params["company_id"]
    branch_id = params["branch_id"]
    start_date = params["start_date"]
    end_date = params["end_date"]

    with rx.session() as session:
        session.info["tenant_bypass"] = True

        if MAX_REPORT_ROWS > 0:
            if report_type == "ventas":
                count_query = (
                    select(func.count(Sale.id))
                    .where(Sale.timestamp >= start_date)
                    .where(Sale.timestamp <= end_date)
                    .where(Sale.company_id == company_id)
                    .where(Sale.branch_id == branch_id)
                )
                if not params["include_cancelled"]:
                    count_query = count_query.where(
                        Sale.status != SaleStatus.cancelled
                    )
                total = session.exec(count_query).one()
                if isinstance(total, tuple):
                    total = total[0]
                if int(total or 0) > MAX_REPORT_ROWS:
                    raise _ReportTooLargeError("Rango demasiado grande.")

            elif report_type == "inventario":
                pw = session.exec(
                    select(func.count(Product.id))
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                    .where(
                        ~exists()
                        .where(ProductVariant.product_id == Product.id)
                        .where(ProductVariant.company_id == company_id)
                        .where(ProductVariant.branch_id == branch_id)
                    )
                ).one()
                if isinstance(pw, tuple):
                    pw = pw[0]
                vc = session.exec(
                    select(func.count(ProductVariant.id))
                    .where(ProductVariant.company_id == company_id)
                    .where(ProductVariant.branch_id == branch_id)
                ).one()
                if isinstance(vc, tuple):
                    vc = vc[0]
                if (int(pw or 0) + int(vc or 0)) > MAX_REPORT_ROWS:
                    raise _ReportTooLargeError("Inventario demasiado grande.")

            elif report_type == "cuentas":
                total = session.exec(
                    select(func.count(SaleInstallment.id))
                    .where(SaleInstallment.status != "paid")
                    .where(SaleInstallment.company_id == company_id)
                    .where(SaleInstallment.branch_id == branch_id)
                ).one()
                if isinstance(total, tuple):
                    total = total[0]
                if int(total or 0) > MAX_REPORT_ROWS:
                    raise _ReportTooLargeError("Cuentas por cobrar demasiado grandes.")

            elif report_type == "caja":
                total = session.exec(
                    select(func.count(CashboxLog.id))
                    .where(CashboxLog.timestamp >= start_date)
                    .where(CashboxLog.timestamp <= end_date)
                    .where(CashboxLog.company_id == company_id)
                    .where(CashboxLog.branch_id == branch_id)
                ).one()
                if isinstance(total, tuple):
                    total = total[0]
                if int(total or 0) > MAX_REPORT_ROWS:
                    raise _ReportTooLargeError("Reporte de caja demasiado grande.")

            elif report_type == "promociones":
                total = session.exec(
                    select(func.count(SaleItem.id))
                    .join(Sale, Sale.id == SaleItem.sale_id)
                    .where(SaleItem.applied_promotion_id.is_not(None))
                    .where(Sale.timestamp >= start_date)
                    .where(Sale.timestamp <= end_date)
                    .where(Sale.status != SaleStatus.cancelled)
                    .where(SaleItem.company_id == company_id)
                    .where(SaleItem.branch_id == branch_id)
                ).one()
                if isinstance(total, tuple):
                    total = total[0]
                if int(total or 0) > MAX_REPORT_ROWS:
                    raise _ReportTooLargeError("Reporte de promociones demasiado grande.")

            elif report_type == "listas_precios":
                total = session.exec(
                    select(func.count(SaleItem.id))
                    .join(Sale, Sale.id == SaleItem.sale_id)
                    .where(Sale.timestamp >= start_date)
                    .where(Sale.timestamp <= end_date)
                    .where(Sale.status != SaleStatus.cancelled)
                    .where(SaleItem.company_id == company_id)
                    .where(SaleItem.branch_id == branch_id)
                ).one()
                if isinstance(total, tuple):
                    total = total[0]
                if int(total or 0) > MAX_REPORT_ROWS:
                    raise _ReportTooLargeError(
                        "Reporte de listas de precios demasiado grande."
                    )

        kw = {
            "company_name": params["company_name"],
            "currency_symbol": params["currency_symbol"],
            "company_id": company_id,
            "branch_id": branch_id,
            "country_code": params["country_code"],
            "timezone": params["timezone"],
            "generated_at": params["generated_at"],
        }

        if report_type == "ventas":
            output = generate_sales_report(
                session, start_date, end_date,
                include_cancelled=params["include_cancelled"], **kw
            )
            filename = (
                f"Reporte_Ventas_{params['start_str']}_{params['end_str']}.xlsx"
            )
        elif report_type == "inventario":
            output = generate_inventory_report(
                session,
                include_zero_stock=params["include_zero_stock"], **kw
            )
            filename = f"Inventario_Valorizado_{params['now_str']}.xlsx"
        elif report_type == "cuentas":
            output = generate_receivables_report(session, **kw)
            filename = f"Cuentas_por_Cobrar_{params['now_str']}.xlsx"
        elif report_type == "caja":
            output = generate_cashbox_report(session, start_date, end_date, **kw)
            filename = (
                f"Reporte_Caja_{params['start_str']}_{params['end_str']}.xlsx"
            )
        elif report_type == "promociones":
            output = generate_promotions_report(session, start_date, end_date, **kw)
            filename = (
                f"Reporte_Promociones_{params['start_str']}_{params['end_str']}.xlsx"
            )
        elif report_type == "listas_precios":
            output = generate_price_lists_report(
                session, start_date, end_date, **kw
            )
            filename = (
                f"Reporte_ListasPrecios_{params['start_str']}_{params['end_str']}.xlsx"
            )
        else:
            raise ValueError(f"Tipo de reporte no válido: {report_type!r}")

    return output.getvalue(), filename


class ReportState(MixinState):
    """Estado para generación de reportes."""

    # Configuración del reporte
    report_type: str = "ventas"  # ventas, inventario, cuentas, caja
    report_period: str = "month"  # Valores: today, week, month, quarter, year, custom
    custom_start_date: str = ""
    custom_end_date: str = ""

    # Estado de generación
    report_loading: bool = False
    report_error: str = ""
    report_ready: bool = False
    _report_download_data: bytes = rx.field(default=b"", is_var=False)
    _report_download_filename: str = rx.field(default="", is_var=False)

    # Opciones de reporte
    include_cancelled: bool = False
    include_zero_stock: bool = True

    # Nombre de empresa (configurable)
    company_name: str = "TUWAYKIAPP"

    @rx.var(cache=True)
    def period_options(self) -> list[dict[str, str]]:
        """Opciones de período disponibles."""
        return [
            {"value": "today", "label": "Hoy"},
            {"value": "week", "label": "Esta Semana"},
            {"value": "month", "label": "Este Mes"},
            {"value": "quarter", "label": "Este Trimestre"},
            {"value": "year", "label": "Este Año"},
            {"value": "custom", "label": "Personalizado"},
        ]

    @rx.var(cache=True)
    def report_types(self) -> list[dict[str, str]]:
        """Tipos de reportes disponibles."""
        return [
            {"value": "ventas", "label": "Reporte de Ventas Consolidado", "icon": "shopping-cart"},
            {"value": "inventario", "label": "Inventario Valorizado", "icon": "package"},
            {"value": "cuentas", "label": "Cuentas por Cobrar", "icon": "credit-card"},
            {"value": "caja", "label": "Gestión de Caja", "icon": "banknote"},
            {"value": "promociones", "label": "Rendimiento de Promociones", "icon": "ticket"},
            {"value": "listas_precios", "label": "Rendimiento por Lista de Precios", "icon": "tag"},
        ]

    @rx.var(cache=True)
    def selected_report_label(self) -> str:
        """Etiqueta del reporte seleccionado."""
        for rt in self.report_types:
            if rt["value"] == self.report_type:
                return rt["label"]
        return "Reporte"

    @rx.var(cache=True)
    def period_label(self) -> str:
        """Etiqueta del período seleccionado."""
        labels = {
            "today": "Hoy",
            "week": "Esta Semana",
            "month": "Este Mes",
            "quarter": "Este Trimestre",
            "year": "Este Año",
            "custom": "Personalizado",
        }
        return labels.get(self.report_period, "Este Mes")

    @rx.var(cache=True)
    def report_period_label(self) -> str:
        """Etiqueta del período para reportes (no colisiona con Dashboard)."""
        if self.report_period == "custom":
            if self.custom_start_date and self.custom_end_date:
                try:
                    start = datetime.strptime(self.custom_start_date, "%Y-%m-%d").strftime("%d/%m/%Y")
                    end = datetime.strptime(self.custom_end_date, "%Y-%m-%d").strftime("%d/%m/%Y")
                    return f"{start} - {end}"
                except ValueError:
                    return f"{self.custom_start_date} a {self.custom_end_date}"
            return "Personalizado"
        labels = {
            "today": "Hoy",
            "week": "Esta Semana",
            "month": "Este Mes",
            "quarter": "Este Trimestre",
            "year": "Este Año",
        }
        return labels.get(self.report_period, "Este Mes")

    @rx.event
    def set_report_type(self, value: str):
        """Establece el tipo de reporte."""
        self.report_type = value
        self.report_error = ""

    @rx.event
    def set_report_period(self, value: str):
        """Establece el período del reporte."""
        self.report_period = value
        self.report_error = ""

    @rx.event
    def set_custom_start(self, value: str):
        """Establece fecha inicio personalizada."""
        self.custom_start_date = value

    @rx.event
    def set_custom_end(self, value: str):
        """Establece fecha fin personalizada."""
        self.custom_end_date = value

    @rx.event
    def toggle_include_cancelled(self):
        """Alterna inclusión de ventas anuladas."""
        self.include_cancelled = not self.include_cancelled

    @rx.event
    def toggle_include_zero_stock(self):
        """Alterna inclusión de productos sin stock."""
        self.include_zero_stock = not self.include_zero_stock

    def _calculate_period_dates(self):
        """Calcula fechas de inicio y fin del período seleccionado."""
        now_local = self._display_now()
        today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now_local.replace(hour=23, minute=59, second=59, microsecond=999999)

        period = self.report_period

        if period == "today":
            return (
                self._company_local_datetime_to_utc_naive(today_start),
                self._company_local_datetime_to_utc_naive(today_end),
            )
        elif period == "week":
            start = today_start - timedelta(days=today_start.weekday())
            return (
                self._company_local_datetime_to_utc_naive(start),
                self._company_local_datetime_to_utc_naive(today_end),
            )
        elif period == "month":
            start = today_start.replace(day=1)
            return (
                self._company_local_datetime_to_utc_naive(start),
                self._company_local_datetime_to_utc_naive(today_end),
            )
        elif period == "quarter":
            quarter = (now_local.month - 1) // 3
            start_month = quarter * 3 + 1
            start = today_start.replace(month=start_month, day=1)
            return (
                self._company_local_datetime_to_utc_naive(start),
                self._company_local_datetime_to_utc_naive(today_end),
            )
        elif period == "year":
            start = today_start.replace(month=1, day=1)
            return (
                self._company_local_datetime_to_utc_naive(start),
                self._company_local_datetime_to_utc_naive(today_end),
            )
        elif period == "custom":
            try:
                start = datetime.strptime(self.custom_start_date, "%Y-%m-%d")
                end = datetime.strptime(self.custom_end_date, "%Y-%m-%d")
                end = end.replace(hour=23, minute=59, second=59)
                return (
                    self._company_local_datetime_to_utc_naive(start),
                    self._company_local_datetime_to_utc_naive(end),
                )
            except (ValueError, TypeError):
                start = today_start.replace(day=1)
                return (
                    self._company_local_datetime_to_utc_naive(start),
                    self._company_local_datetime_to_utc_naive(today_end),
                )
        else:
            # Por defecto: este mes
            start = today_start.replace(day=1)
            return (
                self._company_local_datetime_to_utc_naive(start),
                self._company_local_datetime_to_utc_naive(today_end),
            )

    @rx.event(background=True)
    async def generate_report(self):
        """Genera el reporte seleccionado.

        Patrón lock/work/lock: el state lock se libera durante la generación del Excel
        (CPU + IO síncrono) para no bloquear interacciones del usuario mientras trabaja.
        """
        # ── Paso 1: lock corto — validar y capturar parámetros ──────────────
        async with self:
            if not self.current_user["privileges"].get("export_data"):
                self.report_error = "No tiene permisos para exportar reportes."
                return

            self.report_loading = True
            self.report_error = ""
            self.report_ready = False
            self._report_download_data = b""
            self._report_download_filename = ""

            company_id = self._company_id()
            branch_id = self._branch_id()
            if not company_id or not branch_id:
                self.report_loading = False
                self.report_error = "Empresa o sucursal no definida."
                return

            report_type = self.report_type
            dates = self._calculate_period_dates()
            start_date, end_date = dates[0], dates[1]
            country_code, timezone = self._company_time_context()
            generated_at = self._display_now()
            start_str = self._to_company_datetime(start_date).strftime("%Y%m%d")
            end_str = self._to_company_datetime(end_date).strftime("%Y%m%d")
            now_str = generated_at.strftime("%Y%m%d")

            params = {
                "report_type": report_type,
                "company_id": company_id,
                "branch_id": branch_id,
                "start_date": start_date,
                "end_date": end_date,
                "company_name": self.company_name,
                "include_cancelled": self.include_cancelled,
                "include_zero_stock": self.include_zero_stock,
                "currency_symbol": self.currency_symbol,
                "country_code": country_code,
                "timezone": timezone,
                "generated_at": generated_at,
                "start_str": start_str,
                "end_str": end_str,
                "now_str": now_str,
            }

        # ── Paso 2: trabajo síncrono sin lock — DB queries + Excel ──────────
        try:
            output_bytes, filename = await asyncio.to_thread(_run_report_sync, params)
        except _ReportTooLargeError as e:
            msg = e.args[0] if e.args else "El rango de datos es demasiado grande."
            async with self:
                self.report_loading = False
                self.report_error = msg
            return
        except Exception as e:
            detail = str(e) or type(e).__name__
            logger.exception("Error al generar reporte: %s", detail)
            async with self:
                self.report_loading = False
                self.report_error = f"Error al generar el reporte: {detail}"
            return

        # ── Paso 3: lock corto — guardar resultado ───────────────────────────
        async with self:
            self._report_download_data = output_bytes
            self._report_download_filename = filename
            self.report_ready = True
            self.report_loading = False

    @rx.event
    def download_report(self):
        if not self.report_ready or not self._report_download_data:
            return rx.toast.error(
                "No hay reporte disponible para descargar.", duration=3000
            )
        data = self._report_download_data
        filename = self._report_download_filename or "reporte.xlsx"
        self.report_ready = False
        self._report_download_data = b""
        self._report_download_filename = ""
        return rx.download(data=data, filename=filename)
