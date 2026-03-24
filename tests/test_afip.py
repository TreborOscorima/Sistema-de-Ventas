"""Tests para la integración AFIP (WSAA + WSFEv1).

Cubre:
    - WSAA: Generación y firma del TRA, parseo de respuesta LoginCms.
    - WSFEv1: Parseo de FECAESolicitar y FECompUltimoAutorizado.
    - AFIPBillingStrategy: Flujo completo send_document con mocks.
    - Determinación de tipo de comprobante A/B/C.
    - Cálculo de montos IVA por categoría.
"""
from __future__ import annotations

import base64
import json
import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-for-afip-tests")
os.environ.setdefault("TENANT_STRICT", "0")

from app.enums import FiscalStatus, ReceiptType
from app.services.afip_wsaa import (
    WSAACredentials,
    build_tra_xml,
    _parse_login_response,
    get_cached_credentials,
    cache_credentials,
    clear_cache,
)
from app.services.afip_wsfe import (
    CAEResult,
    FECAERequest,
    UltimoAutorizadoResult,
    _build_fecae_request_xml,
)
from app.services.billing_service import AFIPBillingStrategy, _AFIP_CBTE_TIPO


# ═════════════════════════════════════════════════════════════
# WSAA — TRA XML
# ═════════════════════════════════════════════════════════════


class TestWSAATRA:
    """Tests para la generación del TRA."""

    def test_tra_xml_contains_service(self):
        tra = build_tra_xml("wsfe")
        text = tra.decode("utf-8")
        assert "<service>wsfe</service>" in text

    def test_tra_xml_has_login_ticket_request(self):
        tra = build_tra_xml("wsfe")
        text = tra.decode("utf-8")
        assert "<loginTicketRequest>" in text
        assert "<uniqueId>" in text
        assert "<generationTime>" in text
        assert "<expirationTime>" in text

    def test_tra_xml_different_service(self):
        tra = build_tra_xml("ws_sr_padron_a5")
        text = tra.decode("utf-8")
        assert "<service>ws_sr_padron_a5</service>" in text


# ═════════════════════════════════════════════════════════════
# WSAA — Login Response Parsing
# ═════════════════════════════════════════════════════════════


class TestWSAALoginParsing:
    """Tests para el parseo de la respuesta SOAP de WSAA."""

    def _build_response_xml(
        self, token: str = "TOKEN123", sign: str = "SIGN456"
    ) -> str:
        """Construye una respuesta SOAP típica de WSAA LoginCms."""
        ticket_xml = (
            f"&lt;?xml version=&quot;1.0&quot; encoding=&quot;UTF-8&quot;?&gt;"
            f"&lt;loginTicketResponse&gt;"
            f"&lt;header&gt;"
            f"&lt;expirationTime&gt;2026-03-22T14:00:00-03:00&lt;/expirationTime&gt;"
            f"&lt;/header&gt;"
            f"&lt;credentials&gt;"
            f"&lt;token&gt;{token}&lt;/token&gt;"
            f"&lt;sign&gt;{sign}&lt;/sign&gt;"
            f"&lt;/credentials&gt;"
            f"&lt;/loginTicketResponse&gt;"
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            "<soap:Body>"
            "<loginCmsResponse>"
            f"<loginCmsReturn>{ticket_xml}</loginCmsReturn>"
            "</loginCmsResponse>"
            "</soap:Body>"
            "</soap:Envelope>"
        )

    def test_parse_valid_response(self):
        xml = self._build_response_xml("MY_TOKEN", "MY_SIGN")
        creds = _parse_login_response(xml)
        assert creds.token == "MY_TOKEN"
        assert creds.sign == "MY_SIGN"
        assert creds.expiration > 0

    def test_parse_missing_credentials_raises(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            "<soap:Body>"
            "<loginCmsResponse>"
            "<loginCmsReturn>&lt;loginTicketResponse&gt;"
            "&lt;header&gt;&lt;/header&gt;"
            "&lt;/loginTicketResponse&gt;</loginCmsReturn>"
            "</loginCmsResponse>"
            "</soap:Body>"
            "</soap:Envelope>"
        )
        with pytest.raises(ValueError, match="token/sign"):
            _parse_login_response(xml)

    def test_parse_soap_fault_raises(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            "<soap:Body>"
            "<loginCmsResponse></loginCmsResponse>"
            "</soap:Body>"
            "</soap:Envelope>"
        )
        with pytest.raises(ValueError, match="loginCmsReturn"):
            _parse_login_response(xml)


