"""Formato de cantidad en superficies de salida (reportes, recibo, devoluciones).

Fija que las cantidades fraccionadas (venta al peso/volumen: kg, L, ml) se
muestran con decimales y NO se truncan a entero, y que las cantidades enteras
salen limpias (sin '.0' colgante). Complementa el cambio de resolución 0.001
(ver test_stock_utils.py::TestQuantityDisplayResolution).
"""
from __future__ import annotations

import os
from decimal import Decimal

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-quantity-display-32chars-long")
os.environ.setdefault("TENANT_STRICT", "0")

from app.services.report_service import (
    _quantity_format,
    NUMBER_FORMAT,
    NUMBER_FORMAT_INT,
)
from app.utils.formatting import fmt_input_num


class TestQuantityFormatReports:
    """`_quantity_format`: elige formato decimal-aware para celdas Excel."""

    def test_fraccional_usa_formato_decimal(self):
        # Suma de ventas al peso (0,253 + 0,5 = 0,753 kg) → muestra decimales.
        assert _quantity_format(Decimal("0.753")) == NUMBER_FORMAT
        assert _quantity_format(Decimal("2.5")) == NUMBER_FORMAT

    def test_entero_usa_formato_limpio(self):
        # Unidades enteras → sin separador decimal colgante.
        assert _quantity_format(Decimal("12")) == NUMBER_FORMAT_INT
        assert _quantity_format(Decimal("0")) == NUMBER_FORMAT_INT

    def test_acepta_float_y_str(self):
        assert _quantity_format(0.253) == NUMBER_FORMAT
        assert _quantity_format("3") == NUMBER_FORMAT_INT

    def test_number_format_muestra_hasta_4_decimales(self):
        # El formato decimal solo revela dígitos reales, hasta 4 (escala BD).
        assert NUMBER_FORMAT == "#,##0.####"
        assert NUMBER_FORMAT_INT == "#,##0"


class TestFmtInputNumQuantities:
    """`fmt_input_num`: usado en el comprobante impreso y en devoluciones."""

    def test_decimal_se_preserva(self):
        assert fmt_input_num(0.253) == "0.253"
        assert fmt_input_num(0.095) == "0.095"

    def test_entero_sin_punto_colgante(self):
        # Antes el recibo mostraba "3.0 kg"; ahora "3 kg".
        assert fmt_input_num(3.0) == "3"
        assert fmt_input_num(2) == "2"

    def test_trailing_zeros_se_recortan(self):
        assert fmt_input_num(0.250) == "0.25"

    def test_devolucion_fraccionada_no_es_cero(self):
        # Etiqueta de devolución: 0,253 kg ya no se rotula "x0".
        assert fmt_input_num(Decimal("0.253")) == "0.253"
