"""State, constants and static data for the marketing landing page."""

import os
from urllib.parse import quote

import reflex as rx

from app.constants import WHATSAPP_NUMBER

# ── Environment ──────────────────────────────────────────────
GA4_MEASUREMENT_ID = (os.getenv("GA4_MEASUREMENT_ID") or "").strip()
META_PIXEL_ID = (os.getenv("META_PIXEL_ID") or "").strip()
PUBLIC_SITE_URL = (os.getenv("PUBLIC_SITE_URL") or "").strip().rstrip("/")
PUBLIC_APP_URL = (os.getenv("PUBLIC_APP_URL") or "").strip().rstrip("/")
PUBLIC_FOOD_URL = (os.getenv("PUBLIC_FOOD_URL") or "").strip().rstrip("/")


# ── State ────────────────────────────────────────────────────
class MarketingState(rx.State):
    """Estado reactivo para la landing page."""

    show_announcement: bool = True
    active_tab: str = "nube"

    def dismiss_announcement(self):
        self.show_announcement = False

    def set_tab_nube(self):
        self.active_tab = "nube"

    def set_tab_local(self):
        self.active_tab = "local"


# ── Helpers ──────────────────────────────────────────────────
def _site_href(path: str = "/") -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    if PUBLIC_SITE_URL:
        return f"{PUBLIC_SITE_URL}{normalized}"
    return normalized


def _app_href(path: str = "/") -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    if PUBLIC_APP_URL:
        return f"{PUBLIC_APP_URL}{normalized}"
    return normalized


def _food_href(path: str = "/") -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    if PUBLIC_FOOD_URL:
        return f"{PUBLIC_FOOD_URL}{normalized}"
    return f"#tuwaykifood"


def _wa_link(message: str) -> str:
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(message)}"


# ── Static Data ──────────────────────────────────────────────
TRUST_BADGES = [
    ("zap", "Sin Excel ni papel"),
    ("building-2", "Multi-sucursal real"),
    ("wallet", "Caja y stock en tiempo real"),
    ("monitor", "Accede desde cualquier dispositivo"),
]

INDUSTRIES = [
    ("store",          "Tiendas y retail",      "POS + stock + caja"),
    ("dumbbell",       "Canchas deportivas",     "Reservas + cobros"),
    ("wrench",         "Talleres y servicios",   "Órdenes + historial"),
    ("truck",          "Distribuidoras",         "Inventario intensivo"),
    ("utensils",       "Gastronomía",            "Ventas + caja rápida"),
    ("scissors",       "Salones y estética",     "Turnos + facturación"),
    ("building-2",     "Multi-sucursal",         "Control centralizado"),
    ("package",        "Bodegas",                "Stock + Kardex"),
]

MODULES = [
    {
        "icon": "shopping-cart",
        "title": "Punto de venta",
        "description": "Cobra en segundos con cualquier método de pago. Cada venta queda registrada con usuario, hora y sucursal — sin carga manual.",
        "bullets": [
            "Búsqueda por nombre, código o código de barras",
            "Efectivo, tarjeta y transferencia en un mismo ticket",
            "Stock descontado automáticamente por sucursal",
            "Historial completo por cajero, turno y fecha",
        ],
    },
    {
        "icon": "package",
        "title": "Inventario inteligente",
        "description": "Control de stock en tiempo real por sucursal y bodega, con Kardex auditable y alertas antes de quedarte sin mercadería.",
        "bullets": [
            "Movimientos auditables con usuario y motivo",
            "Alertas de stock mínimo configurables por producto",
            "Kardex completo con cada entrada y salida",
            "Valorización por costo y precio de venta",
        ],
    },
    {
        "icon": "calendar-plus",
        "title": "Reservas y servicios",
        "description": "Agenda operativa para canchas, espacios y servicios. Cobra adelantos y cobros finales desde el mismo sistema.",
        "bullets": [
            "Reservas por horario, estado y responsable",
            "Cobro parcial y cobro final unificados",
            "Vista de disponibilidad por espacio y día",
            "Historial de clientes recurrentes",
        ],
    },
    {
        "icon": "wallet",
        "title": "Gestión de caja",
        "description": "Apertura y cierre de caja por turno con evidencia total. El arqueo muestra diferencias al instante — sin sorpresas al final del día.",
        "bullets": [
            "Apertura y cierre por turno y responsable",
            "Ingresos y egresos con motivo registrado",
            "Arqueo visual con diferencias inmediatas",
            "Historial por día, usuario y sucursal",
        ],
    },
    {
        "icon": "users",
        "title": "Usuarios y permisos",
        "description": "Multi-tenant real: cada empresa y sucursal opera con aislamiento total. Asigna roles exactos a cada integrante del equipo.",
        "bullets": [
            "Roles por función: cajero, supervisor, admin",
            "Acceso granular por módulo y sucursal",
            "Trazabilidad de quién hizo qué y cuándo",
            "Escala sin comprometer la seguridad",
        ],
    },
    {
        "icon": "pie-chart",
        "title": "Reportes y análisis",
        "description": "Indicadores en tiempo real para tomar decisiones con datos. Filtra por período, producto, categoría o sucursal y exporta a Excel.",
        "bullets": [
            "Ventas y rentabilidad por período y categoría",
            "Top productos y rotación de inventario",
            "Comparativo entre sucursales",
            "Exportación a Excel con un clic",
        ],
    },
]

