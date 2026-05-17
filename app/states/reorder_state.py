"""Estado de Órdenes de Compra — reposición automática por stock bajo.

Gestiona el flujo:
1. Detectar productos bajo umbral (vía reorder_service)
2. Agrupar por proveedor preferido
3. Crear PurchaseOrders en estado 'draft'
4. Transiciones: draft → sent → received | cancelled
5. Edición completa de borradores
6. Envío por email / WhatsApp
7. Descarga de PDF
"""
import base64
import logging
import urllib.parse
from decimal import Decimal
from typing import Any, Dict, List, Optional

import reflex as rx

from app.models import PurchaseOrder, PurchaseOrderStatus
from app.models.auth import User
from app.services.reorder_service import (
    ReorderSuggestion,
    cancel_purchase_order,
    create_draft_purchase_order,
    get_po_for_edit,
    get_po_for_send,
    get_purchase_order_detail,
    get_supplier_full_info,
    list_active_suppliers,
    list_purchase_orders,
    mark_purchase_order_received,
    mark_purchase_order_sent,
    suggest_reorders_by_supplier,
    update_draft_purchase_order,
)
from app.utils.tenant import set_tenant_context
from .mixin_state import MixinState

logger = logging.getLogger(__name__)


def _suggestion_from_dict(d: Dict[str, Any]) -> ReorderSuggestion:
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
    """Estado de reposición automática y gestión de órdenes de compra."""

    # ── Sugerencias en memoria ──
    reorder_groups: List[Dict[str, Any]] = []
    reorder_loading: bool = False
    reorder_last_error: str = ""

    # ── Listado de POs existentes ──
    purchase_orders_list: List[Dict[str, Any]] = []
    po_status_filter: str = "all"

    # ── Modal confirmación (nueva PO desde sugerencia) ──
    reorder_confirm_open: bool = False
    reorder_confirm_supplier_id: int = 0
    reorder_confirm_supplier_name: str = ""
    reorder_confirm_items: List[Dict[str, Any]] = []
    reorder_confirm_total: float = 0.0
    reorder_confirm_notes: str = ""

    # ── Modal detalle de PO ──
    po_detail_open: bool = False
    po_detail_id: int = 0
    po_detail_supplier: str = ""
    po_detail_status: str = ""
    po_detail_total_str: str = "0.00"
    po_detail_notes: str = ""
    po_detail_auto_generated: bool = False
    po_detail_created_at: str = ""
    po_detail_items: List[Dict[str, Any]] = []

    # ── Modal edición de PO borrador ──
    po_edit_open: bool = False
    po_edit_id: int = 0
    po_edit_supplier_id: int = 0
    po_edit_supplier_name: str = ""
    po_edit_notes: str = ""
    po_edit_items: List[Dict[str, Any]] = []
    po_edit_total: float = 0.0
    po_edit_suppliers: List[Dict[str, Any]] = []  # [{id, name}]

    # ── Modal envío (email / WhatsApp) ──
    po_send_open: bool = False
    po_send_po_id: int = 0
    po_send_supplier_name: str = ""
    po_send_supplier_email: str = ""
    po_send_supplier_phone: str = ""
    po_send_recipient_email: str = ""
    po_send_total_str: str = "0.00"
    po_send_notes: str = ""
    po_send_items_summary: List[str] = []
    po_send_loading: bool = False
    po_send_error: str = ""

    # ──────────────────────────────────────────────────────────────────────────
    # SUGERENCIAS
    # ──────────────────────────────────────────────────────────────────────────

    @rx.event
    def load_reorder_suggestions(self):
        if not hasattr(self, "current_user") or not self.current_user:
            return rx.toast("Sesión requerida.", duration=3000)
        if not self.current_user.get("privileges", {}).get("create_ingresos"):
            return rx.toast("Sin permiso para gestionar órdenes de compra.", duration=3000)

        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return rx.toast("Tenant no definido.", duration=3000)

        self.reorder_loading = True
        self.reorder_last_error = ""
        try:
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                groups = suggest_reorders_by_supplier(session, company_id, branch_id)
            self.reorder_groups = [g.to_dict() for g in groups]
            if not self.reorder_groups:
                return rx.toast("No hay productos bajo umbral de reposición.", duration=3000)
            return rx.toast(
                f"{len(self.reorder_groups)} proveedores con productos a reponer.",
                duration=3000,
            )
        except Exception as exc:
            logger.exception("load_reorder_suggestions failed")
            self.reorder_last_error = str(exc)
            return rx.toast(f"Error al cargar sugerencias: {exc}", duration=4000)
        finally:
            self.reorder_loading = False

    @rx.event
    def open_reorder_confirm_modal(self, supplier_id: int):
        group = next(
            (g for g in self.reorder_groups if g.get("supplier_id") == supplier_id), None
        )
        if group is None:
            return rx.toast("Proveedor no encontrado.", duration=3000)
        if not supplier_id:
            return rx.toast("Asigne un proveedor al producto antes de crear la PO.", duration=3000)
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
        new_items = list(self.reorder_confirm_items)
        new_items[idx] = item
        total = sum(
            Decimal(str(it.get("suggested_quantity", 0))) * Decimal(str(it.get("unit_cost", 0)))
            for it in new_items
        )
        self.reorder_confirm_items = new_items
        self.reorder_confirm_total = float(total.quantize(Decimal("0.01")))

    @rx.event
    def confirm_create_purchase_order(self):
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
                    session, company_id, branch_id, supplier_id, items,
                    user_id=user_id, notes=self.reorder_confirm_notes, auto_generated=True,
                )
                session.commit()
                po_id = po.id
        except ValueError as exc:
            return rx.toast(f"No se puede crear la PO: {exc}", duration=4000)
        except Exception as exc:
            logger.exception("confirm_create_purchase_order failed")
            return rx.toast(f"Error al crear PO: {exc}", duration=4000)
        self.close_reorder_confirm_modal()
        self.reorder_groups = [
            g for g in self.reorder_groups if g.get("supplier_id") != supplier_id
        ]
        self._refresh_purchase_orders_list()
        return rx.toast(f"PO #{po_id} creada en estado borrador.", duration=3000)

    # ──────────────────────────────────────────────────────────────────────────
    # LISTADO DE POs
    # ──────────────────────────────────────────────────────────────────────────

    def _refresh_purchase_orders_list(self):
        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return
        set_tenant_context(company_id, branch_id)
        status = None if self.po_status_filter == "all" else self.po_status_filter
        with rx.session() as session:
            pos = list_purchase_orders(session, company_id, branch_id, status=status)
            user_ids = list({po.user_id for po in pos if po.user_id})
            user_name_map: dict[int, str] = {}
            if user_ids:
                from sqlmodel import select as _select
                user_rows = session.exec(
                    _select(User).where(User.id.in_(user_ids))
                ).all()
                user_name_map = {u.id: u.username for u in user_rows}
            rows = []
            for po in pos:
                rows.append({
                    "id": po.id,
                    "supplier_id": po.supplier_id,
                    "supplier_name": (po.supplier.name if po.supplier else "-"),
                    "status": po.status,
                    "total_amount": float(po.total_amount or 0),
                    "total_amount_str": f"{float(po.total_amount or 0):.2f}",
                    "auto_generated": bool(po.auto_generated),
                    "item_count": len(po.items or []),
                    "notes": po.notes or "",
                    "created_at": po.created_at.strftime("%d/%m/%Y") if po.created_at else "",
                    "created_by": user_name_map.get(po.user_id, "—") if po.user_id else "—",
                })
        self.purchase_orders_list = rows

    @rx.event
    def load_purchase_orders(self):
        self._refresh_purchase_orders_list()

    @rx.event
    def set_po_status_filter(self, value: str):
        self.po_status_filter = value or "all"
        self._refresh_purchase_orders_list()

    # ──────────────────────────────────────────────────────────────────────────
    # DETALLE DE PO
    # ──────────────────────────────────────────────────────────────────────────

    @rx.event
    def open_po_detail(self, po_id: int):
        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return rx.toast("Tenant no definido.", duration=3000)
        try:
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                detail = get_purchase_order_detail(session, int(po_id), company_id, branch_id)
        except Exception as exc:
            logger.exception("open_po_detail failed")
            return rx.toast(f"Error al cargar detalle: {exc}", duration=4000)
        if detail is None:
            return rx.toast("Orden no encontrada.", duration=3000)
        self.po_detail_id = detail["id"]
        self.po_detail_supplier = detail["supplier_name"]
        self.po_detail_status = detail["status"]
        self.po_detail_total_str = detail["total_amount_str"]
        self.po_detail_notes = detail["notes"]
        self.po_detail_auto_generated = detail["auto_generated"]
        self.po_detail_created_at = detail["created_at"]
        self.po_detail_items = detail["items"]
        self.po_detail_open = True

    @rx.event
    def close_po_detail(self):
        self.po_detail_open = False
        self.po_detail_items = []

    # ──────────────────────────────────────────────────────────────────────────
    # TRANSICIONES DE ESTADO
    # ──────────────────────────────────────────────────────────────────────────

    @rx.event
    def mark_po_received(self, po_id: int):
        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return rx.toast("Tenant no definido.", duration=3000)
        try:
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                mark_purchase_order_received(session, int(po_id), company_id, branch_id)
                session.commit()
        except ValueError as exc:
            return rx.toast(str(exc), duration=4000)
        except Exception as exc:
            logger.exception("mark_po_received failed")
            return rx.toast(f"Error: {exc}", duration=4000)
        self.po_detail_open = False
        self._refresh_purchase_orders_list()
        return rx.toast(f"PO #{po_id} marcada como recibida.", duration=3000)

    @rx.event
    def cancel_po(self, po_id: int):
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

    # ──────────────────────────────────────────────────────────────────────────
    # MODAL DE ENVÍO (email + WhatsApp)
    # ──────────────────────────────────────────────────────────────────────────

    @rx.event
    def open_po_send_modal(self, po_id: int):
        """Carga info del proveedor y abre el modal de envío."""
        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return rx.toast("Tenant no definido.", duration=3000)
        try:
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                info = get_po_for_send(session, int(po_id), company_id, branch_id)
        except Exception as exc:
            logger.exception("open_po_send_modal failed")
            return rx.toast(f"Error: {exc}", duration=4000)
        if info is None:
            return rx.toast("Orden no encontrada.", duration=3000)
        if info["status"] != "draft":
            return rx.toast("Solo se pueden enviar POs en borrador.", duration=3000)

        self.po_send_po_id = int(po_id)
        self.po_send_supplier_name = info["supplier_name"]
        self.po_send_supplier_email = info["supplier_email"]
        self.po_send_supplier_phone = info["supplier_phone"]
        self.po_send_recipient_email = info["supplier_email"]
        self.po_send_total_str = info["total_amount_str"]
        self.po_send_notes = info["notes"]
        self.po_send_items_summary = info["items_summary"]
        self.po_send_loading = False
        self.po_send_error = ""
        self.po_send_open = True

    @rx.event
    def close_po_send_modal(self):
        self.po_send_open = False
        self.po_send_po_id = 0
        self.po_send_supplier_name = ""
        self.po_send_supplier_email = ""
        self.po_send_supplier_phone = ""
        self.po_send_recipient_email = ""
        self.po_send_items_summary = []
        self.po_send_error = ""
        self.po_send_loading = False

    @rx.event
    def set_po_send_recipient(self, value: str):
        self.po_send_recipient_email = str(value or "")

    @rx.event
    def send_po_by_email(self):
        """Genera PDF, envía email al proveedor y marca la PO como enviada."""
        from app.services import email_service, po_pdf_service
        from app.services.email_service import EmailConfigError, build_po_email_body

        po_id = self.po_send_po_id
        recipient = (self.po_send_recipient_email or "").strip()
        if not recipient:
            self.po_send_error = "Ingresa un email de destino."
            return

        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return rx.toast("Tenant no definido.", duration=3000)

        self.po_send_loading = True
        self.po_send_error = ""
        try:
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                detail = get_purchase_order_detail(session, po_id, company_id, branch_id)
                supplier_info = get_supplier_full_info(session, po_id, company_id, branch_id)

            if detail is None:
                self.po_send_error = "Orden no encontrada."
                return

            snap = self._company_settings_snapshot()
            currency = self._currency_symbol_clean()
            user_name = (
                self.current_user.get("full_name")
                or self.current_user.get("username")
                or "Sistema"
            )
            detail["user_name"] = user_name

            company_info = {
                "name": snap.get("company_name", ""),
                "ruc": snap.get("ruc", ""),
                "address": snap.get("address", ""),
                "phone": snap.get("phone", "") or "",
                "branch_name": snap.get("branch_name", "") or "",
                "currency_symbol": currency,
            }

            pdf_bytes = po_pdf_service.generate_po_pdf(
                company_info, supplier_info or {}, detail
            )
            subject = f"Orden de Compra #{po_id} — {company_info['name']}"
            body_html = build_po_email_body(
                company_name=company_info["name"],
                po_id=po_id,
                supplier_name=self.po_send_supplier_name,
                items_summary=self.po_send_items_summary,
                total_str=self.po_send_total_str,
                currency=currency,
                notes=self.po_send_notes,
            )
            email_service.send_email_with_pdf(
                to=recipient,
                subject=subject,
                body_html=body_html,
                pdf_bytes=pdf_bytes,
                pdf_filename=f"OrdenCompra_{po_id}.pdf",
            )

            # Marcar como enviada
            with rx.session() as session:
                mark_purchase_order_sent(session, po_id, company_id, branch_id)
                session.commit()

        except EmailConfigError as exc:
            self.po_send_error = str(exc)
            return
        except Exception as exc:
            logger.exception("send_po_by_email failed")
            self.po_send_error = f"Error al enviar: {exc}"
            return
        finally:
            self.po_send_loading = False

        self.close_po_send_modal()
        self._refresh_purchase_orders_list()
        return rx.toast(f"PO #{po_id} enviada por email y marcada como enviada.", duration=4000)

    @rx.event
    def send_po_whatsapp(self):
        """Genera el link de WhatsApp con el resumen y lo abre en nueva pestaña."""
        po_id = self.po_send_po_id
        currency = self._currency_symbol_clean()
        items_text = "\n".join(self.po_send_items_summary) if self.po_send_items_summary else ""
        notes_line = f"\nNotas: {self.po_send_notes}" if self.po_send_notes else ""
        snap = self._company_settings_snapshot()
        company_name = snap.get("company_name", "TUWAYKIAPP")

        message = (
            f"*ORDEN DE COMPRA #{po_id}*\n"
            f"Empresa: {company_name}\n\n"
            f"*Proveedor:* {self.po_send_supplier_name}\n\n"
            f"*Productos a reponer:*\n{items_text}{notes_line}\n\n"
            f"*Total estimado:* {currency} {self.po_send_total_str}\n\n"
            f"_Generado por TUWAYKIAPP_"
        )
        phone = "".join(c for c in (self.po_send_supplier_phone or "") if c.isdigit())
        encoded = urllib.parse.quote(message)
        if phone:
            url = f"https://wa.me/{phone}?text={encoded}"
        else:
            url = f"https://wa.me/?text={encoded}"

        # También marcamos como enviada (en background, no bloquea si falla)
        company_id, branch_id = self._tenant_ids()
        if company_id and branch_id:
            try:
                set_tenant_context(company_id, branch_id)
                with rx.session() as session:
                    mark_purchase_order_sent(session, po_id, company_id, branch_id)
                    session.commit()
            except Exception:
                pass

        self.close_po_send_modal()
        self._refresh_purchase_orders_list()
        return rx.call_script(f"window.open('{url}', '_blank')")

    @rx.event
    def mark_po_sent_only(self, po_id: int):
        """Solo cambia el estado a enviado sin enviar comunicación."""
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
            logger.exception("mark_po_sent_only failed")
            return rx.toast(f"Error: {exc}", duration=4000)
        self.close_po_send_modal()
        self._refresh_purchase_orders_list()
        return rx.toast(f"PO #{po_id} marcada como enviada.", duration=3000)

    # ──────────────────────────────────────────────────────────────────────────
    # MODAL EDICIÓN DE PO BORRADOR
    # ──────────────────────────────────────────────────────────────────────────

    @rx.event
    def open_po_edit(self, po_id: int):
        """Carga la PO borrador y los proveedores disponibles para editar."""
        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return rx.toast("Tenant no definido.", duration=3000)
        try:
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                po_data = get_po_for_edit(session, int(po_id), company_id, branch_id)
                suppliers = list_active_suppliers(session, company_id, branch_id)
        except Exception as exc:
            logger.exception("open_po_edit failed")
            return rx.toast(f"Error al cargar PO: {exc}", duration=4000)
        if po_data is None:
            return rx.toast("PO no encontrada o ya no está en borrador.", duration=3000)

        self.po_edit_id = int(po_id)
        self.po_edit_supplier_id = po_data["supplier_id"]
        self.po_edit_supplier_name = po_data["supplier_name"]
        self.po_edit_notes = po_data["notes"]
        self.po_edit_items = [dict(it) for it in po_data["items"]]
        self.po_edit_total = sum(it["subtotal"] for it in po_data["items"])
        self.po_edit_suppliers = [{"id": s.id, "name": s.name} for s in suppliers]
        self.po_edit_open = True

    @rx.event
    def close_po_edit(self):
        self.po_edit_open = False
        self.po_edit_id = 0
        self.po_edit_items = []
        self.po_edit_suppliers = []
        self.po_edit_supplier_id = 0
        self.po_edit_supplier_name = ""
        self.po_edit_notes = ""
        self.po_edit_total = 0.0

    @rx.event
    def set_po_edit_supplier(self, value: str):
        try:
            sid = int(value)
        except (ValueError, TypeError):
            return
        match = next((s for s in self.po_edit_suppliers if s["id"] == sid), None)
        self.po_edit_supplier_id = sid
        self.po_edit_supplier_name = match["name"] if match else ""

    @rx.event
    def set_po_edit_notes(self, value: str):
        self.po_edit_notes = str(value or "")[:500]

    @rx.event
    def update_po_edit_item_qty(self, index: int, value: str):
        try:
            idx = int(index)
            new_qty = Decimal(str(value or "0"))
        except Exception:
            return rx.toast("Cantidad inválida.", duration=2500)
        if idx < 0 or idx >= len(self.po_edit_items):
            return
        if new_qty <= 0:
            return rx.toast("La cantidad debe ser positiva.", duration=2500)
        item = dict(self.po_edit_items[idx])
        item["suggested_quantity"] = float(new_qty)
        unit_cost = Decimal(str(item.get("unit_cost", 0)))
        item["subtotal"] = float((new_qty * unit_cost).quantize(Decimal("0.01")))
        item["subtotal_str"] = f"{item['subtotal']:.2f}"
        new_items = list(self.po_edit_items)
        new_items[idx] = item
        self.po_edit_items = new_items
        self.po_edit_total = sum(Decimal(str(it["subtotal"])) for it in new_items)

    @rx.event
    def delete_po_edit_item(self, index: int):
        idx = int(index)
        if idx < 0 or idx >= len(self.po_edit_items):
            return
        if len(self.po_edit_items) <= 1:
            return rx.toast("La PO debe tener al menos un ítem.", duration=2500)
        new_items = [it for i, it in enumerate(self.po_edit_items) if i != idx]
        self.po_edit_items = new_items
        self.po_edit_total = sum(Decimal(str(it["subtotal"])) for it in new_items)

    @rx.event
    def save_po_edit(self):
        """Persiste los cambios del modal de edición."""
        if not self.po_edit_items:
            return rx.toast("La PO debe tener al menos un ítem.", duration=3000)
        if not self.po_edit_supplier_id:
            return rx.toast("Selecciona un proveedor.", duration=3000)

        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return rx.toast("Tenant no definido.", duration=3000)

        items_data = [
            {
                "product_id": it["product_id"],
                "suggested_quantity": it["suggested_quantity"],
            }
            for it in self.po_edit_items
        ]

        try:
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                update_draft_purchase_order(
                    session,
                    self.po_edit_id,
                    company_id,
                    branch_id,
                    self.po_edit_supplier_id,
                    items_data,
                    notes=self.po_edit_notes,
                )
                session.commit()
        except ValueError as exc:
            return rx.toast(str(exc), duration=4000)
        except Exception as exc:
            logger.exception("save_po_edit failed")
            return rx.toast(f"Error al guardar: {exc}", duration=4000)

        po_id = self.po_edit_id
        self.close_po_edit()
        self._refresh_purchase_orders_list()
        return rx.toast(f"PO #{po_id} actualizada.", duration=3000)

    # ──────────────────────────────────────────────────────────────────────────
    # DESCARGA DE PDF
    # ──────────────────────────────────────────────────────────────────────────

    @rx.event
    def download_po_pdf(self, po_id: int):
        """Genera y descarga el PDF de una orden de compra."""
        from app.services import po_pdf_service

        company_id, branch_id = self._tenant_ids()
        if not company_id or not branch_id:
            return rx.toast("Tenant no definido.", duration=3000)
        try:
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                detail = get_purchase_order_detail(session, int(po_id), company_id, branch_id)
                supplier_info = get_supplier_full_info(session, int(po_id), company_id, branch_id)
        except Exception as exc:
            logger.exception("download_po_pdf failed")
            return rx.toast(f"Error al generar PDF: {exc}", duration=4000)
        if detail is None:
            return rx.toast("Orden no encontrada.", duration=3000)

        snap = self._company_settings_snapshot()
        currency = self._currency_symbol_clean()
        user_name = (
            self.current_user.get("full_name")
            or self.current_user.get("username")
            or "Sistema"
        )
        detail["user_name"] = user_name
        company_info = {
            "name": snap.get("company_name", ""),
            "ruc": snap.get("ruc", ""),
            "address": snap.get("address", ""),
            "phone": snap.get("phone", "") or "",
            "branch_name": snap.get("branch_name", "") or "",
            "currency_symbol": currency,
        }

        try:
            pdf_bytes = po_pdf_service.generate_po_pdf(
                company_info, supplier_info or {}, detail
            )
        except Exception as exc:
            logger.exception("generate_po_pdf failed")
            return rx.toast(f"Error al generar PDF: {exc}", duration=4000)

        b64 = base64.b64encode(pdf_bytes).decode()
        filename = f"OrdenCompra_{po_id}.pdf"
        return rx.call_script(
            f"""
            (() => {{
                const a = document.createElement('a');
                a.href = 'data:application/pdf;base64,{b64}';
                a.download = '{filename}';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }})();
            """
        )

    # ──────────────────────────────────────────────────────────────────────────
    # COMPUTED VARS
    # ──────────────────────────────────────────────────────────────────────────

    @rx.var
    def has_reorder_suggestions(self) -> bool:
        return len(self.reorder_groups) > 0

    @rx.var
    def reorder_total_items(self) -> int:
        return sum(int(g.get("item_count", 0)) for g in self.reorder_groups)

    @rx.var
    def reorder_confirm_total_str(self) -> str:
        return f"{self.reorder_confirm_total:.2f}"

    @rx.var
    def po_edit_total_str(self) -> str:
        return f"{float(self.po_edit_total):.2f}"


__all__ = ["ReorderState"]
