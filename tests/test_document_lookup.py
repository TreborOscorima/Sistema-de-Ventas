"""Tests para el servicio de consulta de documentos fiscales.

Cubre:
    - PEDocumentLookup: RUC encontrado, RUC no encontrado, RUC en BAJA, DNI,
      formato inválido, token faltante, timeout, error HTTP.
    - ARDocumentLookup: CUIT encontrado (RI, monotributo, CF, exento),
      CUIT no encontrado, formato inválido, timeout.
    - determine_ar_cbte_tipo: matriz completa A/B/C.
    - DocumentLookupFactory: países soportados y no soportados.
    - LookupResult: dataclass defaults.
    - _get_ttl: TTL por tipo de documento y resultado.
"""
from __future__ import annotations

import os
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-for-lookup-tests")
os.environ.setdefault("TENANT_STRICT", "0")

from app.services.document_lookup_service import (
    ARDocumentLookup,
    CACHE_TTL_DNI,
    CACHE_TTL_NOT_FOUND,
    CACHE_TTL_RUC_CUIT,
    DocumentLookupFactory,
    LookupResult,
    PEDocumentLookup,
    _get_ttl,
    determine_ar_cbte_tipo,
)


# ═════════════════════════════════════════════════════════════
# LookupResult DATACLASS
# ═════════════════════════════════════════════════════════════


class TestLookupResult:
    def test_defaults(self):
        r = LookupResult()
        assert r.found is False
        assert r.doc_number == ""
        assert r.doc_type == ""
        assert r.legal_name == ""
        assert r.fiscal_address == ""
        assert r.status == ""
        assert r.condition == ""
        assert r.iva_condition == ""
        assert r.iva_condition_code == 0
        assert r.error == ""
        assert r.raw_data == {}

    def test_with_values(self):
        r = LookupResult(
            found=True,
            doc_number="20123456789",
            doc_type="RUC",
            legal_name="EMPRESA SAC",
            status="ACTIVO",
            condition="HABIDO",
        )
        assert r.found is True
        assert r.legal_name == "EMPRESA SAC"


# ═════════════════════════════════════════════════════════════
# PERÚ — PEDocumentLookup
# ═════════════════════════════════════════════════════════════


