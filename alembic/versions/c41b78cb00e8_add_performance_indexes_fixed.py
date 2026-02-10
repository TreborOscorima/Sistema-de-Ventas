"""agregar indices de rendimiento (correccion)

ID de revision: c41b78cb00e8
Revisa: e6a2d1cf185c
Fecha de creacion: 2026-01-04 08:15:25.971435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# identificadores de revision, usados por Alembic.
revision: str = 'c41b78cb00e8'
down_revision: Union[str, Sequence[str], None] = 'e6a2d1cf185c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(conn, table: str, index_name: str) -> bool:
    insp = sa.inspect(conn)
    for idx in insp.get_indexes(table):
        if idx.get("name") == index_name:
            return True
    return False


def _column_exists(conn, table: str, column: str) -> bool:
    insp = sa.inspect(conn)
    return column in [c["name"] for c in insp.get_columns(table)]


def upgrade() -> None:
    """Actualizar esquema."""
    conn = op.get_bind()
    # cashboxlog.payment_method_id no se añadió en e6a2d1cf185c (estaba comentado); añadir aquí si falta
    if not _column_exists(conn, "cashboxlog", "payment_method_id"):
        op.add_column("cashboxlog", sa.Column("payment_method_id", sa.Integer(), nullable=True))
    # Índices idempotentes (por si la migración falló a medias y se reintenta)
    if not _index_exists(conn, "cashboxlog", "ix_cashboxlog_action"):
        op.create_index(op.f("ix_cashboxlog_action"), "cashboxlog", ["action"], unique=False)
    if not _index_exists(conn, "cashboxlog", "ix_cashboxlog_payment_method_id"):
        op.create_index(op.f("ix_cashboxlog_payment_method_id"), "cashboxlog", ["payment_method_id"], unique=False)
    if not _index_exists(conn, "cashboxlog", "ix_cashboxlog_timestamp"):
        op.create_index(op.f("ix_cashboxlog_timestamp"), "cashboxlog", ["timestamp"], unique=False)
    if not _index_exists(conn, "product", "ix_product_description"):
        op.create_index(op.f("ix_product_description"), "product", ["description"], unique=False)
    if not _index_exists(conn, "sale", "ix_sale_client_id"):
        op.create_index(op.f("ix_sale_client_id"), "sale", ["client_id"], unique=False)
    if not _index_exists(conn, "sale", "ix_sale_timestamp"):
        op.create_index(op.f("ix_sale_timestamp"), "sale", ["timestamp"], unique=False)


def downgrade() -> None:
    """Revertir esquema."""
    # ### comandos autogenerados por Alembic - ajustar si es necesario! ###
    op.drop_index(op.f('ix_sale_timestamp'), table_name='sale')
    op.drop_index(op.f('ix_sale_client_id'), table_name='sale')
    op.drop_index(op.f('ix_product_description'), table_name='product')
    op.drop_index(op.f('ix_cashboxlog_timestamp'), table_name='cashboxlog')
    op.drop_index(op.f('ix_cashboxlog_payment_method_id'), table_name='cashboxlog')
    op.drop_index(op.f('ix_cashboxlog_action'), table_name='cashboxlog')
    # ### fin de comandos de Alembic ###
