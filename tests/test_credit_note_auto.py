"""Tests para la emisión automática de nota de crédito al procesar devolución.

Cubre:
  - _try_emit_return_credit_note: emite NC cuando hay comprobante autorizado
  - Skips: sin billing activo, sin comprobante, NC ya existente
  - Motivo de la NC incluye el label del ReturnReason
  - Errores no propagan excepción (silencioso)
"""
from __future__ import annotations

import asyncio
import os
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-credit-note-auto-32ch!")
os.environ.setdefault("TENANT_STRICT", "0")

from app.enums import FiscalStatus, ReceiptType, ReturnReason


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mock_company(*, has_billing: bool = True):
    c = MagicMock()
    c.id = 1
    c.has_electronic_billing = has_billing
    return c


def _mock_billing_config(*, is_active: bool = True):
    cfg = MagicMock()
    cfg.company_id = 1
    cfg.is_active = is_active
    return cfg


def _mock_fiscal_doc(*, doc_id: int = 100, sale_id: int = 1, receipt_type: str = ReceiptType.boleta):
    doc = MagicMock()
    doc.id = doc_id
    doc.sale_id = sale_id
    doc.company_id = 1
    doc.fiscal_status = FiscalStatus.authorized
    doc.receipt_type = receipt_type
    doc.buyer_doc_type = "DNI"
    doc.buyer_doc_number = "12345678"
    doc.buyer_name = "Juan Pérez"
    return doc


def _mock_nc_result(*, authorized: bool = True):
    result = MagicMock()
    result.fiscal_status = FiscalStatus.authorized if authorized else FiscalStatus.error
    result.full_number = "F001-00000001"
    return result


class _FakeSessionExec:
    """Simula session.exec().first() con resultados configurables por llamada."""

    def __init__(self, results_by_call: list):
        self._results = list(results_by_call)
        self._call_idx = 0

    def __call__(self, query):
        return self

    def first(self):
        if self._call_idx < len(self._results):
            result = self._results[self._call_idx]
            self._call_idx += 1
            return result
        return None


@contextmanager
def _fake_rx_session(exec_results: list):
    """Context manager que simula rx.session() con resultados predefinidos."""
    mock_session = MagicMock()
    mock_session.exec = _FakeSessionExec(exec_results)
    yield mock_session