class TestPEDocumentLookup:
    """Tests para la estrategia de consulta de Perú.

    El token y URL de API se leen de variables de entorno de plataforma
    (LOOKUP_API_URL, LOOKUP_API_TOKEN), no de CompanyBillingConfig.
    """

    @pytest.fixture
    def strategy(self):
        return PEDocumentLookup()

    @pytest.fixture
    def mock_config(self):
        """Config de empresa (ya no se usa para token, pero se pasa por interfaz)."""
        config = MagicMock()
        config.lookup_api_url = ""
        config.lookup_api_token = None
        return config

    def _mock_response(self, status_code: int, json_data: dict) -> httpx.Response:
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.json.return_value = json_data
        return response

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LOOKUP_API_URL": "https://api.test.pe/v2", "LOOKUP_API_TOKEN": "test_token"})
    async def test_ruc_found_activo_habido(self, strategy, mock_config):
        """RUC válido con estado ACTIVO y condición HABIDO."""
        api_data = {
            "nombre": "EMPRESA DE PRUEBA SAC",
            "direccion": "AV AREQUIPA 1234",
            "estado": "ACTIVO",
            "condicion": "HABIDO",
        }
        mock_response = self._mock_response(200, api_data)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("20123456789", config=mock_config)

        assert result.found is True
        assert result.doc_type == "RUC"
        assert result.legal_name == "EMPRESA DE PRUEBA SAC"
        assert result.fiscal_address == "AV AREQUIPA 1234"
        assert result.status == "ACTIVO"
        assert result.condition == "HABIDO"
        assert result.error == ""
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LOOKUP_API_URL": "https://api.test.pe/v2", "LOOKUP_API_TOKEN": "test_token"})
    async def test_ruc_baja(self, strategy, mock_config):
        """RUC en estado BAJA — debe retornar found=True con status BAJA."""
        api_data = {
            "nombre": "EMPRESA CERRADA SRL",
            "direccion": "JR LIMA 567",
            "estado": "BAJA DE OFICIO",
            "condicion": "NO HABIDO",
        }
        mock_response = self._mock_response(200, api_data)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("20999888777", config=mock_config)

        assert result.found is True
        assert result.status == "BAJA DE OFICIO"
        assert result.condition == "NO HABIDO"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LOOKUP_API_URL": "https://api.test.pe/v2", "LOOKUP_API_TOKEN": "test_token"})
    async def test_ruc_not_found_404(self, strategy, mock_config):
        """RUC no encontrado — API retorna 404."""
        mock_response = self._mock_response(404, {})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("20000000000", config=mock_config)

        assert result.found is False
        assert "no encontrado" in result.error

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LOOKUP_API_URL": "https://api.test.pe/v2", "LOOKUP_API_TOKEN": "test_token"})
    async def test_dni_found(self, strategy, mock_config):
        """DNI válido (8 dígitos) — retorna nombre completo."""
        api_data = {
            "nombres": "JUAN CARLOS",
            "apellidoPaterno": "PEREZ",
            "apellidoMaterno": "GOMEZ",
        }
        mock_response = self._mock_response(200, api_data)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("12345678", config=mock_config)

        assert result.found is True
        assert result.doc_type == "DNI"
        assert result.legal_name == "PEREZ GOMEZ JUAN CARLOS"

    @pytest.mark.asyncio
    async def test_invalid_length(self, strategy, mock_config):
        """Formato inválido — longitud incorrecta."""
        result = await strategy.lookup("12345", config=mock_config)
        assert result.found is False
        assert "Formato inválido" in result.error

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LOOKUP_API_URL": "", "LOOKUP_API_TOKEN": ""})
    async def test_no_token(self, strategy):
        """Sin token configurado — retorna error."""
        result = await strategy.lookup("20123456789")
        assert result.found is False
        assert "no disponible" in result.error or "Contacte" in result.error

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LOOKUP_API_URL": "https://api.test.pe/v2", "LOOKUP_API_TOKEN": "test_token"})
    async def test_timeout(self, strategy, mock_config):
        """Timeout en la API externa."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("20123456789", config=mock_config)

        assert result.found is False
        assert "Timeout" in result.error

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LOOKUP_API_URL": "https://api.test.pe/v2", "LOOKUP_API_TOKEN": "test_token"})
    async def test_http_error(self, strategy, mock_config):
        """Error HTTP (ej. 500)."""
        mock_response = self._mock_response(500, {})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("20123456789", config=mock_config)

        assert result.found is False
        assert "HTTP 500" in result.error

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LOOKUP_API_URL": "https://custom-api.pe/v1", "LOOKUP_API_TOKEN": "test_token"})
    async def test_custom_base_url(self, strategy):
        """Usa URL custom de env var."""
        api_data = {"nombre": "TEST", "direccion": "", "estado": "ACTIVO", "condicion": "HABIDO"}
        mock_response = self._mock_response(200, api_data)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("20123456789")

        assert result.found is True
        call_args = mock_client.get.call_args
        assert "custom-api.pe" in call_args[0][0]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LOOKUP_API_URL": "https://api.test.pe/v2", "LOOKUP_API_TOKEN": "test_token"})
    async def test_ruc_alternative_field_names(self, strategy, mock_config):
        """Prueba campos alternativos de la API (razonSocial en vez de nombre)."""
        api_data = {
            "razonSocial": "ALTERNATIVA SRL",
            "direccion": "CALLE 123",
            "estado": "activo",
            "condicion": "habido",
        }
        mock_response = self._mock_response(200, api_data)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("20123456789", config=mock_config)

        assert result.found is True
        assert result.legal_name == "ALTERNATIVA SRL"


# ═════════════════════════════════════════════════════════════
# ARGENTINA — ARDocumentLookup
# ═════════════════════════════════════════════════════════════


class TestARDocumentLookup:
    """Tests para la estrategia de consulta de Argentina."""

    @pytest.fixture
    def strategy(self):
        return ARDocumentLookup()

    def _mock_response(self, status_code: int, json_data: dict) -> httpx.Response:
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.json.return_value = json_data
        return response

    @pytest.mark.asyncio
    async def test_cuit_found_ri(self, strategy):
        """CUIT encontrado — Responsable Inscripto (IdCondicionIVA=1)."""
        api_data = {
            "Denominacion": "EMPRESA ARGENTINA SA",
            "Domicilio": "AV CORRIENTES 1234, CABA",
            "IdCondicionIVA": 1,
            "EstadoClave": "ACTIVO",
        }
        mock_response = self._mock_response(200, api_data)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("20345678901")

        assert result.found is True
        assert result.doc_type == "CUIT"
        assert result.legal_name == "EMPRESA ARGENTINA SA"
        assert result.fiscal_address == "AV CORRIENTES 1234, CABA"
        assert result.iva_condition == "RI"
        assert result.iva_condition_code == 1

    @pytest.mark.asyncio
    async def test_cuit_found_monotributo(self, strategy):
        """CUIT Monotributista (IdCondicionIVA=6)."""
        api_data = {
            "Denominacion": "GARCIA JUAN",
            "Domicilio": "CALLE FALSA 123",
            "IdCondicionIVA": 6,
        }
        mock_response = self._mock_response(200, api_data)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("27123456789")

        assert result.found is True
        assert result.iva_condition == "monotributo"
        assert result.iva_condition_code == 6

    @pytest.mark.asyncio
    async def test_cuit_found_consumidor_final(self, strategy):
        """CUIT Consumidor Final (IdCondicionIVA=5)."""
        api_data = {
            "Denominacion": "PEREZ MARIA",
            "Domicilio": "",
            "IdCondicionIVA": 5,
        }
        mock_response = self._mock_response(200, api_data)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("20111222333")

        assert result.found is True
        assert result.iva_condition == "CF"
        assert result.iva_condition_code == 5

    @pytest.mark.asyncio
    async def test_cuit_found_exento(self, strategy):
        """CUIT IVA Exento (IdCondicionIVA=4)."""
        api_data = {
            "Denominacion": "FUNDACION EXENTA",
            "Domicilio": "AV RIVADAVIA 5678",
            "IdCondicionIVA": 4,
        }
        mock_response = self._mock_response(200, api_data)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("30111222334")

        assert result.found is True
        assert result.iva_condition == "exento"
        assert result.iva_condition_code == 4

    @pytest.mark.asyncio
    async def test_cuit_not_found(self, strategy):
        """CUIT no encontrado — Denominacion vacía."""
        api_data = {"Denominacion": "", "Domicilio": ""}
        mock_response = self._mock_response(200, api_data)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("20000000000")

        assert result.found is False
        assert "no encontrado" in result.error

    @pytest.mark.asyncio
    async def test_cuit_invalid_format(self, strategy):
        """CUIT con formato inválido — menos de 11 dígitos."""
        result = await strategy.lookup("12345")
        assert result.found is False
        assert "inválido" in result.error

    @pytest.mark.asyncio
    async def test_cuit_non_numeric(self, strategy):
        """CUIT con caracteres no numéricos."""
        result = await strategy.lookup("20-3456789-1")  # hyphens stripped, becomes 2034567891
        # After strip, "20-3456789-1" → "2034567891" which is 10 digits
        assert result.found is False

    @pytest.mark.asyncio
    async def test_cuit_timeout(self, strategy):
        """Timeout en tangofactura."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("20345678901")

        assert result.found is False
        assert "Timeout" in result.error

    @pytest.mark.asyncio
    async def test_cuit_unknown_iva_defaults_to_cf(self, strategy):
        """IVA condition desconocida → defaults to CF."""
        api_data = {
            "Denominacion": "DESCONOCIDO SRL",
            "Domicilio": "",
            "IdCondicionIVA": 999,
        }
        mock_response = self._mock_response(200, api_data)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("20345678901")

        assert result.found is True
        assert result.iva_condition == "CF"
        assert result.iva_condition_code == 5

    @pytest.mark.asyncio
    async def test_cuit_monotributo_social(self, strategy):
        """Monotributo Social (IdCondicionIVA=13) → maps to monotributo."""
        api_data = {
            "Denominacion": "MONOTRIBUTO SOCIAL",
            "Domicilio": "",
            "IdCondicionIVA": 13,
        }
        mock_response = self._mock_response(200, api_data)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await strategy.lookup("20345678901")

        assert result.found is True
        assert result.iva_condition == "monotributo"
        assert result.iva_condition_code == 6


