"""
Servicio de alertas del sistema.

Proporciona funcionalidades para detectar y notificar:
- Stock bajo de productos
- Cuotas de crédito vencidas
- Sesiones de caja abiertas por mucho tiempo
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from app.utils.timezone import country_today_start

import reflex as rx
from sqlmodel import select, func
from sqlalchemy import and_, or_

from app.models import Product, SaleInstallment, Sale, CashboxSession
from app.enums import SaleStatus
from app.utils.formatting import format_currency


class AlertType(str, Enum):
    """Tipos de alerta del sistema."""
    STOCK_LOW = "stock_low"
    STOCK_CRITICAL = "stock_critical"
    INSTALLMENT_DUE = "installment_due"
    INSTALLMENT_OVERDUE = "installment_overdue"
    CASHBOX_OPEN_LONG = "cashbox_open_long"


class AlertSeverity(str, Enum):
    """Severidad de la alerta."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Representa una alerta del sistema."""
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    count: int = 1
    details: Optional[dict] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "count": self.count,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Configuración de umbrales (pueden moverse a constants.py o BD)
STOCK_LOW_THRESHOLD = 10       # Unidades para alerta amarilla
STOCK_CRITICAL_THRESHOLD = 3  # Unidades para alerta roja
INSTALLMENT_DUE_DAYS = 3      # Días antes del vencimiento para alertar
CASHBOX_OPEN_HOURS = 12       # Horas para alertar caja abierta


def get_low_stock_alerts(
    company_id: int | None = None,
    branch_id: int | None = None,
) -> List[Alert]:
    """
    Obtiene alertas de productos con stock bajo.
    
    Returns:
        Lista de alertas de stock
    """
    alerts = []
    
    with rx.session() as session:
        # Productos con stock crítico (< 3)
        critical_query = select(Product).where(
            and_(
                Product.stock <= STOCK_CRITICAL_THRESHOLD,
                Product.stock > 0,
                Product.is_active == True,
            )
        )
        if company_id:
            critical_query = critical_query.where(Product.company_id == company_id)
        if branch_id:
            critical_query = critical_query.where(Product.branch_id == branch_id)
        critical_products = session.exec(critical_query).all()
        
        if critical_products:
            alerts.append(Alert(
                type=AlertType.STOCK_CRITICAL,
                severity=AlertSeverity.CRITICAL,
                title="Stock Crítico",
                message=f"{len(critical_products)} producto(s) con stock crítico (≤{STOCK_CRITICAL_THRESHOLD} unidades)",
                count=len(critical_products),
                details={
                    "products": [
                        {"id": p.id, "name": p.description, "stock": p.stock}
                        for p in critical_products[:5]  # Limitar a 5
                    ]
                }
            ))
        
        # Productos con stock bajo (3-10)
        low_stock_query = select(Product).where(
            and_(
                Product.stock > STOCK_CRITICAL_THRESHOLD,
                Product.stock <= STOCK_LOW_THRESHOLD,
                Product.is_active == True,
            )
        )
        if company_id:
            low_stock_query = low_stock_query.where(Product.company_id == company_id)
        if branch_id:
            low_stock_query = low_stock_query.where(Product.branch_id == branch_id)
        low_stock_products = session.exec(low_stock_query).all()
        
        if low_stock_products:
            alerts.append(Alert(
                type=AlertType.STOCK_LOW,
                severity=AlertSeverity.WARNING,
                title="Stock Bajo",
                message=f"{len(low_stock_products)} producto(s) con stock bajo ({STOCK_CRITICAL_THRESHOLD + 1}-{STOCK_LOW_THRESHOLD} unidades)",
                count=len(low_stock_products),
                details={
                    "products": [
                        {"id": p.id, "name": p.description, "stock": p.stock}
                        for p in low_stock_products[:5]
                    ]
                }
            ))
        
        # Productos sin stock
        out_of_stock_query = (
            select(func.count())
            .select_from(Product)
            .where(
                and_(
                    Product.stock <= 0,
                    Product.is_active == True,
                )
            )
        )
        if company_id:
            out_of_stock_query = out_of_stock_query.where(
                Product.company_id == company_id
            )
        if branch_id:
            out_of_stock_query = out_of_stock_query.where(
                Product.branch_id == branch_id
            )
        out_of_stock = session.exec(out_of_stock_query).one()
        
        if out_of_stock > 0:
            alerts.append(Alert(
                type=AlertType.STOCK_CRITICAL,
                severity=AlertSeverity.ERROR,
                title="Sin Stock",
                message=f"{out_of_stock} producto(s) sin stock disponible",
                count=out_of_stock,
            ))
    
    return alerts


