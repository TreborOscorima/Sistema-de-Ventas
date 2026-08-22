"""Ampliar columnas de stock/cantidad de Numeric(10,4) a Numeric(18,4).

El tipo original DECIMAL(10,4) tope en 999.999,9999. Empresas que operan al por
mayor (o productos con muchas variantes cuyo stock se agrega en el producto padre)
superan ese límite: al recalcular ``product.stock = SUM(variantes)`` o al mover
grandes cantidades, MySQL rechaza el UPDATE con
``(1264) Out of range value for column 'stock'`` y aborta toda la operación
(ej. una transferencia de "todo el stock" entre sucursales).

Se amplían a DECIMAL(18,4) (tope ~99.999 millones de millones) TODAS las columnas
de stock/cantidad del sistema para evitar la misma clase de overflow en ventas,
compras, presupuestos y ajustes. Los precios NO se tocan (no se agregan del mismo
modo). Es una ampliación pura: ningún dato existente se pierde ni se trunca.

Revision ID: z1a2b3c4
Revises: y0z1a2b3
"""
from alembic import op
import sqlalchemy as sa

revision = "z1a2b3c4"
down_revision = "y0z1a2b3"
branch_labels = None
depends_on = None

OLD = sa.Numeric(10, 4)
NEW = sa.Numeric(18, 4)

# (tabla, columna, nullable, server_default)
COLUMNS = [
    ("product", "stock", True, None),
    ("product", "min_stock_alert", False, sa.text("'5.0000'")),
    ("productvariant", "stock", True, None),
    ("productvariant", "min_stock_alert", True, None),
    ("productbatch", "stock", True, None),
    ("stockmovement", "quantity", True, None),
    ("stocktransferitem", "quantity", True, None),
    ("productkit", "quantity", True, None),
    ("cashboxlog", "quantity", True, None),
    ("purchaseitem", "quantity", True, None),
    ("purchaseorderitem", "current_stock", True, None),
    ("purchaseorderitem", "min_stock_alert", True, None),
    ("purchaseorderitem", "suggested_quantity", True, None),
    ("quotationitem", "quantity", True, None),
    ("saleitem", "quantity", True, None),
    ("salereturnitem", "quantity", True, None),
]


def _alter(to_type, from_type):
    # Defensivo: el historial de migraciones del repo es inconsistente — algunas
    # tablas (p.ej. stocktransferitem, quotationitem) las crea una migración que NO
    # está en la ascendencia del head actual, así que en una BD reconstruida sólo
    # con `alembic upgrade head` (CI) todavía no existen en este punto. Sólo
    # alteramos la columna si su tabla y columna existen: en la BD real de
    # producción (que ya tiene todas las tablas) se amplían las 16; en una BD nueva
    # se saltan las ausentes (los tests las crean vía metadata con el tipo nuevo).
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    for table, column, nullable, server_default in COLUMNS:
        if table not in existing_tables:
            continue
        if column not in {c["name"] for c in inspector.get_columns(table)}:
            continue
        op.alter_column(
            table,
            column,
            existing_type=from_type,
            type_=to_type,
            existing_nullable=nullable,
            existing_server_default=server_default,
        )


def upgrade() -> None:
    _alter(NEW, OLD)


def downgrade() -> None:
    _alter(OLD, NEW)
