"""Estado de Proveedores - Gestión de proveedores de compra."""
import reflex as rx
from typing import Any
from sqlmodel import select
from sqlalchemy import or_

from app.models import Supplier, Purchase
from app.utils.sanitization import sanitize_name, sanitize_dni, sanitize_phone, sanitize_text
from .mixin_state import MixinState


class SuppliersState(MixinState):
    suppliers: list[dict[str, Any]] = []
    supplier_search_query: str = ""
    supplier_modal_open: bool = False
    current_supplier: dict[str, Any] = {
        "id": None,
        "name": "",
        "tax_id": "",
        "phone": "",
        "address": "",
        "email": "",
        "is_active": True,
    }

    def _empty_supplier_form(self) -> dict[str, Any]:
        return {
            "id": None,
            "name": "",
            "tax_id": "",
            "phone": "",
            "address": "",
            "email": "",
            "is_active": True,
        }

    @rx.var
    def suppliers_view(self) -> list[dict[str, Any]]:
        return [
            {
                "id": supplier.get("id"),
                "name": supplier.get("name"),
                "tax_id": supplier.get("tax_id"),
                "phone": supplier.get("phone") or "",
                "address": supplier.get("address") or "",
                "email": supplier.get("email") or "",
                "is_active": bool(supplier.get("is_active")),
            }
            for supplier in self.suppliers
        ]

    @rx.event
    def load_suppliers(self):
        term = (self.supplier_search_query or "").strip()
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.suppliers = []
            return
        with rx.session() as session:
            query = (
                select(Supplier)
                .where(Supplier.company_id == company_id)
                .where(Supplier.branch_id == branch_id)
            )
            if term:
                name_prefix = f"{term}%"
                tax_prefix = f"{term}%"
                contact_like = f"%{term}%"
                query = query.where(
                    or_(
                        Supplier.name.ilike(name_prefix),
                        Supplier.tax_id.ilike(tax_prefix),
                        Supplier.phone.ilike(contact_like),
                        Supplier.email.ilike(contact_like),
                    )
                )
                query = query.limit(150)
            else:
                query = query.limit(300)
            query = query.order_by(Supplier.name)
            results = session.exec(query).all()
            self.suppliers = [
                {
                    "id": supplier.id,
                    "name": supplier.name,
                    "tax_id": supplier.tax_id,
                    "phone": supplier.phone,
                    "address": supplier.address,
                    "email": supplier.email,
                    "is_active": supplier.is_active,
                }
                for supplier in results
            ]

    @rx.event
    def set_supplier_search_query(self, value: str):
        self.supplier_search_query = value or ""
        self.load_suppliers()

    @rx.event
    def open_supplier_modal(self, supplier: dict | None = None):
        if isinstance(supplier, dict) and supplier:
            self.current_supplier = {
                "id": supplier.get("id"),
                "name": supplier.get("name", "") or "",
                "tax_id": supplier.get("tax_id", "") or "",
                "phone": supplier.get("phone", "") or "",
                "address": supplier.get("address", "") or "",
                "email": supplier.get("email", "") or "",
                "is_active": bool(supplier.get("is_active", True)),
            }
        else:
            self.current_supplier = self._empty_supplier_form()
        self.supplier_modal_open = True

    @rx.event
    def close_supplier_modal(self):
        self.supplier_modal_open = False
        self.current_supplier = self._empty_supplier_form()

    @rx.event
    def update_current_supplier(self, field: str, value: str | bool):
        if field not in self.current_supplier:
            return
        self.current_supplier[field] = value

    @rx.event
    def save_supplier(self):
        privileges = self.current_user["privileges"]
        if not (privileges.get("manage_proveedores") or privileges.get("manage_clientes")):
            return rx.toast("No tiene permisos para gestionar proveedores.", duration=3000)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)

        name = sanitize_name(self.current_supplier.get("name") or "")
        tax_id = sanitize_dni(self.current_supplier.get("tax_id") or "")
        if not name or not tax_id:
            return rx.toast("Nombre y N° de Registro de Empresa son obligatorios.", duration=3000)

        phone = sanitize_phone(self.current_supplier.get("phone") or "")
        address = sanitize_text(self.current_supplier.get("address") or "")
        email = sanitize_text(self.current_supplier.get("email") or "")
        supplier_id = self.current_supplier.get("id")
        if isinstance(supplier_id, str):
            supplier_id = int(supplier_id) if supplier_id.isdigit() else None

        with rx.session() as session:
            existing = session.exec(
                select(Supplier)
                .where(Supplier.company_id == company_id)
                .where(Supplier.branch_id == branch_id)
                .where(Supplier.tax_id == tax_id)
            ).first()
            if existing and (not supplier_id or existing.id != supplier_id):
                return rx.toast("El N° de Registro de Empresa ya esta registrado.", duration=3000)

            if supplier_id:
                supplier = session.exec(
                    select(Supplier)
                    .where(Supplier.id == supplier_id)
                    .where(Supplier.company_id == company_id)
                    .where(Supplier.branch_id == branch_id)
                ).first()
                if not supplier:
                    return rx.toast("Proveedor no encontrado.", duration=3000)
                supplier.name = name
                supplier.tax_id = tax_id
                supplier.phone = phone or None
                supplier.address = address or None
                supplier.email = email or None
                supplier.is_active = bool(
                    self.current_supplier.get("is_active", True)
                )
                session.add(supplier)
            else:
                supplier = Supplier(
                    company_id=company_id,
                    branch_id=branch_id,
                    name=name,
                    tax_id=tax_id,
                    phone=phone or None,
                    address=address or None,
                    email=email or None,
                    is_active=True,
                )
                session.add(supplier)

            session.commit()

        self.load_suppliers()
        self.close_supplier_modal()
        return rx.toast("Proveedor guardado.", duration=3000)

    @rx.event
    def delete_supplier(self, supplier_id: int):
        privileges = self.current_user["privileges"]
        if not (privileges.get("manage_proveedores") or privileges.get("manage_clientes")):
            return rx.toast("No tiene permisos para gestionar proveedores.", duration=3000)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        with rx.session() as session:
            supplier = session.exec(
                select(Supplier)
                .where(Supplier.id == supplier_id)
                .where(Supplier.company_id == company_id)
                .where(Supplier.branch_id == branch_id)
            ).first()
            if not supplier:
                return rx.toast("Proveedor no encontrado.", duration=3000)
            has_purchases = session.exec(
                select(Purchase)
                .where(Purchase.supplier_id == supplier_id)
                .where(Purchase.company_id == company_id)
                .where(Purchase.branch_id == branch_id)
            ).first()
            if has_purchases:
                return rx.toast(
                    "No se puede eliminar: proveedor con compras registradas.",
                    duration=3000,
                )
            session.delete(supplier)
            session.commit()

        self.load_suppliers()
        return rx.toast("Proveedor eliminado.", duration=3000)
