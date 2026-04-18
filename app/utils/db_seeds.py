from __future__ import annotations

import re
import unicodedata

from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select

from app.enums import PaymentMethodType
from app.models import Category, PaymentMethod, Unit
from app.utils.tenant import set_tenant_context

# ============================================================================
# MÉTODOS DE PAGO POR PAÍS
# Cada país tiene sus propios métodos de pago digitales populares
# ============================================================================

# Métodos de pago universales (disponibles en todos los países)
UNIVERSAL_PAYMENT_METHODS = [
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
    {
        "name": "Tarjeta de Crédito",
        "code": "credit_card",
        "method_id": "credit_card",
        "description": "Pago con tarjeta crédito",
        "kind": PaymentMethodType.credit,
        "allows_change": False,
    },
    {
        "name": "Tarjeta de Débito",
        "code": "debit_card",
        "method_id": "debit_card",
        "description": "Pago con tarjeta débito",
        "kind": PaymentMethodType.debit,
        "allows_change": False,
    },
]

LEGACY_PAYMENT_METHOD_IDS = {"credit_sale"}
RESERVED_PAYMENT_METHOD_NAME_KEYS = {
    "credito fiado",
    "venta a credito",
    "venta al credito",
}

# Métodos específicos por país
COUNTRY_PAYMENT_METHODS = {
    # Perú
    "PE": [
        {
            "name": "Yape",
            "code": "yape",
            "method_id": "yape",
            "description": "Pago con Yape (BCP)",
            "kind": PaymentMethodType.yape,
            "allows_change": False,
        },
        {
            "name": "Plin",
            "code": "plin",
            "method_id": "plin",
            "description": "Pago con Plin",
            "kind": PaymentMethodType.plin,
            "allows_change": False,
        },
    ],
    # Argentina
    "AR": [
        {
            "name": "Mercado Pago",
            "code": "mercadopago",
            "method_id": "mercadopago",
            "description": "Pago con Mercado Pago",
            "kind": PaymentMethodType.wallet,
            "allows_change": False,
        },
        {
            "name": "Cuenta DNI",
            "code": "cuenta_dni",
            "method_id": "cuenta_dni",
            "description": "Pago con Cuenta DNI (Banco Provincia)",
            "kind": PaymentMethodType.wallet,
            "allows_change": False,
        },
        {
            "name": "MODO",
            "code": "modo",
            "method_id": "modo",
            "description": "Pago con MODO",
            "kind": PaymentMethodType.wallet,
            "allows_change": False,
        },
    ],
    # Ecuador
    "EC": [
        {
            "name": "Payphone",
            "code": "payphone",
            "method_id": "payphone",
            "description": "Pago con Payphone",
            "kind": PaymentMethodType.wallet,
            "allows_change": False,
        },
        {
            "name": "De Una",
            "code": "deuna",
            "method_id": "deuna",
            "description": "Pago con De Una (Banco Pichincha)",
            "kind": PaymentMethodType.wallet,
            "allows_change": False,
        },
    ],
    # Colombia
    "CO": [
        {
            "name": "Nequi",
            "code": "nequi",
            "method_id": "nequi",
            "description": "Pago con Nequi",
            "kind": PaymentMethodType.wallet,
            "allows_change": False,
        },
        {
            "name": "Daviplata",
            "code": "daviplata",
            "method_id": "daviplata",
            "description": "Pago con Daviplata",
            "kind": PaymentMethodType.wallet,
            "allows_change": False,
        },
    ],
    # Chile
    "CL": [
        {
            "name": "Mercado Pago",
            "code": "mercadopago",
            "method_id": "mercadopago",
            "description": "Pago con Mercado Pago",
            "kind": PaymentMethodType.wallet,
            "allows_change": False,
        },
        {
            "name": "MACH",
            "code": "mach",
            "method_id": "mach",
            "description": "Pago con MACH",
            "kind": PaymentMethodType.wallet,
            "allows_change": False,
        },
    ],
    # México
    "MX": [
        {
            "name": "Mercado Pago",
            "code": "mercadopago",
            "method_id": "mercadopago",
            "description": "Pago con Mercado Pago",
            "kind": PaymentMethodType.wallet,
            "allows_change": False,
        },
        {
            "name": "CoDi",
            "code": "codi",
            "method_id": "codi",
            "description": "Cobro Digital (Banxico)",
            "kind": PaymentMethodType.wallet,
            "allows_change": False,
        },
    ],
}

