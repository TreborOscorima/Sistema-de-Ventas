from enum import Enum

class ReservationStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    cancelled = "cancelled"
    refunded = "refunded"

    PENDING = pending
    PAID = paid
    CANCELLED = cancelled
    REFUNDED = refunded

class SaleStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"

    PENDING = pending
    COMPLETED = completed
    CANCELLED = cancelled

class PaymentMethodType(str, Enum):
    cash = "cash"
    card = "card"
    transfer = "transfer"
    wallet = "wallet"
    mixed = "mixed"
    other = "other"

    CASH = cash
    CARD = card
    TRANSFER = transfer
    WALLET = wallet
    MIXED = mixed
    OTHER = other

class SportType(str, Enum):
    futbol = "futbol"
    voley = "voley"

    FUTBOL = futbol
    VOLEY = voley
