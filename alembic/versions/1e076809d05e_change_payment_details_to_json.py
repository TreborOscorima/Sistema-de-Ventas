"""change_payment_details_to_json

Revision ID: 1e076809d05e
Revises: 4f8c2f6d1a3b
Create Date: 2025-12-29 07:38:33.030185

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
import sqlmodel

# --- ESTAS SON LAS LÍNEAS QUE FALTABAN O ESTABAN DAÑADAS ---
revision: str = '1e076809d05e'
down_revision: Union[str, Sequence[str], None] = '4f8c2f6d1a3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
# -----------------------------------------------------------

def upgrade() -> None:
    """Upgrade schema: Convertir payment_details de Texto a JSON conservando datos."""
    
    # 1. Renombrar columna vieja
    with op.batch_alter_table('sale', schema=None) as batch_op:
        batch_op.alter_column(
            'payment_details',
            new_column_name='payment_details_old',
            existing_type=mysql.VARCHAR(length=255), 
            existing_nullable=False
        )
        batch_op.add_column(sa.Column('payment_details', sa.JSON(), nullable=True))

    # 2. Migrar datos (UPDATE masivo)
    op.execute(
        sa.text(
            "UPDATE sale "
            "SET payment_details = JSON_OBJECT('legacy', IFNULL(payment_details_old, ''), 'summary', IFNULL(payment_details_old, ''))"
        )
    )

    # 3. Borrar columna vieja
    with op.batch_alter_table('sale', schema=None) as batch_op:
        batch_op.drop_column('payment_details_old')


def downgrade() -> None:
    """Downgrade schema: Revertir de JSON a Texto."""
    with op.batch_alter_table('sale', schema=None) as batch_op:
        batch_op.add_column(sa.Column('payment_details_old', mysql.VARCHAR(length=255), nullable=True))
    
    # Intentamos recuperar el texto 'legacy' del JSON
    op.execute(
        sa.text(
            "UPDATE sale SET payment_details_old = JSON_UNQUOTE(JSON_EXTRACT(payment_details, '$.legacy'))"
        )
    )
    
    with op.batch_alter_table('sale', schema=None) as batch_op:
        batch_op.drop_column('payment_details')
        batch_op.alter_column('payment_details_old', new_column_name='payment_details', existing_type=mysql.VARCHAR(length=255), nullable=False)