# Países soportados con configuración completa
# Incluye: moneda, labels fiscales, formatos de validación
SUPPORTED_COUNTRIES = {
    "PE": {
        "name": "Perú",
        "currency": "PEN",
        "currency_name": "Sol peruano",
        "currency_symbol": "S/",
        "timezone": "America/Lima",
        # Labels fiscales
        "tax_id_label": "RUC",  # Registro Único de Contribuyentes
        "personal_id_label": "DNI",  # Documento Nacional de Identidad
        "tax_id_placeholder": "20123456789",
        "personal_id_placeholder": "12345678",
        # Validaciones
        "phone_digits": [9, 11],  # 9 dígitos o 11 con código país (51)
        "personal_id_length": (8, 8),  # Exactamente 8 dígitos
        "tax_id_length": (11, 11),  # Exactamente 11 dígitos
        # Denominaciones para arqueo de caja (mayor a menor)
        "denominations": [
            {"value": 200, "label": "S/200", "type": "bill"},
            {"value": 100, "label": "S/100", "type": "bill"},
            {"value": 50, "label": "S/50", "type": "bill"},
            {"value": 20, "label": "S/20", "type": "bill"},
            {"value": 10, "label": "S/10", "type": "bill"},
            {"value": 5, "label": "S/5", "type": "coin"},
            {"value": 2, "label": "S/2", "type": "coin"},
            {"value": 1, "label": "S/1", "type": "coin"},
            {"value": 0.50, "label": "S/0.50", "type": "coin"},
            {"value": 0.20, "label": "S/0.20", "type": "coin"},
            {"value": 0.10, "label": "S/0.10", "type": "coin"},
        ],
    },
    "AR": {
        "name": "Argentina",
        "currency": "ARS",
        "currency_name": "Peso argentino",
        "currency_symbol": "$",
        "timezone": "America/Argentina/Buenos_Aires",
        # Labels fiscales
        "tax_id_label": "CUIT",  # Clave Única de Identificación Tributaria
        "personal_id_label": "DNI",  # Documento Nacional de Identidad
        "tax_id_placeholder": "20-12345678-9",
        "personal_id_placeholder": "12345678",
        # Validaciones
        "phone_digits": [10, 13],  # 10 dígitos o 13 con código país (54)
        "personal_id_length": (7, 8),  # 7-8 dígitos
        "tax_id_length": (11, 11),  # 11 dígitos sin guiones
        "denominations": [
            {"value": 20000, "label": "$20.000", "type": "bill"},
            {"value": 10000, "label": "$10.000", "type": "bill"},
            {"value": 2000, "label": "$2.000", "type": "bill"},
            {"value": 1000, "label": "$1.000", "type": "bill"},
            {"value": 500, "label": "$500", "type": "bill"},
            {"value": 200, "label": "$200", "type": "bill"},
            {"value": 100, "label": "$100", "type": "coin"},
            {"value": 50, "label": "$50", "type": "coin"},
            {"value": 20, "label": "$20", "type": "coin"},
            {"value": 10, "label": "$10", "type": "coin"},
            {"value": 5, "label": "$5", "type": "coin"},
            {"value": 2, "label": "$2", "type": "coin"},
            {"value": 1, "label": "$1", "type": "coin"},
        ],
    },
    "EC": {
        "name": "Ecuador",
        "currency": "USD",
        "currency_name": "Dólar estadounidense",
        "currency_symbol": "$",
        "timezone": "America/Guayaquil",
        # Labels fiscales
        "tax_id_label": "RUC",  # Registro Único de Contribuyentes
        "personal_id_label": "Cédula",  # Cédula de Identidad
        "tax_id_placeholder": "1234567890001",
        "personal_id_placeholder": "1234567890",
        # Validaciones
        "phone_digits": [9, 12],  # 9 dígitos o 12 con código país (593)
        "personal_id_length": (10, 10),  # 10 dígitos
        "tax_id_length": (13, 13),  # 13 dígitos
        "denominations": [
            {"value": 100, "label": "$100", "type": "bill"},
            {"value": 50, "label": "$50", "type": "bill"},
            {"value": 20, "label": "$20", "type": "bill"},
            {"value": 10, "label": "$10", "type": "bill"},
            {"value": 5, "label": "$5", "type": "bill"},
            {"value": 1, "label": "$1", "type": "bill"},
            {"value": 0.50, "label": "$0.50", "type": "coin"},
            {"value": 0.25, "label": "$0.25", "type": "coin"},
            {"value": 0.10, "label": "$0.10", "type": "coin"},
            {"value": 0.05, "label": "$0.05", "type": "coin"},
            {"value": 0.01, "label": "$0.01", "type": "coin"},
        ],
    },
    "CO": {
        "name": "Colombia",
        "currency": "COP",
        "currency_name": "Peso colombiano",
        "currency_symbol": "$",
        "timezone": "America/Bogota",
        # Labels fiscales
        "tax_id_label": "NIT",  # Número de Identificación Tributaria
        "personal_id_label": "C.C.",  # Cédula de Ciudadanía
        "tax_id_placeholder": "900123456-7",
        "personal_id_placeholder": "1234567890",
        # Validaciones
        "phone_digits": [10, 12],  # 10 dígitos o 12 con código país (57)
        "personal_id_length": (6, 10),  # 6-10 dígitos
        "tax_id_length": (9, 10),  # 9-10 dígitos sin dígito verificador
        "denominations": [
            {"value": 100000, "label": "$100.000", "type": "bill"},
            {"value": 50000, "label": "$50.000", "type": "bill"},
            {"value": 20000, "label": "$20.000", "type": "bill"},
            {"value": 10000, "label": "$10.000", "type": "bill"},
            {"value": 5000, "label": "$5.000", "type": "bill"},
            {"value": 2000, "label": "$2.000", "type": "bill"},
            {"value": 1000, "label": "$1.000", "type": "coin"},
            {"value": 500, "label": "$500", "type": "coin"},
            {"value": 200, "label": "$200", "type": "coin"},
            {"value": 100, "label": "$100", "type": "coin"},
            {"value": 50, "label": "$50", "type": "coin"},
        ],
    },
    "CL": {
        "name": "Chile",
        "currency": "CLP",
        "currency_name": "Peso chileno",
        "currency_symbol": "$",
        "timezone": "America/Santiago",
        # Labels fiscales
        "tax_id_label": "RUT",  # Rol Único Tributario (empresas)
        "personal_id_label": "RUN",  # Rol Único Nacional (personas)
        "tax_id_placeholder": "12.345.678-9",
        "personal_id_placeholder": "12.345.678-9",
        # Validaciones
        "phone_digits": [9, 11],  # 9 dígitos o 11 con código país (56)
        "personal_id_length": (8, 9),  # 8-9 caracteres (incluye dígito verificador)
        "tax_id_length": (8, 9),  # Mismo formato que RUN
        "denominations": [
            {"value": 20000, "label": "$20.000", "type": "bill"},
            {"value": 10000, "label": "$10.000", "type": "bill"},
            {"value": 5000, "label": "$5.000", "type": "bill"},
            {"value": 2000, "label": "$2.000", "type": "bill"},
            {"value": 1000, "label": "$1.000", "type": "bill"},
            {"value": 500, "label": "$500", "type": "coin"},
            {"value": 100, "label": "$100", "type": "coin"},
            {"value": 50, "label": "$50", "type": "coin"},
            {"value": 10, "label": "$10", "type": "coin"},
        ],
    },
    "MX": {
        "name": "México",
        "currency": "MXN",
        "currency_name": "Peso mexicano",
        "currency_symbol": "$",
        "timezone": "America/Mexico_City",
        # Labels fiscales
        "tax_id_label": "RFC",  # Registro Federal de Contribuyentes
        "personal_id_label": "CURP",  # Clave Única de Registro de Población
        "tax_id_placeholder": "XAXX010101000",
        "personal_id_placeholder": "XEXX010101HNEXXXA4",
        # Validaciones
        "phone_digits": [10, 12],  # 10 dígitos o 12 con código país (52)
        "personal_id_length": (18, 18),  # CURP tiene 18 caracteres
        "tax_id_length": (12, 13),  # RFC 12-13 caracteres
        "denominations": [
            {"value": 1000, "label": "$1,000", "type": "bill"},
            {"value": 500, "label": "$500", "type": "bill"},
            {"value": 200, "label": "$200", "type": "bill"},
            {"value": 100, "label": "$100", "type": "bill"},
            {"value": 50, "label": "$50", "type": "bill"},
            {"value": 20, "label": "$20", "type": "bill"},
            {"value": 10, "label": "$10", "type": "coin"},
            {"value": 5, "label": "$5", "type": "coin"},
            {"value": 2, "label": "$2", "type": "coin"},
            {"value": 1, "label": "$1", "type": "coin"},
            {"value": 0.50, "label": "$0.50", "type": "coin"},
        ],
    },
}


