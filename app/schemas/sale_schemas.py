from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict
except ImportError:  # Pydantic v1
    ConfigDict = None


class BaseSchema(BaseModel):
    if ConfigDict is not None:
        model_config = ConfigDict(extra="ignore")
    else:
        class Config:
            extra = "ignore"

    def to_dict(self) -> dict:
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()


class SaleItemDTO(BaseSchema):
    description: str
    quantity: Decimal
    unit: str = ""
    price: Decimal
    sale_price: Decimal | None = None
    subtotal: Decimal | None = None
    barcode: str | None = None
    category: str | None = None


class PaymentBreakdownItemDTO(BaseSchema):
    label: str = ""
    amount: Decimal = Decimal("0.00")


class PaymentCashDTO(BaseSchema):
    amount: Decimal = Decimal("0.00")
    message: str = ""
    status: str = ""


class PaymentCardDTO(BaseSchema):
    type: str = ""


class PaymentWalletDTO(BaseSchema):
    provider: str = ""
    choice: str = ""


class PaymentMixedDTO(BaseSchema):
    cash: Decimal = Decimal("0.00")
    card: Decimal = Decimal("0.00")
    wallet: Decimal = Decimal("0.00")
    non_cash_kind: str = ""
    notes: str = ""
    message: str = ""
    status: str = ""


class PaymentInfoDTO(BaseSchema):
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