def _format_alert_currency(amount: Decimal, currency_symbol: str | None) -> str:
    symbol = (currency_symbol or "").strip()
    if symbol:
        symbol = f"{symbol} "
    return format_currency(float(amount or 0), symbol or "S/ ")


def get_installment_alerts(
    currency_symbol: str | None = None,
    company_id: int | None = None,
    branch_id: int | None = None,
    country_code: str | None = None,
    timezone: str | None = None,
) -> List[Alert]:
    """
    Obtiene alertas de cuotas próximas a vencer o vencidas.
    
    Returns:
        Lista de alertas de cuotas
    """
    alerts = []
    today = country_today_start(country_code, timezone=timezone)
    due_threshold = today + timedelta(days=INSTALLMENT_DUE_DAYS)
    
    with rx.session() as session:
        # Cuotas vencidas (no pagadas y fecha pasada)
        overdue_query = (
            select(func.count())
            .select_from(SaleInstallment)
            .join(Sale)
            .where(
                and_(
                    func.lower(SaleInstallment.status).not_in(
                        ["paid", "completed"]
                    ),
                    SaleInstallment.due_date < today,
                )
            )
        )
        if company_id:
            overdue_query = overdue_query.where(Sale.company_id == company_id)
        if branch_id:
            overdue_query = overdue_query.where(SaleInstallment.branch_id == branch_id)
        overdue_count = session.exec(overdue_query).one()
        
        if overdue_count > 0:
            # Obtener monto total vencido
            overdue_amount_query = (
                select(func.sum(SaleInstallment.amount - SaleInstallment.paid_amount))
                .select_from(SaleInstallment)
                .join(Sale)
                .where(
                    and_(
                        func.lower(SaleInstallment.status).not_in(
                            ["paid", "completed"]
                        ),
                        SaleInstallment.due_date < today,
                    )
                )
            )
            if company_id:
                overdue_amount_query = overdue_amount_query.where(
                    Sale.company_id == company_id
                )
            if branch_id:
                overdue_amount_query = overdue_amount_query.where(
                    SaleInstallment.branch_id == branch_id
                )
            overdue_amount = session.exec(overdue_amount_query).one() or Decimal("0")
            
            alerts.append(Alert(
                type=AlertType.INSTALLMENT_OVERDUE,
                severity=AlertSeverity.ERROR,
                title="Cuotas Vencidas",
                message=(
                    f"{overdue_count} cuota(s) vencida(s) por "
                    f"{_format_alert_currency(overdue_amount, currency_symbol)}"
                ),
                count=overdue_count,
                details={"total_amount": float(overdue_amount)}
            ))
        
        # Cuotas próximas a vencer (próximos 3 días)
        due_soon_query = (
            select(func.count())
            .select_from(SaleInstallment)
            .join(Sale)
            .where(
                and_(
                    func.lower(SaleInstallment.status).not_in(
                        ["paid", "completed"]
                    ),
                    SaleInstallment.due_date >= today,
                    SaleInstallment.due_date <= due_threshold,
                )
            )
        )
        if company_id:
            due_soon_query = due_soon_query.where(Sale.company_id == company_id)
        if branch_id:
            due_soon_query = due_soon_query.where(SaleInstallment.branch_id == branch_id)
        due_soon_count = session.exec(due_soon_query).one()
        
        if due_soon_count > 0:
            due_soon_amount_query = (
                select(func.sum(SaleInstallment.amount - SaleInstallment.paid_amount))
                .select_from(SaleInstallment)
                .join(Sale)
                .where(
                    and_(
                        func.lower(SaleInstallment.status).not_in(
                            ["paid", "completed"]
                        ),
                        SaleInstallment.due_date >= today,
                        SaleInstallment.due_date <= due_threshold,
                    )
                )
            )
            if company_id:
                due_soon_amount_query = due_soon_amount_query.where(
                    Sale.company_id == company_id
                )
            if branch_id:
                due_soon_amount_query = due_soon_amount_query.where(
                    SaleInstallment.branch_id == branch_id
                )
            due_soon_amount = session.exec(due_soon_amount_query).one() or Decimal("0")
            
            alerts.append(Alert(
                type=AlertType.INSTALLMENT_DUE,
                severity=AlertSeverity.WARNING,
                title="Cuotas por Vencer",
                message=(
                    f"{due_soon_count} cuota(s) vence(n) en los próximos "
                    f"{INSTALLMENT_DUE_DAYS} días "
                    f"({_format_alert_currency(due_soon_amount, currency_symbol)})"
                ),
                count=due_soon_count,
                details={"total_amount": float(due_soon_amount)}
            ))
    
    return alerts


