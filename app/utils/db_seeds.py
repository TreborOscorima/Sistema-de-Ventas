from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select

from app.enums import PaymentMethodType
from app.models import Category, PaymentMethod, Unit

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
    {
        "name": "Crédito / Fiado",
        "code": "credit_sale",
        "method_id": "credit_sale",
        "description": "Venta al crédito",
        "kind": PaymentMethodType.credit,
        "allows_change": False,
    },
]

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
    },
}


def get_country_config(country_code: str) -> dict:
    """Obtiene la configuración completa de un país.
    
    Args:
        country_code: Código ISO del país (ej: 'PE', 'AR', 'EC')
        
    Returns:
        Diccionario con toda la configuración del país
    """
    country_code = (country_code or "PE").upper()
    return SUPPORTED_COUNTRIES.get(country_code, SUPPORTED_COUNTRIES["PE"])


def get_payment_methods_for_country(country_code: str) -> list[dict]:
    """Obtiene los métodos de pago para un país específico.
    
    Args:
        country_code: Código ISO del país (ej: 'PE', 'AR', 'EC')
        
    Returns:
        Lista de métodos de pago (universales + específicos del país)
    """
    country_code = (country_code or "PE").upper()
    methods = list(UNIVERSAL_PAYMENT_METHODS)
    if country_code in COUNTRY_PAYMENT_METHODS:
        methods.extend(COUNTRY_PAYMENT_METHODS[country_code])
    return methods


# Por defecto: Perú (para compatibilidad con instalaciones existentes)
DEFAULT_PAYMENT_METHODS = get_payment_methods_for_country("PE")

def seed_new_branch_data(
    session: Session,
    company_id: int,
    branch_id: int,
) -> None:
    """Carga datos base para una nueva sucursal."""
    if not company_id or not branch_id:
        return
    company_id = int(company_id)
    branch_id = int(branch_id)

    has_categories = session.exec(
        select(Category.id)
        .where(Category.company_id == company_id)
        .where(Category.branch_id == branch_id)
        .limit(1)
    ).first()
    if not has_categories:
        session.add_all(
            [
                Category(name="General", company_id=company_id, branch_id=branch_id),
            ]
        )

    has_units = session.exec(
        select(Unit.id)
        .where(Unit.company_id == company_id)
        .where(Unit.branch_id == branch_id)
        .limit(1)
    ).first()
    if not has_units:
        unit_defaults = [
            ("unidad", False),
            ("kg", True),
            ("g", True),
            ("l", True),
            ("ml", True),
        ]
        session.add_all(
            [
                Unit(
                    name=name,
                    allows_decimal=allows,
                    company_id=company_id,
                    branch_id=branch_id,
                )
                for name, allows in unit_defaults
            ]
        )

    has_methods = session.exec(
        select(PaymentMethod.id)
        .where(PaymentMethod.company_id == company_id)
        .where(PaymentMethod.branch_id == branch_id)
        .limit(1)
    ).first()
    if not has_methods:
        session.add_all(
            [
                PaymentMethod(
                    name=data["name"],
                    code=data["code"],
                    is_active=True,
                    allows_change=data["allows_change"],
                    method_id=data["method_id"],
                    description=data["description"],
                    kind=data["kind"],
                    enabled=True,
                    company_id=company_id,
                    branch_id=branch_id,
                )
                for data in DEFAULT_PAYMENT_METHODS
            ]
        )


def seed_new_company_data(
    session: Session,
    company_id: int,
    branch_id: int | None = None,
) -> None:
    """Compatibilidad: carga datos base para una empresa/sucursal."""
    if not company_id:
        return
    if branch_id:
        seed_new_branch_data(session, company_id, branch_id)


async def init_payment_methods(
    session: AsyncSession,
    company_id: int,
    branch_id: int,
) -> None:
    if not company_id or not branch_id:
        return
    await session.run_sync(
        lambda sync_session: seed_new_branch_data(
            sync_session, company_id, branch_id
        )
    )
    await session.commit()
