"""
Componentes reutilizables para la aplicacion Sistema de Ventas.

Las paginas importan componentes UI directamente desde app.components.ui.
Este modulo re-exporta solo los componentes de nivel superior del paquete.
"""
from app.components.sidebar import sidebar
from app.components.notification import NotificationHolder

__all__ = [
    "sidebar",
    "NotificationHolder",
]
