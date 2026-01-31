from decimal import Decimal

import pytest

from app.enums import PaymentMethodType
from app.models import CashboxLog, Client, Sale, SaleItem, SalePayment, Product
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
        exec_result(first_item=session_mock.get.return_value),
    ]

    result = await SaleService.process_sale(
        session=session_mock,
        company_id=1,
        branch_id=1,
        user_id=sale_data_sample["user_id"],
        items=sale_data_sample["items"],
        payment_data=sale_data_sample["payment_data"],
    )

    assert isinstance(result, SaleProcessResult)
    assert result.sale_total == Decimal("5.00")
    assert any(isinstance(obj, Sale) for obj in session_mock.added)


@pytest.mark.asyncio
async def test_process_sale_cashbox_log_records_sale_id(
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
        company_id=1,
        branch_id=1,
        user_id=sale_data_sample["user_id"],
        items=sale_data_sample["items"],
        payment_data=sale_data_sample["payment_data"],
    )

    logs = [obj for obj in session_mock.added if isinstance(obj, CashboxLog)]
    log = next((entry for entry in logs if entry.action == "Venta"), None)

    assert log is not None
    assert log.sale_id == result.sale.id
    assert log.amount == result.sale_total


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
            company_id=1,
            branch_id=1,
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
        company_id=1,
        branch_id=1,
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
        company_id=1,
        branch_id=1,
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


@pytest.mark.asyncio
async def test_process_sale_prefers_barcode_match(
    session_mock,
    exec_result,
    unit_sample,
):
    product_a = Product(
        id=1,
        barcode="111",
        description="Producto Duplicado",
        stock=Decimal("5.0000"),
        unit="Unidad",
        sale_price=Decimal("5.00"),
    )
    product_b = Product(
        id=2,
        barcode="222",
        description="Producto Duplicado",
        stock=Decimal("5.0000"),
        unit="Unidad",
        sale_price=Decimal("5.00"),
    )
    item = SaleItemDTO(
        description=product_b.description,
        quantity=Decimal("1"),
        unit=product_b.unit,
        price=Decimal("5.00"),
        barcode=product_b.barcode,
    )
    payment_data = PaymentInfoDTO(
        method="cash",
        method_kind="cash",
        cash=PaymentCashDTO(amount=Decimal("5.00")),
    )
    session_mock.exec.side_effect = [
        exec_result(all_items=[]),
        exec_result(all_items=[unit_sample]),
        exec_result(all_items=[product_a, product_b]),
    ]

    await SaleService.process_sale(
        session=session_mock,
        company_id=1,
        branch_id=1,
        user_id=1,
        items=[item],
        payment_data=payment_data,
    )

    sale_items = [
        obj for obj in session_mock.added if isinstance(obj, SaleItem)
    ]
    assert any(sale_item.product_id == product_b.id for sale_item in sale_items)


@pytest.mark.asyncio
async def test_process_sale_ambiguous_description_requires_barcode(
    session_mock,
    exec_result,
    unit_sample,
):
    product_a = Product(
        id=1,
        barcode="111",
        description="Producto Duplicado",
        stock=Decimal("5.0000"),
        unit="Unidad",
        sale_price=Decimal("5.00"),
    )
    product_b = Product(
        id=2,
        barcode="222",
        description="Producto Duplicado",
        stock=Decimal("5.0000"),
        unit="Unidad",
        sale_price=Decimal("5.00"),
    )
    item = SaleItemDTO(
        description=product_a.description,
        quantity=Decimal("1"),
        unit=product_a.unit,
        price=Decimal("5.00"),
        barcode=None,
    )
    payment_data = PaymentInfoDTO(
        method="cash",
        method_kind="cash",
        cash=PaymentCashDTO(amount=Decimal("5.00")),
    )
    session_mock.exec.side_effect = [
        exec_result(all_items=[]),
        exec_result(all_items=[unit_sample]),
        exec_result(all_items=[product_a, product_b]),
    ]

    with pytest.raises(StockError):
        await SaleService.process_sale(
            session=session_mock,
            company_id=1,
            branch_id=1,
            user_id=1,
            items=[item],
            payment_data=payment_data,
        )


@pytest.mark.asyncio
async def test_process_sale_credit_cashbox_uses_initial_payment(
    session_mock,
    exec_result,
    unit_sample,
    product_sample,
):
    product_sample.sale_price = Decimal("50.00")
    item = SaleItemDTO(
        description=product_sample.description,
        quantity=Decimal("1"),
        unit=product_sample.unit,
        price=Decimal("50.00"),
        barcode=product_sample.barcode,
    )
    payment_data = PaymentInfoDTO(
        method="cash",
        method_kind="cash",
        is_credit=True,
        client_id=1,
        initial_payment=Decimal("10.00"),
        installments=2,
        interval_days=30,
        cash=PaymentCashDTO(amount=Decimal("10.00")),
    )
    client = Client(
        id=1,
        name="Cliente Test",
        dni="00000000",
        credit_limit=Decimal("100.00"),
        current_debt=Decimal("0.00"),
    )
    session_mock.get.return_value = client
    session_mock.exec.side_effect = [
        exec_result(all_items=[]),
        exec_result(all_items=[unit_sample]),
        exec_result(all_items=[product_sample]),
        exec_result(first_item=client),
    ]

    result = await SaleService.process_sale(
        session=session_mock,
        company_id=1,
        branch_id=1,
        user_id=1,
        items=[item],
        payment_data=payment_data,
    )

    logs = [obj for obj in session_mock.added if isinstance(obj, CashboxLog)]
    log = next((entry for entry in logs if entry.action == "Inicial Credito"), None)

    assert log is not None
    assert log.sale_id == result.sale.id
    assert log.amount == Decimal("10.00")
