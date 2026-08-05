"""Estado efectivo de una empresa externa (FOOD / LIFE) para el Owner Panel.

Replica la semántica de `owner_service._effective_status` (que aplica sobre las
empresas de SHOP en la misma base) para los productos que el panel consulta por
HTTP y que exponen sus fechas como texto. Así el badge de estado muestra
"Trial Vencido" / "Suspendido" de forma consistente entre los tres productos.

Los productos (FOOD/LIFE) igualmente bloquean el acceso por fecha en su propia
app; esto es solo la representación del estado en el panel.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.utils.timezone import utc_now_naive


def _parse_dt(value) -> datetime | None:
    """Parsea 'YYYY-MM-DD' o ISO-8601 (con o sin 'Z') a datetime naive (UTC).

    Devuelve None si el valor es vacío o no se puede interpretar.
    """
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    # ISO-8601, tolerando el sufijo 'Z' (UTC)
    iso = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        # Solo fecha 'YYYY-MM-DD'
        try:
            dt = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def effective_status(
    *,
    plan: str,
    is_active: bool,
    trial_ends_at,
    plan_expires_at,
    now: datetime | None = None,
) -> str:
    """Estado efectivo del panel: 'active' | 'suspended' | 'trial_expired'.

    - Trial sin fecha o con fecha pasada → 'trial_expired'.
    - Plan de pago con vencimiento pasado (y no ya suspendido) → 'suspended'.
    - En cualquier otro caso → 'active' o 'suspended' según `is_active`.
    """
    now = now or utc_now_naive()
    base = "active" if is_active else "suspended"
    if (plan or "trial") == "trial":
        te = _parse_dt(trial_ends_at)
        if te is None or te < now:
            return "trial_expired"
        return base
    pe = _parse_dt(plan_expires_at)
    if pe is not None and pe < now and base == "active":
        return "suspended"
    return base
