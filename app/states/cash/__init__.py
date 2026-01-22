"""Mixins para CashState - División modular de responsabilidades.

Este paquete contiene mixins que dividen la funcionalidad del estado de caja
en módulos más pequeños y manejables, siguiendo el Principio de Responsabilidad Única.

Mixins disponibles:
    PaymentUtilsMixin: Utilidades para procesamiento de métodos de pago
    PettyCashMixin: Gestión de caja chica (gastos menores)
    CashExportMixin: Exportación de reportes (Excel/PDF)
"""
from .payment_utils_mixin import PaymentUtilsMixin
from .petty_cash_mixin import PettyCashMixin
from .export_mixin import CashExportMixin

__all__ = ["PaymentUtilsMixin", "PettyCashMixin", "CashExportMixin"]
