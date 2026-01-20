from decimal import Decimal

import pytest

from app.models import CashboxLog, Client, Sale, SaleInstallment
from app.services.credit_service import CreditService


@pytest.mark.asyncio
async def test_pay_installment_rejects_overpay(session_mock, exec_result):
    installment = SaleInstallment(
        id=1,
        sale_id=1,
        amount=Decimal("100.00"),
        paid_amount=Decimal("20.00"),
        status="pending",
    )
    sale = Sale(id=1, client_id=1)
    client = Client(id=1, current_debt=Decimal("80.00"))

    session_mock.exec.side_effect = [
        exec_result(first_item=installment),
        exec_result(first_item=sale),
        exec_result(first_item=client),
    ]

    with pytest.raises(ValueError):
        await CreditService.pay_installment(
            session=session_mock,
            installment_id=1,
            amount=Decimal("90.00"),
            payment_method="Efectivo",
            user_id=1,
        )


@pytest.mark.asyncio
async def test_pay_installment_records_sale_id(session_mock, exec_result):
    installment = SaleInstallment(
        id=2,
        sale_id=2,
        amount=Decimal("50.00"),
        paid_amount=Decimal("0.00"),
        status="pending",
    )
    sale = Sale(id=2, client_id=2)
    client = Client(id=2, current_debt=Decimal("50.00"))

    session_mock.exec.side_effect = [
        exec_result(first_item=installment),
        exec_result(first_item=sale),
        exec_result(first_item=client),
    ]

    await CreditService.pay_installment(
        session=session_mock,
        installment_id=2,
        amount=Decimal("20.00"),
        payment_method="Efectivo",
        user_id=99,
    )

    logs = [obj for obj in session_mock.added if isinstance(obj, CashboxLog)]
    assert any(log.sale_id == sale.id for log in logs)


@pytest.mark.asyncio
async def test_pay_installment_partial_updates_status_and_debt(
    session_mock, exec_result
):
    installment = SaleInstallment(
        id=3,
        sale_id=3,
        amount=Decimal("100.00"),
        paid_amount=Decimal("0.00"),
        status="pending",
    )
    sale = Sale(id=3, client_id=3)
    client = Client(id=3, current_debt=Decimal("100.00"))

    session_mock.exec.side_effect = [
        exec_result(first_item=installment),
        exec_result(first_item=sale),
        exec_result(first_item=client),
    ]

    result = await CreditService.pay_installment(
        session=session_mock,
        installment_id=3,
        amount=Decimal("40.00"),
        payment_method="Efectivo",
        user_id=10,
    )

    assert result.status == "partial"
    assert result.paid_amount == Decimal("40.00")
    assert result.payment_date is None
    assert client.current_debt == Decimal("60.00")


@pytest.mark.asyncio
async def test_pay_installment_full_marks_paid(session_mock, exec_result):
    installment = SaleInstallment(
        id=4,
        sale_id=4,
        amount=Decimal("100.00"),
        paid_amount=Decimal("80.00"),
        status="partial",
    )
    sale = Sale(id=4, client_id=4)
    client = Client(id=4, current_debt=Decimal("20.00"))

    session_mock.exec.side_effect = [
        exec_result(first_item=installment),
        exec_result(first_item=sale),
        exec_result(first_item=client),
    ]

    result = await CreditService.pay_installment(
        session=session_mock,
        installment_id=4,
        amount=Decimal("20.00"),
        payment_method="Efectivo",
        user_id=11,
    )

    assert result.status == "paid"
    assert result.paid_amount == Decimal("100.00")
    assert result.payment_date is not None
    assert client.current_debt == Decimal("0.00")
