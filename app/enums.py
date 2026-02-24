"""Enumeraciones del sistema de ventas.

Define los valores válidos para estados, métodos de pago y tipos de deporte.
"""
from enum import Enum

class ReservationStatus(str, Enum):
    """Estados posibles de una reservación."""
    pending = "pending"
    paid = "paid"
    cancelled = "cancelled"
    refunded = "refunded"

    PENDING = pending
    PAID = paid
    CANCELLED = cancelled
    REFUNDED = refunded

class SaleStatus(str, Enum):
    """Estados posibles de una venta."""
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"

    PENDING = pending
    COMPLETED = completed
    CANCELLED = cancelled

class PaymentMethodType(str, Enum):
    """Tipos de método de pago soportados por el sistema."""
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
    """Tipos de deporte disponibles para canchas/servicios."""
    futbol = "futbol"
    voley = "voley"

    FUTBOL = futbol
    VOLEY = voley