def get_cashbox_alerts(
    company_id: int | None = None,
    branch_id: int | None = None,
) -> List[Alert]:
    """
    Obtiene alertas relacionadas con la caja.
    
    Returns:
        Lista de alertas de caja
    """
    alerts = []
    threshold_time = datetime.now() - timedelta(hours=CASHBOX_OPEN_HOURS)
    
    with rx.session() as session:
        # Sesiones de caja abiertas por mucho tiempo
        long_open_query = select(CashboxSession).where(
            and_(
                CashboxSession.closing_time == None,
                CashboxSession.opening_time < threshold_time,
            )
        )
        if company_id:
            long_open_query = long_open_query.where(
                CashboxSession.company_id == company_id
            )
        if branch_id:
            long_open_query = long_open_query.where(
                CashboxSession.branch_id == branch_id
            )
        long_open_sessions = session.exec(long_open_query).all()
        
        if long_open_sessions:
            alerts.append(Alert(
                type=AlertType.CASHBOX_OPEN_LONG,
                severity=AlertSeverity.WARNING,
                title="Caja Abierta",
                message=f"Caja abierta por más de {CASHBOX_OPEN_HOURS} horas",
                count=len(long_open_sessions),
                details={
                    "sessions": [
                        {
                            "id": s.id,
                            "opened_at": s.opening_time.isoformat(),
                            "hours_open": (datetime.now() - s.opening_time).total_seconds() / 3600
                        }
                        for s in long_open_sessions
                    ]
                }
            ))
    
    return alerts


async def get_overdue_count(
    session,
    company_id: int | None = None,
    branch_id: int | None = None,
    country_code: str | None = None,
    timezone: str | None = None,
) -> int:
    """Cuenta cuotas vencidas (pendientes con fecha pasada) usando sesión async."""
    today = country_today_start(country_code, timezone=timezone)
    overdue_query = (
        select(func.count())
        .select_from(SaleInstallment)
        .join(Sale)
        .where(
            and_(
                func.lower(SaleInstallment.status).not_in(["paid", "completed"]),
                SaleInstallment.due_date < today,
            )
        )
    )
    if company_id:
        overdue_query = overdue_query.where(Sale.company_id == company_id)
    if branch_id:
        overdue_query = overdue_query.where(SaleInstallment.branch_id == branch_id)
    result = await session.exec(overdue_query)
    return int(result.one() or 0)


def get_all_alerts(
    currency_symbol: str | None = None,
    company_id: int | None = None,
    branch_id: int | None = None,
    country_code: str | None = None,
    timezone: str | None = None,
) -> List[Alert]:
    """
    Obtiene todas las alertas del sistema.
    
    Returns:
        Lista de todas las alertas ordenadas por severidad
    """
    alerts = []
    
    try:
        alerts.extend(get_low_stock_alerts(company_id, branch_id))
    except Exception:
        pass  # No interrumpir si falla una categoría
    
    try:
        alerts.extend(
            get_installment_alerts(
                currency_symbol,
                company_id,
                branch_id,
                country_code=country_code,
                timezone=timezone,
            )
        )
    except Exception:
        pass
    
    try:
        alerts.extend(get_cashbox_alerts(company_id, branch_id))
    except Exception:
        pass
    
    # Ordenar por severidad (crítico primero)
    severity_order = {
        AlertSeverity.CRITICAL: 0,
        AlertSeverity.ERROR: 1,
        AlertSeverity.WARNING: 2,
        AlertSeverity.INFO: 3,
    }
    
    alerts.sort(key=lambda a: severity_order.get(a.severity, 99))
    
    return alerts


def get_alert_summary(
    currency_symbol: str | None = None,
    company_id: int | None = None,
    branch_id: int | None = None,
    country_code: str | None = None,
    timezone: str | None = None,
) -> dict:
    """
    Obtiene un resumen de alertas para mostrar en el dashboard.
    
    Returns:
        Dict con conteos por severidad
    """
    alerts = get_all_alerts(
        currency_symbol,
        company_id,
        branch_id,
        country_code=country_code,
        timezone=timezone,
    )
    
    summary = {
        "total": len(alerts),
        "critical": sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL),
        "error": sum(1 for a in alerts if a.severity == AlertSeverity.ERROR),
        "warning": sum(1 for a in alerts if a.severity == AlertSeverity.WARNING),
        "info": sum(1 for a in alerts if a.severity == AlertSeverity.INFO),
        "alerts": [a.to_dict() for a in alerts],
    }
    
    return summary
