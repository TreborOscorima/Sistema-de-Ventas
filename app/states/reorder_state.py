"""Estado de Reposición Automática — Órdenes de compra sugeridas por stock bajo.

Gestiona el flujo:
1. Detectar productos bajo umbral (vía reorder_service)
2. Agrupar por proveedor preferido
3. Permitir al usuario crear PurchaseOrders en estado 'draft'
4. Transiciones: draft → sent → received | cancelled
"""
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import reflex as rx

from app.models import PurchaseOrder, PurchaseOrderStatus
from app.services.reorder_service import (
    ReorderSuggestion,
    cancel_purchase_order,
    create_draft_purchase_order,
    list_purchase_orders,
    mark_purchase_order_sent,
    suggest_reorders_by_supplier,
)
from app.utils.tenant import set_tenant_context
from .mixin_state import MixinState

logger = logging.getLogger(__name__)


def _suggestion_from_dict(d: Dict[str, Any]) -> ReorderSuggestion:
    """Reconstruye una ReorderSuggestion desde el payload serializado del estado."""
    return ReorderSuggestion(
        product_id=int(d["product_id"]),
        barcode=str(d["barcode"]),
        description=str(d["description"]),
        current_stock=Decimal(str(d["current_stock"])),
        min_stock_alert=Decimal(str(d["min_stock_alert"])),
        suggested_quantity=Decimal(str(d["suggested_quantity"])),
        unit=str(d["unit"]),
        unit_cost=Decimal(str(d["unit_cost"])),
        default_supplier_id=d.get("default_supplier_id"),
    )


