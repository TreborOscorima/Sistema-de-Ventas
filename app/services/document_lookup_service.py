"""Servicio de consulta de documentos fiscales — Patrón Strategy.

Arquitectura:
    DocumentLookupStrategy (ABC)
    ├── PEDocumentLookup    → Perú vía apis.net.pe (RUC / DNI)
    └── ARDocumentLookup    → Argentina vía tangofactura (CUIT)

    DocumentLookupFactory.get_strategy(country, config?) → instancia concreta

    lookup_document()      → función de orquestación que:
        1. Valida formato del documento
        2. Llama a la API externa vía strategy
        3. Retorna LookupResult

Principios:
    - El servicio es un **cliente de API puro**: no accede a la DB.
    - La lógica de caché (DocumentLookupCache) vive en el Reflex state,
      que tiene acceso a ``rx.session()``.
    - NoOp: si el país no está soportado, se retorna error inmediato.
    - Fail-safe: nunca lanza excepciones — siempre devuelve LookupResult
      con el campo ``error`` informado.

Configuración de credenciales:
    - API de consulta RUC/DNI (apis.net.pe): token de PLATAFORMA en
      ``CompanyBillingConfig.lookup_api_url`` y ``lookup_api_token``,
      o como fallback en env vars ``LOOKUP_API_URL`` / ``LOOKUP_API_TOKEN``
      (un token para todos los tenants).
    - API de consulta CUIT (tangofactura): gratuito, sin auth (sandbox).
"""
from __future__ import annotations

import abc
import logging
import os
from dataclasses import dataclass, field
from datetime import timedelta

import httpx

logger = logging.getLogger(__name__)

# ── TTLs de caché (exportados para el state que gestiona DocumentLookupCache) ──
CACHE_TTL_RUC = timedelta(hours=24)
CACHE_TTL_DNI = timedelta(days=7)
CACHE_TTL_CUIT = timedelta(hours=24)
CACHE_TTL_NOT_FOUND = timedelta(hours=1)

# ── Timeouts HTTP ──────────────────────────────────────────
PE_API_TIMEOUT_SECONDS = 10
AR_API_TIMEOUT_SECONDS = 10

