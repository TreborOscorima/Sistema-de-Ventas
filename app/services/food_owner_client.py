"""Cliente HTTP para que el Owner Admin gestione empresas de TUWAYKIFOOD.

Mismo patrón que food_api_client.py. TUWAYKIFOOD es un repo y una base de
datos completamente separados — sin conexión directa, todo por HTTP.
Las rutas /api/admin/* están protegidas por un secreto compartido
(FOOD_ADMIN_API_SECRET, igual en ambos repos).
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

FOOD_API_TIMEOUT_SECONDS = 10


class FoodOwnerClientError(Exception):
    """Error controlado al llamar a la API admin de TUWAYKIFOOD."""


def _base_url() -> str:
    return (os.getenv("FOOD_API_URL") or "").strip().rstrip("/")


def _headers() -> dict:
    secret = (os.getenv("FOOD_ADMIN_API_SECRET") or "").strip()
    return {"X-Admin-Secret": secret}


def _normalize_food_company(raw: dict) -> dict:
    """Mapea el JSON de Food al mismo shape que espera la UI de Ventas
    (_company_row / _company_mobile_card) -- con placeholders seguros para
    los campos que Food no tiene (planes, módulos, usuarios/sucursales)."""
    return {
        "id": raw.get("id"),
        "name": raw.get("name", ""),
        "ruc": raw.get("slug", ""),
        "admin_email": raw.get("admin_email") or "Sin correo",
        "company_phone": "Sin teléfono",
        "plan_type": "trial",
        "plan": "trial",
        "subscription_status": "active" if raw.get("is_active") else "suspended",
        "effective_status": "active" if raw.get("is_active") else "suspended",
        "current_users": 0,
        "max_users": 0,
        "current_branches": 1,
        "max_branches": 1,
        "trial_ends_at": raw.get("trial_ends_at"),
        "subscription_ends_at": None,
        "has_reservations_module": False,
        "has_services_module": False,
        "has_clients_module": False,
        "has_credits_module": False,
        "has_electronic_billing": False,
        "has_presupuestos_module": False,
        "has_promociones_module": False,
        "has_listas_precios_module": False,
        "has_etiquetas_module": False,
        "product_type": "food",
        "created_at": raw.get("created_at"),
        "is_active": bool(raw.get("is_active")),
    }


async def _request(method: str, path: str, **kwargs) -> dict:
    base_url = _base_url()
    if not base_url:
        raise FoodOwnerClientError("TUWAYKIFOOD no está disponible en este momento.")
    try:
        async with httpx.AsyncClient(timeout=FOOD_API_TIMEOUT_SECONDS) as client:
            response = await client.request(
                method, f"{base_url}{path}", headers=_headers(), **kwargs
            )
        data = response.json() if response.content else {}
        if response.status_code >= 400:
            raise FoodOwnerClientError(data.get("error", f"Error HTTP {response.status_code}."))
        return data
    except FoodOwnerClientError:
        raise
    except httpx.TimeoutException:
        logger.error("Timeout llamando a TUWAYKIFOOD %s %s", method, path)
        raise FoodOwnerClientError("TUWAYKIFOOD no respondió a tiempo. Intenta de nuevo.")
    except httpx.ConnectError:
        logger.error("Error de conexión a TUWAYKIFOOD %s %s", method, path)
        raise FoodOwnerClientError("No se pudo conectar con TUWAYKIFOOD.")
    except Exception:
        logger.exception("Error inesperado llamando a TUWAYKIFOOD %s %s", method, path)
        raise FoodOwnerClientError("Error inesperado al comunicarse con TUWAYKIFOOD.")


async def list_companies(*, search: str = "", page: int = 1, per_page: int = 15) -> tuple[list[dict], int]:
    data = await _request(
        "GET", "/api/admin/companies", params={"search": search, "page": page, "per_page": per_page}
    )
    items = [_normalize_food_company(c) for c in data.get("items", [])]
    return items, data.get("total", 0)


async def get_company_detail(company_id: int) -> dict | None:
    try:
        data = await _request("GET", f"/api/admin/companies/{company_id}")
    except FoodOwnerClientError:
        return None
    return _normalize_food_company(data)


async def activate(company_id: int) -> dict:
    data = await _request("POST", f"/api/admin/companies/{company_id}/activate")
    return data


async def suspend(company_id: int) -> dict:
    data = await _request("POST", f"/api/admin/companies/{company_id}/suspend")
    return data


async def extend_trial(company_id: int, extra_days: int) -> dict:
    data = await _request(
        "POST", f"/api/admin/companies/{company_id}/extend-trial", json={"extra_days": extra_days}
    )
    return data
