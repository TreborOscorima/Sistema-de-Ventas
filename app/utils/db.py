"""Re-exporta el engine async compartido de tuwayki_core para evitar pools duplicados.

Antes de esta corrección existían dos AsyncEngine independientes apuntando al mismo
MySQL — 2× conexiones, posibles inconsistencias de pool. Ahora toda la app (app + core)
comparte un único motor.

load_dotenv() antes del import garantiza que DB_USER/DB_PASSWORD estén disponibles
cuando tuwayki_core.utils.db se cargue por primera vez desde este punto de entrada.
"""
from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from tuwayki_core.utils.db import (  # noqa: E402, F401
    ASYNC_DATABASE_URL,
    AsyncSessionLocal,
    async_engine,
    dispose_engine,
    get_async_session,
)

__all__ = [
    "ASYNC_DATABASE_URL",
    "AsyncSessionLocal",
    "async_engine",
    "dispose_engine",
    "get_async_session",
]
