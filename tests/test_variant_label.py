"""Tests unitarios de ProductVariant.label() — fuente única de verdad del
label visible de variantes (talla/color).

Cubre separadores, fallbacks y, sobre todo, la REGRESIÓN que motivó unificar
las ~9 copias dispersas de `_variant_label`: el SKU/código NUNCA debe anexarse
al label (antes inventario mostraba "42 Negro (uuid)").
"""
from __future__ import annotations

import os
from decimal import Decimal

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-variant-label-32chars-long")
os.environ.setdefault("TENANT_STRICT", "0")

from app.models import ProductVariant


def _variant(*, size=None, color=None, sku="SKU-1") -> ProductVariant:
    return ProductVariant(
        id=1,
        product_id=1,
        company_id=1,
        branch_id=1,
        sku=sku,
        size=size,
        color=color,
        stock=Decimal("0.0000"),
    )


class TestVariantLabelHappyPath:
    def test_talla_y_color(self):
        assert _variant(size="42", color="Negro").label() == "42 Negro"

    def test_solo_talla(self):
        assert _variant(size="42", color=None).label() == "42"

    def test_solo_color(self):
        assert _variant(size=None, color="Negro").label() == "Negro"

    def test_separador_slash(self):
        assert _variant(size="42", color="Negro").label(sep=" / ") == "42 / Negro"


class TestVariantLabelNoAnexaSku:
    """La garantía central: el SKU/código jamás se mete dentro del label."""

    def test_sku_nunca_se_anexa_con_talla_y_color(self):
        v = _variant(size="42", color="Negro", sku="TESTVAR777")
        assert v.label() == "42 Negro"
        assert "TESTVAR777" not in v.label()

    def test_sku_uuid_no_contamina_el_label(self):
        # Reproduce el escenario del bug: variante sin código → sku = uuid.
        v = _variant(size="42", color="Negro", sku="a1b2c3d4-e5f6-7890-abcd-ef0123456789")
        assert v.label() == "42 Negro"
        assert "(" not in v.label()


class TestVariantLabelFallbacks:
    def test_sin_talla_ni_color_cae_al_sku_por_defecto(self):
        assert _variant(size=None, color=None, sku="COD-9").label() == "COD-9"

    def test_sin_talla_ni_color_sin_fallback_usa_default(self):
        v = _variant(size=None, color=None, sku="COD-9")
        assert v.label(sku_fallback=False, default="") == ""

    def test_default_variante_cuando_no_hay_nada(self):
        assert _variant(size=None, color=None, sku="").label() == "Variante"

    def test_default_personalizado(self):
        assert _variant(size=None, color=None, sku="").label(default="-") == "-"


class TestVariantLabelEdgeCases:
    def test_talla_solo_espacios_se_ignora(self):
        assert _variant(size="   ", color="Negro").label() == "Negro"

    def test_valores_se_recortan(self):
        assert _variant(size="  42 ", color=" Negro ").label() == "42 Negro"
