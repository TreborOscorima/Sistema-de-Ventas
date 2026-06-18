"""Tests unitarios para app/api.py.

Cubre:
- /api/ping: liveness sin tocar DB ni Redis
- /api/health: readiness con DB + Redis OK → 200
- /api/health: degraded cuando DB falla → 503
- /api/health: degraded cuando Redis falla → 503
- /api/health: Redis skipped cuando REDIS_URL no está configurada
- _read_version: fallback "dev" cuando VERSION no existe
- _read_version: devuelve contenido del archivo VERSION
- _utcnow_iso: formato ISO-8601 UTC
- _health_check: estructura completa del payload
"""
from __future__ import annotations

import os
from datetime import timezone, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-api-32chars-long-ok")
os.environ.setdefault("TENANT_STRICT", "0")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_request():
    """Request Starlette mínimo para los handlers."""
    return MagicMock()


# ─────────────────────────────────────────────────────────────────────────────
# Tests: /api/ping
# ─────────────────────────────────────────────────────────────────────────────


class TestPing:
    @pytest.mark.asyncio
    async def test_ping_returns_200_pong(self):
        from app.api import _ping

        resp = await _ping(_make_request())

        assert resp.status_code == 200
        import json
        body = json.loads(resp.body)
        assert body["pong"] is True

    @pytest.mark.asyncio
    async def test_ping_does_not_call_db_nor_redis(self):
        """Liveness no debe abrir conexiones — evita cascadas de errores."""
        from app.api import _ping

        with patch("app.api._check_db", new_callable=AsyncMock) as mock_db, \
             patch("app.api._check_redis", new_callable=AsyncMock) as mock_redis:
            await _ping(_make_request())

        mock_db.assert_not_called()
        mock_redis.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Tests: /api/health
# ─────────────────────────────────────────────────────────────────────────────


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_ok_when_all_checks_pass(self):
        from app.api import _health_check

        with patch("app.api._check_db", new_callable=AsyncMock, return_value=(True, None)), \
             patch("app.api._check_redis", new_callable=AsyncMock, return_value=(True, None)):
            resp = await _health_check(_make_request())

        assert resp.status_code == 200
        import json
        body = json.loads(resp.body)
        assert body["status"] == "ok"
        assert body["checks"]["db"]["ok"] is True
        assert body["checks"]["redis"]["ok"] is True
        assert body["checks"]["db"]["error"] is None

    @pytest.mark.asyncio
    async def test_health_degraded_when_db_fails(self):
        from app.api import _health_check

        err = "OperationalError: can't connect"
        with patch("app.api._check_db", new_callable=AsyncMock, return_value=(False, err)), \
             patch("app.api._check_redis", new_callable=AsyncMock, return_value=(True, None)):
            resp = await _health_check(_make_request())

        assert resp.status_code == 503
        import json
        body = json.loads(resp.body)
        assert body["status"] == "degraded"
        assert body["checks"]["db"]["ok"] is False
        assert body["checks"]["db"]["error"] == err

    @pytest.mark.asyncio
    async def test_health_degraded_when_redis_fails(self):
        from app.api import _health_check

        err = "ConnectionRefusedError: redis no disponible"
        with patch("app.api._check_db", new_callable=AsyncMock, return_value=(True, None)), \
             patch("app.api._check_redis", new_callable=AsyncMock, return_value=(False, err)):
            resp = await _health_check(_make_request())

        assert resp.status_code == 503
        import json
        body = json.loads(resp.body)
        assert body["status"] == "degraded"
        assert body["checks"]["redis"]["ok"] is False
        assert body["checks"]["redis"]["error"] == err

    @pytest.mark.asyncio
    async def test_health_payload_has_required_keys(self):
        """El payload siempre incluye status, surface, version, uptime y timestamp."""
        from app.api import _health_check

        with patch("app.api._check_db", new_callable=AsyncMock, return_value=(True, None)), \
             patch("app.api._check_redis", new_callable=AsyncMock, return_value=(True, None)):
            resp = await _health_check(_make_request())

        import json
        body = json.loads(resp.body)
        for key in ("status", "surface", "version", "uptime_seconds", "timestamp", "checks"):
            assert key in body, f"falta la clave '{key}' en el payload"

    @pytest.mark.asyncio
    async def test_health_uptime_is_non_negative(self):
        from app.api import _health_check

        with patch("app.api._check_db", new_callable=AsyncMock, return_value=(True, None)), \
             patch("app.api._check_redis", new_callable=AsyncMock, return_value=(True, None)):
            resp = await _health_check(_make_request())

        import json
        body = json.loads(resp.body)
        assert body["uptime_seconds"] >= 0


# ─────────────────────────────────────────────────────────────────────────────
# Tests: _check_redis sin REDIS_URL
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckRedisNoUrl:
    @pytest.mark.asyncio
    async def test_check_redis_ok_when_no_redis_url(self):
        """Sin REDIS_URL configurada el check devuelve True (dev sin Redis)."""
        from app.api import _check_redis

        with patch.dict(os.environ, {}, clear=False):
            old = os.environ.pop("REDIS_URL", None)
            try:
                ok, err = await _check_redis()
            finally:
                if old is not None:
                    os.environ["REDIS_URL"] = old

        assert ok is True
        assert err is None


# ─────────────────────────────────────────────────────────────────────────────
# Tests: _read_version
# ─────────────────────────────────────────────────────────────────────────────


class TestReadVersion:
    def test_returns_dev_when_file_missing(self, tmp_path):
        from app import api as api_module

        original = api_module._VERSION_FILE
        api_module._VERSION_FILE = str(tmp_path / "VERSION_missing")
        try:
            version = api_module._read_version()
        finally:
            api_module._VERSION_FILE = original

        assert version == "dev"

    def test_returns_file_contents(self, tmp_path):
        from app import api as api_module

        version_file = tmp_path / "VERSION"
        version_file.write_text("1.2.3\n")

        original = api_module._VERSION_FILE
        api_module._VERSION_FILE = str(version_file)
        try:
            version = api_module._read_version()
        finally:
            api_module._VERSION_FILE = original

        assert version == "1.2.3"


# ─────────────────────────────────────────────────────────────────────────────
# Tests: _utcnow_iso
# ─────────────────────────────────────────────────────────────────────────────


class TestUtcnowIso:
    def test_format_iso8601_utc(self):
        from app.api import _utcnow_iso

        result = _utcnow_iso()

        # Debe ser parseable como UTC ISO-8601
        dt = datetime.strptime(result, "%Y-%m-%dT%H:%M:%SZ")
        assert dt.year >= 2024

    def test_ends_with_z(self):
        from app.api import _utcnow_iso

        assert _utcnow_iso().endswith("Z")
