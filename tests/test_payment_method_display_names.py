"""Tests: métodos de pago se muestran por su nombre real (no genérico).

Cubre la resolución central usada en Reportes ("Ingresos por Origen"): un pago
con billetera/custom (Mercado Pago, Cuenta DNI, MODO, o cualquier método de otro
país) se resuelve por su payment_method_id -> nombre real; los estándar
(efectivo/débito/crédito/transferencia) mantienen su etiqueta traducida.
"""
from __future__ import annotations

import os

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-pm-display")
os.environ.setdefault("TENANT_STRICT", "0")


class _MT:
    def __init__(self, value: str):
        self.value = value


class _Payment:
    def __init__(self, method_type: str, pm_id):
        self.method_type = _MT(method_type)
        self.payment_method_id = pm_id


class TestResolvePaymentDisplay:
    def test_wallet_uses_real_name(self):
        from app.services.report_service import _resolve_payment_display
        pm_by_id = {5: "Mercado Pago", 6: "Cuenta DNI", 7: "MODO"}
        assert _resolve_payment_display(_Payment("wallet", 5), pm_by_id) == "Mercado Pago"
        assert _resolve_payment_display(_Payment("wallet", 6), pm_by_id) == "Cuenta DNI"
        assert _resolve_payment_display(_Payment("wallet", 7), pm_by_id) == "MODO"

    def test_other_uses_real_name(self):
        from app.services.report_service import _resolve_payment_display
        assert _resolve_payment_display(_Payment("other", 9), {9: "Rapipago"}) == "Rapipago"

    def test_cash_keeps_standard_label(self):
        from app.services.report_service import _resolve_payment_display
        # Un método estándar NO toma el nombre por id: usa su etiqueta traducida.
        result = _resolve_payment_display(_Payment("cash", 1), {1: "NombreRaro"})
        assert result != "NombreRaro"

    def test_wallet_without_id_falls_back(self):
        from app.services.report_service import _resolve_payment_display
        # Sin id resoluble, no revienta: cae a la etiqueta del tipo.
        result = _resolve_payment_display(_Payment("wallet", None), {})
        assert isinstance(result, str) and result
