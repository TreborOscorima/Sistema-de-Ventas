"""Servicio de transferencias de stock entre sucursales.

Ejecuta la transferencia atómicamente respetando la MISMA jerarquía de
verdad que ``sale_service``: **lote > variante > producto**.

- Con lotes: deducción FEFO en origen y consolidación del lote (mismo
  ``batch_number`` + ``expiration_date``) en destino → el vencimiento viaja
  con la mercadería.
- Con variantes: mueve stock de la variante concreta (por SKU); crea la
  variante en destino si no existe.
- Simple: mueve ``product.stock`` directo.

``product.stock`` es siempre un valor DERIVADO (SUM de variantes/lotes) y se
recalcula tras cada mutación, igual que en la venta. Todo bajo
``with_for_update()`` para evitar lost-updates bajo concurrencia.
"""
import logging
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.models import (
    Branch,
    Product,
    ProductBatch,
    ProductVariant,
    StockMovement,
    StockTransfer,
    StockTransferItem,
    Unit,
)
from app.models.inventory import TransferStatus
from app.services.sale_service import (
    StockError,
    _deduct_from_batches,
    _round_quantity,
    _sum_batch_stock,
)
from app.utils.timezone import utc_now_naive

logger = logging.getLogger(__name__)


class TransferError(Exception):
    pass


def _batch_query(company_id: int, branch_id: int, *, product_id, variant_id):
    """Query FEFO de lotes con stock del dueño (variante o producto)."""
    stmt = select(ProductBatch).where(
        ProductBatch.company_id == company_id,
        ProductBatch.branch_id == branch_id,
        ProductBatch.stock > 0,
    )
    if variant_id is not None:
        stmt = stmt.where(ProductBatch.product_variant_id == variant_id)
    else:
        stmt = stmt.where(
            ProductBatch.product_id == product_id,
            ProductBatch.product_variant_id.is_(None),
        )
    return stmt.order_by(
        ProductBatch.expiration_date.is_(None),
        ProductBatch.expiration_date.asc(),
        ProductBatch.id.asc(),
    )


