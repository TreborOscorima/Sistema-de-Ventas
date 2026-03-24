"""Servicio de consulta de documentos fiscales — Patrón Strategy.

Arquitectura:
    DocumentLookupStrategy (ABC)
    ├── PEDocumentLookup   → Perú vía apis.net.pe REST API
    └── ARDocumentLookup   → Argentina vía tangofactura REST (sandbox)
                             / AFIP ws_sr_padron_a5 (producción futura)

    DocumentLookupFactory.get_strategy(country, config) → instancia concreta

    lookup_document() → función principal con caché en DB

Principios:
    - Caché tenant-agnostic: datos fiscales son registros públicos.
    - TTL: RUC/CUIT=24h, DNI=7d, not-found=1h.
    - Fail-safe: si la API externa falla, retorna LookupResult con error.
    - Todas las llamadas van por backend (CORS bloqueado en APIs externas).

Configuración de credenciales:
    - API de consulta RUC/DNI (apis.net.pe): token de PLATAFORMA en env vars
      LOOKUP_API_URL y LOOKUP_API_TOKEN (un token para todos los tenants).
    - API de consulta CUIT (tangofactura): gratuito, sin auth (sandbox).
"""
from __future__ import annotations

import abc
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import httpx
from sqlmodel import select

from app.models.billing import CompanyBillingConfig
from app.models.lookup_cache import DocumentLookupCache
from app.utils.db import get_async_session
from app.utils.timezone import utc_now_naive

logger = logging.getLogger(__name__)

# ── TTLs de caché ──────────────────────────────────────────
CACHE_TTL_RUC_CUIT = timedelta(hours=24)
CACHE_TTL_DNI = timedelta(days=7)
CACHE_TTL_NOT_FOUND = timedelta(hours=1)

# ── Timeouts HTTP ──────────────────────────────────────────
LOOKUP_TIMEOUT_SECONDS = 15

# ── Condiciones IVA Argentina ──────────────────────────────
IVA_CONDITION_CODES = {
    "RI": 1,
    "monotributo": 6,
    "exento": 4,
    "CF": 5,
}

# ── Matriz de tipo de comprobante Argentina ────────────────
# (emisor_iva, receptor_iva) → (letra, CbteTipo)
_AR_CBTE_MATRIX: dict[tuple[str, str], tuple[str, int]] = {
    # Emisor RI
    ("RI", "RI"): ("A", 1),
    ("RI", "monotributo"): ("B", 6),
    ("RI", "exento"): ("B", 6),
    ("RI", "CF"): ("B", 6),
    # Emisor Monotributo → siempre C
    ("monotributo", "RI"): ("C", 11),
    ("monotributo", "monotributo"): ("C", 11),
    ("monotributo", "exento"): ("C", 11),
    ("monotributo", "CF"): ("C", 11),
    # Emisor Exento → siempre C
    ("exento", "RI"): ("C", 11),
    ("exento", "monotributo"): ("C", 11),
    ("exento", "exento"): ("C", 11),
    ("exento", "CF"): ("C", 11),
}


# ═════════════════════════════════════════════════════════════
# RESULT DATACLASS
# ═════════════════════════════════════════════════════════════


@dataclass
class LookupResult:
    """Resultado de una consulta de documento fiscal."""

    found: bool = False
    doc_number: str = ""
    doc_type: str = ""           # "RUC", "DNI", "CUIT"
    legal_name: str = ""         # razón social / denominación
    fiscal_address: str = ""     # dirección fiscal
    status: str = ""             # "ACTIVO", "BAJA", etc.
    condition: str = ""          # "HABIDO", "NO HABIDO" (PE) / "" (AR)
    iva_condition: str = ""      # "" (PE) / "RI", "monotributo", "exento", "CF" (AR)
    iva_condition_code: int = 0  # 0 (PE) / 1,4,5,6 (AR)
    error: str = ""
    raw_data: dict = field(default_factory=dict)


# ═════════════════════════════════════════════════════════════
# ABSTRACT STRATEGY
# ═════════════════════════════════════════════════════════════


class DocumentLookupStrategy(abc.ABC):
    """Interfaz para estrategias de consulta de documentos fiscales."""

    @abc.abstractmethod
    async def lookup(
        self,
        doc_number: str,
        doc_type: str = "",
        config: CompanyBillingConfig | None = None,
    ) -> LookupResult:
        """Consulta un documento fiscal en la entidad correspondiente."""
        ...


# ═════════════════════════════════════════════════════════════
# PERÚ — apis.net.pe REST API
# ═════════════════════════════════════════════════════════════


