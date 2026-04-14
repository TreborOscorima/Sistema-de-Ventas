"""Tests para refresh token JWT.

Cubre:
  - Creación de refresh token con claim ``typ`` = ``"refresh"``
  - Decodificación: acepta refresh, rechaza access tokens
  - Rotación: ``refresh_access_token`` emite nuevo par (access, refresh)
  - Expiración: refresh token expirado retorna None
  - Token version: se preserva en el par rotado
  - Company ID: se preserva en el par rotado
"""
from __future__ import annotations

import datetime
import os
from unittest.mock import patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-refresh-token-32chars!")
os.environ.setdefault("TENANT_STRICT", "0")

from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    decode_token,
    refresh_access_token,
)


# ─────────────────────────────────────────────────────────────────────────────
# create_refresh_token
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateRefreshToken:
    def test_creates_valid_jwt(self):
        token = create_refresh_token("42")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_includes_typ_refresh(self):
        token = create_refresh_token("42")
        payload = decode_refresh_token(token)
        assert payload is not None
        assert payload["typ"] == "refresh"

    def test_includes_subject(self):
        token = create_refresh_token("99")
        payload = decode_refresh_token(token)
        assert payload["sub"] == "99"

    def test_includes_token_version(self):
        token = create_refresh_token("1", token_version=5)
        payload = decode_refresh_token(token)
        assert payload["ver"] == 5

    def test_includes_company_id(self):
        token = create_refresh_token("1", company_id=10)
        payload = decode_refresh_token(token)
        assert payload["cid"] == 10

    def test_omits_optional_claims(self):
        token = create_refresh_token("1")
        payload = decode_refresh_token(token)
        assert "ver" not in payload
        assert "cid" not in payload


# ─────────────────────────────────────────────────────────────────────────────
# decode_refresh_token
# ─────────────────────────────────────────────────────────────────────────────

class TestDecodeRefreshToken:
    def test_decodes_valid_refresh_token(self):
        token = create_refresh_token("42")
        payload = decode_refresh_token(token)
        assert payload is not None
        assert payload["sub"] == "42"

    def test_rejects_access_token(self):
        """Un access token normal no tiene typ=refresh, debe rechazarse."""
        token = create_access_token("42")
        payload = decode_refresh_token(token)
        assert payload is None

    def test_rejects_empty_string(self):
        assert decode_refresh_token("") is None

    def test_rejects_garbage(self):
        assert decode_refresh_token("not.a.jwt") is None

    def test_rejects_expired_token(self):
        import jwt as pyjwt
        from app.utils.auth import SECRET_KEY, ALGORITHM
        # Manually craft a refresh token with exp in the past
        past = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(hours=1)
        payload = {"sub": "42", "exp": past, "typ": "refresh"}
        token = pyjwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        assert decode_refresh_token(token) is None


# ─────────────────────────────────────────────────────────────────────────────
# refresh_access_token (token rotation)
# ─────────────────────────────────────────────────────────────────────────────

class TestRefreshAccessToken:
    def test_returns_new_pair(self):
        refresh = create_refresh_token("42", token_version=3, company_id=7)
        result = refresh_access_token(refresh)
        assert result is not None
        new_access, new_refresh = result
        # New access token is valid
        access_payload = decode_token(new_access)
        assert access_payload is not None
        assert access_payload["sub"] == "42"
        assert access_payload["ver"] == 3
        assert access_payload["cid"] == 7
        # New refresh token is valid
        refresh_payload = decode_refresh_token(new_refresh)
        assert refresh_payload is not None
        assert refresh_payload["sub"] == "42"
        assert refresh_payload["ver"] == 3
        assert refresh_payload["cid"] == 7

    def test_returns_none_for_access_token(self):
        access = create_access_token("42")
        assert refresh_access_token(access) is None

    def test_returns_none_for_invalid_token(self):
        assert refresh_access_token("garbage") is None

    def test_returns_none_for_empty(self):
        assert refresh_access_token("") is None

    def test_preserves_subject_without_optionals(self):
        refresh = create_refresh_token("55")
        result = refresh_access_token(refresh)
        assert result is not None
        new_access, _ = result
        payload = decode_token(new_access)
        assert payload["sub"] == "55"
        assert "ver" not in payload
        assert "cid" not in payload

    def test_rotated_tokens_are_valid(self):
        refresh = create_refresh_token("42")
        result = refresh_access_token(refresh)
        assert result is not None
        new_access, new_refresh = result
        # Both new tokens must be valid
        assert decode_token(new_access) is not None
        assert decode_refresh_token(new_refresh) is not None


# ─────────────────────────────────────────────────────────────────────────────
# Integration: access token cannot be decoded as refresh and vice versa
# ─────────────────────────────────────────────────────────────────────────────

class TestTokenTypeIsolation:
    def test_access_not_decodable_as_refresh(self):
        access = create_access_token("42")
        assert decode_refresh_token(access) is None

    def test_refresh_decodable_as_generic_jwt(self):
        """decode_token (generic) can decode a refresh token since it's a valid JWT."""
        refresh = create_refresh_token("42")
        payload = decode_token(refresh)
        assert payload is not None
        assert payload["typ"] == "refresh"
