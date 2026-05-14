"""backfill_seed_data_existing_branches

Retroalimenta monedas, unidades de medida y métodos de pago para todas
las sucursales creadas antes de que el seed inicial fuera ampliado.

- Monedas: inserta el catálogo completo global (PEN, ARS, COP, CLP, USD,
  BOB, UYU, PYG, MXN, VES) sin afectar las ya existentes.
- Unidades: agrega las 14 unidades estándar a cada sucursal existente;
  las que ya existen en una sucursal simplemente se saltan.
- Métodos de pago: agrega Efectivo y Transferencia a cada sucursal que
  aún no los tenga; los existentes no se tocan.

Idempotente: usa INSERT IGNORE, por lo que es seguro re-ejecutar.

ID de revision: b0c1d2e3f4a5
Revisa: e7f8a9b0c1d2
Fecha de creacion: 2026-05-14
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b0c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Monedas globales (tabla sin scope de tenant)
    # ------------------------------------------------------------------
    op.execute("""
        INSERT IGNORE INTO currency (code, name, symbol) VALUES
        ('PEN', 'Sol peruano',          'S/'),
        ('ARS', 'Peso argentino',       '$'),
        ('COP', 'Peso colombiano',      '$'),
        ('CLP', 'Peso chileno',         '$'),
        ('USD', 'Dólar estadounidense', '$'),
        ('BOB', 'Boliviano',            'Bs.'),
        ('UYU', 'Peso uruguayo',        '$U'),
        ('PYG', 'Guaraní',              '₲'),
        ('MXN', 'Peso mexicano',        '$'),
        ('VES', 'Bolívar venezolano',   'Bs.S')
    """)

    # ------------------------------------------------------------------
    # 2. Unidades de medida — una por cada sucursal existente
    #    INSERT IGNORE respeta uq_unit_company_branch_name
    # ------------------------------------------------------------------
    op.execute("""
        INSERT IGNORE INTO unit (name, allows_decimal, company_id, branch_id)
        SELECT u.name, u.allows_decimal, b.company_id, b.id
        FROM branch b
        CROSS JOIN (
            SELECT 'bolsa'   AS name, 0 AS allows_decimal UNION ALL
            SELECT 'botella',         0                    UNION ALL
            SELECT 'caja',            0                    UNION ALL
            SELECT 'cm',              1                    UNION ALL
            SELECT 'docena',          0                    UNION ALL
            SELECT 'g',               1                    UNION ALL
            SELECT 'kg',              1                    UNION ALL
            SELECT 'l',               1                    UNION ALL
            SELECT 'lata',            0                    UNION ALL
            SELECT 'm',               1                    UNION ALL
            SELECT 'ml',              1                    UNION ALL
            SELECT 'paquete',         0                    UNION ALL
            SELECT 'pieza',           0                    UNION ALL
            SELECT 'unidad',          0
        ) u
    """)

    # ------------------------------------------------------------------
    # 3. Métodos de pago — Efectivo y Transferencia por sucursal
    #    INSERT IGNORE respeta uq_paymentmethod_company_branch_code
    # ------------------------------------------------------------------
    op.execute("""
        INSERT IGNORE INTO paymentmethod
            (name, code, method_id, description, kind,
             is_active, allows_change, enabled, company_id, branch_id)
        SELECT pm.name, pm.code, pm.method_id, pm.description, pm.kind,
               1, pm.allows_change, 1, b.company_id, b.id
        FROM branch b
        CROSS JOIN (
            SELECT 'Efectivo'      AS name,
                   'cash'          AS code,
                   'cash'          AS method_id,
                   'Billetes, Monedas' AS description,
                   'cash'          AS kind,
                   1               AS allows_change
            UNION ALL
            SELECT 'Transferencia',
                   'transfer',
                   'transfer',
                   'Transferencia bancaria',
                   'transfer',
                   0
        ) pm
    """)


def downgrade() -> None:
    # No se revierten inserciones de datos de referencia;
    # eliminarlos podría romper registros dependientes.
    pass
