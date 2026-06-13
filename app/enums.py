"""Enumeraciones del sistema de ventas.

Las enumeraciones de plataforma viven en tuwayki_core.enums.
Aquí se re-exportan para compatibilidad y se agregan las específicas de Ventas.
"""
from enum import Enum

# ── Re-export de enums de plataforma ─────────────────────────────────────────
from tuwayki_core.enums import (  # noqa: F401
    SaleStatus,
    PaymentMethodType,
    ReturnReason,
    ReceiptType,
    FiscalStatus,
)


# ── Enums específicos de Ventas ───────────────────────────────────────────────

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


class SportType(str, Enum):
    """Tipos de deporte disponibles para canchas/servicios."""
    futbol = "futbol"
    voley = "voley"

    FUTBOL = futbol
    VOLEY = voley
