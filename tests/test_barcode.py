"""Tests para app/utils/barcode.py — clean_barcode y validate_barcode."""
import pytest
from app.utils.barcode import clean_barcode, validate_barcode


class TestCleanBarcode:
    def test_removes_spaces(self):
        assert clean_barcode("123 456") == "123456"

    def test_removes_dashes(self):
        assert clean_barcode("123-456-789") == "123456789"

    def test_removes_dots(self):
        assert clean_barcode("123.456") == "123456"

    def test_removes_commas(self):
        assert clean_barcode("123,456") == "123456"

    def test_strips_whitespace(self):
        assert clean_barcode("  ABC123  ") == "ABC123"

    def test_handles_empty(self):
        assert clean_barcode("") == ""

    def test_handles_none(self):
        assert clean_barcode(None) == ""

    def test_preserves_alphanumeric(self):
        assert clean_barcode("ABC123XYZ") == "ABC123XYZ"

    def test_combined_special_chars(self):
        assert clean_barcode(" 12-34.56,78 ") == "12345678"


class TestValidateBarcode:
    def test_valid_barcode(self):
        assert validate_barcode("1234567890123") is True

    def test_too_short(self):
        assert validate_barcode("AB") is False

    def test_too_long(self):
        assert validate_barcode("A" * 51) is False

    def test_empty_string(self):
        assert validate_barcode("") is False

    def test_none(self):
        assert validate_barcode(None) is False

    def test_custom_min_length(self):
        assert validate_barcode("AB", min_length=2) is True
        assert validate_barcode("A", min_length=2) is False

    def test_custom_max_length(self):
        assert validate_barcode("ABCDE", max_length=5) is True
        assert validate_barcode("ABCDEF", max_length=5) is False

    def test_with_special_chars_cleaned(self):
        # "12-34" becomes "1234" after cleaning, length 4 >= 3
        assert validate_barcode("12-34") is True
