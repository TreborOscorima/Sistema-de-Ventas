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
    StockTransfer,
    StockTransferItem,
)
from app.models.inventory import TransferStatus
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
                        Product.stock > 0,
                        (Product.description.ilike(f"%{escaped}%"))
                        | (Product.barcode.ilike(f"%{escaped}%")),
                    )
                    .limit(10)
                ).all()

                self.transfer_search_results = [
                    {
                        "id": p.id,
                        "barcode": p.barcode or "",
                        "description": p.description,
                        "stock": self._fmt_stock(p.stock, p.unit),
                        "unit": p.unit,
                    }
                    for p in prods
                ]
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
                prod = ctx.session.exec(
                    select(Product)
                    .where(
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

                if prod.stock <= 0:
                    return self.add_notification(
                        f"'{prod.description}' no tiene stock disponible.", "warning"
                    )

                for item in self.transfer_items:
                    if item["product_id"] == prod.id:
                        new_qty = int(item["quantity"]) + 1
                        self.transfer_items = [
                            {**i, "quantity": str(new_qty)}
                            if i["product_id"] == prod.id
                            else i
                            for i in self.transfer_items
                        ]
                        return self.add_notification(
                            f"'{prod.description}' +1 (total: {new_qty}).", "info"
                        )

                self.transfer_items = [
                    *self.transfer_items,
                    {
                        "product_id": prod.id,
                        "barcode": prod.barcode or "",
                        "description": prod.description,
                        "available_stock": self._fmt_stock(prod.stock, prod.unit),
                        "unit": prod.unit,
                        "quantity": "1",
                    },
                ]
        except ValueError:
            return

    @rx.event
    def transfer_add_item(self, product_id: int):
        for item in self.transfer_items:
            if item["product_id"] == product_id:
                return self.add_notification("Producto ya agregado.", "warning")

        prod = None
        for r in self.transfer_search_results:
            if r["id"] == product_id:
                prod = r
                break
        if not prod:
            return

        self.transfer_items = [
            *self.transfer_items,
            {
                "product_id": prod["id"],
                "barcode": prod["barcode"],
                "description": prod["description"],
                "available_stock": prod["stock"],  # already formatted by search
                "unit": prod["unit"],
                "quantity": "1",
            },
        ]
        self.transfer_search_term = ""
        self.transfer_search_results = []

    @rx.event
    def transfer_remove_item(self, product_id: int):
        self.transfer_items = [
            i for i in self.transfer_items if i["product_id"] != product_id
        ]

    @rx.event
    def transfer_update_qty(self, product_id: int, qty: str):
        new_items = []
        for item in self.transfer_items:
            if item["product_id"] == product_id:
                item = {**item, "quantity": qty}
            new_items.append(item)
        self.transfer_items = new_items

    @rx.event
    def transfer_increment_qty(self, product_id: int):
        new_items = []
        for item in self.transfer_items:
            if item["product_id"] == product_id:
                current = int(item["quantity"]) if item["quantity"].isdigit() else 1
                stock = int(float(item["available_stock"])) if item["available_stock"] else 9999
                new_val = min(current + 1, stock)
                item = {**item, "quantity": str(new_val)}
            new_items.append(item)
        self.transfer_items = new_items

    @rx.event
    def transfer_decrement_qty(self, product_id: int):
        new_items = []
        for item in self.transfer_items:
            if item["product_id"] == product_id:
                current = int(item["quantity"]) if item["quantity"].isdigit() else 1
                new_val = max(current - 1, 1)
                item = {**item, "quantity": str(new_val)}
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
            yield type(self).load_inventory_page
        except TransferError as e:
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
