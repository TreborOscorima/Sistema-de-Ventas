"""
Estado para la gestión de reportes contables y financieros.

Proporciona funcionalidades para generar reportes profesionales
para evaluaciones administrativas, contables y financieras.
"""
import logging
import traceback
from datetime import datetime, timedelta
from typing import Any

import reflex as rx
from sqlmodel import select, func
from sqlalchemy import exists

from app.constants import MAX_REPORT_ROWS
from app.enums import SaleStatus
from app.models import Sale, CashboxLog, SaleInstallment, Product, ProductVariant
from app.services.report_service import (
    generate_sales_report,
    generate_inventory_report,
    generate_receivables_report,
    generate_cashbox_report,
)
from app.utils.tenant import set_tenant_context
from .mixin_state import MixinState

logger = logging.getLogger(__name__)


class ReportState(MixinState):
    """Estado para generación de reportes."""
    
    # Configuración del reporte
    report_type: str = "ventas"  # ventas, inventario, cuentas, caja
    report_period: str = "month"  # today, week, month, quarter, year, custom
    custom_start_date: str = ""
    custom_end_date: str = ""
    
    # Estado de generación
    report_loading: bool = False
    report_error: str = ""
    report_ready: bool = False
    report_download_data: bytes = b""
    report_download_filename: str = ""
    
    # Opciones de reporte
    include_cancelled: bool = False
    include_zero_stock: bool = True
    
    # Nombre de empresa (configurable)
    company_name: str = "TUWAYKIAPP"
    
    @rx.var
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
    
    @rx.var
    def report_types(self) -> list[dict[str, str]]:
        """Tipos de reportes disponibles."""
        return [
            {"value": "ventas", "label": "Reporte de Ventas Consolidado", "icon": "shopping-cart"},
            {"value": "inventario", "label": "Inventario Valorizado", "icon": "package"},
            {"value": "cuentas", "label": "Cuentas por Cobrar", "icon": "credit-card"},
            {"value": "caja", "label": "Gestión de Caja", "icon": "banknote"},
        ]
    
    @rx.var
    def selected_report_label(self) -> str:
        """Etiqueta del reporte seleccionado."""
        for rt in self.report_types:
            if rt["value"] == self.report_type:
                return rt["label"]
        return "Reporte"
    
    @rx.var
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

    @rx.var
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
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        period = self.report_period
        
        if period == "today":
            return (today_start, today_end)
        elif period == "week":
            start = today_start - timedelta(days=today_start.weekday())
            return (start, today_end)
        elif period == "month":
            start = today_start.replace(day=1)
            return (start, today_end)
        elif period == "quarter":
            quarter = (now.month - 1) // 3
            start_month = quarter * 3 + 1
            start = today_start.replace(month=start_month, day=1)
            return (start, today_end)
        elif period == "year":
            start = today_start.replace(month=1, day=1)
            return (start, today_end)
        elif period == "custom":
            try:
                start = datetime.strptime(self.custom_start_date, "%Y-%m-%d")
                end = datetime.strptime(self.custom_end_date, "%Y-%m-%d")
                end = end.replace(hour=23, minute=59, second=59)
                return (start, end)
            except (ValueError, TypeError):
                start = today_start.replace(day=1)
                return (start, today_end)
        else:
            # Por defecto: este mes
            start = today_start.replace(day=1)
            return (start, today_end)
    
    @rx.event(background=True)
    async def generate_report(self):
        """Genera el reporte seleccionado."""
        async with self:
            if not self.current_user["privileges"].get("export_data"):
                self.report_error = "No tiene permisos para exportar reportes."
                return

            self.report_loading = True
            self.report_error = ""
            self.report_ready = False
            self.report_download_data = b""
            self.report_download_filename = ""

            try:
                company_id = self._company_id()
                branch_id = self._branch_id()
                if not company_id or not branch_id:
                    self.report_loading = False
                    self.report_error = "Empresa o sucursal no definida."
                    return
                set_tenant_context(company_id, branch_id)
                # Calcular fechas directamente
                dates = self._calculate_period_dates()
                start_date = dates[0]
                end_date = dates[1]

                with rx.session() as session:
                    if MAX_REPORT_ROWS > 0:
                        if self.report_type == "ventas":
                            count_query = (
                                select(func.count(Sale.id))
                                .where(Sale.timestamp >= start_date)
                                .where(Sale.timestamp <= end_date)
                                .where(Sale.company_id == company_id)
                                .where(Sale.branch_id == branch_id)
                            )
                            if not self.include_cancelled:
                                count_query = count_query.where(
                                    Sale.status != SaleStatus.cancelled
                                )
                            total_sales = session.exec(count_query).one()
                            if isinstance(total_sales, tuple):
                                total_sales = total_sales[0]
                            if int(total_sales or 0) > MAX_REPORT_ROWS:
                                self.report_loading = False
                                self.report_error = "Rango demasiado grande."
                                return

                        elif self.report_type == "inventario":
                            products_without_variants = session.exec(
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
                            if isinstance(products_without_variants, tuple):
                                products_without_variants = products_without_variants[0]
                            variant_count = session.exec(
                                select(func.count(ProductVariant.id))
                                .where(ProductVariant.company_id == company_id)
                                .where(ProductVariant.branch_id == branch_id)
                            ).one()
                            if isinstance(variant_count, tuple):
                                variant_count = variant_count[0]
                            estimated_rows = int(products_without_variants or 0) + int(
                                variant_count or 0
                            )
                            if estimated_rows > MAX_REPORT_ROWS:
                                self.report_loading = False
                                self.report_error = "Inventario demasiado grande."
                                return

                        elif self.report_type == "cuentas":
                            count_query = (
                                select(func.count(SaleInstallment.id))
                                .where(SaleInstallment.status != "paid")
                                .where(SaleInstallment.company_id == company_id)
                                .where(SaleInstallment.branch_id == branch_id)
                            )
                            total_installments = session.exec(count_query).one()
                            if isinstance(total_installments, tuple):
                                total_installments = total_installments[0]
                            if int(total_installments or 0) > MAX_REPORT_ROWS:
                                self.report_loading = False
                                self.report_error = "Cuentas por cobrar demasiado grandes."
                                return

                        elif self.report_type == "caja":
                            count_query = (
                                select(func.count(CashboxLog.id))
                                .where(CashboxLog.timestamp >= start_date)
                                .where(CashboxLog.timestamp <= end_date)
                                .where(CashboxLog.company_id == company_id)
                                .where(CashboxLog.branch_id == branch_id)
                            )
                            total_logs = session.exec(count_query).one()
                            if isinstance(total_logs, tuple):
                                total_logs = total_logs[0]
                            if int(total_logs or 0) > MAX_REPORT_ROWS:
                                self.report_loading = False
                                self.report_error = "Reporte de caja demasiado grande."
                                return

                    if self.report_type == "ventas":
                        output = generate_sales_report(
                            session,
                            start_date,
                            end_date,
                            company_name=self.company_name,
                            include_cancelled=self.include_cancelled,
                            currency_symbol=self.currency_symbol,
                            company_id=company_id,
                            branch_id=branch_id,
                        )
                        filename = f"Reporte_Ventas_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

                    elif self.report_type == "inventario":
                        output = generate_inventory_report(
                            session,
                            company_name=self.company_name,
                            include_zero_stock=self.include_zero_stock,
                            currency_symbol=self.currency_symbol,
                            company_id=company_id,
                            branch_id=branch_id,
                        )
                        filename = f"Inventario_Valorizado_{datetime.now().strftime('%Y%m%d')}.xlsx"

                    elif self.report_type == "cuentas":
                        output = generate_receivables_report(
                            session,
                            company_name=self.company_name,
                            currency_symbol=self.currency_symbol,
                            company_id=company_id,
                            branch_id=branch_id,
                        )
                        filename = f"Cuentas_por_Cobrar_{datetime.now().strftime('%Y%m%d')}.xlsx"

                    elif self.report_type == "caja":
                        output = generate_cashbox_report(
                            session,
                            start_date,
                            end_date,
                            company_name=self.company_name,
                            currency_symbol=self.currency_symbol,
                            company_id=company_id,
                            branch_id=branch_id,
                        )
                        filename = f"Reporte_Caja_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

                    else:
                        self.report_loading = False
                        self.report_error = "Tipo de reporte no válido."
                        return

                self.report_download_data = output.getvalue()
                self.report_download_filename = filename
                self.report_ready = True
            except Exception as e:
                self.report_error = str(e)
                logger.error(f"Error al generar reporte: {e}")
                logger.error(traceback.format_exc())
            finally:
                self.report_loading = False

    @rx.event
    def download_report(self):
        if not self.report_ready or not self.report_download_data:
            return rx.toast.error(
                "No hay reporte disponible para descargar.", duration=3000
            )
        data = self.report_download_data
        filename = self.report_download_filename or "reporte.xlsx"
        self.report_ready = False
        self.report_download_data = b""
        self.report_download_filename = ""
        return rx.download(data=data, filename=filename)