class TransferService:
    """Operaciones de transferencia de stock entre sucursales."""

    @staticmethod
    async def _decimal_units(session, company_id, branch_id) -> dict:
        units = (
            await session.exec(
                select(Unit).where(
                    Unit.company_id == company_id,
                    Unit.branch_id == branch_id,
                )
            )
        ).all()
        return {u.name.strip().lower(): u.allows_decimal for u in units}

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

        decimal_units = await TransferService._decimal_units(
            session, company_id, origin_branch_id
        )

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

            product = (
                await session.exec(
                    select(Product).where(
                        Product.id == product_id,
                        Product.company_id == company_id,
                        Product.branch_id == origin_branch_id,
                    )
                )
            ).first()
            if not product:
                raise TransferError(f"Producto ID {product_id} no encontrado en sucursal de origen.")

            allows_decimal = decimal_units.get((product.unit or "").strip().lower(), False)

            variant = None
            if variant_id is not None:
                variant = (
                    await session.exec(
                        select(ProductVariant).where(
                            ProductVariant.id == variant_id,
                            ProductVariant.company_id == company_id,
                            ProductVariant.branch_id == origin_branch_id,
                            ProductVariant.product_id == product_id,
                        )
                    )
                ).first()
                if not variant:
                    raise TransferError(
                        f"Variante ID {variant_id} no encontrada en sucursal de origen."
                    )

            # Stock disponible del dueño real (lote > variante > producto).
            available = await TransferService._available_stock(
                session,
                company_id=company_id,
                branch_id=origin_branch_id,
                product=product,
                variant=variant,
                allows_decimal=allows_decimal,
            )
            if available < quantity:
                name = variant.sku if variant else product.description
                raise TransferError(
                    f"Stock insuficiente de '{name}': "
                    f"disponible {available}, solicitado {quantity}."
                )

            ti = StockTransferItem(
                transfer_id=transfer.id,
                product_id=product_id,
                product_variant_id=variant_id,
                quantity=quantity,
                product_name_snapshot=(
                    f"{product.description} ({variant.size or ''} {variant.color or ''})".strip()
                    if variant
                    else product.description
                ),
            )
            session.add(ti)

        await session.flush()
        return transfer

    @staticmethod
    async def _available_stock(
        session, *, company_id, branch_id, product, variant, allows_decimal
    ) -> Decimal:
        batches = (
            await session.exec(
                _batch_query(
                    company_id,
                    branch_id,
                    product_id=product.id,
                    variant_id=variant.id if variant else None,
                )
            )
        ).all()
        if batches:
            return _sum_batch_stock(batches, allows_decimal)
        if variant:
            return _round_quantity(variant.stock, allows_decimal)
        return _round_quantity(product.stock, allows_decimal)

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

        # Nombres de sucursal para descripciones de kardex auto-explicativas.
        origin_branch = await session.get(Branch, origin_id)
        dest_branch = await session.get(Branch, dest_id)
        origin_name = origin_branch.name if origin_branch else f"sucursal {origin_id}"
        dest_name = dest_branch.name if dest_branch else f"sucursal {dest_id}"

        decimal_units = await TransferService._decimal_units(session, company_id, origin_id)
        # Productos cuyo agregado debe recalcularse desde variantes al final.
        origin_products_recalc: set[int] = set()
        dest_products_recalc: set[int] = set()

        for item in transfer.items:
            # ── ORIGEN: bloquear producto + (variante) + lotes ──
            origin_product = (
                await session.exec(
                    select(Product)
                    .where(
                        Product.id == item.product_id,
                        Product.company_id == company_id,
                        Product.branch_id == origin_id,
                    )
                    .with_for_update()
                )
            ).first()
            if not origin_product:
                raise TransferError(
                    f"Producto '{item.product_name_snapshot}' ya no existe en sucursal origen."
                )

            allows_decimal = decimal_units.get(
                (origin_product.unit or "").strip().lower(), False
            )
            qty = _round_quantity(item.quantity, allows_decimal)

            origin_variant = None
            if item.product_variant_id is not None:
                origin_variant = (
                    await session.exec(
                        select(ProductVariant)
                        .where(
                            ProductVariant.id == item.product_variant_id,
                            ProductVariant.company_id == company_id,
                            ProductVariant.branch_id == origin_id,
                        )
                        .with_for_update()
                    )
                ).first()
                if not origin_variant:
                    raise TransferError(
                        f"Variante de '{item.product_name_snapshot}' ya no existe en origen."
                    )

            origin_batches = (
                await session.exec(
                    _batch_query(
                        company_id,
                        origin_id,
                        product_id=origin_product.id,
                        variant_id=origin_variant.id if origin_variant else None,
                    ).with_for_update()
                )
            ).all()

            # Deducción respetando la jerarquía + captura de lo tomado por lote.
            moved_batches: list[tuple[str, object, Decimal]] = []
            if origin_batches:
                before = {b.id: _round_quantity(b.stock, allows_decimal) for b in origin_batches}
                used = _deduct_from_batches(origin_batches, qty, allows_decimal)
                for b in used:
                    taken = before[b.id] - _round_quantity(b.stock, allows_decimal)
                    if taken > 0:
                        moved_batches.append((b.batch_number, b.expiration_date, taken))
                    session.add(b)
                if origin_variant:
                    origin_variant.stock = _sum_batch_stock(origin_batches, allows_decimal)
                    session.add(origin_variant)
                    origin_products_recalc.add(origin_product.id)
                else:
                    origin_product.stock = _sum_batch_stock(origin_batches, allows_decimal)
                    session.add(origin_product)
            elif origin_variant:
                new_stock = _round_quantity(origin_variant.stock, allows_decimal) - qty
                if new_stock < 0:
                    raise TransferError(
                        f"Stock insuficiente de '{origin_variant.sku}' (concurrencia detectada)."
                    )
                origin_variant.stock = new_stock
                session.add(origin_variant)
                origin_products_recalc.add(origin_product.id)
            else:
                new_stock = _round_quantity(origin_product.stock, allows_decimal) - qty
                if new_stock < 0:
                    raise TransferError(
                        f"Stock insuficiente de '{origin_product.description}' "
                        f"(concurrencia detectada)."
                    )
                origin_product.stock = new_stock
                session.add(origin_product)

            session.add(StockMovement(
                company_id=company_id,
                branch_id=origin_id,
                product_id=origin_product.id,
                user_id=user_id,
                type="Transferencia Salida",
                quantity=-qty,
                description=f"Transferencia #{transfer.id} · hacia {dest_name}",
                timestamp=now,
            ))

            # ── DESTINO: resolver/crear producto (+variante) espejo ──
            dest_product = await TransferService._resolve_dest_product(
                session,
                company_id=company_id,
                dest_id=dest_id,
                origin_product=origin_product,
            )

            dest_variant = None
            if origin_variant is not None:
                dest_variant = await TransferService._resolve_dest_variant(
                    session,
                    company_id=company_id,
                    dest_id=dest_id,
                    dest_product=dest_product,
                    origin_variant=origin_variant,
                )

            if moved_batches:
                await TransferService._apply_dest_batches(
                    session,
                    company_id=company_id,
                    dest_id=dest_id,
                    dest_product=dest_product,
                    dest_variant=dest_variant,
                    moved_batches=moved_batches,
                    allows_decimal=allows_decimal,
                )
                if dest_variant:
                    dest_products_recalc.add(dest_product.id)
            elif dest_variant is not None:
                dest_variant.stock = _round_quantity(dest_variant.stock, allows_decimal) + qty
                session.add(dest_variant)
                dest_products_recalc.add(dest_product.id)
            else:
                dest_product.stock = _round_quantity(dest_product.stock, allows_decimal) + qty
                session.add(dest_product)

            session.add(StockMovement(
                company_id=company_id,
                branch_id=dest_id,
                product_id=dest_product.id,
                user_id=user_id,
                type="Transferencia Ingreso",
                quantity=qty,
                description=f"Transferencia #{transfer.id} · desde {origin_name}",
                timestamp=now,
            ))

        # Recalcular product.stock = SUM(variantes) donde hubo variantes.
        await session.flush()
        await TransferService._recalc_products_from_variants(
            session, company_id, origin_id, origin_products_recalc, decimal_units
        )
        await TransferService._recalc_products_from_variants(
            session, company_id, dest_id, dest_products_recalc, decimal_units
        )

        transfer.status = TransferStatus.COMPLETED
        transfer.completed_at = now
        transfer.completed_by_id = user_id
        session.add(transfer)
        await session.flush()

        return transfer

    @staticmethod
    async def _resolve_dest_product(session, *, company_id, dest_id, origin_product) -> Product:
        dest_query = select(Product).where(
            Product.company_id == company_id,
            Product.branch_id == dest_id,
            Product.is_active == True,  # noqa: E712
        )
        if origin_product.barcode:
            dest_query = dest_query.where(Product.barcode == origin_product.barcode)
        else:
            dest_query = dest_query.where(
                Product.description == origin_product.description,
                Product.barcode == "",
            )
        dest_product = (await session.exec(dest_query.with_for_update())).first()
        if dest_product:
            return dest_product

        dest_product = Product(
            company_id=company_id,
            branch_id=dest_id,
            barcode=origin_product.barcode,
            description=origin_product.description,
            category=origin_product.category,
            stock=Decimal("0.0000"),
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
        return dest_product

    @staticmethod
    async def _resolve_dest_variant(
        session, *, company_id, dest_id, dest_product, origin_variant
    ) -> ProductVariant:
        dest_variant = (
            await session.exec(
                select(ProductVariant)
                .where(
                    ProductVariant.company_id == company_id,
                    ProductVariant.branch_id == dest_id,
                    ProductVariant.sku == origin_variant.sku,
                )
                .with_for_update()
            )
        ).first()
        if dest_variant:
            return dest_variant

        dest_variant = ProductVariant(
            company_id=company_id,
            branch_id=dest_id,
            product_id=dest_product.id,
            sku=origin_variant.sku,
            size=origin_variant.size,
            color=origin_variant.color,
            stock=Decimal("0.0000"),
            min_stock_alert=origin_variant.min_stock_alert,
            sale_price=origin_variant.sale_price,
        )
        session.add(dest_variant)
        await session.flush()
        return dest_variant

    @staticmethod
    async def _apply_dest_batches(
        session, *, company_id, dest_id, dest_product, dest_variant, moved_batches, allows_decimal
    ) -> None:
        variant_id = dest_variant.id if dest_variant else None
        for batch_number, expiration_date, taken in moved_batches:
            batch_stmt = select(ProductBatch).where(
                ProductBatch.company_id == company_id,
                ProductBatch.branch_id == dest_id,
                ProductBatch.batch_number == batch_number,
            )
            if variant_id is not None:
                batch_stmt = batch_stmt.where(
                    ProductBatch.product_variant_id == variant_id
                )
            else:
                batch_stmt = batch_stmt.where(
                    ProductBatch.product_id == dest_product.id,
                    ProductBatch.product_variant_id.is_(None),
                )
            dest_batch = (await session.exec(batch_stmt.with_for_update())).first()
            if dest_batch:
                dest_batch.stock = _round_quantity(dest_batch.stock, allows_decimal) + taken
                if expiration_date:
                    dest_batch.expiration_date = expiration_date
            else:
                dest_batch = ProductBatch(
                    company_id=company_id,
                    branch_id=dest_id,
                    batch_number=batch_number,
                    expiration_date=expiration_date,
                    stock=taken,
                    product_id=None if variant_id is not None else dest_product.id,
                    product_variant_id=variant_id,
                )
            session.add(dest_batch)

        await session.flush()
        # Recalcular el dueño (variante o producto) desde sus lotes.
        owner_batches = (
            await session.exec(
                select(ProductBatch).where(
                    ProductBatch.company_id == company_id,
                    ProductBatch.branch_id == dest_id,
                    (
                        ProductBatch.product_variant_id == variant_id
                        if variant_id is not None
                        else (
                            (ProductBatch.product_id == dest_product.id)
                            & (ProductBatch.product_variant_id.is_(None))
                        )
                    ),
                )
            )
        ).all()
        total = _sum_batch_stock(owner_batches, allows_decimal)
        if dest_variant:
            dest_variant.stock = total
            session.add(dest_variant)
        else:
            dest_product.stock = total
            session.add(dest_product)

    @staticmethod
    async def _recalc_products_from_variants(
        session, company_id, branch_id, product_ids, decimal_units
    ) -> None:
        for product_id in product_ids:
            product = (
                await session.exec(
                    select(Product).where(
                        Product.id == product_id,
                        Product.company_id == company_id,
                        Product.branch_id == branch_id,
                    )
                )
            ).first()
            if not product:
                continue
            total_row = (
                await session.exec(
                    select(func.coalesce(func.sum(ProductVariant.stock), 0)).where(
                        ProductVariant.product_id == product_id,
                        ProductVariant.company_id == company_id,
                        ProductVariant.branch_id == branch_id,
                    )
                )
            ).first()
            if total_row is None:
                total_stock = Decimal("0.0000")
            elif isinstance(total_row, tuple):
                total_stock = total_row[0]
            else:
                total_stock = total_row
            allows_decimal = decimal_units.get((product.unit or "").strip().lower(), False)
            product.stock = _round_quantity(total_stock, allows_decimal)
            session.add(product)

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