# ═════════════════════════════════════════════════════════════
# DETERMINE AR CBTE TIPO — MATRIZ COMPLETA
# ═════════════════════════════════════════════════════════════


class TestDetermineARCbteTipo:
    """Prueba la matriz completa de determinación de comprobante AR."""

    # Emisor RI
    def test_ri_to_ri_gives_factura_a(self):
        letra, cbte = determine_ar_cbte_tipo("RI", "RI")
        assert letra == "A"
        assert cbte == 1

    def test_ri_to_monotributo_gives_factura_b(self):
        letra, cbte = determine_ar_cbte_tipo("RI", "monotributo")
        assert letra == "B"
        assert cbte == 6

    def test_ri_to_exento_gives_factura_b(self):
        letra, cbte = determine_ar_cbte_tipo("RI", "exento")
        assert letra == "B"
        assert cbte == 6

    def test_ri_to_cf_gives_factura_b(self):
        letra, cbte = determine_ar_cbte_tipo("RI", "CF")
        assert letra == "B"
        assert cbte == 6

    # Emisor Monotributo → siempre C
    def test_mono_to_ri_gives_factura_c(self):
        letra, cbte = determine_ar_cbte_tipo("monotributo", "RI")
        assert letra == "C"
        assert cbte == 11

    def test_mono_to_mono_gives_factura_c(self):
        letra, cbte = determine_ar_cbte_tipo("monotributo", "monotributo")
        assert letra == "C"
        assert cbte == 11

    def test_mono_to_exento_gives_factura_c(self):
        letra, cbte = determine_ar_cbte_tipo("monotributo", "exento")
        assert letra == "C"
        assert cbte == 11

    def test_mono_to_cf_gives_factura_c(self):
        letra, cbte = determine_ar_cbte_tipo("monotributo", "CF")
        assert letra == "C"
        assert cbte == 11

    # Emisor Exento → siempre C
    def test_exento_to_ri_gives_factura_c(self):
        letra, cbte = determine_ar_cbte_tipo("exento", "RI")
        assert letra == "C"
        assert cbte == 11

    def test_exento_to_cf_gives_factura_c(self):
        letra, cbte = determine_ar_cbte_tipo("exento", "CF")
        assert letra == "C"
        assert cbte == 11

    # Fallbacks
    def test_ri_unknown_receptor_fallback_b(self):
        """RI con receptor desconocido → fallback a B."""
        letra, cbte = determine_ar_cbte_tipo("RI", "desconocido")
        assert letra == "B"
        assert cbte == 6

    def test_unknown_emisor_fallback_c(self):
        """Emisor desconocido → fallback a C."""
        letra, cbte = determine_ar_cbte_tipo("otro", "RI")
        assert letra == "C"
        assert cbte == 11

    # Whitespace handling
    def test_whitespace_stripped(self):
        letra, cbte = determine_ar_cbte_tipo("  RI  ", "  CF  ")
        assert letra == "B"
        assert cbte == 6


