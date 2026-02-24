from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Esquema base con configuración común para DTOs del sistema."""

    model_config = ConfigDict(extra="ignore")

    def to_dict(self) -> dict:
        return self.model_dump()


class SaleItemDTO(BaseSchema):
    """DTO de un ítem de venta con datos del producto."""

    description: str
    quantity: Decimal
    unit: str = ""
    price: Decimal
    sale_price: Decimal | None = None
    subtotal: Decimal | None = None
    barcode: str | None = None
    category: str | None = None
    product_id: int | None = None
    variant_id: int | None = None


class PaymentBreakdownItemDTO(BaseSchema):
    """DTO de un ítem del desglose de pago."""

    label: str = ""
    amount: Decimal = Decimal("0.00")


class PaymentCashDTO(BaseSchema):
    """DTO de datos de pago en efectivo."""

    amount: Decimal = Decimal("0.00")
    message: str = ""
    status: str = ""


class PaymentCardDTO(BaseSchema):
    """DTO de datos de pago con tarjeta."""

    type: str = ""


class PaymentWalletDTO(BaseSchema):
    """DTO de datos de pago con billetera digital."""

    provider: str = ""
    choice: str = ""


class PaymentMixedDTO(BaseSchema):
    """DTO de datos de pago mixto (efectivo + electrónico)."""

    cash: Decimal = Decimal("0.00")
    card: Decimal = Decimal("0.00")
    wallet: Decimal = Decimal("0.00")
    non_cash_kind: str = ""
    notes: str = ""
    message: str = ""
    status: str = ""


class PaymentInfoDTO(BaseSchema):
    """DTO con toda la información de pago de una venta."""

    summary: str = ""
    method: str = ""
    method_kind: str = ""
    label: str = ""
    client_id: int | None = None
    is_credit: bool = False
    installments: int = 1
    interval_days: int = 30
    initial_payment: Decimal = Decimal("0.00")
    breakdown: list[PaymentBreakdownItemDTO] = Field(default_factory=list)
    total: Decimal = Decimal("0.00")
    cash: PaymentCashDTO = Field(default_factory=PaymentCashDTO)
    card: PaymentCardDTO = Field(default_factory=PaymentCardDTO)
    wallet: PaymentWalletDTO = Field(default_factory=PaymentWalletDTO)
    mixed: PaymentMixedDTO = Field(default_factory=PaymentMixedDTO)
