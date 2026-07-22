"""Mixin de transferencias de stock entre sucursales."""
from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, List

import reflex as rx
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.models import (
    Branch,
    Product,
    ProductVariant,
    StockTransfer,
    StockTransferItem,
)
from app.models.inventory import TransferStatus
from app.services.sale_service import StockError
from app.services.transfer_service import TransferError, TransferService
from app.utils.sanitization import escape_like

logger = logging.getLogger(__name__)


class TransferMixin:
    """Mixin para gestionar transferencias de stock entre sucursales."""

    transfer_modal_open: bool = False
    transfer_dest_branch_id: str = ""
    transfer_notes: str = ""
    transfer_items: List[Dict[str, Any]] = []
    transfer_search_term: str = ""
    transfer_search_results: List[Dict[str, Any]] = []
    transfer_history: List[Dict[str, Any]] = []
    transfer_history_page: int = 1
    transfer_loading: bool = False
    transfer_show_history: bool = False
    transfer_barcode_key: int = 0

    def _fmt_stock(self, value, unit: str) -> str:
        d = Decimal(str(value or 0))
        if self._unit_allows_decimal(unit):
            return str(d.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
        return str(int(d))

    @staticmethod
    def _fmt_qty(value) -> str:
        d = Decimal(str(value or 0))
        if d == d.to_integral_value():
            return str(int(d))
        return str(d.normalize())

    def _product_row(self, p) -> Dict[str, Any]:
        return {
            "id": p.id,
            "key": f"{p.id}:0",
            "variant_id": None,
            "variant_label": "",
            "barcode": p.barcode or "",
            "description": p.description,
            "stock": self._fmt_stock(p.stock, p.unit),
            "unit": p.unit,
        }

    def _variant_row(self, p, v) -> Dict[str, Any]:
        label = " / ".join(x for x in (v.size, v.color) if x) or (v.sku or "")
        return {
            "id": p.id,
            "key": f"{p.id}:{v.id}",
            "variant_id": v.id,
            "variant_label": label,
            "barcode": v.sku or "",
            "description": p.description,
            "stock": self._fmt_stock(v.stock, p.unit),
            "unit": p.unit,
        }

    def _add_or_inc_row(self, row: Dict[str, Any]):
        """Agrega la fila (producto o variante) al carrito, o incrementa +1 si ya está."""
        for item in self.transfer_items:
            if item["key"] == row["key"]:
                new_qty = self._fmt_qty(Decimal(str(item["quantity"] or "0")) + 1)
                self.transfer_items = [
                    {**i, "quantity": new_qty} if i["key"] == row["key"] else i
                    for i in self.transfer_items
                ]
                label = row["description"]
                if row["variant_label"]:
                    label = f"{label} ({row['variant_label']})"
                return self.add_notification(f"'{label}' +1 (total: {new_qty}).", "info")

        self.transfer_items = [
            *self.transfer_items,
            {
                "product_id": row["id"],
                "key": row["key"],
                "variant_id": row["variant_id"],
                "variant_label": row["variant_label"],
                "barcode": row["barcode"],
                "description": row["description"],
                "available_stock": row["stock"],
                "unit": row["unit"],
                "quantity": "1",
            },
        ]
        self.transfer_search_term = ""
        self.transfer_search_results = []

    @rx.event
    def transfer_open_modal(self):
        block = self._require_active_subscription()
        if block:
            return block
        self.transfer_modal_open = True
        self.transfer_dest_branch_id = ""
        self.transfer_notes = ""
        self.transfer_items = []
        self.transfer_search_term = ""
        self.transfer_search_results = []

    @rx.event
    def transfer_close_modal(self):
        self.transfer_modal_open = False

    @rx.event
    def transfer_set_dest_branch(self, value: str):
        self.transfer_dest_branch_id = value

    @rx.event
    def transfer_set_notes(self, value: str):
        self.transfer_notes = value[:500]

    @rx.event
    def transfer_search_products(self, term: str):
        self.transfer_search_term = term
        if not term or len(term) < 2:
            self.transfer_search_results = []
            return

        try:
            with self.scoped_session() as ctx:
                escaped = escape_like(term)
                prods = ctx.session.exec(
                    select(Product)
                    .where(
                        Product.company_id == ctx.company_id,
                        Product.branch_id == ctx.branch_id,
                        Product.is_active == True,  # noqa: E712
                        (Product.description.ilike(f"%{escaped}%"))
                        | (Product.barcode.ilike(f"%{escaped}%")),
                    )
                    .limit(10)
                ).all()

                results: List[Dict[str, Any]] = []
                for p in prods:
                    variants = ctx.session.exec(
                        select(ProductVariant).where(
                            ProductVariant.company_id == ctx.company_id,
                            ProductVariant.branch_id == ctx.branch_id,
                            ProductVariant.product_id == p.id,
                        )
                    ).all()
                    if variants:
                        # Un producto con variantes se expande: cada variante con
                        # stock es una unidad de stock transferible inequívoca.
                        for v in variants:
                            if Decimal(str(v.stock or 0)) > 0:
                                results.append(self._variant_row(p, v))
                    elif Decimal(str(p.stock or 0)) > 0:
                        results.append(self._product_row(p))

                self.transfer_search_results = results[:15]
        except ValueError:
            return

    @rx.event
    def transfer_barcode_submit(self, form_data: dict):
        barcode = (form_data.get("barcode") or "").strip()
        self.transfer_barcode_key += 1
        if not barcode:
            return

        try:
            with self.scoped_session() as ctx:
                # 1) Variante por SKU (el escaneo de una talla/color concreta).
                variant = ctx.session.exec(
                    select(ProductVariant).where(
                        ProductVariant.company_id == ctx.company_id,
                        ProductVariant.branch_id == ctx.branch_id,
                        ProductVariant.sku == barcode,
                    )
                ).first()
                if variant:
                    prod = ctx.session.get(Product, variant.product_id)
                    if not prod or not prod.is_active:
                        return self.add_notification(
                            f"No se encontró producto con código '{barcode}'.", "warning"
                        )
                    if Decimal(str(variant.stock or 0)) <= 0:
                        return self.add_notification(
                            f"'{prod.description}' no tiene stock en esa variante.", "warning"
                        )
                    return self._add_or_inc_row(self._variant_row(prod, variant))

                # 2) Producto por código de barras.
                prod = ctx.session.exec(
                    select(Product).where(
                        Product.company_id == ctx.company_id,
                        Product.branch_id == ctx.branch_id,
                        Product.is_active == True,  # noqa: E712
                        Product.barcode == barcode,
                    )
                ).first()

                if not prod:
                    return self.add_notification(
                        f"No se encontró producto con código '{barcode}'.", "warning"
                    )

                has_variants = ctx.session.exec(
                    select(ProductVariant.id).where(
                        ProductVariant.company_id == ctx.company_id,
                        ProductVariant.branch_id == ctx.branch_id,
                        ProductVariant.product_id == prod.id,
                    ).limit(1)
                ).first()
                if has_variants:
                    return self.add_notification(
                        f"'{prod.description}' tiene variantes; búsquelo y elija la talla/color.",
                        "warning",
                    )

                if prod.stock <= 0:
                    return self.add_notification(
                        f"'{prod.description}' no tiene stock disponible.", "warning"
                    )

                return self._add_or_inc_row(self._product_row(prod))
        except ValueError:
            return

    @rx.event
    def transfer_add_item(self, key: str):
        for item in self.transfer_items:
            if item["key"] == key:
                return self.add_notification("Producto ya agregado.", "warning")

        row = None
        for r in self.transfer_search_results:
            if r["key"] == key:
                row = r
                break
        if not row:
            return

        return self._add_or_inc_row(row)

    @rx.event
    def transfer_remove_item(self, key: str):
        self.transfer_items = [
            i for i in self.transfer_items if i["key"] != key
        ]

    @rx.event
    def transfer_update_qty(self, key: str, qty: str):
        new_items = []
        for item in self.transfer_items:
            if item["key"] == key:
                item = {**item, "quantity": qty}
            new_items.append(item)
        self.transfer_items = new_items

    @rx.event
    def transfer_increment_qty(self, key: str):
        new_items = []
        for item in self.transfer_items:
            if item["key"] == key:
                try:
                    current = Decimal(str(item["quantity"] or "0"))
                except (InvalidOperation, ValueError):
                    current = Decimal("1")
                try:
                    stock = Decimal(str(item["available_stock"] or "0"))
                except (InvalidOperation, ValueError):
                    stock = Decimal("999999")
                new_val = min(current + 1, stock) if stock > 0 else current + 1
                item = {**item, "quantity": self._fmt_qty(new_val)}
            new_items.append(item)
        self.transfer_items = new_items

    @rx.event
    def transfer_decrement_qty(self, key: str):
        new_items = []
        for item in self.transfer_items:
            if item["key"] == key:
                try:
                    current = Decimal(str(item["quantity"] or "0"))
                except (InvalidOperation, ValueError):
                    current = Decimal("1")
                new_val = current - 1
                if new_val < 1:
                    new_val = Decimal("1")
                item = {**item, "quantity": self._fmt_qty(new_val)}
            new_items.append(item)
        self.transfer_items = new_items

    @rx.event
    async def transfer_submit(self):
        if not self.transfer_items:
            yield self.add_notification("Agregue al menos un producto.", "warning")
            return

        if not self.transfer_dest_branch_id:
            yield self.add_notification("Seleccione la sucursal destino.", "warning")
            return

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return

        try:
            dest_id = int(self.transfer_dest_branch_id)
        except (TypeError, ValueError):
            yield self.add_notification("Sucursal destino inválida.", "error")
            return

        if dest_id == branch_id:
            yield self.add_notification(
                "La sucursal destino no puede ser la misma que la actual.", "warning"
            )
            return

        items_data = []
        for item in self.transfer_items:
            try:
                qty = Decimal(str(item["quantity"]))
            except (InvalidOperation, TypeError, ValueError):
                yield self.add_notification(
                    f"Cantidad inválida para '{item['description']}'.", "error"
                )
                return
            if qty <= 0:
                yield self.add_notification(
                    f"La cantidad de '{item['description']}' debe ser mayor a 0.", "error"
                )
                return
            items_data.append({
                "product_id": item["product_id"],
                "quantity": qty,
                "variant_id": item.get("variant_id"),
            })

        self.transfer_loading = True
        yield

        try:
            from app.utils.db import AsyncSessionLocal
            from app.utils.tenant import tenant_bypass

            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    transfer = await TransferService.create_transfer(
                        session,
                        company_id=company_id,
                        origin_branch_id=branch_id,
                        destination_branch_id=dest_id,
                        items=items_data,
                        user_id=self.current_user.get("id"),
                        notes=self.transfer_notes,
                    )
                    transfer = await TransferService.execute_transfer(
                        session,
                        transfer_id=transfer.id,
                        company_id=company_id,
                        user_id=self.current_user.get("id"),
                    )
                    await session.commit()

            self.transfer_modal_open = False
            self.transfer_items = []
            self._inventory_update_trigger += 1
            yield self.add_notification(
                f"Transferencia #{transfer.id} completada exitosamente.", "success"
            )
            yield type(self).refresh_inventory_cache
        except (TransferError, StockError) as e:
            yield self.add_notification(str(e), "error")
        except Exception:
            logger.exception("Error en transferencia de stock")
            yield self.add_notification("Error al procesar la transferencia.", "error")
        finally:
            self.transfer_loading = False

    @rx.event
    async def transfer_load_history(self):
        company_id = self._company_id()
        if not company_id:
            return

        self.transfer_loading = True
        yield

        try:
            from app.utils.db import AsyncSessionLocal
            from app.utils.tenant import tenant_bypass

            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    transfers = await TransferService.list_transfers(
                        session,
                        company_id=company_id,
                        limit=50,
                    )

                    self.transfer_history = []
                    for t in transfers:
                        origin_name = ""
                        dest_name = ""
                        origin = await session.get(Branch, t.origin_branch_id)
                        dest = await session.get(Branch, t.destination_branch_id)
                        if origin:
                            origin_name = origin.name
                        if dest:
                            dest_name = dest.name

                        items_summary = ", ".join(
                            f"{i.product_name_snapshot} ({'×'}{i.quantity})"
                            for i in t.items
                        )
                        self.transfer_history.append({
                            "id": t.id,
                            "origin": origin_name,
                            "destination": dest_name,
                            "status": t.status.value,
                            "items_summary": items_summary,
                            "items_count": len(t.items),
                            "notes": t.notes,
                            "created_at": t.created_at.strftime("%d/%m/%Y %H:%M") if t.created_at else "",
                            "completed_at": t.completed_at.strftime("%d/%m/%Y %H:%M") if t.completed_at else "",
                        })
        except Exception:
            logger.exception("Error cargando historial de transferencias")
        finally:
            self.transfer_loading = False

    @rx.event
    def transfer_toggle_history(self):
        self.transfer_show_history = not self.transfer_show_history
        if self.transfer_show_history:
            return type(self).transfer_load_history
