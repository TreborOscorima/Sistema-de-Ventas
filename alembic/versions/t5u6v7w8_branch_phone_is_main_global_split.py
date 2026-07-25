"""Branch.phone + Branch.is_main y unificación de datos globales de empresa.

Separación Global (empresa) vs Sucursal:
- Agrega ``branch.phone`` (teléfono por local, se imprime en el ticket de esa
  sucursal) y ``branch.is_main`` (marca la Casa Central/matriz; una por empresa).
- Backfill: marca como matriz la sucursal de menor id por empresa.
- Backfill: copia ``companysettings.phone`` -> ``branch.phone`` de cada sucursal.
- Unifica los campos GLOBALES (razón social, RUC, domicilio fiscal, rubro,
  moneda, país, mensaje de ticket y leyenda global) de todas las sucursales
  hacia los valores de la matriz. Corrige divergencias previas (p. ej. distinta
  razón social por sucursal bajo el mismo RUC).

Revision ID: t5u6v7w8
Revises: s4t5u6v7
Create Date: 2026-07-25
"""

import sqlalchemy as sa
from alembic import op

revision = "t5u6v7w8"
down_revision = "s4t5u6v7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "branch",
        sa.Column(
            "phone",
            sa.String(50),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "branch",
        sa.Column(
            "is_main",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )

    # 1) Marcar como matriz la sucursal de menor id por empresa.
    op.execute(
        """
        UPDATE branch b
        JOIN (
            SELECT company_id, MIN(id) AS min_id
            FROM branch
            GROUP BY company_id
        ) m ON b.company_id = m.company_id AND b.id = m.min_id
        SET b.is_main = 1
        """
    )

    # 2) Copiar el teléfono existente (CompanySettings) al local correspondiente.
    op.execute(
        """
        UPDATE branch b
        JOIN companysettings cs
          ON cs.company_id = b.company_id AND cs.branch_id = b.id
        SET b.phone = COALESCE(cs.phone, '')
        WHERE cs.phone IS NOT NULL AND cs.phone <> ''
        """
    )

    # 3) Unificar los campos GLOBALES de todas las sucursales con los de la
    #    matriz (la fila de CompanySettings de la sucursal is_main).
    op.execute(
        """
        UPDATE companysettings cs
        JOIN branch mb
          ON mb.company_id = cs.company_id AND mb.is_main = 1
        JOIN companysettings main_cs
          ON main_cs.company_id = cs.company_id AND main_cs.branch_id = mb.id
        SET cs.company_name          = main_cs.company_name,
            cs.ruc                   = main_cs.ruc,
            cs.address               = main_cs.address,
            cs.business_vertical     = main_cs.business_vertical,
            cs.default_currency_code = main_cs.default_currency_code,
            cs.country_code          = main_cs.country_code,
            cs.footer_message        = main_cs.footer_message,
            cs.consumer_defense_legend = main_cs.consumer_defense_legend
        WHERE cs.branch_id <> mb.id
        """
    )


def downgrade() -> None:
    op.drop_column("branch", "is_main")
    op.drop_column("branch", "phone")
