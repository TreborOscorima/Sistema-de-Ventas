"""
Módulo de internacionalización (i18n) — constantes de mensajes.

Centraliza todos los strings user-facing para:
1. Eliminar duplicación de mensajes repetidos
2. Punto único de mantenimiento para cambios de redacción
3. Futura extensión multi-idioma (dict por locale)

Uso:
    from app.i18n import MSG
    yield rx.toast(MSG.PERM_CASH)
"""

from app.i18n.messages import MSG

__all__ = ["MSG"]
