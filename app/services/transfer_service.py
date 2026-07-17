"""Servicio de transferencias de stock entre sucursales.

Ejecuta la transferencia atómicamente: descuenta stock en origen,
suma en destino, genera StockMovements en ambas sucursales y
actualiza el estado de la transferencia.
"""
import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.models import (
    Branch,
    Product,
    StockMovement,
    StockTransfer,
    StockTransferItem,
)
from app.models.inventory import TransferStatus
from app.utils.timezone import utc_now_naive

logger = logging.getLogger(__name__)


class TransferError(Exception):
    pass


class TransferService:
    """Operaciones de transferencia de stock entre sucursales."""

    @staticmethod
    async def create_transfer(
        session: AsyncSession,
        *,
        company_id: int,
        origin_branch_id: int,
        destination_branch_id: int,
        items: list[dict],
        user_id: int | None = None,
        notes: str = "",
    ) -> StockTransfer:
        if origin_branch_id == destination_branch_id:
            raise TransferError("La sucursal de origen y destino no pueden ser la misma.")

        if not items:
            raise TransferError("Debe incluir al menos un producto.")

        origin = await session.get(Branch, origin_branch_id)
        dest = await session.get(Branch, destination_branch_id)
        if not origin or origin.company_id != company_id:
            raise TransferError("Sucursal de origen no pertenece a la empresa.")
        if not dest or dest.company_id != company_id:
            raise TransferError("Sucursal de destino no pertenece a la empresa.")

        transfer = StockTransfer(
            company_id=company_id,
            origin_branch_id=origin_branch_id,
            destination_branch_id=destination_branch_id,
            notes=notes,
            created_by_id=user_id,
            status=TransferStatus.PENDING,
        )
        session.add(transfer)
        await session.flush()

        for item in items:
            product_id = item["product_id"]
            quantity = Decimal(str(item["quantity"]))
            variant_id = item.get("variant_id")

            if quantity <= 0:
                raise TransferError(f"La cantidad debe ser mayor a 0 (producto ID {product_id}).")

            product = await session.exec(
                select(Product).where(
                    Product.id == product_id,
                    Product.company_id == company_id,
                    Product.branch_id == origin_branch_id,
                )
            )
            product = product.first()
            if not product:
                raise TransferError(f"Producto ID {product_id} no encontrado en sucursal de origen.")

            if product.stock < quantity:
                raise TransferError(
                    f"Stock insuficiente de '{product.description}': "
                    f"disponible {product.stock}, solicitado {quantity}."
                )

            ti = StockTransferItem(
                transfer_id=transfer.id,
                product_id=product_id,
                product_variant_id=variant_id,
                quantity=quantity,
                product_name_snapshot=product.description,
            )
            session.add(ti)

        await session.flush()
        return transfer

    @staticmethod
    async def execute_transfer(
        session: AsyncSession,
        *,
        transfer_id: int,
        company_id: int,
        user_id: int | None = None,
    ) -> StockTransfer:
        result = await session.exec(
            select(StockTransfer)
            .where(
                StockTransfer.id == transfer_id,
                StockTransfer.company_id == company_id,
            )
            .options(selectinload(StockTransfer.items))
        )
        transfer = result.first()
        if not transfer:
            raise TransferError("Transferencia no encontrada.")

        if transfer.status != TransferStatus.PENDING:
            raise TransferError(f"La transferencia ya está en estado '{transfer.status.value}'.")

        origin_id = transfer.origin_branch_id
        dest_id = transfer.destination_branch_id
        now = utc_now_naive()

        for item in transfer.items:
            origin_product = await session.exec(
                select(Product).where(
                    Product.id == item.product_id,
                    Product.company_id == company_id,
                    Product.branch_id == origin_id,
                )
            )
            origin_product = origin_product.first()
            if not origin_product:
                raise TransferError(
                    f"Producto '{item.product_name_snapshot}' ya no existe en sucursal origen."
                )

            if origin_product.stock < item.quantity:
                raise TransferError(
                    f"Stock insuficiente de '{origin_product.description}': "
                    f"disponible {origin_product.stock}, requerido {item.quantity}."
                )

            origin_product.stock -= item.quantity
            session.add(origin_product)

            session.add(StockMovement(
                company_id=company_id,
                branch_id=origin_id,
                product_id=item.product_id,
                user_id=user_id,
                type="Transferencia Salida",
                quantity=-item.quantity,
                description=f"Transferencia #{transfer.id} → sucursal destino",
                timestamp=now,
            ))

            dest_query = select(Product).where(
                Product.company_id == company_id,
                Product.branch_id == dest_id,
            )
            if origin_product.barcode:
                dest_query = dest_query.where(Product.barcode == origin_product.barcode)
            else:
                dest_query = dest_query.where(Product.description == origin_product.description)
            dest_product = (await session.exec(dest_query)).first()

            if dest_product:
                dest_product.stock += item.quantity
                session.add(dest_product)
            else:
                dest_product = Product(
                    company_id=company_id,
                    branch_id=dest_id,
                    barcode=origin_product.barcode,
                    description=origin_product.description,
                    category=origin_product.category,
                    stock=item.quantity,
                    unit=origin_product.unit,
                    purchase_price=origin_product.purchase_price,
                    sale_price=origin_product.sale_price,
                    is_active=True,
                    min_stock_alert=origin_product.min_stock_alert,
                    tax_included=origin_product.tax_included,
                    tax_rate=origin_product.tax_rate,
                    tax_category=origin_product.tax_category,
                    custom_profit_margin=origin_product.custom_profit_margin,
                )
                session.add(dest_product)
                await session.flush()

            session.add(StockMovement(
                company_id=company_id,
                branch_id=dest_id,
                product_id=dest_product.id,
                user_id=user_id,
                type="Transferencia Ingreso",
                quantity=item.quantity,
                description=f"Transferencia #{transfer.id} ← sucursal origen",
                timestamp=now,
            ))

        transfer.status = TransferStatus.COMPLETED
        transfer.completed_at = now
        transfer.completed_by_id = user_id
        session.add(transfer)
        await session.flush()

        return transfer

    @staticmethod
    async def cancel_transfer(
        session: AsyncSession,
        *,
        transfer_id: int,
        company_id: int,
    ) -> StockTransfer:
        result = await session.exec(
            select(StockTransfer).where(
                StockTransfer.id == transfer_id,
                StockTransfer.company_id == company_id,
            )
        )
        transfer = result.first()
        if not transfer:
            raise TransferError("Transferencia no encontrada.")

        if transfer.status != TransferStatus.PENDING:
            raise TransferError("Solo se pueden cancelar transferencias pendientes.")

        transfer.status = TransferStatus.CANCELLED
        session.add(transfer)
        await session.flush()
        return transfer

    @staticmethod
    async def list_transfers(
        session: AsyncSession,
        *,
        company_id: int,
        status: TransferStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StockTransfer]:
        stmt = (
            select(StockTransfer)
            .where(StockTransfer.company_id == company_id)
            .options(selectinload(StockTransfer.items))
            .order_by(StockTransfer.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status:
            stmt = stmt.where(StockTransfer.status == status)

        result = await session.exec(stmt)
        return list(result.all())
