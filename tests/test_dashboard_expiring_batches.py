"""Tests del dashboard de lotes por vencer.

Cubre:
  - DashboardState._load_expiring_batches: arma la lista para el panel UI,
    distinguiendo lotes vencidos vs. próximos a vencer y heredando descripción
    del producto raíz / variante.
  - alert_service.get_expiring_batches_alerts: produce alertas Alert para
    integrarse en el panel global de alertas (vence en N días / vencido).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-expiring-batches-32chars")
os.environ.setdefault("TENANT_STRICT", "0")

import reflex as rx

from app.services.alert_service import (
    AlertSeverity,
    AlertType,
    BATCH_EXPIRING_DAYS,
)
from app.states.dashboard_state import (
    DashboardState,
    EXPIRING_BATCHES_DISPLAY_LIMIT,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


class _ExecResult:
    """Resultado de session.exec() que permite .all() y .one()."""

    def __init__(self, rows=None, scalar=None):
        self._rows = rows or []
        self._scalar = scalar

    def all(self):
        return self._rows

    def one(self):
        return self._scalar


class _FakeSession:
    """FakeSession que devuelve resultados secuenciales por cada exec().

    Útil para mockear queries múltiples (rows + count expired + count soon).
    """

    def __init__(self, results: list[_ExecResult]):
        self._results = list(results)
        self._executed = 0

    def exec(self, statement):
        if not self._results:
            return _ExecResult(rows=[], scalar=0)
        self._executed += 1
        return self._results.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _row(
    *,
    id_: int,
    batch_number: str,
    expiration: datetime,
    stock: float,
    description: str,
    product_id: int = 1,
    variant_id: int | None = None,
    size: str | None = None,
    color: str | None = None,
    sku: str | None = None,
):
    """Tupla con el mismo shape que la query de _load_expiring_batches."""
    return (
        id_,
        batch_number,
        expiration,
        Decimal(str(stock)),
        product_id,
        variant_id,
        description,
        size,
        color,
        sku,
    )


# ─────────────────────────────────────────────────────────────────────────────
# DashboardState._load_expiring_batches
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadExpiringBatches:
    """El loader del dashboard arma la lista visible y los conteos."""

    def test_separa_vencidos_y_por_vencer_y_calcula_dias(self, monkeypatch):
        state = DashboardState()
        monkeypatch.setattr(state, "_company_id", lambda: 1)
        monkeypatch.setattr(state, "_branch_id", lambda: 1)

        # Congelamos "ahora" para que los días_left sean determinísticos
        fake_now = datetime(2026, 4, 8, 12, 0, 0)
        monkeypatch.setattr(
            "app.states.dashboard_state.utc_now_naive", lambda: fake_now
        )

        rows = [
            _row(
                id_=10,
                batch_number="L-EXP",
                expiration=fake_now - timedelta(days=2),  # vencido
                stock=5.0,
                description="Ibuprofeno 400mg",
                product_id=100,
            ),
            _row(
                id_=11,
                batch_number="L-SOON",
                expiration=fake_now + timedelta(days=10),  # por vencer
                stock=12.0,
                description="Paracetamol 500mg",
                product_id=101,
            ),
        ]

        session = _FakeSession(
            [
                _ExecResult(rows=rows),       # query principal
                _ExecResult(scalar=1),         # count vencidos
                _ExecResult(scalar=1),         # count por vencer
            ]
        )
        monkeypatch.setattr(rx, "session", lambda: session)

        state._load_expiring_batches()

        assert len(state.dash_expiring_batches) == 2
        first = state.dash_expiring_batches[0]
        assert first["batch_number"] == "L-EXP"
        assert first["is_expired"] is True
        assert first["days_left"] == -2
        assert first["description"] == "Ibuprofeno 400mg"
        assert first["expiration_date"] == "2026-04-06"
        assert first["stock"] == 5.0

        second = state.dash_expiring_batches[1]
        assert second["batch_number"] == "L-SOON"
        assert second["is_expired"] is False
        assert second["days_left"] == 10
        assert second["expiration_date"] == "2026-04-18"

        assert state.expired_batches_count == 1
        assert state.expiring_batches_count == 1

    def test_describe_variante_con_talla_color(self, monkeypatch):
        state = DashboardState()
        monkeypatch.setattr(state, "_company_id", lambda: 1)
        monkeypatch.setattr(state, "_branch_id", lambda: 1)
        fake_now = datetime(2026, 4, 8, 0, 0, 0)
        monkeypatch.setattr(
            "app.states.dashboard_state.utc_now_naive", lambda: fake_now
        )

        rows = [
            _row(
                id_=20,
                batch_number="L-V1",
                expiration=fake_now + timedelta(days=5),
                stock=3.0,
                description="Polo deportivo",
                product_id=200,
                variant_id=300,
                size="XL",
                color="Rojo",
                sku="POLO-XL-R",
            ),
        ]
        session = _FakeSession(
            [_ExecResult(rows=rows), _ExecResult(scalar=0), _ExecResult(scalar=1)]
        )
        monkeypatch.setattr(rx, "session", lambda: session)

        state._load_expiring_batches()

        assert state.dash_expiring_batches[0]["description"] == "Polo deportivo (XL / Rojo)"
        assert state.dash_expiring_batches[0]["product_variant_id"] == 300

    def test_sin_company_o_branch_resetea_y_no_consulta(self, monkeypatch):
        state = DashboardState()
        # Pre-cargamos valores para verificar que se resetean
        state.dash_expiring_batches = [{"id": 99}]
        state.expiring_batches_count = 5
        state.expired_batches_count = 2

        monkeypatch.setattr(state, "_company_id", lambda: None)
        monkeypatch.setattr(state, "_branch_id", lambda: 1)

        # Si llegara a llamar rx.session sería un fallo silencioso → forzamos error
        def _explode():
            raise AssertionError("No debería abrir sesión sin tenant")

        monkeypatch.setattr(rx, "session", _explode)

        state._load_expiring_batches()

        assert state.dash_expiring_batches == []
        assert state.expiring_batches_count == 0
        assert state.expired_batches_count == 0

    def test_filas_con_expiration_none_se_ignoran(self, monkeypatch):
        state = DashboardState()
        monkeypatch.setattr(state, "_company_id", lambda: 1)
        monkeypatch.setattr(state, "_branch_id", lambda: 1)
        fake_now = datetime(2026, 4, 8, 0, 0, 0)
        monkeypatch.setattr(
            "app.states.dashboard_state.utc_now_naive", lambda: fake_now
        )

        # Una fila con expiration=None — no debe romper, solo ignorarse
        rows = [
            _row(
                id_=30,
                batch_number="L-NULL",
                expiration=None,  # type: ignore[arg-type]
                stock=10.0,
                description="Producto sin vencimiento",
                product_id=400,
            ),
            _row(
                id_=31,
                batch_number="L-OK",
                expiration=fake_now + timedelta(days=3),
                stock=8.0,
                description="Producto vigente",
                product_id=401,
            ),
        ]
        session = _FakeSession(
            [_ExecResult(rows=rows), _ExecResult(scalar=0), _ExecResult(scalar=1)]
        )
        monkeypatch.setattr(rx, "session", lambda: session)

        state._load_expiring_batches()

        assert len(state.dash_expiring_batches) == 1
        assert state.dash_expiring_batches[0]["batch_number"] == "L-OK"

    def test_descripcion_fallback_cuando_producto_es_none(self, monkeypatch):
        state = DashboardState()
        monkeypatch.setattr(state, "_company_id", lambda: 1)
        monkeypatch.setattr(state, "_branch_id", lambda: 1)
        fake_now = datetime(2026, 4, 8, 0, 0, 0)
        monkeypatch.setattr(
            "app.states.dashboard_state.utc_now_naive", lambda: fake_now
        )

        rows = [
            _row(
                id_=40,
                batch_number="L-ORPHAN",
                expiration=fake_now + timedelta(days=2),
                stock=1.0,
                description=None,  # producto sin nombre
                product_id=None,
            ),
        ]
        session = _FakeSession(
            [_ExecResult(rows=rows), _ExecResult(scalar=0), _ExecResult(scalar=1)]
        )
        monkeypatch.setattr(rx, "session", lambda: session)

        state._load_expiring_batches()

        assert state.dash_expiring_batches[0]["description"] == "(Sin descripción)"
        assert state.dash_expiring_batches[0]["product_id"] is None


# ─────────────────────────────────────────────────────────────────────────────
# alert_service.get_expiring_batches_alerts
# ─────────────────────────────────────────────────────────────────────────────


class _AlertSession:
    """FakeSession para get_expiring_batches_alerts.

    La función ejecuta 4 queries: expired_query (rows), expired_count,
    soon_query (rows), soon_count.
    """

    def __init__(self, results):
        self._results = list(results)

    def exec(self, statement):
        return self._results.pop(0) if self._results else _ExecResult(scalar=0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _make_batch_obj(*, id_: int, batch_number: str, expiration, stock: float):
    b = MagicMock()
    b.id = id_
    b.batch_number = batch_number
    b.expiration_date = expiration
    b.stock = Decimal(str(stock))
    b.product_id = 1
    b.product_variant_id = None
    return b


class TestGetExpiringBatchesAlerts:
    """El servicio de alertas produce Alert objects para vencidos y próximos."""

    def test_produce_alerta_de_vencidos_y_de_proximos(self, monkeypatch):
        from app.services import alert_service

        fake_now = datetime(2026, 4, 8, 0, 0, 0)
        monkeypatch.setattr(alert_service, "utc_now_naive", lambda: fake_now)

        expired = [
            _make_batch_obj(
                id_=1,
                batch_number="L-OLD",
                expiration=fake_now - timedelta(days=5),
                stock=4.0,
            )
        ]
        soon = [
            _make_batch_obj(
                id_=2,
                batch_number="L-NEW",
                expiration=fake_now + timedelta(days=15),
                stock=8.0,
            )
        ]

        session = _AlertSession(
            [
                _ExecResult(rows=expired),  # expired_query
                _ExecResult(scalar=1),       # expired_count
                _ExecResult(rows=soon),      # soon_query
                _ExecResult(scalar=1),       # soon_count
            ]
        )
        monkeypatch.setattr(rx, "session", lambda: session)

        alerts = alert_service.get_expiring_batches_alerts(
            company_id=1, branch_id=1
        )

        assert len(alerts) == 2
        types = {a.type for a in alerts}
        assert AlertType.BATCH_EXPIRED in types
        assert AlertType.BATCH_EXPIRING_SOON in types

        expired_alert = next(a for a in alerts if a.type == AlertType.BATCH_EXPIRED)
        assert expired_alert.severity == AlertSeverity.ERROR
        assert expired_alert.count == 1
        assert expired_alert.details["batches"][0]["batch_number"] == "L-OLD"

        soon_alert = next(
            a for a in alerts if a.type == AlertType.BATCH_EXPIRING_SOON
        )
        assert soon_alert.severity == AlertSeverity.WARNING
        assert str(BATCH_EXPIRING_DAYS) in soon_alert.message

    def test_sin_lotes_no_genera_alertas(self, monkeypatch):
        from app.services import alert_service

        fake_now = datetime(2026, 4, 8, 0, 0, 0)
        monkeypatch.setattr(alert_service, "utc_now_naive", lambda: fake_now)

        session = _AlertSession(
            [
                _ExecResult(rows=[]),
                _ExecResult(scalar=0),
                _ExecResult(rows=[]),
                _ExecResult(scalar=0),
            ]
        )
        monkeypatch.setattr(rx, "session", lambda: session)

        alerts = alert_service.get_expiring_batches_alerts(
            company_id=1, branch_id=1
        )
        assert alerts == []

    def test_solo_vencidos_omite_alerta_de_proximos(self, monkeypatch):
        from app.services import alert_service

        fake_now = datetime(2026, 4, 8, 0, 0, 0)
        monkeypatch.setattr(alert_service, "utc_now_naive", lambda: fake_now)

        expired = [
            _make_batch_obj(
                id_=1,
                batch_number="L-VIEJO",
                expiration=fake_now - timedelta(days=1),
                stock=2.0,
            )
        ]
        session = _AlertSession(
            [
                _ExecResult(rows=expired),
                _ExecResult(scalar=1),
                _ExecResult(rows=[]),
                _ExecResult(scalar=0),
            ]
        )
        monkeypatch.setattr(rx, "session", lambda: session)

        alerts = alert_service.get_expiring_batches_alerts(
            company_id=1, branch_id=1
        )
        assert len(alerts) == 1
        assert alerts[0].type == AlertType.BATCH_EXPIRED


# ─────────────────────────────────────────────────────────────────────────────
# Constantes y exports — sanity check
# ─────────────────────────────────────────────────────────────────────────────


def test_display_limit_es_razonable():
    """El panel del dashboard no debería ser una lista infinita."""
    assert 1 <= EXPIRING_BATCHES_DISPLAY_LIMIT <= 50
