"""
Utilidades para manejo de codigos de barras.
"""
import re


def clean_barcode(barcode: str) -> str:
    """
    Limpia un codigo de barras eliminando espacios, guiones, puntos y otros caracteres especiales.

    Parametros:
        barcode: Codigo de barras a limpiar

    Retorna:
        Codigo de barras limpio, solo con caracteres alfanumericos
    """
    if not barcode:
        return ""

    # Eliminar espacios en blanco al inicio y final
    code = barcode.strip()

    # Eliminar caracteres especiales comunes (espacios, guiones, puntos, comas)
    code = code.replace(" ", "").replace("-", "").replace(".", "").replace(",", "")

    # Opcional: Eliminar cualquier otro caracter que no sea alfanumerico
    # code = re.sub(r'[^a-zA-Z0-9]', '', code)

    return code


def validate_barcode(barcode: str, min_length: int = 3, max_length: int = 50) -> bool:
    """
    Valida que un codigo de barras tenga un formato valido.

    Parametros:
        barcode: Codigo de barras a validar
        min_length: Longitud minima permitida (default: 3)
        max_length: Longitud maxima permitida (default: 50)

    Retorna:
        True si el codigo es valido, False en caso contrario
    """
    if not barcode:
        return False

    clean_code = clean_barcode(barcode)

    # Verificar longitud
    if len(clean_code) < min_length or len(clean_code) > max_length:
        return False

    # El codigo debe contener al menos un caracter alfanumerico
    if not re.search(r'[a-zA-Z0-9]', clean_code):
        return False

    return True