def get_country_config(country_code: str) -> dict:
    """Obtiene la configuración completa de un país.

    Parámetros:
        country_code: Código ISO del país (ej: 'PE', 'AR', 'EC')

    Retorna:
        Diccionario con toda la configuración del país
    """
    country_code = (country_code or "PE").upper()
    return SUPPORTED_COUNTRIES.get(country_code, SUPPORTED_COUNTRIES["PE"])


def _payment_method_name_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    collapsed = re.sub(r"[^a-z0-9]+", " ", without_accents.lower()).strip()
    return collapsed


def is_reserved_payment_method(
    *,
    method_id: str | None = None,
    code: str | None = None,
    name: str | None = None,
) -> bool:
    """Determina si un método corresponde al flujo reservado de venta a crédito."""
    normalized_method_id = (method_id or "").strip().lower()
    normalized_code = (code or "").strip().lower()
    if (
        normalized_method_id in LEGACY_PAYMENT_METHOD_IDS
        or normalized_code in LEGACY_PAYMENT_METHOD_IDS
    ):
        return True
    return _payment_method_name_key(name or "") in RESERVED_PAYMENT_METHOD_NAME_KEYS


def get_payment_methods_for_country(country_code: str) -> list[dict]:
    """Obtiene los métodos de pago para un país específico.

    Parámetros:
        country_code: Código ISO del país (ej: 'PE', 'AR', 'EC')

    Retorna:
        Lista de métodos de pago (universales + específicos del país)
    """
    country_code = (country_code or "PE").upper()
    methods = list(UNIVERSAL_PAYMENT_METHODS)
    if country_code in COUNTRY_PAYMENT_METHODS:
        methods.extend(COUNTRY_PAYMENT_METHODS[country_code])
    return [
        dict(method)
        for method in methods
        if not is_reserved_payment_method(
            method_id=method.get("method_id"),
            code=method.get("code"),
            name=method.get("name"),
        )
    ]


# Por defecto: Perú (para compatibilidad con instalaciones existentes)
DEFAULT_PAYMENT_METHODS = get_payment_methods_for_country("PE")

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

    # Unidades
    unit_defaults = [
        ("unidad", False),
        ("kg", True),
        ("g", True),
        ("l", True),
        ("ml", True),
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

    # Métodos de pago
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
        for data in DEFAULT_PAYMENT_METHODS
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