STEPS = [
    ("01", "Activa tu cuenta", "Empresa, sucursal inicial y credenciales de equipo."),
    ("02", "Configura la operación", "Moneda, catálogo, permisos y reglas de trabajo."),
    ("03", "Empieza a vender", "Ventas y cobros con trazabilidad automática."),
    ("04", "Controla en tiempo real", "Caja, stock y reservas en una sola vista."),
    ("05", "Escala con datos", "Reportes para optimizar y crecer con orden."),
]

FAQ_ITEMS = [
    ("¿Cuánto tarda implementarlo?", "Puedes comenzar el mismo día. El onboarding toma minutos y escalas por módulos según tu ritmo."),
    ("¿Necesito tarjeta para el trial?", "No. Prueba gratis de 15 días sin tarjeta. Valida el flujo completo antes de decidir."),
    ("¿Sirve para varias empresas o sucursales?", "Sí. Arquitectura multi-tenant real: cada empresa y sucursal opera con aislamiento total de datos."),
    ("¿Puedo vender productos y servicios?", "Sí. Punto de venta, reservas, adelantos, cobro final y caja en un solo sistema integrado."),
    ("¿Qué incluye el soporte?", "Acompañamiento funcional, resolución de dudas y guía para una adopción ordenada."),
    ("¿Qué pasa cuando termina el trial?", "Eliges Standard, Professional o Enterprise. Tu configuración y datos se mantienen intactos."),
]

STRENGTH_METRICS = [
    {"icon": "shield-check", "title": "Multi-tenant real", "detail": "Aislamiento total de datos entre empresas y sucursales. Cada negocio opera con privacidad absoluta."},
    {"icon": "database", "title": "Trazabilidad completa", "detail": "Cada movimiento de caja, venta y ajuste queda registrado con usuario, timestamp y sucursal."},
    {"icon": "git-branch", "title": "Arquitectura escalable", "detail": "Agrega sucursales, usuarios y módulos sin migrar datos ni detener operaciones."},
    {"icon": "lock", "title": "Permisos granulares", "detail": "Control de acceso por rol, módulo y sucursal. Define exactamente quién ve y hace qué."},
]

USE_CASES = [
    {
        "icon": "store",
        "title": "Tiendas y Bodegas",
        "description": "Venta al detalle con múltiples cajas, control de stock en tiempo real y precios por lista personalizada.",
        "features": ["POS con código de barras", "Stock por sucursal y bodega", "Listas de precios y descuentos"],
        "accent": "indigo",
    },
    {
        "icon": "calendar-check",
        "title": "Canchas y Deportes",
        "description": "Agenda de canchas y espacios por horario con cobro de adelantos y gestión de reservas sin papeles.",
        "features": ["Reservas por horario y estado", "Cobro parcial integrado", "Control de disponibilidad"],
        "accent": "emerald",
    },
    {
        "icon": "wrench",
        "title": "Servicios y Talleres",
        "description": "Órdenes de trabajo, cobro por servicio finalizado y seguimiento de clientes recurrentes con historial.",
        "features": ["Órdenes de servicio", "Cobro parcial y final", "Historial de clientes"],
        "accent": "amber",
    },
    {
        "icon": "building-2",
        "title": "Multi-sucursal y Cadenas",
        "description": "Operación centralizada con aislamiento completo por empresa y reportes consolidados entre sedes.",
        "features": ["Múltiples empresas y sedes", "Permisos granulares por sede", "Reportes cruzados"],
        "accent": "violet",
    },
]

EXTRA_CAPABILITIES = [
    ("shopping-bag", "Compras y Proveedores", "Registro de compras con actualización automática de stock."),
    ("file-text", "Presupuestos", "Genera cotizaciones y conviértelas en ventas con un clic."),
    ("receipt", "Documentos Fiscales", "Facturas, boletas y comprobantes listos para imprimir."),
    ("tag", "Etiquetas de Productos", "Imprime etiquetas con código de barras desde el inventario."),
    ("percent", "Promociones y Descuentos", "Reglas de precio automáticas por cliente, cantidad o fecha."),
    ("users", "Gestión de Clientes", "Fichas de clientes con historial, cuentas corrientes y saldo."),
    ("bar-chart-2", "Dashboard en Tiempo Real", "Métricas del día: ventas, caja, stock crítico y más."),
    ("mail", "Campañas de Marketing", "Segmenta clientes y envía comunicaciones comerciales."),
]

