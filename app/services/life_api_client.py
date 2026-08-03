"""Cliente HTTP para llamadas servidor-a-servidor a la API pública de TUWAYKILIFE.

TUWAYKILIFE (Sistema para Clínicas) es un repo y una base de datos completamente
separados — toda comunicación pasa por HTTP, nunca por una conexión de base de
datos compartida. Mismo patrón que app/services/food_api_client.py.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

LIFE_API_TIMEOUT_SECONDS = 10


def _life_api_url() -> str:
    return (os.getenv("LIFE_API_URL") or "").strip().rstrip("/")


async def register_life_company(
    *, company_name: str, email: str, password: str, confirm_password: str, phone: str
) -> dict:
    """POST /api/registro en TUWAYKILIFE. Nunca loguea la contraseña."""
    base_url = _life_api_url()
    if not base_url:
        return {
            "ok": False, "status_code": 0, "data": {},
            "error": "TUWAYKILIFE no está disponible en este momento.",
        }
    payload = {
        "company_name": company_name,
        "email": email,
        "password": password,
        "confirm_password": confirm_password,
        "phone": phone,
    }
    try:
        async with httpx.AsyncClient(timeout=LIFE_API_TIMEOUT_SECONDS) as client:
            response = await client.post(f"{base_url}/api/registro", json=payload)
        data = response.json() if response.content else {}
        if response.status_code == 201:
            return {"ok": True, "status_code": 201, "data": data, "error": ""}
        return {
            "ok": False, "status_code": response.status_code, "data": data,
            "error": data.get("error", "No se pudo completar el registro."),
        }
    except httpx.TimeoutException:
        logger.error("Timeout llamando a TUWAYKILIFE /api/registro (email=%s)", email[:20])
        return {
            "ok": False, "status_code": 0, "data": {},
            "error": "TUWAYKILIFE no respondió a tiempo. Intenta de nuevo.",
        }
    except httpx.ConnectError:
        logger.error("Error de conexión a TUWAYKILIFE /api/registro")
        return {
            "ok": False, "status_code": 0, "data": {},
            "error": "No se pudo conectar con TUWAYKILIFE.",
        }
    except httpx.HTTPStatusError as exc:
        logger.error("Error HTTP de TUWAYKILIFE: %s", exc)
        return {
            "ok": False, "status_code": 0, "data": {},
            "error": "Error al comunicarse con TUWAYKILIFE.",
        }
    except Exception:
        logger.exception("Error inesperado llamando a TUWAYKILIFE /api/registro")
        return {
            "ok": False, "status_code": 0, "data": {},
            "error": "Error inesperado. Intenta de nuevo.",
        }
