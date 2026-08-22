"""Crear tablas stocktransfer y stocktransferitem si faltan.

CAUSA RAÍZ (2026-08-22): el módulo de transferencias entre sucursales se agregó
como modelos SQLModel (``StockTransfer`` / ``StockTransferItem``) pero NUNCA tuvo
una migración que creara sus tablas. En desarrollo las tablas existían porque
alguna corrida de ``SQLModel.metadata.create_all`` las materializó; en producción
—que aplica SOLO Alembic— las tablas nunca se crearon. Resultado: TODA
transferencia fallaba en el primer INSERT con
``(1146) Table 'sistema_ventas.stocktransfer' doesn't exist`` y la UI mostraba el
genérico "Error al procesar la transferencia".

Esta migración crea ambas tablas de forma DEFENSIVA (solo si no existen), con el
esquema exacto que esperan los modelos. En una BD que ya las tiene (dev, o un
prod futuro ya reparado) es un no-op. Los tests de CI las crean vía metadata, así
que allí también se saltan.

Revision ID: z2b3c4d5
Revises: z1a2b3c4
"""
from alembic import op
import sqlalchemy as sa

revision = "z2b3c4d5"
down_revision = "z1a2b3c4"
branch_labels = None
depends_on = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    if "stocktransfer" not in existing:
        op.create_table(
            "stocktransfer",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("origin_branch_id", sa.Integer(), nullable=False),
            sa.Column("destination_branch_id", sa.Integer(), nullable=False),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("notes", sa.String(length=500), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("completed_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
            sa.ForeignKeyConstraint(["origin_branch_id"], ["branch.id"]),
            sa.ForeignKeyConstraint(["destination_branch_id"], ["branch.id"]),
            sa.ForeignKeyConstraint(
                ["created_by_id"], ["user.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["completed_by_id"], ["user.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_stocktransfer_company_id", "stocktransfer", ["company_id"]
        )
        op.create_index(
            "ix_stocktransfer_origin_branch_id",
            "stocktransfer",
            ["origin_branch_id"],
        )
        op.create_index(
            "ix_stocktransfer_destination_branch_id",
            "stocktransfer",
            ["destination_branch_id"],
        )
        op.create_index(
            "ix_stocktransfer_company_status",
            "stocktransfer",
            ["company_id", "status"],
        )
        op.create_index(
            "ix_stocktransfer_company_created",
            "stocktransfer",
            ["company_id", "created_at"],
        )

    # Releer: stocktransferitem referencia stocktransfer por FK.
    existing = _existing_tables()
    if "stocktransferitem" not in existing:
        op.create_table(
            "stocktransferitem",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("transfer_id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("product_variant_id", sa.Integer(), nullable=True),
            sa.Column("quantity", sa.Numeric(18, 4), nullable=True),
            sa.Column(
                "product_name_snapshot", sa.String(length=500), nullable=False
            ),
            sa.ForeignKeyConstraint(
                ["transfer_id"], ["stocktransfer.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["product_id"], ["product.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["product_variant_id"],
                ["productvariant.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint(
                "quantity > 0", name="ck_stocktransferitem_qty_pos"
            ),
        )
        op.create_index(
            "ix_stocktransferitem_transfer_id",
            "stocktransferitem",
            ["transfer_id"],
        )
        op.create_index(
            "ix_stocktransferitem_transfer",
            "stocktransferitem",
            ["transfer_id"],
        )
        op.create_index(
            "ix_stocktransferitem_product_id",
            "stocktransferitem",
            ["product_id"],
        )


def downgrade() -> None:
    existing = _existing_tables()
    if "stocktransferitem" in existing:
        op.drop_table("stocktransferitem")
    existing = _existing_tables()
    if "stocktransfer" in existing:
        op.drop_table("stocktransfer")
