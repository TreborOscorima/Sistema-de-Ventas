"""
Utilidades para manejo de códigos de barras
"""
import re


def clean_barcode(barcode: str) -> str:
    """
    Limpia un código de barras eliminando espacios, guiones, puntos y otros caracteres especiales.
    
    Args:
        barcode: El código de barras a limpiar
        
    Returns:
        El código de barras limpio, solo con caracteres alfanuméricos
    """
    if not barcode:
        return ""
    
    # Eliminar espacios en blanco al inicio y final
    code = barcode.strip()
    
    # Eliminar caracteres especiales comunes (espacios, guiones, puntos, comas)
    code = code.replace(" ", "").replace("-", "").replace(".", "").replace(",", "")
    
    # Opcional: Eliminar cualquier otro caracter que no sea alfanumérico
    # code = re.sub(r'[^a-zA-Z0-9]', '', code)
    
    return code


def validate_barcode(barcode: str, min_length: int = 3, max_length: int = 50) -> bool:
    """
    Valida que un código de barras tenga un formato válido.
    
    Args:
        barcode: El código de barras a validar
        min_length: Longitud mínima permitida (default: 3)
        max_length: Longitud máxima permitida (default: 50)
        
    Returns:
        True si el código es válido, False en caso contrario
    """
    if not barcode:
        return False
    
    clean_code = clean_barcode(barcode)
    
    # Verificar longitud
    if len(clean_code) < min_length or len(clean_code) > max_length:
        return False
    
    # El código debe contener al menos un carácter alfanumérico
    if not re.search(r'[a-zA-Z0-9]', clean_code):
        return False
    
    return True


def normalize_barcode(barcode: str) -> str:
    """
    Normaliza un código de barras para búsqueda y comparación.
    Convierte a mayúsculas y limpia caracteres especiales.
    
    Args:
        barcode: El código de barras a normalizar
        
    Returns:
        El código de barras normalizado
    """
    clean_code = clean_barcode(barcode)
    return clean_code.upper()


def format_barcode_for_display(barcode: str, group_size: int = 4) -> str:
    """
    Formatea un código de barras para visualización, agrupando dígitos.
    Ej: "1234567890" -> "1234-5678-90"
    
    Args:
        barcode: El código de barras a formatear
        group_size: Tamaño de cada grupo (default: 4)
        
    Returns:
        El código de barras formateado con guiones
    """
    if not barcode:
        return ""
    
    clean_code = clean_barcode(barcode)
    
    # Agrupar en bloques del tamaño especificado
    groups = [clean_code[i:i+group_size] for i in range(0, len(clean_code), group_size)]
    
    return "-".join(groups)