SCREENSHOT_TABS = [
    {
        "id": "dashboard",
        "label": "Dashboard",
        "icon": "layout-dashboard",
        "src": "/dashboard-screenshot.webp",
        "alt": "Dashboard principal de TUWAYKIAPP",
        "headline": "El estado de tu negocio en una sola pantalla",
        "bullets": [
            "Ventas del día, semana y mes en tiempo real",
            "Alertas de stock crítico antes de que se agote",
            "Movimientos de caja por turno y responsable",
            "Top productos y categorías con mayor rotación",
        ],
    },
    {
        "id": "venta",
        "label": "Punto de Venta",
        "icon": "shopping-cart",
        "src": "/venta-screenshot.webp",
        "alt": "Punto de venta de TUWAYKIAPP",
        "headline": "Cobra en segundos, registra todo automáticamente",
        "bullets": [
            "Busca por nombre, código interno o código de barras",
            "Efectivo, tarjeta y transferencia en el mismo ticket",
            "Stock descontado al instante por sucursal",
            "Historial de ventas por cajero, turno y fecha",
        ],
    },
    {
        "id": "inventario",
        "label": "Inventario",
        "icon": "package",
        "src": "/inventario-screenshot.webp",
        "alt": "Gestión de inventario de TUWAYKIAPP",
        "headline": "Stock auditado, Kardex completo, cero sorpresas",
        "bullets": [
            "Cada movimiento registrado con usuario y motivo",
            "Alertas configurables de stock mínimo por producto",
            "Valorización por costo y precio de venta",
            "Categorías, unidades y múltiples bodegas",
        ],
    },
    {
        "id": "caja",
        "label": "Caja",
        "icon": "wallet",
        "src": "/caja-screenshot.webp",
        "alt": "Gestión de caja de TUWAYKIAPP",
        "headline": "Cierra caja con evidencia. Sin diferencias ocultas.",
        "bullets": [
            "Apertura y cierre de turno con monto inicial registrado",
            "Ingresos y egresos con motivo y responsable",
            "Arqueo visual: diferencias calculadas al instante",
            "Historial completo por día, turno y sucursal",
        ],
    },
    {
        "id": "reportes",
        "label": "Reportes",
        "icon": "bar-chart-3",
        "src": "/reportes-screenshot.webp",
        "alt": "Reportes y analítica de TUWAYKIAPP",
        "headline": "Datos reales para decisiones que generan resultado",
        "bullets": [
            "Rentabilidad por período, categoría y producto",
            "Comparativo entre sucursales y rangos de fechas",
            "Rotación de inventario y productos sin movimiento",
            "Exportación a Excel con un clic",
        ],
    },
]

# ── Shared Links ─────────────────────────────────────────────
_demo_link = _wa_link("Hola, quiero una demo en vivo de TUWAYKIAPP.")
_local_link = _wa_link("Hola, me interesa TUWAYKIAPP en modalidad Local (pago anual). Quiero coordinar precio y detalles.")
_standard_link = _wa_link("Hola, quiero el Plan Standard (USD 35/mes) de TUWAYKIAPP.")
_professional_link = _wa_link("Hola, quiero el Plan Professional (USD 55/mes) de TUWAYKIAPP.")
_enterprise_link = _wa_link("Hola, quiero el Plan Enterprise (USD 175/mes) de TUWAYKIAPP.")
_food_demo_link = _wa_link("Hola, me interesa conocer TUWAYKIFOOD para mi restaurante. Quiero coordinar una demo.")

# ── TUWAYKIFOOD Static Data ───────────────────────────────────
FOOD_FEATURES = [
    ("utensils", "Carta Digital", "Administra tu menú con categorías, platos y precios. Activá o desactivá platos en tiempo real."),
    ("qr-code", "QR para clientes", "Tus clientes ven la carta actualizada desde su celular escaneando el QR de la mesa."),
    ("layout-grid", "Gestión de Mesas", "Mapa visual de tu salón. Cada mesa muestra su estado: libre, ocupada o cuenta pedida."),
    ("clipboard-list", "Pedidos por Tablet", "El mozo toma el pedido en tablet mesa por mesa. El pedido llega directo a cocina."),
    ("printer", "Comanda automática", "Al confirmar el pedido se imprime la comanda en cocina automáticamente. Sin confusiones."),
    ("wallet", "Caja Integrada", "Los pedidos cerrados se registran en caja con diferenciador. Arqueo al cierre del turno."),
]
