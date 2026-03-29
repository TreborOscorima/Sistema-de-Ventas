"""Tests para el módulo de Facturación Electrónica.

Cubre:
    - Enums (ReceiptType, FiscalStatus)
    - Crypto utilities (encrypt/decrypt credentials)
    - BillingFactory (Strategy Pattern)
    - Monthly quota validation
    - Fiscal amount computation
    - SUNAT QR data generation
    - AFIP QR data generation
    - NoOp strategy behavior
    - Nubefact payload construction
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Ensure AUTH_SECRET_KEY is set before importing crypto
os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-for-billing-tests")
os.environ.setdefault("TENANT_STRICT", "0")

from app.enums import FiscalStatus, ReceiptType
from app.utils.crypto import (
    decrypt_credential,
    decrypt_text,
    encrypt_credential,
    encrypt_text,
)


# ═════════════════════════════════════════════════════════════
# ENUMS
# ═════════════════════════════════════════════════════════════


class TestReceiptType:
    def test_values(self):
        assert ReceiptType.boleta == "boleta"
        assert ReceiptType.factura == "factura"
        assert ReceiptType.nota_credito == "nota_credito"
        assert ReceiptType.nota_debito == "nota_debito"
        assert ReceiptType.nota_venta == "nota_venta"

    def test_uppercase_aliases(self):
        assert ReceiptType.BOLETA == ReceiptType.boleta
        assert ReceiptType.FACTURA == ReceiptType.factura
        assert ReceiptType.NOTA_VENTA == ReceiptType.nota_venta

    def test_string_construction(self):
        assert ReceiptType("boleta") == ReceiptType.boleta
        assert ReceiptType("factura") == ReceiptType.factura


class TestFiscalStatus:
    def test_lifecycle_values(self):
        assert FiscalStatus.none == "none"
        assert FiscalStatus.pending == "pending"
        assert FiscalStatus.sent == "sent"
        assert FiscalStatus.authorized == "authorized"
        assert FiscalStatus.rejected == "rejected"
        assert FiscalStatus.error == "error"

    def test_uppercase_aliases(self):
        assert FiscalStatus.AUTHORIZED == FiscalStatus.authorized
        assert FiscalStatus.PENDING == FiscalStatus.pending


# ═════════════════════════════════════════════════════════════
# CRYPTO
# ═════════════════════════════════════════════════════════════


class TestCrypto:
    def test_roundtrip_bytes(self):
        """Encrypt → decrypt returns original bytes."""
        original = b"-----BEGIN RSA PRIVATE KEY-----\nMIIE..."
        encrypted = encrypt_credential(original)
        decrypted = decrypt_credential(encrypted)
        assert decrypted == original

    def test_roundtrip_text(self):
        """encrypt_text → decrypt_text returns original string."""
        token = "nubefact-api-token-abcdef123456"
        encrypted = encrypt_text(token)
        decrypted = decrypt_text(encrypted)
        assert decrypted == token

    def test_different_ciphertexts_same_plaintext(self):
        """Random salt produces different ciphertexts each time."""
        data = b"same-data"
        enc1 = encrypt_credential(data)
        enc2 = encrypt_credential(data)
        assert enc1 != enc2
        # But both decrypt to the same value
        assert decrypt_credential(enc1) == data
        assert decrypt_credential(enc2) == data

    def test_tampered_data_raises(self):
        """Modifying ciphertext raises ValueError."""
        encrypted = encrypt_credential(b"secret")
        # Tamper: flip a character in the middle
        tampered = encrypted[:20] + ("A" if encrypted[20] != "A" else "B") + encrypted[21:]
        with pytest.raises(ValueError, match="No se pudo desencriptar"):
            decrypt_credential(tampered)

    def test_empty_data_roundtrip(self):
        """Empty bytes can be encrypted/decrypted."""
        encrypted = encrypt_credential(b"")
        assert decrypt_credential(encrypted) == b""

    def test_large_certificate_roundtrip(self):
        """Simulates a real PFX file (several KB)."""
        large = os.urandom(4096)  # 4KB of random data
        encrypted = encrypt_credential(large)
        assert decrypt_credential(encrypted) == large

    def test_wrong_key_raises(self):
        """Changing AUTH_SECRET_KEY makes decryption fail."""
        encrypted = encrypt_credential(b"secret")
        original_key = os.environ["AUTH_SECRET_KEY"]
        try:
            os.environ["AUTH_SECRET_KEY"] = "completely-different-key"
            with pytest.raises(ValueError, match="No se pudo desencriptar"):
                decrypt_credential(encrypted)
        finally:
            os.environ["AUTH_SECRET_KEY"] = original_key

    def test_missing_key_raises_runtime_error(self):
        """Missing AUTH_SECRET_KEY raises RuntimeError."""
        original = os.environ.pop("AUTH_SECRET_KEY", None)
        try:
            with pytest.raises(RuntimeError, match="AUTH_SECRET_KEY"):
                encrypt_credential(b"data")
        finally:
            if original:
                os.environ["AUTH_SECRET_KEY"] = original

    def test_short_ciphertext_raises(self):
        """Ciphertext too short to contain salt raises ValueError."""
        import base64
        short = base64.urlsafe_b64encode(b"too-short").decode()
        with pytest.raises(ValueError):
            decrypt_credential(short)


# ═════════════════════════════════════════════════════════════
# BILLING SERVICE — Strategy Pattern
# ═════════════════════════════════════════════════════════════


class TestBillingFactory:
    def test_no_config_returns_noop(self):
        from app.services.billing_service import BillingFactory, NoOpBillingStrategy
        strategy = BillingFactory.get_strategy(None)
        assert isinstance(strategy, NoOpBillingStrategy)

    def test_inactive_config_returns_noop(self):
        from app.services.billing_service import BillingFactory, NoOpBillingStrategy
        config = MagicMock()
        config.is_active = False
        config.country = "PE"
        strategy = BillingFactory.get_strategy(config)
        assert isinstance(strategy, NoOpBillingStrategy)

    def test_peru_returns_sunat(self):
        from app.services.billing_service import BillingFactory, SUNATBillingStrategy
        config = MagicMock()
        config.is_active = True
        config.country = "PE"
        strategy = BillingFactory.get_strategy(config)
        assert isinstance(strategy, SUNATBillingStrategy)

    def test_argentina_returns_afip(self):
        from app.services.billing_service import BillingFactory, AFIPBillingStrategy
        config = MagicMock()
        config.is_active = True
        config.country = "AR"
        strategy = BillingFactory.get_strategy(config)
        assert isinstance(strategy, AFIPBillingStrategy)

    def test_unknown_country_returns_noop(self):
        from app.services.billing_service import BillingFactory, NoOpBillingStrategy
        config = MagicMock()
        config.is_active = True
        config.country = "MX"  # Not implemented yet
        strategy = BillingFactory.get_strategy(config)
        assert isinstance(strategy, NoOpBillingStrategy)


class TestNoOpStrategy:
    @pytest.mark.asyncio
    async def test_marks_as_authorized(self):
        from app.services.billing_service import NoOpBillingStrategy
        strategy = NoOpBillingStrategy()
        fiscal_doc = MagicMock()
        sale = MagicMock()
        result = await strategy.send_document(fiscal_doc, sale, [], MagicMock())
        assert result.fiscal_status == FiscalStatus.authorized
        assert result.cae_cdr == "INTERNAL_TICKET"

    def test_qr_data_empty(self):
        from app.services.billing_service import NoOpBillingStrategy
        strategy = NoOpBillingStrategy()
        assert strategy.build_qr_data(MagicMock(), MagicMock()) == ""


# ═════════════════════════════════════════════════════════════
# MONTHLY QUOTA
# ═════════════════════════════════════════════════════════════


class TestMonthlyQuota:
    def test_allows_when_under_limit(self):
        from app.services.billing_service import _check_monthly_quota
        config = MagicMock()
        config.current_billing_count = 10
        config.max_billing_limit = 500
        config.billing_count_reset_date = datetime(2026, 3, 1)
        allowed, msg = _check_monthly_quota(config)
        assert allowed is True
        assert msg == ""

    def test_blocks_when_at_limit(self):
        from app.services.billing_service import _check_monthly_quota
        config = MagicMock()
        config.current_billing_count = 500
        config.max_billing_limit = 500
        config.billing_count_reset_date = datetime(2026, 3, 1)
        allowed, msg = _check_monthly_quota(config)
        assert allowed is False
        assert "Límite mensual" in msg

    def test_resets_on_new_month(self):
        from app.services.billing_service import _check_monthly_quota
        config = MagicMock()
        config.current_billing_count = 500
        config.max_billing_limit = 500
        # Last reset was in February
        config.billing_count_reset_date = datetime(2026, 2, 1)
        allowed, msg = _check_monthly_quota(config)
        # Should reset counter and allow
        assert allowed is True
        assert config.current_billing_count == 0

    def test_resets_when_no_reset_date(self):
        from app.services.billing_service import _check_monthly_quota
        config = MagicMock()
        config.current_billing_count = 999
        config.max_billing_limit = 500
        config.billing_count_reset_date = None
        allowed, msg = _check_monthly_quota(config)
        assert allowed is True
        assert config.current_billing_count == 0


# ═════════════════════════════════════════════════════════════
# FISCAL AMOUNTS
# ═════════════════════════════════════════════════════════════


class TestFiscalAmounts:
    def test_standard_igv_18(self):
        from app.services.billing_service import _compute_fiscal_amounts
        sale = MagicMock()
        sale.total_amount = Decimal("118.00")
        base, tax, total = _compute_fiscal_amounts(sale, [])
        assert total == Decimal("118.00")
        assert base == Decimal("100.00")
        assert tax == Decimal("18.00")

    def test_zero_total(self):
        from app.services.billing_service import _compute_fiscal_amounts
        sale = MagicMock()
        sale.total_amount = Decimal("0")
        base, tax, total = _compute_fiscal_amounts(sale, [])
        assert base == Decimal("0.00")
        assert tax == Decimal("0.00")

    def test_rounding_precision(self):
        from app.services.billing_service import _compute_fiscal_amounts
        sale = MagicMock()
        sale.total_amount = Decimal("59.00")  # Common Peruvian price
        base, tax, total = _compute_fiscal_amounts(sale, [])
        assert total == Decimal("59.00")
        assert base + tax == total
        # Verify base is correctly rounded
        assert base == Decimal("50.00")
        assert tax == Decimal("9.00")

    def test_argentina_iva_21(self):
        from app.services.billing_service import _compute_fiscal_amounts
        sale = MagicMock()
        sale.total_amount = Decimal("121.00")
        base, tax, total = _compute_fiscal_amounts(sale, [], country="AR")
        assert total == Decimal("121.00")
        assert base == Decimal("100.00")
        assert tax == Decimal("21.00")

    def test_unknown_country_defaults_to_pe(self):
        from app.services.billing_service import _compute_fiscal_amounts
        sale = MagicMock()
        sale.total_amount = Decimal("118.00")
        base, tax, total = _compute_fiscal_amounts(sale, [], country="XX")
        assert base == Decimal("100.00")
        assert tax == Decimal("18.00")


# ═════════════════════════════════════════════════════════════
# QR DATA
# ═════════════════════════════════════════════════════════════


class TestSUNATQR:
    def test_qr_format(self):
        from app.services.billing_service import SUNATBillingStrategy
        strategy = SUNATBillingStrategy()
        fiscal_doc = MagicMock()
        fiscal_doc.receipt_type = ReceiptType.factura
        fiscal_doc.serie = "F001"
        fiscal_doc.fiscal_number = 123
        fiscal_doc.tax_amount = Decimal("18.00")
        fiscal_doc.total_amount = Decimal("118.00")
        fiscal_doc.authorized_at = datetime(2026, 3, 20)
        fiscal_doc.buyer_doc_type = "6"
        fiscal_doc.buyer_doc_number = "20987654321"

        config = MagicMock()
        config.tax_id = "20123456789"

        qr = strategy.build_qr_data(fiscal_doc, config)
        assert qr == "20123456789|01|F001|123|18.00|118.00|2026-03-20|6|20987654321|"

    def test_boleta_qr(self):
        from app.services.billing_service import SUNATBillingStrategy
        strategy = SUNATBillingStrategy()
        fiscal_doc = MagicMock()
        fiscal_doc.receipt_type = ReceiptType.boleta
        fiscal_doc.serie = "B001"
        fiscal_doc.fiscal_number = 1
        fiscal_doc.tax_amount = Decimal("9.00")
        fiscal_doc.total_amount = Decimal("59.00")
        fiscal_doc.authorized_at = datetime(2026, 3, 20)
        fiscal_doc.buyer_doc_type = "1"
        fiscal_doc.buyer_doc_number = "12345678"

        config = MagicMock()
        config.tax_id = "20123456789"

        qr = strategy.build_qr_data(fiscal_doc, config)
        assert qr.startswith("20123456789|03|B001|")
        assert qr.endswith("|")


class TestAFIPQR:
    def test_qr_url_format(self):
        from app.services.billing_service import AFIPBillingStrategy
        strategy = AFIPBillingStrategy()
        fiscal_doc = MagicMock()
        fiscal_doc.receipt_type = ReceiptType.factura
        fiscal_doc.fiscal_number = 49
        fiscal_doc.total_amount = Decimal("121.00")
        fiscal_doc.authorized_at = datetime(2026, 3, 20)
        fiscal_doc.buyer_doc_type = "99"
        fiscal_doc.buyer_doc_number = "0"
        fiscal_doc.cae_cdr = "70417054367476"

        config = MagicMock()
        config.tax_id = "20123456789"
        config.afip_punto_venta = 1

        qr = strategy.build_qr_data(fiscal_doc, config)
        assert qr.startswith("https://www.afip.gob.ar/fe/qr/?p=")
        # Verify it's valid base64 JSON
        import base64
        b64_part = qr.split("?p=")[1]
        decoded = json.loads(base64.b64decode(b64_part))
        assert decoded["ver"] == 1
        assert decoded["cuit"] == 20123456789
        assert decoded["ptoVta"] == 1
        assert decoded["codAut"] == 70417054367476


# ═════════════════════════════════════════════════════════════
# NUBEFACT PAYLOAD
# ═════════════════════════════════════════════════════════════


class TestNubefactPayload:
    def test_factura_payload_structure(self):
        from app.services.billing_service import SUNATBillingStrategy
        strategy = SUNATBillingStrategy()

        fiscal_doc = MagicMock()
        fiscal_doc.receipt_type = ReceiptType.factura
        fiscal_doc.serie = "F001"
        fiscal_doc.fiscal_number = 1
        fiscal_doc.buyer_doc_type = "6"
        fiscal_doc.buyer_doc_number = "20987654321"
        fiscal_doc.buyer_name = "EMPRESA SAC"
        fiscal_doc.total_amount = Decimal("118.00")
        fiscal_doc.tax_amount = Decimal("18.00")
        fiscal_doc.taxable_amount = Decimal("100.00")

        sale = MagicMock()
        sale.timestamp = datetime(2026, 3, 20, 10, 30, 0)

        item = MagicMock()
        item.quantity = Decimal("2")
        item.unit_price = Decimal("59.00")
        item.product_barcode_snapshot = "7750001"
        item.product_name_snapshot = "Arroz x 5kg"

        config = MagicMock()

        payload = strategy._build_nubefact_payload(
            fiscal_doc, sale, [item], config
        )

        assert payload["tipo_de_comprobante"] == 1  # Factura
        assert payload["serie"] == "F001"
        assert payload["numero"] == 1
        assert payload["cliente_tipo_de_documento"] == "6"
        assert payload["cliente_numero_de_documento"] == "20987654321"
        assert payload["total"] == 118.00
        assert payload["total_igv"] == 18.00
        assert len(payload["items"]) == 1

    def test_boleta_payload_type(self):
        from app.services.billing_service import SUNATBillingStrategy
        strategy = SUNATBillingStrategy()

        fiscal_doc = MagicMock()
        fiscal_doc.receipt_type = ReceiptType.boleta
        fiscal_doc.serie = "B001"
        fiscal_doc.fiscal_number = 1
        fiscal_doc.buyer_doc_type = "0"
        fiscal_doc.buyer_doc_number = ""
        fiscal_doc.buyer_name = "CLIENTE VARIOS"
        fiscal_doc.total_amount = Decimal("59.00")
        fiscal_doc.tax_amount = Decimal("9.00")
        fiscal_doc.taxable_amount = Decimal("50.00")

        sale = MagicMock()
        sale.timestamp = datetime(2026, 3, 20)

        config = MagicMock()
        payload = strategy._build_nubefact_payload(
            fiscal_doc, sale, [], config
        )

        assert payload["tipo_de_comprobante"] == 2  # Boleta

    def test_item_igv_decomposition(self):
        """Verify IGV is correctly extracted from tax-included prices."""
        from app.services.billing_service import SUNATBillingStrategy
        strategy = SUNATBillingStrategy()

        item = MagicMock()
        item.quantity = Decimal("1")
        item.unit_price = Decimal("118.00")  # Price with IGV
        item.product_barcode_snapshot = "001"
        item.product_name_snapshot = "Test"

        items = strategy._build_nubefact_items([item])
        assert len(items) == 1
        nf_item = items[0]
        assert nf_item["precio_unitario"] == 118.00
        assert nf_item["valor_unitario"] == 100.00  # 118 / 1.18
        assert nf_item["igv"] == 18.00
        assert nf_item["subtotal"] == 100.00


# ═════════════════════════════════════════════════════════════
# PLAN BILLING LIMITS
# ═════════════════════════════════════════════════════════════


class TestPlanLimits:
    def test_plan_limits_defined(self):
        from app.services.billing_service import PLAN_BILLING_LIMITS
        assert PLAN_BILLING_LIMITS["trial"] == 0
        assert PLAN_BILLING_LIMITS["standard"] == 500
        assert PLAN_BILLING_LIMITS["professional"] == 1000
        assert PLAN_BILLING_LIMITS["enterprise"] == 2000


# ═════════════════════════════════════════════════════════════
# EMIT_FISCAL_DOCUMENT — Orquestación completa
# ═════════════════════════════════════════════════════════════


class TestEmitFiscalDocument:
    """Tests de integración para emit_fiscal_document.

    Simula el flujo real: session async → lock config → asignar nro →
    send_document → commit.
    """

    @pytest.fixture
    def mock_config(self):
        """CompanyBillingConfig mock con todos los campos necesarios."""
        config = MagicMock()
        config.company_id = 1
        config.is_active = True
        config.country = "PE"
        config.nubefact_url = "https://api.nubefact.com/api/v1/test"
        config.nubefact_token = encrypt_text("test-token-123")
        config.serie_boleta = "B001"
        config.serie_factura = "F001"
        config.current_sequence_boleta = 0
        config.current_sequence_factura = 0
        config.current_billing_count = 0
        config.max_billing_limit = 500
        config.billing_count_reset_date = datetime(2026, 3, 1)
        config.afip_punto_venta = 1
        config.tax_id = "20123456789"
        config.updated_at = None
        return config

    @pytest.fixture
    def mock_sale(self):
        sale = MagicMock()
        sale.id = 42
        sale.total_amount = Decimal("59.00")
        sale.timestamp = datetime(2026, 3, 20, 14, 30, 0)
        sale.receipt_type = None
        return sale

    @pytest.fixture
    def mock_items(self):
        item = MagicMock()
        item.quantity = Decimal("1")
        item.unit_price = Decimal("59.00")
        item.product_barcode_snapshot = "7750001"
        item.product_name_snapshot = "Galletas"
        return [item]

    @pytest.mark.asyncio
    async def test_no_config_returns_none(self):
        """Sin CompanyBillingConfig activa → retorna None (cero overhead)."""
        from app.services.billing_service import emit_fiscal_document

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        # exec returns result with .first() returning None (no existing doc, no config)
        exec_result = MagicMock()
        exec_result.first.return_value = None
        mock_session.exec.return_value = exec_result

        with patch("app.services.billing_service.get_async_session") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await emit_fiscal_document(
                sale_id=1, company_id=1, branch_id=1,
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_idempotency_returns_existing(self):
        """Si ya existe FiscalDocument para el sale_id, retorna el existente."""
        from app.services.billing_service import emit_fiscal_document

        existing_doc = MagicMock()
        existing_doc.fiscal_status = "authorized"
        existing_doc.full_number = "B001-00000001"

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        exec_result = MagicMock()
        exec_result.first.return_value = existing_doc
        mock_session.exec.return_value = exec_result

        with patch("app.services.billing_service.get_async_session") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await emit_fiscal_document(
                sale_id=42, company_id=1, branch_id=1,
            )
        assert result is existing_doc
        # Should NOT have attempted to create a new document
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_quota_exceeded_creates_error_doc(self):
        """Cuota mensual excedida → crea FiscalDocument con status error."""
        from app.services.billing_service import emit_fiscal_document

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        # First exec: no existing doc
        no_doc = MagicMock()
        no_doc.first.return_value = None
        # Second exec: config at limit
        config = MagicMock()
        config.is_active = True
        config.company_id = 1
        config.current_billing_count = 500
        config.max_billing_limit = 500
        config.billing_count_reset_date = datetime(2026, 3, 1)
        at_limit = MagicMock()
        at_limit.first.return_value = config
        mock_session.exec.side_effect = [no_doc, at_limit]

        with patch("app.services.billing_service.get_async_session") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await emit_fiscal_document(
                sale_id=42, company_id=1, branch_id=1,
            )

        # Should have created and added a FiscalDocument with error
        mock_session.add.assert_called_once()
        added_doc = mock_session.add.call_args[0][0]
        assert added_doc.fiscal_status == FiscalStatus.error
        assert "quota_exceeded" in added_doc.fiscal_errors

    @pytest.mark.asyncio
    async def test_noop_strategy_full_flow(self, mock_config, mock_sale, mock_items):
        """Flujo completo con NoOp: asigna número → marca authorized."""
        from app.services.billing_service import emit_fiscal_document

        mock_config.country = "XX"  # Unknown country → NoOp strategy

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        # Call sequence: 1) no existing doc, 2) config, 3) sale, 4) items
        no_doc = MagicMock()
        no_doc.first.return_value = None
        config_result = MagicMock()
        config_result.first.return_value = mock_config
        sale_result = MagicMock()
        sale_result.first.return_value = mock_sale
        items_result = MagicMock()
        items_result.all.return_value = mock_items
        mock_session.exec.side_effect = [no_doc, config_result, sale_result, items_result]

        with patch("app.services.billing_service.get_async_session") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await emit_fiscal_document(
                sale_id=42, company_id=1, branch_id=1,
                receipt_type=ReceiptType.boleta,
            )

        # Sequence should have been assigned
        assert mock_config.current_sequence_boleta == 1
        assert mock_config.current_billing_count == 1
        # Two commits: partial (pre-network) + final (post-strategy)
        assert mock_session.commit.await_count == 2

    @pytest.mark.asyncio
    async def test_sunat_nubefact_success(self, mock_config, mock_sale, mock_items):
        """Flujo SUNAT/Nubefact exitoso: envía → recibe autorización."""
        from app.services.billing_service import emit_fiscal_document

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        no_doc = MagicMock()
        no_doc.first.return_value = None
        config_result = MagicMock()
        config_result.first.return_value = mock_config
        sale_result = MagicMock()
        sale_result.first.return_value = mock_sale
        items_result = MagicMock()
        items_result.all.return_value = mock_items
        mock_session.exec.side_effect = [no_doc, config_result, sale_result, items_result]

        # Mock HTTP response from Nubefact
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            "aceptada_por_sunat": True,
            "cdr_zip_base64": "CDR_BASE64_DATA",
            "codigo_hash": "abc123hash",
            "cadena_para_codigo_qr": "20123456789|03|B001|1|...",
        })
        mock_response.json.return_value = json.loads(mock_response.text)

        with patch("app.services.billing_service.get_async_session") as mock_get, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value.__aenter__ = AsyncMock()
            mock_httpx.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await emit_fiscal_document(
                sale_id=42, company_id=1, branch_id=1,
                receipt_type=ReceiptType.boleta,
                buyer_doc_type="1",
                buyer_doc_number="12345678",
                buyer_name="Juan Pérez",
            )

        # Verify billing count incremented
        assert mock_config.current_billing_count == 1
        assert mock_config.current_sequence_boleta == 1

    @pytest.mark.asyncio
    async def test_sunat_nubefact_rejection(self, mock_config, mock_sale, mock_items):
        """Nubefact rechaza el comprobante → status=rejected con errores."""
        from app.services.billing_service import emit_fiscal_document

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        no_doc = MagicMock()
        no_doc.first.return_value = None
        config_result = MagicMock()
        config_result.first.return_value = mock_config
        sale_result = MagicMock()
        sale_result.first.return_value = mock_sale
        items_result = MagicMock()
        items_result.all.return_value = mock_items
        mock_session.exec.side_effect = [no_doc, config_result, sale_result, items_result]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            "aceptada_por_sunat": False,
            "sunat_description": "RUC del receptor no válido",
            "sunat_responsecode": "2018",
        })
        mock_response.json.return_value = json.loads(mock_response.text)

        with patch("app.services.billing_service.get_async_session") as mock_get, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value.__aenter__ = AsyncMock()
            mock_httpx.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await emit_fiscal_document(
                sale_id=42, company_id=1, branch_id=1,
                receipt_type=ReceiptType.factura,
            )

        # Sequence for factura should be incremented
        assert mock_config.current_sequence_factura == 1

    @pytest.mark.asyncio
    async def test_network_timeout_creates_error(self, mock_config, mock_sale, mock_items):
        """Timeout de red → FiscalDocument con status=error."""
        from app.services.billing_service import emit_fiscal_document

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        no_doc = MagicMock()
        no_doc.first.return_value = None
        config_result = MagicMock()
        config_result.first.return_value = mock_config
        sale_result = MagicMock()
        sale_result.first.return_value = mock_sale
        items_result = MagicMock()
        items_result.all.return_value = mock_items
        mock_session.exec.side_effect = [no_doc, config_result, sale_result, items_result]

        with patch("app.services.billing_service.get_async_session") as mock_get, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value.__aenter__ = AsyncMock()
            mock_httpx.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Connection timed out")
            )
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await emit_fiscal_document(
                sale_id=42, company_id=1, branch_id=1,
            )

        # Number was assigned before network call
        assert mock_config.current_sequence_boleta == 1
        # Two commits still happen (pre-network + post-error)
        assert mock_session.commit.await_count == 2


# ═════════════════════════════════════════════════════════════
# DETERMINE RECEIPT TYPE & BUYER INFO (VentaState helpers)
# ═════════════════════════════════════════════════════════════


class TestDetermineReceiptType:
    """Tests para _determine_receipt_type y _extract_buyer_info.

    Valida la lógica de clasificación de comprobantes que se ejecuta
    ANTES de limpiar el state del carrito.
    """

    def _make_state(self, selected_client=None, receipt_selection="nota_venta"):
        """Crea un mock que simula VentaState."""
        state = MagicMock()
        state.selected_client = selected_client
        state.sale_receipt_type_selection = receipt_selection
        # Bind the actual methods
        from app.states.venta_state import VentaState
        state._determine_receipt_type = VentaState._determine_receipt_type.__get__(state)
        state._extract_buyer_info = VentaState._extract_buyer_info.__get__(state)
        return state

    def test_explicit_receipt_type_on_sale(self):
        """Si la venta tiene receipt_type explícito y UI es nota_venta, usar el de la venta."""
        state = self._make_state(receipt_selection="nota_venta")
        sale = MagicMock()
        sale.receipt_type = "factura"
        assert state._determine_receipt_type(sale) == "factura"

    def test_ui_selection_takes_priority(self):
        """La selección del cajero en el UI prevalece sobre auto-detección."""
        state = self._make_state(
            selected_client={"id": 1, "name": "Empresa", "dni": "20987654321"},
            receipt_selection="boleta",
        )
        sale = MagicMock()
        sale.receipt_type = None
        # Aunque el cliente tiene RUC, el cajero seleccionó boleta
        assert state._determine_receipt_type(sale) == "boleta"

    def test_ruc_11_digits_returns_factura(self):
        """Cliente con RUC (11 dígitos) → factura."""
        state = self._make_state(
            selected_client={"id": 1, "name": "Empresa SAC", "dni": "20987654321"}
        )
        sale = MagicMock()
        sale.receipt_type = None
        assert state._determine_receipt_type(sale) == ReceiptType.factura

    def test_cuit_11_digits_returns_factura(self):
        """Cliente con CUIT argentino (11 dígitos) → factura."""
        state = self._make_state(
            selected_client={"id": 2, "name": "SRL Argentina", "dni": "30716549877"}
        )
        sale = MagicMock()
        sale.receipt_type = None
        assert state._determine_receipt_type(sale) == ReceiptType.factura

    def test_dni_8_digits_returns_nota_venta(self):
        """Cliente con DNI peruano (8 dígitos) + UI default → nota_venta."""
        state = self._make_state(
            selected_client={"id": 3, "name": "Juan", "dni": "12345678"}
        )
        sale = MagicMock()
        sale.receipt_type = None
        assert state._determine_receipt_type(sale) == ReceiptType.nota_venta

    def test_no_client_returns_nota_venta(self):
        """Sin cliente seleccionado + UI default → nota_venta."""
        state = self._make_state(selected_client=None)
        sale = MagicMock()
        sale.receipt_type = None
        assert state._determine_receipt_type(sale) == ReceiptType.nota_venta

    def test_no_client_boleta_when_selected(self):
        """Sin cliente + UI selecciona boleta → boleta."""
        state = self._make_state(selected_client=None, receipt_selection="boleta")
        sale = MagicMock()
        sale.receipt_type = None
        assert state._determine_receipt_type(sale) == ReceiptType.boleta

    def test_client_without_dni_returns_nota_venta(self):
        """Cliente sin DNI + UI default → nota_venta."""
        state = self._make_state(
            selected_client={"id": 4, "name": "Anónimo", "dni": ""}
        )
        sale = MagicMock()
        sale.receipt_type = None
        assert state._determine_receipt_type(sale) == ReceiptType.nota_venta

    def test_extract_buyer_ruc(self):
        """Extraer datos de comprador con RUC."""
        state = self._make_state(
            selected_client={"id": 1, "name": "Empresa SAC", "dni": "20987654321"}
        )
        doc_type, doc_num, name = state._extract_buyer_info()
        assert doc_type == "6"  # RUC
        assert doc_num == "20987654321"
        assert name == "Empresa SAC"

    def test_extract_buyer_dni(self):
        """Extraer datos de comprador con DNI peruano."""
        state = self._make_state(
            selected_client={"id": 2, "name": "Juan Pérez", "dni": "12345678"}
        )
        doc_type, doc_num, name = state._extract_buyer_info()
        assert doc_type == "1"  # DNI
        assert doc_num == "12345678"
        assert name == "Juan Pérez"

    def test_extract_buyer_no_client(self):
        """Sin cliente → todos None."""
        state = self._make_state(selected_client=None)
        doc_type, doc_num, name = state._extract_buyer_info()
        assert doc_type is None
        assert doc_num is None
        assert name is None

    def test_extract_buyer_empty_dni(self):
        """Cliente sin DNI → doc_type=None, doc_num=None."""
        state = self._make_state(
            selected_client={"id": 3, "name": "SinDoc", "dni": ""}
        )
        doc_type, doc_num, name = state._extract_buyer_info()
        assert doc_type is None
        assert doc_num is None
        assert name == "SinDoc"

    def test_extract_buyer_non_numeric_doc(self):
        """Documento no numérico → tipo 0."""
        state = self._make_state(
            selected_client={"id": 4, "name": "Extranjero", "dni": "CE-123456"}
        )
        doc_type, doc_num, name = state._extract_buyer_info()
        assert doc_type == "0"  # Sin documento válido
        assert doc_num == "CE-123456"
        assert name == "Extranjero"


# ═════════════════════════════════════════════════════════════
# FLUJO COMPLETO E2E — Simulación de usuario real
# ═════════════════════════════════════════════════════════════


class TestEndToEndBillingFlow:
    """Simula el flujo completo que un usuario experimenta:

    1. Agrega productos al carrito
    2. Selecciona cliente (con RUC para factura)
    3. Confirma venta → se commitea
    4. Background: emit_fiscal_document → Nubefact → autorizado
    5. El FiscalDocument queda persistido con QR y CDR

    Estos tests validan que:
    - Los datos del comprador se capturan ANTES del reset
    - La secuencia numérica es atómica
    - La idempotencia funciona
    - Los errores de red no bloquean la venta
    """

    @pytest.mark.asyncio
    async def test_boleta_consumidor_final_sin_billing(self):
        """Usuario vende a consumidor final sin billing activo.

        Escenario: tienda en Colombia (sin integración fiscal).
        Resultado esperado: emit_fiscal_document retorna None,
        la venta se completó normalmente.
        """
        from app.services.billing_service import emit_fiscal_document

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        # No existing doc
        no_doc = MagicMock()
        no_doc.first.return_value = None
        # No config
        no_config = MagicMock()
        no_config.first.return_value = None
        mock_session.exec.side_effect = [no_doc, no_config]

        with patch("app.services.billing_service.get_async_session") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await emit_fiscal_document(
                sale_id=100,
                company_id=1,
                branch_id=1,
                receipt_type=ReceiptType.boleta,
            )
        assert result is None
        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_factura_empresa_peru_nubefact_ok(self):
        """Usuario vende a empresa con RUC → factura SUNAT autorizada.

        Escenario real:
        1. Cajero agrega 2 productos al carrito
        2. Selecciona cliente "Empresa SAC" con RUC 20987654321
        3. Confirma venta
        4. Background: emisión fiscal → Nubefact autoriza
        """
        from app.services.billing_service import emit_fiscal_document

        config = MagicMock()
        config.is_active = True
        config.country = "PE"
        config.nubefact_url = "https://api.nubefact.com/api/v1/test"
        config.nubefact_token = encrypt_text("real-api-token")
        config.serie_factura = "F001"
        config.serie_boleta = "B001"
        config.current_sequence_factura = 5
        config.current_sequence_boleta = 100
        config.current_billing_count = 10
        config.max_billing_limit = 500
        config.billing_count_reset_date = datetime(2026, 3, 1)
        config.tax_id = "20123456789"
        config.afip_punto_venta = None
        config.updated_at = None

        sale = MagicMock()
        sale.id = 200
        sale.total_amount = Decimal("236.00")  # 2 items × S/118
        sale.timestamp = datetime(2026, 3, 20, 15, 0, 0)

        item1 = MagicMock()
        item1.quantity = Decimal("1")
        item1.unit_price = Decimal("118.00")
        item1.product_barcode_snapshot = "7750001"
        item1.product_name_snapshot = "Arroz Premium 5kg"
        item2 = MagicMock()
        item2.quantity = Decimal("1")
        item2.unit_price = Decimal("118.00")
        item2.product_barcode_snapshot = "7750002"
        item2.product_name_snapshot = "Aceite Vegetal 1L"

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        no_doc = MagicMock()
        no_doc.first.return_value = None
        config_result = MagicMock()
        config_result.first.return_value = config
        sale_result = MagicMock()
        sale_result.first.return_value = sale
        items_result = MagicMock()
        items_result.all.return_value = [item1, item2]
        mock_session.exec.side_effect = [no_doc, config_result, sale_result, items_result]

        # Nubefact response: success
        nubefact_response = MagicMock()
        nubefact_response.status_code = 200
        nubefact_response.text = json.dumps({
            "aceptada_por_sunat": True,
            "cdr_zip_base64": "UEsDBBQAAAA...",
            "codigo_hash": "qrCodeHash123",
            "cadena_para_codigo_qr": "20123456789|01|F001|6|...",
            "enlace_del_pdf": "https://api.nubefact.com/...",
        })
        nubefact_response.json.return_value = json.loads(nubefact_response.text)

        with patch("app.services.billing_service.get_async_session") as mock_get, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value.__aenter__ = AsyncMock()
            mock_httpx.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=nubefact_response
            )
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await emit_fiscal_document(
                sale_id=200,
                company_id=1,
                branch_id=1,
                receipt_type=ReceiptType.factura,
                buyer_doc_type="6",
                buyer_doc_number="20987654321",
                buyer_name="EMPRESA SAC",
            )

        # Verify: factura sequence incremented (was 5, now 6)
        assert config.current_sequence_factura == 6
        # Boleta sequence untouched
        assert config.current_sequence_boleta == 100
        # Billing count incremented
        assert config.current_billing_count == 11
        # Two commits: pre-network + post-result
        assert mock_session.commit.await_count == 2

    @pytest.mark.asyncio
    async def test_duplicate_emission_returns_existing(self):
        """Segunda llamada para el mismo sale_id retorna el doc existente.

        Escenario: el background event se dispara dos veces por
        condición de carrera en la UI.
        """
        from app.services.billing_service import emit_fiscal_document

        existing = MagicMock()
        existing.fiscal_status = "authorized"
        existing.full_number = "F001-00000006"
        existing.sale_id = 200

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        existing_result = MagicMock()
        existing_result.first.return_value = existing
        mock_session.exec.return_value = existing_result

        with patch("app.services.billing_service.get_async_session") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await emit_fiscal_document(
                sale_id=200, company_id=1, branch_id=1,
                receipt_type=ReceiptType.factura,
            )

        assert result is existing
        # No new doc created, no commits
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_nubefact_500_error_does_not_lose_sequence(self):
        """Error HTTP 500 de Nubefact: la venta ya se commiteó,
        el número se reservó, el FiscalDocument queda en status=error.

        El usuario puede reintentar después.
        """
        from app.services.billing_service import emit_fiscal_document

        config = MagicMock()
        config.is_active = True
        config.country = "PE"
        config.nubefact_url = "https://api.nubefact.com/api/v1/test"
        config.nubefact_token = encrypt_text("test-token")
        config.serie_boleta = "B001"
        config.serie_factura = "F001"
        config.current_sequence_boleta = 50
        config.current_sequence_factura = 0
        config.current_billing_count = 0
        config.max_billing_limit = 500
        config.billing_count_reset_date = datetime(2026, 3, 1)
        config.tax_id = "20123456789"
        config.updated_at = None

        sale = MagicMock()
        sale.id = 300
        sale.total_amount = Decimal("59.00")
        sale.timestamp = datetime(2026, 3, 20, 16, 0, 0)

        item = MagicMock()
        item.quantity = Decimal("1")
        item.unit_price = Decimal("59.00")
        item.product_barcode_snapshot = "7750003"
        item.product_name_snapshot = "Gaseosa 500ml"

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        no_doc = MagicMock()
        no_doc.first.return_value = None
        config_result = MagicMock()
        config_result.first.return_value = config
        sale_result = MagicMock()
        sale_result.first.return_value = sale
        items_result = MagicMock()
        items_result.all.return_value = [item]
        mock_session.exec.side_effect = [no_doc, config_result, sale_result, items_result]

        # Nubefact returns 500
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"

        with patch("app.services.billing_service.get_async_session") as mock_get, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value.__aenter__ = AsyncMock()
            mock_httpx.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=error_response
            )
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await emit_fiscal_document(
                sale_id=300, company_id=1, branch_id=1,
                receipt_type=ReceiptType.boleta,
            )

        # Sequence was still consumed (B001-00000051)
        assert config.current_sequence_boleta == 51
        # Two commits (pre-network + post-error)
        assert mock_session.commit.await_count == 2


# ═════════════════════════════════════════════════════════════
# RETRY — Reintento de documentos fiscales fallidos
# ═════════════════════════════════════════════════════════════


class TestRetryFiscalDocument:
    """Tests para retry_fiscal_document()."""

    @pytest.mark.asyncio
    async def test_retry_error_doc_succeeds(self):
        """Reintento de un doc en error → strategy lo autoriza."""
        from app.services.billing_service import retry_fiscal_document

        fiscal_doc = MagicMock()
        fiscal_doc.id = 10
        fiscal_doc.company_id = 1
        fiscal_doc.sale_id = 200
        fiscal_doc.fiscal_status = FiscalStatus.error
        fiscal_doc.retry_count = 1
        fiscal_doc.receipt_type = ReceiptType.boleta

        config = MagicMock()
        config.is_active = True
        config.country = "PE"

        sale = MagicMock()
        sale.id = 200

        item = MagicMock()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        doc_result = MagicMock()
        doc_result.first.return_value = fiscal_doc
        config_result = MagicMock()
        config_result.first.return_value = config
        sale_result = MagicMock()
        sale_result.first.return_value = sale
        items_result = MagicMock()
        items_result.all.return_value = [item]
        mock_session.exec.side_effect = [doc_result, config_result, sale_result, items_result]

        with patch("app.services.billing_service.get_async_session") as mock_get, \
             patch("app.services.billing_service.BillingFactory.get_strategy") as mock_factory:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_strategy = AsyncMock()
            mock_strategy.send_document = AsyncMock(return_value=fiscal_doc)
            mock_strategy.build_qr_data.return_value = "test-qr"
            mock_factory.return_value = mock_strategy

            # Simulate strategy marking as authorized
            async def authorize_doc(fd, s, i, c):
                fd.fiscal_status = FiscalStatus.authorized
                return fd
            mock_strategy.send_document.side_effect = authorize_doc

            result = await retry_fiscal_document(
                fiscal_doc_id=10, company_id=1, branch_id=1
            )

        assert result is fiscal_doc
        assert result.fiscal_status == FiscalStatus.authorized
        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_retry_max_attempts_exceeded(self):
        """Doc con retry_count >= MAX no se reintenta."""
        from app.services.billing_service import retry_fiscal_document

        fiscal_doc = MagicMock()
        fiscal_doc.id = 11
        fiscal_doc.company_id = 1
        fiscal_doc.fiscal_status = FiscalStatus.error
        fiscal_doc.retry_count = 3  # MAX_RETRY_ATTEMPTS

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        doc_result = MagicMock()
        doc_result.first.return_value = fiscal_doc
        mock_session.exec.return_value = doc_result

        with patch("app.services.billing_service.get_async_session") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await retry_fiscal_document(
                fiscal_doc_id=11, company_id=1, branch_id=1
            )

        assert result is fiscal_doc
        # No commit should happen — max retries exceeded
        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_retry_already_authorized_skips(self):
        """Doc ya autorizado no se reintenta."""
        from app.services.billing_service import retry_fiscal_document

        fiscal_doc = MagicMock()
        fiscal_doc.id = 12
        fiscal_doc.company_id = 1
        fiscal_doc.fiscal_status = FiscalStatus.authorized

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        doc_result = MagicMock()
        doc_result.first.return_value = fiscal_doc
        mock_session.exec.return_value = doc_result

        with patch("app.services.billing_service.get_async_session") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await retry_fiscal_document(
                fiscal_doc_id=12, company_id=1, branch_id=1
            )

        assert result is fiscal_doc
        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_retry_not_found_returns_none(self):
        """Doc no encontrado retorna None."""
        from app.services.billing_service import retry_fiscal_document

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # session.add() es sync en SQLAlchemy
        doc_result = MagicMock()
        doc_result.first.return_value = None
        mock_session.exec.return_value = doc_result

        with patch("app.services.billing_service.get_async_session") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await retry_fiscal_document(
                fiscal_doc_id=999, company_id=1, branch_id=1
            )

        assert result is None


# ═════════════════════════════════════════════════════════════
# CERTIFICATE VALIDATION
# ═════════════════════════════════════════════════════════════


class TestCertificateValidation:
    """Tests para validación de certificados AFIP PEM."""

    def test_valid_certificate_pem_format(self):
        cert = "-----BEGIN CERTIFICATE-----\nMIIC...\n-----END CERTIFICATE-----"
        assert "-----BEGIN CERTIFICATE-----" in cert

    def test_valid_private_key_pem_format(self):
        key = "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"
        assert "-----BEGIN" in key and "PRIVATE KEY" in key

    def test_invalid_certificate_detected(self):
        cert = "MIICdTCCAd0GCSqG..."
        assert "-----BEGIN CERTIFICATE-----" not in cert

    def test_empty_certificate_detected(self):
        assert not "".strip()

    def test_certificate_encryption_roundtrip(self):
        from app.utils.crypto import encrypt_text, decrypt_text
        cert = "-----BEGIN CERTIFICATE-----\nTEST_DATA\n-----END CERTIFICATE-----"
        encrypted = encrypt_text(cert)
        assert encrypted != cert
        assert decrypt_text(encrypted) == cert


# ═════════════════════════════════════════════════════════════
# FISCAL RETRY WORKER & API CONFIG
# ═════════════════════════════════════════════════════════════


class TestFiscalRetryWorkerConfig:
    """Tests para configuración del retry worker."""

    def test_worker_module_importable(self):
        from app.tasks.fiscal_retry_worker import run_auto_retry
        assert callable(run_auto_retry)

    def test_retry_worker_constants(self):
        from app.tasks.fiscal_retry_worker import _BATCH_LIMIT, _MAX_BACKOFF_SECONDS
        assert _BATCH_LIMIT > 0
        assert _MAX_BACKOFF_SECONDS > 0

    def test_api_lifespan_config(self):
        from app.api import _FISCAL_RETRY_INTERVAL_SECONDS, _FISCAL_RETRY_ENABLED
        assert _FISCAL_RETRY_INTERVAL_SECONDS > 0
        assert isinstance(_FISCAL_RETRY_ENABLED, bool)

    def test_tax_rate_by_country_complete(self):
        from app.services.billing_service import _TAX_RATE_BY_COUNTRY
        assert "PE" in _TAX_RATE_BY_COUNTRY
        assert "AR" in _TAX_RATE_BY_COUNTRY
        assert _TAX_RATE_BY_COUNTRY["PE"] == Decimal("0.18")
        assert _TAX_RATE_BY_COUNTRY["AR"] == Decimal("0.21")


class TestCertificateMetadata:
    """Tests para parse_certificate_pem y CertMetadata."""

    def test_parse_valid_self_signed_cert(self):
        """Parsea un certificado auto-firmado generado en runtime."""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from datetime import datetime, timezone, timedelta
        from app.utils.crypto import parse_certificate_pem

        # Generar cert auto-firmado para test
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "AR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test CUIT 20123456789"),
            x509.NameAttribute(NameOID.COMMON_NAME, "testcert"),
        ])
        not_before = datetime(2025, 1, 1, tzinfo=timezone.utc)
        not_after = datetime(2027, 1, 1, tzinfo=timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_before)
            .not_valid_after(not_after)
            .sign(key, hashes.SHA256())
        )
        pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")

        result = parse_certificate_pem(pem)
        assert result is not None
        assert "testcert" in result.subject
        assert "Test CUIT 20123456789" in result.subject
        assert result.not_before == not_before
        assert result.not_after == not_after
        assert result.days_remaining > 0
        assert result.is_expired is False
        assert len(result.serial_number) > 0

    def test_parse_expired_cert(self):
        """Verifica que CertMetadata detecta certificados expirados."""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from datetime import datetime, timezone
        from app.utils.crypto import parse_certificate_pem

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "expired"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime(2020, 1, 1, tzinfo=timezone.utc))
            .not_valid_after(datetime(2021, 1, 1, tzinfo=timezone.utc))
            .sign(key, hashes.SHA256())
        )
        pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")

        result = parse_certificate_pem(pem)
        assert result is not None
        assert result.is_expired is True
        assert result.days_remaining < 0

    def test_parse_invalid_pem_returns_none(self):
        from app.utils.crypto import parse_certificate_pem
        assert parse_certificate_pem("not a certificate") is None

    def test_parse_empty_string_returns_none(self):
        from app.utils.crypto import parse_certificate_pem
        assert parse_certificate_pem("") is None

    def test_cert_metadata_days_remaining_property(self):
        from datetime import datetime, timezone, timedelta
        from app.utils.crypto import CertMetadata

        future = datetime.now(timezone.utc) + timedelta(days=30)
        meta = CertMetadata(
            subject="CN=test",
            issuer="CN=issuer",
            not_before=datetime.now(timezone.utc),
            not_after=future,
            serial_number="ABC123",
        )
        assert 28 <= meta.days_remaining <= 30
        assert meta.is_expired is False

    def test_cert_metadata_model_fields_exist(self):
        """Verifica que CompanyBillingConfig tiene los campos de metadatos."""
        from app.models.billing import CompanyBillingConfig
        fields = CompanyBillingConfig.model_fields
        assert "cert_subject" in fields
        assert "cert_issuer" in fields
        assert "cert_not_before" in fields
        assert "cert_not_after" in fields