class PEDocumentLookup(DocumentLookupStrategy):
    """Consulta RUC/DNI en Perú vía apis.net.pe.

    Endpoints:
        GET {base_url}/sunat/ruc?numero={11_dígitos}
        GET {base_url}/sunat/dni?numero={8_dígitos}

    Auth: Bearer token en header Authorization.
    """

    DEFAULT_BASE_URL = "https://api.apis.net.pe/v2"

    async def lookup(
        self,
        doc_number: str,
        doc_type: str = "",
        config: CompanyBillingConfig | None = None,
    ) -> LookupResult:
        doc_number = doc_number.strip()

        # Determinar tipo por longitud
        if len(doc_number) == 11:
            endpoint = "sunat/ruc"
            doc_type = "RUC"
        elif len(doc_number) == 8:
            endpoint = "sunat/dni"
            doc_type = "DNI"
        else:
            return LookupResult(
                error=f"Formato inválido: se esperan 8 (DNI) u 11 (RUC) dígitos, "
                f"se recibieron {len(doc_number)}.",
                doc_number=doc_number,
            )

        # Obtener URL y token de las variables de entorno de PLATAFORMA.
        # Estos son credenciales del servicio TuWaykiApp (no del tenant).
        base_url = (
            os.getenv("LOOKUP_API_URL", "").strip().rstrip("/")
            or self.DEFAULT_BASE_URL
        )
        api_token = os.getenv("LOOKUP_API_TOKEN", "").strip()

        if not api_token:
            return LookupResult(
                error="Servicio de consulta RUC/DNI no disponible. "
                "Contacte al administrador de la plataforma.",
                doc_number=doc_number,
                doc_type=doc_type,
            )

        url = f"{base_url}/{endpoint}"
        headers = {"Authorization": f"Bearer {api_token}"}
        params = {"numero": doc_number}

        try:
            async with httpx.AsyncClient(timeout=LOOKUP_TIMEOUT_SECONDS) as client:
                response = await client.get(url, headers=headers, params=params)

            if response.status_code == 404:
                return LookupResult(
                    found=False,
                    doc_number=doc_number,
                    doc_type=doc_type,
                    error=f"{doc_type} {doc_number} no encontrado.",
                )

            if response.status_code != 200:
                return LookupResult(
                    error=f"Error en API de consulta: HTTP {response.status_code}",
                    doc_number=doc_number,
                    doc_type=doc_type,
                )

            data = response.json()
            return self._parse_response(data, doc_number, doc_type)

        except httpx.TimeoutException:
            return LookupResult(
                error="Timeout al consultar API de documentos.",
                doc_number=doc_number,
                doc_type=doc_type,
            )
        except Exception as exc:
            logger.exception("PEDocumentLookup error: %s", exc)
            return LookupResult(
                error=f"Error de consulta: {type(exc).__name__}",
                doc_number=doc_number,
                doc_type=doc_type,
            )

    def _parse_response(
        self, data: dict, doc_number: str, doc_type: str
    ) -> LookupResult:
        """Parsea la respuesta de apis.net.pe."""
        if doc_type == "RUC":
            legal_name = (
                data.get("nombre")
                or data.get("razonSocial")
                or data.get("nombre_o_razon_social")
                or ""
            )
            fiscal_address = data.get("direccion") or ""
            status = (data.get("estado") or "").upper()
            condition = (data.get("condicion") or "").upper()

            return LookupResult(
                found=True,
                doc_number=doc_number,
                doc_type="RUC",
                legal_name=legal_name,
                fiscal_address=fiscal_address,
                status=status,
                condition=condition,
                raw_data=data,
            )
        else:
            # DNI
            nombre = data.get("nombre") or data.get("nombres") or ""
            apellido_p = data.get("apellidoPaterno") or ""
            apellido_m = data.get("apellidoMaterno") or ""
            full_name = " ".join(
                p for p in [apellido_p, apellido_m, nombre] if p
            ).strip()

            return LookupResult(
                found=True,
                doc_number=doc_number,
                doc_type="DNI",
                legal_name=full_name,
                status="ACTIVO",
                raw_data=data,
            )


# ═════════════════════════════════════════════════════════════
# ARGENTINA — tangofactura REST (sandbox/fallback)
# ═════════════════════════════════════════════════════════════


