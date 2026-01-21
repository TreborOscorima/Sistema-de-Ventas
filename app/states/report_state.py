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

from app.services.report_service import (
    generate_sales_report,
    generate_inventory_report,
    generate_receivables_report,
    generate_cashbox_report,
)
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
            # Default: este mes
            start = today_start.replace(day=1)
            return (start, today_end)
    
    @rx.event
    def generate_report(self):
        """Genera el reporte seleccionado."""
        if not self.current_user["privileges"].get("export_data"):
            return rx.toast.error("No tiene permisos para exportar reportes.", duration=3000)
        
        self.report_loading = True
        self.report_error = ""
        
        try:
            # Calcular fechas directamente
            dates = self._calculate_period_dates()
            start_date = dates[0]
            end_date = dates[1]
            
            with rx.session() as session:
                if self.report_type == "ventas":
                    output = generate_sales_report(
                        session,
                        start_date,
                        end_date,
                        company_name=self.company_name,
                        include_cancelled=self.include_cancelled,
                    )
                    filename = f"Reporte_Ventas_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
                
                elif self.report_type == "inventario":
                    output = generate_inventory_report(
                        session,
                        company_name=self.company_name,
                        include_zero_stock=self.include_zero_stock,
                    )
                    filename = f"Inventario_Valorizado_{datetime.now().strftime('%Y%m%d')}.xlsx"
                
                elif self.report_type == "cuentas":
                    output = generate_receivables_report(
                        session,
                        company_name=self.company_name,
                    )
                    filename = f"Cuentas_por_Cobrar_{datetime.now().strftime('%Y%m%d')}.xlsx"
                
                elif self.report_type == "caja":
                    output = generate_cashbox_report(
                        session,
                        start_date,
                        end_date,
                        company_name=self.company_name,
                    )
                    filename = f"Reporte_Caja_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
                
                else:
                    self.report_loading = False
                    return rx.toast.error("Tipo de reporte no válido.", duration=3000)
            
            self.report_loading = False
            return rx.download(data=output.getvalue(), filename=filename)
        
        except Exception as e:
            self.report_loading = False
            self.report_error = str(e)
            logger.error(f"Error al generar reporte: {e}")
            logger.error(traceback.format_exc())
            return rx.toast.error(f"Error al generar reporte: {str(e)[:100]}", duration=5000)
