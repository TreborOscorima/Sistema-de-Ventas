"""
Health check y endpoints API personalizados para TUWAYKI.

Se integran con Reflex via `api_transformer` en app.py.
Reflex 0.8.x utiliza Starlette como framework ASGI subyacente.

Incluye lifespan handler para el fiscal retry worker (background task).
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import random
import time
from datetime import datetime, timezone

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

_logger = logging.getLogger("api")

# Timestamp de arranque para cálculo de uptime.
_BOOT_TS = time.monotonic()

APP_SURFACE = (os.getenv("APP_SURFACE") or "all").strip().lower()
_VERSION_FILE = os.path.join(os.path.dirname(__file__), "..", "VERSION")


def _read_version() -> str:
    """Lee la versión del archivo VERSION en la raíz del proyecto (si existe)."""
    try:
        with open(_VERSION_FILE) as fh:
            return fh.read().strip()
    except FileNotFoundError:
        return "dev"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _health_check(request: Request) -> JSONResponse:
    """Health check liviano: confirma que el backend responde."""
    uptime_s = round(time.monotonic() - _BOOT_TS, 1)
    return JSONResponse(
        content={
            "status": "ok",
            "surface": APP_SURFACE,
            "version": _read_version(),
            "uptime_seconds": uptime_s,
            "timestamp": _utcnow_iso(),
        },
        status_code=200,
    )


async def _ping(request: Request) -> JSONResponse:
    """Ping mínimo para load balancers y uptime monitors."""
    return JSONResponse(content={"pong": True}, status_code=200)


# ── Fiscal Retry Worker (background task) ──────────────────
_FISCAL_RETRY_INTERVAL_SECONDS = int(
    os.getenv("FISCAL_RETRY_INTERVAL", "1800")  # 30 min default
)
_FISCAL_RETRY_ENABLED = os.getenv("FISCAL_RETRY_ENABLED", "1").strip() != "0"

# El worker solo debe correr en superficies que emiten documentos fiscales (POS).
# Landing (marketing público) y owner (backoffice plataforma) no tienen razón
# de golpear AFIP/SUNAT — en el stack 3-superficies eso triplicaría la carga
# externa y generaría contención sobre la misma cola de reintentos.
_FISCAL_RETRY_SURFACES = {"app", "all"}
_FISCAL_RETRY_ALLOWED_HERE = APP_SURFACE in _FISCAL_RETRY_SURFACES


async def _fiscal_retry_loop():
    """Ejecuta el worker de reintento fiscal periódicamente con jitter.

    El jitter evita "thundering herd" cuando múltiples workers detrás del ALB
    golpean AFIP/SUNAT al mismo segundo (todas las instancias fueron iniciadas
    con ~mismo uptime).
    """
    from app.tasks.fiscal_retry_worker import run_auto_retry

    # Espera inicial aleatoria (30-60s) para desincronizar instancias al boot.
    await asyncio.sleep(30 + random.uniform(0, 30))
    _logger.info(
        "Fiscal retry worker started (interval=%ss ±10%%)",
        _FISCAL_RETRY_INTERVAL_SECONDS,
    )
    while True:
        try:
            stats = await run_auto_retry()
            if stats["processed"] > 0:
                _logger.info("Fiscal retry: %s", stats)
        except Exception:
            _logger.exception("Error en fiscal retry worker")
        # Jitter ±10% sobre el intervalo base.
        jitter = _FISCAL_RETRY_INTERVAL_SECONDS * 0.1
        delay = _FISCAL_RETRY_INTERVAL_SECONDS + random.uniform(-jitter, jitter)
        await asyncio.sleep(delay)


@contextlib.asynccontextmanager
async def _lifespan(app):
    """Lifespan handler: inicia background tasks al arrancar y libera
    recursos al apagar (pool DB async, tareas pendientes)."""
    tasks = []
    if _FISCAL_RETRY_ENABLED and _FISCAL_RETRY_ALLOWED_HERE:
        task = asyncio.create_task(_fiscal_retry_loop())
        tasks.append(task)
    elif _FISCAL_RETRY_ENABLED:
        _logger.info(
            "Fiscal retry worker NO iniciado en superficie '%s' (solo corre en %s)",
            APP_SURFACE,
            sorted(_FISCAL_RETRY_SURFACES),
        )
    try:
        yield
    finally:
        # Cancelar tareas en curso.
        for task in tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        # Cerrar pool async de MySQL para evitar Aborted_clients en RDS.
        try:
            from app.utils.db import dispose_engine
            await dispose_engine()
        except Exception:
            _logger.exception("Error cerrando engine async en shutdown")


# Starlette app con las rutas de operaciones.
health_app = Starlette(
    routes=[
        Route("/api/health", _health_check, methods=["GET"]),
        Route("/api/ping", _ping, methods=["GET"]),
    ],
    lifespan=_lifespan,
)
