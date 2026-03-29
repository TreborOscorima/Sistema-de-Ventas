"""Modelos de Facturación Electrónica.

Contiene las entidades para configuración de billing por empresa
y documentos fiscales emitidos.  Diseñados para soportar AFIP (Argentina)
y SUNAT (Perú) sin contaminar los modelos de venta existentes.

Seguridad:
    - Certificados y tokens se almacenan **encriptados** en columnas Text.
    - La encriptación usa Fernet + PBKDF2 (ver app/utils/crypto.py).
    - Nunca se almacena texto plano de credenciales fiscales.

Multi-tenant:
    - CompanyBillingConfig: scoped por company_id (una config por empresa).
    - FiscalDocument: scoped por company_id + branch_id (un doc por venta).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

import reflex as rx
import sqlalchemy
from sqlalchemy import DateTime, Numeric, Text, UniqueConstraint
from sqlmodel import Field, Relationship

from app.enums import FiscalStatus, ReceiptType
from app.utils.timezone import utc_now_naive

if TYPE_CHECKING:
    from .sales import Sale


# ═════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE BILLING POR EMPRESA
# ═════════════════════════════════════════════════════════════


class CompanyBillingConfig(rx.Model, table=True):
    """Configuración de facturación electrónica por empresa.

    Una fila por empresa (no por sucursal): las credenciales fiscales
    (RUC/CUIT, certificados) son a nivel de razón social.

    Los campos ``encrypted_*`` y ``nubefact_token`` se almacenan
    encriptados usando ``app.utils.crypto.encrypt_credential``.

    Campos de numeración (``current_sequence_*``) se incrementan
    atómicamente con ``SELECT ... FOR UPDATE`` para evitar duplicados
    en emisión concurrente.
    """

    __tablename__ = "companybillingconfig"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            name="uq_companybillingconfig_company",
        ),
    )

    # ── Tenant ───────────────────────────────────────────────
    company_id: int = Field(
        foreign_key="company.id",
        index=True,
        nullable=False,
    )

    # ── Identificación fiscal ────────────────────────────────
    country: str = Field(
        default="PE",
        max_length=5,
        description="Código ISO país: PE (Perú) o AR (Argentina). "
        "Determina qué BillingStrategy se instancia.",
    )
    environment: str = Field(
        default="sandbox",
        max_length=20,
        description="'sandbox' (homologación/beta) o 'production'.",
    )
    tax_id: str = Field(
        default="",
        max_length=20,
        description="RUC (Perú, 11 dígitos) o CUIT (Argentina, 11 dígitos).",
    )
    tax_id_type: str = Field(
        default="RUC",
        max_length=10,
        description="Tipo de ID fiscal: 'RUC', 'CUIT'.",
    )
    business_name: str = Field(
        default="",
        description="Razón social registrada ante la autoridad tributaria.",
    )
    business_address: str = Field(
        default="",
        description="Domicilio fiscal registrado.",
    )

    # ── Certificados (encriptados) ───────────────────────────
    encrypted_certificate: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(Text, nullable=True),
        description="Certificado X.509 (.crt/.pem) encriptado con Fernet. "
        "Para AFIP: PEM. Para SUNAT: se extrae del PFX.",
    )
    encrypted_private_key: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(Text, nullable=True),
        description="Clave privada (.key) encriptada con Fernet. "
        "Para AFIP: RSA PEM. Para SUNAT: se extrae del PFX.",
    )

    # ── Metadatos de certificado (para alertas de expiración) ─
    cert_subject: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Subject (CN) del certificado X.509. "
        "Ej: 'SERIALNUMBER=CUIT 20123456789, CN=nombre'.",
    )
    cert_issuer: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Emisor (Issuer) del certificado. "
        "Ej: 'CN=AC AFIP, O=AFIP'.",
    )
    cert_not_before: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(DateTime, nullable=True),
        description="Fecha de inicio de validez del certificado (UTC).",
    )
    cert_not_after: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(DateTime, nullable=True),
        description="Fecha de expiración del certificado (UTC). "
        "Usado para alertas de renovación.",
    )

    # ── Nubefact / OSE (Perú) ────────────────────────────────
    nubefact_url: Optional[str] = Field(
        default=None,
        max_length=512,
        description="URL completa del endpoint Nubefact: "
        "https://api.nubefact.com/api/v1/{ruta_unica}",
    )
    nubefact_token: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(Text, nullable=True),
        description="API token de Nubefact, encriptado con Fernet.",
    )

    # ── AFIP (Argentina) ─────────────────────────────────────
    afip_punto_venta: int = Field(
        default=1,
        description="Número de punto de venta habilitado en AFIP (1-99998).",
    )
    emisor_iva_condition: str = Field(
        default="RI",
        max_length=20,
        description="Condición IVA del emisor AR: 'RI' (Resp. Inscripto), "
        "'monotributo', 'exento'. Determina Factura A/B/C.",
    )
    afip_concepto: int = Field(
        default=1,
        description="Concepto AFIP: 1=Productos, 2=Servicios, 3=Productos y Servicios. "
        "Determina campos obligatorios (fecha_serv_desde/hasta para 2 y 3).",
    )
    ar_identification_threshold: Decimal = Field(
        default=Decimal("68782.00"),
        sa_column=sqlalchemy.Column(
            Numeric(12, 2), nullable=False, server_default="68782.00"
        ),
        description="Umbral ARS para identificación obligatoria en Factura B. "
        "AFIP lo actualiza periódicamente (RG 5616/2024: $68.782).",
    )

    # ── Lookup API (consulta RUC/DNI/CUIT) ─────────────────
    lookup_api_url: str = Field(
        default="",
        max_length=512,
        description="URL base del servicio de consulta RUC/DNI. "
        "Perú: 'https://api.apis.net.pe/v2'. Argentina: vacío (usa AFIP).",
    )
    lookup_api_token: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(Text, nullable=True),
        description="Token de API para consulta RUC/DNI, encriptado con Fernet.",
    )

    # ── Series / Numeración ──────────────────────────────────
    serie_factura: str = Field(
        default="F001",
        max_length=10,
        description="Serie para Facturas. Perú: F001+. Argentina: via PtoVta.",
    )
    serie_boleta: str = Field(
        default="B001",
        max_length=10,
        description="Serie para Boletas. Perú: B001+. Argentina: via PtoVta.",
    )
    current_sequence_factura: int = Field(
        default=0,
        description="Último correlativo emitido para Facturas. "
        "Se incrementa atómicamente con FOR UPDATE.",
    )
    current_sequence_boleta: int = Field(
        default=0,
        description="Último correlativo emitido para Boletas. "
        "Se incrementa atómicamente con FOR UPDATE.",
    )

    # ── Cuota mensual ────────────────────────────────────────
    current_billing_count: int = Field(
        default=0,
        description="Documentos fiscales emitidos en el mes actual.",
    )
    billing_count_reset_date: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False), nullable=True
        ),
        description="Fecha del último reset del contador mensual.",
    )
    max_billing_limit: int = Field(
        default=500,
        description="Límite mensual según plan: "
        "Standard=500, Professional=1000, Enterprise=2000.",
    )

    # ── Estado ───────────────────────────────────────────────
    is_active: bool = Field(
        default=False,
        description="Toggle maestro. Si es False, se usa NoOpBillingStrategy.",
    )
    created_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False),
            server_default=sqlalchemy.func.now(),
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False), nullable=True
        ),
    )

    # Nota: no se define Relationship a Company porque es lookup
    # unidireccional vía company_id — evita importación circular.


# ═════════════════════════════════════════════════════════════
# DOCUMENTO FISCAL (un registro por venta facturada)
# ═════════════════════════════════════════════════════════════


class FiscalDocument(rx.Model, table=True):
    """Documento fiscal electrónico vinculado a una venta.

    Almacena la respuesta de SUNAT (CDR) o AFIP (CAE), datos de QR,
    y auditoría de XML enviado/recibido.

    Relación 1:1 con Sale — una venta genera como máximo un documento fiscal.
    Si la venta no requiere facturación, no se crea FiscalDocument.

    Ciclo de vida (fiscal_status):
        pending → sent → authorized   (flujo exitoso)
        pending → sent → rejected     (datos incorrectos)
        pending → sent → error        (timeout, red caída)
        pending → error               (fallo antes de enviar)
    """

    __tablename__ = "fiscaldocument"

    __table_args__ = (
        # Unicidad por (company_id, sale_id, receipt_type):
        # permite que la misma venta tenga una Factura/Boleta Y una Nota de Crédito.
        UniqueConstraint(
            "company_id",
            "sale_id",
            "receipt_type",
            name="uq_fiscaldocument_company_sale_type",
        ),
        sqlalchemy.Index(
            "ix_fiscaldocument_tenant_status",
            "company_id",
            "fiscal_status",
        ),
        sqlalchemy.Index(
            "ix_fiscaldocument_tenant_sent",
            "company_id",
            "sent_at",
        ),
    )

    # ── Tenant ───────────────────────────────────────────────
    company_id: int = Field(
        foreign_key="company.id",
        index=True,
        nullable=False,
    )
    branch_id: int = Field(
        foreign_key="branch.id",
        index=True,
        nullable=False,
    )

    # ── Venta vinculada ──────────────────────────────────────
    sale_id: int = Field(
        foreign_key="sale.id",
        index=True,
        nullable=False,
    )

    # ── Tipo y numeración ────────────────────────────────────
    receipt_type: str = Field(
        default=ReceiptType.boleta,
        max_length=20,
        index=True,
        description="Tipo de comprobante: boleta, factura, nota_credito, nota_debito.",
    )
    serie: str = Field(
        default="",
        max_length=10,
        description="Serie del comprobante: B001, F001, etc.",
    )
    fiscal_number: Optional[int] = Field(
        default=None,
        description="Número correlativo asignado al emitir.",
    )
    full_number: Optional[str] = Field(
        default=None,
        max_length=30,
        description="Número completo formateado: B001-00000123.",
    )

    # ── Estado fiscal ────────────────────────────────────────
    fiscal_status: str = Field(
        default=FiscalStatus.pending,
        max_length=20,
        index=True,
        description="Estado del ciclo de vida fiscal.",
    )

    # ── Respuesta de la entidad fiscal ───────────────────────
    cae_cdr: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(Text, nullable=True),
        description="CAE (AFIP, 14 dígitos) o CDR XML (SUNAT).",
    )
    fiscal_errors: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(Text, nullable=True),
        description="Errores de la entidad fiscal (JSON serializado).",
    )
    qr_data: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(Text, nullable=True),
        description="Payload del código QR para impresión del comprobante.",
    )
    hash_code: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Hash/digest de SUNAT para verificación.",
    )

    # ── Auditoría XML ────────────────────────────────────────
    xml_request: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(Text, nullable=True),
        description="XML/JSON enviado a la entidad fiscal (para auditoría).",
    )
    xml_response: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(Text, nullable=True),
        description="XML/JSON de respuesta de la entidad fiscal.",
    )

    # ── Reintentos ───────────────────────────────────────────
    retry_count: int = Field(
        default=0,
        description="Número de intentos de envío.",
    )

    # ── Timestamps ───────────────────────────────────────────
    sent_at: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False), nullable=True
        ),
        description="Momento del primer envío a la entidad fiscal.",
    )
    authorized_at: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False), nullable=True
        ),
        description="Momento en que fue autorizado (CAE/CDR exitoso).",
    )
    created_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False),
            server_default=sqlalchemy.func.now(),
        ),
    )

    # ── Datos del receptor (snapshot para auditoría) ─────────
    buyer_doc_type: Optional[str] = Field(
        default=None,
        max_length=5,
        description="Tipo doc receptor: '6'=RUC, '1'=DNI, '0'=Sin doc (SUNAT). "
        "'80'=CUIT, '96'=DNI, '99'=CF (AFIP).",
    )
    buyer_doc_number: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Número de documento del receptor.",
    )
    buyer_name: Optional[str] = Field(
        default=None,
        description="Nombre/razón social del receptor.",
    )

    # ── Montos fiscales (snapshot) ───────────────────────────
    taxable_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(12, 2)),
        description="Base imponible (monto sin impuesto).",
    )
    tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(12, 2)),
        description="Monto del impuesto (IGV/IVA).",
    )
    total_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(12, 2)),
        description="Total del comprobante (base + impuesto).",
    )

    # Nota: la relación bidireccional se define solo desde Sale
    # (sale.fiscal_document) para evitar problemas de resolución
    # de nombres cross-file con el registry de SQLAlchemy/Reflex.
