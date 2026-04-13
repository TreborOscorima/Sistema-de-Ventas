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
    returned = "returned"

    PENDING = pending
    COMPLETED = completed
    CANCELLED = cancelled
    RETURNED = returned


class ReturnReason(str, Enum):
    """Motivos de devolución."""
    defective = "defective"
    wrong_item = "wrong_item"
    change_mind = "change_mind"
    not_as_described = "not_as_described"
    other = "other"

    @property
    def display_label(self) -> str:
        labels = {
            "defective": "Producto defectuoso",
            "wrong_item": "Producto equivocado",
            "change_mind": "Cambio de opinión",
            "not_as_described": "No es lo esperado",
            "other": "Otro motivo",
        }
        return labels.get(self.value, self.value)

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


# ─────────────────────────────────────────────────────────────
# Facturación Electrónica
# ─────────────────────────────────────────────────────────────


class ReceiptType(str, Enum):
    """Tipo de comprobante fiscal emitido.

    Cubre los tipos requeridos por SUNAT (Perú) y AFIP (Argentina).
    - nota_venta: comprobante interno sin validez fiscal (NoOp / países sin billing).
    - boleta: B2C Perú (SUNAT catálogo 01 = "03") / Argentina (Factura B, CbteTipo=6).
    - factura: B2B Perú (SUNAT catálogo 01 = "01") / Argentina (Factura A, CbteTipo=1).
    - nota_credito: anulación o corrección de comprobante previo.
    - nota_debito: incremento de valor o intereses de mora.
    """

    nota_venta = "nota_venta"
    boleta = "boleta"
    factura = "factura"
    nota_credito = "nota_credito"
    nota_debito = "nota_debito"

    NOTA_VENTA = nota_venta
    BOLETA = boleta
    FACTURA = factura
    NOTA_CREDITO = nota_credito
    NOTA_DEBITO = nota_debito


class FiscalStatus(str, Enum):
    """Ciclo de vida de un documento fiscal electrónico.

    Flujo normal: none → pending → sent → authorized
    Flujo error:  none → pending → sent → rejected / error
    - none:       la venta no requiere emisión fiscal.
    - pending:    encolada, aún no enviada a la entidad fiscal.
    - sent:       enviada, esperando respuesta (transiente).
    - authorized: aprobada por SUNAT/AFIP — CAE/CDR recibido.
    - rejected:   rechazada por la entidad fiscal (datos incorrectos).
    - error:      fallo de transporte (timeout, red, servicio caído).
    """

    none = "none"
    pending = "pending"
    sent = "sent"
    authorized = "authorized"
    rejected = "rejected"
    error = "error"

    NONE = none
    PENDING = pending
    SENT = sent
    AUTHORIZED = authorized
    REJECTED = rejected
    ERROR = error
