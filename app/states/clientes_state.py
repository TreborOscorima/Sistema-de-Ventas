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
import logging
from decimal import Decimal

import reflex as rx
from sqlmodel import select
from sqlalchemy import or_

from app.models import Client, Sale
from app.utils.tenant import set_tenant_context
from app.utils.sanitization import (
    escape_like,
    sanitize_name,
    sanitize_dni,
    sanitize_phone,
    sanitize_text,
)
from .mixin_state import MixinState

logger = logging.getLogger(__name__)


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
        "email": "",
        "credit_limit": "0.00",
        "current_debt": "0.00",
        "price_list_id": "",
        "segment": "",
    }
    # Listas de precios disponibles para el selector del modal.
    available_price_lists: list[dict] = []

    # ── Historial de ventas por cliente ──────────────────────────
    show_historial: bool = False
    historial_client: dict = {}
    client_sales: list[dict] = []
    historial_sale_count: int = 0
    historial_total_spent: str = "0.00"

    _VALID_SEGMENTS: list[str] = ["nuevo", "regular", "vip", "mayorista"]

    def _empty_client_form(self) -> dict:
        return {
            "id": None,
            "name": "",
            "dni": "",
            "phone": "",
            "address": "",
            "email": "",
            "credit_limit": "0.00",
            "current_debt": "0.00",
            "price_list_id": "",
            "segment": "",
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

    @rx.var(cache=True)
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
            segment = (
                client.get("segment", "") or ""
                if isinstance(client, dict)
                else (getattr(client, "segment", "") or "")
            )
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
                    "segment": segment,
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
            self.available_price_lists = []
            return
        with rx.session() as session:
            query = (
                select(Client)
                .where(Client.company_id == company_id)
                .where(Client.branch_id == branch_id)
            )
            if term:
                like = f"%{escape_like(term)}%"
                query = query.where(
                    or_(
                        Client.name.ilike(like),
                        Client.dni.ilike(like),
                        Client.phone.ilike(like),
                        Client.address.ilike(like),
                    )
                )
            query = query.order_by(Client.name)
            results = session.exec(query).all()
            self.clients = [
                {
                    "id": client.id,
                    "name": client.name,
                    "dni": client.dni,
                    "phone": client.phone,
                    "address": client.address,
                    "email": client.email or "",
                    "credit_limit": client.credit_limit,
                    "current_debt": client.current_debt,
                    "price_list_id": client.price_list_id or 0,
                    "segment": client.segment or "",
                }
                for client in results
            ]
            # Listas activas del tenant para el selector del modal de cliente.
            from app.models.price_lists import PriceList
            pl_rows = session.exec(
                select(PriceList)
                .where(PriceList.company_id == company_id)
                .where(PriceList.branch_id == branch_id)
                .where(PriceList.is_active == True)  # noqa: E712
                .order_by(PriceList.is_default.desc(), PriceList.name)
            ).all()
            # Pre-computar display_name para evitar concat de Var+str en la UI
            # (Reflex 0.8 no soporta `var + literal` sobre ObjectItemOperation;
            # con esto el componente sólo lee strings ya formateados).
            self.available_price_lists = [
                {
                    "id": str(pl.id),
                    "name": pl.name,
                    "display_name": (
                        f"{pl.name} (predeterminada)" if pl.is_default else pl.name
                    ),
                    "is_default": pl.is_default,
                }
                for pl in pl_rows
            ]

    @rx.event
    def set_search_query(self, value: str):
        self.search_query = value or ""
        self.load_clients()

    @rx.event
    def open_modal(self, client: dict | None = None):
        self.select_after_save = False
        if isinstance(client, dict) and client:
            pl_id = client.get("price_list_id") or 0
            self.current_client = {
                "id": client.get("id"),
                "name": client.get("name", "") or "",
                "dni": client.get("dni", "") or "",
                "phone": client.get("phone", "") or "",
                "address": client.get("address", "") or "",
                "email": client.get("email", "") or "",
                "credit_limit": str(client.get("credit_limit", "0.00")),
                "current_debt": str(client.get("current_debt", "0.00")),
                "price_list_id": str(pl_id) if pl_id else "",
                "segment": client.get("segment", "") or "",
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
        email = sanitize_text((self.current_client.get("email") or ""), max_length=255).strip() or None
        raw_segment = (self.current_client.get("segment") or "").strip().lower()
        segment: str | None = raw_segment if raw_segment in self._VALID_SEGMENTS else None
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

                # Validar la lista de precios contra el tenant. Sin este check
                # un cliente manipulado podría enlazarse con una lista de otra
                # empresa, que se resolvería al cobrar la venta.
                resolved_price_list_id: int | None = None
                pl_raw = (self.current_client.get("price_list_id") or "").strip()
                if pl_raw:
                    try:
                        candidate_id = int(pl_raw)
                    except (ValueError, TypeError):
                        candidate_id = 0
                    if candidate_id:
                        from app.models.price_lists import PriceList as _PriceList
                        candidate = session.exec(
                            select(_PriceList)
                            .where(_PriceList.id == candidate_id)
                            .where(_PriceList.company_id == company_id)
                            .where(_PriceList.branch_id == branch_id)
                        ).first()
                        if not candidate:
                            return self.add_notification(
                                "La lista de precios seleccionada no pertenece a esta sucursal.",
                                "error",
                            )
                        resolved_price_list_id = candidate.id

                if client_id:
                    # FIX 39a: with_for_update to prevent TOCTOU on credit fields
                    client = session.exec(
                        select(Client)
                        .where(Client.id == client_id)
                        .where(Client.company_id == company_id)
                        .where(Client.branch_id == branch_id)
                        .with_for_update()
                    ).first()
                    if not client:
                        return self.add_notification("Cliente no encontrado.", "error")
                    client.name = name
                    client.dni = dni
                    client.phone = phone or None
                    client.address = address or None
                    client.email = email
                    client.credit_limit = credit_limit
                    client.current_debt = current_debt
                    client.price_list_id = resolved_price_list_id
                    client.segment = segment
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
                        email=email,
                        credit_limit=credit_limit,
                        current_debt=current_debt,
                        price_list_id=resolved_price_list_id,
                        segment=segment,
                        company_id=company_id,
                        branch_id=branch_id,
                    )
                    session.add(payload)
                    session.commit()
                    session.refresh(payload)
                    saved = payload
        except Exception:
            logger.exception(
                "save_client failed | company=%s",
                self._company_id(),
            )
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
                "balance": self._round_currency(balance),
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
            logger.exception(
                "delete_client failed | company=%s",
                self._company_id(),
            )
            return self.add_notification(
                "No se pudo eliminar el cliente.", "error"
            )
        finally:
            self.is_loading = False

        self.load_clients()
        return self.add_notification("Cliente eliminado.", "success")

    # ── Historial de ventas por cliente ──────────────────────────────────────

    @rx.event
    def open_historial(self, client: dict):
        self.historial_client = client
        self.client_sales = []
        self.historial_sale_count = 0
        self.historial_total_spent = "0.00"
        self.show_historial = True
        self._load_client_sales_inner(client.get("id"))

    def _load_client_sales_inner(self, client_id: int | None):
        if not client_id:
            return
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return
        from app.enums import SaleStatus
        with rx.session() as session:
            rows = session.exec(
                select(Sale)
                .where(Sale.client_id == client_id)
                .where(Sale.company_id == company_id)
                .where(Sale.branch_id == branch_id)
                .order_by(Sale.timestamp.desc())
            ).all()
        total = Decimal("0.00")
        sales_list = []
        for s in rows:
            is_completed = s.status == SaleStatus.completed
            if is_completed:
                total += s.total_amount
            sales_list.append({
                "id": s.id,
                "fecha": s.timestamp.strftime("%d/%m/%Y %H:%M") if s.timestamp else "-",
                "condicion": "Crédito" if s.payment_condition == "credito" else "Contado",
                "total": str(s.total_amount),
                "estado": "Completada" if is_completed else "Anulada",
                "anulada": not is_completed,
            })
        self.client_sales = sales_list
        self.historial_sale_count = len(sales_list)
        self.historial_total_spent = f"{total:.2f}"

    @rx.event
    def close_historial(self):
        self.show_historial = False
        self.historial_client = {}
        self.client_sales = []