class ARDocumentLookup(DocumentLookupStrategy):
    """Consulta CUIT en Argentina vía tangofactura REST.

    Endpoint gratuito sin autenticación (sandbox/fallback).
    Para producción con certificado AFIP → futuro: ws_sr_padron_a5 SOAP.

    GET https://afip.tangofactura.com/Rest/GetContribuyente?cuit={CUIT}
    """

    TANGOFACTURA_URL = (
        "https://afip.tangofactura.com/Rest/GetContribuyente"
    )

    async def lookup(
        self,
        doc_number: str,
        doc_type: str = "",
        config: CompanyBillingConfig | None = None,
    ) -> LookupResult:
        doc_number = doc_number.strip().replace("-", "")

        if len(doc_number) != 11 or not doc_number.isdigit():
            return LookupResult(
                error="CUIT inválido: debe tener 11 dígitos numéricos.",
                doc_number=doc_number,
                doc_type="CUIT",
            )

        try:
            async with httpx.AsyncClient(timeout=LOOKUP_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    self.TANGOFACTURA_URL,
                    params={"cuit": doc_number},
                )

            if response.status_code != 200:
                return LookupResult(
                    error=f"Error consultando CUIT: HTTP {response.status_code}",
                    doc_number=doc_number,
                    doc_type="CUIT",
                )

            data = response.json()
            return self._parse_response(data, doc_number)

        except httpx.TimeoutException:
            return LookupResult(
                error="Timeout al consultar servicio de CUIT.",
                doc_number=doc_number,
                doc_type="CUIT",
            )
        except Exception as exc:
            logger.exception("ARDocumentLookup error: %s", exc)
            return LookupResult(
                error=f"Error de consulta: {type(exc).__name__}",
                doc_number=doc_number,
                doc_type="CUIT",
            )

    def _parse_response(self, data: dict, doc_number: str) -> LookupResult:
        """Parsea la respuesta de tangofactura."""
        # tangofactura retorna: Denominacion, IdCondicionIVA, etc.
        denominacion = data.get("Denominacion") or data.get("denominacion") or ""
        domicilio = data.get("Domicilio") or data.get("domicilio") or ""

        if not denominacion:
            return LookupResult(
                found=False,
                doc_number=doc_number,
                doc_type="CUIT",
                error=f"CUIT {doc_number} no encontrado.",
            )

        # Determinar condición IVA
        iva_id = data.get("IdCondicionIVA") or data.get("idCondicionIVA") or 0
        try:
            iva_id = int(iva_id)
        except (TypeError, ValueError):
            iva_id = 0

        iva_condition, iva_code = self._map_iva_condition(iva_id)

        estado_clave = data.get("EstadoClave") or data.get("estadoClave") or ""

        return LookupResult(
            found=True,
            doc_number=doc_number,
            doc_type="CUIT",
            legal_name=denominacion,
            fiscal_address=domicilio,
            status=str(estado_clave).upper() if estado_clave else "ACTIVO",
            iva_condition=iva_condition,
            iva_condition_code=iva_code,
            raw_data=data,
        )

    @staticmethod
    def _map_iva_condition(iva_id: int) -> tuple[str, int]:
        """Mapea IdCondicionIVA de AFIP a nombre interno."""
        mapping = {
            1: ("RI", 1),           # IVA Responsable Inscripto
            4: ("exento", 4),       # IVA Sujeto Exento
            5: ("CF", 5),           # Consumidor Final
            6: ("monotributo", 6),  # Responsable Monotributo
            11: ("RI", 1),          # RI - Agente de Percepción
            13: ("monotributo", 6), # Monotributista Social
        }
        return mapping.get(iva_id, ("CF", 5))


# ═════════════════════════════════════════════════════════════
# FACTORY
# ═════════════════════════════════════════════════════════════


class DocumentLookupFactory:
    """Fábrica que selecciona la estrategia según el país."""

    _strategies: dict[str, type[DocumentLookupStrategy]] = {
        "PE": PEDocumentLookup,
        "AR": ARDocumentLookup,
    }

    @classmethod
    def get_strategy(
        cls,
        country: str,
        config: CompanyBillingConfig | None = None,
    ) -> DocumentLookupStrategy:
        strategy_cls = cls._strategies.get(country)
        if strategy_cls is None:
            raise ValueError(f"País no soportado para consulta: {country}")
        return strategy_cls()


# ═════════════════════════════════════════════════════════════
# UTILIDAD: DETERMINACIÓN DE COMPROBANTE ARGENTINA
# ═════════════════════════════════════════════════════════════


def determine_ar_cbte_tipo(
    emisor_iva: str,
    receptor_iva: str,
) -> tuple[str, int]:
    """Determina el tipo de comprobante argentino según la matriz IVA.

    Args:
        emisor_iva: condición IVA del emisor ("RI", "monotributo", "exento")
        receptor_iva: condición IVA del receptor ("RI", "monotributo", "exento", "CF")

    Returns:
        (letra, CbteTipo): ej. ("A", 1), ("B", 6), ("C", 11)
    """
    key = (emisor_iva.strip(), receptor_iva.strip())
    result = _AR_CBTE_MATRIX.get(key)
    if result is not None:
        return result
    # Fallback: si el emisor es RI y no matchea → Factura B (conservador)
    if emisor_iva == "RI":
        return ("B", 6)
    # Monotributo/Exento → siempre C
    return ("C", 11)


