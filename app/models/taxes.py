from decimal import Decimal

import sqlalchemy
from sqlalchemy import Numeric
from sqlmodel import Field, SQLModel


class CompanyTaxRate(SQLModel, table=True):
    """Tasa de impuesto configurable por empresa.

    Una empresa puede tener múltiples tasas (ej. IVA 21% estándar,
    IVA 10.5% reducida). La marcada como is_default se usa como tasa
    de fallback en documentos fiscales y vista previa de recibos.
    Scope: company_id (sin branch_id — el régimen fiscal es por empresa).
    """

    __tablename__ = "companytaxrate"

    __table_args__ = (
        sqlalchemy.Index("ix_companytaxrate_company", "company_id"),
        sqlalchemy.Index(
            "ix_companytaxrate_company_active", "company_id", "is_active"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(
        foreign_key="company.id",
        nullable=False,
    )
    tax_name: str = Field(
        max_length=20,
        nullable=False,
        description="Sigla del impuesto: IGV, IVA, IVA-I, etc.",
    )
    label: str = Field(
        max_length=50,
        nullable=False,
        description="Descripción humana: Estándar, Reducida, Incrementada",
    )
    rate: Decimal = Field(
        sa_column=sqlalchemy.Column(
            Numeric(5, 2), nullable=False, comment="Tasa en porcentaje (ej. 18.00)"
        )
    )
    is_default: bool = Field(
        default=False,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Boolean, nullable=False, server_default="0"
        ),
        description="Tasa por defecto usada en nuevos documentos fiscales.",
    )
    is_active: bool = Field(
        default=True,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Boolean, nullable=False, server_default="1"
        ),
    )
    display_order: int = Field(
        default=0,
        sa_column=sqlalchemy.Column(
            sqlalchemy.SmallInteger, nullable=False, server_default="0"
        ),
    )
