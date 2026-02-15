"""Estado de Clientes - Gestión del padrón de clientes.

Este módulo maneja el CRUD de clientes:

Funcionalidades principales:
- Listado con búsqueda por nombre/DNI
- Crear nuevos clientes
- Editar datos y límite de crédito
- Eliminar clientes (solo sin deuda)

Integración con ventas a crédito:
- Los clientes pueden tener límite de crédito
- Se rastrea deuda actual automáticamente
- Solo clientes registrados pueden comprar a crédito

Permisos requeridos:
- view_clientes: Ver listado
- manage_clientes: Crear, editar, eliminar

Clases:
    ClientesState: Estado principal del módulo de clientes
"""
from decimal import Decimal

import reflex as rx
from sqlmodel import select
from sqlalchemy import or_

from app.models import Client, Sale
from app.utils.tenant import set_tenant_context
from app.utils.sanitization import (
    sanitize_name,
    sanitize_dni,
    sanitize_phone,
    sanitize_text,
)
from .mixin_state import MixinState


class ClientesState(MixinState):
    """Estado de gestión de clientes.
    
    Maneja el padrón de clientes y su información crediticia.
    Los clientes son requeridos para ventas a crédito.
    
    Attributes:
        clients: Lista de clientes cargados
        search_query: Término de búsqueda actual
        show_modal: Estado del modal de edición
        select_after_save: Si True, selecciona el cliente después de guardar
        current_client: Cliente en edición (dict temporal)
    """
    clients: list[dict] = []
    search_query: str = ""
    show_modal: bool = False
    select_after_save: bool = False
    current_client: dict = {
        "id": None,
        "name": "",
        "dni": "",
        "phone": "",
        "address": "",
        "credit_limit": "0.00",
        "current_debt": "0.00",
    }

    def _empty_client_form(self) -> dict:
        return {
            "id": None,
            "name": "",
            "dni": "",
            "phone": "",
            "address": "",
            "credit_limit": "0.00",
            "current_debt": "0.00",
        }

    def _parse_decimal(self, value: str | float | Decimal) -> Decimal:
        try:
            parsed = Decimal(str(value or "0"))
        except Exception:
            parsed = Decimal("0")
        if parsed < 0:
            parsed = Decimal("0")
        return parsed

    def _company_id(self) -> int | None:
        company_id, branch_id = self._tenant_ids()
        set_tenant_context(company_id, branch_id)
        return company_id

    @rx.var
    def clients_view(self) -> list[dict]:
        rows: list[dict] = []
        for client in self.clients:
            if isinstance(client, dict):
                credit_limit_raw = client.get("credit_limit", 0)
                current_debt_raw = client.get("current_debt", 0)
                client_id = client.get("id")
                name = client.get("name")
                dni = client.get("dni")
                phone = client.get("phone")
                address = client.get("address")
            else:
                credit_limit_raw = getattr(client, "credit_limit", 0)
                current_debt_raw = getattr(client, "current_debt", 0)
                client_id = getattr(client, "id", None)
                name = getattr(client, "name", "")
                dni = getattr(client, "dni", "")
                phone = getattr(client, "phone", "")
                address = getattr(client, "address", "")
            credit_limit = self._parse_decimal(credit_limit_raw)
            current_debt = self._parse_decimal(current_debt_raw)
            available = credit_limit - current_debt
            if available < 0:
                available = Decimal("0")
            rows.append(
                {
                    "id": client_id,
                    "name": name,
                    "dni": dni,
                    "phone": phone,
                    "address": address,
                    "credit_limit": credit_limit,
                    "current_debt": current_debt,
                    "credit_available": available,
                }
            )
        return rows

    @rx.event
    def load_clients(self):
        term = (self.search_query or "").strip()
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.clients = []
            return
        with rx.session() as session:
            query = (
                select(Client)
                .where(Client.company_id == company_id)
                .where(Client.branch_id == branch_id)
            )
            if term:
                name_prefix = f"{term}%"
                dni_prefix = f"{term}%"
                phone_prefix = f"{term}%"
                address_like = f"%{term}%"
                query = query.where(
                    or_(
                        Client.name.ilike(name_prefix),
                        Client.dni.ilike(dni_prefix),
                        Client.phone.ilike(phone_prefix),
                        Client.address.ilike(address_like),
                    )
                )
                query = query.limit(150)
            else:
                query = query.limit(300)
            query = query.order_by(Client.name)
            results = session.exec(query).all()
            self.clients = [
                {
                    "id": client.id,
                    "name": client.name,
                    "dni": client.dni,
                    "phone": client.phone,
                    "address": client.address,
                    "credit_limit": client.credit_limit,
                    "current_debt": client.current_debt,
                }
                for client in results
            ]

    @rx.event
    def set_search_query(self, value: str):
        self.search_query = value or ""
        self.load_clients()

    @rx.event
    def open_modal(self, client: dict | None = None):
        self.select_after_save = False
        if isinstance(client, dict) and client:
            self.current_client = {
                "id": client.get("id"),
                "name": client.get("name", "") or "",
                "dni": client.get("dni", "") or "",
                "phone": client.get("phone", "") or "",
                "address": client.get("address", "") or "",
                "credit_limit": str(client.get("credit_limit", "0.00")),
                "current_debt": str(client.get("current_debt", "0.00")),
            }
        else:
            self.current_client = self._empty_client_form()
        self.show_modal = True

    @rx.event
    def open_modal_from_pos(self):
        self.select_after_save = True
        self.current_client = self._empty_client_form()
        self.show_modal = True

    @rx.event
    def close_modal(self):
        self.show_modal = False
        self.select_after_save = False
        self.current_client = self._empty_client_form()

    @rx.event
    def update_current_client(self, field: str, value: str | float):
        if field not in self.current_client:
            return
        value_str = "" if value is None else str(value)
        self.current_client[field] = value_str

    @rx.event
    def save_client(self):
        if not self.current_user["privileges"].get("manage_clientes"):
            return self.add_notification(
                "No tiene permisos para gestionar clientes.", "error"
            )
        
        # Sanitizar inputs para prevenir XSS e inyecciones
        name = sanitize_name((self.current_client.get("name") or ""))
        dni = sanitize_dni((self.current_client.get("dni") or ""))
        if not name or not dni:
            return self.add_notification(
                "Nombre y documento de identidad son obligatorios.", "error"
            )

        phone = sanitize_phone((self.current_client.get("phone") or ""))
        address = sanitize_text((self.current_client.get("address") or ""))
        credit_limit = self._parse_decimal(
            self.current_client.get("credit_limit", "0.00")
        )
        current_debt = self._parse_decimal(
            self.current_client.get("current_debt", "0.00")
        )
        client_id = self.current_client.get("id")
        if isinstance(client_id, str):
            client_id = int(client_id) if client_id.isdigit() else None
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return self.add_notification("Empresa no definida.", "error")

        self.is_loading = True
        yield

        saved = None
        try:
            with rx.session() as session:
                existing = session.exec(
                    select(Client)
                    .where(Client.dni == dni)
                    .where(Client.company_id == company_id)
                    .where(Client.branch_id == branch_id)
                ).first()
                if existing and (not client_id or existing.id != client_id):
                    return self.add_notification(
                        "El documento ya está registrado.", "error"
                    )

                if client_id:
                    client = session.exec(
                        select(Client)
                        .where(Client.id == client_id)
                        .where(Client.company_id == company_id)
                        .where(Client.branch_id == branch_id)
                    ).first()
                    if not client:
                        return self.add_notification("Cliente no encontrado.", "error")
                    client.name = name
                    client.dni = dni
                    client.phone = phone or None
                    client.address = address or None
                    client.credit_limit = credit_limit
                    client.current_debt = current_debt
                    session.add(client)
                    session.commit()
                    session.refresh(client)
                    saved = client
                else:
                    payload = Client(
                        name=name,
                        dni=dni,
                        phone=phone or None,
                        address=address or None,
                        credit_limit=credit_limit,
                        current_debt=current_debt,
                        company_id=company_id,
                        branch_id=branch_id,
                    )
                    session.add(payload)
                    session.commit()
                    session.refresh(payload)
                    saved = payload
        except Exception:
            return self.add_notification(
                "No se pudo guardar el cliente.", "error"
            )
        finally:
            self.is_loading = False

        self.load_clients()
        self.show_modal = False
        self.current_client = self._empty_client_form()
        self.is_loading = False

        if self.select_after_save and saved:
            balance = saved.credit_limit - saved.current_debt
            if balance < 0:
                balance = Decimal("0")
            client_payload = {
                "id": saved.id,
                "name": saved.name,
                "dni": saved.dni,
                "balance": self._round_currency(float(balance)),
            }
            if hasattr(self, "select_client"):
                self.select_client(client_payload)
            self.select_after_save = False

        return self.add_notification("Cliente guardado.", "success")

    @rx.event
    def delete_client(self, client_id: int):
        if not self.current_user["privileges"].get("manage_clientes"):
            return self.add_notification(
                "No tiene permisos para gestionar clientes.", "error"
            )
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return self.add_notification("Empresa no definida.", "error")

        self.is_loading = True
        yield
        try:
            with rx.session() as session:
                client = session.exec(
                    select(Client)
                    .where(Client.id == client_id)
                    .where(Client.company_id == company_id)
                    .where(Client.branch_id == branch_id)
                ).first()
                if not client:
                    return self.add_notification("Cliente no encontrado.", "error")
                if client.current_debt and client.current_debt > 0:
                    return self.add_notification(
                        "No se puede eliminar: cliente con deuda.", "error"
                    )
                has_sales = session.exec(
                    select(Sale)
                    .where(Sale.client_id == client_id)
                    .where(Sale.company_id == company_id)
                    .where(Sale.branch_id == branch_id)
                ).first()
                if has_sales:
                    return self.add_notification(
                        "No se puede eliminar: cliente con ventas.", "error"
                    )
                session.delete(client)
                session.commit()
        except Exception:
            return self.add_notification(
                "No se pudo eliminar el cliente.", "error"
            )
        finally:
            self.is_loading = False

        self.load_clients()
        return self.add_notification("Cliente eliminado.", "success")
