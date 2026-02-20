"""
Utilidades centralizadas para manejo de métodos de pago.

Este módulo elimina duplicación de código relacionado con la normalización
y conversión de métodos de pago entre diferentes formatos.
"""
from __future__ import annotations

from app.enums import PaymentMethodType


def normalize_payment_method_kind(kind: str) -> PaymentMethodType:
    """
    Normaliza un string de método de pago al enum correspondiente.

    Parámetros:
        kind: String que representa el tipo de método de pago

    Retorna:
        PaymentMethodType correspondiente
    """
    normalized = (kind or "").strip().lower()

    mapping = {
        "cash": PaymentMethodType.cash,
        "efectivo": PaymentMethodType.cash,
        "debit": PaymentMethodType.debit,
        "debito": PaymentMethodType.debit,
        "credit": PaymentMethodType.credit,
        "credito": PaymentMethodType.credit,
        "yape": PaymentMethodType.yape,
        "plin": PaymentMethodType.plin,
        "transfer": PaymentMethodType.transfer,
        "transferencia": PaymentMethodType.transfer,
        "mixed": PaymentMethodType.mixed,
        "mixto": PaymentMethodType.mixed,
        "card": PaymentMethodType.credit,
        "tarjeta": PaymentMethodType.credit,
        "wallet": PaymentMethodType.yape,
        "billetera": PaymentMethodType.yape,
    }

    return mapping.get(normalized, PaymentMethodType.other)


def card_method_type(card_type: str) -> PaymentMethodType:
    """
    Determina el tipo de método de pago para tarjetas.

    Parámetros:
        card_type: Tipo de tarjeta ("debito", "credito", etc.)

    Retorna:
        PaymentMethodType.debit o PaymentMethodType.credit
    """
    value = (card_type or "").strip().lower()

    if "deb" in value or "debito" in value or "débito" in value:
        return PaymentMethodType.debit

    return PaymentMethodType.credit


def wallet_method_type(provider: str) -> PaymentMethodType:
    """
    Determina el tipo de método de pago para billeteras digitales.

    Parámetros:
        provider: Nombre del proveedor ("Yape", "Plin", etc.)

    Retorna:
        PaymentMethodType correspondiente
    """
    value = (provider or "").strip().lower()

    if "plin" in value:
        return PaymentMethodType.plin

    return PaymentMethodType.yape


def payment_method_code(method_type: PaymentMethodType) -> str | None:
    """
    Obtiene el código normalizado para un tipo de método de pago.

    Parámetros:
        method_type: Enum del tipo de método

    Retorna:
        Código string o None si no hay mapeo
    """
    mapping = {
        PaymentMethodType.cash: "cash",
        PaymentMethodType.yape: "yape",
        PaymentMethodType.plin: "plin",
        PaymentMethodType.transfer: "transfer",
        PaymentMethodType.debit: "debit_card",
        PaymentMethodType.credit: "credit_card",
    }

    return mapping.get(method_type)


def payment_method_label(kind: str) -> str:
    """
    Obtiene la etiqueta legible para un tipo de método de pago.

    Parámetros:
        kind: Código del tipo de método

    Retorna:
        Etiqueta en español
    """
    normalized = (kind or "").strip().lower()

    labels = {
        "cash": "Efectivo",
        "debit": "Tarjeta de Débito",
        "credit": "Tarjeta de Crédito",
        "yape": "Billetera Digital (Yape)",
        "plin": "Billetera Digital (Plin)",
        "transfer": "Transferencia Bancaria",
        "mixed": "Pago Mixto",
        "card": "Tarjeta de Crédito",
        "wallet": "Billetera Digital (Yape)",
        "other": "Otros",
    }

    return labels.get(normalized, "Otros")


def normalize_wallet_label(label: str) -> str:
    """
    Normaliza etiquetas de billetera/método de pago para mostrar.

    Parámetros:
        label: Etiqueta original

    Retorna:
        Etiqueta normalizada en español
    """
    value = (label or "").strip()
    if not value:
        return value

    key = value.lower()

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

    if key in mapping:
        return mapping[key]

    if key == "card":
        return mapping["credit"]
    if key == "wallet":
        return mapping["yape"]

    # Detección por contenido
    if "mixto" in key and "(" in value and ")" in value:
        suffix = value[value.find("("):].strip()
        return f"{mapping['mixed']} {suffix}"
    if "mixto" in key:
        return mapping["mixed"]
    if "debito" in key or "débito" in key:
        return mapping["debit"]
    if "credito" in key or "crédito" in key or "tarjeta" in key:
        return mapping["credit"]
    if "yape" in key:
        return mapping["yape"]
    if "plin" in key:
        return mapping["plin"]
    if "billetera" in key or "qr" in key:
        return mapping["yape"]
    if "transfer" in key or "banco" in key:
        return mapping["transfer"]
    if "efectivo" in key:
        return mapping["cash"]

    return value


def payment_category(method: str, kind: str = "") -> str:
    """
    Categoriza un método de pago para reportes.

    Parámetros:
        method: Nombre del método
        kind: Tipo de método

    Retorna:
        Categoría del pago
    """
    normalized_kind = (kind or "").lower()
    label = method.lower() if method else ""

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

    if normalized_kind == "mixed" or "mixto" in label:
        return mapping["mixed"]
    if normalized_kind == "debit" or "debito" in label or "débito" in label:
        return mapping["debit"]
    if normalized_kind == "credit" or "credito" in label or "crédito" in label or "tarjeta" in label:
        return mapping["credit"]
    if normalized_kind == "yape" or "yape" in label:
        return mapping["yape"]
    if normalized_kind == "plin" or "plin" in label:
        return mapping["plin"]
    if normalized_kind == "transfer" or "transfer" in label or "banco" in label:
        return mapping["transfer"]
    if normalized_kind == "cash" or "efectivo" in label:
        return mapping["cash"]

    return mapping["other"]
