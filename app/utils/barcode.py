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


def normalize_barcode(barcode: str) -> str:
    """
    Normaliza un codigo de barras para busqueda y comparacion.
    Convierte a mayusculas y limpia caracteres especiales.

    Parametros:
        barcode: Codigo de barras a normalizar

    Retorna:
        Codigo de barras normalizado
    """
    clean_code = clean_barcode(barcode)
    return clean_code.upper()


def format_barcode_for_display(barcode: str, group_size: int = 4) -> str:
    """
    Formatea un codigo de barras para visualizacion, agrupando digitos.
    Ej: "1234567890" -> "1234-5678-90"

    Parametros:
        barcode: Codigo de barras a formatear
        group_size: Tamano de cada grupo (default: 4)

    Retorna:
        Codigo de barras formateado con guiones
    """
    if not barcode:
        return ""

    clean_code = clean_barcode(barcode)

    # Agrupar en bloques del tamano especificado
    groups = [clean_code[i:i+group_size] for i in range(0, len(clean_code), group_size)]

    return "-".join(groups)
