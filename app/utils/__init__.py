"""
Modulos de utilidades para Sistema de Ventas.

Este paquete contiene funciones puras extraidas de State
para mejorar la reutilizacion de codigo y reducir duplicacion.
"""
from app.utils.formatting import (
    format_currency,
    round_currency,
    parse_float_safe,
    normalize_quantity_value,
)
from app.utils.dates import (
    get_current_timestamp,
    parse_date,
    format_datetime_display,
    get_today_str,
    get_current_month_str,
    get_current_week_str,
)
from app.utils.exports import (
    create_excel_workbook,
    style_header_row,
    add_data_rows,
)
from app.utils.validators import (
    validate_positive_number,
    validate_non_negative,
    validate_email,
    validate_required,
    validate_password_strength,
    validate_password,
)
from app.utils.performance import (
    log_slow_query,
    query_timer,
    timed_operation,
    QueryStats,
)

__all__ = [
    # formateo
    "format_currency",
    "round_currency",
    "parse_float_safe",
    "normalize_quantity_value",
    # fechas
    "get_current_timestamp",
    "parse_date",
    "format_datetime_display",
    "get_today_str",
    "get_current_month_str",
    "get_current_week_str",
    # exportaciones
    "create_excel_workbook",
    "style_header_row",
    "add_data_rows",
    # validadores
    "validate_positive_number",
    "validate_non_negative",
    "validate_email",
    "validate_required",
    "validate_password_strength",
    "validate_password",
    # performance
    "log_slow_query",
    "query_timer",
    "timed_operation",
    "QueryStats",
]