# ── Condiciones IVA Argentina (referencia para otros módulos) ──
IVA_CONDITION_CODES: dict[str, int] = {
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
# RESULTADO DE CONSULTA
# ═════════════════════════════════════════════════════════════


@dataclass
class LookupResult:
    """Resultado de consulta de documento fiscal."""

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
# ABSTRACT BASE CLASS
# ═════════════════════════════════════════════════════════════


class DocumentLookupStrategy(abc.ABC):
    """Interfaz abstracta para estrategias de consulta de documentos.

    Cada implementación encapsula la comunicación con un servicio
    de consulta fiscal específico (apis.net.pe, tangofactura).
    """

    @abc.abstractmethod
    async def lookup(self, doc_number: str, doc_type: str = "") -> LookupResult:
        """Consulta un documento fiscal en la API externa.

        Args:
            doc_number: número de documento (solo dígitos).
            doc_type: tipo de documento hint ("RUC", "DNI", "CUIT").
                      Para PE se auto-detecta por longitud si está vacío.

        Returns:
            LookupResult con los datos del contribuyente o error.
        """
        ...


# ═════════════════════════════════════════════════════════════
# PERÚ — apis.net.pe (RUC / DNI)
# ═════════════════════════════════════════════════════════════


class PEDocumentLookup(DocumentLookupStrategy):
    """Consulta de RUC/DNI para Perú vía apis.net.pe.

    Endpoints:
        - RUC (11 dígitos): GET {base_url}/sunat/ruc?numero={ruc}
        - DNI (8 dígitos):  GET {base_url}/reniec/dni?numero={dni}

    Auth: Bearer token opcional (sin token: rate-limit bajo).

    Las credenciales se inyectan por constructor (desde
    CompanyBillingConfig o variables de entorno).
    """

    DEFAULT_BASE_URL = "https://api.apis.net.pe/v2"

    def __init__(
        self,
        api_url: str = "",
        api_token: str = "",
    ):
        self.api_url = (api_url or "").rstrip("/") or self.DEFAULT_BASE_URL
        self.api_token = api_token or ""

    async def lookup(self, doc_number: str, doc_type: str = "") -> LookupResult:
        doc_number = doc_number.strip().replace("-", "")

        # D1-02: defensa en profundidad — si el caller directo (bypass
        # lookup_document) pasa algo no-numérico, frenamos aquí antes de
        # construir la URL.
        if not doc_number.isdigit():
            return LookupResult(
                error="El número de documento debe contener solo dígitos.",
                doc_number=doc_number,
            )

        # Auto-detectar tipo por longitud
        if len(doc_number) == 11:
            doc_type = "RUC"
            endpoint = f"{self.api_url}/sunat/ruc"
        elif len(doc_number) == 8:
            doc_type = "DNI"
            endpoint = f"{self.api_url}/reniec/dni"
        else:
            return LookupResult(
                error=(
                    f"Número debe tener 8 (DNI) u 11 (RUC) dígitos, "
                    f"tiene {len(doc_number)}."
                ),
                doc_number=doc_number,
            )

        headers: dict[str, str] = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        try:
            async with httpx.AsyncClient(timeout=PE_API_TIMEOUT_SECONDS) as client:
                resp = await client.get(
                    endpoint,
                    params={"numero": doc_number},
                    headers=headers,
                )

            if resp.status_code == 404:
                return LookupResult(
                    doc_number=doc_number,
                    doc_type=doc_type,
                    error="Documento no encontrado.",
                )

            if resp.status_code == 422:
                return LookupResult(
                    doc_number=doc_number,
                    doc_type=doc_type,
                    error="Número de documento inválido.",
                )

            resp.raise_for_status()
            data: dict = resp.json()

            if doc_type == "RUC":
                return LookupResult(
                    found=True,
                    doc_number=doc_number,
                    doc_type="RUC",
                    legal_name=data.get("razonSocial", data.get("nombre", "")),
                    fiscal_address=data.get("direccion", ""),
                    status=data.get("estado", ""),
                    condition=data.get("condicion", ""),
                    raw_data=data,
                )

            # DNI
            nombre_completo = (
                f"{data.get('nombres', '')} "
                f"{data.get('apellidoPaterno', '')} "
                f"{data.get('apellidoMaterno', '')}"
            ).strip()
            return LookupResult(
                found=True,
                doc_number=doc_number,
                doc_type="DNI",
                legal_name=nombre_completo,
                raw_data=data,
            )

        except httpx.TimeoutException:
            return LookupResult(
                doc_number=doc_number,
                doc_type=doc_type,
                error="Timeout al consultar el servicio. Intente nuevamente.",
            )
        except httpx.HTTPStatusError as e:
            logger.warning(
                "PE lookup HTTP error %s for %s", e.response.status_code, doc_number
            )
            return LookupResult(
                doc_number=doc_number,
                doc_type=doc_type,
                error=f"Error del servicio (HTTP {e.response.status_code}).",
            )
        except Exception:
            logger.exception("PE lookup unexpected error for %s", doc_number)
            return LookupResult(
                doc_number=doc_number,
                doc_type=doc_type,
                error="Error inesperado al consultar el documento.",
            )


# ═════════════════════════════════════════════════════════════
# ARGENTINA — tangofactura (CUIT)
# ═════════════════════════════════════════════════════════════


class ARDocumentLookup(DocumentLookupStrategy):
    """Consulta de CUIT para Argentina vía tangofactura / AFIP.

    Endpoint gratuito sin autenticación (sandbox/fallback).
    Para producción con certificado AFIP: futuro ws_sr_padron_a5 SOAP.

    GET https://afip.tangofactura.com/Rest/GetContribuyente?cuit={CUIT}

    Respuesta relevante:
        - Denominacion: razón social
        - Domicilio: domicilio fiscal
        - tipoResponsable / IdCondicionIVA: condición IVA
        - errorGetData: True si no se encontró
        - EstadoClave: estado de la clave fiscal
    """

    TANGOFACTURA_URL = (
        "https://afip.tangofactura.com/Rest/GetContribuyente"
    )

    def __init__(
        self,
        api_url: str = "",
    ):
        self.api_url = api_url or self.TANGOFACTURA_URL

    async def lookup(self, doc_number: str, doc_type: str = "") -> LookupResult:
        doc_number = doc_number.strip().replace("-", "")

        if len(doc_number) != 11:
            return LookupResult(error="El CUIT debe tener 11 dígitos.")

        try:
            async with httpx.AsyncClient(timeout=AR_API_TIMEOUT_SECONDS) as client:
                resp = await client.get(
                    self.api_url,
                    params={"cuit": doc_number},
                )

            if resp.status_code == 404:
                return LookupResult(
                    doc_number=doc_number,
                    doc_type="CUIT",
                    error="CUIT no encontrado.",
                )

            resp.raise_for_status()
            data: dict = resp.json()

            # tangofactura retorna errorGetData = True cuando no encuentra
            if data.get("errorGetData"):
                return LookupResult(
                    doc_number=doc_number,
                    doc_type="CUIT",
                    error="CUIT no encontrado en AFIP.",
                )

            # Mapear condición IVA (soportar ambos formatos de respuesta)
            iva_raw = (data.get("tipoResponsable") or "").strip()
            if iva_raw:
                iva_condition, iva_code = _map_ar_iva_condition(iva_raw)
            else:
                # Fallback: usar IdCondicionIVA numérico
                iva_id = data.get("IdCondicionIVA") or data.get("idCondicionIVA") or 0
                try:
                    iva_id = int(iva_id)
                except (TypeError, ValueError):
                    iva_id = 0
                iva_condition, iva_code = _map_ar_iva_condition_by_id(iva_id)

            estado_clave = data.get("EstadoClave") or data.get("estadoClave") or ""

            return LookupResult(
                found=True,
                doc_number=doc_number,
                doc_type="CUIT",
                legal_name=data.get("Denominacion", data.get("denominacion", "")),
                fiscal_address=data.get("Domicilio", data.get("domicilio", "")),
                status=str(estado_clave).upper() if estado_clave else "ACTIVO",
                iva_condition=iva_condition,
                iva_condition_code=iva_code,
                raw_data=data,
            )

        except httpx.TimeoutException:
            return LookupResult(
                doc_number=doc_number,
                doc_type="CUIT",
                error="Timeout al consultar AFIP. Intente nuevamente.",
            )
        except httpx.HTTPStatusError as e:
            logger.warning(
                "AR lookup HTTP error %s for %s", e.response.status_code, doc_number
            )
            return LookupResult(
                doc_number=doc_number,
                doc_type="CUIT",
                error=f"Error del servicio (HTTP {e.response.status_code}).",
            )
        except Exception:
            logger.exception("AR lookup unexpected error for %s", doc_number)
            return LookupResult(
                doc_number=doc_number,
                doc_type="CUIT",
                error="Error inesperado al consultar el CUIT.",
            )


# ═════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════


def _map_ar_iva_condition(raw: str) -> tuple[str, int]:
    """Mapea la condición IVA de AFIP (texto) a (condition_normalizada, código).

    Códigos AFIP estándar:
        1 = Responsable Inscripto (RI)
        4 = Exento
        5 = Consumidor Final (CF)
        6 = Monotributo
    """
    raw_lower = raw.lower()

    if "responsable inscripto" in raw_lower or raw_lower == "ri":
        return "RI", 1
    if "monotributo" in raw_lower:
        return "monotributo", 6
    if "exento" in raw_lower:
        return "exento", 4
    if "no responsable" in raw_lower or "consumidor final" in raw_lower:
        return "CF", 5

    # Desconocido: preservar el texto original
    return raw or "desconocido", 0


def _map_ar_iva_condition_by_id(iva_id: int) -> tuple[str, int]:
    """Mapea IdCondicionIVA numérico de AFIP a (condition, código)."""
    mapping: dict[int, tuple[str, int]] = {
        1: ("RI", 1),           # IVA Responsable Inscripto
        4: ("exento", 4),       # IVA Sujeto Exento
        5: ("CF", 5),           # Consumidor Final
        6: ("monotributo", 6),  # Responsable Monotributo
        11: ("RI", 1),          # RI - Agente de Percepción
        13: ("monotributo", 6), # Monotributista Social
    }
    return mapping.get(iva_id, ("CF", 5))


def determine_ar_cbte_tipo(
    emisor_iva: str,
    receptor_iva: str,
) -> tuple[str, int]:
    """Determina el tipo de factura argentina (A/B/C) según condiciones IVA.

    Reglas:
        - Emisor RI → Receptor RI  = Factura A (CbteTipo 1)
        - Emisor RI → Otro         = Factura B (CbteTipo 6)
        - Emisor Monotributo/Exento = Factura C (CbteTipo 11)

    Args:
        emisor_iva: condición IVA del emisor ("RI", "monotributo", "exento").
        receptor_iva: condición IVA del receptor ("RI", "monotributo", "exento", "CF").

    Returns:
        Tupla (letra, CbteTipo_code) para AFIP.
    """
    key = (emisor_iva.strip(), receptor_iva.strip())
    result = _AR_CBTE_MATRIX.get(key)
    if result is not None:
        return result
    # Fallback: si el emisor es RI y no matchea → Factura B (conservador)
    if emisor_iva.strip() == "RI":
        return "B", 6
    # Monotributo/Exento → siempre C
    return "C", 11


def get_cache_ttl(doc_type: str, found: bool) -> timedelta:
    """Retorna el TTL de caché según tipo de documento y resultado.

    Exportado para uso en el Reflex state que gestiona
    DocumentLookupCache.

    Args:
        doc_type: "RUC", "DNI", o "CUIT".
        found: si el documento fue encontrado o no.

    Returns:
        timedelta con el TTL correspondiente.
    """
    if not found:
        return CACHE_TTL_NOT_FOUND
    if doc_type == "DNI":
        return CACHE_TTL_DNI
    if doc_type == "CUIT":
        return CACHE_TTL_CUIT
    return CACHE_TTL_RUC  # RUC y default


# ═════════════════════════════════════════════════════════════
# FACTORY
# ═════════════════════════════════════════════════════════════


# País normalizado → aliases aceptados
_COUNTRY_ALIASES: dict[str, str] = {
    "PE": "PE",
    "PER": "PE",
    "PERU": "PE",
    "PERÚ": "PE",
    "AR": "AR",
    "ARG": "AR",
    "ARGENTINA": "AR",
}


class DocumentLookupFactory:
    """Fábrica que selecciona la estrategia de consulta según el país.

    Decisión:
        country == "PE" → PEDocumentLookup
        country == "AR" → ARDocumentLookup
        otro            → ValueError
    """

    _strategies: dict[str, type[DocumentLookupStrategy]] = {
        "PE": PEDocumentLookup,
        "AR": ARDocumentLookup,
    }

    @classmethod
    def get_strategy(
        cls,
        country: str,
        config: object | None = None,
    ) -> DocumentLookupStrategy:
        """Instancia la estrategia correcta según el país.

        Args:
            country: código de país (PE, AR, o alias).
            config: CompanyBillingConfig opcional — se usa para extraer
                    lookup_api_url / lookup_api_token en Perú.

        Returns:
            Instancia concreta de DocumentLookupStrategy.

        Raises:
            ValueError: si el país no está soportado.
        """
        country_key = _COUNTRY_ALIASES.get((country or "").strip().upper(), "")

        if country_key == "PE":
            # Binding atómico: URL y token DEBEN provenir del mismo origen
            # (config ó env). Nunca mezclar — evita exfiltrar el token de
            # plataforma hacia una URL controlada por el tenant.
            api_url = ""
            api_token = ""
            config_url = ""
            config_token = ""
            if config is not None:
                config_url = (getattr(config, "lookup_api_url", "") or "").strip()
                config_token = (getattr(config, "lookup_api_token", "") or "").strip()

            if config_url or config_token:
                # Origen = config (aunque token esté vacío, NO hacer fallback).
                api_url = config_url
                api_token = config_token
            else:
                # Origen = env (par completo).
                api_url = os.getenv("LOOKUP_API_URL", "").strip()
                api_token = os.getenv("LOOKUP_API_TOKEN", "").strip()

            return PEDocumentLookup(
                api_url=api_url,
                api_token=api_token,
            )

        if country_key == "AR":
            return ARDocumentLookup()

        raise ValueError(
            f"País '{country}' no soportado para consulta de documentos."
        )


# ═════════════════════════════════════════════════════════════
# FUNCIÓN DE ORQUESTACIÓN (API pura, sin acceso a DB)
# ═════════════════════════════════════════════════════════════


async def lookup_document(
    doc_number: str,
    country: str,
    config: object | None = None,
) -> LookupResult:
    """Consulta un documento fiscal en la API externa.

    Función principal de entrada al servicio. Valida formato,
    selecciona la strategy vía factory, y retorna el resultado.

    **No accede a la base de datos.** La lógica de caché
    (DocumentLookupCache) se gestiona en el Reflex state que
    invoca esta función.

    Args:
        doc_number: número de documento (RUC, DNI o CUIT).
        country: código de país ("PE", "AR", o alias).
        config: CompanyBillingConfig opcional para API URLs/tokens.

    Returns:
        LookupResult con datos del contribuyente o error descriptivo.
    """
    doc_number = (doc_number or "").strip().replace("-", "")
    country_key = _COUNTRY_ALIASES.get((country or "").strip().upper(), "")

    # ── Validaciones básicas ──────────────────────────────────
    if not doc_number or not doc_number.isdigit():
        return LookupResult(
            error="El número de documento debe contener solo dígitos.",
            doc_number=doc_number,
        )

    if not country_key:
        return LookupResult(
            error=f"País '{country}' no soportado.",
            doc_number=doc_number,
        )

    # Validar longitud según país antes de llamar a la API
    if country_key == "PE":
        if len(doc_number) not in (8, 11):
            return LookupResult(
                error=(
                    "Para Perú, el documento debe tener "
                    "8 (DNI) u 11 (RUC) dígitos."
                ),
                doc_number=doc_number,
            )
    elif country_key == "AR":
        if len(doc_number) != 11:
            return LookupResult(
                error="El CUIT debe tener 11 dígitos.",
                doc_number=doc_number,
            )

    # ── Llamar a la API externa vía strategy ──────────────────
    try:
        strategy = DocumentLookupFactory.get_strategy(country_key, config)
        result = await strategy.lookup(doc_number)
    except ValueError as e:
        return LookupResult(error=str(e), doc_number=doc_number)
    except Exception:
        logger.exception("Lookup failed for %s/%s", country_key, doc_number)
        return LookupResult(
            error="Error al consultar el documento.",
            doc_number=doc_number,
        )

    return result
