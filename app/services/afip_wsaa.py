"""Cliente WSAA (Web Service de Autenticación y Autorización) de AFIP.

Implementa el flujo completo de autenticación para acceder a los
web services de AFIP (WSFEv1, etc.):

    1. Genera un TRA (Ticket de Requerimiento de Acceso) — XML firmado.
    2. Firma el TRA con CMS/PKCS#7 usando el certificado X.509 y clave
       privada de la empresa.
    3. Envía el CMS firmado al endpoint LoginCms de WSAA vía SOAP.
    4. Parsea la respuesta: Token + Sign (válidos por 12h).
    5. Cachea el resultado para evitar re-autenticaciones innecesarias.

Seguridad:
    - Certificados y claves privadas se almacenan encriptados en DB
      (encrypt_credential/decrypt_credential de app.utils.crypto).
    - La clave privada nunca se escribe a disco — se maneja solo en memoria.
    - Cada empresa tiene su propio par cert+key (multi-tenant).

Endpoints AFIP:
    - Homologación: https://wsaahomo.afip.gov.ar/ws/services/LoginCms
    - Producción:   https://wsaa.afip.gov.ar/ws/services/LoginCms
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from xml.etree import ElementTree as ET

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7

from app.utils.crypto import decrypt_credential

logger = logging.getLogger(__name__)

# ── Constantes ───────────────────────────────────────────────

WSAA_URLS = {
    "sandbox": "https://wsaahomo.afip.gov.ar/ws/services/LoginCms",
    "production": "https://wsaa.afip.gov.ar/ws/services/LoginCms",
}

# Margen de seguridad: renovar 10 minutos antes de expirar
_TOKEN_RENEW_MARGIN_SECONDS = 600

# Timeout para la llamada SOAP a WSAA
_WSAA_TIMEOUT_SECONDS = 30

# Duración del TRA (12 horas como AFIP permite)
_TRA_DURATION_HOURS = 12


# ── Dataclass para credenciales WSAA ─────────────────────────

@dataclass
class WSAACredentials:
    """Token + Sign obtenidos de WSAA para un servicio específico."""
    token: str
    sign: str
    expiration: float  # time.time() cuando expira
    service: str = "wsfe"

    @property
    def is_valid(self) -> bool:
        """True si el token aún es válido (con margen de seguridad)."""
        return time.time() < (self.expiration - _TOKEN_RENEW_MARGIN_SECONDS)


# ── Cache en memoria (por company_id + service) ─────────────

_credentials_cache: dict[str, WSAACredentials] = {}
_cache_locks: dict[str, asyncio.Lock] = {}
_cache_locks_mutex: asyncio.Lock = asyncio.Lock()


async def _get_company_lock(key: str) -> asyncio.Lock:
    """Retorna (o crea) el Lock async para una clave de empresa."""
    async with _cache_locks_mutex:
        if key not in _cache_locks:
            _cache_locks[key] = asyncio.Lock()
        return _cache_locks[key]


def _cache_key(company_id: int, service: str) -> str:
    return f"{company_id}:{service}"


def get_cached_credentials(
    company_id: int,
    service: str = "wsfe",
) -> Optional[WSAACredentials]:
    """Retorna credenciales cacheadas si aún son válidas."""
    key = _cache_key(company_id, service)
    creds = _credentials_cache.get(key)
    if creds and creds.is_valid:
        return creds
    # Expirada o no existe — limpiar
    _credentials_cache.pop(key, None)
    return None


def cache_credentials(
    company_id: int,
    credentials: WSAACredentials,
) -> None:
    """Almacena credenciales en el cache."""
    key = _cache_key(company_id, credentials.service)
    _credentials_cache[key] = credentials


def clear_cache(company_id: int | None = None) -> None:
    """Limpia el cache de credenciales.

    Si company_id es None, limpia TODO el cache.
    """
    if company_id is None:
        _credentials_cache.clear()
    else:
        keys_to_remove = [
            k for k in _credentials_cache if k.startswith(f"{company_id}:")
        ]
        for k in keys_to_remove:
            del _credentials_cache[k]


# ── Generación y firma del TRA ───────────────────────────────

def build_tra_xml(service: str = "wsfe") -> bytes:
    """Construye el TRA (Ticket de Requerimiento de Acceso) como XML.

    El TRA define:
    - Servicio solicitado (wsfe para factura electrónica)
    - Ventana de validez (generationTime → expirationTime)

    Returns:
        Bytes del XML del TRA.
    """
    now = datetime.now(timezone.utc)
    # Generado 5 minutos atrás para tolerar desfase de reloj
    gen_time = now - timedelta(minutes=5)
    exp_time = now + timedelta(hours=_TRA_DURATION_HOURS)

    tra = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<loginTicketRequest>"
        "<header>"
        f"<uniqueId>{int(now.timestamp())}</uniqueId>"
        f'<generationTime>{gen_time.strftime("%Y-%m-%dT%H:%M:%S%z")}</generationTime>'
        f'<expirationTime>{exp_time.strftime("%Y-%m-%dT%H:%M:%S%z")}</expirationTime>'
        "</header>"
        f"<service>{service}</service>"
        "</loginTicketRequest>"
    )
    return tra.encode("utf-8")


def sign_tra(
    tra_xml: bytes,
    certificate_pem: bytes,
    private_key_pem: bytes,
) -> str:
    """Firma el TRA con CMS/PKCS#7 usando el certificado y clave privada.

    AFIP requiere firma CMS detached en formato DER, codificada en Base64.

    Args:
        tra_xml: Contenido XML del TRA.
        certificate_pem: Certificado X.509 en formato PEM.
        private_key_pem: Clave privada RSA en formato PEM.

    Returns:
        String Base64 del CMS firmado (listo para enviar a WSAA).

    Raises:
        ValueError: Si el certificado o clave son inválidos.
    """
    try:
        cert = x509.load_pem_x509_certificate(certificate_pem)
    except Exception as exc:
        raise ValueError(f"Certificado PEM inválido: {exc}") from exc

    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem, password=None
        )
    except Exception as exc:
        raise ValueError(f"Clave privada PEM inválida: {exc}") from exc

    # Firmar con PKCS7 — AFIP requiere Binary + NoAttributes
    try:
        signed_data = (
            pkcs7.PKCS7SignatureBuilder()
            .set_data(tra_xml)
            .add_signer(cert, private_key, hashes.SHA256())
            .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.Binary])
        )
    except Exception as exc:
        raise ValueError(f"Error al firmar CMS: {exc}") from exc

    return base64.b64encode(signed_data).decode("ascii")


# ── Llamada SOAP a WSAA LoginCms ─────────────────────────────

def _build_login_cms_soap(cms_base64: str) -> str:
    """Construye el envelope SOAP para el método LoginCms de WSAA."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        'xmlns:wsaa="http://wsaa.view.sua.dvadac.desein.afip.gov">'
        "<soapenv:Body>"
        "<wsaa:loginCms>"
        f"<wsaa:in0>{cms_base64}</wsaa:in0>"
        "</wsaa:loginCms>"
        "</soapenv:Body>"
        "</soapenv:Envelope>"
    )


