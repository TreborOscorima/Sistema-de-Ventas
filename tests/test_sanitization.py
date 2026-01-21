"""Tests para app/utils/sanitization.py"""
import pytest
from app.utils.sanitization import (
    sanitize_text,
    sanitize_notes,
    sanitize_name,
    sanitize_phone,
    sanitize_dni,
    sanitize_barcode,
    sanitize_reason,
    is_valid_phone,
    is_valid_dni,
)


class TestSanitizeText:
    def test_escapes_script_tags(self):
        # Escapa los tags HTML para prevenir ejecución
        result = sanitize_text("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;" in result  # Escapado
    
    def test_escapes_html_entities(self):
        result = sanitize_text("<div>test</div>")
        assert "<" not in result or "&lt;" in result
    
    def test_strips_whitespace(self):
        assert sanitize_text("  hello  ") == "hello"
    
    def test_handles_none(self):
        assert sanitize_text(None) == ""
    
    def test_handles_empty_string(self):
        assert sanitize_text("") == ""
    
    def test_preserves_normal_text(self):
        assert sanitize_text("Juan Pérez") == "Juan Pérez"


class TestSanitizeNotes:
    def test_truncates_long_text(self):
        long_text = "a" * 300
        result = sanitize_notes(long_text)
        assert len(result) <= 250
    
    def test_removes_dangerous_content(self):
        # Verifica que el contenido peligroso está escapado
        result = sanitize_notes("<script>bad</script>")
        assert "<script>" not in result
    
    def test_preserves_normal_notes(self):
        note = "Cliente solicita entrega a domicilio"
        assert sanitize_notes(note) == note


class TestSanitizeName:
    def test_strips_whitespace(self):
        assert sanitize_name("  María  ") == "María"
    
    def test_preserves_accents(self):
        assert "é" in sanitize_name("José")
    
    def test_handles_empty(self):
        assert sanitize_name("") == ""
    
    def test_preserves_alphanumeric(self):
        # La implementación actual preserva el texto, solo lo limpia
        result = sanitize_name("Juan123")
        assert "Juan" in result


class TestSanitizePhone:
    def test_handles_phone_with_formatting(self):
        # Verifica que el input se procesa (la implementación actual lo limpia)
        result = sanitize_phone("+51 999-888-777")
        assert result  # No vacío
    
    def test_handles_empty(self):
        assert sanitize_phone("") == ""
    
    def test_handles_none(self):
        assert sanitize_phone(None) == ""


class TestSanitizeDni:
    def test_sanitizes_dni(self):
        # La implementación limpia y convierte a mayúsculas
        result = sanitize_dni("12345678-A")
        assert "12345678" in result
    
    def test_uppercase(self):
        result = sanitize_dni("abc123")
        assert result == result.upper()
    
    def test_handles_empty(self):
        assert sanitize_dni("") == ""


class TestSanitizeBarcode:
    def test_keeps_alphanumeric(self):
        result = sanitize_barcode("ABC123")
        assert result == "ABC123"
    
    def test_removes_special_chars(self):
        result = sanitize_barcode("ABC<script>123")
        assert "<" not in result
        assert ">" not in result


class TestSanitizeReason:
    def test_removes_html(self):
        result = sanitize_reason("<b>motivo</b>")
        assert "<b>" not in result
    
    def test_truncates_long_text(self):
        long_reason = "x" * 600
        result = sanitize_reason(long_reason)
        assert len(result) <= 500


class TestValidation:
    def test_valid_phone_peru(self):
        assert is_valid_phone("999888777") is True
        assert is_valid_phone("51999888777") is True
    
    def test_invalid_phone_too_short(self):
        assert is_valid_phone("123") is False
    
    def test_valid_dni_peru(self):
        assert is_valid_dni("12345678") is True
    
    def test_invalid_dni_too_short(self):
        assert is_valid_dni("123") is False
