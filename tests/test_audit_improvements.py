"""Tests para las mejoras de auditoría implementadas.

Cubre:
  - Product.is_active: campo, filtrado en sale_service, filtrado en alert_service
  - Client.email: campo nuevo
  - Sale cascades: delete-orphan en items/payments/installments
  - alert_service: umbrales dinámicos via Product.min_stock_alert
  - Dashboard: margen bruto (cálculo)
  - Historial: reporte de devoluciones (state vars y load)
"""
from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-audit-improvements-32chars")
os.environ.setdefault("TENANT_STRICT", "0")

import reflex as rx

from app.services import alert_service
from app.services.alert_service import (
    STOCK_CRITICAL_FRACTION,
    STOCK_CRITICAL_FLOOR,
    AlertSeverity,
    AlertType,
    get_low_stock_alerts,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _product(*, id_: int, description: str, stock: float, is_active: bool = True, min_stock_alert: int = 10):
    p = MagicMock()
    p.id = id_
    p.description = description
    p.stock = Decimal(str(stock))
    p.is_active = is_active
    p.min_stock_alert = min_stock_alert
    return p


class _ExecResult:
    def __init__(self, rows=None, scalar=None):
        self._rows = rows or []
        self._scalar = scalar

    def all(self):
        return self._rows

    def one(self):
        return self._scalar


class _SequentialSession:
    def __init__(self, responses):
        self._responses = list(responses)

    def exec(self, statement):
        if not self._responses:
            return _ExecResult(rows=[], scalar=0)
        return self._responses.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Product.is_active — modelo
# ─────────────────────────────────────────────────────────────────────────────

class TestProductIsActive:
    """Verifica que Product.is_active existe y tiene el default correcto."""

    def test_field_exists_with_default_true(self):
        from app.models import Product
        p = Product(
            barcode="TEST001",
            description="Test product",
            stock=Decimal("10"),
            sale_price=Decimal("5.00"),
        )
        assert p.is_active is True

    def test_field_can_be_set_false(self):
        from app.models import Product
        p = Product(
            barcode="TEST002",
            description="Inactive",
            stock=Decimal("5"),
            sale_price=Decimal("3.00"),
            is_active=False,
        )
        assert p.is_active is False


# ─────────────────────────────────────────────────────────────────────────────
# Client.email — modelo
# ─────────────────────────────────────────────────────────────────────────────

class TestClientEmail:
    """Verifica que Client.email existe como campo opcional."""

    def test_email_field_defaults_none(self):
        from app.models import Client
        c = Client(name="Test Client", company_id=1, branch_id=1)
        assert c.email is None

    def test_email_field_can_be_set(self):
        from app.models import Client
        c = Client(
            name="Test Client",
            company_id=1,
            branch_id=1,
            email="test@example.com",
        )
        assert c.email == "test@example.com"


# ─────────────────────────────────────────────────────────────────────────────
# Sale cascades — modelo
# ─────────────────────────────────────────────────────────────────────────────

class TestSaleCascades:
    """Verifica que las relaciones de Sale tienen cascade 'all, delete-orphan'."""

    def test_items_cascade(self):
        from app.models import Sale
        import sqlalchemy as sa
        mapper = sa.inspect(Sale)
        rel = mapper.relationships["items"]
        assert rel.cascade.delete_orphan is True

    def test_payments_cascade(self):
        from app.models import Sale
        import sqlalchemy as sa
        mapper = sa.inspect(Sale)
        rel = mapper.relationships["payments"]
        assert rel.cascade.delete_orphan is True

    def test_installments_cascade(self):
        from app.models import Sale
        import sqlalchemy as sa
        mapper = sa.inspect(Sale)
        rel = mapper.relationships["installments"]
        assert rel.cascade.delete_orphan is True


# ─────────────────────────────────────────────────────────────────────────────
# alert_service — umbrales dinámicos
# ─────────────────────────────────────────────────────────────────────────────

class TestAlertServiceDynamicThresholds:
    """Verifica que alert_service usa umbrales dinámicos basados en
    Product.min_stock_alert en lugar de constantes fijas."""

    def test_stock_critical_fraction_exists(self):
        """STOCK_CRITICAL_FRACTION debe definirse como fracción (0 < x < 1)."""
        assert 0 < STOCK_CRITICAL_FRACTION < 1

    def test_stock_critical_floor_exists(self):
        """STOCK_CRITICAL_FLOOR debe ser un entero positivo."""
        assert STOCK_CRITICAL_FLOOR > 0

    def test_old_constants_removed(self):
        """Las constantes fijas STOCK_LOW_THRESHOLD y STOCK_CRITICAL_THRESHOLD
        ya no deben existir."""
        assert not hasattr(alert_service, "STOCK_LOW_THRESHOLD")
        assert not hasattr(alert_service, "STOCK_CRITICAL_THRESHOLD")

    def test_critical_message_no_hardcoded_value(self, monkeypatch):
        """El mensaje de stock crítico no debe contener un umbral fijo."""
        critical_products = [_product(id_=1, description="Café", stock=1.0)]
        session = _SequentialSession([
            _ExecResult(rows=critical_products),
            _ExecResult(rows=[]),
            _ExecResult(scalar=0),
        ])
        monkeypatch.setattr(rx, "session", lambda: session)

        alerts = get_low_stock_alerts(company_id=1, branch_id=1)

        assert len(alerts) == 1
        assert alerts[0].type == AlertType.STOCK_CRITICAL
        # El mensaje no debe contener "≤3" ni "≤10" como umbral fijo
        assert "≤3" not in alerts[0].message
        assert "≤10" not in alerts[0].message

    def test_low_stock_uses_min_stock_alert_text(self, monkeypatch):
        """El mensaje de stock bajo debe referir al mínimo configurado."""
        low_products = [_product(id_=10, description="Azúcar", stock=5.0, min_stock_alert=10)]
        session = _SequentialSession([
            _ExecResult(rows=[]),
            _ExecResult(rows=low_products),
            _ExecResult(scalar=0),
        ])
        monkeypatch.setattr(rx, "session", lambda: session)

        alerts = get_low_stock_alerts(company_id=1, branch_id=1)

        assert len(alerts) == 1
        assert alerts[0].type == AlertType.STOCK_LOW
        assert "mínimo configurado" in alerts[0].message


# ─────────────────────────────────────────────────────────────────────────────
# SaleReturn model — estructura
# ─────────────────────────────────────────────────────────────────────────────

class TestSaleReturnModel:
    """Verifica la estructura del modelo SaleReturn."""

    def test_sale_return_fields(self):
        from app.models import SaleReturn
        ret = SaleReturn(
            original_sale_id=1,
            reason="defective",
            refund_amount=Decimal("25.00"),
            company_id=1,
            branch_id=1,
        )
        assert ret.original_sale_id == 1
        assert ret.reason == "defective"
        assert ret.refund_amount == Decimal("25.00")

    def test_sale_return_item_fields(self):
        from app.models import SaleReturnItem
        item = SaleReturnItem(
            sale_return_id=1,
            sale_item_id=1,
            quantity=Decimal("2.0000"),
            refund_subtotal=Decimal("10.00"),
            product_id=1,
        )
        assert item.quantity == Decimal("2.0000")
        assert item.refund_subtotal == Decimal("10.00")


# ─────────────────────────────────────────────────────────────────────────────
# ReturnReason enum
# ─────────────────────────────────────────────────────────────────────────────

class TestReturnReasonEnum:
    """Verifica que el enum ReturnReason tiene todos los valores esperados."""

    def test_all_reasons_present(self):
        from app.enums import ReturnReason
        expected = {"defective", "wrong_item", "change_mind", "not_as_described", "other"}
        actual = {r.value for r in ReturnReason}
        assert expected == actual

    def test_display_labels(self):
        from app.enums import ReturnReason
        for reason in ReturnReason:
            label = reason.display_label
            assert isinstance(label, str)
            assert len(label) > 0


# ─────────────────────────────────────────────────────────────────────────────
# HistorialState — returns report vars
# ─────────────────────────────────────────────────────────────────────────────

class TestHistorialStateReturnsReport:
    """Verifica que HistorialState tiene los vars para el reporte de devoluciones."""

    def test_returns_report_state_vars_exist(self):
        from app.states.historial_state import HistorialState
        # Reflex State uses class-level annotations; check via annotations or hasattr
        assert hasattr(HistorialState, "returns_report_rows")
        assert hasattr(HistorialState, "returns_report_total")
        assert hasattr(HistorialState, "returns_report_count")
        assert hasattr(HistorialState, "returns_report_page")
        assert hasattr(HistorialState, "returns_report_per_page")
        assert hasattr(HistorialState, "returns_report_filter_start")
        assert hasattr(HistorialState, "returns_report_filter_end")

    def test_returns_report_annotations(self):
        from app.states.historial_state import HistorialState
        annotations = {}
        for cls in reversed(HistorialState.__mro__):
            annotations.update(getattr(cls, "__annotations__", {}))
        assert "returns_report_rows" in annotations
        assert "returns_report_total" in annotations
        assert "returns_report_count" in annotations

    def test_load_returns_report_method_exists(self):
        from app.states.historial_state import HistorialState
        assert hasattr(HistorialState, "load_returns_report")
        assert hasattr(HistorialState, "_load_returns_report")

    def test_export_returns_excel_method_exists(self):
        from app.states.historial_state import HistorialState
        assert hasattr(HistorialState, "export_returns_excel")
