"""Servicio de Facturación Electrónica — Patrón Strategy.

Arquitectura:
    BillingStrategy (ABC)
    ├── NoOpBillingStrategy    → países sin billing / billing deshabilitado
    ├── SUNATBillingStrategy   → Perú vía Nubefact REST API (Fase 1)
    └── AFIPBillingStrategy    → Argentina vía WSAA+WSFEv1 SOAP (Fase 1)

    BillingFactory.get_strategy(country_code) → instancia concreta

    emit_fiscal_document() → función de orquestación que:
        1. Valida cuota mensual (rate limit por plan)
        2. Asigna numeración atómica (FOR UPDATE)
        3. Invoca la strategy en background
        4. Persiste el FiscalDocument con resultado

Principios:
    - sale_service.py NO se modifica — el hook es post-commit.
    - NoOp es el default — cero overhead para el 99% del mundo.
    - Idempotencia: Nubefact rechaza duplicados; AFIP devuelve mismo CAE.
    - Fail-safe: si la autoridad fiscal falla, la venta ya está commiteada.
      El FiscalDocument queda en estado ``error`` para reintento posterior.
"""
from __future__ import annotations

import abc
import json
import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx
from sqlmodel import select

from app.enums import FiscalStatus, ReceiptType
from app.models.billing import CompanyBillingConfig, FiscalDocument
from app.models.sales import Sale, SaleItem
from app.utils.crypto import decrypt_text
from app.utils.db import get_async_session
from app.utils.fiscal_validators import VALID_ENVIRONMENTS, validate_cuit
from app.utils.tenant import set_tenant_context
from app.utils.timezone import utc_now_naive

logger = logging.getLogger(__name__)

# ── Constantes ───────────────────────────────────────────────
MAX_RETRY_ATTEMPTS = 3
NUBEFACT_TIMEOUT_SECONDS = 30
AFIP_TIMEOUT_SECONDS = 15

# Límites de facturación por tipo de plan
PLAN_BILLING_LIMITS: dict[str, int] = {
    "trial": 0,        # Trial no factura
    "standard": 500,
    "professional": 1000,
    "enterprise": 2000,
}

# Mapeo ReceiptType → código Nubefact
_NUBEFACT_RECEIPT_TYPE: dict[str, int] = {
    ReceiptType.factura: 1,
    ReceiptType.boleta: 2,
    ReceiptType.nota_credito: 3,
    ReceiptType.nota_debito: 4,
}

# Mapeo tipo_de_igv de Nubefact según categoría fiscal
_NUBEFACT_IGV_TYPE: dict[str, int] = {
    "gravado": 1,       # Gravado - Operación Onerosa
    "exonerado": 8,     # Exonerado - Operación Onerosa
    "inafecto": 9,      # Inafecto - Operación Onerosa
    "gratuito": 2,      # Gravado - Retiro por premio (gratuito)
}

# Mapeo ReceiptType → CbteTipo AFIP
_AFIP_CBTE_TIPO: dict[str, dict[str, int]] = {
    # Monotributista (Factura C)
    "C": {
        ReceiptType.factura: 11,
        ReceiptType.boleta: 11,  # En AR no hay "boleta", se usa Factura C
        ReceiptType.nota_credito: 13,
        ReceiptType.nota_debito: 12,
    },
    # Responsable Inscripto → Consumidor Final (Factura B)
    "B": {
        ReceiptType.factura: 6,
        ReceiptType.boleta: 6,
        ReceiptType.nota_credito: 8,
        ReceiptType.nota_debito: 7,
    },
    # Responsable Inscripto → Responsable Inscripto (Factura A)
    "A": {
        ReceiptType.factura: 1,
        ReceiptType.boleta: 1,
        ReceiptType.nota_credito: 3,
        ReceiptType.nota_debito: 2,
    },
}


# ═════════════════════════════════════════════════════════════
# ABSTRACT BASE CLASS
# ═════════════════════════════════════════════════════════════


class BillingStrategy(abc.ABC):
    """Interfaz abstracta para estrategias de facturación electrónica.

    Cada implementación encapsula la comunicación con una entidad
    fiscal específica (SUNAT, AFIP) o la ausencia de ella (NoOp).
    """

    @abc.abstractmethod
    async def send_document(
        self,
        fiscal_doc: FiscalDocument,
        sale: Sale,
        items: list[SaleItem],
        config: CompanyBillingConfig,
    ) -> FiscalDocument:
        """Envía el documento fiscal a la autoridad tributaria.

        Actualiza ``fiscal_doc`` in-place con el resultado:
        - fiscal_status → authorized / rejected / error
        - cae_cdr → respuesta de autorización
        - fiscal_errors → detalles de rechazo
        - qr_data → payload para QR del comprobante impreso

        Args:
            fiscal_doc: documento fiscal con numeración ya asignada.
            sale: cabecera de la venta.
            items: líneas de la venta con detalle de productos.
            config: configuración de billing de la empresa.

        Returns:
            El mismo ``fiscal_doc`` actualizado.
        """
        ...

    @abc.abstractmethod
    def build_qr_data(
        self,
        fiscal_doc: FiscalDocument,
        config: CompanyBillingConfig,
    ) -> str:
        """Genera el payload del código QR para el comprobante impreso.

        Args:
            fiscal_doc: documento con numeración y CAE/CDR asignados.
            config: configuración de billing para datos del emisor.

        Returns:
            String con el contenido del QR (URL para AFIP, pipe-separated para SUNAT).
        """
        ...


# ═════════════════════════════════════════════════════════════
# NO-OP STRATEGY (Default para países sin billing)
# ═════════════════════════════════════════════════════════════


