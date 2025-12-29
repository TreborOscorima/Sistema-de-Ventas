from __future__ import annotations

import datetime
from typing import Any

import jwt
from jwt import ExpiredSignatureError, PyJWTError

SECRET_KEY = "tuwaykiapp_dev_secret_2025_04_18_8f45d2f7a9c94c4d9b3a1d5f3c7a2b91"
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
