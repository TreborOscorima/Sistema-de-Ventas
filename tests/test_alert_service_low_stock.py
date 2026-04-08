"""Tests del servicio de alertas — stock bajo + integración global.

Cubre:
  - get_low_stock_alerts: detecta productos críticos / bajos / sin stock,
    ya scoped por tenant. (Regression: antes fallaba silenciosamente porque
    referenciaba Product.is_active, atributo inexistente en el modelo.)
  - get_all_alerts: integra batches por vencer, no rompe ante falla parcial.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-alert-service-32chars-pls")
os.environ.setdefault("TENANT_STRICT", "0")

import reflex as rx

from app.services import alert_service
from app.services.alert_service import (
    AlertSeverity,
    AlertType,
    get_all_alerts,
    get_low_stock_alerts,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _product(*, id_: int, description: str, stock: float):
    p = MagicMock()
    p.id = id_
    p.description = description
    p.stock = Decimal(str(stock))
    return p


class _ExecResult:
    def __init__(self, rows=None, scalar=None):
        self._rows = rows or []
        self._scalar = scalar

    def all(self):
        return self._rows

    def one(self):
        return self._scalar


class _SequentialSession:
    """FakeSession que responde queries en el orden esperado.

    get_low_stock_alerts ejecuta exactamente 3 queries en este orden:
      1. critical_query  (.all())
      2. low_stock_query (.all())
      3. out_of_stock_query (.one())
    """

    def __init__(self, responses):
        self._responses = list(responses)

    def exec(self, statement):
        if not self._responses:
            return _ExecResult(rows=[], scalar=0)
        return self._responses.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Regression: get_low_stock_alerts ya no crashea por Product.is_active
# ─────────────────────────────────────────────────────────────────────────────


class TestGetLowStockAlertsRegression:
    """Estos tests previenen una regresión real: get_low_stock_alerts crasheaba
    con AttributeError porque referenciaba Product.is_active, atributo que
    nunca existió en el modelo. El error se silenciaba en get_all_alerts via
    try/except, dejando el centro de alertas mudo en producción.
    """

    def test_funcion_no_crashea_con_db_vacia(self, monkeypatch):
        """La función debe construir las queries sin AttributeError."""
        session = _SequentialSession(
            [
                _ExecResult(rows=[]),
                _ExecResult(rows=[]),
                _ExecResult(scalar=0),
            ]
        )
        monkeypatch.setattr(rx, "session", lambda: session)

        alerts = get_low_stock_alerts(company_id=1, branch_id=1)
        assert alerts == []

    def test_detecta_stock_critico(self, monkeypatch):
        """Productos con stock <= 3 → alerta CRITICAL."""
        critical_products = [
            _product(id_=1, description="Café", stock=1.0),
            _product(id_=2, description="Té", stock=2.0),
        ]
        session = _SequentialSession(
            [
                _ExecResult(rows=critical_products),
                _ExecResult(rows=[]),
                _ExecResult(scalar=0),
            ]
        )
        monkeypatch.setattr(rx, "session", lambda: session)

        alerts = get_low_stock_alerts(company_id=1, branch_id=1)

        assert len(alerts) == 1
        assert alerts[0].type == AlertType.STOCK_CRITICAL
        assert alerts[0].severity == AlertSeverity.CRITICAL
        assert alerts[0].count == 2
        assert len(alerts[0].details["products"]) == 2

    def test_detecta_stock_bajo_warning(self, monkeypatch):
        """Productos con 3 < stock <= 10 → alerta WARNING."""
        low_products = [_product(id_=10, description="Azúcar", stock=5.0)]
        session = _SequentialSession(
            [
                _ExecResult(rows=[]),
                _ExecResult(rows=low_products),
                _ExecResult(scalar=0),
            ]
        )
        monkeypatch.setattr(rx, "session", lambda: session)

        alerts = get_low_stock_alerts(company_id=1, branch_id=1)

        assert len(alerts) == 1
        assert alerts[0].type == AlertType.STOCK_LOW
        assert alerts[0].severity == AlertSeverity.WARNING

    def test_detecta_sin_stock_error(self, monkeypatch):
        """Productos con stock <= 0 → alerta ERROR."""
        session = _SequentialSession(
            [
                _ExecResult(rows=[]),
                _ExecResult(rows=[]),
                _ExecResult(scalar=4),
            ]
        )
        monkeypatch.setattr(rx, "session", lambda: session)

        alerts = get_low_stock_alerts(company_id=1, branch_id=1)

        assert len(alerts) == 1
        assert alerts[0].type == AlertType.STOCK_CRITICAL
        assert alerts[0].severity == AlertSeverity.ERROR
        assert alerts[0].count == 4

    def test_combinacion_de_los_tres_niveles(self, monkeypatch):
        """Cuando coexisten críticos + bajos + sin stock, devuelve las 3."""
        critical = [_product(id_=1, description="X", stock=1.0)]
        low = [_product(id_=2, description="Y", stock=8.0)]
        session = _SequentialSession(
            [
                _ExecResult(rows=critical),
                _ExecResult(rows=low),
                _ExecResult(scalar=2),
            ]
        )
        monkeypatch.setattr(rx, "session", lambda: session)

        alerts = get_low_stock_alerts(company_id=1, branch_id=1)
        types = [a.type for a in alerts]

        assert AlertType.STOCK_CRITICAL in types
        assert AlertType.STOCK_LOW in types
        # STOCK_CRITICAL aparece dos veces: una crítica (severity CRITICAL)
        # y una sin stock (severity ERROR)
        assert types.count(AlertType.STOCK_CRITICAL) == 2

    def test_requiere_company_y_branch(self):
        """Llamadas sin tenant deben fallar fuerte (no silenciosamente)."""
        with pytest.raises(ValueError, match="company_id"):
            get_low_stock_alerts(company_id=None, branch_id=1)

        with pytest.raises(ValueError, match="branch_id"):
            get_low_stock_alerts(company_id=1, branch_id=None)


# ─────────────────────────────────────────────────────────────────────────────
# get_all_alerts — integración del pipeline completo
# ─────────────────────────────────────────────────────────────────────────────


class TestGetAllAlertsIntegration:
    """Verifica que get_all_alerts orqueste correctamente las distintas
    fuentes de alertas y siga adelante si una de ellas falla.
    """

    def test_combina_low_stock_y_expiring_batches(self, monkeypatch):
        """get_all_alerts debe llamar tanto a low_stock como a expiring_batches."""
        low_alert = alert_service.Alert(
            type=AlertType.STOCK_LOW,
            severity=AlertSeverity.WARNING,
            title="x",
            message="3 productos",
        )
        expiring_alert = alert_service.Alert(
            type=AlertType.BATCH_EXPIRING_SOON,
            severity=AlertSeverity.WARNING,
            title="y",
            message="2 lotes",
        )

        monkeypatch.setattr(
            alert_service,
            "get_low_stock_alerts",
            lambda *a, **kw: [low_alert],
        )
        monkeypatch.setattr(
            alert_service,
            "get_expiring_batches_alerts",
            lambda *a, **kw: [expiring_alert],
        )
        monkeypatch.setattr(
            alert_service,
            "get_installment_alerts",
            lambda *a, **kw: [],
        )
        monkeypatch.setattr(
            alert_service,
            "get_cashbox_alerts",
            lambda *a, **kw: [],
        )

        alerts = get_all_alerts(company_id=1, branch_id=1)

        types = {a.type for a in alerts}
        assert AlertType.STOCK_LOW in types
        assert AlertType.BATCH_EXPIRING_SOON in types

    def test_falla_parcial_no_rompe_otras_alertas(self, monkeypatch):
        """Si una fuente truena, las otras siguen funcionando."""
        good_alert = alert_service.Alert(
            type=AlertType.BATCH_EXPIRED,
            severity=AlertSeverity.ERROR,
            title="lotes vencidos",
            message="2 lotes",
        )

        def _explode(*a, **kw):
            raise RuntimeError("DB down for low_stock")

        monkeypatch.setattr(
            alert_service, "get_low_stock_alerts", _explode
        )
        monkeypatch.setattr(
            alert_service,
            "get_expiring_batches_alerts",
            lambda *a, **kw: [good_alert],
        )
        monkeypatch.setattr(
            alert_service,
            "get_installment_alerts",
            lambda *a, **kw: [],
        )
        monkeypatch.setattr(
            alert_service,
            "get_cashbox_alerts",
            lambda *a, **kw: [],
        )

        alerts = get_all_alerts(company_id=1, branch_id=1)

        # La alerta sobreviviente debe estar presente
        assert any(a.type == AlertType.BATCH_EXPIRED for a in alerts)
        assert not any(a.type == AlertType.STOCK_LOW for a in alerts)

    def test_ordena_por_severidad_critical_primero(self, monkeypatch):
        """get_all_alerts ordena las alertas: CRITICAL → ERROR → WARNING → INFO."""
        warning = alert_service.Alert(
            type=AlertType.BATCH_EXPIRING_SOON,
            severity=AlertSeverity.WARNING,
            title="warn",
            message="m",
        )
        critical = alert_service.Alert(
            type=AlertType.STOCK_CRITICAL,
            severity=AlertSeverity.CRITICAL,
            title="crit",
            message="m",
        )
        error = alert_service.Alert(
            type=AlertType.BATCH_EXPIRED,
            severity=AlertSeverity.ERROR,
            title="err",
            message="m",
        )

        monkeypatch.setattr(
            alert_service,
            "get_low_stock_alerts",
            lambda *a, **kw: [warning, critical],
        )
        monkeypatch.setattr(
            alert_service,
            "get_expiring_batches_alerts",
            lambda *a, **kw: [error],
        )
        monkeypatch.setattr(
            alert_service, "get_installment_alerts", lambda *a, **kw: []
        )
        monkeypatch.setattr(
            alert_service, "get_cashbox_alerts", lambda *a, **kw: []
        )

        alerts = get_all_alerts(company_id=1, branch_id=1)

        severities = [a.severity for a in alerts]
        assert severities == [
            AlertSeverity.CRITICAL,
            AlertSeverity.ERROR,
            AlertSeverity.WARNING,
        ]
