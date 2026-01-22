"""
Utilidades de validacion para inputs.
"""
import re
from app.constants import (
    PASSWORD_MIN_LENGTH,
    PASSWORD_REQUIRE_UPPERCASE,
    PASSWORD_REQUIRE_DIGIT,
    PASSWORD_REQUIRE_SPECIAL,
)

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


def validate_password_strength(
    password: str,
    min_length: int = 6,
    require_uppercase: bool = False,
    require_digit: bool = False,
    require_special: bool = False,
) -> tuple[bool, str]:
    """
    Valida la fortaleza de una contraseña.
    
    Args:
        password: Contraseña a validar
        min_length: Longitud mínima requerida
        require_uppercase: Si requiere al menos una mayúscula
        require_digit: Si requiere al menos un dígito
        require_special: Si requiere al menos un carácter especial
    
    Returns:
        Tupla (es_valida, mensaje_error)
    """
    if not password:
        return False, "La contraseña no puede estar vacía."
    
    if len(password) < min_length:
        return False, f"La contraseña debe tener al menos {min_length} caracteres."
    
    if require_uppercase and not re.search(r"[A-Z]", password):
        return False, "La contraseña debe contener al menos una mayúscula."
    
    if require_digit and not re.search(r"\d", password):
        return False, "La contraseña debe contener al menos un número."
    
    if require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "La contraseña debe contener al menos un carácter especial."
    
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    """
    Valida una contraseña usando la configuración del sistema.
    
    Esta función usa las constantes definidas en app.constants:
    - PASSWORD_MIN_LENGTH
    - PASSWORD_REQUIRE_UPPERCASE (controlado por env var)
    - PASSWORD_REQUIRE_DIGIT (controlado por env var)
    - PASSWORD_REQUIRE_SPECIAL (controlado por env var)
    
    Para activar validación robusta en producción, configurar en .env:
        PASSWORD_REQUIRE_UPPERCASE=true
        PASSWORD_REQUIRE_DIGIT=true
        PASSWORD_REQUIRE_SPECIAL=true
    
    Args:
        password: Contraseña a validar
    
    Returns:
        Tupla (es_valida, mensaje_error)
    
    Ejemplo:
        is_valid, error = validate_password("MiClave123!")
        if not is_valid:
            return rx.toast(error)
    """
    return validate_password_strength(
        password,
        min_length=PASSWORD_MIN_LENGTH,
        require_uppercase=PASSWORD_REQUIRE_UPPERCASE,
        require_digit=PASSWORD_REQUIRE_DIGIT,
        require_special=PASSWORD_REQUIRE_SPECIAL,
    )
