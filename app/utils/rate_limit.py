"""
Rate Limiting centralizado con soporte para Redis (producción) y memoria (desarrollo).

Este módulo proporciona protección contra ataques de fuerza bruta
en el sistema de autenticación, compartiendo estado entre workers.
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List

# Intentar importar Redis, fallback a memoria si no está disponible
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.constants import MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES

logger = logging.getLogger("RateLimit")

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

_redis_client: "redis.Redis | None" = None
_memory_store: Dict[str, List[datetime]] = defaultdict(list)


def _get_environment() -> str:
    """Obtiene el entorno actual."""
    env = (os.getenv("ENV") or "dev").strip().lower()
    return "prod" if env in {"prod", "production"} else "dev"


def _allow_memory_fallback_in_prod() -> bool:
    value = (os.getenv("ALLOW_MEMORY_RATE_LIMIT_FALLBACK") or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _strict_rate_limit_backend() -> bool:
    return _get_environment() == "prod" and not _allow_memory_fallback_in_prod()


def _get_redis() -> "redis.Redis | None":
    """
    Obtiene cliente Redis configurado.
    
    Returns:
        Cliente Redis o None si no está disponible/configurado
    """
    global _redis_client
    
    strict_backend = _strict_rate_limit_backend()
    if not REDIS_AVAILABLE:
        if strict_backend:
            logger.critical(
                "Redis requerido en producción para rate limiting distribuido."
            )
        return None
    
    if _redis_client is not None:
        return _redis_client
    
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        if strict_backend:
            logger.critical(
                "REDIS_URL no configurado y fallback en memoria deshabilitado."
            )
        return None
    
    try:
        _redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        # Test de conexión
        _redis_client.ping()
        logger.info("Redis conectado para rate limiting")
        return _redis_client
    except Exception as e:
        if strict_backend:
            logger.critical(
                "Redis no disponible y fallback en memoria deshabilitado: %s",
                str(e)[:120],
            )
        else:
            logger.warning("Redis no disponible, usando memoria: %s", str(e)[:50])
        _redis_client = None
        return None


# =============================================================================
# FUNCIONES PRINCIPALES
# =============================================================================

def _normalize_ip(ip_address: str | None) -> str | None:
    if not ip_address:
        return None
    ip = str(ip_address).strip()
    if "," in ip:
        ip = ip.split(",", 1)[0].strip()
    return ip or None


def _build_key(username: str, ip_address: str | None = None) -> str | None:
    key = (username or "").lower().strip()
    if not key:
        return None
    ip = _normalize_ip(ip_address)
    if ip:
        return f"{key}|{ip}"
    return key


def is_rate_limited(
    username: str,
    max_attempts: int = MAX_LOGIN_ATTEMPTS,
    window_minutes: int = LOGIN_LOCKOUT_MINUTES,
    ip_address: str | None = None,
) -> bool:
    """
    Verifica si un usuario está bloqueado por demasiados intentos fallidos.
    
    Args:
        username: Nombre de usuario a verificar
        max_attempts: Número máximo de intentos permitidos
        window_minutes: Ventana de tiempo en minutos
        
    Returns:
        True si está bloqueado, False si puede intentar
    """
    key = _build_key(username, ip_address)
    if not key:
        return False
    
    redis_client = _get_redis()
    if redis_client is None and _strict_rate_limit_backend():
        # Fail-closed: en producción no se permite backend en memoria.
        return True
    
    if redis_client is not None:
        # Modo Redis (producción)
        try:
            redis_key = f"login_attempts:{key}"
            attempts = redis_client.get(redis_key)
            return int(attempts or 0) >= max_attempts
        except Exception as e:
            logger.error("Error Redis is_rate_limited: %s", e)
            if _strict_rate_limit_backend():
                return True
            return _is_rate_limited_memory(key, max_attempts, window_minutes)
    
    # Modo memoria (desarrollo)
    return _is_rate_limited_memory(key, max_attempts, window_minutes)


def _is_rate_limited_memory(
    username: str,
    max_attempts: int,
    window_minutes: int,
) -> bool:
    """Rate limiting en memoria (single worker)."""
    now = datetime.now()
    cutoff = now - timedelta(minutes=window_minutes)
    
    # Limpiar intentos antiguos
    _memory_store[username] = [
        t for t in _memory_store[username] if t > cutoff
    ]
    
    return len(_memory_store[username]) >= max_attempts


def record_failed_attempt(
    username: str,
    window_minutes: int = LOGIN_LOCKOUT_MINUTES,
    ip_address: str | None = None,
) -> None:
    """
    Registra un intento de login fallido.
    
    Args:
        username: Nombre de usuario
        window_minutes: Tiempo de expiración del registro
    """
    key = _build_key(username, ip_address)
    if not key:
        return
    
    redis_client = _get_redis()
    if redis_client is None and _strict_rate_limit_backend():
        logger.error(
            "Intento fallido no registrado: Redis no disponible en modo estricto."
        )
        return
    
    if redis_client is not None:
        try:
            redis_key = f"login_attempts:{key}"
            pipe = redis_client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, window_minutes * 60)
            pipe.execute()
            return
        except Exception as e:
            logger.error("Error Redis record_failed_attempt: %s", e)
    
    # Fallback a memoria
    _memory_store[key].append(datetime.now())


def clear_login_attempts(username: str, ip_address: str | None = None) -> None:
    """
    Limpia los intentos fallidos tras login exitoso.
    
    Args:
        username: Nombre de usuario
    """
    key = _build_key(username, ip_address)
    if not key:
        return
    
    redis_client = _get_redis()
    if redis_client is None and _strict_rate_limit_backend():
        return
    
    if redis_client is not None:
        try:
            redis_client.delete(f"login_attempts:{key}")
        except Exception as e:
            logger.error("Error Redis clear_login_attempts: %s", e)
    
    # Limpiar también en memoria (por si hubo fallback)
    _memory_store.pop(key, None)


def remaining_lockout_time(
    username: str,
    window_minutes: int = LOGIN_LOCKOUT_MINUTES,
    ip_address: str | None = None,
) -> int:
    """
    Calcula los minutos restantes de bloqueo.
    
    Args:
        username: Nombre de usuario
        window_minutes: Ventana de tiempo original
        
    Returns:
        Minutos restantes o 0 si no está bloqueado
    """
    key = _build_key(username, ip_address)
    if not key:
        return 0
    
    redis_client = _get_redis()
    if redis_client is None and _strict_rate_limit_backend():
        return max(1, int(window_minutes))
    
    if redis_client is not None:
        try:
            redis_key = f"login_attempts:{key}"
            ttl = redis_client.ttl(redis_key)
            if ttl and ttl > 0:
                return max(1, (ttl + 59) // 60)  # Redondear hacia arriba
            return 0
        except Exception as e:
            logger.error("Error Redis remaining_lockout_time: %s", e)
    
    # Modo memoria
    if not _memory_store.get(key):
        return 0
    
    oldest_attempt = min(_memory_store[key])
    unlock_time = oldest_attempt + timedelta(minutes=window_minutes)
    remaining = (unlock_time - datetime.now()).total_seconds() / 60
    
    return max(0, int(remaining) + 1)


def get_rate_limit_status() -> dict:
    """
    Obtiene estado del sistema de rate limiting (para debugging).
    
    Returns:
        Dict con información del estado actual
    """
    redis_client = _get_redis()
    
    return {
        "backend": "redis" if redis_client else "memory",
        "redis_available": REDIS_AVAILABLE,
        "redis_connected": redis_client is not None,
        "strict_backend": _strict_rate_limit_backend(),
        "memory_fallback_allowed": _allow_memory_fallback_in_prod(),
        "memory_entries": len(_memory_store),
    }