def _run(coro):
    """Ejecuta un coroutine en el event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_state():
    """Crea un mock de HistorialState con el método real inyectado."""
    from app.states.historial_state import HistorialState
    state = MagicMock(spec=HistorialState)
    state._try_emit_return_credit_note = (
        HistorialState._try_emit_return_credit_note.__get__(state)
    )
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTryEmitReturnCreditNote:
    """Tests para HistorialState._try_emit_return_credit_note."""

    @pytest.fixture
    def state(self):
        return _make_state()

    def _patch_session(self, exec_results):
        return patch("reflex.session", return_value=_fake_rx_session(exec_results))

    def _patch_emit(self, **kwargs):
        return patch(
            "app.services.billing_service.emit_fiscal_document",
            new_callable=AsyncMock,
            **kwargs,
        )

    def test_emits_credit_note_when_authorized_doc_exists(self, state):
        """Cuando la venta tiene un comprobante autorizado, debe emitir NC."""
        company = _mock_company(has_billing=True)
        config = _mock_billing_config(is_active=True)
        original_doc = _mock_fiscal_doc(doc_id=100, sale_id=1)
        nc_result = _mock_nc_result(authorized=True)

        with self._patch_session([company, config, original_doc, None]):
            with self._patch_emit(return_value=nc_result) as mock_emit:
                _run(state._try_emit_return_credit_note(
                    sale_id=1, company_id=1, branch_id=1, reason="defective",
                ))
                mock_emit.assert_called_once()
                kw = mock_emit.call_args.kwargs
                assert kw["receipt_type_override"] == ReceiptType.nota_credito
                assert kw["original_fiscal_doc_id"] == 100
                assert "DEVOLUCIÓN" in kw["credit_note_reason"]
                assert kw["buyer_doc_type"] == "DNI"
                assert kw["buyer_doc_number"] == "12345678"

    def test_skips_when_no_electronic_billing(self, state):
        """No emite NC si la empresa no tiene facturación electrónica."""
        company = _mock_company(has_billing=False)

        with self._patch_session([company]):
            with self._patch_emit() as mock_emit:
                _run(state._try_emit_return_credit_note(
                    sale_id=1, company_id=1, branch_id=1, reason="other",
                ))
                mock_emit.assert_not_called()

    def test_skips_when_billing_config_inactive(self, state):
        """No emite NC si CompanyBillingConfig.is_active == False."""
        company = _mock_company(has_billing=True)

        with self._patch_session([company, None]):
            with self._patch_emit() as mock_emit:
                _run(state._try_emit_return_credit_note(
                    sale_id=1, company_id=1, branch_id=1, reason="other",
                ))
                mock_emit.assert_not_called()

    def test_skips_when_no_authorized_doc(self, state):
        """No emite NC si la venta no tiene comprobante fiscal autorizado."""
        company = _mock_company(has_billing=True)
        config = _mock_billing_config(is_active=True)

        with self._patch_session([company, config, None]):
            with self._patch_emit() as mock_emit:
                _run(state._try_emit_return_credit_note(
                    sale_id=1, company_id=1, branch_id=1, reason="other",
                ))
                mock_emit.assert_not_called()

    def test_skips_when_nc_already_exists(self, state):
        """No emite NC si ya existe una para esta venta."""
        company = _mock_company(has_billing=True)
        config = _mock_billing_config(is_active=True)
        original_doc = _mock_fiscal_doc(doc_id=100, sale_id=1)
        existing_nc = _mock_fiscal_doc(
            doc_id=200, sale_id=1, receipt_type=ReceiptType.nota_credito,
        )

        with self._patch_session([company, config, original_doc, existing_nc]):
            with self._patch_emit() as mock_emit:
                _run(state._try_emit_return_credit_note(
                    sale_id=1, company_id=1, branch_id=1, reason="defective",
                ))
                mock_emit.assert_not_called()

    def test_includes_reason_label_in_credit_note(self, state):
        """El motivo de la NC incluye el display_label del ReturnReason."""
        company = _mock_company(has_billing=True)
        config = _mock_billing_config(is_active=True)
        original_doc = _mock_fiscal_doc(doc_id=100, sale_id=1)
        nc_result = _mock_nc_result(authorized=True)

        with self._patch_session([company, config, original_doc, None]):
            with self._patch_emit(return_value=nc_result) as mock_emit:
                _run(state._try_emit_return_credit_note(
                    sale_id=1, company_id=1, branch_id=1, reason="defective",
                ))
                reason_arg = mock_emit.call_args.kwargs["credit_note_reason"]
                assert "Producto defectuoso" in reason_arg

    def test_error_does_not_propagate(self, state):
        """Si emit_fiscal_document lanza excepción, no se propaga."""
        company = _mock_company(has_billing=True)
        config = _mock_billing_config(is_active=True)
        original_doc = _mock_fiscal_doc(doc_id=100, sale_id=1)

        with self._patch_session([company, config, original_doc, None]):
            with self._patch_emit(side_effect=RuntimeError("Network timeout")):
                # Should not raise
                _run(state._try_emit_return_credit_note(
                    sale_id=1, company_id=1, branch_id=1, reason="other",
                ))

    def test_factura_receipt_type_also_triggers(self, state):
        """Comprobante tipo factura también gatilla NC automática."""
        company = _mock_company(has_billing=True)
        config = _mock_billing_config(is_active=True)
        original_doc = _mock_fiscal_doc(
            doc_id=200, sale_id=5, receipt_type=ReceiptType.factura,
        )
        nc_result = _mock_nc_result(authorized=True)

        with self._patch_session([company, config, original_doc, None]):
            with self._patch_emit(return_value=nc_result) as mock_emit:
                _run(state._try_emit_return_credit_note(
                    sale_id=5, company_id=1, branch_id=1, reason="wrong_item",
                ))
                mock_emit.assert_called_once()
                assert mock_emit.call_args.kwargs["sale_id"] == 5


class TestReturnReasonLabel:
    """Verifica que el mapping de ReturnReason.display_label funciona."""

    @pytest.mark.parametrize("reason,expected_label", [
        ("defective", "Producto defectuoso"),
        ("wrong_item", "Producto equivocado"),
        ("change_mind", "Cambio de opinión"),
        ("not_as_described", "No es lo esperado"),
        ("other", "Otro motivo"),
    ])
    def test_display_labels(self, reason, expected_label):
        assert ReturnReason(reason).display_label == expected_label
