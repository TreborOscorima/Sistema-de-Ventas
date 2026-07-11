"""Tests del servicio de alertas — certificado fiscal por vencer / vencido.

Cubre:
  - get_cert_expiry_alerts: detecta certificados vencidos (CRITICAL) y
    próximos a vencer (WARNING/ERROR según días restantes).
  - No genera alerta si no hay config o si cert_not_after > 30 días.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-cert-alert-32chars-pls!")
os.environ.setdefault("TENANT_STRICT", "0")

from app.services.alert_service import (
    AlertSeverity,
    AlertType,
    CERT_EXPIRING_DAYS,
    get_cert_expiry_alerts,
)
from app.utils.timezone import utc_now_naive


def _make_config(cert_not_after: datetime | None, is_active: bool = True):
    config = MagicMock()
    config.company_id = 1
    config.is_active = is_active
    config.cert_not_after = cert_not_after
    return config


def _mock_session(config):
    session = MagicMock()
    result = MagicMock()
    result.first.return_value = config
    session.exec.return_value = result
    return session


class TestCertExpiryAlerts:
    def test_no_config_returns_empty(self):
        session = _mock_session(None)
        alerts = get_cert_expiry_alerts(company_id=1, branch_id=1, _session=session)
        assert alerts == []

    def test_cert_far_future_returns_empty(self):
        future = datetime(2027, 12, 31)
        session = _mock_session(_make_config(future))
        alerts = get_cert_expiry_alerts(company_id=1, branch_id=1, _session=session)
        assert alerts == []

    def test_cert_expiring_within_30_days_warning(self):
        expiry = utc_now_naive() + timedelta(days=20)
        session = _mock_session(_make_config(expiry))
        alerts = get_cert_expiry_alerts(company_id=1, branch_id=1, _session=session)
        assert len(alerts) == 1
        assert alerts[0].type == AlertType.CERT_EXPIRING
        assert alerts[0].severity == AlertSeverity.WARNING
        assert "20" in alerts[0].message or "19" in alerts[0].message

    def test_cert_expiring_within_7_days_error(self):
        expiry = utc_now_naive() + timedelta(days=5)
        session = _mock_session(_make_config(expiry))
        alerts = get_cert_expiry_alerts(company_id=1, branch_id=1, _session=session)
        assert len(alerts) == 1
        assert alerts[0].type == AlertType.CERT_EXPIRING
        assert alerts[0].severity == AlertSeverity.ERROR

    def test_cert_expired_critical(self):
        expiry = utc_now_naive() - timedelta(days=3)
        session = _mock_session(_make_config(expiry))
        alerts = get_cert_expiry_alerts(company_id=1, branch_id=1, _session=session)
        assert len(alerts) == 1
        assert alerts[0].type == AlertType.CERT_EXPIRED
        assert alerts[0].severity == AlertSeverity.CRITICAL
        assert "venció hace" in alerts[0].message

    def test_no_company_id_returns_empty(self):
        alerts = get_cert_expiry_alerts(company_id=None, branch_id=1)
        assert alerts == []
