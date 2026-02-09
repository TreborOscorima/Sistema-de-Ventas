from app.states.venta_state import VentaState


def test_cash_payment_requires_amount_for_non_credit_sale():
    state = VentaState()
    state.payment_method_kind = "cash"
    state.payment_cash_amount = 0

    state._refresh_payment_feedback(total_override=5.5)
    error = state._validate_payment_before_confirm(5.5, is_credit=False)

    assert error == "Ingrese un monto valido."


def test_cash_payment_validation_passes_with_exact_amount():
    state = VentaState()
    state.payment_method_kind = "cash"
    state.payment_cash_amount = 5.5

    state._refresh_payment_feedback(total_override=5.5)
    error = state._validate_payment_before_confirm(5.5, is_credit=False)

    assert error is None


def test_cash_payment_validation_uses_default_message_when_feedback_empty():
    state = VentaState()
    state.payment_method_kind = "cash"
    state.payment_cash_amount = 0
    state.payment_cash_message = ""

    error = state._validate_payment_before_confirm(5.5, is_credit=False)

    assert error == "Ingrese un monto valido en efectivo."
