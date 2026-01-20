import pytest

from app.enums import PaymentMethodType
from app.states.services_state import ServicesState


def test_build_reservation_payments_cash_caps_total():
    state = ServicesState()
    state.payment_method_kind = "cash"
    state.payment_cash_amount = 200

    allocations = state._build_reservation_payments(100)

    method, amount = allocations[0]
    assert method == PaymentMethodType.CASH
    assert amount == pytest.approx(100.0)


def test_build_reservation_payments_card_uses_total():
    state = ServicesState()
    state.payment_method_kind = "card"
    state.payment_card_type = "debit"

    allocations = state._build_reservation_payments(80)

    method, amount = allocations[0]
    assert method == PaymentMethodType.DEBIT
    assert amount == pytest.approx(80.0)


def test_build_reservation_payments_mixed_allocates_remainder():
    state = ServicesState()
    state.payment_method_kind = "mixed"
    state.payment_mixed_non_cash_kind = "transfer"
    state.payment_mixed_card = 20
    state.payment_mixed_wallet = 10
    state.payment_mixed_cash = 0
    state.payment_wallet_provider = "plin"

    allocations = state._build_reservation_payments(100)

    assert allocations[0][0] == PaymentMethodType.TRANSFER
    assert allocations[0][1] == pytest.approx(90.0)
    assert allocations[1][0] == PaymentMethodType.PLIN
    assert allocations[1][1] == pytest.approx(10.0)