# ═════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL CON CACHÉ
# ═════════════════════════════════════════════════════════════


def _get_ttl(doc_type: str, found: bool) -> timedelta:
    """Retorna el TTL de caché según tipo de documento y resultado."""
    if not found:
        return CACHE_TTL_NOT_FOUND
    if doc_type == "DNI":
        return CACHE_TTL_DNI
    return CACHE_TTL_RUC_CUIT


async def lookup_document(
    doc_number: str,
    country: str,
    config: CompanyBillingConfig | None = None,
    force_refresh: bool = False,
) -> LookupResult:
    """Consulta un documento fiscal con caché en DB.

    Flujo:
        1. Validar formato básico.
        2. Buscar en caché (DocumentLookupCache).
        3. Si miss/stale/force → llamar strategy externa.
        4. Guardar en caché.
        5. Retornar resultado.

    Args:
        doc_number: número de documento (RUC/DNI/CUIT).
        country: código país ("PE" / "AR").
        config: config de billing (para API tokens).
        force_refresh: ignorar caché y consultar API externa.

    Returns:
        LookupResult con los datos fiscales del contribuyente.
    """
    doc_number = (doc_number or "").strip().replace("-", "")

    if not doc_number.isdigit():
        return LookupResult(
            error="El número de documento debe contener solo dígitos.",
            doc_number=doc_number,
        )

    # 1. Buscar en caché
    if not force_refresh:
        cached = await _get_from_cache(country, doc_number)
        if cached is not None:
            return cached

    # 2. Llamar strategy externa
    try:
        strategy = DocumentLookupFactory.get_strategy(country, config)
    except ValueError as exc:
        return LookupResult(error=str(exc), doc_number=doc_number)

    result = await strategy.lookup(doc_number, config=config)

    # 3. Guardar en caché (incluso resultados no encontrados, para cache negativo)
    if not result.error or not result.found:
        await _save_to_cache(country, result)

    return result


async def _get_from_cache(
    country: str, doc_number: str
) -> LookupResult | None:
    """Busca un resultado en caché. Retorna None si miss o expirado."""
    try:
        async with get_async_session() as session:
            cached = (
                await session.exec(
                    select(DocumentLookupCache)
                    .where(DocumentLookupCache.country == country)
                    .where(DocumentLookupCache.doc_number == doc_number)
                )
            ).first()

            if cached is None:
                return None

            ttl = _get_ttl(cached.doc_type, bool(cached.legal_name))
            if utc_now_naive() - cached.fetched_at > ttl:
                return None  # Expirado

            return LookupResult(
                found=bool(cached.legal_name),
                doc_number=cached.doc_number,
                doc_type=cached.doc_type,
                legal_name=cached.legal_name,
                fiscal_address=cached.fiscal_address,
                status=cached.status,
                condition=cached.condition,
                iva_condition=cached.iva_condition,
                iva_condition_code=cached.iva_condition_code,
                raw_data=json.loads(cached.raw_json) if cached.raw_json else {},
            )
    except Exception as exc:
        logger.warning("Cache read error: %s", exc)
        return None


async def _save_to_cache(country: str, result: LookupResult) -> None:
    """Guarda o actualiza un resultado en caché."""
    try:
        async with get_async_session() as session:
            existing = (
                await session.exec(
                    select(DocumentLookupCache)
                    .where(DocumentLookupCache.country == country)
                    .where(DocumentLookupCache.doc_number == result.doc_number)
                )
            ).first()

            if existing:
                existing.doc_type = result.doc_type
                existing.legal_name = result.legal_name
                existing.fiscal_address = result.fiscal_address
                existing.status = result.status
                existing.condition = result.condition
                existing.iva_condition = result.iva_condition
                existing.iva_condition_code = result.iva_condition_code
                existing.raw_json = json.dumps(result.raw_data, default=str)
                existing.fetched_at = utc_now_naive()
                session.add(existing)
            else:
                cache_entry = DocumentLookupCache(
                    country=country,
                    doc_type=result.doc_type,
                    doc_number=result.doc_number,
                    legal_name=result.legal_name,
                    fiscal_address=result.fiscal_address,
                    status=result.status,
                    condition=result.condition,
                    iva_condition=result.iva_condition,
                    iva_condition_code=result.iva_condition_code,
                    raw_json=json.dumps(result.raw_data, default=str),
                    fetched_at=utc_now_naive(),
                )
                session.add(cache_entry)

            await session.commit()
    except Exception as exc:
        logger.warning("Cache write error: %s", exc)
