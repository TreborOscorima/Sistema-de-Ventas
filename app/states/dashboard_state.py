"""
Estado del Dashboard con métricas y KPIs del sistema.

Proporciona:
- Resumen de ventas (diarias, semanales, mensuales)
- KPIs principales
- Datos para gráficos
- Alertas del sistema
"""
from datetime import datetime, timedelta
from decimal import Decimal

import reflex as rx
from sqlmodel import select, func
from sqlalchemy import and_, or_, extract

from app.models import (
    Sale,
    SaleItem,
    Product,
    Client,
    SaleInstallment,
    CashboxLog,
    FieldReservation,
)
from .inventory_state import LOW_STOCK_THRESHOLD
from app.enums import SaleStatus, ReservationStatus
from app.services.alert_service import get_alert_summary
from app.utils.timezone import country_now
from .mixin_state import MixinState


class DashboardState(MixinState):
    """Estado para el dashboard de métricas."""

    # Filtro de período
    selected_period: str = "month"  # today, week, month, custom
    custom_start_date: str = ""
    custom_end_date: str = ""

    # Datos de resumen (período seleccionado)
    period_sales: float = 0.0
    period_sales_count: int = 0
    period_reservations_count: int = 0
    period_prev_sales: float = 0.0  # Período anterior para comparación

    # Datos de resumen
    today_sales: float = 0.0
    today_sales_count: int = 0
    week_sales: float = 0.0
    week_sales_count: int = 0
    month_sales: float = 0.0
    month_sales_count: int = 0

    # KPIs
    avg_ticket: float = 0.0
    total_clients: int = 0
    active_credits: int = 0
    pending_debt: float = 0.0
    low_stock_count: int = 0

    # Alertas
    alerts: list[dict] = []
    alert_count: int = 0

    # Datos para gráficos
    dash_sales_by_day: list[dict] = []       # Últimos 7 días
    dash_sales_by_category: list[dict] = []  # Por categoría
    dash_top_products: list[dict] = []       # Top 5 productos
    dash_payment_breakdown: list[dict] = []

    # Estado de carga
    dashboard_loading: bool = False
    last_refresh: str = ""

    def set_loading(self, loading: bool):
        """Establece el estado de carga."""
        self.dashboard_loading = loading

    def _load_dashboard_data(self) -> None:
        """Carga todos los datos del dashboard sin manejar UI state."""
        self._load_sales_summary()
        self._load_kpis()
        self._load_alerts()
        self._load_sales_by_day()
        self._load_top_products()
        self._load_sales_by_category()
        self._load_payment_breakdown()
        self.last_refresh = datetime.now().strftime("%H:%M:%S")

    def _tz_now(self) -> datetime:
        """Devuelve datetime.now() en la zona horaria de la empresa.

        Usa la configuración de país/timezone del tenant.
        Si no hay config disponible, cae a datetime.now() (hora local del server).
        """
        settings = {}
        if hasattr(self, "_company_settings_snapshot"):
            settings = self._company_settings_snapshot()
        country_code = settings.get("country_code") or getattr(
            self, "selected_country_code", None
        )
        timezone = settings.get("timezone")
        now = country_now(country_code, timezone=timezone)
        # Stripea tzinfo para comparar naive con naive (DB almacena naive)
        return now.replace(tzinfo=None)

    def _get_period_dates(self) -> tuple[datetime, datetime, datetime, datetime]:
        """Obtiene fechas de inicio y fin del período seleccionado y período anterior."""
        now = self._tz_now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if self.selected_period == "today":
            start = today_start
            end = now
            prev_start = today_start - timedelta(days=1)
            prev_end = today_start
        elif self.selected_period == "week":
            start = today_start - timedelta(days=today_start.weekday())
            end = now
            prev_start = start - timedelta(days=7)
            prev_end = start
        elif self.selected_period == "custom" and self.custom_start_date and self.custom_end_date:
            start = datetime.strptime(self.custom_start_date, "%Y-%m-%d")
            end = datetime.strptime(self.custom_end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            delta = end - start
            prev_start = start - delta - timedelta(days=1)
            prev_end = start - timedelta(days=1)
        else:  # mes (por defecto)
            start = today_start.replace(day=1)
            end = now
            prev_month = start - timedelta(days=1)
            prev_start = prev_month.replace(day=1)
            prev_end = start

        return start, end, prev_start, prev_end

    def _get_reservation_period_end(self, today_start: datetime) -> datetime:
        """Devuelve fin de día actual (23:59:59) para contar reservas.

        Las reservas se agendan a futuro, así que una reserva hoy a las 20:00
        debe contarse incluso si ahora son las 15:00.  Para el período custom
        se respeta el end seleccionado por el usuario.
        """
        if self.selected_period == "custom" and self.custom_end_date:
            return datetime.strptime(self.custom_end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
        return today_start.replace(hour=23, minute=59, second=59)

    @rx.event
    def set_period(self, period: str):
        """Cambia el período seleccionado y recarga datos."""
        self.selected_period = period
        self.load_dashboard()

    @rx.event
    def set_custom_dates(self, start: str, end: str):
        """Establece fechas personalizadas."""
        self.custom_start_date = start
        self.custom_end_date = end
        self.selected_period = "custom"
        self.load_dashboard()

    @rx.event
    def load_dashboard(self):
        """Carga todos los datos del dashboard."""
        self.dashboard_loading = True

        try:
            self._load_dashboard_data()
        except Exception as e:
            print(f"Error loading dashboard: {e}")
        finally:
            self.dashboard_loading = False

    @rx.event(background=True)
    async def load_dashboard_background(self):
        """Carga el dashboard en segundo plano para mejorar la navegación."""
        async with self:
            self.dashboard_loading = True
            try:
                self._load_dashboard_data()
            except Exception as e:
                print(f"Error loading dashboard: {e}")
            finally:
                self.dashboard_loading = False

    def _load_sales_summary(self):
        """Carga resumen de ventas por período."""
        now = self._tz_now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.today_sales = 0.0
            self.today_sales_count = 0
            self.week_sales = 0.0
            self.week_sales_count = 0
            self.month_sales = 0.0
            self.month_sales_count = 0
            self.period_sales = 0.0
            self.period_sales_count = 0
            self.period_reservations_count = 0
            self.period_prev_sales = 0.0
            self.avg_ticket = 0.0
            return

        with rx.session() as session:
            # Ventas de hoy
            today_result = session.exec(
                select(
                    func.count(Sale.id),
                    func.coalesce(func.sum(Sale.total_amount), 0)
                )
                .where(
                    and_(
                        Sale.timestamp >= today_start,
                        Sale.status != SaleStatus.cancelled,
                        Sale.company_id == company_id,
                        Sale.branch_id == branch_id,
                    )
                )
            ).one()
            self.today_sales_count = today_result[0] or 0
            self.today_sales = float(today_result[1] or 0)

            # Ventas de la semana
            week_result = session.exec(
                select(
                    func.count(Sale.id),
                    func.coalesce(func.sum(Sale.total_amount), 0)
                )
                .where(
                    and_(
                        Sale.timestamp >= week_start,
                        Sale.status != SaleStatus.cancelled,
                        Sale.company_id == company_id,
                        Sale.branch_id == branch_id,
                    )
                )
            ).one()
            self.week_sales_count = week_result[0] or 0
            self.week_sales = float(week_result[1] or 0)

            # Ventas del mes
            month_result = session.exec(
                select(
                    func.count(Sale.id),
                    func.coalesce(func.sum(Sale.total_amount), 0)
                )
                .where(
                    and_(
                        Sale.timestamp >= month_start,
                        Sale.status != SaleStatus.cancelled,
                        Sale.company_id == company_id,
                        Sale.branch_id == branch_id,
                    )
                )
            ).one()
            self.month_sales_count = month_result[0] or 0
            self.month_sales = float(month_result[1] or 0)

            # Ventas del período seleccionado y período anterior
            period_start, period_end, prev_start, prev_end = self._get_period_dates()

            period_result = session.exec(
                select(
                    func.count(Sale.id),
                    func.coalesce(func.sum(Sale.total_amount), 0)
                )
                .where(
                    and_(
                        Sale.timestamp >= period_start,
                        Sale.timestamp <= period_end,
                        Sale.status != SaleStatus.cancelled,
                        Sale.company_id == company_id,
                        Sale.branch_id == branch_id,
                    )
                )
            ).one()
            self.period_sales_count = period_result[0] or 0
            self.period_sales = float(period_result[1] or 0)

            # Reservas del período seleccionado (agenda operativa).
            # Se usa end-of-day para incluir reservas futuras del día actual,
            # ya que start_datetime es la hora agendada (no la hora de creación).
            # Excluye estados cancelled y refunded.
            reservation_end = self._get_reservation_period_end(
                now.replace(hour=0, minute=0, second=0, microsecond=0)
            )
            reservation_result = session.exec(
                select(func.count(FieldReservation.id))
                .where(
                    and_(
                        FieldReservation.start_datetime >= period_start,
                        FieldReservation.start_datetime <= reservation_end,
                        FieldReservation.status.notin_(
                            [ReservationStatus.CANCELLED, ReservationStatus.REFUNDED]
                        ),
                        FieldReservation.company_id == company_id,
                        FieldReservation.branch_id == branch_id,
                    )
                )
            ).one()
            self.period_reservations_count = int(reservation_result or 0)

            # Ticket promedio del período seleccionado
            if self.period_sales_count > 0:
                self.avg_ticket = self.period_sales / self.period_sales_count
            else:
                self.avg_ticket = 0.0

            # Período anterior para comparación
            prev_result = session.exec(
                select(func.coalesce(func.sum(Sale.total_amount), 0))
                .where(
                    and_(
                        Sale.timestamp >= prev_start,
                        Sale.timestamp < prev_end,
                        Sale.status != SaleStatus.cancelled,
                        Sale.company_id == company_id,
                        Sale.branch_id == branch_id,
                    )
                )
            ).one()
            self.period_prev_sales = float(prev_result or 0)

    def _load_kpis(self):
        """Carga KPIs principales."""
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.total_clients = 0
            self.active_credits = 0
            self.pending_debt = 0.0
            self.low_stock_count = 0
            return
        with rx.session() as session:
            # Total de clientes
            self.total_clients = session.exec(
                select(func.count())
                .select_from(Client)
                .where(Client.company_id == company_id)
                .where(Client.branch_id == branch_id)
            ).one() or 0

            # Créditos activos (ventas a crédito con cuotas pendientes)
            self.active_credits = session.exec(
                select(func.count(func.distinct(Sale.id)))
                .select_from(Sale)
                .join(SaleInstallment)
                .where(
                    and_(
                        Sale.status != SaleStatus.cancelled,
                        SaleInstallment.status == "pending",
                        Sale.company_id == company_id,
                        Sale.branch_id == branch_id,
                    )
                )
            ).one() or 0

            # Deuda pendiente total
            pending = session.exec(
                select(func.sum(SaleInstallment.amount - SaleInstallment.paid_amount))
                .select_from(SaleInstallment)
                .join(Sale)
                .where(
                    and_(
                        SaleInstallment.status == "pending",
                        Sale.company_id == company_id,
                        Sale.branch_id == branch_id,
                    )
                )
            ).one()
            self.pending_debt = float(pending or 0)

            # Productos con stock bajo (alineado con Inventario)
            self.low_stock_count = session.exec(
                select(func.count())
                .select_from(Product)
                .where(
                    and_(
                        Product.company_id == company_id,
                        Product.branch_id == branch_id,
                        Product.stock > 0,
                        Product.stock <= LOW_STOCK_THRESHOLD,
                    )
                )
            ).one() or 0

    def _load_alerts(self):
        """Carga alertas del sistema."""
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.alerts = []
            self.alert_count = 0
            return
        settings = {}
        if hasattr(self, "_company_settings_snapshot"):
            settings = self._company_settings_snapshot()
        country_code = settings.get("country_code") or getattr(
            self, "selected_country_code", None
        )
        timezone = settings.get("timezone")
        summary = get_alert_summary(
            self.currency_symbol,
            company_id=company_id,
            branch_id=branch_id,
            country_code=country_code,
            timezone=timezone,
        )
        self.alerts = summary.get("alerts", [])
        self.alert_count = summary.get("total", 0)

    def _load_sales_by_day(self):
        """Carga ventas de los últimos 7 días para gráfico."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.dash_sales_by_day = []
            return

        days_data = []
        day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        start_date = today - timedelta(days=6)
        end_date = today + timedelta(days=1)

        with rx.session() as session:
            results = session.exec(
                select(
                    func.date(Sale.timestamp).label("day"),
                    func.coalesce(func.sum(Sale.total_amount), 0).label("total"),
                )
                .where(
                    and_(
                        Sale.timestamp >= start_date,
                        Sale.timestamp < end_date,
                        Sale.status != SaleStatus.cancelled,
                        Sale.company_id == company_id,
                        Sale.branch_id == branch_id,
                    )
                )
                .group_by(func.date(Sale.timestamp))
            ).all()

            totals_by_day = {}
            for row in results:
                day_value = row[0]
                if isinstance(day_value, str):
                    try:
                        day_value = datetime.strptime(day_value, "%Y-%m-%d").date()
                    except ValueError:
                        continue
                if hasattr(day_value, "date"):
                    day_value = day_value.date()
                totals_by_day[day_value] = float(row[1] or 0)

            for i in range(6, -1, -1):
                day_start = today - timedelta(days=i)
                day_key = day_start.date()
                days_data.append({
                    "day": day_names[day_start.weekday()],
                    "date": day_start.strftime("%d/%m"),
                    "total": float(totals_by_day.get(day_key, 0)),
                })

        self.dash_sales_by_day = days_data

    def _load_top_products(self):
        """Carga los 5 productos más vendidos del período seleccionado."""
        period_start, period_end, _, _ = self._get_period_dates()
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.dash_top_products = []
            return

        with rx.session() as session:
            results = session.exec(
                select(
                    Product.description,
                    func.sum(SaleItem.quantity).label("qty"),
                    func.sum(SaleItem.subtotal).label("revenue")
                )
                .select_from(SaleItem)
                .join(Product)
                .join(Sale)
                .where(
                    and_(
                        Sale.timestamp >= period_start,
                        Sale.timestamp <= period_end,
                        Sale.status != SaleStatus.cancelled,
                        Sale.company_id == company_id,
                        Sale.branch_id == branch_id,
                        Product.company_id == company_id,
                        Product.branch_id == branch_id,
                    )
                )
                .group_by(Product.id, Product.description)
                .order_by(func.sum(SaleItem.quantity).desc())
                .limit(10)
            ).all()

            self.dash_top_products = [
                {
                    "name": r[0][:25] + "..." if len(r[0]) > 25 else r[0],
                    "quantity": int(r[1] or 0),
                    "revenue": float(r[2] or 0),
                }
                for r in results
            ]

    def _load_sales_by_category(self):
        """Carga ventas por categoría del período seleccionado."""
        self.dash_sales_by_category = self._query_sales_by_category(limit=10)

    def _query_sales_by_category(self, limit: int | None = None) -> list[dict]:
        """Obtiene ventas agrupadas por categoría para el período seleccionado."""
        period_start, period_end, _, _ = self._get_period_dates()
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return []

        with rx.session() as session:
            category_expr = func.coalesce(
                func.nullif(func.trim(SaleItem.product_category_snapshot), ""),
                Product.category,
                "Sin categoría",
            )
            query = (
                select(
                    category_expr,
                    func.sum(SaleItem.subtotal).label("total"),
                )
                .select_from(SaleItem)
                .outerjoin(Product, Product.id == SaleItem.product_id)
                .join(Sale, Sale.id == SaleItem.sale_id)
                .where(
                    and_(
                        Sale.timestamp >= period_start,
                        Sale.timestamp <= period_end,
                        Sale.status != SaleStatus.cancelled,
                        Sale.company_id == company_id,
                        Sale.branch_id == branch_id,
                        SaleItem.company_id == company_id,
                        SaleItem.branch_id == branch_id,
                    )
                )
                .group_by(category_expr)
                .order_by(func.sum(SaleItem.subtotal).desc())
            )
            if limit is not None and int(limit) > 0:
                query = query.limit(int(limit))
            rows = session.exec(query).all()

        total_sales = sum(float(row[1] or 0) for row in rows)
        return [
            {
                "category": row[0] or "Sin categoría",
                "total": float(row[1] or 0),
                "percentage": (
                    round((float(row[1] or 0) / total_sales * 100), 1)
                    if total_sales > 0
                    else 0
                ),
            }
            for row in rows
        ]

    def _load_payment_breakdown(self):
        """Carga desglose de métodos de pago del período seleccionado."""
        period_start, period_end, _, _ = self._get_period_dates()
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.dash_payment_breakdown = []
            return

        with rx.session() as session:
            results = session.exec(
                select(
                    CashboxLog.action,
                    func.sum(CashboxLog.amount).label("total")
                )
                .where(
                    and_(
                        CashboxLog.timestamp >= period_start,
                        CashboxLog.timestamp <= period_end,
                        CashboxLog.is_voided == False,
                        CashboxLog.action.in_(["Venta", "Cobranza", "Cobro Cuota", "Reserva", "Adelanto"]),
                        CashboxLog.company_id == company_id,
                        CashboxLog.branch_id == branch_id,
                    )
                )
                .group_by(CashboxLog.action)
            ).all()

            self.dash_payment_breakdown = [
                {
                    "method": r[0],
                    "total": float(r[1] or 0),
                }
                for r in results
            ]

    @rx.var(cache=True)
    def has_critical_alerts(self) -> bool:
        """Indica si hay alertas críticas."""
        return any(a.get("severity") in ("critical", "error") for a in self.alerts)

    @rx.var(cache=True)
    def period_label(self) -> str:
        """Etiqueta del período seleccionado."""
        labels = {
            "today": "Hoy",
            "week": "Esta Semana",
            "month": "Este Mes",
            "custom": "Personalizado",
        }
        return labels.get(self.selected_period, "Este Mes")

    @rx.var(cache=True)
    def sales_change_percent(self) -> float:
        """Porcentaje de cambio vs período anterior."""
        if self.period_prev_sales > 0:
            return ((self.period_sales - self.period_prev_sales) / self.period_prev_sales) * 100
        return 0.0

    @rx.var(cache=True)
    def sales_trend_up(self) -> bool:
        """Indica si las ventas van en aumento."""
        return self.period_sales >= self.period_prev_sales

    @rx.var(cache=True)
    def formatted_sales_change(self) -> str:
        """Cambio formateado con signo."""
        change = self.sales_change_percent
        if change >= 0:
            return f"+{change:.1f}%"
        return f"{change:.1f}%"

    @rx.var(cache=True)
    def formatted_today_sales(self) -> str:
        return f"{self.currency_symbol}{self.today_sales:,.2f}"

    @rx.var(cache=True)
    def formatted_week_sales(self) -> str:
        return f"{self.currency_symbol}{self.week_sales:,.2f}"

    @rx.var(cache=True)
    def formatted_month_sales(self) -> str:
        return f"{self.currency_symbol}{self.month_sales:,.2f}"

    @rx.var(cache=True)
    def formatted_avg_ticket(self) -> str:
        return f"{self.currency_symbol}{self.avg_ticket:,.2f}"

    @rx.var(cache=True)
    def formatted_pending_debt(self) -> str:
        return f"{self.currency_symbol}{self.pending_debt:,.2f}"

    @rx.var(cache=True)
    def formatted_period_sales(self) -> str:
        return f"{self.currency_symbol}{self.period_sales:,.2f}"

    @rx.var(cache=True)
    def category_total_sales(self) -> float:
        """Total de ventas de todas las categorías."""
        return sum(c.get("total", 0) for c in self.dash_sales_by_category)

    @rx.var(cache=True)
    def formatted_category_total(self) -> str:
        return f"{self.currency_symbol}{self.category_total_sales:,.2f}"

    @rx.event
    def export_categories_excel(self):
        """Exporta ventas por categoría a Excel con formato profesional."""
        import io
        import os
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
        from openpyxl.chart import PieChart, Reference

        wb = Workbook()
        ws = wb.active
        ws.title = "Ventas por Categoría"
        export_categories = self._query_sales_by_category(limit=None)

        # Estilos
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        total_font = Font(bold=True, size=11)
        total_fill = PatternFill(start_color="E5E7EB", end_color="E5E7EB", fill_type="solid")
        currency_symbol = (self.currency_symbol or "$").strip()
        currency_format = f'"{currency_symbol}"#,##0.00'
        percent_format = '0.0%'
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # Título del reporte
        ws.merge_cells('A1:D1')
        ws['A1'] = f"Reporte de Ventas por Categoría - {self.period_label}"
        ws['A1'].font = Font(bold=True, size=14)
        ws['A1'].alignment = Alignment(horizontal='center')

        ws.merge_cells('A2:D2')
        ws['A2'] = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        ws['A2'].alignment = Alignment(horizontal='center')
        ws['A2'].font = Font(italic=True, color="666666")

        # Encabezados (fila 4)
        headers = ["#", "Categoría", "Total Ventas", "Participación"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border

        # Datos
        total = sum(cat.get("total", 0) for cat in export_categories)
        for idx, cat in enumerate(export_categories, 1):
            row = idx + 4
            pct = cat["total"] / total if total > 0 else 0

            ws.cell(row=row, column=1, value=idx).border = thin_border
            ws.cell(row=row, column=2, value=cat["category"]).border = thin_border

            cell_total = ws.cell(row=row, column=3, value=cat["total"])
            cell_total.number_format = currency_format
            cell_total.border = thin_border
            cell_total.alignment = Alignment(horizontal='right')

            cell_pct = ws.cell(row=row, column=4, value=pct)
            cell_pct.number_format = percent_format
            cell_pct.border = thin_border
            cell_pct.alignment = Alignment(horizontal='right')

        # Fila de total
        total_row = len(export_categories) + 5
        ws.cell(row=total_row, column=1, value="").border = thin_border
        ws.cell(row=total_row, column=2, value="TOTAL").font = total_font
        ws.cell(row=total_row, column=2).fill = total_fill
        ws.cell(row=total_row, column=2).border = thin_border

        cell_grand_total = ws.cell(row=total_row, column=3, value=total)
        cell_grand_total.number_format = currency_format
        cell_grand_total.font = total_font
        cell_grand_total.fill = total_fill
        cell_grand_total.border = thin_border
        cell_grand_total.alignment = Alignment(horizontal='right')

        cell_100 = ws.cell(row=total_row, column=4, value=1)
        cell_100.number_format = percent_format
        cell_100.font = total_font
        cell_100.fill = total_fill
        cell_100.border = thin_border
        cell_100.alignment = Alignment(horizontal='right')

        # Ajustar anchos de columna
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 18
        ws.column_dimensions['D'].width = 15

        # Agregar gráfico de torta
        if len(export_categories) > 0:
            chart = PieChart()
            chart.title = "Distribución de Ventas"

            data = Reference(ws, min_col=3, min_row=4, max_row=total_row-1)
            labels = Reference(ws, min_col=2, min_row=5, max_row=total_row-1)

            chart.add_data(data, titles_from_data=True)
            chart.set_categories(labels)
            chart.width = 12
            chart.height = 8

            ws.add_chart(chart, "F4")

        # Guardar a bytes y codificar en base64
        import io
        import base64

        output = io.BytesIO()
        wb.save(output)
        excel_bytes = output.getvalue()
        output.close()

        # Crear data URL para descarga directa
        b64_data = base64.b64encode(excel_bytes).decode('utf-8')
        filename = f"ventas_categoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        # Usar JavaScript para descargar el archivo
        js_code = f"""
        (function() {{
            var byteCharacters = atob('{b64_data}');
            var byteNumbers = new Array(byteCharacters.length);
            for (var i = 0; i < byteCharacters.length; i++) {{
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }}
            var byteArray = new Uint8Array(byteNumbers);
            var blob = new Blob([byteArray], {{type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}});
            var link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = '{filename}';
            link.click();
        }})();
        """

        return rx.call_script(js_code)
