from __future__ import annotations

import datetime
import os
from typing import Any

import jwt
from dotenv import load_dotenv
from jwt import ExpiredSignatureError, PyJWTError

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
    """Crea un token JWT de acceso con expiración de 24 horas."""
    expire = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(hours=24)
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
