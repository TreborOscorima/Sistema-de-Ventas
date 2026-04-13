"""
Constantes centralizadas del sistema.

Este módulo contiene todas las constantes mágicas del sistema
para facilitar su mantenimiento y configuración.
"""
from __future__ import annotations

# =============================================================================
# CONTACTO / WHATSAPP
# =============================================================================

# Número de WhatsApp de soporte/ventas (sin "+", solo dígitos con código de país)
WHATSAPP_NUMBER: str = "5491168376517"

# URL directa de WhatsApp para ventas (formato wa.me/message/...)
WHATSAPP_SALES_URL: str = "https://wa.me/message/ULLEZ4HUFB5HA1"


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
import os

# Longitud mínima de contraseña (8 es el mínimo aceptable para sistemas financieros)
PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))

# Tiempo de bloqueo por intentos fallidos (minutos)
LOGIN_LOCKOUT_MINUTES: int = 15

# Máximo de intentos de login antes de bloqueo
MAX_LOGIN_ATTEMPTS: int = 5

# Configuración de fortaleza de contraseña.
# Activados por defecto — se pueden desactivar con env var solo en desarrollo.
def _env_bool(var_name: str, default: bool = True) -> bool:
    val = os.getenv(var_name, "").strip().lower()
    if not val:
        return default
    return val in {"1", "true", "yes", "on"}


PASSWORD_REQUIRE_UPPERCASE: bool = _env_bool("PASSWORD_REQUIRE_UPPERCASE", True)
PASSWORD_REQUIRE_DIGIT: bool = _env_bool("PASSWORD_REQUIRE_DIGIT", True)
PASSWORD_REQUIRE_SPECIAL: bool = _env_bool("PASSWORD_REQUIRE_SPECIAL", False)


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
    "Devolucion",
}


# =============================================================================
# MÉTODOS DE REPORTE
# =============================================================================

# Límite máximo de filas para exportaciones (previene OOM en reportes masivos).
# Para cargas enterprise, usar workers dedicados de reportes y colas asíncronas.
MAX_REPORT_ROWS: int = int(os.getenv("MAX_REPORT_ROWS", "25000"))

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


# =============================================================================
# SIDEBAR NAVIGATION — Subsecciones por módulo
# (Datos de dominio centralizados aquí; la UI los importa desde constants)
# =============================================================================

CONFIG_SUBSECTIONS: list[dict] = [
    {"key": "empresa", "label": "Datos de Empresa", "icon": "building"},
    {"key": "sucursales", "label": "Sucursales", "icon": "map-pin"},
    {"key": "usuarios", "label": "Gestion de Usuarios", "icon": "users"},
    {"key": "monedas", "label": "Selector de Monedas", "icon": "coins"},
    {"key": "unidades", "label": "Unidades de Medida", "icon": "ruler"},
    {"key": "pagos", "label": "Metodos de Pago", "icon": "credit-card"},
    {"key": "facturacion", "label": "Facturacion Electronica", "icon": "file-text"},
    {"key": "suscripcion", "label": "Suscripcion", "icon": "sparkles"},
]

CASH_SUBSECTIONS: list[dict] = [
    {"key": "resumen", "label": "Resumen de Caja", "icon": "layout-dashboard"},
    {"key": "movimientos", "label": "Movimientos de Caja Chica", "icon": "arrow-left-right"},
]

SERVICES_SUBSECTIONS: list[dict] = [
    {"key": "campo", "label": "Alquiler de Campo", "icon": "trophy"},
    {"key": "precios_campo", "label": "Precios de Campo", "icon": "tags"},
]


# =============================================================================
# PRICING PLANS — Datos centralizados para el modal de planes
# =============================================================================

# URLs de WhatsApp pre-formadas por plan (se construyen en runtime con WHATSAPP_NUMBER)
def _make_wa_url(text: str) -> str:
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={text}"


PRICING_PLANS: list[dict] = [
    {
        "title": "PLAN STANDARD",
        "icon": "sparkles",
        "limits": ["Hasta 5 sucursales", "10 usuarios"],
        "modules": [
            "Múltiples usuarios y roles",
            "Ventas rápidas con lector de código o teclado",
            "Productos por unidad, peso y litros",
            "Gestión de stock y reposición",
            "Reportes diarios de ventas e ingresos",
            "Clientes y cuentas corrientes",
        ],
        "action_label": "Elegir Standard",
        "wa_text": "Hola,%20quiero%20el%20Plan%20Standard%20(USD%2045/mes)%20de%20TUWAYKIAPP.",
        "highlight": False,
        "badge_text": None,
    },
    {
        "title": "PLAN PROFESSIONAL",
        "icon": "crown",
        "limits": ["Hasta 10 sucursales", "Usuarios ilimitados"],
        "modules": [
            "Todo lo del Standard",
            "Multi-sucursal con control centralizado",
            "Reportes avanzados y comparativos",
            "Soporte prioritario",
            "Automatizaciones y aprobaciones",
            "Integraciones personalizadas",
        ],
        "action_label": "Elegir Professional",
        "wa_text": "Hola,%20quiero%20el%20Plan%20Professional%20(USD%2075/mes)%20de%20TUWAYKIAPP.",
        "highlight": True,
        "badge_text": "Más popular",
    },
    {
        "title": "PLAN ENTERPRISE",
        "icon": "rocket",
        "limits": ["Sucursales a medida", "Usuarios ilimitados"],
        "modules": [
            "Facturación electrónica",
            "API Access y webhooks",
            "Gerente de cuenta dedicado",
            "SLA y soporte 24/7",
            "Implementación a medida",
            "Onboarding y capacitación",
        ],
        "action_label": "Contactar",
        "wa_text": "Hola,%20quiero%20el%20Plan%20Enterprise%20(USD%20175/mes)%20de%20TUWAYKIAPP.",
        "highlight": False,
        "badge_text": None,
    },
]