# ═════════════════════════════════════════════════════════════
# WSAA — Cache
# ═════════════════════════════════════════════════════════════


class TestWSAACache:
    """Tests para el cache de credenciales WSAA."""

    def setup_method(self):
        clear_cache()

    def test_cache_and_retrieve(self):
        import time
        creds = WSAACredentials(
            token="T", sign="S",
            expiration=time.time() + 3600,
            service="wsfe",
        )
        cache_credentials(1, creds)
        cached = get_cached_credentials(1, "wsfe")
        assert cached is not None
        assert cached.token == "T"

    def test_expired_not_returned(self):
        import time
        creds = WSAACredentials(
            token="T", sign="S",
            expiration=time.time() - 100,  # Already expired
            service="wsfe",
        )
        cache_credentials(1, creds)
        cached = get_cached_credentials(1, "wsfe")
        assert cached is None

    def test_clear_cache_by_company(self):
        import time
        creds = WSAACredentials(
            token="T", sign="S",
            expiration=time.time() + 3600,
            service="wsfe",
        )
        cache_credentials(1, creds)
        cache_credentials(2, creds)
        clear_cache(1)
        assert get_cached_credentials(1, "wsfe") is None
        assert get_cached_credentials(2, "wsfe") is not None

    def test_clear_all_cache(self):
        import time
        creds = WSAACredentials(
            token="T", sign="S",
            expiration=time.time() + 3600,
            service="wsfe",
        )
        cache_credentials(1, creds)
        cache_credentials(2, creds)
        clear_cache()
        assert get_cached_credentials(1, "wsfe") is None
        assert get_cached_credentials(2, "wsfe") is None


# ═════════════════════════════════════════════════════════════
# WSFEv1 — FECAESolicitar XML
# ═════════════════════════════════════════════════════════════


class TestWSFERequestXML:
    """Tests para la construcción del XML de FECAESolicitar."""

    def test_basic_request(self):
        req = FECAERequest(
            cbte_tipo=11,
            punto_vta=1,
            cbte_desde=1,
            cbte_hasta=1,
            fecha_cbte="20260322",
            imp_total=1000.0,
            imp_tot_conc=1000.0,
            imp_neto=0.0,
            imp_iva=0.0,
        )
        xml = _build_fecae_request_xml("TOKEN", "SIGN", 20345678906, req)
        assert "<wsfe:Token>TOKEN</wsfe:Token>" in xml
        assert "<wsfe:Cuit>20345678906</wsfe:Cuit>" in xml
        assert "<wsfe:CbteTipo>11</wsfe:CbteTipo>" in xml
        assert "<wsfe:ImpTotal>1000.00</wsfe:ImpTotal>" in xml

    def test_request_with_iva_items(self):
        req = FECAERequest(
            cbte_tipo=1,
            punto_vta=1,
            cbte_desde=1,
            cbte_hasta=1,
            fecha_cbte="20260322",
            imp_total=1210.0,
            imp_neto=1000.0,
            imp_iva=210.0,
            iva_items=[{"Id": 5, "BaseImp": 1000.0, "Importe": 210.0}],
        )
        xml = _build_fecae_request_xml("TOKEN", "SIGN", 20345678906, req)
        assert "<wsfe:Iva>" in xml
        assert "<wsfe:AlicIva>" in xml
        assert "<wsfe:Id>5</wsfe:Id>" in xml
        assert "<wsfe:BaseImp>1000.00</wsfe:BaseImp>" in xml

    def test_request_without_iva(self):
        req = FECAERequest(
            cbte_tipo=11,
            punto_vta=1,
            cbte_desde=1,
            cbte_hasta=1,
            fecha_cbte="20260322",
            imp_total=500.0,
            imp_tot_conc=500.0,
        )
        xml = _build_fecae_request_xml("TOKEN", "SIGN", 20345678906, req)
        assert "<wsfe:Iva>" not in xml


# ═════════════════════════════════════════════════════════════
# AFIPBillingStrategy — Montos IVA
# ═════════════════════════════════════════════════════════════


