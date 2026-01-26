"""Estado de Compras - Registro de documentos de ingreso."""
import datetime
import reflex as rx
from typing import Any
from sqlmodel import select
from sqlalchemy import or_, func
from sqlalchemy.orm import selectinload

from app.models import Purchase, Supplier
from .mixin_state import MixinState


class PurchasesState(MixinState):
    purchases_active_tab: str = "registro"
    purchase_search_term: str = ""
    purchase_start_date: str = ""
    purchase_end_date: str = ""
    purchase_current_page: int = 1
    purchase_items_per_page: int = 10
    purchase_detail_modal_open: bool = False
    purchase_detail: dict[str, Any] | None = None
    _purchase_update_trigger: int = 0

    @rx.event
    def set_purchases_tab(self, tab: str):
        if tab in {"registro", "proveedores"}:
            self.purchases_active_tab = tab

    @rx.event
    def set_purchase_search_term(self, value: str):
        self.purchase_search_term = value or ""
        self.purchase_current_page = 1

    @rx.event
    def set_purchase_start_date(self, value: str):
        self.purchase_start_date = value or ""
        self.purchase_current_page = 1

    @rx.event
    def set_purchase_end_date(self, value: str):
        self.purchase_end_date = value or ""
        self.purchase_current_page = 1

    @rx.event
    def set_purchase_page(self, page: int):
        if 1 <= page <= self.purchase_total_pages:
            self.purchase_current_page = page

    @rx.event
    def prev_purchase_page(self):
        if self.purchase_current_page > 1:
            self.purchase_current_page -= 1

    @rx.event
    def next_purchase_page(self):
        if self.purchase_current_page < self.purchase_total_pages:
            self.purchase_current_page += 1

    @rx.event
    def reset_purchase_filters(self):
        self.purchase_search_term = ""
        self.purchase_start_date = ""
        self.purchase_end_date = ""
        self.purchase_current_page = 1

    def _parse_date(self, value: str, end: bool = False) -> datetime.datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None
        if end:
            return parsed.replace(hour=23, minute=59, second=59)
        return parsed

    def _purchase_filters(self):
        term = (self.purchase_search_term or "").strip()
        filters = []
        if term:
            like = f"%{term}%"
            filters.append(
                or_(
                    Purchase.number.ilike(like),
                    Purchase.series.ilike(like),
                    Supplier.name.ilike(like),
                    Supplier.tax_id.ilike(like),
                )
            )
        start_dt = self._parse_date(self.purchase_start_date)
        if start_dt:
            filters.append(Purchase.issue_date >= start_dt)
        end_dt = self._parse_date(self.purchase_end_date, end=True)
        if end_dt:
            filters.append(Purchase.issue_date <= end_dt)
        return filters

    def _purchase_query(self):
        filters = self._purchase_filters()
        query = (
            select(Purchase)
            .join(Supplier, isouter=True)
            .options(
                selectinload(Purchase.supplier),
                selectinload(Purchase.user),
                selectinload(Purchase.items),
            )
            .order_by(Purchase.issue_date.desc(), Purchase.id.desc())
        )
        for clause in filters:
            query = query.where(clause)
        return query

    @rx.var
    def purchase_records(self) -> list[dict[str, Any]]:
        _ = self._purchase_update_trigger
        privileges = self.current_user["privileges"]
        if not (privileges.get("view_compras") or privileges.get("view_ingresos")):
            return []
        page = max(self.purchase_current_page, 1)
        per_page = max(self.purchase_items_per_page, 1)
        offset = (page - 1) * per_page
        with rx.session() as session:
            records = session.exec(
                self._purchase_query().offset(offset).limit(per_page)
            ).all()
        rows = []
        for purchase in records:
            supplier = purchase.supplier
            user = purchase.user
            series = purchase.series or ""
            number = purchase.number or ""
            if series:
                doc_label = f"{purchase.doc_type.upper()} {series}-{number}"
            else:
                doc_label = f"{purchase.doc_type.upper()} {number}"
            rows.append(
                {
                    "id": purchase.id,
                    "issue_date": purchase.issue_date.strftime("%Y-%m-%d")
                    if purchase.issue_date
                    else "",
                    "doc_label": doc_label,
                    "supplier_name": supplier.name if supplier else "",
                    "supplier_tax_id": supplier.tax_id if supplier else "",
                    "total_amount": float(purchase.total_amount or 0),
                    "currency_code": purchase.currency_code or "",
                    "user": user.username if user else "Sistema",
                    "items_count": len(purchase.items or []),
                    "notes": purchase.notes or "",
                }
            )
        return rows

    @rx.var
    def purchase_total_pages(self) -> int:
        _ = self._purchase_update_trigger
        privileges = self.current_user["privileges"]
        if not (privileges.get("view_compras") or privileges.get("view_ingresos")):
            return 1
        with rx.session() as session:
            count_query = select(func.count(Purchase.id)).select_from(Purchase).join(
                Supplier, isouter=True
            )
            for clause in self._purchase_filters():
                count_query = count_query.where(clause)
            total = session.exec(count_query).one() or 0
        if total == 0:
            return 1
        return (total + self.purchase_items_per_page - 1) // self.purchase_items_per_page

    @rx.event
    def open_purchase_detail(self, purchase_id: int):
        privileges = self.current_user["privileges"]
        if not (privileges.get("view_compras") or privileges.get("view_ingresos")):
            return rx.toast("No tiene permisos para ver compras.", duration=3000)
        with rx.session() as session:
            purchase = session.exec(
                select(Purchase)
                .where(Purchase.id == purchase_id)
                .options(
                    selectinload(Purchase.supplier),
                    selectinload(Purchase.user),
                    selectinload(Purchase.items),
                )
            ).first()
            if not purchase:
                return rx.toast("Compra no encontrada.", duration=3000)

            supplier = purchase.supplier
            user = purchase.user
            doc_type = (purchase.doc_type or "").upper()
            series = purchase.series or ""
            number = purchase.number or ""
            if series:
                doc_label = f"{doc_type} {series}-{number}"
            else:
                doc_label = f"{doc_type} {number}"
            items = []
            for item in purchase.items or []:
                items.append(
                    {
                        "description": item.description_snapshot,
                        "barcode": item.barcode_snapshot,
                        "category": item.category_snapshot,
                        "quantity": float(item.quantity or 0),
                        "unit": item.unit,
                        "unit_cost": float(item.unit_cost or 0),
                        "subtotal": float(item.subtotal or 0),
                    }
                )

            self.purchase_detail = {
                "id": purchase.id,
                "doc_label": doc_label,
                "issue_date": purchase.issue_date.strftime("%Y-%m-%d")
                if purchase.issue_date
                else "",
                "supplier_name": supplier.name if supplier else "",
                "supplier_tax_id": supplier.tax_id if supplier else "",
                "total_amount": float(purchase.total_amount or 0),
                "currency_code": purchase.currency_code or "",
                "user": user.username if user else "Sistema",
                "notes": purchase.notes or "",
                "items": items,
            }
            self.purchase_detail_modal_open = True

    @rx.event
    def close_purchase_detail(self):
        self.purchase_detail_modal_open = False
        self.purchase_detail = None

    @rx.var
    def purchase_detail_items(self) -> list[dict[str, Any]]:
        detail = self.purchase_detail or {}
        items = detail.get("items")
        return items if isinstance(items, list) else []