class NoOpBillingStrategy(BillingStrategy):
    """Estrategia nula — retorno inmediato sin comunicación fiscal.

    Se usa cuando:
    - La empresa no tiene ``has_electronic_billing = True``.
    - El país no tiene integración fiscal implementada.
    - La empresa aún no configuró sus credenciales.

    Costo computacional: O(1), sin I/O de red.
    """

    async def send_document(
        self,
        fiscal_doc: FiscalDocument,
        sale: Sale,
        items: list[SaleItem],
        config: CompanyBillingConfig,
    ) -> FiscalDocument:
        # NoOp: marca como autorizado internamente (ticket interno).
        fiscal_doc.fiscal_status = FiscalStatus.authorized
        fiscal_doc.authorized_at = utc_now_naive()
        fiscal_doc.cae_cdr = "INTERNAL_TICKET"
        logger.debug(
            "NoOp billing: sale_id=%s marcada como ticket interno",
            sale.id,
        )
        return fiscal_doc

    def build_qr_data(
        self,
        fiscal_doc: FiscalDocument,
        config: CompanyBillingConfig,
    ) -> str:
        return ""


# ═════════════════════════════════════════════════════════════
# SUNAT STRATEGY (Perú — Nubefact REST API)
# ═════════════════════════════════════════════════════════════


