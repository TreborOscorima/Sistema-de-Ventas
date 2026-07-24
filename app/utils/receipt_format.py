"""Estilos de impresión de comprobantes según el papel (térmico o A4).

Centraliza el CSS (`@page` + tipografía) para que todos los comprobantes
—ticket POS, reimpresiones, arqueo de caja, reportes, constancias de reserva—
salgan consistentes y **auto-adaptados** al tamaño elegido, sin cortarse:

- Térmico (cualquier ancho en mm — 58, 80 o personalizado): `@page size: {mm}mm auto`
  (alto según contenido) + texto que envuelve (`pre-wrap` / `break-word`). No corta
  ni a lo largo (da igual el diámetro/largo del rollo) ni a lo ancho.
- A4: `@page size: A4` con márgenes; el ticket se centra en una columna legible
  (auto-adaptado). El layout tipo factura queda para una etapa posterior.
"""

MIN_THERMAL_MM = 40
MAX_THERMAL_MM = 120


def normalize_paper(paper: str | None) -> str:
    """Normaliza el papel: 'a4', o el ancho térmico en mm como string ('58', '80', '76'...).

    El diámetro del rollo no importa para imprimir (solo el ancho), por eso se
    conserva únicamente el ancho en mm, acotado a un rango razonable.
    """
    p = (paper or "").strip().lower()
    if p in {"a4", "a-4", "hoja", "carta", "letter"}:
        return "a4"
    digits = "".join(ch for ch in p if ch.isdigit())
    if digits:
        mm = int(digits)
        mm = max(MIN_THERMAL_MM, min(mm, MAX_THERMAL_MM))
        return str(mm)
    return "80"


def is_a4(paper: str | None) -> bool:
    return normalize_paper(paper) == "a4"


def paper_mm(paper: str | None) -> int:
    """Ancho térmico en mm (80 si es A4 o inválido — solo para compatibilidad)."""
    fmt = normalize_paper(paper)
    return 80 if fmt == "a4" else int(fmt)


def receipt_style(paper: str | None) -> str:
    """Devuelve el contenido de `<style>` (sin las etiquetas) para el papel dado."""
    fmt = normalize_paper(paper)
    if fmt == "a4":
        return (
            "@page { size: A4; margin: 16mm; }"
            "body { margin: 0; }"
            "pre { font-family: 'Courier New', monospace; font-size: 13px; "
            "line-height: 1.4; margin: 0 auto; max-width: 105mm; "
            "white-space: pre-wrap; word-break: break-word; }"
            "img { display: block; margin: 0 auto; }"
        )
    mm = int(fmt)
    return (
        f"@page {{ size: {mm}mm auto; margin: 0; }}"
        "body { margin: 0; padding: 2mm; }"
        "pre { font-family: monospace; font-size: 12px; margin: 0; "
        "white-space: pre-wrap; word-break: break-word; }"
    )