# ═════════════════════════════════════════════════════════════
# FACTORY
# ═════════════════════════════════════════════════════════════


class TestDocumentLookupFactory:
    def test_pe_strategy(self):
        strategy = DocumentLookupFactory.get_strategy("PE")
        assert isinstance(strategy, PEDocumentLookup)

    def test_ar_strategy(self):
        strategy = DocumentLookupFactory.get_strategy("AR")
        assert isinstance(strategy, ARDocumentLookup)

    def test_unsupported_country_raises(self):
        with pytest.raises(ValueError, match="no soportado"):
            DocumentLookupFactory.get_strategy("BR")


# ═════════════════════════════════════════════════════════════
# TTL HELPER
# ═════════════════════════════════════════════════════════════


class TestGetTTL:
    def test_ruc_found_24h(self):
        assert _get_ttl("RUC", found=True) == CACHE_TTL_RUC_CUIT

    def test_cuit_found_24h(self):
        assert _get_ttl("CUIT", found=True) == CACHE_TTL_RUC_CUIT

    def test_dni_found_7d(self):
        assert _get_ttl("DNI", found=True) == CACHE_TTL_DNI

    def test_not_found_1h(self):
        assert _get_ttl("RUC", found=False) == CACHE_TTL_NOT_FOUND
        assert _get_ttl("DNI", found=False) == CACHE_TTL_NOT_FOUND
        assert _get_ttl("CUIT", found=False) == CACHE_TTL_NOT_FOUND

    def test_ttl_values(self):
        assert CACHE_TTL_RUC_CUIT == timedelta(hours=24)
        assert CACHE_TTL_DNI == timedelta(days=7)
        assert CACHE_TTL_NOT_FOUND == timedelta(hours=1)


# ═════════════════════════════════════════════════════════════
# AR IVA CONDITION MAPPING
# ═════════════════════════════════════════════════════════════


class TestARIvaMapping:
    """Tests para _map_iva_condition de ARDocumentLookup."""

    def test_ri(self):
        assert ARDocumentLookup._map_iva_condition(1) == ("RI", 1)

    def test_exento(self):
        assert ARDocumentLookup._map_iva_condition(4) == ("exento", 4)

    def test_cf(self):
        assert ARDocumentLookup._map_iva_condition(5) == ("CF", 5)

    def test_monotributo(self):
        assert ARDocumentLookup._map_iva_condition(6) == ("monotributo", 6)

    def test_monotributo_social(self):
        cond, code = ARDocumentLookup._map_iva_condition(13)
        assert cond == "monotributo"
        assert code == 6  # normalized to 6

    def test_unknown_defaults_cf(self):
        cond, code = ARDocumentLookup._map_iva_condition(999)
        assert cond == "CF"
        assert code == 5
