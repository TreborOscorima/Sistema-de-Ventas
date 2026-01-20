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
