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
from app.utils.timezone import local_day_bounds_utc_naive, utc_now_naive

import reflex as rx
from sqlmodel import select, func
from sqlalchemy import and_, or_

from app.models import (
    Product,
    ProductBatch,
    SaleInstallment,
    Sale,
    CashboxSession,
)
from app.enums import SaleStatus
from app.i18n import MSG
from app.utils.formatting import format_currency
from app.utils.tenant import set_tenant_context


class AlertType(str, Enum):
    """Tipos de alerta del sistema."""
    STOCK_LOW = "stock_low"
    STOCK_CRITICAL = "stock_critical"
    INSTALLMENT_DUE = "installment_due"
    INSTALLMENT_OVERDUE = "installment_overdue"
    CASHBOX_OPEN_LONG = "cashbox_open_long"
    BATCH_EXPIRING_SOON = "batch_expiring_soon"
    BATCH_EXPIRED = "batch_expired"


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
            self.created_at = utc_now_naive()

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
STOCK_CRITICAL_FRACTION = 0.3  # Fracción de min_stock_alert para considerar crítico
STOCK_CRITICAL_FLOOR = 3       # Mínimo absoluto para umbral crítico
INSTALLMENT_DUE_DAYS = 3      # Días antes del vencimiento para alertar
CASHBOX_OPEN_HOURS = 12       # Horas para alertar caja abierta
BATCH_EXPIRING_DAYS = 30      # Ventana de "lotes por vencer" (Farmacia/Supermercado)


def _require_tenant(company_id: int | None, branch_id: int | None) -> None:
    if not company_id:
        raise ValueError("company_id requerido para alertas.")
    if not branch_id:
        raise ValueError("branch_id requerido para alertas.")


def get_low_stock_alerts(
    company_id: int | None = None,
    branch_id: int | None = None,
) -> List[Alert]:
    """
    Obtiene alertas de productos con stock bajo.
    
    Returns:
        Lista de alertas de stock
    """
    _require_tenant(company_id, branch_id)
    set_tenant_context(company_id, branch_id)
    alerts = []
    
    with rx.session() as session:
        # Umbral crítico dinámico por producto: max(min_stock_alert * 0.3, STOCK_CRITICAL_FLOOR)
        critical_threshold_expr = func.greatest(
            Product.min_stock_alert * STOCK_CRITICAL_FRACTION,
            STOCK_CRITICAL_FLOOR,
        )

        # Productos con stock crítico (≤ umbral crítico dinámico)
        critical_query = select(Product).where(
            and_(
                Product.is_active == True,
                Product.stock <= critical_threshold_expr,
                Product.stock > 0,
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
                title=MSG.ALERT_CRITICAL_STOCK,
                message=f"{len(critical_products)} producto(s) con stock crítico",
                count=len(critical_products),
                details={
                    "products": [
                        {"id": p.id, "name": p.description, "stock": p.stock}
                        for p in critical_products[:5]
                    ]
                }
            ))

        # Productos con stock bajo (entre umbral crítico y min_stock_alert)
        low_stock_query = select(Product).where(
            and_(
                Product.is_active == True,
                Product.stock > critical_threshold_expr,
                Product.stock <= Product.min_stock_alert,
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
                title=MSG.ALERT_LOW_STOCK,
                message=f"{len(low_stock_products)} producto(s) con stock bajo (debajo del mínimo configurado)",
                count=len(low_stock_products),
                details={
                    "products": [
                        {"id": p.id, "name": p.description, "stock": p.stock}
                        for p in low_stock_products[:5]
                    ]
                }
            ))
        
        # Productos sin stock (solo activos)
        out_of_stock_query = (
            select(func.count())
            .select_from(Product)
            .where(and_(Product.is_active == True, Product.stock <= 0))
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
                title=MSG.ALERT_NO_STOCK,
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
    _require_tenant(company_id, branch_id)
    set_tenant_context(company_id, branch_id)
    alerts = []
    today, _ = local_day_bounds_utc_naive(
        None,
        country_code,
        timezone=timezone,
    )
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
                title=MSG.ALERT_OVERDUE_INSTALLMENTS,
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
    _require_tenant(company_id, branch_id)
    set_tenant_context(company_id, branch_id)
    alerts = []
    threshold_time = utc_now_naive() - timedelta(hours=CASHBOX_OPEN_HOURS)
    
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
                title=MSG.ALERT_OPEN_CASHBOX,
                message=f"Caja abierta por más de {CASHBOX_OPEN_HOURS} horas",
                count=len(long_open_sessions),
                details={
                    "sessions": [
                        {
                            "id": s.id,
                            "opened_at": s.opening_time.isoformat(),
                            "hours_open": (utc_now_naive() - s.opening_time).total_seconds() / 3600
                        }
                        for s in long_open_sessions
                    ]
                }
            ))
    
    return alerts


