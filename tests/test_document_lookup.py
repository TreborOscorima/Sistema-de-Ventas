"""Tests para app.services.document_lookup_service.

Cubre:
    - PEDocumentLookup: RUC/DNI exitoso, 404, longitud invalida, timeout, HTTP error.
    - ARDocumentLookup: CUIT exitoso (RI, monotributo, CF), errorGetData, longitud
      invalida, timeout.
    - determine_ar_cbte_tipo: matriz A/B/C completa.
    - DocumentLookupFactory: paises soportados, alias, no soportados.
    - _map_ar_iva_condition: mapeo de texto AFIP a tupla normalizada.
    - lookup_document: validaciones de entrada (vacio, no digitos, pais, longitud).
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-for-lookup-tests")
os.environ.setdefault("TENANT_STRICT", "0")

from app.services.document_lookup_service import (
    ARDocumentLookup,
    DocumentLookupFactory,
    LookupResult,
    PEDocumentLookup,
    _map_ar_iva_condition,
    determine_ar_cbte_tipo,
    lookup_document,
)


# ── helpers ───────────────────────────────────────────────


def _mock_httpx_client(mock_response=None, side_effect=None):
    """Patch context-manager para httpx.AsyncClient."""
    patcher = patch("app.services.document_lookup_service.httpx.AsyncClient")
    mock_cls = patcher.start()
    mock_client = AsyncMock()
    if side_effect is not None:
        mock_client.get.side_effect = side_effect
    else:
        mock_client.get.return_value = mock_response
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return patcher, mock_client


def _make_response(status_code: int, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status = MagicMock()
    return resp


# ═══════════════════════════════════════════════════════════
# PEDocumentLookup
# ═══════════════════════════════════════════════════════════


class TestPEDocumentLookup:
    """Consulta de RUC/DNI para Peru via apis.net.pe."""

    @pytest.fixture
    def strategy(self):
        return PEDocumentLookup(api_url="https://api.test.pe/v2", api_token="tok123")

    # ── RUC exitoso ───────────────────────────────────────

    @pytest.mark.asyncio
    async def test_successful_ruc_lookup(self, strategy):
        """RUC valido con datos SUNAT-like."""
        data = {
            "razonSocial": "EMPRESA SAC",
            "direccion": "AV. LIMA 123",
            "estado": "ACTIVO",
            "condicion": "HABIDO",
        }
        resp = _make_response(200, data)
        patcher, client = _mock_httpx_client(mock_response=resp)
        try:
            result = await strategy.lookup("20123456789")
        finally:
            patcher.stop()

        assert result.found is True
        assert result.doc_type == "RUC"
        assert result.legal_name == "EMPRESA SAC"
        assert result.fiscal_address == "AV. LIMA 123"
        assert result.status == "ACTIVO"
        assert result.condition == "HABIDO"
        assert result.error == ""
        assert result.raw_data == data

    # ── DNI exitoso ───────────────────────────────────────

    @pytest.mark.asyncio
    async def test_successful_dni_lookup(self, strategy):
        """DNI valido (8 digitos) retorna nombre completo."""
        data = {
            "nombres": "JUAN CARLOS",
            "apellidoPaterno": "PEREZ",
            "apellidoMaterno": "GOMEZ",
        }
        resp = _make_response(200, data)
        patcher, _ = _mock_httpx_client(mock_response=resp)
        try:
            result = await strategy.lookup("12345678")
        finally:
            patcher.stop()

        assert result.found is True
        assert result.doc_type == "DNI"
        assert result.legal_name == "JUAN CARLOS PEREZ GOMEZ"
        assert result.error == ""

    # ── RUC no encontrado (404) ───────────────────────────

    @pytest.mark.asyncio
    async def test_ruc_not_found_404(self, strategy):
        resp = _make_response(404)
        # 404 is handled before raise_for_status, so reset side_effect
        resp.raise_for_status = MagicMock()
        patcher, _ = _mock_httpx_client(mock_response=resp)
        try:
            result = await strategy.lookup("20000000000")
        finally:
            patcher.stop()

        assert result.found is False
        assert result.doc_type == "RUC"
        assert "no encontrado" in result.error

    # ── Longitud invalida ─────────────────────────────────

    @pytest.mark.asyncio
    async def test_invalid_document_length(self, strategy):
        """Documento con longitud que no es 8 ni 11 retorna error sin llamar API."""
        result = await strategy.lookup("12345")

        assert result.found is False
        assert "dígitos" in result.error
        assert "5" in result.error

    # ── Timeout ───────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_timeout_handling(self, strategy):
        patcher, _ = _mock_httpx_client(side_effect=httpx.TimeoutException("timed out"))
        try:
            result = await strategy.lookup("20123456789")
        finally:
            patcher.stop()

        assert result.found is False
        assert "Timeout" in result.error

    # ── HTTP error generico ───────────────────────────────

    @pytest.mark.asyncio
    async def test_http_error_handling(self, strategy):
        resp = _make_response(500)
        patcher, _ = _mock_httpx_client(mock_response=resp)
        try:
            result = await strategy.lookup("20123456789")
        finally:
            patcher.stop()

        assert result.found is False
        assert "HTTP 500" in result.error

    # ── Campo razonSocial alternativo ─────────────────────

    @pytest.mark.asyncio
    async def test_ruc_razon_social_field(self, strategy):
        """Cuando existe razonSocial se usa en vez de nombre."""
        data = {
            "razonSocial": "RAZON SOCIAL SRL",
            "nombre": "NOMBRE FALLBACK",
            "direccion": "",
            "estado": "ACTIVO",
            "condicion": "HABIDO",
        }
        resp = _make_response(200, data)
        patcher, _ = _mock_httpx_client(mock_response=resp)
        try:
            result = await strategy.lookup("20123456789")
        finally:
            patcher.stop()

        assert result.legal_name == "RAZON SOCIAL SRL"


# ═══════════════════════════════════════════════════════════
# ARDocumentLookup
# ═══════════════════════════════════════════════════════════


class TestARDocumentLookup:
    """Consulta de CUIT para Argentina via tangofactura."""

    @pytest.fixture
    def strategy(self):
        return ARDocumentLookup()

    # ── CUIT exitoso con RI ───────────────────────────────

    @pytest.mark.asyncio
    async def test_successful_cuit_lookup_ri(self, strategy):
        data = {
            "Denominacion": "EMPRESA ARGENTINA SA",
            "Domicilio": "AV CORRIENTES 1234",
            "tipoResponsable": "IVA Responsable Inscripto",
            "EstadoClave": "ACTIVA",
            "errorGetData": False,
        }
        resp = _make_response(200, data)
        patcher, _ = _mock_httpx_client(mock_response=resp)
        try:
            result = await strategy.lookup("20345678901")
        finally:
            patcher.stop()

        assert result.found is True
        assert result.doc_type == "CUIT"
        assert result.legal_name == "EMPRESA ARGENTINA SA"
        assert result.fiscal_address == "AV CORRIENTES 1234"
        assert result.iva_condition == "RI"
        assert result.iva_condition_code == 1
        assert result.error == ""

    # ── CUIT monotributo ──────────────────────────────────

    @pytest.mark.asyncio
    async def test_cuit_with_monotributo(self, strategy):
        data = {
            "Denominacion": "PERSONA MONOTRIBUTO",
            "Domicilio": "CALLE FALSA 456",
            "tipoResponsable": "Responsable Monotributo",
            "EstadoClave": "ACTIVA",
            "errorGetData": False,
        }
        resp = _make_response(200, data)
        patcher, _ = _mock_httpx_client(mock_response=resp)
        try:
            result = await strategy.lookup("27123456789")
        finally:
            patcher.stop()

        assert result.found is True
        assert result.iva_condition == "monotributo"
        assert result.iva_condition_code == 6

    # ── CUIT consumidor final ─────────────────────────────

    @pytest.mark.asyncio
    async def test_cuit_with_consumidor_final(self, strategy):
        data = {
            "Denominacion": "CONSUMIDOR",
            "Domicilio": "",
            "tipoResponsable": "Consumidor Final",
            "errorGetData": False,
        }
        resp = _make_response(200, data)
        patcher, _ = _mock_httpx_client(mock_response=resp)
        try:
            result = await strategy.lookup("20111222333")
        finally:
            patcher.stop()

        assert result.found is True
        assert result.iva_condition == "CF"
        assert result.iva_condition_code == 5

    # ── CUIT no encontrado (errorGetData=True) ────────────

    @pytest.mark.asyncio
    async def test_cuit_not_found_error_get_data(self, strategy):
        data = {"errorGetData": True}
        resp = _make_response(200, data)
        patcher, _ = _mock_httpx_client(mock_response=resp)
        try:
            result = await strategy.lookup("20000000000")
        finally:
            patcher.stop()

        assert result.found is False
        assert "no encontrado" in result.error

    # ── Longitud invalida de CUIT ─────────────────────────

    @pytest.mark.asyncio
    async def test_invalid_cuit_length(self, strategy):
        result = await strategy.lookup("1234567")
        assert result.found is False
        assert "11 dígitos" in result.error

    # ── Timeout ───────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_timeout_handling(self, strategy):
        patcher, _ = _mock_httpx_client(side_effect=httpx.TimeoutException("timed out"))
        try:
            result = await strategy.lookup("20345678901")
        finally:
            patcher.stop()

        assert result.found is False
        assert "Timeout" in result.error

    # ── Fallback a IdCondicionIVA numerico ────────────────

    @pytest.mark.asyncio
    async def test_fallback_to_id_condicion_iva(self, strategy):
        """Cuando tipoResponsable esta vacio, usa IdCondicionIVA numerico."""
        data = {
            "Denominacion": "SIN TIPO RESPONSABLE",
            "Domicilio": "",
            "tipoResponsable": "",
            "IdCondicionIVA": 6,
            "errorGetData": False,
        }
        resp = _make_response(200, data)
        patcher, _ = _mock_httpx_client(mock_response=resp)
        try:
            result = await strategy.lookup("20345678901")
        finally:
            patcher.stop()

        assert result.found is True
        assert result.iva_condition == "monotributo"
        assert result.iva_condition_code == 6


# ═══════════════════════════════════════════════════════════
# determine_ar_cbte_tipo
# ═══════════════════════════════════════════════════════════


class TestDetermineARCbteTipo:
    """Matriz de tipo de comprobante Argentina."""

    def test_ri_to_ri_factura_a(self):
        letra, cbte = determine_ar_cbte_tipo("RI", "RI")
        assert letra == "A"
        assert cbte == 1

    def test_ri_to_monotributo_factura_b(self):
        letra, cbte = determine_ar_cbte_tipo("RI", "monotributo")
        assert letra == "B"
        assert cbte == 6

    def test_ri_to_cf_factura_b(self):
        letra, cbte = determine_ar_cbte_tipo("RI", "CF")
        assert letra == "B"
        assert cbte == 6

    def test_monotributo_to_any_factura_c(self):
        for receptor in ("RI", "monotributo", "exento", "CF"):
            letra, cbte = determine_ar_cbte_tipo("monotributo", receptor)
            assert letra == "C", f"Expected C for monotributo -> {receptor}"
            assert cbte == 11

    def test_exento_to_any_factura_c(self):
        for receptor in ("RI", "monotributo", "exento", "CF"):
            letra, cbte = determine_ar_cbte_tipo("exento", receptor)
            assert letra == "C", f"Expected C for exento -> {receptor}"
            assert cbte == 11

    def test_ri_to_exento_factura_b(self):
        letra, cbte = determine_ar_cbte_tipo("RI", "exento")
        assert letra == "B"
        assert cbte == 6

    def test_ri_unknown_receptor_fallback_b(self):
        """RI con receptor no mapeado -> fallback conservador a B."""
        letra, cbte = determine_ar_cbte_tipo("RI", "desconocido")
        assert letra == "B"
        assert cbte == 6

    def test_unknown_emisor_fallback_c(self):
        """Emisor desconocido -> fallback a C."""
        letra, cbte = determine_ar_cbte_tipo("otro", "RI")
        assert letra == "C"
        assert cbte == 11

    def test_whitespace_stripped(self):
        letra, cbte = determine_ar_cbte_tipo("  RI  ", "  CF  ")
        assert letra == "B"
        assert cbte == 6


# ═══════════════════════════════════════════════════════════
# DocumentLookupFactory
# ═══════════════════════════════════════════════════════════


class TestDocumentLookupFactory:
    """Fabrica que selecciona la estrategia segun el pais."""

    def test_pe_creates_pe_strategy(self):
        strategy = DocumentLookupFactory.get_strategy("PE")
        assert isinstance(strategy, PEDocumentLookup)

    def test_ar_creates_ar_strategy(self):
        strategy = DocumentLookupFactory.get_strategy("AR")
        assert isinstance(strategy, ARDocumentLookup)

    def test_unknown_country_raises_value_error(self):
        with pytest.raises(ValueError, match="no soportado"):
            DocumentLookupFactory.get_strategy("BR")

    @pytest.mark.parametrize("alias", ["pe", "PER", "PERU"])
    def test_peru_country_variants(self, alias):
        strategy = DocumentLookupFactory.get_strategy(alias)
        assert isinstance(strategy, PEDocumentLookup)

    @pytest.mark.parametrize("alias", ["ar", "ARG", "ARGENTINA"])
    def test_argentina_country_variants(self, alias):
        strategy = DocumentLookupFactory.get_strategy(alias)
        assert isinstance(strategy, ARDocumentLookup)

    def test_pe_uses_config_credentials(self):
        config = MagicMock()
        config.lookup_api_url = "https://custom.api/v2"
        config.lookup_api_token = "custom_token_abc"

        strategy = DocumentLookupFactory.get_strategy("PE", config=config)
        assert isinstance(strategy, PEDocumentLookup)
        assert strategy.api_url == "https://custom.api/v2"
        assert strategy.api_token == "custom_token_abc"

    def test_pe_falls_back_to_env_vars(self):
        with patch.dict(
            os.environ,
            {"LOOKUP_API_URL": "https://env.api/v2", "LOOKUP_API_TOKEN": "env_tok"},
        ):
            strategy = DocumentLookupFactory.get_strategy("PE")
        assert isinstance(strategy, PEDocumentLookup)
        assert strategy.api_url == "https://env.api/v2"
        assert strategy.api_token == "env_tok"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="no soportado"):
            DocumentLookupFactory.get_strategy("")

    def test_none_raises(self):
        with pytest.raises(ValueError, match="no soportado"):
            DocumentLookupFactory.get_strategy(None)


# ═══════════════════════════════════════════════════════════
# _map_ar_iva_condition
# ═══════════════════════════════════════════════════════════


class TestMapArIvaCondition:
    """Mapeo de condicion IVA de AFIP (texto) a tupla normalizada."""

    def test_responsable_inscripto(self):
        cond, code = _map_ar_iva_condition("Responsable Inscripto")
        assert cond == "RI"
        assert code == 1

    def test_iva_responsable_inscripto(self):
        cond, code = _map_ar_iva_condition("IVA Responsable Inscripto")
        assert cond == "RI"
        assert code == 1

    def test_responsable_monotributo(self):
        cond, code = _map_ar_iva_condition("Responsable Monotributo")
        assert cond == "monotributo"
        assert code == 6

    def test_iva_sujeto_exento(self):
        cond, code = _map_ar_iva_condition("IVA Sujeto Exento")
        assert cond == "exento"
        assert code == 4

    def test_consumidor_final(self):
        cond, code = _map_ar_iva_condition("Consumidor Final")
        assert cond == "CF"
        assert code == 5

    def test_unknown_empty_returns_desconocido(self):
        cond, code = _map_ar_iva_condition("")
        assert cond == "desconocido"
        assert code == 0

    def test_unknown_text_preserved(self):
        """Texto no reconocido se preserva como condicion."""
        cond, code = _map_ar_iva_condition("Tipo Raro Nuevo")
        assert cond == "Tipo Raro Nuevo"
        assert code == 0

    def test_case_insensitive(self):
        cond, code = _map_ar_iva_condition("responsable inscripto")
        assert cond == "RI"
        assert code == 1

    def test_ri_shorthand(self):
        cond, code = _map_ar_iva_condition("RI")
        assert cond == "RI"
        assert code == 1


# ═══════════════════════════════════════════════════════════
# lookup_document (funcion de orquestacion)
# ═══════════════════════════════════════════════════════════


class TestLookupDocument:
    """Validaciones de entrada de la funcion principal."""

    @pytest.mark.asyncio
    async def test_empty_doc_number(self):
        result = await lookup_document("", "PE")
        assert result.found is False
        assert "dígitos" in result.error

    @pytest.mark.asyncio
    async def test_non_digit_doc_number(self):
        result = await lookup_document("ABC123XYZ", "PE")
        assert result.found is False
        assert "dígitos" in result.error

    @pytest.mark.asyncio
    async def test_unsupported_country(self):
        result = await lookup_document("12345678901", "BR")
        assert result.found is False
        assert "no soportado" in result.error

    @pytest.mark.asyncio
    async def test_pe_wrong_length_not_8_or_11(self):
        result = await lookup_document("12345", "PE")
        assert result.found is False
        assert "8 (DNI) u 11 (RUC)" in result.error

    @pytest.mark.asyncio
    async def test_ar_wrong_length_not_11(self):
        result = await lookup_document("12345", "AR")
        assert result.found is False
        assert "11 dígitos" in result.error

    @pytest.mark.asyncio
    async def test_whitespace_only(self):
        result = await lookup_document("   ", "PE")
        assert result.found is False
        assert "dígitos" in result.error

    @pytest.mark.asyncio
    async def test_none_doc_number(self):
        result = await lookup_document(None, "PE")
        assert result.found is False

    @pytest.mark.asyncio
    async def test_hyphens_stripped(self):
        """Guiones se eliminan antes de validar longitud."""
        # "20-123456-789" stripped -> "20123456789" (11 digits) -> valid RUC length
        # Should attempt API call (not fail on format)
        patcher, _ = _mock_httpx_client(
            mock_response=_make_response(
                200,
                {
                    "razonSocial": "TEST",
                    "direccion": "",
                    "estado": "ACTIVO",
                    "condicion": "HABIDO",
                },
            )
        )
        try:
            result = await lookup_document("20-123456-789", "PE")
        finally:
            patcher.stop()

        # Should have passed validation and reached the API
        assert result.found is True or result.error == ""
