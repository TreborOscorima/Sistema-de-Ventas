from __future__ import annotations

import datetime
import os
from typing import Any

import jwt
from dotenv import load_dotenv
from jwt import ExpiredSignatureError, PyJWTError

from app.constants import TOKEN_EXPIRY_HOURS, REFRESH_TOKEN_EXPIRY_DAYS

load_dotenv()


def _require_env(var_name: str) -> str:
    """Obtiene una variable de entorno obligatoria o lanza error."""
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(f"Variable de entorno requerida no encontrada: {var_name}")
    return value


def _is_prod_environment() -> bool:
    """Determina si el entorno actual es producción."""
    value = (os.getenv("ENV") or "dev").strip().lower()
    return value in {"prod", "production"}


SECRET_KEY = _require_env("AUTH_SECRET_KEY")
if _is_prod_environment():
    secret_lower = SECRET_KEY.strip().lower()
    if len(SECRET_KEY) < 32 or secret_lower in {"change_me", "changeme", "default"}:
        raise RuntimeError(
            "AUTH_SECRET_KEY insegura para producción. Usa mínimo 32 caracteres aleatorios."
        )
ALGORITHM = "HS256"


def create_access_token(
    subject: str | Any,
    token_version: int | None = None,
    company_id: int | None = None,
) -> str:
    """Crea un token JWT de acceso con expiración configurable."""
    expire = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(hours=TOKEN_EXPIRY_HOURS)
    payload = {
        "sub": str(subject),
        "exp": expire,
    }
    if token_version is not None:
        payload["ver"] = int(token_version)
    if company_id is not None:
        payload["cid"] = int(company_id)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict | None:
    """Decodifica y valida un token JWT. Retorna el payload o None si es inválido."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("sub"):
            return None
        return payload
    except ExpiredSignatureError:
        return None
    except PyJWTError:
        return None


def verify_token(token: str) -> str | None:
    """Verifica un token JWT y retorna el subject (usuario) o None."""
    payload = decode_token(token)
    if not payload:
        return None
    return str(payload.get("sub"))


# ── Refresh tokens ─────────────────────────────────────────

def create_refresh_token(
    subject: str | Any,
    token_version: int | None = None,
    company_id: int | None = None,
) -> str:
    """Crea un refresh token JWT con expiración extendida.

    El claim ``typ`` = ``"refresh"`` permite distinguirlo de un access token
    durante la validación.
    """
    expire = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(
        days=REFRESH_TOKEN_EXPIRY_DAYS,
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "typ": "refresh",
    }
    if token_version is not None:
        payload["ver"] = int(token_version)
    if company_id is not None:
        payload["cid"] = int(company_id)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_refresh_token(token: str) -> dict | None:
    """Decodifica un refresh token. Retorna payload sólo si ``typ`` == ``"refresh"``."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("typ") != "refresh":
            return None
        if not payload.get("sub"):
            return None
        return payload
    except ExpiredSignatureError:
        return None
    except PyJWTError:
        return None


def refresh_access_token(refresh_tok: str) -> tuple[str, str] | None:
    """Valida un refresh token y emite un nuevo par (access, refresh).

    Retorna ``(new_access_token, new_refresh_token)`` o ``None`` si el
    refresh token es inválido o expirado.  Aplica *token rotation*: cada
    uso del refresh token produce uno nuevo para limitar la ventana de
    reutilización.
    """
    payload = decode_refresh_token(refresh_tok)
    if not payload:
        return None
    subject = payload["sub"]
    version = payload.get("ver")
    company_id = payload.get("cid")
    new_access = create_access_token(subject, token_version=version, company_id=company_id)
    new_refresh = create_refresh_token(subject, token_version=version, company_id=company_id)
    return new_access, new_refresh
