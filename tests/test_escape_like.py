"""Tests para escape_like() — FIX de LIKE injection (Sprint 0).

Verifica que los caracteres wildcard de SQL LIKE se escapan correctamente
para prevenir information disclosure vía búsquedas manipuladas.
"""
import pytest
from app.utils.sanitization import escape_like


class TestEscapeLike:
    """FIX: LIKE injection prevention."""

    def test_escapes_percent(self):
        assert escape_like("100%") == "100\\%"

    def test_escapes_underscore(self):
        assert escape_like("test_value") == "test\\_value"

    def test_escapes_backslash(self):
        assert escape_like("path\\file") == "path\\\\file"

    def test_escapes_all_wildcards_together(self):
        result = escape_like("%_\\")
        assert result == "\\%\\_\\\\"

    def test_preserves_normal_text(self):
        assert escape_like("producto normal") == "producto normal"

    def test_preserves_empty_string(self):
        assert escape_like("") == ""

    def test_preserves_unicode(self):
        assert escape_like("café") == "café"

    def test_multiple_wildcards(self):
        result = escape_like("%%__")
        assert result == "\\%\\%\\_\\_"

    def test_real_attack_pattern(self):
        """Simula ataque: buscar '%' para ver todo el inventario."""
        result = escape_like("%")
        assert result == "\\%"
        # Cuando se usa en f"%{result}%", genera "%\%%"
        # que solo matchea texto que contiene literal '%'

    def test_mixed_content_with_wildcards(self):
        result = escape_like("50% descuento_especial")
        assert result == "50\\% descuento\\_especial"