def _parse_login_response(response_xml: str) -> WSAACredentials:
    """Parsea la respuesta SOAP de WSAA LoginCms.

    Extrae Token, Sign y expirationTime del loginTicketResponse.

    Args:
        response_xml: XML completo de la respuesta SOAP.

    Returns:
        WSAACredentials con token, sign y tiempo de expiración.

    Raises:
        ValueError: Si la respuesta no contiene los datos esperados.
    """
    try:
        root = ET.fromstring(response_xml)
    except ET.ParseError as exc:
        raise ValueError(f"XML de respuesta WSAA inválido: {exc}") from exc

    # Buscar el contenido de loginCmsReturn (puede estar en diferentes namespaces)
    return_text = None
    for elem in root.iter():
        if "loginCmsReturn" in (elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag):
            return_text = elem.text
            break

    if not return_text:
        # Buscar errores SOAP
        fault_string = ""
        for elem in root.iter():
            tag_local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag_local == "faultstring":
                fault_string = elem.text or ""
                break
        raise ValueError(
            f"WSAA no retornó loginCmsReturn. "
            f"Posible error SOAP: {fault_string or 'desconocido'}"
        )

    # El return contiene un XML embebido (loginTicketResponse)
    try:
        ticket = ET.fromstring(return_text)
    except ET.ParseError as exc:
        raise ValueError(
            f"loginTicketResponse XML inválido: {exc}"
        ) from exc

    # Extraer campos del header del ticket
    token = ""
    sign = ""
    expiration_str = ""

    header = ticket.find("header")
    if header is not None:
        exp_elem = header.find("expirationTime")
        if exp_elem is not None and exp_elem.text:
            expiration_str = exp_elem.text

    credentials = ticket.find("credentials")
    if credentials is not None:
        token_elem = credentials.find("token")
        sign_elem = credentials.find("sign")
        if token_elem is not None and token_elem.text:
            token = token_elem.text
        if sign_elem is not None and sign_elem.text:
            sign = sign_elem.text

    if not token or not sign:
        raise ValueError(
            "WSAA loginTicketResponse no contiene token/sign válidos."
        )

    # Parsear expiración
    expiration_ts = time.time() + (_TRA_DURATION_HOURS * 3600)
    if expiration_str:
        try:
            # AFIP retorna formato ISO con timezone
            exp_dt = datetime.fromisoformat(expiration_str)
            expiration_ts = exp_dt.timestamp()
        except (ValueError, TypeError):
            logger.warning(
                "No se pudo parsear expirationTime de WSAA: %s",
                expiration_str,
            )

    return WSAACredentials(
        token=token,
        sign=sign,
        expiration=expiration_ts,
        service="wsfe",
    )


