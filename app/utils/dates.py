"""
Utilidades de fecha y hora.

Funciones puras de fecha/hora extraidas para reutilizacion.
"""
import datetime
import logging


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


