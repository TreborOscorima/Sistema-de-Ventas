"""Tests para app/utils/rate_limit.py"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from app.utils.rate_limit import (
    is_rate_limited,
    record_failed_attempt,
    clear_login_attempts,
    remaining_lockout_time,
    get_rate_limit_status,
    _memory_store,
    _is_rate_limited_memory,
)


class TestMemoryRateLimiting:
    """Tests para rate limiting en memoria (sin Redis)."""

    def setup_method(self):
        """Limpiar store de memoria antes de cada test."""
        _memory_store.clear()

    def test_not_rate_limited_initially(self):
        """Usuario nuevo no está bloqueado."""
        assert is_rate_limited("testuser", max_attempts=5) is False

    def test_rate_limited_after_max_attempts(self):
        """Usuario bloqueado después de máximos intentos."""
        for _ in range(5):
            record_failed_attempt("testuser")
        
        assert is_rate_limited("testuser", max_attempts=5) is True

    def test_not_rate_limited_below_max(self):
        """Usuario no bloqueado con menos de máximos intentos."""
        for _ in range(4):
            record_failed_attempt("testuser")
        
        assert is_rate_limited("testuser", max_attempts=5) is False

    def test_clear_login_attempts(self):
        """Limpiar intentos desbloquea al usuario."""
        for _ in range(5):
            record_failed_attempt("testuser")
        
        assert is_rate_limited("testuser", max_attempts=5) is True
        
        clear_login_attempts("testuser")
        
        assert is_rate_limited("testuser", max_attempts=5) is False

    def test_username_case_insensitive(self):
        """Username normalizado a minúsculas."""
        record_failed_attempt("TestUser")
        record_failed_attempt("TESTUSER")
        record_failed_attempt("testuser")
        
        # Todos deberían contar para el mismo usuario
        assert len(_memory_store.get("testuser", [])) == 3

    def test_empty_username_not_blocked(self):
        """Username vacío no causa bloqueo."""
        assert is_rate_limited("", max_attempts=1) is False
        record_failed_attempt("")
        assert is_rate_limited("", max_attempts=1) is False

    def test_remaining_lockout_time_not_blocked(self):
        """Sin tiempo restante si no está bloqueado."""
        assert remaining_lockout_time("newuser") == 0

    def test_remaining_lockout_time_blocked(self):
        """Tiempo restante calculado correctamente."""
        for _ in range(5):
            record_failed_attempt("testuser")
        
        remaining = remaining_lockout_time("testuser", window_minutes=15)
        # Debería estar entre 14 y 16 minutos (por redondeo)
        assert 14 <= remaining <= 16

    def test_get_rate_limit_status_memory(self):
        """Estado del sistema muestra backend de memoria."""
        with patch('app.utils.rate_limit._get_redis', return_value=None):
            status = get_rate_limit_status()
            assert status["backend"] == "memory"
            assert status["redis_connected"] is False


class TestRateLimitingWithRedis:
    """Tests para rate limiting con Redis (mockeado)."""

    def test_is_rate_limited_uses_redis(self):
        """Verifica que use Redis cuando está disponible."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = "3"
        
        with patch('app.utils.rate_limit._get_redis', return_value=mock_redis):
            result = is_rate_limited("testuser", max_attempts=5)
            
            assert result is False
            mock_redis.get.assert_called_once_with("login_attempts:testuser")

    def test_is_rate_limited_blocked_in_redis(self):
        """Usuario bloqueado cuando Redis devuelve >= max_attempts."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = "5"
        
        with patch('app.utils.rate_limit._get_redis', return_value=mock_redis):
            result = is_rate_limited("testuser", max_attempts=5)
            
            assert result is True

    def test_record_failed_attempt_redis(self):
        """Registra intento fallido en Redis con pipeline."""
        mock_pipe = MagicMock()
        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe
        
        with patch('app.utils.rate_limit._get_redis', return_value=mock_redis):
            record_failed_attempt("testuser", window_minutes=15)
            
            mock_pipe.incr.assert_called_once_with("login_attempts:testuser")
            mock_pipe.expire.assert_called_once_with("login_attempts:testuser", 15 * 60)
            mock_pipe.execute.assert_called_once()

    def test_clear_login_attempts_redis(self):
        """Limpia intentos en Redis."""
        mock_redis = MagicMock()
        
        with patch('app.utils.rate_limit._get_redis', return_value=mock_redis):
            clear_login_attempts("testuser")
            
            mock_redis.delete.assert_called_once_with("login_attempts:testuser")

    def test_fallback_to_memory_on_redis_error(self):
        """Fallback a memoria si Redis falla."""
        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("Redis connection error")
        
        _memory_store.clear()
        
        with patch('app.utils.rate_limit._get_redis', return_value=mock_redis):
            # No debería lanzar excepción
            result = is_rate_limited("testuser", max_attempts=5)
            assert result is False

    def test_remaining_time_from_redis_ttl(self):
        """Tiempo restante calculado desde TTL de Redis."""
        mock_redis = MagicMock()
        mock_redis.ttl.return_value = 600  # 10 minutos en segundos
        
        with patch('app.utils.rate_limit._get_redis', return_value=mock_redis):
            remaining = remaining_lockout_time("testuser")
            
            # 600 segundos = 10 minutos, redondeado hacia arriba
            assert remaining == 10

    def test_get_rate_limit_status_redis(self):
        """Estado del sistema muestra backend Redis."""
        mock_redis = MagicMock()
        
        with patch('app.utils.rate_limit._get_redis', return_value=mock_redis):
            status = get_rate_limit_status()
            assert status["backend"] == "redis"
            assert status["redis_connected"] is True
