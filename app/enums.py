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
    debit = "debit"
    credit = "credit"
    yape = "yape"
    plin = "plin"
    transfer = "transfer"
    mixed = "mixed"
    other = "other"
    card = "card"
    wallet = "wallet"

    CASH = cash
    DEBIT = debit
    CREDIT = credit
    YAPE = yape
    PLIN = plin
    TRANSFER = transfer
    MIXED = mixed
    OTHER = other
    CARD = card
    WALLET = wallet

class SportType(str, Enum):
    futbol = "futbol"
    voley = "voley"

    FUTBOL = futbol
    VOLEY = voley
