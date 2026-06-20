from __future__ import annotations

from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session

from app.enums import PaymentMethodType
from app.models import Category, Currency, PaymentMethod, Unit
from app.utils.tenant import set_tenant_context

# ── Re-export de datos de países desde tuwayki-core ──────────────────────────
from tuwayki_core.countries import (  # noqa: F401
    SUPPORTED_COUNTRIES,
    get_country_config,
    get_country_config_by_currency,
    UNIVERSAL_PAYMENT_METHODS,
    COUNTRY_PAYMENT_METHODS,
    LEGACY_PAYMENT_METHOD_IDS,
    RESERVED_PAYMENT_METHOD_NAME_KEYS,
    CURRENCY_CATALOG,
    is_reserved_payment_method,
    get_payment_methods_for_country,
)

# Por defecto: Perú (para compatibilidad con instalaciones existentes)
DEFAULT_PAYMENT_METHODS = get_payment_methods_for_country("PE")

# Métodos de pago que se crean por defecto al abrir una sucursal.
SEED_PAYMENT_METHODS = [
    {
        "name": "Efectivo",
        "code": "cash",
        "method_id": "cash",
        "description": "Billetes, Monedas",
        "kind": PaymentMethodType.cash,
        "allows_change": True,
    },
    {
        "name": "Transferencia",
        "code": "transfer",
        "method_id": "transfer",
        "description": "Transferencia bancaria",
        "kind": PaymentMethodType.transfer,
        "allows_change": False,
    },
]


def seed_new_branch_data(
    session: Session,
    company_id: int,
    branch_id: int,
) -> None:
    """Carga datos base para una nueva sucursal.

    Idempotente a nivel motor vía INSERT ... ON DUPLICATE KEY UPDATE — seguro
    bajo concurrencia (dos llamadas simultáneas para la misma branch no chocan
    contra UNIQUE).
    """
    if not company_id or not branch_id:
        return
    company_id = int(company_id)
    branch_id = int(branch_id)
    set_tenant_context(company_id, branch_id)

    # Categorías
    category_rows = [
        {"name": "General", "company_id": company_id, "branch_id": branch_id},
    ]
    stmt = mysql_insert(Category).values(category_rows)
    session.execute(stmt.on_duplicate_key_update(name=stmt.inserted.name))

    # Monedas globales (sin scope de tenant) — idempotente por UNIQUE(code)
    currency_rows = [
        {"code": c["code"], "name": c["name"], "symbol": c["symbol"]}
        for c in CURRENCY_CATALOG
    ]
    stmt = mysql_insert(Currency).values(currency_rows)
    session.execute(
        stmt.on_duplicate_key_update(
            name=stmt.inserted.name,
            symbol=stmt.inserted.symbol,
        )
    )

    # Unidades de medida
    unit_defaults = [
        ("bolsa",   False),
        ("botella", False),
        ("caja",    False),
        ("cm",      True),
        ("docena",  False),
        ("g",       True),
        ("kg",      True),
        ("l",       True),
        ("lata",    False),
        ("m",       True),
        ("ml",      True),
        ("paquete", False),
        ("pieza",   False),
        ("unidad",  False),
    ]
    unit_rows = [
        {
            "name": name,
            "allows_decimal": allows,
            "company_id": company_id,
            "branch_id": branch_id,
        }
        for name, allows in unit_defaults
    ]
    stmt = mysql_insert(Unit).values(unit_rows)
    session.execute(stmt.on_duplicate_key_update(name=stmt.inserted.name))

    # Métodos de pago — sólo Efectivo y Transferencia por defecto
    pm_rows = [
        {
            "name": data["name"],
            "code": data["code"],
            "is_active": True,
            "allows_change": data["allows_change"],
            "method_id": data["method_id"],
            "description": data["description"],
            "kind": data["kind"],
            "enabled": True,
            "company_id": company_id,
            "branch_id": branch_id,
        }
        for data in SEED_PAYMENT_METHODS
    ]
    if pm_rows:
        stmt = mysql_insert(PaymentMethod).values(pm_rows)
        session.execute(stmt.on_duplicate_key_update(method_id=stmt.inserted.method_id))


async def init_payment_methods(
    session: AsyncSession,
    company_id: int,
    branch_id: int,
) -> None:
    if not company_id or not branch_id:
        return
    set_tenant_context(company_id, branch_id)
    await session.run_sync(
        lambda sync_session: seed_new_branch_data(
            sync_session, company_id, branch_id
        )
    )
    await session.commit()