class ReorderState(MixinState):
    """Estado de reposición automática por stock bajo."""

    # ── Sugerencias en memoria ──
    reorder_groups: List[Dict[str, Any]] = []
    reorder_loading: bool = False
    reorder_last_error: str = ""

    # ── Listado de POs existentes ──
    purchase_orders_list: List[Dict[str, Any]] = []
    po_status_filter: str = "all"  # "all" | draft | sent | received | cancelled

    # ── Modal confirmación ──
    reorder_confirm_open: bool = False
    reorder_confirm_supplier_id: int = 0
    reorder_confirm_supplier_name: str = ""
    reorder_confirm_items: List[Dict[str, Any]] = []
    reorder_confirm_total: float = 0.0
    reorder_confirm_notes: str = ""

    @rx.event
    def load_reorder_suggestions(self):
        """Escanea productos bajo umbral y arma grupos por proveedor."""
        if not hasattr(self, "current_user") or not self.current_user:
            return rx.toast("Sesión requerida.", duration=3000)
        if not self.current_user.get("privileges", {}).get("create_ingresos"):
            return rx.toast(
                "Sin permiso para gestionar órdenes de compra.", duration=3000
            )

        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return rx.toast("Tenant no definido.", duration=3000)

        self.reorder_loading = True
        self.reorder_last_error = ""
        try:
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                groups = suggest_reorders_by_supplier(
                    session, company_id, branch_id
                )
            self.reorder_groups = [g.to_dict() for g in groups]
            if not self.reorder_groups:
                return rx.toast(
                    "No hay productos bajo umbral de reposición.", duration=3000
                )
            return rx.toast(
                f"{len(self.reorder_groups)} proveedores con productos a reponer.",
                duration=3000,
            )
        except Exception as exc:
            logger.exception("load_reorder_suggestions failed")
            self.reorder_last_error = str(exc)
            return rx.toast(
                f"Error al cargar sugerencias: {exc}", duration=4000
            )
        finally:
            self.reorder_loading = False

    @rx.event
    def open_reorder_confirm_modal(self, supplier_id: int):
        """Abre el modal para confirmar/editar una PO para un proveedor."""
        group = next(
            (g for g in self.reorder_groups if g.get("supplier_id") == supplier_id),
            None,
        )
        if group is None:
            return rx.toast("Proveedor no encontrado.", duration=3000)
        if not supplier_id:
            return rx.toast(
                "Asigne un proveedor al producto antes de crear la PO.",
                duration=3000,
            )

        self.reorder_confirm_open = True
        self.reorder_confirm_supplier_id = supplier_id
        self.reorder_confirm_supplier_name = group.get("supplier_name", "")
        self.reorder_confirm_items = [dict(it) for it in group.get("items", [])]
        self.reorder_confirm_total = float(group.get("total_estimated", 0))
        self.reorder_confirm_notes = ""

    @rx.event
    def close_reorder_confirm_modal(self):
        self.reorder_confirm_open = False
        self.reorder_confirm_supplier_id = 0
        self.reorder_confirm_supplier_name = ""
        self.reorder_confirm_items = []
        self.reorder_confirm_total = 0.0
        self.reorder_confirm_notes = ""

    @rx.event
    def set_reorder_confirm_notes(self, value: str):
        self.reorder_confirm_notes = str(value or "")[:500]

    @rx.event
    def update_confirm_item_quantity(self, index: int, value: str):
        """Permite editar manualmente la cantidad sugerida antes de confirmar."""
        try:
            idx = int(index)
            new_qty = Decimal(str(value or "0"))
        except Exception:
            return rx.toast("Cantidad inválida.", duration=2500)
        if idx < 0 or idx >= len(self.reorder_confirm_items):
            return
        if new_qty <= 0:
            return rx.toast("La cantidad debe ser positiva.", duration=2500)

        item = dict(self.reorder_confirm_items[idx])
        item["suggested_quantity"] = float(new_qty)
        unit_cost = Decimal(str(item.get("unit_cost", 0)))
        # recomputar total
        new_items = list(self.reorder_confirm_items)
        new_items[idx] = item
        total = sum(
            Decimal(str(it.get("suggested_quantity", 0)))
            * Decimal(str(it.get("unit_cost", 0)))
            for it in new_items
        )
        self.reorder_confirm_items = new_items
        self.reorder_confirm_total = float(total.quantize(Decimal("0.01")))

    @rx.event
    def confirm_create_purchase_order(self):
        """Confirma la creación de la PO draft con los ítems editados."""
        if not self.current_user.get("privileges", {}).get("create_ingresos"):
            return rx.toast("Sin permiso.", duration=3000)

        supplier_id = self.reorder_confirm_supplier_id
        if not supplier_id:
            return rx.toast("Proveedor no definido.", duration=3000)
        if not self.reorder_confirm_items:
            return rx.toast("No hay ítems para crear la PO.", duration=3000)

        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return rx.toast("Tenant no definido.", duration=3000)

        items = [_suggestion_from_dict(it) for it in self.reorder_confirm_items]
        user_id = None
        if hasattr(self, "current_user"):
            try:
                user_id = int(self.current_user.get("id") or 0) or None
            except (TypeError, ValueError):
                user_id = None

        try:
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                po = create_draft_purchase_order(
                    session,
                    company_id,
                    branch_id,
                    supplier_id,
                    items,
                    user_id=user_id,
                    notes=self.reorder_confirm_notes,
                    auto_generated=True,
                )
                session.commit()
                po_id = po.id
        except ValueError as exc:
            return rx.toast(f"No se puede crear la PO: {exc}", duration=4000)
        except Exception as exc:
            logger.exception("confirm_create_purchase_order failed")
            return rx.toast(f"Error al crear PO: {exc}", duration=4000)

        self.close_reorder_confirm_modal()
        # Remover el grupo procesado de las sugerencias
        self.reorder_groups = [
            g for g in self.reorder_groups if g.get("supplier_id") != supplier_id
        ]
        # Refrescar listado de POs
        self._refresh_purchase_orders_list()
        return rx.toast(f"PO #{po_id} creada en estado borrador.", duration=3000)

    # ── Listado de POs ──

    def _refresh_purchase_orders_list(self):
        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return
        set_tenant_context(company_id, branch_id)
        status = None if self.po_status_filter == "all" else self.po_status_filter
        with rx.session() as session:
            pos = list_purchase_orders(session, company_id, branch_id, status=status)
            rows = []
            for po in pos:
                rows.append({
                    "id": po.id,
                    "supplier_id": po.supplier_id,
                    "supplier_name": (po.supplier.name if po.supplier else "-"),
                    "status": po.status,
                    "total_amount": float(po.total_amount or 0),
                    "auto_generated": bool(po.auto_generated),
                    "item_count": len(po.items or []),
                    "notes": po.notes or "",
                    "created_at": po.created_at.isoformat() if po.created_at else "",
                })
        self.purchase_orders_list = rows

    @rx.event
    def load_purchase_orders(self):
        """Carga POs del tenant aplicando filtro de status actual."""
        self._refresh_purchase_orders_list()

    @rx.event
    def set_po_status_filter(self, value: str):
        self.po_status_filter = value or "all"
        self._refresh_purchase_orders_list()

    @rx.event
    def mark_po_sent(self, po_id: int):
        """Transiciona una PO draft → sent."""
        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return rx.toast("Tenant no definido.", duration=3000)
        try:
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                mark_purchase_order_sent(session, int(po_id), company_id, branch_id)
                session.commit()
        except ValueError as exc:
            return rx.toast(str(exc), duration=4000)
        except Exception as exc:
            logger.exception("mark_po_sent failed")
            return rx.toast(f"Error: {exc}", duration=4000)
        self._refresh_purchase_orders_list()
        return rx.toast(f"PO #{po_id} marcada como enviada.", duration=3000)

    @rx.event
    def cancel_po(self, po_id: int):
        """Cancela una PO no recibida."""
        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return rx.toast("Tenant no definido.", duration=3000)
        try:
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                cancel_purchase_order(session, int(po_id), company_id, branch_id)
                session.commit()
        except ValueError as exc:
            return rx.toast(str(exc), duration=4000)
        except Exception as exc:
            logger.exception("cancel_po failed")
            return rx.toast(f"Error: {exc}", duration=4000)
        self._refresh_purchase_orders_list()
        return rx.toast(f"PO #{po_id} cancelada.", duration=3000)

    @rx.var
    def has_reorder_suggestions(self) -> bool:
        return len(self.reorder_groups) > 0

    @rx.var
    def reorder_total_items(self) -> int:
        return sum(int(g.get("item_count", 0)) for g in self.reorder_groups)


__all__ = ["ReorderState"]
