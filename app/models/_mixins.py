"""Mixins reutilizables para modelos de dominio.

Este módulo centraliza patrones estructurales que se repiten a lo
largo de los modelos SQLModel/Reflex, principalmente el scope
multi-tenant.

Uso:
    class Product(TenantMixin, rx.Model, table=True):
        # company_id/branch_id inyectados por el mixin.
        barcode: str = Field(...)

Nota sobre MRO: ``TenantMixin`` debe ir ANTES de ``rx.Model`` en la
lista de bases. SQLModel procesa las anotaciones heredadas como
columnas, por lo que el orden define correctamente la precedencia
del metaclass.

Diseño:
    - ``TenantMixin`` hereda de ``SQLModel`` (sin ``table=True``) para
      que sus anotaciones se integren correctamente en la clase tabla
      derivada.
    - El listener ``before_flush`` en ``app/utils/tenant.py`` introspecciona
      ``company_id``/``branch_id`` por nombre de columna; agregar el
      mixin no cambia ese contrato.
"""
from __future__ import annotations

from sqlmodel import Field, SQLModel


class TenantMixin(SQLModel):
    """Scope multi-tenant: ``company_id`` + ``branch_id`` NOT NULL con FK e índice.

    Aplicar sólo a modelos que operen con ambos niveles de tenancy.
    Modelos con scope únicamente por empresa (p. ej. ``CompanyBillingConfig``,
    ``Role``, ``User``) definen ``company_id`` directamente en la clase.
    """

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
