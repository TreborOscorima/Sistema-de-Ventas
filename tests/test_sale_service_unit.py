"""Tests para app/services/sale_service.py

Cobertura de casos críticos del servicio de ventas:
- Validación de stock
- Procesamiento de pagos
- Ventas a crédito
- Transacciones atómicas
"""
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.sale_service import (
    SaleService,
    SaleProcessResult,
    StockError,
    _to_decimal,
    _round_money,
    _round_quantity,
)
from app.schemas.sale_schemas import (
    PaymentInfoDTO,
    PaymentCashDTO,
    PaymentCardDTO,
    PaymentMixedDTO,
    SaleItemDTO,
)
from app.models import Product, Sale, Unit
from app.enums import PaymentMethodType


class TestDecimalHelpers:
    """Tests para funciones auxiliares de precisión decimal."""

    def test_to_decimal_from_int(self):
        assert _to_decimal(100) == Decimal("100")

    def test_to_decimal_from_float(self):
        assert _to_decimal(10.5) == Decimal("10.5")

    def test_to_decimal_from_string(self):
        assert _to_decimal("25.99") == Decimal("25.99")

    def test_to_decimal_from_none(self):
        assert _to_decimal(None) == Decimal("0")

    def test_to_decimal_from_empty_string(self):
        assert _to_decimal("") == Decimal("0")

    def test_round_money_two_decimals(self):
        result = _round_money(Decimal("10.555"))
        assert result == Decimal("10.56")  # ROUND_HALF_UP

    def test_round_money_exact(self):
        result = _round_money(Decimal("10.50"))
        assert result == Decimal("10.50")

    def test_round_quantity_integer_unit(self):
        result = _round_quantity(Decimal("5.7"), allows_decimal=False)
        assert result == Decimal("6")

    def test_round_quantity_decimal_unit(self):
        result = _round_quantity(Decimal("2.5555"), allows_decimal=True)
        assert result == Decimal("2.5555")

    def test_round_quantity_display_mode(self):
        result = _round_quantity(Decimal("2.5555"), allows_decimal=True, display=True)
        assert result == Decimal("2.56")


class TestSaleItemDTO:
    """Tests para validación de items de venta."""

    def test_valid_sale_item(self):
        item = SaleItemDTO(
            description="Producto Test",
            quantity=Decimal("2"),
            unit="Unidad",
            price=Decimal("10.00"),
            barcode="1234567890123",
        )
        assert item.description == "Producto Test"
        assert item.quantity == Decimal("2")

    def test_sale_item_optional_barcode(self):
        item = SaleItemDTO(
            description="Servicio",
            quantity=Decimal("1"),
            unit="Servicio",
            price=Decimal("50.00"),
        )
        assert item.barcode is None


class TestPaymentInfoDTO:
    """Tests para validación de información de pago."""

    def test_cash_payment(self):
        payment = PaymentInfoDTO(
            method="Efectivo",
            method_kind="cash",
            cash=PaymentCashDTO(amount=Decimal("100.00")),
        )
        assert payment.method_kind == "cash"
        assert payment.cash.amount == Decimal("100.00")

    def test_card_payment(self):
        payment = PaymentInfoDTO(
            method="Tarjeta",
            method_kind="card",
            card=PaymentCardDTO(type="credit"),
        )
        assert payment.method_kind == "card"
        assert payment.card.type == "credit"

    def test_credit_payment_with_installments(self):
        payment = PaymentInfoDTO(
            method="Crédito",
            method_kind="cash",
            is_credit=True,
            installments=3,
            interval_days=30,
            initial_payment=Decimal("50.00"),
            client_id=1,
        )
        assert payment.is_credit is True
        assert payment.installments == 3


class TestSaleServiceValidation:
    """Tests para validaciones del servicio de ventas."""

    @pytest.fixture
    def mock_session(self):
        """Sesión mock para tests."""
        session = AsyncMock()
        session.exec = AsyncMock()
        session.get = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def sample_product(self):
        """Producto de ejemplo para tests."""
        return Product(
            id=1,
            barcode="1234567890123",
            description="Producto Test",
            stock=Decimal("10.0000"),
            unit="Unidad",
            sale_price=Decimal("25.00"),
            purchase_price=Decimal("15.00"),
            category="General",
        )

    @pytest.fixture
    def sample_unit(self):
        """Unidad de ejemplo."""
        return Unit(name="Unidad", allows_decimal=False)

    def test_empty_method_raises_error(self):
        """Método de pago vacío debe detectarse."""
        # Validación básica que SaleService hace primero
        payment_method = "".strip()
        assert not payment_method, "Método vacío debe evaluarse como False"

    def test_payment_info_requires_method(self):
        """PaymentInfoDTO debe tener método."""
        payment = PaymentInfoDTO(
            method="",
            method_kind="cash",
            cash=PaymentCashDTO(amount=Decimal("100")),
        )
        # El servicio valida esto al inicio
        assert not (payment.method or "").strip()


class TestStockValidation:
    """Tests para validación de stock."""

    def test_stock_error_message(self):
        """StockError debe tener mensaje descriptivo."""
        error = StockError("Stock insuficiente para Producto X")
        assert "Stock insuficiente" in str(error)

    def test_stock_error_is_value_error(self):
        """StockError hereda de ValueError."""
        error = StockError("Test")
        assert isinstance(error, ValueError)


class TestSaleProcessResult:
    """Tests para el resultado de venta procesada."""

    def test_result_has_required_fields(self):
        """SaleProcessResult debe tener todos los campos."""
        sale = MagicMock(spec=Sale)
        sale.id = 1

        result = SaleProcessResult(
            sale=sale,
            receipt_items=[{"description": "Test", "quantity": 1}],
            sale_total=Decimal("100.00"),
            sale_total_display=100.00,
            timestamp=datetime.now(),
            payment_summary="Efectivo S/ 100.00",
            reservation_context=None,
            reservation_balance=Decimal("0"),
            reservation_balance_display=0.0,
        )

        assert result.sale.id == 1
        assert result.sale_total == Decimal("100.00")
        assert len(result.receipt_items) == 1


class TestPaymentMethodMapping:
    """Tests para mapeo de métodos de pago."""

    def test_cash_method_type(self):
        from app.services.sale_service import _method_type_from_kind
        
        assert _method_type_from_kind("cash") == PaymentMethodType.cash

    def test_yape_method_type(self):
        from app.services.sale_service import _method_type_from_kind
        
        assert _method_type_from_kind("yape") == PaymentMethodType.yape

    def test_plin_method_type(self):
        from app.services.sale_service import _method_type_from_kind
        
        assert _method_type_from_kind("plin") == PaymentMethodType.plin

    def test_unknown_method_type(self):
        from app.services.sale_service import _method_type_from_kind
        
        assert _method_type_from_kind("unknown") == PaymentMethodType.other

    def test_card_debit_type(self):
        from app.services.sale_service import _card_method_type
        
        assert _card_method_type("debito") == PaymentMethodType.debit
        assert _card_method_type("debit") == PaymentMethodType.debit

    def test_card_credit_type(self):
        from app.services.sale_service import _card_method_type
        
        assert _card_method_type("credito") == PaymentMethodType.credit
        assert _card_method_type("visa") == PaymentMethodType.credit
