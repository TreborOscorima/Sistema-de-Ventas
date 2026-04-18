"""Servicio de devoluciones parciales o totales de ventas.

Procesa la devolución revirtiendo stock (variante/lote/producto),
creando registros SaleReturn/SaleReturnItem, y generando un egreso
en CashboxLog para reflejar el reembolso en caja.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlmodel import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Sale,
    SaleItem,
    SaleInstallment,
    SaleReturn,
    SaleReturnItem,
    CashboxLog,
    Client,
    StockMovement,
    Product,
    ProductVariant,
    ProductBatch,
)
from app.enums import SaleStatus
from app.utils.stock import recalculate_stock_totals
from app.utils.tenant import set_tenant_context
from app.utils.timezone import utc_now_naive

logger = logging.getLogger(__name__)


class DuplicateReturnError(ValueError):
    """Se intentó registrar una devolución con un ``idempotency_key`` ya usado.

    El atributo ``sale_return_id`` apunta a la devolución original persistida,
    permitiendo al caller mostrar "devolución ya registrada #N" en lugar de
    reintentar ciegamente.
    """

    def __init__(self, sale_return_id: int):
        super().__init__(f"Duplicate return (sale_return_id={sale_return_id})")
        self.sale_return_id = sale_return_id


@dataclass
class ReturnItemRequest:
    """Un ítem a devolver."""
    sale_item_id: int
    quantity: Decimal


@dataclass
class ReturnResult:
    """Resultado del procesamiento de devolución."""
    success: bool
    sale_return_id: int | None = None
    refund_amount: Decimal = Decimal("0.00")
    error: str = ""
    items_returned: int = 0


def process_return(
    session: Session,
    *,
    sale_id: int,
    company_id: int,
    branch_id: int,
    user_id: int,
    reason: str,
    notes: str,
    items: list[ReturnItemRequest],
    timestamp: datetime | None = None,
    refund_method: str | None = None,
    idempotency_key: str | None = None,
) -> ReturnResult:
    """Procesa una devolución parcial o total.

    Args:
        session: Sesión de DB activa (caller maneja commit/rollback)
        sale_id: ID de la venta original
        company_id, branch_id: Tenant
        user_id: Usuario que procesa la devolución
        reason: Motivo (ReturnReason value)
        notes: Notas adicionales
        items: Lista de ítems a devolver con cantidades
        timestamp: Timestamp del evento (default: utc_now_naive)
        refund_method: Medio de pago del reembolso (efectivo/tarjeta/…); se
            registra como ``CashboxLog.payment_method`` cuando la UI lo
            provee. ``None`` = no informado (casos legacy).
        idempotency_key: Token opaco del frontend para deduplicar doble-click
            y retries. Si existe una devolución previa con la misma clave en
            este tenant, se eleva ``DuplicateReturnError`` con el id original.

    Returns:
        ReturnResult con éxito/error y monto reembolsado

    Raises:
        DuplicateReturnError: ya existe una devolución con ese idempotency_key.
    """
    set_tenant_context(company_id, branch_id)
    try:
        return _process_return_impl(
            session,
            sale_id=sale_id,
            company_id=company_id,
            branch_id=branch_id,
            user_id=user_id,
            reason=reason,
            notes=notes,
            items=items,
            timestamp=timestamp,
            refund_method=refund_method,
            idempotency_key=idempotency_key,
        )
    finally:
        set_tenant_context(None, None)


def _process_return_impl(
    session: Session,
    *,
    sale_id: int,
    company_id: int,
    branch_id: int,
    user_id: int,
    reason: str,
    notes: str,
    items: list[ReturnItemRequest],
    timestamp: datetime | None,
    refund_method: str | None,
    idempotency_key: str | None,
) -> ReturnResult:
    ts = timestamp or utc_now_naive()

    # R1-03: chequeo idempotente pre-flush. Si ya existe devolución con este
    # token para el tenant, devolvemos el id original — el retry/doble-click
    # no crea un duplicado.
    idem_key = (idempotency_key or "").strip() or None
    if idem_key:
        existing = session.exec(
            select(SaleReturn)
            .where(SaleReturn.company_id == company_id)
            .where(SaleReturn.idempotency_key == idem_key)
        ).first()
        if existing:
            raise DuplicateReturnError(existing.id)

    # R1-02: FOR UPDATE para serializar devoluciones concurrentes sobre la
    # misma venta (evita doble reembolso / stock revertido dos veces).
    sale = session.exec(
        select(Sale)
        .where(Sale.id == sale_id)
        .where(Sale.company_id == company_id)
        .where(Sale.branch_id == branch_id)
        .with_for_update()
    ).first()

    if not sale:
        return ReturnResult(success=False, error="Venta no encontrada.")
    # R1-04: bloquear también ventas ya totalmente devueltas.
    if sale.status == SaleStatus.cancelled:
        return ReturnResult(success=False, error="La venta ya fue anulada.")
    if sale.status == SaleStatus.returned:
        return ReturnResult(
            success=False,
            error="La venta ya fue devuelta en su totalidad.",
        )

    if not items:
        return ReturnResult(success=False, error="No se seleccionaron ítems para devolver.")

    # Cargar ítems de la venta
    sale_items_map: dict[int, SaleItem] = {}
    for item in sale.items:
        sale_items_map[item.id] = item

    # Cargar devoluciones previas para validar cantidades
    existing_returns = session.exec(
        select(SaleReturnItem)
        .join(SaleReturn)
        .where(SaleReturn.original_sale_id == sale_id)
        .where(SaleReturn.company_id == company_id)
    ).all()
    already_returned: dict[int, Decimal] = {}
    for er in existing_returns:
        already_returned[er.sale_item_id] = (
            already_returned.get(er.sale_item_id, Decimal("0")) + er.quantity
        )

    # Validar cantidades
    return_items: list[tuple[ReturnItemRequest, SaleItem]] = []
    for req in items:
        si = sale_items_map.get(req.sale_item_id)
        if not si:
            return ReturnResult(
                success=False,
                error=f"Ítem #{req.sale_item_id} no pertenece a esta venta.",
            )
        if req.quantity <= 0:
            continue
        prev = already_returned.get(si.id, Decimal("0"))
        available = (si.quantity or Decimal("0")) - prev
        if req.quantity > available:
            return ReturnResult(
                success=False,
                error=(
                    f"'{si.product_name_snapshot}': se quiere devolver "
                    f"{req.quantity} pero solo quedan {available} disponibles."
                ),
            )
        return_items.append((req, si))

    if not return_items:
        return ReturnResult(success=False, error="Las cantidades a devolver son 0.")

    # Calcular monto de reembolso
    refund_total = Decimal("0.00")
    for req, si in return_items:
        unit_price = si.unit_price or Decimal("0")
        refund_total += (unit_price * req.quantity).quantize(Decimal("0.01"))

    # Crear SaleReturn
    sale_return = SaleReturn(
        original_sale_id=sale_id,
        reason=reason,
        notes=notes,
        refund_amount=refund_total,
        company_id=company_id,
        branch_id=branch_id,
        user_id=user_id,
        timestamp=ts,
        idempotency_key=idem_key,
    )
    session.add(sale_return)
    try:
        session.flush()  # Obtener ID
    except IntegrityError:
        # Race: otro request insertó la misma idempotency_key entre nuestro
        # lookup y el flush. Rollback y re-lookup para devolver el id ganador.
        session.rollback()
        if idem_key:
            winner = session.exec(
                select(SaleReturn)
                .where(SaleReturn.company_id == company_id)
                .where(SaleReturn.idempotency_key == idem_key)
            ).first()
            if winner:
                raise DuplicateReturnError(winner.id)
        raise

    # Recopilar IDs para pre-carga batch
    needed_variant_ids: set[int] = set()
    needed_product_ids: set[int] = set()
    needed_batch_ids: set[int] = set()
    for _, si in return_items:
        if si.product_variant_id:
            needed_variant_ids.add(si.product_variant_id)
        if si.product_id:
            needed_product_ids.add(si.product_id)
        if si.product_batch_id:
            needed_batch_ids.add(si.product_batch_id)

    # Pre-cargar entidades con FOR UPDATE
    variants_map: dict[int, ProductVariant] = {}
    if needed_variant_ids:
        rows = session.exec(
            select(ProductVariant)
            .where(ProductVariant.id.in_(needed_variant_ids))
            .where(ProductVariant.company_id == company_id)
            .where(ProductVariant.branch_id == branch_id)
            .with_for_update()
        ).all()
        variants_map = {v.id: v for v in rows}

    products_map: dict[int, Product] = {}
    if needed_product_ids:
        rows = session.exec(
            select(Product)
            .where(Product.id.in_(needed_product_ids))
            .where(Product.company_id == company_id)
            .where(Product.branch_id == branch_id)
            .with_for_update()
        ).all()
        products_map = {p.id: p for p in rows}

    batches_map: dict[int, ProductBatch] = {}
    if needed_batch_ids:
        rows = session.exec(
            select(ProductBatch)
            .where(ProductBatch.id.in_(needed_batch_ids))
            .where(ProductBatch.company_id == company_id)
            .where(ProductBatch.branch_id == branch_id)
            .with_for_update()
        ).all()
        batches_map = {b.id: b for b in rows}

    # Procesar cada ítem: crear SaleReturnItem + revertir stock
    variants_recalc_batches: set[int] = set()
    products_recalc_variants: set[int] = set()
    products_recalc_batches: set[int] = set()

    for req, si in return_items:
        unit_price = si.unit_price or Decimal("0")
        subtotal = (unit_price * req.quantity).quantize(Decimal("0.01"))

        return_item = SaleReturnItem(
            sale_return_id=sale_return.id,
            sale_item_id=si.id,
            quantity=req.quantity,
            refund_subtotal=subtotal,
            product_id=si.product_id,
            product_variant_id=si.product_variant_id,
            product_batch_id=si.product_batch_id,
        )
        session.add(return_item)

        # Revertir stock (misma lógica que delete_sale en cash_state)
        qty = req.quantity
        if si.product_variant_id:
            variant = variants_map.get(si.product_variant_id)
            if variant:
                if si.product_batch_id:
                    batch = batches_map.get(si.product_batch_id)
                    if batch:
                        batch.stock = (batch.stock or 0) + qty
                        session.add(batch)
                        variants_recalc_batches.add(variant.id)
                        products_recalc_variants.add(variant.product_id)
                    else:
                        variant.stock = (variant.stock or 0) + qty
                        session.add(variant)
                        products_recalc_variants.add(variant.product_id)
                else:
                    variant.stock = (variant.stock or 0) + qty
                    session.add(variant)
                    products_recalc_variants.add(variant.product_id)
        elif si.product_id:
            product = products_map.get(si.product_id)
            if product:
                if si.product_batch_id:
                    batch = batches_map.get(si.product_batch_id)
                    if batch:
                        batch.stock = (batch.stock or 0) + qty
                        session.add(batch)
                        products_recalc_batches.add(product.id)
                    else:
                        product.stock = (product.stock or 0) + qty
                        session.add(product)
                else:
                    product.stock = (product.stock or 0) + qty
                    session.add(product)

        # Movimiento de stock (incluir contexto de kit si aplica)
        desc = f"Devolución venta #{sale_id}: {si.product_name_snapshot}"
        if getattr(si, "kit_product_name", None):
            desc += f" (componente de kit: {si.kit_product_name})"
        movement = StockMovement(
            product_id=si.product_id,
            user_id=user_id,
            type="Devolucion",
            quantity=qty,
            description=desc,
            timestamp=ts,
            company_id=company_id,
            branch_id=branch_id,
        )
        session.add(movement)

    # Recalcular totales de stock
    recalculate_stock_totals(
        session=session,
        company_id=company_id,
        branch_id=branch_id,
        variants_from_batches=variants_recalc_batches,
        products_from_variants=products_recalc_variants,
        products_from_batches=products_recalc_batches,
    )

    # Verificar si la venta quedó totalmente devuelta
    total_returned_after: dict[int, Decimal] = dict(already_returned)
    for req, si in return_items:
        total_returned_after[si.id] = (
            total_returned_after.get(si.id, Decimal("0")) + req.quantity
        )
    all_returned = True
    for si_id, si in sale_items_map.items():
        returned_qty = total_returned_after.get(si_id, Decimal("0"))
        if returned_qty < (si.quantity or Decimal("0")):
            all_returned = False
            break

    if all_returned:
        sale.status = SaleStatus.returned
        session.add(sale)

    # R1-06: en ventas a crédito, el reembolso reduce la deuda del cliente
    # y cancela cuotas pendientes (top-down: número mayor primero, ya que
    # las próximas a vencer son las más urgentes de mantener activas si la
    # devolución es parcial).
    if (
        (sale.payment_condition or "").strip().lower() == "credito"
        and sale.client_id
        and refund_total > 0
    ):
        client = session.exec(
            select(Client)
            .where(Client.id == sale.client_id)
            .where(Client.company_id == company_id)
            .with_for_update()
        ).first()
        if client:
            current = client.current_debt or Decimal("0.00")
            new_debt = current - refund_total
            # Respeta CheckConstraint current_debt >= 0 y evita dejar saldo
            # negativo aunque el refund supere la deuda (caso de pagos
            # parciales previos ya descontados).
            if new_debt < 0:
                new_debt = Decimal("0.00")
            client.current_debt = new_debt.quantize(Decimal("0.01"))
            session.add(client)

        # Cancelar cuotas pendientes absorbiendo el refund de mayor a menor.
        pending_installments = session.exec(
            select(SaleInstallment)
            .where(SaleInstallment.sale_id == sale_id)
            .where(SaleInstallment.company_id == company_id)
            .where(SaleInstallment.status.in_(["pending", "partial"]))
            .order_by(SaleInstallment.number.desc())
            .with_for_update()
        ).all()
        remaining_refund = refund_total
        for inst in pending_installments:
            if remaining_refund <= 0:
                break
            amount = inst.amount or Decimal("0.00")
            paid = inst.paid_amount or Decimal("0.00")
            outstanding = amount - paid
            if outstanding <= 0:
                continue
            if remaining_refund >= outstanding:
                inst.paid_amount = amount
                inst.status = "paid"
                remaining_refund -= outstanding
            else:
                inst.paid_amount = (paid + remaining_refund).quantize(Decimal("0.01"))
                inst.status = "partial"
                remaining_refund = Decimal("0.00")
            session.add(inst)

    # Registrar egreso en CashboxLog (R1-07: payment_method si el UI lo pasa)
    log = CashboxLog(
        company_id=company_id,
        branch_id=branch_id,
        user_id=user_id,
        action="Devolucion",
        amount=refund_total,
        notes=f"Devolución venta #{sale_id} ({len(return_items)} ítems)",
        sale_id=sale_id,
        timestamp=ts,
        payment_method=(refund_method or None),
    )
    session.add(log)

    return ReturnResult(
        success=True,
        sale_return_id=sale_return.id,
        refund_amount=refund_total,
        items_returned=len(return_items),
    )
