"""
Constantes centralizadas del sistema.

Este módulo contiene todas las constantes mágicas del sistema
para facilitar su mantenimiento y configuración.
"""
from __future__ import annotations

# =============================================================================
# LÍMITES DE BÚSQUEDA Y PAGINACIÓN
# =============================================================================

# Número máximo de sugerencias de clientes en búsqueda
CLIENT_SUGGESTIONS_LIMIT: int = 6

# Número máximo de sugerencias de productos en autocompletado
PRODUCT_SUGGESTIONS_LIMIT: int = 5

# Límite de productos recientes a mostrar en inventario
INVENTORY_RECENT_LIMIT: int = 100

# Items por página por defecto
DEFAULT_ITEMS_PER_PAGE: int = 10

# Items por página en historial de caja
CASHBOX_ITEMS_PER_PAGE: int = 5


# =============================================================================
# LÍMITES DE TEXTO
# =============================================================================

# Longitud máxima de notas/observaciones
NOTES_MAX_LENGTH: int = 250

# Longitud máxima de descripciones
DESCRIPTION_MAX_LENGTH: int = 200

# Longitud máxima de nombres
NAME_MAX_LENGTH: int = 100

# Longitud máxima de direcciones
ADDRESS_MAX_LENGTH: int = 300

# Longitud máxima de razones (cancelación, eliminación)
REASON_MAX_LENGTH: int = 200


# =============================================================================
# CONFIGURACIÓN DE CRÉDITOS
# =============================================================================

# Intervalo de días por defecto entre cuotas
DEFAULT_CREDIT_INTERVAL_DAYS: int = 30

# Cantidad de cuotas por defecto
DEFAULT_INSTALLMENTS_COUNT: int = 1

# Mínimo de cuotas permitidas
MIN_INSTALLMENTS: int = 1

# Máximo de cuotas permitidas
MAX_INSTALLMENTS: int = 36


# =============================================================================
# CONFIGURACIÓN DE CONTRASEÑAS
# =============================================================================

# Longitud mínima de contraseña
PASSWORD_MIN_LENGTH: int = 6

# Tiempo de bloqueo por intentos fallidos (minutos)
LOGIN_LOCKOUT_MINUTES: int = 15

# Máximo de intentos de login antes de bloqueo
MAX_LOGIN_ATTEMPTS: int = 5


# =============================================================================
# CONFIGURACIÓN DE RECIBOS
# =============================================================================

# Ancho por defecto de recibo (caracteres)
DEFAULT_RECEIPT_WIDTH: int = 42

# Ancho mínimo de recibo
MIN_RECEIPT_WIDTH: int = 24

# Ancho máximo de recibo
MAX_RECEIPT_WIDTH: int = 64

# Ancho de papel por defecto (mm)
DEFAULT_PAPER_WIDTH_MM: int = 80


# =============================================================================
# TOKENS Y SESIONES
# =============================================================================

# Duración de token JWT (horas)
TOKEN_EXPIRY_HOURS: int = 24


# =============================================================================
# CONFIGURACIÓN DE DECIMALES
# =============================================================================

# Precisión para cantidades en stock
STOCK_DECIMAL_PLACES: int = 4

# Precisión para montos monetarios
MONEY_DECIMAL_PLACES: int = 2


# =============================================================================
# ACCIONES DE CAJA
# =============================================================================

# Acciones que representan ingresos de caja
CASHBOX_INCOME_ACTIONS: set[str] = {
    "Venta",
    "Inicial Credito",
    "Reserva",
    "Adelanto",
    "Cobranza",
    "Cobro de Cuota",
    "Pago Cuota",
    "Cobro Cuota",
    "Ingreso Cuota",
    "Amortizacion",
    "Pago Credito",
}

# Acciones que representan egresos de caja
CASHBOX_EXPENSE_ACTIONS: set[str] = {
    "gasto_caja_chica",
}


# =============================================================================
# MÉTODOS DE REPORTE
# =============================================================================

REPORT_METHOD_KEYS: list[str] = [
    "cash",
    "debit",
    "credit",
    "yape",
    "plin",
    "transfer",
    "mixed",
    "other",
]

REPORT_SOURCE_OPTIONS: list[list[str]] = [
    ["Todos", "Todos"],
    ["Ventas", "Ventas"],
    ["Cobranzas", "Cobranzas"],
]

REPORT_CASHBOX_ACTIONS: set[str] = {
    "Cobranza",
    "Cobro de Cuota",
    "Pago Cuota",
    "Cobro Cuota",
    "Ingreso Cuota",
    "Amortizacion",
    "Pago Credito",
}