def get_expiring_batches_alerts(
    company_id: int | None = None,
    branch_id: int | None = None,
    days_threshold: int = BATCH_EXPIRING_DAYS,
) -> List[Alert]:
    """
    Obtiene alertas de lotes próximos a vencer y lotes ya vencidos con stock.

    Aplica a verticales Farmacia / Supermercado donde los productos tienen
    fecha de vencimiento. Solo cuenta lotes con stock > 0 (no tiene sentido
    alertar sobre lotes ya consumidos).

    Args:
        days_threshold: Ventana en días para considerar "por vencer".

    Returns:
        Lista con (a lo sumo) dos alertas: una de lotes vencidos (ERROR)
        y una de lotes por vencer (WARNING).
    """
    _require_tenant(company_id, branch_id)
    set_tenant_context(company_id, branch_id)
    alerts: List[Alert] = []
    now = utc_now_naive()
    threshold = now + timedelta(days=days_threshold)

    with rx.session() as session:
        # 1) Lotes ya vencidos con stock > 0
        expired_query = select(ProductBatch).where(
            and_(
                ProductBatch.expiration_date != None,
                ProductBatch.expiration_date < now,
                ProductBatch.stock > 0,
            )
        )
        if company_id:
            expired_query = expired_query.where(
                ProductBatch.company_id == company_id
            )
        if branch_id:
            expired_query = expired_query.where(
                ProductBatch.branch_id == branch_id
            )
        expired_batches = session.exec(
            expired_query.order_by(ProductBatch.expiration_date.asc()).limit(10)
        ).all()
        expired_count_query = select(func.count()).select_from(ProductBatch).where(
            and_(
                ProductBatch.expiration_date != None,
                ProductBatch.expiration_date < now,
                ProductBatch.stock > 0,
            )
        )
        if company_id:
            expired_count_query = expired_count_query.where(
                ProductBatch.company_id == company_id
            )
        if branch_id:
            expired_count_query = expired_count_query.where(
                ProductBatch.branch_id == branch_id
            )
        expired_count = int(session.exec(expired_count_query).one() or 0)

        if expired_count > 0:
            alerts.append(
                Alert(
                    type=AlertType.BATCH_EXPIRED,
                    severity=AlertSeverity.ERROR,
                    title=MSG.ALERT_BATCH_EXPIRED,
                    message=f"{expired_count} lote(s) vencido(s) con stock disponible",
                    count=expired_count,
                    details={
                        "batches": [
                            {
                                "id": b.id,
                                "batch_number": b.batch_number,
                                "expiration_date": b.expiration_date.isoformat(),
                                "stock": float(b.stock or 0),
                                "product_id": b.product_id,
                                "product_variant_id": b.product_variant_id,
                            }
                            for b in expired_batches
                        ]
                    },
                )
            )

        # 2) Lotes por vencer (entre hoy y threshold) con stock > 0
        soon_query = select(ProductBatch).where(
            and_(
                ProductBatch.expiration_date != None,
                ProductBatch.expiration_date >= now,
                ProductBatch.expiration_date <= threshold,
                ProductBatch.stock > 0,
            )
        )
        if company_id:
            soon_query = soon_query.where(ProductBatch.company_id == company_id)
        if branch_id:
            soon_query = soon_query.where(ProductBatch.branch_id == branch_id)
        soon_batches = session.exec(
            soon_query.order_by(ProductBatch.expiration_date.asc()).limit(10)
        ).all()
        soon_count_query = select(func.count()).select_from(ProductBatch).where(
            and_(
                ProductBatch.expiration_date != None,
                ProductBatch.expiration_date >= now,
                ProductBatch.expiration_date <= threshold,
                ProductBatch.stock > 0,
            )
        )
        if company_id:
            soon_count_query = soon_count_query.where(
                ProductBatch.company_id == company_id
            )
        if branch_id:
            soon_count_query = soon_count_query.where(
                ProductBatch.branch_id == branch_id
            )
        soon_count = int(session.exec(soon_count_query).one() or 0)

        if soon_count > 0:
            alerts.append(
                Alert(
                    type=AlertType.BATCH_EXPIRING_SOON,
                    severity=AlertSeverity.WARNING,
                    title=MSG.ALERT_BATCH_EXPIRING,
                    message=(
                        f"{soon_count} lote(s) vence(n) en los próximos "
                        f"{days_threshold} días"
                    ),
                    count=soon_count,
                    details={
                        "batches": [
                            {
                                "id": b.id,
                                "batch_number": b.batch_number,
                                "expiration_date": b.expiration_date.isoformat(),
                                "stock": float(b.stock or 0),
                                "product_id": b.product_id,
                                "product_variant_id": b.product_variant_id,
                            }
                            for b in soon_batches
                        ]
                    },
                )
            )

    return alerts


async def get_overdue_count(
    session,
    company_id: int | None = None,
    branch_id: int | None = None,
    country_code: str | None = None,
    timezone: str | None = None,
) -> int:
    """Cuenta cuotas vencidas (pendientes con fecha pasada) usando sesión async."""
    _require_tenant(company_id, branch_id)
    set_tenant_context(company_id, branch_id)
    today, _ = local_day_bounds_utc_naive(
        None,
        country_code,
        timezone=timezone,
    )
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
    _require_tenant(company_id, branch_id)
    set_tenant_context(company_id, branch_id)
    alerts = []
    
    try:
        alerts.extend(get_low_stock_alerts(company_id, branch_id))
    except Exception:
        pass  # No interrumpir si falla una categoría

    try:
        alerts.extend(get_expiring_batches_alerts(company_id, branch_id))
    except Exception:
        pass

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
    _require_tenant(company_id, branch_id)
    set_tenant_context(company_id, branch_id)
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
