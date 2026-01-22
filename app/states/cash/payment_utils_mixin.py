"""Mixin de utilidades de métodos de pago para CashState.

Este módulo contiene funciones puras para el procesamiento y formateo
de métodos de pago. No tiene dependencias de base de datos ni de UI.

Funciones incluidas:
    - Normalización de claves de método de pago
    - Etiquetas y abreviaciones localizadas
    - Ordenamiento consistente de métodos
    - Resúmenes y desgloses de pagos
"""
from typing import Any

from app.enums import PaymentMethodType


class PaymentUtilsMixin:
    """Utilidades para procesamiento de métodos de pago.
    
    Proporciona métodos para normalizar, formatear y resumir
    información de métodos de pago en ventas y transacciones.
    """

    def _payment_method_key(self, method_type: Any) -> str:
        """Normaliza un tipo de método de pago a una clave estándar.
        
        Args:
            method_type: Puede ser PaymentMethodType, objeto con .value, o string
            
        Returns:
            Clave normalizada en minúsculas (ej: 'cash', 'credit', 'yape')
        """
        if isinstance(method_type, PaymentMethodType):
            key = method_type.value
        elif hasattr(method_type, "value"):
            key = str(method_type.value).strip().lower()
        else:
            key = str(method_type or "").strip().lower()
        if key == "card":
            return "credit"
        if key == "wallet":
            return "yape"
        return key

    def _payment_method_label(self, method_key: str) -> str:
        """Obtiene la etiqueta legible para un método de pago.
        
        Args:
            method_key: Clave normalizada del método
            
        Returns:
            Nombre legible en español (ej: 'Efectivo', 'Tarjeta de Crédito')
        """
        mapping = {
            "cash": "Efectivo",
            "debit": "Tarjeta de Débito",
            "credit": "Tarjeta de Crédito",
            "yape": "Billetera Digital (Yape)",
            "plin": "Billetera Digital (Plin)",
            "transfer": "Transferencia Bancaria",
            "mixed": "Pago Mixto",
            "other": "Otros",
        }
        return mapping.get(method_key, "Otros")

    def _payment_method_abbrev(self, method_key: str) -> str:
        """Obtiene la abreviación de un método de pago.
        
        Args:
            method_key: Clave normalizada del método
            
        Returns:
            Abreviación corta (ej: 'Efe', 'Cre', 'Yap')
        """
        mapping = {
            "cash": "Efe",
            "debit": "Deb",
            "credit": "Cre",
            "yape": "Yap",
            "plin": "Plin",
            "transfer": "Transf",
            "mixed": "Mixto",
            "other": "Otro",
        }
        return mapping.get(method_key, "Otro")

    def _sorted_payment_keys(self, keys: list[str]) -> list[str]:
        """Ordena claves de métodos de pago en orden estándar.
        
        Args:
            keys: Lista de claves de métodos
            
        Returns:
            Lista ordenada según prioridad visual estándar
        """
        order = [
            "cash",
            "debit",
            "credit",
            "yape",
            "plin",
            "transfer",
            "mixed",
            "other",
        ]
        ordered = [key for key in order if key in keys]
        for key in keys:
            if key not in ordered:
                ordered.append(key)
        return ordered

    def _payment_summary_from_payments(self, payments: list[Any]) -> str:
        """Genera un resumen textual de los pagos.
        
        Args:
            payments: Lista de objetos de pago con method_type y amount
            
        Returns:
            Texto con formato "Efectivo: S/50.00, Yape: S/30.00"
        """
        if not payments:
            return "-"
        totals: dict[str, float] = {}
        for payment in payments:
            key = self._payment_method_key(getattr(payment, "method_type", None))
            if not key:
                continue
            amount = float(getattr(payment, "amount", 0) or 0)
            totals[key] = totals.get(key, 0.0) + amount
        if not totals:
            return "-"
        parts = []
        for key in self._sorted_payment_keys(list(totals.keys())):
            label = self._payment_method_label(key)
            parts.append(f"{label}: {self._format_currency(totals[key])}")
        return ", ".join(parts)

    def _payment_method_display(self, payments: list[Any]) -> str:
        """Genera etiqueta de display para métodos de pago.
        
        Args:
            payments: Lista de objetos de pago
            
        Returns:
            Etiqueta como "Efectivo" o "Pago Mixto (Efe/Yap)"
        """
        if not payments:
            return "-"
        keys: list[str] = []
        for payment in payments:
            key = self._payment_method_key(getattr(payment, "method_type", None))
            if key and key not in keys:
                keys.append(key)
        if not keys:
            return "-"
        if len(keys) == 1:
            return self._payment_method_label(keys[0])
        abbrevs = [
            self._payment_method_abbrev(key)
            for key in self._sorted_payment_keys(keys)
        ]
        return f"{self._payment_method_label('mixed')} ({'/'.join(abbrevs)})"

    def _payment_breakdown_from_payments(self, payments: list[Any]) -> list[dict[str, float]]:
        """Genera desglose de pagos por método.
        
        Args:
            payments: Lista de objetos de pago
            
        Returns:
            Lista de dicts con 'label' y 'amount' por cada método
        """
        if not payments:
            return []
        totals: dict[str, float] = {}
        for payment in payments:
            key = self._payment_method_key(getattr(payment, "method_type", None))
            if not key:
                continue
            amount = float(getattr(payment, "amount", 0) or 0)
            totals[key] = totals.get(key, 0.0) + amount
        breakdown = []
        for key in self._sorted_payment_keys(list(totals.keys())):
            label = self._payment_method_label(key)
            breakdown.append({"label": label, "amount": self._round_currency(totals[key])})
        return breakdown

    def _payment_kind_from_payments(self, payments: list[Any]) -> str:
        """Determina el tipo de pago (simple o mixto).
        
        Args:
            payments: Lista de objetos de pago
            
        Returns:
            Clave del método único o 'mixed' si hay varios
        """
        keys = {
            self._payment_method_key(getattr(payment, "method_type", None))
            for payment in payments
        }
        keys.discard("")
        if len(keys) > 1:
            return "mixed"
        if len(keys) == 1:
            return next(iter(keys))
        return ""