async def authenticate(
    company_id: int,
    certificate_encrypted: str,
    private_key_encrypted: str,
    environment: str = "sandbox",
    service: str = "wsfe",
) -> WSAACredentials:
    """Autenticación completa contra WSAA de AFIP.

    Flujo:
        1. Verifica cache → si hay credenciales válidas, las retorna.
        2. Desencripta certificado y clave privada desde DB.
        3. Genera TRA XML.
        4. Firma TRA con CMS/PKCS#7.
        5. Envía SOAP a WSAA LoginCms.
        6. Parsea respuesta y cachea credenciales.

    Args:
        company_id: ID de la empresa (para cache multi-tenant).
        certificate_encrypted: Certificado X.509 PEM encriptado (de DB).
        private_key_encrypted: Clave privada RSA PEM encriptada (de DB).
        environment: "sandbox" o "production".
        service: Servicio AFIP a autorizar (default: "wsfe").

    Returns:
        WSAACredentials con token y sign para usar en WSFEv1.

    Raises:
        ValueError: Si los certificados son inválidos o WSAA rechaza.
        ConnectionError: Si no se puede contactar a WSAA.
    """
    key = _cache_key(company_id, service)

    # 1. Fast path: verificar cache sin lock
    cached = get_cached_credentials(company_id, service)
    if cached:
        logger.debug(
            "WSAA: usando token cacheado company_id=%s service=%s",
            company_id, service,
        )
        return cached

    # Slow path: adquirir lock por empresa antes de autenticar
    company_lock = await _get_company_lock(key)
    async with company_lock:
        # Double-check después de adquirir el lock (otro worker puede haber completado)
        cached = get_cached_credentials(company_id, service)
        if cached:
            logger.debug(
                "WSAA: token cacheado post-lock company_id=%s service=%s",
                company_id, service,
            )
            return cached

        logger.info(
            "WSAA: autenticando company_id=%s environment=%s service=%s",
            company_id, environment, service,
        )

        # 2. Desencriptar certificados
        try:
            cert_pem = decrypt_credential(certificate_encrypted)
            key_pem = decrypt_credential(private_key_encrypted)
        except (ValueError, RuntimeError) as exc:
            raise ValueError(
                f"Error desencriptando certificados AFIP: {exc}"
            ) from exc

        # 3. Generar y firmar TRA
        tra_xml = build_tra_xml(service)
        cms_base64 = sign_tra(tra_xml, cert_pem, key_pem)

        # 4. Enviar SOAP a WSAA
        wsaa_url = WSAA_URLS.get(environment, WSAA_URLS["sandbox"])
        soap_envelope = _build_login_cms_soap(cms_base64)

        try:
            async with httpx.AsyncClient(timeout=_WSAA_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    wsaa_url,
                    content=soap_envelope.encode("utf-8"),
                    headers={
                        "Content-Type": "text/xml; charset=utf-8",
                        "SOAPAction": '""',
                    },
                )
        except httpx.TimeoutException:
            raise ConnectionError(
                f"Timeout conectando a WSAA ({wsaa_url}). "
                "AFIP puede estar experimentando demoras."
            )
        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"No se pudo conectar a WSAA ({wsaa_url}): {exc}"
            ) from exc

        if response.status_code != 200:
            raise ValueError(
                f"WSAA retornó HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        # 5. Parsear respuesta y cachear (dentro del lock)
        credentials = _parse_login_response(response.text)
        credentials.service = service
        _credentials_cache[key] = credentials

        logger.info(
            "WSAA: autenticación exitosa company_id=%s, "
            "token válido hasta %s",
            company_id,
            datetime.fromtimestamp(credentials.expiration, tz=timezone.utc)
            .strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

        return credentials
