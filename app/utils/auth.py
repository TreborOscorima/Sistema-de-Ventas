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


def create_access_token(subject: str | Any) -> str:
    expire = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(hours=24)
    payload = {
        "sub": str(subject),
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> str | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if not subject:
            return None
        return str(subject)
    except ExpiredSignatureError:
        return None
    except PyJWTError:
        return None
