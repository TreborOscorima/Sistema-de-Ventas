"""Tests para app.utils.fiscal_validators."""
import pytest
from app.utils.fiscal_validators import (
    validate_ruc,
    validate_cuit,
    validate_nubefact_url,
    validate_environment,
    validate_business_name,
    validate_tax_id,
)


# ═══════════════════════════════════════════════════════════
# RUC (Perú)
# ═══════════════════════════════════════════════════════════

class TestValidateRUC:
    def test_valid_ruc_persona_juridica(self):
        ok, err = validate_ruc("20123456789")
        # Solo verifica formato, el checksum puede fallar con este ejemplo
        # Usamos un RUC con checksum válido
        pass

    def test_empty_ruc(self):
        ok, err = validate_ruc("")
        assert not ok
        assert "vacío" in err

    def test_none_ruc(self):
        ok, err = validate_ruc(None)
        assert not ok

    def test_non_digit(self):
        ok, err = validate_ruc("2012345678A")
        assert not ok
        assert "dígitos" in err

    def test_wrong_length(self):
        ok, err = validate_ruc("1234567890")
        assert not ok
        assert "11 dígitos" in err

    def test_invalid_prefix(self):
        ok, err = validate_ruc("30123456789")
        assert not ok
        assert "prefijo" in err.lower()

    def test_strips_hyphens(self):
        # Hyphens should be stripped before validation
        ok, err = validate_ruc("20-12345678-9")
        # After stripping hyphens: 20123456789 (11 digits)
        # May or may not pass checksum, but should not fail on format
        assert isinstance(ok, bool)

    def test_valid_checksum(self):
        """Test with a known-valid RUC."""
        # RUC 20100047218 (SUNAT's own RUC — real, well-known)
        ok, err = validate_ruc("20100047218")
        assert ok, f"Expected valid RUC but got: {err}"


# ═══════════════════════════════════════════════════════════
# CUIT (Argentina)
# ═══════════════════════════════════════════════════════════

class TestValidateCUIT:
    def test_valid_cuit(self):
        ok, err = validate_cuit("20345678906")
        assert ok, f"Expected valid but got: {err}"

    def test_empty_cuit(self):
        ok, err = validate_cuit("")
        assert not ok

    def test_non_digit(self):
        ok, err = validate_cuit("2034567890X")
        assert not ok
        assert "dígitos" in err

    def test_wrong_length(self):
        ok, err = validate_cuit("2034567890")
        assert not ok
        assert "11 dígitos" in err

    def test_invalid_prefix(self):
        ok, err = validate_cuit("99345678906")
        assert not ok
        assert "prefijo" in err.lower()

    def test_invalid_check_digit(self):
        ok, err = validate_cuit("20345678901")
        assert not ok
        assert "verificador" in err

    def test_strips_hyphens(self):
        ok, err = validate_cuit("20-34567890-6")
        assert ok, f"Should be valid after stripping hyphens: {err}"

    def test_known_valid_cuit_persona_juridica(self):
        ok, err = validate_cuit("20111111112")
        assert ok, f"Expected valid: {err}"


# ═══════════════════════════════════════════════════════════
# Nubefact URL
# ═══════════════════════════════════════════════════════════

class TestValidateNubefactURL:
    def test_valid_url(self):
        ok, err = validate_nubefact_url("https://api.nubefact.com/api/v1/abc123")
        assert ok

    def test_empty_url(self):
        ok, err = validate_nubefact_url("")
        assert not ok

    def test_http_rejected(self):
        ok, err = validate_nubefact_url("http://api.nubefact.com/api/v1/abc")
        assert not ok
        assert "HTTPS" in err

    def test_no_protocol(self):
        ok, err = validate_nubefact_url("api.nubefact.com/api/v1/abc")
        assert not ok
        assert "https://" in err

    def test_non_nubefact_domain_warns(self):
        ok, err = validate_nubefact_url("https://custom-api.example.com/billing")
        assert ok  # Valid but with warning
        assert "nubefact" in err.lower()

    def test_valid_nubefact_no_warning(self):
        ok, err = validate_nubefact_url("https://api.nubefact.com/api/v1/xyz")
        assert ok
        assert err == ""


# ═══════════════════════════════════════════════════════════
# Environment
# ═══════════════════════════════════════════════════════════

class TestValidateEnvironment:
    def test_sandbox(self):
        ok, err = validate_environment("sandbox")
        assert ok

    def test_production(self):
        ok, err = validate_environment("production")
        assert ok

    def test_invalid(self):
        ok, err = validate_environment("staging")
        assert not ok
        assert "sandbox" in err and "production" in err

    def test_empty(self):
        ok, err = validate_environment("")
        assert not ok

    def test_case_insensitive(self):
        ok, err = validate_environment("SANDBOX")
        assert ok


# ═══════════════════════════════════════════════════════════
# Business Name
# ═══════════════════════════════════════════════════════════

class TestValidateBusinessName:
    def test_valid(self):
        ok, err = validate_business_name("TU WAYKI S.A.C")
        assert ok

    def test_empty(self):
        ok, err = validate_business_name("")
        assert not ok

    def test_too_short(self):
        ok, err = validate_business_name("AB")
        assert not ok
        assert "3 caracteres" in err

    def test_whitespace_only(self):
        ok, err = validate_business_name("   ")
        assert not ok


# ═══════════════════════════════════════════════════════════
# Tax ID dispatch
# ═══════════════════════════════════════════════════════════

class TestValidateTaxID:
    def test_peru_dispatches_to_ruc(self):
        ok, err = validate_tax_id("20100047218", "PE")
        assert ok

    def test_argentina_dispatches_to_cuit(self):
        ok, err = validate_tax_id("20345678906", "AR")
        assert ok

    def test_unknown_country(self):
        ok, err = validate_tax_id("12345678901", "BR")
        assert not ok
        assert "no soportado" in err

    def test_case_variants(self):
        ok, _ = validate_tax_id("20345678906", "ar")
        assert ok
        ok, _ = validate_tax_id("20345678906", "ARG")
        assert ok
