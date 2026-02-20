import os
from urllib.parse import quote_plus
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.utils.logger import get_logger
from app.utils.tenant import register_tenant_listeners

load_dotenv()

logger = get_logger("DatabaseTurbo")


def _require_env(var_name: str) -> str:
    """Obtiene una variable de entorno obligatoria o lanza error."""
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(f"Variable de entorno requerida no encontrada: {var_name}")
    return value

DB_USER = _require_env("DB_USER")
DB_PASSWORD = _require_env("DB_PASSWORD")
DB_HOST = _require_env("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = _require_env("DB_NAME")

DB_USER_ESCAPED = quote_plus(DB_USER or "")
DB_PASSWORD_ESCAPED = quote_plus(DB_PASSWORD or "")

ASYNC_DATABASE_URL = (
    f"mysql+aiomysql://{DB_USER_ESCAPED}:{DB_PASSWORD_ESCAPED}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

async_engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
    pool_recycle=1800,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Registrar listeners de aislamiento multi-tenant.
register_tenant_listeners()


@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Context manager asíncrono para obtener una sesión de base de datos."""
    logger.info("🚀 Iniciando Transacción ASÍNCRONA...")
    try:
        async with AsyncSessionLocal() as session:
            try:
                yield session
            except Exception as e:
                logger.error(f"🔥 Error en sesión DB: {e}")
                await session.rollback()
                raise
    except Exception as e:
        logger.error("🔥 No se pudo abrir sesión DB.", exc_info=True)
        raise
