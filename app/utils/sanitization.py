"""
Utilidades de sanitización para prevenir XSS y validar entrada de datos.

Este módulo proporciona funciones para limpiar y validar datos de entrada
antes de almacenarlos en la base de datos o mostrarlos en el frontend.
"""
from __future__ import annotations

import html
import re
from typing import Any


def sanitize_text(value: Any, max_length: int = 500) -> str:
    """
    Sanitiza texto de entrada para prevenir XSS y limitar longitud.

    Parámetros:
        value: Valor a sanitizar (se convierte a string)
        max_length: Longitud máxima permitida

    Retorna:
        String sanitizado y truncado
    """
    if value is None:
        return ""

    # Convertir a string y limpiar espacios
    cleaned = str(value).strip()

    # Eliminado html.escape para evitar doble codificación en BD y reportes.
    # En su lugar, removemos tags HTML para sanitización real (limpieza).
    if "<" in cleaned and ">" in cleaned:
        cleaned = re.sub(r"<[^>]*>", "", cleaned)

    # Limitar longitud
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned


def sanitize_text_preserve_spaces(value: Any, max_length: int = 500) -> str:
    """
    Sanitiza texto sin recortar espacios al final (para inputs en vivo).

    Parámetros:
        value: Valor a sanitizar
        max_length: Longitud máxima permitida
    """
    if value is None:
        return ""
    cleaned = str(value)
    if "<" in cleaned and ">" in cleaned:
        cleaned = re.sub(r"<[^>]*>", "", cleaned)
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def sanitize_notes(value: Any) -> str:
    """
    Sanitiza campos de notas/observaciones.

    Límite de 250 caracteres para notas.

    Parámetros:
        value: Texto de notas a sanitizar

    Retorna:
        String sanitizado
    """
    return sanitize_text(value, max_length=250)


def sanitize_notes_preserve_spaces(value: Any) -> str:
    """Sanitiza notas sin eliminar espacios al final."""
    return sanitize_text_preserve_spaces(value, max_length=250)


def sanitize_name(value: Any) -> str:
    """
    Sanitiza nombres (clientes, usuarios, etc).

    Límite de 100 caracteres.

    Parámetros:
        value: Nombre a sanitizar

    Retorna:
        String sanitizado
    """
    return sanitize_text(value, max_length=100)


def sanitize_phone(value: Any) -> str:
    """
    Sanitiza números de teléfono.

    Solo permite dígitos, espacios, guiones y el símbolo +.

    Parámetros:
        value: Teléfono a sanitizar

    Retorna:
        String sanitizado con solo caracteres válidos
    """
    if value is None:
        return ""

    cleaned = str(value).strip()
    # Solo permitir dígitos, espacios, guiones y +
    cleaned = re.sub(r"[^\d\s\-+]", "", cleaned)

    return cleaned[:20]  # Límite razonable para teléfonos


def sanitize_dni(value: Any) -> str:
    """
    Sanitiza documentos de identidad (DNI/RUC).

    Solo permite caracteres alfanuméricos y guiones.

    Parámetros:
        value: Documento a sanitizar

    Retorna:
        String sanitizado
    """
    if value is None:
        return ""

    cleaned = str(value).strip().upper()
    # Solo permitir alfanuméricos y guiones
    cleaned = re.sub(r"[^A-Z0-9\-]", "", cleaned)

    return cleaned[:20]


def sanitize_barcode(value: Any) -> str:
    """
    Sanitiza códigos de barra.

    Solo permite caracteres alfanuméricos.

    Parámetros:
        value: Código de barra a sanitizar

    Retorna:
        String sanitizado
    """
    if value is None:
        return ""

    cleaned = str(value).strip()
    # Solo alfanuméricos para códigos de barra
    cleaned = re.sub(r"[^A-Za-z0-9]", "", cleaned)

    return cleaned[:50]


def sanitize_reason(value: Any) -> str:
    """
    Sanitiza motivos/razones (eliminación, cancelación, etc).

    Límite de 200 caracteres.

    Parámetros:
        value: Razón a sanitizar

    Retorna:
        String sanitizado
    """
    return sanitize_text(value, max_length=200)


def sanitize_reason_preserve_spaces(value: Any) -> str:
    """Sanitiza razones sin eliminar espacios al final (para inputs en vivo)."""
    return sanitize_text_preserve_spaces(value, max_length=200)


def is_valid_phone(phone: str, country_code: str = "PE") -> bool:
    """
    Valida formato de teléfono según el país.

    Parámetros:
        phone: Número de teléfono a validar
        country_code: Código ISO del país (default: PE)

    Retorna:
        True si es un formato válido para el país
    """
    from app.utils.db_seeds import get_country_config

    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        return False

    config = get_country_config(country_code)
    valid_lengths = config.get("phone_digits", [9, 11])
    return len(digits) in valid_lengths


def is_valid_personal_id(id_value: str, country_code: str = "PE") -> bool:
    """
    Valida formato de documento de identidad personal según el país.

    - Perú: DNI (8 dígitos)
    - Argentina: DNI (7-8 dígitos)
    - Ecuador: Cédula (10 dígitos)
    - Colombia: C.C. (6-10 dígitos)
    - Chile: RUN (8-9 caracteres)
    - México: CURP (18 caracteres)

    Parámetros:
        id_value: Documento a validar
        country_code: Código ISO del país (default: PE)

    Retorna:
        True si es un formato válido para el país
    """
    from app.utils.db_seeds import get_country_config

    cleaned = re.sub(r"[^A-Za-z0-9]", "", id_value or "")
    if not cleaned:
        return False

    config = get_country_config(country_code)
    min_len, max_len = config.get("personal_id_length", (6, 12))
    return min_len <= len(cleaned) <= max_len


# Alias para compatibilidad con código existente
def is_valid_dni(dni: str, country_code: str = "PE") -> bool:
    """
    Alias de is_valid_personal_id para compatibilidad.

    Parámetros:
        dni: Documento a validar
        country_code: Código ISO del país (default: PE)

    Retorna:
        True si es un formato válido
    """
    return is_valid_personal_id(dni, country_code)