class SUNATBillingStrategy(BillingStrategy):
    """Estrategia de facturación para Perú vía Nubefact OSE.

    Fase 1: REST API de Nubefact (OSE autorizado por SUNAT).
    - Endpoint: POST https://api.nubefact.com/api/v1/{ruta}
    - Auth: Token en header Authorization.
    - Request: JSON plano con datos del comprobante.
    - Response: JSON con aceptada_por_sunat, CDR, QR, PDF.

    El OSE se encarga de:
    - Generar el XML UBL 2.1 firmado.
    - Enviarlo a SUNAT.
    - Gestionar el Resumen Diario para boletas.
    - Almacenar CDR y generar PDF.
    """

    async def send_document(
        self,
        fiscal_doc: FiscalDocument,
        sale: Sale,
        items: list[SaleItem],
        config: CompanyBillingConfig,
    ) -> FiscalDocument:
        """Envía comprobante a Nubefact y procesa la respuesta."""
        if not config.nubefact_url or not config.nubefact_token:
            fiscal_doc.fiscal_status = FiscalStatus.error
            fiscal_doc.fiscal_errors = json.dumps({
                "error": "Configuración Nubefact incompleta",
                "detail": "nubefact_url o nubefact_token no configurados",
            })
            return fiscal_doc

        try:
            api_token = decrypt_text(config.nubefact_token)
        except (ValueError, RuntimeError) as exc:
            fiscal_doc.fiscal_status = FiscalStatus.error
            fiscal_doc.fiscal_errors = json.dumps({
                "error": "Error desencriptando token Nubefact",
                "detail": str(exc),
            })
            return fiscal_doc

        payload = self._build_nubefact_payload(fiscal_doc, sale, items, config)
        fiscal_doc.xml_request = json.dumps(payload, default=str)
        fiscal_doc.fiscal_status = FiscalStatus.sent
        fiscal_doc.sent_at = fiscal_doc.sent_at or utc_now_naive()
        fiscal_doc.retry_count += 1

        try:
            async with httpx.AsyncClient(timeout=NUBEFACT_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    config.nubefact_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f'Token token="{api_token}"',
                    },
                )

            fiscal_doc.xml_response = response.text

            if response.status_code == 200:
                data = response.json()
                if data.get("aceptada_por_sunat"):
                    fiscal_doc.fiscal_status = FiscalStatus.authorized
                    fiscal_doc.authorized_at = utc_now_naive()
                    fiscal_doc.cae_cdr = data.get("cdr_zip_base64", "")
                    fiscal_doc.hash_code = data.get("codigo_hash", "")
                    fiscal_doc.qr_data = data.get(
                        "cadena_para_codigo_qr", ""
                    )
                    logger.info(
                        "SUNAT: documento %s autorizado | sale_id=%s",
                        fiscal_doc.full_number,
                        sale.id,
                    )
                else:
                    fiscal_doc.fiscal_status = FiscalStatus.rejected
                    fiscal_doc.fiscal_errors = json.dumps({
                        "sunat_description": data.get("sunat_description", ""),
                        "sunat_note": data.get("sunat_note", ""),
                        "sunat_responsecode": data.get("sunat_responsecode", ""),
                        "sunat_soap_error": data.get("sunat_soap_error", ""),
                    })
                    logger.warning(
                        "SUNAT: documento %s rechazado | sale_id=%s | %s",
                        fiscal_doc.full_number,
                        sale.id,
                        data.get("sunat_description", ""),
                    )
            else:
                fiscal_doc.fiscal_status = FiscalStatus.error
                fiscal_doc.fiscal_errors = json.dumps({
                    "http_status": response.status_code,
                    "body": response.text[:500],
                })
                logger.error(
                    "SUNAT: error HTTP %d | sale_id=%s",
                    response.status_code,
                    sale.id,
                )

        except httpx.TimeoutException:
            fiscal_doc.fiscal_status = FiscalStatus.error
            fiscal_doc.fiscal_errors = json.dumps({
                "error": "TimeoutError",
                "detail": f"Nubefact no respondió en {NUBEFACT_TIMEOUT_SECONDS}s",
            })
            logger.error("SUNAT: timeout al enviar sale_id=%s", sale.id)

        except Exception as exc:
            fiscal_doc.fiscal_status = FiscalStatus.error
            fiscal_doc.fiscal_errors = json.dumps({
                "error": type(exc).__name__,
                "detail": str(exc)[:500],
            })
            logger.exception("SUNAT: error inesperado | sale_id=%s", sale.id)

        return fiscal_doc

    def _build_nubefact_payload(
        self,
        fiscal_doc: FiscalDocument,
        sale: Sale,
        items: list[SaleItem],
        config: CompanyBillingConfig,
    ) -> dict[str, Any]:
        """Construye el JSON para la API de Nubefact."""
        nubefact_type = _NUBEFACT_RECEIPT_TYPE.get(
            fiscal_doc.receipt_type, 2  # default boleta
        )

        # Determinar tipo de documento del cliente
        client_doc_type = fiscal_doc.buyer_doc_type or "0"
        client_doc_number = fiscal_doc.buyer_doc_number or ""
        client_name = fiscal_doc.buyer_name or "CLIENTE VARIOS"

        # Calcular totales fiscales
        total = fiscal_doc.total_amount
        tax_amount = fiscal_doc.tax_amount
        taxable = fiscal_doc.taxable_amount

        payload: dict[str, Any] = {
            "operacion": "generar_comprobante",
            "tipo_de_comprobante": nubefact_type,
            "serie": fiscal_doc.serie,
            "numero": fiscal_doc.fiscal_number,
            "sunat_transaction": 1,  # Venta interna
            "cliente_tipo_de_documento": client_doc_type,
            "cliente_numero_de_documento": client_doc_number,
            "cliente_denominacion": client_name,
            "cliente_direccion": "",
            "cliente_email": "",
            "fecha_de_emision": (
                sale.timestamp.strftime("%Y-%m-%d")
                if sale.timestamp
                else utc_now_naive().strftime("%Y-%m-%d")
            ),
            "moneda": 1,  # 1=PEN (Soles)
            "porcentaje_de_igv": 18.00,
            "total_gravada": float(taxable),
            "total_igv": float(tax_amount),
            "total_exonerada": 0,
            "total_inafecta": 0,
            "total": float(total),
            "enviar_automaticamente_a_la_sunat": True,
            "enviar_automaticamente_al_cliente": False,
            "formato_de_pdf": "TICKET",
            "items": self._build_nubefact_items(items),
        }

        return payload

    def _build_nubefact_items(
        self,
        items: list[SaleItem],
    ) -> list[dict[str, Any]]:
        """Convierte SaleItems a formato de ítems Nubefact."""
        nubefact_items: list[dict[str, Any]] = []
        igv_rate = Decimal("0.18")

        for item in items:
            qty = item.quantity or Decimal("1")
            unit_price_with_igv = item.unit_price or Decimal("0")

            # Descomponer precio: asumir tax_included=True (estándar retail)
            valor_unitario = (
                unit_price_with_igv / (1 + igv_rate)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            subtotal_sin_igv = (valor_unitario * qty).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            igv_item = (subtotal_sin_igv * igv_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_item = subtotal_sin_igv + igv_item

            nubefact_items.append({
                "unidad_de_medida": "NIU",
                "codigo": item.product_barcode_snapshot or "",
                "descripcion": item.product_name_snapshot or "Producto",
                "cantidad": float(qty),
                "valor_unitario": float(valor_unitario),
                "precio_unitario": float(unit_price_with_igv),
                "subtotal": float(subtotal_sin_igv),
                "tipo_de_igv": 1,  # Gravado - Operación Onerosa
                "igv": float(igv_item),
                "total": float(total_item),
                "anticipo_regularizacion": False,
            })

        return nubefact_items

    def build_qr_data(
        self,
        fiscal_doc: FiscalDocument,
        config: CompanyBillingConfig,
    ) -> str:
        """QR SUNAT: campos pipe-separated.

        Formato:
        {RUC}|{TipoDoc}|{Serie}|{Numero}|{IGV}|{Total}|{Fecha}|{TipoDocCliente}|{NroDocCliente}|
        """
        tipo_doc_map = {
            ReceiptType.factura: "01",
            ReceiptType.boleta: "03",
            ReceiptType.nota_credito: "07",
            ReceiptType.nota_debito: "08",
        }
        tipo_doc = tipo_doc_map.get(fiscal_doc.receipt_type, "03")

        fecha = ""
        if fiscal_doc.authorized_at:
            fecha = fiscal_doc.authorized_at.strftime("%Y-%m-%d")

        parts = [
            config.tax_id,
            tipo_doc,
            fiscal_doc.serie,
            str(fiscal_doc.fiscal_number or 0),
            f"{fiscal_doc.tax_amount:.2f}",
            f"{fiscal_doc.total_amount:.2f}",
            fecha,
            fiscal_doc.buyer_doc_type or "0",
            fiscal_doc.buyer_doc_number or "",
        ]
        return "|".join(parts) + "|"


# ═════════════════════════════════════════════════════════════
# AFIP STRATEGY (Argentina — WSAA + WSFEv1 SOAP)
# ═════════════════════════════════════════════════════════════


class AFIPBillingStrategy(BillingStrategy):
    """Estrategia de facturación para Argentina vía AFIP WSAA/WSFEv1.

    Flujo completo:
        1. Autenticar con WSAA → obtener Token + Sign (cache 12h).
        2. Determinar tipo de comprobante (A/B/C) según IVA emisor/receptor.
        3. Calcular montos con discriminación IVA según categoría.
        4. Llamar FECAESolicitar con datos del comprobante.
        5. Recibir CAE (14 dígitos) + FchVto.
        6. Generar QR según RG 4291/2018.

    Prerequisitos por empresa:
        - Certificado X.509 (.pem) y clave privada encriptados en
          CompanyBillingConfig.encrypted_certificate / encrypted_private_key.
        - CUIT en config.tax_id.
        - Punto de venta habilitado en config.afip_punto_venta.
        - Condición IVA en config.emisor_iva_condition.
    """

    # Alícuota IVA 21% — ID AFIP = 5 (tabla de alícuotas)
    _IVA_21_ID = 5
    _IVA_RATE = Decimal("0.21")

    def _determine_cbte_category(
        self,
        config: CompanyBillingConfig,
        fiscal_doc: FiscalDocument,
    ) -> str:
        """Determina la categoría de comprobante (A/B/C) según IVA del emisor.

        - RI (Resp. Inscripto):
            → Si receptor es RI → Factura A
            → Si receptor es CF/Monotributo/Exento → Factura B
        - Monotributo / Exento → siempre Factura C

        Para determinar la categoría del receptor se usa buyer_doc_type:
            "80" (CUIT) con IVA lookup previo → puede ser RI
            "96" (DNI), "99" (CF) → Consumidor Final
        """
        from app.services.document_lookup_service import determine_ar_cbte_tipo

        emisor_iva = (config.emisor_iva_condition or "RI").strip()

        # Inferir condición IVA del receptor desde doc_type
        # Si es CUIT (80), asumimos CF por defecto — el lookup previo
        # debería haber seteado la condición real en buyer_doc_type
        receptor_iva = "CF"  # Default: Consumidor Final
        buyer_doc_type = fiscal_doc.buyer_doc_type or "99"
        if buyer_doc_type == "80":
            # CUIT — podría ser RI, pero sin lookup asumimos CF
            # En el flujo normal, el vendedor ya seleccionó factura
            # (que implica receptor RI) o boleta (receptor CF).
            if fiscal_doc.receipt_type == ReceiptType.factura:
                receptor_iva = "RI"
            else:
                receptor_iva = "CF"

        letra, _ = determine_ar_cbte_tipo(emisor_iva, receptor_iva)
        return letra

    def _compute_afip_amounts(
        self,
        cbte_category: str,
        total: Decimal,
    ) -> tuple[Decimal, Decimal, Decimal, list[dict]]:
        """Calcula montos AFIP según categoría de comprobante.

        Factura C (monotributo): no discrimina IVA → todo va a imp_tot_conc.
        Factura A/B (RI): discrimina IVA 21% → base + IVA separados.

        Returns:
            (imp_neto, imp_iva, imp_tot_conc, iva_items)
        """
        if cbte_category == "C":
            # Factura C: no discrimina IVA
            return Decimal("0"), Decimal("0"), total, []

        # Factura A o B: discriminar IVA 21%
        # total = base * (1 + 0.21) → base = total / 1.21
        imp_neto = (total / (1 + self._IVA_RATE)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        imp_iva = total - imp_neto
        iva_items = [{
            "Id": self._IVA_21_ID,  # 5 = 21%
            "BaseImp": float(imp_neto),
            "Importe": float(imp_iva),
        }]
        return imp_neto, imp_iva, Decimal("0"), iva_items

    async def send_document(
        self,
        fiscal_doc: FiscalDocument,
        sale: Sale,
        items: list[SaleItem],
        config: CompanyBillingConfig,
    ) -> FiscalDocument:
        """Envía comprobante a AFIP WSFEv1 y obtiene CAE.

        Flujo:
            1. Validar que existan certificados.
            2. Autenticar con WSAA (con cache de 12h).
            3. Determinar tipo de comprobante (A/B/C).
            4. Construir request FECAESolicitar.
            5. Enviar y procesar respuesta.
            6. Actualizar FiscalDocument con CAE o error.
        """
        from app.services.afip_wsaa import authenticate
        from app.services.afip_wsfe import FECAERequest, fe_cae_solicitar

        cuit_str = (config.tax_id or "").strip()
        environment = (config.environment or "sandbox").strip().lower()

        # ── 0. Validar environment ─────────────────────────
        if environment not in VALID_ENVIRONMENTS:
            fiscal_doc.fiscal_status = FiscalStatus.error
            fiscal_doc.fiscal_errors = json.dumps({
                "error": f"Entorno '{environment}' no válido. "
                f"Valores permitidos: {', '.join(sorted(VALID_ENVIRONMENTS))}.",
            })
            return fiscal_doc

        # ── 1. Validar certificados ──────────────────────────
        if not config.encrypted_certificate or not config.encrypted_private_key:
            fiscal_doc.fiscal_status = FiscalStatus.error
            fiscal_doc.fiscal_errors = json.dumps({
                "error": "Certificados AFIP no configurados para esta empresa. "
                "Contacte al administrador de la plataforma para cargar "
                "el certificado X.509 y la clave privada.",
            })
            logger.warning(
                "AFIP: sin certificados company_id=%s cuit=%s",
                config.company_id, cuit_str,
            )
            return fiscal_doc

        # Validar CUIT con dígito verificador (Ley 20.594)
        cuit_ok, cuit_err = validate_cuit(cuit_str)
        if not cuit_ok:
            fiscal_doc.fiscal_status = FiscalStatus.error
            fiscal_doc.fiscal_errors = json.dumps({
                "error": f"CUIT inválido: {cuit_err}",
            })
            return fiscal_doc

        cuit = int(cuit_str)

        # ── 2. Autenticar con WSAA ───────────────────────────
        try:
            wsaa_creds = await authenticate(
                company_id=config.company_id,
                certificate_encrypted=config.encrypted_certificate,
                private_key_encrypted=config.encrypted_private_key,
                environment=environment,
                service="wsfe",
            )
        except ValueError as exc:
            fiscal_doc.fiscal_status = FiscalStatus.error
            fiscal_doc.fiscal_errors = json.dumps({
                "error": f"Error de autenticación WSAA: {exc}",
                "tipo": "wsaa_auth",
            })
            logger.error(
                "AFIP WSAA auth error company_id=%s: %s",
                config.company_id, exc,
            )
            return fiscal_doc
        except ConnectionError as exc:
            fiscal_doc.fiscal_status = FiscalStatus.error
            fiscal_doc.fiscal_errors = json.dumps({
                "error": f"No se pudo conectar a WSAA: {exc}",
                "tipo": "wsaa_connection",
            })
            logger.error(
                "AFIP WSAA connection error company_id=%s: %s",
                config.company_id, exc,
            )
            return fiscal_doc

        # ── 3. Determinar tipo de comprobante ────────────────
        cbte_category = self._determine_cbte_category(config, fiscal_doc)
        cbte_tipo = _AFIP_CBTE_TIPO.get(cbte_category, {}).get(
            fiscal_doc.receipt_type, 11  # Default: Factura C
        )

        # ── 4. Calcular montos ───────────────────────────────
        total = fiscal_doc.total_amount
        imp_neto, imp_iva, imp_tot_conc, iva_items = self._compute_afip_amounts(
            cbte_category, total
        )

        # ── 5. Construir y enviar FECAESolicitar ─────────────
        fecha_cbte = (
            sale.timestamp.strftime("%Y%m%d")
            if sale.timestamp
            else utc_now_naive().strftime("%Y%m%d")
        )

        # Concepto AFIP: 1=Productos, 2=Servicios, 3=Ambos
        concepto = getattr(config, "afip_concepto", 1) or 1
        if concepto not in (1, 2, 3):
            concepto = 1

        # Fechas de servicio — obligatorias para concepto 2 y 3
        fecha_serv_desde = ""
        fecha_serv_hasta = ""
        fecha_vto_pago = ""
        if concepto in (2, 3):
            fecha_serv_desde = fecha_cbte
            fecha_serv_hasta = fecha_cbte
            fecha_vto_pago = fecha_cbte

        fecae_request = FECAERequest(
            cbte_tipo=cbte_tipo,
            punto_vta=config.afip_punto_venta,
            concepto=concepto,
            tipo_doc=int(fiscal_doc.buyer_doc_type or 99),
            nro_doc=int(fiscal_doc.buyer_doc_number or 0),
            cbte_desde=fiscal_doc.fiscal_number or 0,
            cbte_hasta=fiscal_doc.fiscal_number or 0,
            fecha_cbte=fecha_cbte,
            imp_total=float(total),
            imp_tot_conc=float(imp_tot_conc),
            imp_neto=float(imp_neto),
            imp_iva=float(imp_iva),
            imp_trib=0.0,
            imp_op_ex=0.0,
            mon_id="PES",
            mon_cotiz=1.0,
            fecha_serv_desde=fecha_serv_desde,
            fecha_serv_hasta=fecha_serv_hasta,
            fecha_vto_pago=fecha_vto_pago,
            iva_items=iva_items,
        )

        # Guardar request para auditoría
        fiscal_doc.xml_request = json.dumps({
            "cbte_tipo": cbte_tipo,
            "cbte_category": cbte_category,
            "punto_vta": config.afip_punto_venta,
            "cbte_nro": fiscal_doc.fiscal_number,
            "cuit": cuit,
            "imp_total": float(total),
            "imp_neto": float(imp_neto),
            "imp_iva": float(imp_iva),
            "imp_tot_conc": float(imp_tot_conc),
            "tipo_doc": fecae_request.tipo_doc,
            "nro_doc": fecae_request.nro_doc,
            "fecha_cbte": fecha_cbte,
            "environment": environment,
        })
        fiscal_doc.fiscal_status = FiscalStatus.sent
        fiscal_doc.sent_at = utc_now_naive()
        fiscal_doc.retry_count += 1

        try:
            cae_result = await fe_cae_solicitar(
                token=wsaa_creds.token,
                sign=wsaa_creds.sign,
                cuit=cuit,
                request=fecae_request,
                environment=environment,
            )
        except Exception as exc:
            fiscal_doc.fiscal_status = FiscalStatus.error
            fiscal_doc.fiscal_errors = json.dumps({
                "error": f"Error en FECAESolicitar: {exc}",
                "tipo": "wsfe_exception",
            })
            logger.exception(
                "AFIP FECAESolicitar exception company_id=%s sale_id=%s",
                config.company_id, sale.id,
            )
            return fiscal_doc

        # ── 6. Procesar resultado ────────────────────────────
        fiscal_doc.xml_response = json.dumps({
            "resultado": cae_result.resultado,
            "cae": cae_result.cae,
            "cae_fch_vto": cae_result.cae_fch_vto,
            "cbte_nro": cae_result.cbte_nro,
            "errors": cae_result.errors,
            "observations": cae_result.observations,
        })

        if cae_result.success:
            # ── AUTORIZADO ──
            fiscal_doc.fiscal_status = FiscalStatus.authorized
            fiscal_doc.cae_cdr = cae_result.cae
            fiscal_doc.hash_code = cae_result.cae_fch_vto  # Vencimiento del CAE
            fiscal_doc.authorized_at = utc_now_naive()
            logger.info(
                "AFIP: comprobante autorizado | sale_id=%s | CAE=%s | "
                "cbte=%s-%08d | company_id=%s",
                sale.id, cae_result.cae,
                fiscal_doc.serie, fiscal_doc.fiscal_number,
                config.company_id,
            )
        else:
            # ── RECHAZADO ──
            fiscal_doc.fiscal_status = FiscalStatus.rejected
            all_msgs = cae_result.errors + cae_result.observations
            fiscal_doc.fiscal_errors = json.dumps({
                "resultado": cae_result.resultado,
                "errors": cae_result.errors,
                "observations": cae_result.observations,
                "detail": "; ".join(all_msgs) if all_msgs else "Rechazado por AFIP",
            })
            logger.warning(
                "AFIP: comprobante rechazado | sale_id=%s | "
                "resultado=%s | errors=%s | company_id=%s",
                sale.id, cae_result.resultado,
                all_msgs, config.company_id,
            )

        return fiscal_doc

    def build_qr_data(
        self,
        fiscal_doc: FiscalDocument,
        config: CompanyBillingConfig,
    ) -> str:
        """QR AFIP según RG 4291/2018: JSON base64-encoded en URL.

        Formato: https://www.afip.gob.ar/fe/qr/?p={base64_json}
        """
        import base64

        cbte_category = self._determine_cbte_category(config, fiscal_doc)
        cbte_tipo = _AFIP_CBTE_TIPO.get(cbte_category, {}).get(
            fiscal_doc.receipt_type, 11
        )

        qr_payload = {
            "ver": 1,
            "fecha": (
                fiscal_doc.authorized_at.strftime("%Y-%m-%d")
                if fiscal_doc.authorized_at
                else ""
            ),
            "cuit": int(config.tax_id) if config.tax_id.isdigit() else 0,
            "ptoVta": config.afip_punto_venta,
            "tipoCmp": cbte_tipo,
            "nroCmp": fiscal_doc.fiscal_number or 0,
            "importe": float(fiscal_doc.total_amount),
            "moneda": "PES",
            "ctz": 1,
            "tipoDocRec": int(fiscal_doc.buyer_doc_type or 99),
            "nroDocRec": (
                int(fiscal_doc.buyer_doc_number)
                if fiscal_doc.buyer_doc_number
                and fiscal_doc.buyer_doc_number.isdigit()
                else 0
            ),
            "tipoCodAut": "E",  # E = CAE
            "codAut": (
                int(fiscal_doc.cae_cdr)
                if fiscal_doc.cae_cdr and fiscal_doc.cae_cdr.isdigit()
                else 0
            ),
        }

        json_bytes = json.dumps(qr_payload, separators=(",", ":")).encode()
        b64 = base64.b64encode(json_bytes).decode()
        return f"https://www.afip.gob.ar/fe/qr/?p={b64}"


# ═════════════════════════════════════════════════════════════
# BILLING FACTORY
# ═════════════════════════════════════════════════════════════


class BillingFactory:
    """Fábrica que selecciona la estrategia según el país de la empresa.

    Decisión:
        country == "PE" → SUNATBillingStrategy
        country == "AR" → AFIPBillingStrategy
        otro / sin config → NoOpBillingStrategy
    """

    _strategies: dict[str, type[BillingStrategy]] = {
        "PE": SUNATBillingStrategy,
        "AR": AFIPBillingStrategy,
    }

    @classmethod
    def get_strategy(
        cls,
        config: CompanyBillingConfig | None,
    ) -> BillingStrategy:
        """Instancia la estrategia correcta según la configuración.

        Args:
            config: configuración de billing de la empresa, o None.

        Returns:
            Instancia concreta de BillingStrategy.
        """
        if config is None or not config.is_active:
            return NoOpBillingStrategy()

        strategy_cls = cls._strategies.get(config.country, NoOpBillingStrategy)
        return strategy_cls()


# ═════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL DE ORQUESTACIÓN
# ═════════════════════════════════════════════════════════════


def _check_monthly_quota(
    config: CompanyBillingConfig,
) -> tuple[bool, str]:
    """Valida si la empresa tiene cuota mensual disponible.

    Resetea el contador si cambió el mes.

    Args:
        config: configuración de billing (debe estar locked con FOR UPDATE).

    Returns:
        (allowed, message): True si puede emitir, False con razón si no.
    """
    now = utc_now_naive()

    # Reset mensual: si el mes actual difiere del último reset
    if config.billing_count_reset_date is None or (
        config.billing_count_reset_date.year != now.year
        or config.billing_count_reset_date.month != now.month
    ):
        config.current_billing_count = 0
        config.billing_count_reset_date = now

    if config.current_billing_count >= config.max_billing_limit:
        return False, (
            f"Límite mensual alcanzado ({config.max_billing_limit} documentos). "
            "Actualice su plan para emitir más comprobantes electrónicos."
        )

    return True, ""


def _compute_fiscal_amounts(
    sale: Sale,
    items: list[SaleItem],
) -> tuple[Decimal, Decimal, Decimal]:
    """Calcula montos fiscales desde los ítems de la venta.

    Asume que los precios ya incluyen IGV (tax_included=True,
    estándar retail en Perú y Argentina).

    Returns:
        (base_imponible, monto_impuesto, total)
    """
    total = sale.total_amount or Decimal("0")
    igv_rate = Decimal("0.18")  # TODO: parametrizar por país/producto

    base = (total / (1 + igv_rate)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    tax = total - base
    return base, tax, total


async def emit_fiscal_document(
    sale_id: int,
    company_id: int,
    branch_id: int,
    receipt_type: str = ReceiptType.boleta,
    buyer_doc_type: str | None = None,
    buyer_doc_number: str | None = None,
    buyer_name: str | None = None,
    # ── Nota de Crédito ─────────────────────────────────────
    receipt_type_override: str | None = None,
    credit_note_reason: str | None = None,
    original_fiscal_doc_id: int | None = None,
) -> FiscalDocument | None:
    """Orquesta la emisión de un documento fiscal electrónico.

    Esta función es el punto de entrada principal. Se ejecuta en background
    (invocada desde VentaState.emit_fiscal_background o BillingState.emit_credit_note).

    Flujo:
        1. Consulta CompanyBillingConfig con FOR UPDATE (lock atómico).
        2. Valida cuota mensual.
        3. Asigna número correlativo.
        4. Crea FiscalDocument en estado ``pending``.
        5. Commit parcial (persiste numeración antes de red).
        6. Invoca la estrategia correspondiente (llamada HTTP async).
        7. Commit final con resultado y QR.

    Args:
        sale_id: ID de la venta ya commiteada.
        company_id: tenant company.
        branch_id: tenant branch.
        receipt_type: tipo de comprobante a emitir.
        buyer_doc_type: tipo de documento del receptor (RUC/DNI/CUIT).
        buyer_doc_number: número de documento del receptor.
        buyer_name: nombre/razón social del receptor.
        receipt_type_override: si se provee, sobreescribe ``receipt_type``.
            Usado para emitir Nota de Crédito (ReceiptType.nota_credito).
        credit_note_reason: motivo de la nota de crédito (texto libre).
        original_fiscal_doc_id: ID del FiscalDocument original que se está anulando.

    Returns:
        FiscalDocument con resultado, o None si billing no está activo.
    """
    # Aplicar override de tipo si se provee
    effective_receipt_type = receipt_type_override if receipt_type_override else receipt_type

    set_tenant_context(company_id, branch_id)

    try:
        async with get_async_session() as session:
            # 0. Idempotencia: checar por sale_id + receipt_type
            #    (una venta puede tener una factura Y una nota_credito)
            existing = (
                await session.exec(
                    select(FiscalDocument)
                    .where(FiscalDocument.company_id == company_id)
                    .where(FiscalDocument.sale_id == sale_id)
                    .where(FiscalDocument.receipt_type == effective_receipt_type)
                )
            ).first()
            if existing is not None:
                logger.info(
                    "FiscalDocument tipo=%s ya existe para sale_id=%s (status=%s), "
                    "omitiendo emisión duplicada",
                    effective_receipt_type,
                    sale_id,
                    existing.fiscal_status,
                )
                return existing

            # 1. Obtener config con lock exclusivo para numeración atómica
            config = (
                await session.exec(
                    select(CompanyBillingConfig)
                    .where(CompanyBillingConfig.company_id == company_id)
                    .where(CompanyBillingConfig.is_active == True)  # noqa: E712
                    .with_for_update()
                )
            ).first()

            if config is None:
                logger.debug(
                    "Billing no activo para company_id=%s, omitiendo",
                    company_id,
                )
                return None

            # 2. Validar cuota mensual
            allowed, message = _check_monthly_quota(config)
            if not allowed:
                logger.warning(
                    "Cuota billing agotada: company_id=%s | %s",
                    company_id,
                    message,
                )
                # Crear FiscalDocument con error de cuota
                fiscal_doc = FiscalDocument(
                    company_id=company_id,
                    branch_id=branch_id,
                    sale_id=sale_id,
                    receipt_type=receipt_type,
                    fiscal_status=FiscalStatus.error,
                    fiscal_errors=json.dumps({"quota_exceeded": message}),
                )
                session.add(fiscal_doc)
                await session.commit()
                return fiscal_doc

            # 3. Asignar serie y número correlativo (atómico bajo FOR UPDATE)
            # Nota de crédito y nota de débito usan la serie de factura/boleta
            # según el tipo de documento original al que referencian.
            _uses_factura_serie = effective_receipt_type in (
                ReceiptType.factura,
                ReceiptType.nota_credito,  # NC factura usa serie F
                ReceiptType.nota_debito,
            )
            # Verificar si hay "FACTURA" (mayúsculas) por compatibilidad
            try:
                _uses_factura_serie = _uses_factura_serie or (
                    effective_receipt_type == ReceiptType.FACTURA
                )
            except AttributeError:
                pass

            if _uses_factura_serie:
                config.current_sequence_factura += 1
                serie = config.serie_factura
                seq = config.current_sequence_factura
            else:
                config.current_sequence_boleta += 1
                serie = config.serie_boleta
                seq = config.current_sequence_boleta

            full_number = f"{serie}-{seq:08d}"

            # 4. Incrementar contador mensual
            config.current_billing_count += 1
            config.updated_at = utc_now_naive()

            # 5. Cargar la venta y sus ítems
            sale = (
                await session.exec(
                    select(Sale).where(Sale.id == sale_id)
                )
            ).first()
            if sale is None:
                logger.error("Sale id=%s no encontrada", sale_id)
                return None

            items = (
                await session.exec(
                    select(SaleItem).where(SaleItem.sale_id == sale_id)
                )
            ).all()

            # 6. Calcular montos fiscales
            base, tax, total = _compute_fiscal_amounts(sale, items)

            # 7. Crear FiscalDocument
            # Para nota de crédito, almacenar el motivo y doc original
            _fiscal_errors_pre = None
            if effective_receipt_type == ReceiptType.nota_credito:
                nc_info: dict[str, Any] = {}
                if credit_note_reason:
                    nc_info["motivo"] = credit_note_reason
                if original_fiscal_doc_id:
                    nc_info["original_fiscal_doc_id"] = original_fiscal_doc_id
                if nc_info:
                    _fiscal_errors_pre = json.dumps(nc_info)

            fiscal_doc = FiscalDocument(
                company_id=company_id,
                branch_id=branch_id,
                sale_id=sale_id,
                receipt_type=effective_receipt_type,
                serie=serie,
                fiscal_number=seq,
                full_number=full_number,
                fiscal_status=FiscalStatus.pending,
                buyer_doc_type=buyer_doc_type,
                buyer_doc_number=buyer_doc_number,
                buyer_name=buyer_name,
                taxable_amount=base,
                tax_amount=tax,
                total_amount=total,
                fiscal_errors=_fiscal_errors_pre,
            )
            session.add(fiscal_doc)

            # Commit parcial: persiste la numeración y el doc en pending
            # ANTES de la llamada de red (si la red falla, no se pierde el nro)
            await session.commit()
            await session.refresh(fiscal_doc)
            await session.refresh(config)

            # 8. Invocar estrategia (llamada HTTP async a SUNAT/AFIP)
            strategy = BillingFactory.get_strategy(config)
            fiscal_doc = await strategy.send_document(
                fiscal_doc, sale, items, config
            )

            # 9. Generar QR si fue autorizado (no-fatal si falla)
            if fiscal_doc.fiscal_status == FiscalStatus.authorized:
                try:
                    fiscal_doc.qr_data = strategy.build_qr_data(
                        fiscal_doc, config
                    )
                except Exception as qr_exc:
                    logger.warning(
                        "Error generando QR para sale_id=%s: %s",
                        sale_id,
                        qr_exc,
                    )

            # 10. Commit final con resultado
            session.add(fiscal_doc)
            await session.commit()

            logger.info(
                "Fiscal doc emitido: %s | status=%s | sale_id=%s",
                fiscal_doc.full_number,
                fiscal_doc.fiscal_status,
                sale_id,
            )
            return fiscal_doc

    except Exception as exc:
        logger.exception(
            "Error crítico en emit_fiscal_document | sale_id=%s",
            sale_id,
        )
        # Intentar persistir el error en una sesión nueva
        try:
            async with get_async_session() as err_session:
                set_tenant_context(company_id, branch_id)
                fiscal_doc = FiscalDocument(
                    company_id=company_id,
                    branch_id=branch_id,
                    sale_id=sale_id,
                    receipt_type=effective_receipt_type,
                    fiscal_status=FiscalStatus.error,
                    fiscal_errors=json.dumps({
                        "error": type(exc).__name__,
                        "detail": str(exc)[:500],
                    }),
                )
                err_session.add(fiscal_doc)
                await err_session.commit()
                return fiscal_doc
        except Exception:
            logger.exception(
                "No se pudo persistir error fiscal | sale_id=%s",
                sale_id,
            )
            return None


async def retry_fiscal_document(
    fiscal_doc_id: int,
    company_id: int,
    branch_id: int,
) -> FiscalDocument | None:
    """Reintenta la emisión de un FiscalDocument en estado error/pending.

    Solo documentos que ya tienen numeración asignada pueden ser reintentados.
    Se respeta el límite de MAX_RETRY_ATTEMPTS.

    Args:
        fiscal_doc_id: ID del FiscalDocument a reintentar.
        company_id: tenant company.
        branch_id: tenant branch.

    Returns:
        FiscalDocument actualizado, o None si no se pudo reintentar.
    """
    set_tenant_context(company_id, branch_id)

    try:
        async with get_async_session() as session:
            fiscal_doc = (
                await session.exec(
                    select(FiscalDocument)
                    .where(FiscalDocument.id == fiscal_doc_id)
                    .where(FiscalDocument.company_id == company_id)
                )
            ).first()

            if fiscal_doc is None:
                logger.warning(
                    "retry: FiscalDocument id=%s no encontrado para company=%s",
                    fiscal_doc_id,
                    company_id,
                )
                return None

            # Solo reintentar error o pending
            if fiscal_doc.fiscal_status not in (
                FiscalStatus.error,
                FiscalStatus.pending,
            ):
                logger.info(
                    "retry: FiscalDocument id=%s ya tiene status=%s, omitiendo",
                    fiscal_doc_id,
                    fiscal_doc.fiscal_status,
                )
                return fiscal_doc

            if fiscal_doc.retry_count >= MAX_RETRY_ATTEMPTS:
                logger.warning(
                    "retry: FiscalDocument id=%s alcanzó máximo de reintentos (%d)",
                    fiscal_doc_id,
                    MAX_RETRY_ATTEMPTS,
                )
                return fiscal_doc

            # Cargar config
            config = (
                await session.exec(
                    select(CompanyBillingConfig)
                    .where(CompanyBillingConfig.company_id == company_id)
                    .where(CompanyBillingConfig.is_active == True)  # noqa: E712
                )
            ).first()

            if config is None:
                fiscal_doc.fiscal_errors = json.dumps({
                    "error": "Billing desactivado al momento del reintento",
                })
                session.add(fiscal_doc)
                await session.commit()
                return fiscal_doc

            # Cargar venta e ítems
            sale = (
                await session.exec(
                    select(Sale).where(Sale.id == fiscal_doc.sale_id)
                )
            ).first()

            if sale is None:
                logger.error(
                    "retry: Sale id=%s no encontrada",
                    fiscal_doc.sale_id,
                )
                return fiscal_doc

            items = (
                await session.exec(
                    select(SaleItem).where(SaleItem.sale_id == sale.id)
                )
            ).all()

            # Ejecutar strategy
            strategy = BillingFactory.get_strategy(config)
            fiscal_doc = await strategy.send_document(
                fiscal_doc, sale, items, config
            )

            # QR si fue autorizado
            if fiscal_doc.fiscal_status == FiscalStatus.authorized:
                try:
                    fiscal_doc.qr_data = strategy.build_qr_data(
                        fiscal_doc, config
                    )
                except Exception as qr_exc:
                    logger.warning(
                        "retry: Error generando QR para doc_id=%s: %s",
                        fiscal_doc_id,
                        qr_exc,
                    )

            session.add(fiscal_doc)
            await session.commit()

            logger.info(
                "retry: FiscalDocument id=%s | status=%s | retry_count=%d",
                fiscal_doc_id,
                fiscal_doc.fiscal_status,
                fiscal_doc.retry_count,
            )
            return fiscal_doc

    except Exception as exc:
        logger.exception(
            "retry: Error crítico reintentando fiscal_doc_id=%s",
            fiscal_doc_id,
        )
        return None
