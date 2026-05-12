"""Servicio de gestión de tasas de impuesto por empresa.

Operaciones CRUD sobre ``CompanyTaxRate`` con las invariantes:
- Siempre existe al máximo una tasa marcada como ``is_default`` por empresa.
- El soft-delete (``is_active=False``) preserva el historial fiscal.
- ``initialize_country_defaults`` siembra las tasas desde ``COUNTRY_TAX_PRESETS``.
"""

from __future__ import annotations

from decimal import Decimal

from sqlmodel import Session, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.taxes import CompanyTaxRate
from app.utils.tax_presets import get_presets_for_country

_FALLBACK_RATE = Decimal("0.18")


# ── Consultas ──────────────────────────────────────────────────────────────────


def get_company_tax_rates(company_id: int, session: Session) -> list[CompanyTaxRate]:
    """Retorna las tasas activas de la empresa, ordenadas por display_order."""
    return session.exec(
        select(CompanyTaxRate)
        .where(CompanyTaxRate.company_id == company_id)
        .where(CompanyTaxRate.is_active == True)  # noqa: E712
        .order_by(CompanyTaxRate.display_order, CompanyTaxRate.id)
    ).all()


async def get_default_rate_async(company_id: int, session: AsyncSession) -> Decimal:
    """Versión async de get_default_rate para usar dentro de emit_fiscal_document."""
    row = (
        await session.exec(
            select(CompanyTaxRate)
            .where(CompanyTaxRate.company_id == company_id)
            .where(CompanyTaxRate.is_default == True)  # noqa: E712
            .where(CompanyTaxRate.is_active == True)  # noqa: E712
        )
    ).first()
    if row:
        return row.rate / Decimal("100")
    first = (
        await session.exec(
            select(CompanyTaxRate)
            .where(CompanyTaxRate.company_id == company_id)
            .where(CompanyTaxRate.is_active == True)  # noqa: E712
            .order_by(CompanyTaxRate.display_order, CompanyTaxRate.id)
        )
    ).first()
    if first:
        return first.rate / Decimal("100")
    return _FALLBACK_RATE


def get_default_rate(company_id: int, session: Session) -> Decimal:
    """Retorna la tasa default de la empresa (fracción, ej. 0.18).

    Usa ``_FALLBACK_RATE`` si la empresa no tiene ninguna tasa configurada.
    """
    row = session.exec(
        select(CompanyTaxRate)
        .where(CompanyTaxRate.company_id == company_id)
        .where(CompanyTaxRate.is_default == True)  # noqa: E712
        .where(CompanyTaxRate.is_active == True)  # noqa: E712
    ).first()
    if row:
        return row.rate / Decimal("100")
    # Fallback: primera tasa activa si no hay default marcada
    first = session.exec(
        select(CompanyTaxRate)
        .where(CompanyTaxRate.company_id == company_id)
        .where(CompanyTaxRate.is_active == True)  # noqa: E712
        .order_by(CompanyTaxRate.display_order, CompanyTaxRate.id)
    ).first()
    if first:
        return first.rate / Decimal("100")
    return _FALLBACK_RATE


# ── Mutaciones ─────────────────────────────────────────────────────────────────


def initialize_country_defaults(
    company_id: int, country_code: str, session: Session
) -> list[CompanyTaxRate]:
    """Reemplaza las tasas de la empresa con los presets del país.

    Hace soft-delete de las tasas anteriores antes de crear las nuevas
    para no romper referencias históricas en FiscalDocument.
    """
    existing = session.exec(
        select(CompanyTaxRate).where(CompanyTaxRate.company_id == company_id)
    ).all()
    for rate in existing:
        rate.is_active = False
        session.add(rate)

    presets = get_presets_for_country(country_code)
    new_rates: list[CompanyTaxRate] = []
    for preset in presets:
        tax_rate = CompanyTaxRate(
            company_id=company_id,
            tax_name=preset["tax_name"],
            label=preset["label"],
            rate=preset["rate"],
            is_default=preset["is_default"],
            is_active=True,
            display_order=preset["display_order"],
        )
        session.add(tax_rate)
        new_rates.append(tax_rate)

    session.flush()
    return new_rates


def upsert_tax_rate(
    *,
    company_id: int,
    tax_name: str,
    label: str,
    rate: Decimal,
    is_default: bool,
    session: Session,
    rate_id: int | None = None,
) -> CompanyTaxRate:
    """Crea o actualiza una tasa de impuesto.

    Si ``is_default=True``, desmarca cualquier otra tasa default de la empresa
    antes de guardar para mantener la invariante de unicidad.
    """
    if is_default:
        _clear_default(company_id, session, exclude_id=rate_id)

    if rate_id is not None:
        obj = session.exec(
            select(CompanyTaxRate)
            .where(CompanyTaxRate.id == rate_id)
            .where(CompanyTaxRate.company_id == company_id)
        ).first()
        if obj is None:
            raise ValueError(f"CompanyTaxRate id={rate_id} no encontrada para company_id={company_id}")
        obj.tax_name = tax_name
        obj.label = label
        obj.rate = rate
        obj.is_default = is_default
        obj.is_active = True
    else:
        # Calcular display_order para el nuevo registro
        existing_count = len(
            session.exec(
                select(CompanyTaxRate).where(CompanyTaxRate.company_id == company_id)
            ).all()
        )
        obj = CompanyTaxRate(
            company_id=company_id,
            tax_name=tax_name,
            label=label,
            rate=rate,
            is_default=is_default,
            is_active=True,
            display_order=existing_count + 1,
        )

    session.add(obj)
    session.flush()
    return obj


def set_default_rate(rate_id: int, company_id: int, session: Session) -> None:
    """Marca una tasa como default, desmarcando las demás."""
    _clear_default(company_id, session, exclude_id=rate_id)
    obj = session.exec(
        select(CompanyTaxRate)
        .where(CompanyTaxRate.id == rate_id)
        .where(CompanyTaxRate.company_id == company_id)
    ).first()
    if obj:
        obj.is_default = True
        session.add(obj)
        session.flush()


def delete_tax_rate(rate_id: int, company_id: int, session: Session) -> None:
    """Soft-delete de una tasa. Si era la default, promueve la siguiente."""
    obj = session.exec(
        select(CompanyTaxRate)
        .where(CompanyTaxRate.id == rate_id)
        .where(CompanyTaxRate.company_id == company_id)
    ).first()
    if obj is None:
        return
    was_default = obj.is_default
    obj.is_active = False
    obj.is_default = False
    session.add(obj)
    session.flush()

    if was_default:
        # Promover la primera tasa activa restante
        first_active = session.exec(
            select(CompanyTaxRate)
            .where(CompanyTaxRate.company_id == company_id)
            .where(CompanyTaxRate.is_active == True)  # noqa: E712
            .order_by(CompanyTaxRate.display_order, CompanyTaxRate.id)
        ).first()
        if first_active:
            first_active.is_default = True
            session.add(first_active)
            session.flush()


# ── Helpers privados ───────────────────────────────────────────────────────────


def _clear_default(
    company_id: int, session: Session, exclude_id: int | None = None
) -> None:
    rows = session.exec(
        select(CompanyTaxRate)
        .where(CompanyTaxRate.company_id == company_id)
        .where(CompanyTaxRate.is_default == True)  # noqa: E712
    ).all()
    for row in rows:
        if exclude_id is not None and row.id == exclude_id:
            continue
        row.is_default = False
        session.add(row)
    session.flush()
