"""
Utilidades de validacion para inputs.
"""
import re

def validate_positive_number(value: float | str) -> bool:
    """
    Valida si un numero es positivo.
    """
    try:
        return float(value) > 0
    except (ValueError, TypeError):
        return False

def validate_non_negative(value: float | str) -> bool:
    """
    Valida si un numero es no negativo.
    """
    try:
        return float(value) >= 0
    except (ValueError, TypeError):
        return False

def validate_email(email: str) -> bool:
    """
    Valida el formato de email.
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def validate_required(value: str) -> bool:
    """
    Valida si un string no esta vacio.
    """
    return bool(value and value.strip())
