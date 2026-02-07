"""Estado de Compras - Registro de documentos de ingreso."""
import datetime
from decimal import Decimal
from typing import Any

import reflex as rx
from sqlmodel import select
from sqlalchemy import or_, func
from sqlalchemy.orm import selectinload

from app.models import Purchase, Supplier, Product, PurchaseItem, StockMovement
from app.utils.sanitization import sanitize_text
from .mixin_state import MixinState


class PurchasesState(MixinState):
    purchases_active_tab: str = "registro"
    purchase_search_term: str = ""
    purchase_start_date: str = ""
    purchase_end_date: str = ""
    purchase_current_page: int = 1
    purchase_items_per_page: int = 10
    purchase_detail_modal_open: bool = False
    purchase_edit_modal_open: bool = False
    purchase_delete_modal_open: bool = False
    purchase_detail: dict[str, Any] | None = None
    purchase_edit_form: dict[str, Any] = {
        "id": None,
        "doc_type": "boleta",
        "series": "",
        "number": "",
        "issue_date": "",
        "notes": "",
        "supplier_id": None,
        "supplier_name": "",
        "supplier_tax_id": "",
    }
    purchase_edit_supplier_query: str = ""
    purchase_edit_supplier_suggestions: list[dict[str, Any]] = []
    purchase_delete_target: dict[str, Any] | None = None
    _purchase_update_trigger: int = 0

    def _empty_purchase_edit_form(self) -> dict[str, Any]:
        return {
            "id": None,
            "doc_type": "boleta",
            "series": "",
            "number": "",
            "issue_date": "",
            "notes": "",
            "supplier_id": None,
            "supplier_name": "",
            "supplier_tax_id": "",
        }

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
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return select(Purchase).where(Purchase.id == -1)
        query = (
            select(Purchase)
            .join(Supplier, isouter=True)
            .options(
                selectinload(Purchase.supplier),
                selectinload(Purchase.user),
                selectinload(Purchase.items),
            )
            .where(Purchase.company_id == company_id)
            .where(Purchase.branch_id == branch_id)
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
            doc_type = (purchase.doc_type or "").upper() or "-"
            series = purchase.series or ""
            number = purchase.number or ""
            series_display = series if series else "-"
            number_display = number if number else "-"
            if series:
                doc_label = f"{doc_type} {series}-{number}"
            else:
                doc_label = f"{doc_type} {number}"
            rows.append(
                {
                    "id": purchase.id,
                    "issue_date": purchase.issue_date.strftime("%Y-%m-%d")
                    if purchase.issue_date
                    else "",
                    "registered_time": purchase.created_at.strftime("%H:%M")
                    if purchase.created_at
                    else "",
                    "doc_type": doc_type,
                    "series": series_display,
                    "number": number_display,
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
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return 1
        with rx.session() as session:
            count_query = select(func.count(Purchase.id)).select_from(Purchase).join(
                Supplier, isouter=True
            )
            count_query = count_query.where(Purchase.company_id == company_id)
            count_query = count_query.where(Purchase.branch_id == branch_id)
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
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        with rx.session() as session:
            purchase = session.exec(
                select(Purchase)
                .where(Purchase.id == purchase_id)
                .where(Purchase.company_id == company_id)
                .where(Purchase.branch_id == branch_id)
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
            doc_type = (purchase.doc_type or "").upper() or "-"
            series = purchase.series or ""
            number = purchase.number or ""
            series_display = series if series else "-"
            number_display = number if number else "-"
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
                "doc_type": doc_type,
                "series": series_display,
                "number": number_display,
                "issue_date": purchase.issue_date.strftime("%Y-%m-%d")
                if purchase.issue_date
                else "",
                "registered_time": purchase.created_at.strftime("%H:%M")
                if purchase.created_at
                else "",
                "supplier_name": supplier.name if supplier else "",
                "supplier_tax_id": supplier.tax_id if supplier else "",
                "total_amount": float(purchase.total_amount or 0),
                "currency_code": purchase.currency_code or "",
                "user": user.username if user else "Sistema",
                "items_count": len(items),
                "notes": purchase.notes or "",
                "items": items,
            }
            self.purchase_detail_modal_open = True

    @rx.event
    def close_purchase_detail(self):
        self.purchase_detail_modal_open = False
        self.purchase_detail = None

    @rx.event
    def open_purchase_edit_modal(self, purchase_id: int):
        if not self.current_user["privileges"].get("create_ingresos"):
            return rx.toast("No tiene permisos para editar compras.", duration=3000)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        with rx.session() as session:
            purchase = session.exec(
                select(Purchase)
                .where(Purchase.id == purchase_id)
                .where(Purchase.company_id == company_id)
                .where(Purchase.branch_id == branch_id)
                .options(selectinload(Purchase.supplier))
            ).first()
            if not purchase:
                return rx.toast("Compra no encontrada.", duration=3000)

            supplier = purchase.supplier
            self.purchase_edit_form = {
                "id": purchase.id,
                "doc_type": purchase.doc_type or "boleta",
                "series": purchase.series or "",
                "number": purchase.number or "",
                "issue_date": purchase.issue_date.strftime("%Y-%m-%d")
                if purchase.issue_date
                else "",
                "notes": purchase.notes or "",
                "supplier_id": supplier.id if supplier else None,
                "supplier_name": supplier.name if supplier else "",
                "supplier_tax_id": supplier.tax_id if supplier else "",
            }

        self.purchase_edit_supplier_query = ""
        self.purchase_edit_supplier_suggestions = []
        self.purchase_edit_modal_open = True

    @rx.event
    def close_purchase_edit_modal(self):
        self.purchase_edit_modal_open = False
        self.purchase_edit_form = self._empty_purchase_edit_form()
        self.purchase_edit_supplier_query = ""
        self.purchase_edit_supplier_suggestions = []

    @rx.event
    def update_purchase_edit_field(self, field: str, value: str):
        if field not in self.purchase_edit_form:
            return
        self.purchase_edit_form[field] = value

    @rx.event
    def search_purchase_edit_supplier(self, query: str):
        self.purchase_edit_supplier_query = query or ""
        term = (query or "").strip()
        if len(term) < 2:
            self.purchase_edit_supplier_suggestions = []
            return

        search = f"%{term}%"
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.purchase_edit_supplier_suggestions = []
            return
        with rx.session() as session:
            suppliers = session.exec(
                select(Supplier)
                .where(
                    or_(
                        Supplier.name.ilike(search),
                        Supplier.tax_id.ilike(search),
                    )
                )
                .where(Supplier.company_id == company_id)
                .where(Supplier.branch_id == branch_id)
                .order_by(Supplier.name)
                .limit(6)
            ).all()

        self.purchase_edit_supplier_suggestions = [
            {
                "id": supplier.id,
                "name": supplier.name,
                "tax_id": supplier.tax_id,
            }
            for supplier in suppliers
        ]

    @rx.event
    def select_purchase_edit_supplier(self, supplier_data: dict | Supplier):
        selected = None
        if isinstance(supplier_data, Supplier):
            selected = {
                "id": supplier_data.id,
                "name": supplier_data.name,
                "tax_id": supplier_data.tax_id,
            }
        elif isinstance(supplier_data, dict) and supplier_data:
            selected = dict(supplier_data)
        if not selected:
            return

        self.purchase_edit_form["supplier_id"] = selected.get("id")
        self.purchase_edit_form["supplier_name"] = selected.get("name", "") or ""
        self.purchase_edit_form["supplier_tax_id"] = selected.get("tax_id", "") or ""
        self.purchase_edit_supplier_query = ""
        self.purchase_edit_supplier_suggestions = []

    @rx.event
    def clear_purchase_edit_supplier(self):
        self.purchase_edit_form["supplier_id"] = None
        self.purchase_edit_form["supplier_name"] = ""
        self.purchase_edit_form["supplier_tax_id"] = ""

    @rx.event
    def save_purchase_edit(self):
        if not self.current_user["privileges"].get("create_ingresos"):
            return rx.toast("No tiene permisos para editar compras.", duration=3000)
        block = self._require_active_subscription()
        if block:
            return block

        purchase_id = self.purchase_edit_form.get("id")
        if not purchase_id:
            return rx.toast("Compra no encontrada.", duration=3000)

        doc_type = (self.purchase_edit_form.get("doc_type") or "").strip().lower()
        if doc_type not in {"boleta", "factura"}:
            return rx.toast("Seleccione tipo de documento valido.", duration=3000)

        series = sanitize_text(self.purchase_edit_form.get("series") or "", max_length=20)
        number = sanitize_text(self.purchase_edit_form.get("number") or "", max_length=30)
        notes = sanitize_text(self.purchase_edit_form.get("notes") or "", max_length=500)
        supplier_id = self.purchase_edit_form.get("supplier_id")

        if not number:
            return rx.toast("Ingrese numero de documento.", duration=3000)
        if not supplier_id:
            return rx.toast("Seleccione un proveedor.", duration=3000)

        issue_date_raw = (self.purchase_edit_form.get("issue_date") or "").strip()
        if not issue_date_raw:
            return rx.toast("Ingrese fecha de documento.", duration=3000)
        try:
            issue_date = datetime.datetime.strptime(issue_date_raw, "%Y-%m-%d")
        except ValueError:
            return rx.toast("Fecha de documento invalida.", duration=3000)

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)

        with rx.session() as session:
            existing = session.exec(
                select(Purchase).where(
                    Purchase.company_id == company_id,
                    Purchase.branch_id == branch_id,
                    Purchase.id != purchase_id,
                    Purchase.supplier_id == supplier_id,
                    Purchase.doc_type == doc_type,
                    Purchase.series == series,
                    Purchase.number == number,
                )
            ).first()
            if existing:
                return rx.toast(
                    "Documento ya registrado para este proveedor.",
                    duration=3000,
                )

            purchase = session.exec(
                select(Purchase)
                .where(Purchase.id == purchase_id)
                .where(Purchase.company_id == company_id)
                .where(Purchase.branch_id == branch_id)
            ).first()
            if not purchase:
                return rx.toast("Compra no encontrada.", duration=3000)

            purchase.doc_type = doc_type
            purchase.series = series
            purchase.number = number
            purchase.issue_date = issue_date
            purchase.notes = notes
            purchase.supplier_id = supplier_id
            session.add(purchase)
            session.commit()

        self._purchase_update_trigger += 1
        self.close_purchase_edit_modal()
        return rx.toast("Compra actualizada.", duration=3000)

    @rx.event
    def open_purchase_delete_modal(self, purchase_id: int):
        if not self.current_user["privileges"].get("create_ingresos"):
            return rx.toast("No tiene permisos para eliminar compras.", duration=3000)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        with rx.session() as session:
            purchase = session.exec(
                select(Purchase)
                .where(Purchase.id == purchase_id)
                .where(Purchase.company_id == company_id)
                .where(Purchase.branch_id == branch_id)
                .options(selectinload(Purchase.supplier))
            ).first()
            if not purchase:
                return rx.toast("Compra no encontrada.", duration=3000)

            supplier = purchase.supplier
            self.purchase_delete_target = {
                "id": purchase.id,
                "doc_type": (purchase.doc_type or "").upper() or "-",
                "series": purchase.series or "-",
                "number": purchase.number or "-",
                "supplier_name": supplier.name if supplier else "",
                "supplier_tax_id": supplier.tax_id if supplier else "",
            }

        self.purchase_delete_modal_open = True

    @rx.event
    def close_purchase_delete_modal(self):
        self.purchase_delete_modal_open = False
        self.purchase_delete_target = None

    @rx.event
    def delete_purchase(self):
        if not self.current_user["privileges"].get("create_ingresos"):
            return rx.toast("No tiene permisos para eliminar compras.", duration=3000)
        block = self._require_active_subscription()
        if block:
            return block

        target = self.purchase_delete_target or {}
        purchase_id = target.get("id")
        if not purchase_id:
            return rx.toast("Compra no encontrada.", duration=3000)

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        with rx.session() as session:
            purchase = session.exec(
                select(Purchase)
                .where(Purchase.id == purchase_id)
                .where(Purchase.company_id == company_id)
                .where(Purchase.branch_id == branch_id)
                .options(selectinload(Purchase.items))
            ).first()
            if not purchase:
                return rx.toast("Compra no encontrada.", duration=3000)

            items = purchase.items or []
            for item in items:
                if not item.product_id:
                    return rx.toast(
                        "No se puede eliminar: item sin producto asociado.",
                        duration=3000,
                    )
                product = session.exec(
                    select(Product)
                    .where(Product.id == item.product_id)
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                ).first()
                if not product:
                    return rx.toast(
                        "No se puede eliminar: producto no encontrado.",
                        duration=3000,
                    )
                qty = Decimal(str(item.quantity or 0))
                if (product.stock or Decimal("0")) - qty < 0:
                    return rx.toast(
                        "No se puede eliminar: el stock actual es menor al ingreso.",
                        duration=4000,
                    )

            doc_type = (purchase.doc_type or "").upper()
            series = purchase.series or ""
            number = purchase.number or ""
            doc_label = f"{doc_type} {series}-{number}" if series else f"{doc_type} {number}"
            user_id = self.current_user.get("id")

            for item in items:
                product = session.exec(
                    select(Product)
                    .where(Product.id == item.product_id)
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                ).first()
                qty = Decimal(str(item.quantity or 0))
                product.stock = (product.stock or Decimal("0")) - qty
                session.add(product)
                session.add(
                    StockMovement(
                        type="Anulacion Ingreso",
                        product_id=product.id,
                        quantity=-qty,
                        description=f"Anulación compra {doc_label}",
                        user_id=user_id,
                        company_id=company_id,
                        branch_id=branch_id,
                    )
                )

            for item in items:
                session.delete(item)
            session.delete(purchase)
            session.commit()

        self._purchase_update_trigger += 1
        if hasattr(self, "_inventory_update_trigger"):
            self._inventory_update_trigger += 1
        self.close_purchase_delete_modal()
        return rx.toast("Compra eliminada.", duration=3000)

    @rx.var
    def purchase_detail_items(self) -> list[dict[str, Any]]:
        detail = self.purchase_detail or {}
        items = detail.get("items")
        return items if isinstance(items, list) else []
