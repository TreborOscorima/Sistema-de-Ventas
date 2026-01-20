import datetime
from decimal import Decimal
from unittest.mock import Mock

import reflex as rx

from app.enums import PaymentMethodType, ReservationStatus
from app.models import CashboxLog, FieldReservation, Sale, SalePayment, SaleItem, User
from app.states.services_state import ServicesState


class ExecResult:
    def __init__(self, all_items=None, first_item=None) -> None:
        self._all_items = all_items if all_items is not None else []
        self._first_item = first_item

    def all(self):
        return self._all_items

    def first(self):
        return self._first_item


class FakeSession:
    def __init__(self, exec_results):
        self.exec_results = exec_results
        self.exec_calls = 0
        self.added = []
        self.commit = Mock()

    def exec(self, statement):
        result = self.exec_results[self.exec_calls]
        self.exec_calls += 1
        return result

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        for obj in self.added:
            if isinstance(obj, Sale) and getattr(obj, "id", None) is None:
                obj.id = 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_apply_reservation_payment_partial_creates_logs(monkeypatch):
    state = ServicesState()
    state.current_user = {
        "username": "alice",
        "privileges": {"manage_reservations": True},
    }
    state.reservation_payment_id = "1"
    state.reservation_payment_amount = "50"
    state.payment_method = "Efectivo"
    state.payment_method_kind = "mixed"
    state.payment_mixed_non_cash_kind = "debit"
    state.payment_card_type = "debit"
    state.payment_mixed_card = 30
    state.payment_mixed_wallet = 0
    state.payment_mixed_cash = 20

    reservation = {
        "id": "1",
        "status": "pendiente",
        "total_amount": 100.0,
        "paid_amount": 40.0,
        "field_name": "Cancha 1",
    }
    state._find_reservation_by_id = lambda rid: reservation
    state._log_service_action = lambda *args, **kwargs: None
    state._set_last_reservation_receipt = lambda *args, **kwargs: None

    user = User(username="alice", password_hash="x", role_id=1)
    reservation_model = FieldReservation(
        id=1,
        client_name="Cliente Test",
        field_name="Cancha 1",
        start_datetime=datetime.datetime(2024, 1, 1, 10, 0),
        end_datetime=datetime.datetime(2024, 1, 1, 11, 0),
        total_amount=Decimal("100.00"),
        paid_amount=Decimal("40.00"),
        status=ReservationStatus.PENDING,
    )
    fake_session = FakeSession(
        [ExecResult(first_item=user), ExecResult(first_item=reservation_model)]
    )
    monkeypatch.setattr(rx, "session", lambda: fake_session)
    monkeypatch.setattr(rx, "toast", lambda *args, **kwargs: None)

    state.apply_reservation_payment()

    payments = [
        obj for obj in fake_session.added if isinstance(obj, SalePayment)
    ]
    methods = {payment.method_type for payment in payments}
    log = next(
        obj for obj in fake_session.added if isinstance(obj, CashboxLog)
    )

    assert reservation["paid_amount"] == 90.0
    assert reservation["status"] == "pendiente"
    assert methods == {PaymentMethodType.DEBIT, PaymentMethodType.CASH}
    assert log.action == "Adelanto"
    assert log.sale_id is not None
    assert any(isinstance(obj, SaleItem) for obj in fake_session.added)
    fake_session.commit.assert_called_once()


def test_pay_reservation_with_payment_method_full_payment(monkeypatch):
    state = ServicesState()
    state.current_user = {
        "username": "bob",
        "privileges": {"manage_reservations": True},
    }
    state.reservation_payment_id = "2"
    state.payment_method = "Efectivo"
    state.payment_method_kind = "cash"
    state.payment_cash_amount = 60
    state.payment_cash_status = "exact"
    state._update_cash_feedback = lambda **kwargs: None

    reservation = {
        "id": "2",
        "status": "pendiente",
        "total_amount": 100.0,
        "paid_amount": 40.0,
        "field_name": "Cancha 2",
    }
    state._find_reservation_by_id = lambda rid: reservation
    state._log_service_action = lambda *args, **kwargs: None
    state._set_last_reservation_receipt = lambda *args, **kwargs: None

    user = User(username="bob", password_hash="x", role_id=1)
    reservation_model = FieldReservation(
        id=2,
        client_name="Cliente Dos",
        field_name="Cancha 2",
        start_datetime=datetime.datetime(2024, 1, 1, 12, 0),
        end_datetime=datetime.datetime(2024, 1, 1, 13, 0),
        total_amount=Decimal("100.00"),
        paid_amount=Decimal("40.00"),
        status=ReservationStatus.PENDING,
    )
    fake_session = FakeSession(
        [ExecResult(first_item=user), ExecResult(first_item=reservation_model)]
    )
    monkeypatch.setattr(rx, "session", lambda: fake_session)
    monkeypatch.setattr(rx, "toast", lambda *args, **kwargs: None)

    state.pay_reservation_with_payment_method()

    payments = [
        obj for obj in fake_session.added if isinstance(obj, SalePayment)
    ]
    log = next(
        obj for obj in fake_session.added if isinstance(obj, CashboxLog)
    )

    assert reservation["paid_amount"] == 100.0
    assert reservation["status"] == "pagado"
    assert len(payments) == 1
    assert payments[0].method_type == PaymentMethodType.CASH
    assert payments[0].amount == Decimal("60.00")
    assert log.action == "Reserva"
    assert log.sale_id is not None
    fake_session.commit.assert_called_once()
