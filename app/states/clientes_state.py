from decimal import Decimal

import reflex as rx
from sqlmodel import select
from sqlalchemy import or_

from app.models import Client, Sale
from .mixin_state import MixinState


class ClientesState(MixinState):
    clients: list[Client] = []
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

    @rx.var
    def clients_view(self) -> list[dict]:
        rows: list[dict] = []
        for client in self.clients:
            credit_limit = self._parse_decimal(getattr(client, "credit_limit", 0))
            current_debt = self._parse_decimal(getattr(client, "current_debt", 0))
            available = credit_limit - current_debt
            if available < 0:
                available = Decimal("0")
            rows.append(
                {
                    "id": client.id,
                    "name": client.name,
                    "dni": client.dni,
                    "phone": client.phone,
                    "address": client.address,
                    "credit_limit": credit_limit,
                    "current_debt": current_debt,
                    "credit_available": available,
                }
            )
        return rows

    @rx.event
    def load_clients(self):
        term = (self.search_query or "").strip()
        with rx.session() as session:
            query = select(Client)
            if term:
                like = f"%{term}%"
                query = query.where(
                    or_(
                        Client.name.ilike(like),
                        Client.dni.ilike(like),
                        Client.phone.ilike(like),
                        Client.address.ilike(like),
                    )
                )
            query = query.order_by(Client.name)
            self.clients = session.exec(query).all()

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
        name = (self.current_client.get("name") or "").strip()
        dni = (self.current_client.get("dni") or "").strip()
        if not name or not dni:
            return rx.toast("Nombre y DNI son obligatorios.", duration=3000)

        phone = (self.current_client.get("phone") or "").strip()
        address = (self.current_client.get("address") or "").strip()
        credit_limit = self._parse_decimal(
            self.current_client.get("credit_limit", "0.00")
        )
        current_debt = self._parse_decimal(
            self.current_client.get("current_debt", "0.00")
        )
        client_id = self.current_client.get("id")
        if isinstance(client_id, str):
            client_id = int(client_id) if client_id.isdigit() else None

        with rx.session() as session:
            existing = session.exec(select(Client).where(Client.dni == dni)).first()
            if existing and (not client_id or existing.id != client_id):
                return rx.toast("El DNI ya esta registrado.", duration=3000)

            if client_id:
                payload = Client(
                    id=client_id,
                    name=name,
                    dni=dni,
                    phone=phone or None,
                    address=address or None,
                    credit_limit=credit_limit,
                    current_debt=current_debt,
                )
                saved = session.merge(payload)
                session.commit()
                session.refresh(saved)
            else:
                payload = Client(
                    name=name,
                    dni=dni,
                    phone=phone or None,
                    address=address or None,
                    credit_limit=credit_limit,
                    current_debt=current_debt,
                )
                session.add(payload)
                session.commit()
                session.refresh(payload)
                saved = payload

        self.load_clients()
        self.show_modal = False
        self.current_client = self._empty_client_form()

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

        return rx.toast("Cliente guardado.", duration=3000)

    @rx.event
    def delete_client(self, client_id: int):
        with rx.session() as session:
            client = session.get(Client, client_id)
            if not client:
                return rx.toast("Cliente no encontrado.", duration=3000)
            if client.current_debt and client.current_debt > 0:
                return rx.toast(
                    "No se puede eliminar: cliente con deuda.", duration=3000
                )
            has_sales = session.exec(
                select(Sale).where(Sale.client_id == client_id)
            ).first()
            if has_sales:
                return rx.toast(
                    "No se puede eliminar: cliente con ventas.", duration=3000
                )
            session.delete(client)
            session.commit()

        self.load_clients()
        return rx.toast("Cliente eliminado.", duration=3000)
