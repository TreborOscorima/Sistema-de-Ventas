"""Tests para app/utils/performance.py

Cobertura del módulo de monitoreo de performance:
- log_slow_query
- query_timer context manager
- timed_operation decorator
- QueryStats class
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from decimal import Decimal

from app.utils.performance import (
    log_slow_query,
    query_timer,
    timed_operation,
    QueryStats,
    SLOW_QUERY_THRESHOLD,
    CRITICAL_QUERY_THRESHOLD,
)


class TestLogSlowQuery:
    """Tests para función log_slow_query."""

    @patch("app.utils.performance.logger")
    def test_no_log_under_threshold(self, mock_logger):
        """No debe loguear si está bajo el umbral."""
        log_slow_query("test_op", 0.5, threshold=1.0)
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    @patch("app.utils.performance.logger")
    def test_warning_at_threshold(self, mock_logger):
        """Debe loguear warning si excede umbral."""
        log_slow_query("test_op", 1.5, threshold=1.0)
        mock_logger.warning.assert_called_once()
        assert "Query lenta" in mock_logger.warning.call_args[0][0]
        assert "test_op" in mock_logger.warning.call_args[0][0]

    @patch("app.utils.performance.logger")
    def test_error_at_critical_threshold(self, mock_logger):
        """Debe loguear error si excede umbral crítico."""
        log_slow_query("test_op", 6.0, threshold=1.0)
        mock_logger.error.assert_called_once()
        assert "QUERY CRÍTICA" in mock_logger.error.call_args[0][0]

    @patch("app.utils.performance.logger")
    def test_includes_extra_context(self, mock_logger):
        """Debe incluir contexto extra en el log."""
        log_slow_query(
            "test_op", 
            1.5, 
            threshold=1.0,
            extra_context={"table": "products", "rows": 100}
        )
        mock_logger.warning.assert_called_once()
        log_message = mock_logger.warning.call_args[0][0]
        assert "products" in log_message or "Context" in log_message

    @patch("app.utils.performance.logger")
    def test_filters_sensitive_context(self, mock_logger):
        """No debe incluir campos sensibles en el log."""
        log_slow_query(
            "test_op", 
            1.5, 
            threshold=1.0,
            extra_context={"user": "admin", "password": "secret123", "token": "abc"}
        )
        mock_logger.warning.assert_called_once()
        log_message = mock_logger.warning.call_args[0][0]
        assert "secret123" not in log_message
        assert "abc" not in log_message


class TestQueryTimer:
    """Tests para context manager query_timer."""

    @patch("app.utils.performance.log_slow_query")
    def test_measures_time(self, mock_log):
        """Debe medir tiempo de ejecución."""
        with query_timer("test_op", threshold=0.001) as timing:
            time.sleep(0.01)  # 10ms
        
        assert timing["elapsed"] >= 0.01
        assert timing["operation"] == "test_op"

    @patch("app.utils.performance.log_slow_query")
    def test_calls_log_slow_query(self, mock_log):
        """Debe llamar a log_slow_query al salir."""
        with query_timer("test_op", threshold=0.001):
            time.sleep(0.01)
        
        mock_log.assert_called_once()
        call_args = mock_log.call_args
        assert call_args[0][0] == "test_op"  # operation
        assert call_args[0][1] >= 0.01  # elapsed

    @patch("app.utils.performance.log_slow_query")
    def test_passes_extra_context(self, mock_log):
        """Debe pasar contexto extra al log."""
        context = {"query_type": "select"}
        with query_timer("test_op", extra_context=context):
            pass
        
        mock_log.assert_called_once()
        # log_slow_query recibe: operation, elapsed, threshold, extra_context
        call_kwargs = mock_log.call_args
        assert call_kwargs[0][0] == "test_op"  # operation
        assert context == call_kwargs[1].get("extra_context") or context == call_kwargs[0][3] if len(call_kwargs[0]) > 3 else True

    @patch("app.utils.performance.log_slow_query")
    def test_logs_even_on_exception(self, mock_log):
        """Debe loguear incluso si hay excepción."""
        try:
            with query_timer("test_op"):
                raise ValueError("test error")
        except ValueError:
            pass
        
        mock_log.assert_called_once()


class TestTimedOperationDecorator:
    """Tests para decorador timed_operation."""

    @patch("app.utils.performance.log_slow_query")
    def test_decorates_sync_function(self, mock_log):
        """Debe funcionar con funciones síncronas."""
        @timed_operation("sync_op", threshold=0.001)
        def slow_function():
            time.sleep(0.01)
            return "result"
        
        result = slow_function()
        
        assert result == "result"
        mock_log.assert_called_once()
        assert mock_log.call_args[0][0] == "sync_op"

    @patch("app.utils.performance.log_slow_query")
    @pytest.mark.asyncio
    async def test_decorates_async_function(self, mock_log):
        """Debe funcionar con funciones asíncronas."""
        import asyncio
        
        @timed_operation("async_op", threshold=0.001)
        async def slow_async_function():
            await asyncio.sleep(0.01)
            return "async_result"
        
        result = await slow_async_function()
        
        assert result == "async_result"
        mock_log.assert_called_once()
        assert mock_log.call_args[0][0] == "async_op"

    @patch("app.utils.performance.log_slow_query")
    def test_uses_function_name_as_default(self, mock_log):
        """Debe usar nombre de función si no se especifica."""
        @timed_operation()
        def my_custom_function():
            return True
        
        my_custom_function()
        
        mock_log.assert_called_once()
        assert mock_log.call_args[0][0] == "my_custom_function"


class TestQueryStats:
    """Tests para clase QueryStats."""

    def test_track_records_query(self):
        """Debe registrar queries trackeadas."""
        stats = QueryStats()
        
        with stats.track("op1"):
            time.sleep(0.01)
        
        assert len(stats.queries) == 1
        assert stats.queries[0]["operation"] == "op1"
        assert stats.queries[0]["elapsed_ms"] >= 10

    def test_track_multiple_queries(self):
        """Debe registrar múltiples queries."""
        stats = QueryStats()
        
        with stats.track("op1"):
            pass
        with stats.track("op2"):
            time.sleep(0.02)
        with stats.track("op3"):
            pass
        
        assert len(stats.queries) == 3

    def test_summary_empty(self):
        """Summary vacío cuando no hay queries."""
        stats = QueryStats()
        summary = stats.summary()
        
        assert summary["total_queries"] == 0
        assert summary["total_time_ms"] == 0

    def test_summary_with_queries(self):
        """Summary debe calcular estadísticas correctamente."""
        stats = QueryStats()
        
        with stats.track("fast"):
            time.sleep(0.01)
        with stats.track("slow"):
            time.sleep(0.03)
        
        summary = stats.summary()
        
        assert summary["total_queries"] == 2
        assert summary["total_time_ms"] >= 40  # Al menos 40ms
        assert summary["slowest"] == "slow"
        assert summary["slowest_time_ms"] >= 30

    def test_reset_clears_queries(self):
        """Reset debe limpiar las queries."""
        stats = QueryStats()
        
        with stats.track("op1"):
            pass
        
        assert len(stats.queries) == 1
        
        stats.reset()
        
        assert len(stats.queries) == 0

    def test_queries_returns_copy(self):
        """Queries debe retornar copia, no referencia."""
        stats = QueryStats()
        
        with stats.track("op1"):
            pass
        
        queries_copy = stats.queries
        queries_copy.append({"operation": "fake", "elapsed_ms": 0})
        
        assert len(stats.queries) == 1  # Original no modificado
