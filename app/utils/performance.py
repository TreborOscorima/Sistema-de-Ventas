"""Utilidades de monitoreo de rendimiento para consultas de base de datos.

Este módulo proporciona herramientas para detectar y registrar consultas lentas,
útil para optimización y depuración en producción.

Uso básico::

    from app.utils.performance import query_timer, log_slow_query

    async with query_timer("load_products") as timer:
        products = await session.exec(select(Product))
    # Automáticamente logea si excede umbral

    # O manualmente
    start = time.perf_counter()
    # ... ejecutar query ...
    elapsed = time.perf_counter() - start
    log_slow_query("buscar_clientes", elapsed)
"""
import os
import time
from contextlib import contextmanager
from typing import Generator
from functools import wraps
from decimal import Decimal

from app.utils.logger import get_logger

logger = get_logger("Performance")

# Umbral en segundos para considerar una query "lenta"
SLOW_QUERY_THRESHOLD = float(os.getenv("SLOW_QUERY_THRESHOLD", "1.0"))

# Umbral para consultas muy lentas (alertar inmediatamente)
CRITICAL_QUERY_THRESHOLD = float(os.getenv("CRITICAL_QUERY_THRESHOLD", "5.0"))


def log_slow_query(
    operation: str,
    elapsed: float,
    threshold: float = SLOW_QUERY_THRESHOLD,
    extra_context: dict | None = None,
) -> None:
    """
    Registra una query si excede el umbral de tiempo.

    Parámetros:
        operation: Nombre descriptivo de la operación
        elapsed: Tiempo transcurrido en segundos
        threshold: Umbral personalizado (default: SLOW_QUERY_THRESHOLD)
        extra_context: Información adicional para el log
    """
    if elapsed < threshold:
        return

    # Redondear para legibilidad
    elapsed_ms = round(elapsed * 1000, 2)

    context_str = ""
    if extra_context:
        # Filtrar info sensible
        safe_context = {
            k: v for k, v in extra_context.items()
            if k.lower() not in ("password", "token", "secret", "key")
        }
        context_str = f" | Context: {safe_context}"

    if elapsed >= CRITICAL_QUERY_THRESHOLD:
        logger.error(
            f"⚠️ QUERY CRÍTICA: '{operation}' tardó {elapsed_ms}ms "
            f"(umbral crítico: {CRITICAL_QUERY_THRESHOLD * 1000}ms){context_str}"
        )
    else:
        logger.warning(
            f"🐢 Query lenta: '{operation}' tardó {elapsed_ms}ms "
            f"(umbral: {threshold * 1000}ms){context_str}"
        )


@contextmanager
def query_timer(
    operation: str,
    threshold: float = SLOW_QUERY_THRESHOLD,
    extra_context: dict | None = None,
) -> Generator[dict, None, None]:
    """
    Context manager para medir tiempo de ejecución de consultas.

    Parámetros:
        operation: Nombre descriptivo de la operación
        threshold: Umbral en segundos para alertar
        extra_context: Información adicional para el log

    Genera:
        Dict con información de timing (elapsed se llena al salir)

    Ejemplo::

        async with query_timer("cargar_productos", extra_context={"filtro": "activos"}):
            products = await session.exec(select(Product).where(Product.active == True))
    """
    timing_info = {"elapsed": 0.0, "operation": operation}
    start = time.perf_counter()

    try:
        yield timing_info
    finally:
        elapsed = time.perf_counter() - start
        timing_info["elapsed"] = elapsed
        log_slow_query(operation, elapsed, threshold, extra_context)


def timed_operation(operation_name: str | None = None, threshold: float = SLOW_QUERY_THRESHOLD):
    """
    Decorador para medir tiempo de funciones/métodos.

    Parámetros:
        operation_name: Nombre para el log (default: nombre de función)
        threshold: Umbral en segundos

    Ejemplo::

        @timed_operation("buscar_cliente_por_dni")
        async def find_client(session, dni: str):
            ...
    """
    def decorator(func):
        name = operation_name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                log_slow_query(name, elapsed, threshold)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                log_slow_query(name, elapsed, threshold)

        # Detectar si es función async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class QueryStats:
    """
    Recolector de estadísticas de consultas para análisis.

    Uso para depuración local o tests::

        stats = QueryStats()

        with stats.track("load_sales"):
            sales = await load_sales()

        with stats.track("load_items"):
            items = await load_items()

        print(stats.summary())
        # {'total_queries': 2, 'total_time_ms': 45.2, 'slowest': 'load_sales'}
    """

    def __init__(self):
        self._queries: list[dict] = []

    @contextmanager
    def track(self, operation: str) -> Generator[None, None, None]:
        """Trackear una operación."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self._queries.append({
                "operation": operation,
                "elapsed_ms": round(elapsed * 1000, 2),
            })

    def summary(self) -> dict:
        """Obtener resumen de estadísticas."""
        if not self._queries:
            return {"total_queries": 0, "total_time_ms": 0}

        total_time = sum(q["elapsed_ms"] for q in self._queries)
        slowest = max(self._queries, key=lambda q: q["elapsed_ms"])

        return {
            "total_queries": len(self._queries),
            "total_time_ms": round(total_time, 2),
            "avg_time_ms": round(total_time / len(self._queries), 2),
            "slowest": slowest["operation"],
            "slowest_time_ms": slowest["elapsed_ms"],
        }

    def reset(self) -> None:
        """Limpiar estadísticas."""
        self._queries.clear()

    @property
    def queries(self) -> list[dict]:
        """Lista de consultas trackeadas."""
        return self._queries.copy()