class TestAFIPAmounts:
    """Tests para el cálculo de montos IVA."""

    def setup_method(self):
        self.strategy = AFIPBillingStrategy()

    def test_factura_c_no_discrimina_iva(self):
        neto, iva, conc, items = self.strategy._compute_afip_amounts(
            "C", Decimal("1000.00")
        )
        assert neto == Decimal("0")
        assert iva == Decimal("0")
        assert conc == Decimal("1000.00")
        assert items == []

    def test_factura_a_discrimina_iva(self):
        neto, iva, conc, items = self.strategy._compute_afip_amounts(
            "A", Decimal("1210.00")
        )
        assert neto == Decimal("1000.00")
        assert iva == Decimal("210.00")
        assert conc == Decimal("0")
        assert len(items) == 1
        assert items[0]["Id"] == 5  # IVA 21%

    def test_factura_b_discrimina_iva(self):
        neto, iva, conc, items = self.strategy._compute_afip_amounts(
            "B", Decimal("121.00")
        )
        assert neto == Decimal("100.00")
        assert iva == Decimal("21.00")
        assert len(items) == 1


# ═════════════════════════════════════════════════════════════
# AFIPBillingStrategy — send_document
# ═════════════════════════════════════════════════════════════


class TestAFIPSendDocument:
    """Tests para el flujo completo de AFIPBillingStrategy.send_document."""

    def _make_config(self, **overrides):
        config = MagicMock()
        config.company_id = 1
        config.tax_id = "20345678906"
        config.environment = "sandbox"
        config.afip_punto_venta = 1
        config.emisor_iva_condition = "monotributo"
        config.encrypted_certificate = "encrypted_cert"
        config.encrypted_private_key = "encrypted_key"
        config.serie_factura = "0001"
        config.serie_boleta = "0001"
        config.afip_concepto = 1
        for k, v in overrides.items():
            setattr(config, k, v)
        return config

    def _make_fiscal_doc(self, **overrides):
        doc = MagicMock()
        doc.fiscal_number = 1
        doc.receipt_type = ReceiptType.factura
        doc.total_amount = Decimal("1000.00")
        doc.taxable_amount = Decimal("1000.00")
        doc.tax_amount = Decimal("0.00")
        doc.buyer_doc_type = "99"
        doc.buyer_doc_number = "0"
        doc.buyer_name = "CONSUMIDOR FINAL"
        doc.serie = "0001"
        doc.cae_cdr = None
        doc.hash_code = None
        doc.xml_request = None
        doc.xml_response = None
        doc.fiscal_errors = None
        doc.fiscal_status = FiscalStatus.pending
        doc.sent_at = None
        doc.authorized_at = None
        doc.retry_count = 0
        for k, v in overrides.items():
            setattr(doc, k, v)
        return doc

    def _make_sale(self):
        sale = MagicMock()
        sale.id = 100
        sale.timestamp = MagicMock()
        sale.timestamp.strftime = MagicMock(return_value="20260322")
        return sale

    @pytest.mark.asyncio
    async def test_missing_certificates_returns_error(self):
        strategy = AFIPBillingStrategy()
        config = self._make_config(
            encrypted_certificate=None,
            encrypted_private_key=None,
        )
        doc = self._make_fiscal_doc()
        sale = self._make_sale()

        result = await strategy.send_document(doc, sale, [], config)

        assert result.fiscal_status == FiscalStatus.error
        assert "Certificados AFIP" in result.fiscal_errors

    @pytest.mark.asyncio
    async def test_invalid_cuit_returns_error(self):
        strategy = AFIPBillingStrategy()
        config = self._make_config(tax_id="12345")
        doc = self._make_fiscal_doc()
        sale = self._make_sale()

        result = await strategy.send_document(doc, sale, [], config)

        assert result.fiscal_status == FiscalStatus.error
        errors = json.loads(result.fiscal_errors)
        assert "CUIT inválido" in errors.get("error", "")

    @pytest.mark.asyncio
    @patch("app.services.afip_wsaa.authenticate")
    @patch("app.services.afip_wsfe.fe_cae_solicitar")
    async def test_successful_cae(self, mock_fe, mock_auth):
        mock_auth.return_value = WSAACredentials(
            token="T", sign="S", expiration=999999999999.0
        )
        mock_fe.return_value = CAEResult(
            success=True,
            cae="71234567890123",
            cae_fch_vto="20260402",
            cbte_nro=1,
            resultado="A",
        )

        strategy = AFIPBillingStrategy()
        config = self._make_config()
        doc = self._make_fiscal_doc()
        sale = self._make_sale()

        result = await strategy.send_document(doc, sale, [], config)

        assert result.fiscal_status == FiscalStatus.authorized
        assert result.cae_cdr == "71234567890123"
        assert result.authorized_at is not None
        mock_auth.assert_called_once()
        mock_fe.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.afip_wsaa.authenticate")
    @patch("app.services.afip_wsfe.fe_cae_solicitar")
    async def test_rejected_by_afip(self, mock_fe, mock_auth):
        mock_auth.return_value = WSAACredentials(
            token="T", sign="S", expiration=999999999999.0
        )
        mock_fe.return_value = CAEResult(
            success=False,
            resultado="R",
            errors=["[10016] Comprobante duplicado"],
        )

        strategy = AFIPBillingStrategy()
        config = self._make_config()
        doc = self._make_fiscal_doc()
        sale = self._make_sale()

        result = await strategy.send_document(doc, sale, [], config)

        assert result.fiscal_status == FiscalStatus.rejected
        assert "10016" in result.fiscal_errors

    @pytest.mark.asyncio
    @patch("app.services.afip_wsaa.authenticate")
    async def test_wsaa_auth_failure(self, mock_auth):
        mock_auth.side_effect = ValueError("Certificado expirado")

        strategy = AFIPBillingStrategy()
        config = self._make_config()
        doc = self._make_fiscal_doc()
        sale = self._make_sale()

        result = await strategy.send_document(doc, sale, [], config)

        assert result.fiscal_status == FiscalStatus.error
        assert "WSAA" in result.fiscal_errors

    @pytest.mark.asyncio
    @patch("app.services.afip_wsaa.authenticate")
    async def test_wsaa_connection_failure(self, mock_auth):
        mock_auth.side_effect = ConnectionError("Timeout")

        strategy = AFIPBillingStrategy()
        config = self._make_config()
        doc = self._make_fiscal_doc()
        sale = self._make_sale()

        result = await strategy.send_document(doc, sale, [], config)

        assert result.fiscal_status == FiscalStatus.error
        assert "conectar" in result.fiscal_errors


