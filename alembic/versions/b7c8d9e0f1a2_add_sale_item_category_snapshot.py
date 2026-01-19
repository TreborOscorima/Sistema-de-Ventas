"""agregar snapshot de categoria en items de venta

ID de revision: b7c8d9e0f1a2
Revisa: a1b2c3d4e5f6
Fecha de creacion: 2026-02-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# identificadores de revision, usados por Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualizar esquema."""
    op.add_column(
        "saleitem",
        sa.Column(
            "product_category_snapshot",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="",
        ),
    )
    op.execute(
        """
        UPDATE saleitem AS si
        JOIN product p ON si.product_id = p.id
        SET si.product_category_snapshot = COALESCE(NULLIF(p.category, ''), 'General')
        WHERE si.product_id IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE saleitem
        SET product_category_snapshot = 'Servicios'
        WHERE (product_id IS NULL OR product_category_snapshot = '')
        """
    )
    op.alter_column("saleitem", "product_category_snapshot", server_default=None)


def downgrade() -> None:
    """Revertir esquema."""
    op.drop_column("saleitem", "product_category_snapshot")
