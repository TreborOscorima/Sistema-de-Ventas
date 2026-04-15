"""Mixin de Eliminación/Anulación de Ventas y Log Detail."""
import reflex as rx
import logging
from typing import Any

from sqlmodel import select

from app.enums import SaleStatus
from app.models import (
    CashboxLog as CashboxLogModel,
    User as UserModel,
    Sale,
    Product,
    ProductVariant,
    ProductBatch,
    StockMovement,
)
from app.i18n import MSG
from app.utils.sanitization import sanitize_reason, sanitize_reason_preserve_spaces
from app.utils.stock import recalculate_stock_totals

logger = logging.getLogger(__name__)


class DeleteMixin:
    """Detalle de log de caja y anulación de ventas con restauración de stock."""

    @rx.event
    def show_cashbox_log(self, log_id: str):
        if not self.current_user["privileges"]["view_cashbox"]:
            return rx.toast(MSG.PERM_CASH_MGMT, duration=3000)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast(MSG.VAL_COMPANY_UNDEFINED, duration=3000)
        with rx.session() as session:
            log = session.exec(
                select(CashboxLogModel)
                .where(CashboxLogModel.id == int(log_id))
                .where(CashboxLogModel.company_id == company_id)
                .where(CashboxLogModel.branch_id == branch_id)
            ).first()
            if not log:
                return rx.toast(MSG.CASH_RECORD_NOT_FOUND, duration=3000)

            # Obtener username via user_id
            user = session.get(UserModel, log.user_id)
            username = user.username if user else "Unknown"

            self.cashbox_log_selected = {
                "id": str(log.id),
                "action": log.action,
                "timestamp": self._format_event_timestamp(log.timestamp),
                "user": username,
                "opening_amount": log.amount if log.action == "apertura" else 0.0,
                "closing_total": log.amount if log.action == "cierre" else 0.0,
                "totals_by_method": [],
                "notes": log.notes or "",
                "amount": log.amount or 0.0,
                "quantity": 0.0,
                "unit": "",
                "cost": 0.0,
                "formatted_amount": self._format_currency(log.amount or 0),
                "formatted_cost": "",
                "formatted_quantity": "",
            }
            self.cashbox_log_modal_open = True

    @rx.event
    def close_cashbox_log_modal(self):
        self.cashbox_log_modal_open = False
        self.cashbox_log_selected = None

    @rx.event
    def open_sale_delete_modal(self, sale_id: str):
        denial = self._cashbox_guard()
        if denial:
            return denial
        self.sale_to_delete = sale_id
        self.sale_delete_reason = ""
        self.sale_delete_modal_open = True

    @rx.event
    def close_sale_delete_modal(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        self.sale_delete_modal_open = False
        self.sale_to_delete = ""
        self.sale_delete_reason = ""

    @rx.event
    def set_sale_delete_reason(self, value: str):
        denial = self._cashbox_guard()
        if denial:
            return denial
        self.sale_delete_reason = sanitize_reason_preserve_spaces(value)

    @rx.event
    def delete_sale(self):
        denial = self._cashbox_guard()
        if denial:
            return denial
        if not self.current_user["privileges"]["delete_sales"]:
            return rx.toast(MSG.PERM_DELETE_SALE, duration=3000)
        block = self._require_active_subscription()
        if block:
            return block
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast(MSG.VAL_COMPANY_UNDEFINED, duration=3000)
        sale_id = self.sale_to_delete
        reason = sanitize_reason(self.sale_delete_reason).strip()
        if not sale_id:
            return rx.toast(MSG.SALE_SELECT_DELETE, duration=3000)
        if not reason:
            return rx.toast(
                MSG.SALE_ENTER_DELETE_REASON, duration=3000
            )

        try:
            sale_db_id = int(sale_id)
        except ValueError:
            return rx.toast(MSG.VAL_INVALID_SALE_ID, duration=3000)

        with rx.session() as session:
            sale_db = session.exec(
                select(Sale)
                .where(Sale.id == sale_db_id)
                .where(Sale.company_id == company_id)
                .where(Sale.branch_id == branch_id)
            ).first()

            if not sale_db:
                return rx.toast("Venta no encontrada en BD.", duration=3000)
            if sale_db.status == SaleStatus.cancelled:
                return rx.toast("La venta ya fue anulada.", duration=3000)

            try:
                # Marcar como cancelado en BD
                sale_db.status = SaleStatus.cancelled
                sale_db.delete_reason = reason
                session.add(sale_db)

                logs = session.exec(
                    select(CashboxLogModel)
                    .where(CashboxLogModel.sale_id == sale_db_id)
                    .where(CashboxLogModel.company_id == company_id)
                    .where(CashboxLogModel.branch_id == branch_id)
                ).all()
                for log in logs:
                    if log.is_voided:
                        continue
                    log.is_voided = True
                    if reason:
                        suffix = f" | ANULADA: {reason}"
                        if suffix not in (log.notes or ""):
                            log.notes = f"{log.notes or ''}{suffix}".strip()
                    session.add(log)

                # ── Restaurar stock (batch pre-carga para evitar N+1) ──
                needed_variant_ids: set[int] = set()
                needed_product_ids: set[int] = set()
                needed_batch_ids: set[int] = set()
                items_to_restore = []
                for item in sale_db.items:
                    quantity = item.quantity or 0
                    if quantity <= 0:
                        continue
                    items_to_restore.append(item)
                    if item.product_variant_id:
                        needed_variant_ids.add(item.product_variant_id)
                    if item.product_id:
                        needed_product_ids.add(item.product_id)
                    if item.product_batch_id:
                        needed_batch_ids.add(item.product_batch_id)

                # Pre-cargar todos con FOR UPDATE en 3 queries batch
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

                # Restaurar stock usando los mapas pre-cargados
                products_recalc_variants: set[int] = set()
                products_recalc_batches: set[int] = set()
                variants_recalc_batches: set[int] = set()

                for item in items_to_restore:
                    quantity = item.quantity or 0

                    if item.product_variant_id:
                        variant = variants_map.get(item.product_variant_id)
                        if variant:
                            if item.product_batch_id:
                                batch = batches_map.get(item.product_batch_id)
                                if batch:
                                    batch.stock = (batch.stock or 0) + quantity
                                    session.add(batch)
                                    variants_recalc_batches.add(variant.id)
                                    products_recalc_variants.add(variant.product_id)
                                else:
                                    variant.stock = (variant.stock or 0) + quantity
                                    session.add(variant)
                                    products_recalc_variants.add(variant.product_id)
                            else:
                                variant.stock = (variant.stock or 0) + quantity
                                session.add(variant)
                                products_recalc_variants.add(variant.product_id)
                    elif item.product_id:
                        product = products_map.get(item.product_id)
                        if product:
                            if item.product_batch_id:
                                batch = batches_map.get(item.product_batch_id)
                                if batch:
                                    batch.stock = (batch.stock or 0) + quantity
                                    session.add(batch)
                                    products_recalc_batches.add(product.id)
                                else:
                                    product.stock = (product.stock or 0) + quantity
                                    session.add(product)
                            else:
                                product.stock = (product.stock or 0) + quantity
                                session.add(product)

                    # Registrar movimiento de stock
                    movement = StockMovement(
                        product_id=item.product_id,
                        user_id=self.current_user.get("id"),
                        type="Devolucion Venta",
                        quantity=quantity,
                        description=f"Venta anulada #{sale_db.id}: {reason}",
                        timestamp=self._event_timestamp(),
                        company_id=company_id,
                        branch_id=branch_id,
                    )
                    session.add(movement)

                # Recalcular totales de stock (helper centralizado)
                recalculate_stock_totals(
                    session=session,
                    company_id=company_id,
                    branch_id=branch_id,
                    variants_from_batches=variants_recalc_batches,
                    products_from_variants=products_recalc_variants,
                    products_from_batches=products_recalc_batches,
                )
                session.commit()
            except Exception:
                session.rollback()
                logger.exception("Error al anular venta #%s", sale_db_id)
                return rx.toast(
                    "Error al anular la venta. Intente nuevamente.",
                    duration=4000,
                )

        self._cashbox_update_trigger += 1
        self._refresh_cashbox_caches()
        self.close_sale_delete_modal()
        return rx.toast("Venta eliminada correctamente.", duration=3000)