# ═════════════════════════════════════════════════════════════
# AFIPBillingStrategy — QR
# ═════════════════════════════════════════════════════════════


class TestAFIPQR:
    """Tests para la generación de QR AFIP."""

    def test_qr_url_format(self):
        strategy = AFIPBillingStrategy()
        doc = MagicMock()
        doc.receipt_type = ReceiptType.factura
        doc.buyer_doc_type = "99"
        doc.buyer_doc_number = "0"
        doc.fiscal_number = 1
        doc.total_amount = Decimal("1000.00")
        doc.cae_cdr = "71234567890123"
        doc.authorized_at = MagicMock()
        doc.authorized_at.strftime = MagicMock(return_value="2026-03-22")

        config = MagicMock()
        config.tax_id = "20345678906"
        config.afip_punto_venta = 1
        config.emisor_iva_condition = "monotributo"

        qr = strategy.build_qr_data(doc, config)

        assert qr.startswith("https://www.afip.gob.ar/fe/qr/?p=")
        # Decodificar y verificar contenido
        b64_part = qr.split("p=")[1]
        payload = json.loads(base64.b64decode(b64_part))
        assert payload["ver"] == 1
        assert payload["cuit"] == 20345678906
        assert payload["tipoCodAut"] == "E"
        assert payload["codAut"] == 71234567890123


# ═════════════════════════════════════════════════════════════
# AFIP CBTE TIPO MAPPING
# ═════════════════════════════════════════════════════════════


class TestAFIPCbteTipo:
    """Tests para el mapeo de tipos de comprobante AFIP."""

    def test_factura_c_factura(self):
        assert _AFIP_CBTE_TIPO["C"][ReceiptType.factura] == 11

    def test_factura_c_nota_credito(self):
        assert _AFIP_CBTE_TIPO["C"][ReceiptType.nota_credito] == 13

    def test_factura_b_factura(self):
        assert _AFIP_CBTE_TIPO["B"][ReceiptType.factura] == 6

    def test_factura_b_nota_credito(self):
        assert _AFIP_CBTE_TIPO["B"][ReceiptType.nota_credito] == 8

    def test_factura_a_factura(self):
        assert _AFIP_CBTE_TIPO["A"][ReceiptType.factura] == 1

    def test_factura_a_nota_credito(self):
        assert _AFIP_CBTE_TIPO["A"][ReceiptType.nota_credito] == 3

    def test_factura_a_nota_debito(self):
        assert _AFIP_CBTE_TIPO["A"][ReceiptType.nota_debito] == 2
