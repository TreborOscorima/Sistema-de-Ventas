from __future__ import annotations

import datetime
import os
from typing import Any

import jwt
from dotenv import load_dotenv
from jwt import ExpiredSignatureError, PyJWTError

load_dotenv()


def _require_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {var_name}")
    return value


SECRET_KEY = _require_env("AUTH_SECRET_KEY")
ALGORITHM = "HS256"


def create_access_token(
    subject: str | Any,
    token_version: int | None = None,
    company_id: int | None = None,
) -> str:
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
    payload = decode_token(token)
    if not payload:
        return None
    return str(payload.get("sub"))
