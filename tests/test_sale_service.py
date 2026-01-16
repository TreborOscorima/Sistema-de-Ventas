from decimal import Decimal

import pytest

from app.enums import PaymentMethodType
from app.models import Sale, SalePayment
from app.schemas.sale_schemas import (
    PaymentCardDTO,
    PaymentCashDTO,
    PaymentInfoDTO,
    PaymentMixedDTO,
    SaleItemDTO,
)
from app.services.sale_service import SaleProcessResult, SaleService, StockError


@pytest.mark.asyncio
async def test_process_sale_cash_happy_path(
    session_mock,
    exec_result,
    unit_sample,
    product_sample,
    sale_data_sample,
):
    session_mock.exec.side_effect = [
        exec_result(all_items=[]),
        exec_result(all_items=[unit_sample]),
        exec_result(all_items=[product_sample]),
    ]

    result = await SaleService.process_sale(
        session=session_mock,
        user_id=sale_data_sample["user_id"],
        items=sale_data_sample["items"],
        payment_data=sale_data_sample["payment_data"],
    )

    assert isinstance(result, SaleProcessResult)
    assert result.sale_total == Decimal("5.00")
    assert any(isinstance(obj, Sale) for obj in session_mock.added)


@pytest.mark.asyncio
async def test_process_sale_stock_insufficient(
    session_mock,
    exec_result,
    unit_sample,
    product_sample,
):
    product_sample.stock = Decimal("5.0000")
    item = SaleItemDTO(
        description=product_sample.description,
        quantity=Decimal("10"),
        unit=product_sample.unit,
        price=Decimal("5.00"),
        barcode=product_sample.barcode,
    )
    payment_data = PaymentInfoDTO(
        method="cash",
        method_kind="cash",
        cash=PaymentCashDTO(amount=Decimal("50.00")),
    )
    session_mock.exec.side_effect = [
        exec_result(all_items=[]),
        exec_result(all_items=[unit_sample]),
        exec_result(all_items=[product_sample]),
    ]

    with pytest.raises((StockError, ValueError)):
        await SaleService.process_sale(
            session=session_mock,
            user_id=1,
            items=[item],
            payment_data=payment_data,
        )


@pytest.mark.asyncio
async def test_process_sale_decimal_math(
    session_mock,
    exec_result,
    unit_sample,
    product_sample,
):
    item = SaleItemDTO(
        description=product_sample.description,
        quantity=Decimal("3"),
        unit=product_sample.unit,
        price=Decimal("10.00"),
        barcode=product_sample.barcode,
    )
    payment_data = PaymentInfoDTO(
        method="cash",
        method_kind="cash",
        cash=PaymentCashDTO(amount=Decimal("30.00")),
    )
    session_mock.exec.side_effect = [
        exec_result(all_items=[]),
        exec_result(all_items=[unit_sample]),
        exec_result(all_items=[product_sample]),
    ]

    result = await SaleService.process_sale(
        session=session_mock,
        user_id=1,
        items=[item],
        payment_data=payment_data,
    )

    assert result.sale_total == Decimal("30.00")


@pytest.mark.asyncio
async def test_process_sale_mixed_payment(
    session_mock,
    exec_result,
    unit_sample,
    product_sample,
):
    item = SaleItemDTO(
        description=product_sample.description,
        quantity=Decimal("2"),
        unit=product_sample.unit,
        price=Decimal("10.00"),
        barcode=product_sample.barcode,
    )
    payment_data = PaymentInfoDTO(
        method="mixed",
        method_kind="mixed",
        mixed=PaymentMixedDTO(
            cash=Decimal("10.00"),
            card=Decimal("10.00"),
            wallet=Decimal("0.00"),
            non_cash_kind="debit",
        ),
        card=PaymentCardDTO(type="debit"),
    )
    session_mock.exec.side_effect = [
        exec_result(all_items=[]),
        exec_result(all_items=[unit_sample]),
        exec_result(all_items=[product_sample]),
    ]

    await SaleService.process_sale(
        session=session_mock,
        user_id=1,
        items=[item],
        payment_data=payment_data,
    )

    payments = [
        obj for obj in session_mock.added if isinstance(obj, SalePayment)
    ]
    amounts = {(payment.method_type, payment.amount) for payment in payments}

    assert len(payments) == 2
    assert (PaymentMethodType.debit, Decimal("10.00")) in amounts
    assert (PaymentMethodType.cash, Decimal("10.00")) in amounts
