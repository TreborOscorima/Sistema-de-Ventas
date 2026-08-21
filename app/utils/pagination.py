"""Utilidades de paginación compartidas por los estados.

`build_page_window` genera la lista de números de página para la barra numérica
clickeable de `app.components.ui.pagination_controls` (modo numérico). Se centraliza
acá para no duplicar el algoritmo en cada estado que la usa.
"""
from __future__ import annotations


def build_page_window(current: int, total: int) -> list[int]:
    """Devuelve los nº de página a mostrar en la barra numérica.

    Siempre incluye la primera (1) y la última; muestra los vecinos de la página
    actual y usa ``-1`` como marcador de elipsis (…) para los tramos omitidos.

    Ejemplos:
        total=4,  actual=2  -> [1, 2, 3, 4]
        total=37, actual=1  -> [1, 2, -1, 37]
        total=37, actual=20 -> [1, -1, 19, 20, 21, -1, 37]
    """
    if total <= 1:
        return [1]
    cur = current
    if cur < 1:
        cur = 1
    elif cur > total:
        cur = total
    if total <= 7:
        return list(range(1, total + 1))
    left = max(2, cur - 1)
    right = min(total - 1, cur + 1)
    window: list[int] = [1]
    if left > 2:
        window.append(-1)
    window.extend(range(left, right + 1))
    if right < total - 1:
        window.append(-1)
    window.append(total)
    return window
