"""
Health check y endpoints API personalizados para TUWAYKI.

Se integran con Reflex via `api_transformer` en app.py.
Reflex 0.8.x utiliza Starlette como framework ASGI subyacente.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

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


# Starlette app con las rutas de operaciones.
health_app = Starlette(
    routes=[
        Route("/api/health", _health_check, methods=["GET"]),
        Route("/api/ping", _ping, methods=["GET"]),
    ],
)
