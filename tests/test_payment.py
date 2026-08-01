"""Tests para app/utils/payment.py"""
import pytest
from app.enums import PaymentMethodType
from app.utils.payment import (
    normalize_payment_method_kind,
    card_method_type,
    wallet_method_type,
    wallet_method_type_scoped,
    payment_method_code,
    payment_method_label,
    normalize_wallet_label,
    payment_category,
)


class TestWalletMethodTypeScoped:
    """Regresión: billeteras país-específicas NO deben colapsar a Yape.

    Bug real: MODO/Cuenta DNI (Argentina) se registraban con el
    payment_method_id de Yape porque wallet_method_type() defaultea a yape.
    El helper scoped devuelve `other` para que el id se resuelva por nombre.
    """

    def test_yape_plin_keep_specific_type(self):
        assert wallet_method_type_scoped("Yape") == PaymentMethodType.yape
        assert wallet_method_type_scoped("yape") == PaymentMethodType.yape
        assert wallet_method_type_scoped("Plin") == PaymentMethodType.plin

    def test_argentine_wallets_map_to_other_not_yape(self):
        for provider in ("MODO", "Cuenta DNI", "Mercado Pago"):
            result = wallet_method_type_scoped(provider)
            assert result == PaymentMethodType.other, (
                f"{provider} debería mapear a 'other', no a {result}"
            )
            assert result != PaymentMethodType.yape

    def test_future_country_wallets_map_to_other(self):
        # Colombia (Nequi/Daviplata), Bolivia, etc.: cualquier billetera
        # desconocida cae en 'other' → se resuelve por nombre/ID real.
        for provider in ("Nequi", "Daviplata", "QR Simple", ""):
            assert wallet_method_type_scoped(provider) == PaymentMethodType.other


class TestNormalizePaymentMethodKind:
    def test_cash_variants(self):
        assert normalize_payment_method_kind("cash") == PaymentMethodType.cash
        assert normalize_payment_method_kind("efectivo") == PaymentMethodType.cash
        assert normalize_payment_method_kind("CASH") == PaymentMethodType.cash
    
    def test_card_variants(self):
        assert normalize_payment_method_kind("debit") == PaymentMethodType.debit
        assert normalize_payment_method_kind("debito") == PaymentMethodType.debit
        assert normalize_payment_method_kind("credit") == PaymentMethodType.credit
        assert normalize_payment_method_kind("credito") == PaymentMethodType.credit
        assert normalize_payment_method_kind("card") == PaymentMethodType.credit
        assert normalize_payment_method_kind("tarjeta") == PaymentMethodType.credit
    
    def test_wallet_variants(self):
        assert normalize_payment_method_kind("yape") == PaymentMethodType.yape
        assert normalize_payment_method_kind("plin") == PaymentMethodType.plin
        assert normalize_payment_method_kind("wallet") == PaymentMethodType.yape
        assert normalize_payment_method_kind("billetera") == PaymentMethodType.yape
    
    def test_transfer(self):
        assert normalize_payment_method_kind("transfer") == PaymentMethodType.transfer
        assert normalize_payment_method_kind("transferencia") == PaymentMethodType.transfer
    
    def test_mixed(self):
        assert normalize_payment_method_kind("mixed") == PaymentMethodType.mixed
        assert normalize_payment_method_kind("mixto") == PaymentMethodType.mixed
    
    def test_unknown_returns_other(self):
        assert normalize_payment_method_kind("unknown") == PaymentMethodType.other
        assert normalize_payment_method_kind("") == PaymentMethodType.other
        assert normalize_payment_method_kind(None) == PaymentMethodType.other


class TestCardMethodType:
    def test_debit_detection(self):
        assert card_method_type("debito") == PaymentMethodType.debit
        assert card_method_type("débito") == PaymentMethodType.debit
        assert card_method_type("Tarjeta de Débito") == PaymentMethodType.debit
    
    def test_credit_default(self):
        assert card_method_type("credito") == PaymentMethodType.credit
        assert card_method_type("") == PaymentMethodType.credit
        assert card_method_type("unknown") == PaymentMethodType.credit


class TestWalletMethodType:
    def test_plin_detection(self):
        assert wallet_method_type("plin") == PaymentMethodType.plin
        assert wallet_method_type("Plin") == PaymentMethodType.plin
    
    def test_yape_default(self):
        assert wallet_method_type("yape") == PaymentMethodType.yape
        assert wallet_method_type("") == PaymentMethodType.yape
        assert wallet_method_type("other") == PaymentMethodType.yape


class TestPaymentMethodCode:
    def test_known_methods(self):
        assert payment_method_code(PaymentMethodType.cash) == "cash"
        assert payment_method_code(PaymentMethodType.yape) == "yape"
        assert payment_method_code(PaymentMethodType.plin) == "plin"
        assert payment_method_code(PaymentMethodType.debit) == "debit_card"
        assert payment_method_code(PaymentMethodType.credit) == "credit_card"
    
    def test_unknown_returns_none(self):
        assert payment_method_code(PaymentMethodType.other) is None


class TestPaymentMethodLabel:
    def test_spanish_labels(self):
        assert payment_method_label("cash") == "Efectivo"
        assert payment_method_label("debit") == "Tarjeta de Débito"
        assert payment_method_label("credit") == "Tarjeta de Crédito"
        assert payment_method_label("yape") == "Billetera Digital (Yape)"
        assert payment_method_label("plin") == "Billetera Digital (Plin)"
        assert payment_method_label("transfer") == "Transferencia Bancaria"
        assert payment_method_label("mixed") == "Pago Mixto"
    
    def test_unknown_returns_otros(self):
        assert payment_method_label("unknown") == "Otros"
        assert payment_method_label("") == "Otros"


class TestNormalizeWalletLabel:
    def test_basic_mappings(self):
        assert normalize_wallet_label("cash") == "Efectivo"
        assert normalize_wallet_label("yape") == "Billetera Digital (Yape)"
    
    def test_content_detection(self):
        assert "Yape" in normalize_wallet_label("pago con yape")
        assert "Plin" in normalize_wallet_label("billetera plin")
        assert "Efectivo" in normalize_wallet_label("pago efectivo")
    
    def test_preserves_unknown(self):
        assert normalize_wallet_label("Método Personalizado") == "Método Personalizado"
    
    def test_handles_empty(self):
        assert normalize_wallet_label("") == ""
        assert normalize_wallet_label(None) == ""


class TestPaymentCategory:
    def test_by_kind(self):
        assert payment_category("", "cash") == "Efectivo"
        assert payment_category("", "yape") == "Billetera Digital (Yape)"
        assert payment_category("", "mixed") == "Pago Mixto"
    
    def test_by_label(self):
        assert payment_category("pago efectivo", "") == "Efectivo"
        assert payment_category("tarjeta debito", "") == "Tarjeta de Débito"
    
    def test_kind_takes_precedence(self):
        assert payment_category("efectivo", "yape") == "Billetera Digital (Yape)"
    
    def test_unknown_returns_otros(self):
        assert payment_category("", "") == "Otros"
        assert payment_category("unknown", "unknown") == "Otros"
