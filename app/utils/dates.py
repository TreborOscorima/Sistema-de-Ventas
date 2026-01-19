"""
Utilidades de fecha y hora.

Funciones puras de fecha/hora extraidas para reutilizacion.
"""
import datetime
import logging


def get_current_timestamp() -> str:
    """
    Obtiene el timestamp actual en formato YYYY-MM-DD HH:MM:SS.
    
    Retorna:
        Timestamp actual como string
    """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_today_str() -> str:
    """
    Obtiene la fecha de hoy en formato YYYY-MM-DD.
    
    Retorna:
        Fecha de hoy como string
    """
    return datetime.date.today().strftime("%Y-%m-%d")


def get_current_month_str() -> str:
    """
    Obtiene el mes actual en formato YYYY-MM.
    
    Retorna:
        Mes actual como string
    """
    return datetime.date.today().strftime("%Y-%m")


def get_current_week_str() -> str:
    """
    Obtiene la semana ISO actual en formato YYYY-WNN.
    
    Retorna:
        Semana actual como string (ej. "2024-W52")
    """
    return datetime.date.today().strftime("%G-W%V")


def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> datetime.datetime | None:
    """
    Parseo seguro de una fecha en string.
    
    Parametros:
        date_str: Fecha en string a parsear
        fmt: Formato (default: "%Y-%m-%d")
        
    Retorna:
        Datetime parseado o None si falla el parseo
    """
    if not date_str:
        return None
    try:
        return datetime.datetime.strptime(date_str, fmt)
    except ValueError as e:
        logging.debug(f"Failed to parse date '{date_str}' with format '{fmt}': {e}")
        return None


def format_datetime_display(dt: datetime.datetime | None) -> str:
    """
    Formatea un datetime para mostrarlo.
    
    Parametros:
        dt: Datetime a formatear
        
    Retorna:
        String formateado o vacio si dt es None
    """
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")


def parse_date_from_timestamp(timestamp: str) -> datetime.date | None:
    """
    Extrae la fecha de un timestamp (separa por espacio).
    
    Parametros:
        timestamp: Timestamp como "2024-01-15 14:30:00"
        
    Retorna:
        Fecha o None si falla el parseo
    """
    if not timestamp:
        return None
    try:
        date_part = timestamp.split(" ")[0]
        return datetime.datetime.strptime(date_part, "%Y-%m-%d").date()
    except (ValueError, IndexError):
        return None
