"""Cliente WSFEv1 (Web Service de Factura Electrónica v1) de AFIP.

Implementa las operaciones necesarias para emitir comprobantes
electrónicos ante AFIP:

    - FECompUltimoAutorizado: obtiene último comprobante autorizado.
    - FECAESolicitar: solicita CAE para un comprobante nuevo.
    - FEParamGetTiposCbte: consulta tipos de comprobante (diagnóstico).

Arquitectura:
    Usa httpx para las llamadas SOAP (sin dependencia de zeep/suds)
    con envelopes XML construidos manualmente — más liviano y
    predecible que un cliente WSDL genérico.

Endpoints AFIP:
    - Homologación: https://wswhomo.afip.gov.ar/wsfev1/service.asmx
    - Producción:   https://servicios1.afip.gov.ar/wsfev1/service.asmx

Multi-tenant:
    Cada llamada recibe token/sign de WSAA + CUIT del emisor,
    por lo que múltiples empresas pueden operar concurrentemente.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

# ── Constantes ───────────────────────────────────────────────

WSFE_URLS = {
    "sandbox": "https://wswhomo.afip.gov.ar/wsfev1/service.asmx",
    "production": "https://servicios1.afip.gov.ar/wsfev1/service.asmx",
}

_WSFE_NAMESPACE = "http://ar.gov.afip.dif.FEV1/"
_WSFE_TIMEOUT_SECONDS = 30


# ── Dataclasses de resultado ─────────────────────────────────

@dataclass
class CAEResult:
    """Resultado de FECAESolicitar."""
    success: bool
    cae: str = ""
    cae_fch_vto: str = ""  # Formato YYYYMMDD
    cbte_nro: int = 0
    resultado: str = ""    # "A" = Aprobado, "R" = Rechazado, "O" = Observado
    errors: list[str] = None
    observations: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.observations is None:
            self.observations = []


@dataclass
class UltimoAutorizadoResult:
    """Resultado de FECompUltimoAutorizado."""
    success: bool
    cbte_nro: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


# ── SOAP Helpers ─────────────────────────────────────────────

def _soap_envelope(method: str, body_content: str) -> str:
    """Construye un envelope SOAP para WSFEv1."""
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" '
        f'xmlns:wsfe="{_WSFE_NAMESPACE}">'
        "<soap:Body>"
        f"<wsfe:{method}>"
        f"{body_content}"
        f"</wsfe:{method}>"
        "</soap:Body>"
        "</soap:Envelope>"
    )


def _auth_xml(token: str, sign: str, cuit: int) -> str:
    """Bloque XML de autenticación para WSFEv1."""
    return (
        "<wsfe:Auth>"
        f"<wsfe:Token>{token}</wsfe:Token>"
        f"<wsfe:Sign>{sign}</wsfe:Sign>"
        f"<wsfe:Cuit>{cuit}</wsfe:Cuit>"
        "</wsfe:Auth>"
    )


def _find_text(root: ET.Element, path_parts: list[str]) -> str:
    """Busca texto en un XML ignorando namespaces."""
    current = root
    for part in path_parts:
        found = None
        for child in current:
            tag_local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag_local == part:
                found = child
                break
        if found is None:
            return ""
        current = found
    return current.text or ""


def _find_element(root: ET.Element, path_parts: list[str]) -> Optional[ET.Element]:
    """Busca un elemento en XML ignorando namespaces."""
    current = root
    for part in path_parts:
        found = None
        for child in current:
            tag_local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag_local == part:
                found = child
                break
        if found is None:
            return None
        current = found
    return current


def _extract_errors(result_elem: ET.Element) -> list[str]:
    """Extrae mensajes de error del bloque Errors de WSFEv1."""
    errors = []
    errors_block = _find_element(result_elem, ["Errors"])
    if errors_block is not None:
        for err in errors_block:
            tag_local = err.tag.split("}")[-1] if "}" in err.tag else err.tag
            if tag_local == "Err":
                code = _find_text(err, ["Code"])
                msg = _find_text(err, ["Msg"])
                errors.append(f"[{code}] {msg}" if code else msg)
    return errors


def _extract_observations(det_elem: ET.Element) -> list[str]:
    """Extrae observaciones del bloque Observaciones."""
    observations = []
    obs_block = _find_element(det_elem, ["Observaciones"])
    if obs_block is not None:
        for obs in obs_block:
            tag_local = obs.tag.split("}")[-1] if "}" in obs.tag else obs.tag
            if tag_local == "Obs":
                code = _find_text(obs, ["Code"])
                msg = _find_text(obs, ["Msg"])
                observations.append(f"[{code}] {msg}" if code else msg)
    return observations


async def _soap_call(
    url: str,
    soap_action: str,
    envelope: str,
) -> ET.Element:
    """Ejecuta una llamada SOAP y retorna el XML de respuesta parseado.

    Raises:
        ConnectionError: Si no se puede contactar al servidor.
        ValueError: Si la respuesta no es XML válido o contiene un SOAP Fault.
    """
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"{_WSFE_NAMESPACE}{soap_action}"',
    }

    try:
        async with httpx.AsyncClient(timeout=_WSFE_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                content=envelope.encode("utf-8"),
                headers=headers,
            )
    except httpx.TimeoutException:
        raise ConnectionError(
            f"Timeout conectando a WSFEv1 ({url}). "
            "AFIP puede estar experimentando demoras."
        )
    except httpx.ConnectError as exc:
        raise ConnectionError(
            f"No se pudo conectar a WSFEv1 ({url}): {exc}"
        ) from exc

    if response.status_code != 200:
        raise ValueError(
            f"WSFEv1 retornó HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as exc:
        raise ValueError(f"Respuesta SOAP inválida: {exc}") from exc

    # Verificar SOAP Fault
    for elem in root.iter():
        tag_local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag_local == "Fault":
            fault_string = _find_text(elem, ["faultstring"])
            raise ValueError(f"SOAP Fault de AFIP: {fault_string}")

    return root


# ── FECompUltimoAutorizado ───────────────────────────────────

async def fe_comp_ultimo_autorizado(
    token: str,
    sign: str,
    cuit: int,
    punto_venta: int,
    cbte_tipo: int,
    environment: str = "sandbox",
) -> UltimoAutorizadoResult:
    """Consulta el último comprobante autorizado para un tipo y punto de venta.

    Esto es necesario para verificar la secuencia numérica antes de emitir
    un comprobante nuevo (AFIP no acepta saltos de numeración).

    Args:
        token: Token de WSAA.
        sign: Sign de WSAA.
        cuit: CUIT del emisor (11 dígitos como int).
        punto_venta: Punto de venta AFIP (1-99998).
        cbte_tipo: Código de tipo de comprobante AFIP.
        environment: "sandbox" o "production".

    Returns:
        UltimoAutorizadoResult con el último número autorizado.
    """
    url = WSFE_URLS.get(environment, WSFE_URLS["sandbox"])

    body = (
        f"{_auth_xml(token, sign, cuit)}"
        f"<wsfe:PtoVta>{punto_venta}</wsfe:PtoVta>"
        f"<wsfe:CbteTipo>{cbte_tipo}</wsfe:CbteTipo>"
    )
    envelope = _soap_envelope("FECompUltimoAutorizado", body)

    try:
        root = await _soap_call(url, "FECompUltimoAutorizado", envelope)
    except (ConnectionError, ValueError) as exc:
        return UltimoAutorizadoResult(
            success=False,
            errors=[str(exc)],
        )

    # Buscar FECompUltimoAutorizadoResult en el Body
    result_elem = None
    for elem in root.iter():
        tag_local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag_local == "FECompUltimoAutorizadoResult":
            result_elem = elem
            break

    if result_elem is None:
        return UltimoAutorizadoResult(
            success=False,
            errors=["No se encontró FECompUltimoAutorizadoResult en respuesta."],
        )

    cbte_nro_str = _find_text(result_elem, ["CbteNro"])
    errors = _extract_errors(result_elem)

    cbte_nro = 0
    try:
        cbte_nro = int(cbte_nro_str) if cbte_nro_str else 0
    except (ValueError, TypeError):
        pass

    return UltimoAutorizadoResult(
        success=len(errors) == 0,
        cbte_nro=cbte_nro,
        errors=errors,
    )


# ── FECAESolicitar ───────────────────────────────────────────

@dataclass
class FECAERequest:
    """Datos necesarios para FECAESolicitar."""
    # Cabecera
    cbte_tipo: int
    punto_vta: int
    # Detalle
    concepto: int = 1           # 1=Productos, 2=Servicios, 3=Ambos
    tipo_doc: int = 99          # 80=CUIT, 96=DNI, 99=CF
    nro_doc: int = 0
    cbte_desde: int = 0
    cbte_hasta: int = 0
    fecha_cbte: str = ""        # YYYYMMDD
    imp_total: float = 0.0
    imp_tot_conc: float = 0.0   # No gravado
    imp_neto: float = 0.0       # Base imponible
    imp_iva: float = 0.0
    imp_trib: float = 0.0
    imp_op_ex: float = 0.0      # Exentas
    mon_id: str = "PES"         # Pesos argentinos
    mon_cotiz: float = 1.0
    # Fechas de servicio (obligatorias para concepto 2 y 3)
    fecha_serv_desde: str = ""  # YYYYMMDD — requerido si concepto != 1
    fecha_serv_hasta: str = ""  # YYYYMMDD — requerido si concepto != 1
    fecha_vto_pago: str = ""    # YYYYMMDD — requerido si concepto != 1
    # IVA (para facturas A y B que discriminan IVA)
    iva_items: list[dict] = None  # [{"Id": 5, "BaseImp": X, "Importe": Y}]

    def __post_init__(self):
        if self.iva_items is None:
            self.iva_items = []


def _build_fecae_request_xml(
    token: str,
    sign: str,
    cuit: int,
    req: FECAERequest,
) -> str:
    """Construye el XML para FECAESolicitar."""
    # Bloque Iva (solo si hay items de IVA — Factura A/B)
    iva_xml = ""
    if req.iva_items:
        iva_entries = ""
        for item in req.iva_items:
            iva_entries += (
                "<wsfe:AlicIva>"
                f"<wsfe:Id>{item['Id']}</wsfe:Id>"
                f"<wsfe:BaseImp>{item['BaseImp']:.2f}</wsfe:BaseImp>"
                f"<wsfe:Importe>{item['Importe']:.2f}</wsfe:Importe>"
                "</wsfe:AlicIva>"
            )
        iva_xml = f"<wsfe:Iva>{iva_entries}</wsfe:Iva>"

    body = (
        f"{_auth_xml(token, sign, cuit)}"
        "<wsfe:FeCAEReq>"
        "<wsfe:FeCabReq>"
        f"<wsfe:CantReg>1</wsfe:CantReg>"
        f"<wsfe:PtoVta>{req.punto_vta}</wsfe:PtoVta>"
        f"<wsfe:CbteTipo>{req.cbte_tipo}</wsfe:CbteTipo>"
        "</wsfe:FeCabReq>"
        "<wsfe:FeDetReq>"
        "<wsfe:FECAEDetRequest>"
        f"<wsfe:Concepto>{req.concepto}</wsfe:Concepto>"
        f"<wsfe:DocTipo>{req.tipo_doc}</wsfe:DocTipo>"
        f"<wsfe:DocNro>{req.nro_doc}</wsfe:DocNro>"
        f"<wsfe:CbteDesde>{req.cbte_desde}</wsfe:CbteDesde>"
        f"<wsfe:CbteHasta>{req.cbte_hasta}</wsfe:CbteHasta>"
        f"<wsfe:CbteFch>{req.fecha_cbte}</wsfe:CbteFch>"
        f"<wsfe:ImpTotal>{req.imp_total:.2f}</wsfe:ImpTotal>"
        f"<wsfe:ImpTotConc>{req.imp_tot_conc:.2f}</wsfe:ImpTotConc>"
        f"<wsfe:ImpNeto>{req.imp_neto:.2f}</wsfe:ImpNeto>"
        f"<wsfe:ImpOpEx>{req.imp_op_ex:.2f}</wsfe:ImpOpEx>"
        f"<wsfe:ImpTrib>{req.imp_trib:.2f}</wsfe:ImpTrib>"
        f"<wsfe:ImpIVA>{req.imp_iva:.2f}</wsfe:ImpIVA>"
        f"<wsfe:MonId>{req.mon_id}</wsfe:MonId>"
        f"<wsfe:MonCotiz>{req.mon_cotiz:.6f}</wsfe:MonCotiz>"
        + (
            f"<wsfe:FchServDesde>{req.fecha_serv_desde}</wsfe:FchServDesde>"
            f"<wsfe:FchServHasta>{req.fecha_serv_hasta}</wsfe:FchServHasta>"
            f"<wsfe:FchVtoPago>{req.fecha_vto_pago}</wsfe:FchVtoPago>"
            if req.concepto in (2, 3) and req.fecha_serv_desde
            else ""
        )
        + f"{iva_xml}"
        "</wsfe:FECAEDetRequest>"
        "</wsfe:FeDetReq>"
        "</wsfe:FeCAEReq>"
    )
    return _soap_envelope("FECAESolicitar", body)


async def fe_cae_solicitar(
    token: str,
    sign: str,
    cuit: int,
    request: FECAERequest,
    environment: str = "sandbox",
) -> CAEResult:
    """Solicita un CAE (Código de Autorización Electrónica) a AFIP.

    Este es el método principal de emisión de comprobantes electrónicos.

    Args:
        token: Token de WSAA.
        sign: Sign de WSAA.
        cuit: CUIT del emisor.
        request: Datos del comprobante a emitir.
        environment: "sandbox" o "production".

    Returns:
        CAEResult con el CAE asignado o errores de rechazo.
    """
    url = WSFE_URLS.get(environment, WSFE_URLS["sandbox"])
    envelope = _build_fecae_request_xml(token, sign, cuit, request)

    logger.info(
        "AFIP FECAESolicitar: cuit=%s pto_vta=%s cbte_tipo=%s nro=%s total=%.2f",
        cuit, request.punto_vta, request.cbte_tipo,
        request.cbte_desde, request.imp_total,
    )

    try:
        root = await _soap_call(url, "FECAESolicitar", envelope)
    except (ConnectionError, ValueError) as exc:
        logger.error("AFIP FECAESolicitar error: %s", exc)
        return CAEResult(
            success=False,
            errors=[str(exc)],
        )

    # Buscar FECAESolicitarResult
    result_elem = None
    for elem in root.iter():
        tag_local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag_local == "FECAESolicitarResult":
            result_elem = elem
            break

    if result_elem is None:
        return CAEResult(
            success=False,
            errors=["No se encontró FECAESolicitarResult en respuesta AFIP."],
        )

    # Extraer errores generales
    general_errors = _extract_errors(result_elem)

    # Buscar FECAEDetResponse (detalle del comprobante)
    det_response = None
    for elem in result_elem.iter():
        tag_local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag_local == "FECAEDetResponse":
            det_response = elem
            break

    if det_response is None:
        return CAEResult(
            success=False,
            errors=general_errors or [
                "No se encontró FECAEDetResponse en respuesta AFIP."
            ],
        )

    # Extraer datos del detalle
    resultado = _find_text(det_response, ["Resultado"])
    cae = _find_text(det_response, ["CAE"])
    cae_fch_vto = _find_text(det_response, ["CAEFchVto"])
    cbte_desde_str = _find_text(det_response, ["CbteDesde"])
    observations = _extract_observations(det_response)
    det_errors = _extract_errors(det_response)

    cbte_nro = 0
    try:
        cbte_nro = int(cbte_desde_str) if cbte_desde_str else request.cbte_desde
    except (ValueError, TypeError):
        cbte_nro = request.cbte_desde

    all_errors = general_errors + det_errors
    is_approved = resultado == "A" and bool(cae)

    if is_approved:
        logger.info(
            "AFIP CAE obtenido: %s vto=%s cbte_nro=%s",
            cae, cae_fch_vto, cbte_nro,
        )
    else:
        logger.warning(
            "AFIP CAE rechazado/observado: resultado=%s errors=%s obs=%s",
            resultado, all_errors, observations,
        )

    return CAEResult(
        success=is_approved,
        cae=cae,
        cae_fch_vto=cae_fch_vto,
        cbte_nro=cbte_nro,
        resultado=resultado,
        errors=all_errors,
        observations=observations,
    )
