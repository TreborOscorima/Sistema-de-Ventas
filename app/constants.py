"""
Constantes centralizadas del sistema.

Las constantes de plataforma viven en tuwayki_core.constants.
Aquí se re-exportan para compatibilidad y se agregan las específicas de Ventas.
"""
from __future__ import annotations

# ── Re-export de constantes de plataforma ────────────────────────────────────
from tuwayki_core.constants import (  # noqa: F401
    WHATSAPP_NUMBER,
    WHATSAPP_SALES_URL,
    CLIENT_SUGGESTIONS_LIMIT,
    PRODUCT_SUGGESTIONS_LIMIT,
    INVENTORY_RECENT_LIMIT,
    DEFAULT_ITEMS_PER_PAGE,
    CASHBOX_ITEMS_PER_PAGE,
    NOTES_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
    ADDRESS_MAX_LENGTH,
    REASON_MAX_LENGTH,
    DEFAULT_CREDIT_INTERVAL_DAYS,
    DEFAULT_INSTALLMENTS_COUNT,
    MIN_INSTALLMENTS,
    MAX_INSTALLMENTS,
    PASSWORD_MIN_LENGTH,
    LOGIN_LOCKOUT_MINUTES,
    MAX_LOGIN_ATTEMPTS,
    PASSWORD_REQUIRE_UPPERCASE,
    PASSWORD_REQUIRE_DIGIT,
    PASSWORD_REQUIRE_SPECIAL,
    DEFAULT_RECEIPT_WIDTH,
    MIN_RECEIPT_WIDTH,
    MAX_RECEIPT_WIDTH,
    DEFAULT_PAPER_WIDTH_MM,
    TOKEN_EXPIRY_HOURS,
    REFRESH_TOKEN_EXPIRY_DAYS,
    STOCK_DECIMAL_PLACES,
    MONEY_DECIMAL_PLACES,
    CASHBOX_INCOME_ACTIONS,
    CASHBOX_EXPENSE_ACTIONS,
    MAX_REPORT_ROWS,
)


# =============================================================================
# MÉTODOS DE REPORTE — específicos de Ventas
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


# =============================================================================
# SIDEBAR NAVIGATION — Subsecciones por módulo
# =============================================================================

CONFIG_SUBSECTIONS: list[dict] = [
    {"key": "empresa", "label": "Datos de Empresa", "icon": "building"},
    {"key": "sucursales", "label": "Sucursales", "icon": "map-pin"},
    {"key": "usuarios", "label": "Gestion de Usuarios", "icon": "users"},
    {"key": "monedas", "label": "Selector de Monedas", "icon": "coins"},
    {"key": "unidades", "label": "Unidades de Medida", "icon": "ruler"},
    {"key": "pagos", "label": "Metodos de Pago", "icon": "credit-card"},
    {"key": "impuestos", "label": "Impuestos", "icon": "percent"},
    {"key": "facturacion", "label": "Facturacion Electronica", "icon": "receipt"},
    {"key": "suscripcion", "label": "Suscripcion", "icon": "sparkles"},
]

CASH_SUBSECTIONS: list[dict] = [
    {"key": "resumen", "label": "Resumen de Caja", "icon": "pie-chart"},
    {"key": "movimientos", "label": "Movimientos de Caja Chica", "icon": "arrow-left-right"},
]

SERVICES_SUBSECTIONS: list[dict] = [
    {"key": "campo", "label": "Alquiler de Campo", "icon": "calendar-check"},
    {"key": "precios_campo", "label": "Precios de Campo", "icon": "tags"},
]


# =============================================================================
# PRICING PLANS
# =============================================================================

def _make_wa_url(text: str) -> str:
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={text}"


PRICING_PLANS: list[dict] = [
    {
        "title": "PLAN STANDARD",
        "icon": "sparkles",
        "limits": ["Hasta 2 sucursales", "5 usuarios"],
        "modules": [
            "Múltiples usuarios y roles",
            "Ventas rápidas con lector de código o teclado",
            "Productos por unidad, peso y litros",
            "Gestión de stock y reposición",
            "Caja, compras e ingresos de mercancía",
            "Reportes diarios de ventas e ingresos",
        ],
        "action_label": "Elegir Standard",
        "wa_text": "Hola,%20quiero%20el%20Plan%20Standard%20(USD%2035/mes)%20de%20TUWAYKIAPP.",
        "highlight": False,
        "badge_text": None,
    },
    {
        "title": "PLAN PROFESSIONAL",
        "icon": "crown",
        "limits": ["Hasta 5 sucursales", "10 usuarios"],
        "modules": [
            "Todo lo del Standard",
            "Clientes, cuentas corrientes y crédito/fiado",
            "Presupuestos y cotizaciones",
            "Promociones y listas de precios",
            "Etiquetas y códigos de barras",
            "Servicios y reservas",
        ],
        "action_label": "Elegir Professional",
        "wa_text": "Hola,%20quiero%20el%20Plan%20Professional%20(USD%2055/mes)%20de%20TUWAYKIAPP.",
        "highlight": True,
        "badge_text": "Más popular",
    },
    {
        "title": "PLAN ENTERPRISE",
        "icon": "rocket",
        "limits": ["Sucursales a medida", "Usuarios ilimitados"],
        "modules": [
            "Todo lo del Professional",
            "Facturación electrónica (SUNAT/AFIP)",
            "Documentos fiscales: boletas y facturas",
            "Gerente de cuenta dedicado",
            "SLA y soporte 24/7",
            "Implementación y onboarding a medida",
        ],
        "action_label": "Contactar",
        "wa_text": "Hola,%20quiero%20el%20Plan%20Enterprise%20(USD%20175/mes)%20de%20TUWAYKIAPP.",
        "highlight": False,
        "badge_text": None,
    },
]
