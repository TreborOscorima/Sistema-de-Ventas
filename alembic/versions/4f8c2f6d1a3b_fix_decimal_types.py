"""fix_decimal_types

Revision ID: 4f8c2f6d1a3b
Revises: 23c0e16c9726
Create Date: 2025-12-29 02:44:30.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "4f8c2f6d1a3b"
down_revision: Union[str, Sequence[str], None] = "23c0e16c9726"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("cashboxlog", schema=None) as batch_op:
        batch_op.alter_column(
            "amount",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "quantity",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 4),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "cost",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
        )

    with op.batch_alter_table("cashboxsession", schema=None) as batch_op:
        batch_op.alter_column(
            "opening_amount",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "closing_amount",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
        )

    with op.batch_alter_table("fieldprice", schema=None) as batch_op:
        batch_op.alter_column(
            "price",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
        )

    with op.batch_alter_table("fieldreservation", schema=None) as batch_op:
        batch_op.alter_column(
            "total_amount",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "paid_amount",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
        )

    with op.batch_alter_table("product", schema=None) as batch_op:
        batch_op.alter_column(
            "stock",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 4),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "purchase_price",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "sale_price",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
        )

    with op.batch_alter_table("sale", schema=None) as batch_op:
        batch_op.alter_column(
            "total_amount",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
        )

    with op.batch_alter_table("saleitem", schema=None) as batch_op:
        batch_op.alter_column(
            "quantity",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 4),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "unit_price",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "subtotal",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
        )

    with op.batch_alter_table("stockmovement", schema=None) as batch_op:
        batch_op.alter_column(
            "quantity",
            existing_type=mysql.FLOAT(),
            type_=sa.Numeric(10, 4),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("stockmovement", schema=None) as batch_op:
        batch_op.alter_column(
            "quantity",
            existing_type=sa.Numeric(10, 4),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )

    with op.batch_alter_table("saleitem", schema=None) as batch_op:
        batch_op.alter_column(
            "subtotal",
            existing_type=sa.Numeric(10, 2),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "unit_price",
            existing_type=sa.Numeric(10, 2),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "quantity",
            existing_type=sa.Numeric(10, 4),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )

    with op.batch_alter_table("sale", schema=None) as batch_op:
        batch_op.alter_column(
            "total_amount",
            existing_type=sa.Numeric(10, 2),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )

    with op.batch_alter_table("product", schema=None) as batch_op:
        batch_op.alter_column(
            "sale_price",
            existing_type=sa.Numeric(10, 2),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "purchase_price",
            existing_type=sa.Numeric(10, 2),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "stock",
            existing_type=sa.Numeric(10, 4),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )

    with op.batch_alter_table("fieldreservation", schema=None) as batch_op:
        batch_op.alter_column(
            "paid_amount",
            existing_type=sa.Numeric(10, 2),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "total_amount",
            existing_type=sa.Numeric(10, 2),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )

    with op.batch_alter_table("fieldprice", schema=None) as batch_op:
        batch_op.alter_column(
            "price",
            existing_type=sa.Numeric(10, 2),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )

    with op.batch_alter_table("cashboxsession", schema=None) as batch_op:
        batch_op.alter_column(
            "closing_amount",
            existing_type=sa.Numeric(10, 2),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "opening_amount",
            existing_type=sa.Numeric(10, 2),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )

    with op.batch_alter_table("cashboxlog", schema=None) as batch_op:
        batch_op.alter_column(
            "cost",
            existing_type=sa.Numeric(10, 2),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "quantity",
            existing_type=sa.Numeric(10, 4),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "amount",
            existing_type=sa.Numeric(10, 2),
            type_=mysql.FLOAT(),
            existing_nullable=True,
        )
