"""
Estados de la aplicación.

Este módulo exporta los estados y utilidades principales.
"""
from .mixin_state import require_permission, require_cashbox_open

__all__ = [
    "require_permission",
    "require_cashbox_open",
]
