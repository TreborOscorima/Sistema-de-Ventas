"""Estado reactivo para Presupuestos / Cotizaciones."""
from __future__ import annotations

import uuid
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import reflex as rx
from sqlmodel import select, func

from app.models import Client, Product, ProductVariant, Quotation, QuotationItem
from app.models.quotations import QuotationStatus
from app.services.quotation_service import (
    CreateQuotationDTO,
    QuotationItemDTO,
    QuotationService,
)
from app.utils.db import get_async_session
from app.utils.timezone import utc_now_naive

from .mixin_state import MixinState, require_permission

logger = logging.getLogger(__name__)

_STATUS_LABEL = {
    QuotationStatus.DRAFT: "Borrador",
    QuotationStatus.SENT: "Enviado",
    QuotationStatus.ACCEPTED: "Aceptado",
    QuotationStatus.REJECTED: "Rechazado",
    QuotationStatus.EXPIRED: "Vencido",
    QuotationStatus.CONVERTED: "Convertido",
}

_STATUS_COLOR = {
    QuotationStatus.DRAFT: "text-slate-600 bg-slate-100",
    QuotationStatus.SENT: "text-blue-700 bg-blue-100",
    QuotationStatus.ACCEPTED: "text-emerald-700 bg-emerald-100",
    QuotationStatus.REJECTED: "text-red-700 bg-red-100",
    QuotationStatus.EXPIRED: "text-amber-700 bg-amber-100",
    QuotationStatus.CONVERTED: "text-indigo-700 bg-indigo-100",
}


class QuotationState(MixinState):
    """Estado para el módulo de Presupuestos."""

    # ── Lista ────────────────────────────────────────────────────────
    quotations: list[dict[str, Any]] = []
    quotations_page: int = 1
    quotations_page_size: int = 20
    quotations_total: int = 0
    quotations_filter_status: str = ""
    quotations_search: str = ""

    # ── Formulario de creación ───────────────────────────────────────
    show_quotation_form: bool = False
    quot_form_key: int = 0
    quot_client_id: str = ""
    quot_validity_days: str = "15"
    quot_notes: str = ""
    quot_global_discount: str = "0"
    # Idempotency key estable durante toda la edición del formulario.
    # Se asigna al abrir el form y se reusa en cada intento de save_quotation,
    # de forma que el UNIQUE (company_id, idempotency_key) bloquee duplicados
    # ante doble-click o reintentos por timeout.
    quot_idempotency_key: str = ""

    # Carrito del presupuesto
    quot_cart: list[dict[str, Any]] = []
    quot_search: str = ""
    quot_search_results: list[dict[str, Any]] = []

    # ── Detalle / edición ────────────────────────────────────────────
    show_quotation_detail: bool = False
    selected_quotation: dict[str, Any] = {}
    selected_quotation_items: list[dict[str, Any]] = []

    # ── Clientes disponibles (para selector) ─────────────────────────
    quotation_clients: list[dict[str, Any]] = []

    # Presupuesto pre-cargado al POS pendiente de vincular tras confirmar venta
    _pending_quotation_id: int = rx.field(default=0, is_var=False)

    # ─── Inicialización de página ────────────────────────────────────
    # Nombre con prefijo `bg_` para no colisionar con el guard
    # `State.page_init_presupuestos` (definido en app/state.py).
    # Reflex resuelve mixins por MRO: si dos clases definen el mismo nombre
    # gana la más específica, dejando muerta a la otra. Mantener nombres
    # distintos garantiza que ambos métodos sean alcanzables.

    @rx.event
    async def bg_load_quotations(self):
        guard = self._require_active_subscription()
        if guard:
            yield guard
            return
        self.quotations_page = 1
        self.quotations_filter_status = ""
        self.quotations_search = ""
        await self._load_quotations()
        await self._load_quotation_clients()

    # ─── Cargar lista ────────────────────────────────────────────────

    async def _load_quotations(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return

        from app.utils.tenant import set_tenant_context
        from sqlalchemy import update as sa_update
        set_tenant_context(company_id, branch_id)
        now = utc_now_naive()
        with rx.session() as session:
            # Auto-expirar presupuestos vencidos del tenant antes de listar.
            # Idempotente y barato (UPDATE WHERE status IN draft|sent AND expires_at < now);
            # garantiza que el filtro "Vencidos" muestre lo correcto sin job externo.
            session.exec(
                sa_update(Quotation)
                .where(Quotation.company_id == company_id)
                .where(Quotation.branch_id == branch_id)
                .where(Quotation.expires_at.isnot(None))
                .where(Quotation.expires_at < now)
                .where(Quotation.status.in_([QuotationStatus.DRAFT, QuotationStatus.SENT]))
                .values(status=QuotationStatus.EXPIRED)
            )
            session.commit()

            stmt = (
                select(Quotation)
                .where(Quotation.company_id == company_id)
                .where(Quotation.branch_id == branch_id)
            )
            if self.quotations_filter_status:
                stmt = stmt.where(Quotation.status == self.quotations_filter_status)
            if self.quotations_search.strip():
                # Búsqueda básica por notas o número
                pass

            count_stmt = select(func.count()).select_from(stmt.subquery())
            self.quotations_total = session.exec(count_stmt).one() or 0

            stmt = (
                stmt.order_by(Quotation.created_at.desc())
                .offset((self.quotations_page - 1) * self.quotations_page_size)
                .limit(self.quotations_page_size)
            )
            rows = session.exec(stmt).all()

        result = []
        for q in rows:
            result.append({
                "id": q.id,
                "created_at": self._format_company_datetime(q.created_at, "%d/%m/%Y"),
                "expires_at": self._format_company_datetime(q.expires_at, "%d/%m/%Y"),
                "status": q.status,
                "status_label": _STATUS_LABEL.get(q.status, q.status),
                "status_color": _STATUS_COLOR.get(q.status, "text-slate-600 bg-slate-100"),
                "total_amount": self._format_currency(float(q.total_amount or 0)),
                "total_raw": float(q.total_amount or 0),
                "client_id": q.client_id,
                "notes": q.notes or "",
                "converted_sale_id": q.converted_sale_id,
            })
        self.quotations = result

    async def _load_quotation_clients(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return

        from app.utils.tenant import set_tenant_context
        set_tenant_context(company_id, branch_id)
        with rx.session() as session:
            stmt = (
                select(Client)
                .where(Client.company_id == company_id)
                .where(Client.branch_id == branch_id)
                .order_by(Client.name)
                .limit(200)
            )
            rows = session.exec(stmt).all()
        self.quotation_clients = [
            {"id": str(c.id), "name": c.name, "dni": c.dni}
            for c in rows
        ]

    # ─── Formulario ──────────────────────────────────────────────────

    @rx.event
    def open_quotation_form(self):
        self.show_quotation_form = True
        self.quot_cart = []
        self.quot_client_id = ""
        self.quot_validity_days = "15"
        self.quot_notes = ""
        self.quot_global_discount = "0"
        self.quot_search = ""
        self.quot_search_results = []
        self.quot_form_key += 1
        self.quot_idempotency_key = str(uuid.uuid4())

    @rx.event
    def close_quotation_form(self):
        self.show_quotation_form = False

    @rx.event
    def set_quot_client(self, value: str):
        self.quot_client_id = value

    @rx.event
    def set_quot_validity(self, value: str):
        self.quot_validity_days = value

    @rx.event
    def set_quot_notes(self, value: str):
        self.quot_notes = value

    @rx.event
    def set_quot_global_discount(self, value: str):
        self.quot_global_discount = value

    # ─── Búsqueda de productos ───────────────────────────────────────

    @rx.event
    async def quot_search_products(self, query: str):
        self.quot_search = query
        if len(query.strip()) < 2:
            self.quot_search_results = []
            return

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return

        from app.utils.tenant import set_tenant_context
        set_tenant_context(company_id, branch_id)
        q_lower = query.strip().lower()
        with rx.session() as session:
            stmt = (
                select(Product)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
                .where(Product.is_active == True)
                .where(
                    (func.lower(Product.description).contains(q_lower))
                    | (Product.barcode.contains(query.strip()))
                )
                .limit(10)
            )
            rows = session.exec(stmt).all()

        self.quot_search_results = [
            {
                "id": str(p.id),
                "description": p.description,
                "barcode": p.barcode,
                "sale_price": float(p.sale_price or 0),
                "category": p.category or "",
            }
            for p in rows
        ]

    @rx.event
    def quot_add_product(self, product_data: dict):
        """Agrega un producto al carrito del presupuesto."""
        self.quot_search = ""
        self.quot_search_results = []
        # Verificar si ya está en el carrito
        for item in self.quot_cart:
            if item["product_id"] == product_data.get("id"):
                item["quantity"] = str(float(item["quantity"]) + 1)
                item["subtotal"] = self._round_currency(
                    float(item["quantity"]) * float(item["unit_price"])
                    * (1 - float(item["discount_percentage"]) / 100)
                )
                self.quot_cart = list(self.quot_cart)
                return

        self.quot_cart.append({
            "product_id": product_data.get("id"),
            "description": product_data.get("description", ""),
            "barcode": product_data.get("barcode", ""),
            "quantity": "1",
            "unit_price": str(product_data.get("sale_price", 0)),
            "discount_percentage": "0",
            "subtotal": self._round_currency(float(product_data.get("sale_price", 0))),
        })

    @rx.event
    def quot_remove_item(self, idx: int):
        self.quot_cart = [item for i, item in enumerate(self.quot_cart) if i != idx]

    @rx.event
    def quot_update_item_qty(self, idx: int, value: str):
        if 0 <= idx < len(self.quot_cart):
            self.quot_cart[idx]["quantity"] = value
            self._recalc_quot_item(idx)

    @rx.event
    def quot_update_item_price(self, idx: int, value: str):
        if 0 <= idx < len(self.quot_cart):
            self.quot_cart[idx]["unit_price"] = value
            self._recalc_quot_item(idx)

    @rx.event
    def quot_update_item_discount(self, idx: int, value: str):
        if 0 <= idx < len(self.quot_cart):
            self.quot_cart[idx]["discount_percentage"] = value
            self._recalc_quot_item(idx)

    def _recalc_quot_item(self, idx: int):
        item = self.quot_cart[idx]
        try:
            qty = float(item["quantity"] or 0)
            price = float(item["unit_price"] or 0)
            disc = float(item["discount_percentage"] or 0)
            item["subtotal"] = self._round_currency(qty * price * (1 - disc / 100))
        except (ValueError, TypeError):
            item["subtotal"] = 0.0
        self.quot_cart = list(self.quot_cart)

    @rx.var(cache=False)
    def quot_cart_total(self) -> float:
        total = sum(float(item.get("subtotal", 0)) for item in self.quot_cart)
        disc = float(self.quot_global_discount or 0)
        return self._round_currency(total * (1 - disc / 100))

    # ─── Guardar presupuesto ─────────────────────────────────────────

    @rx.event
    @require_permission("create_ventas")
    async def save_quotation(self):
        if not self.quot_cart:
            yield rx.toast("Agrega al menos un producto al presupuesto.", duration=3000)
            return

        self.is_loading = True
        try:
            company_id = self._company_id()
            branch_id = self._branch_id()
            user_id = (self.current_user or {}).get("id")

            items = []
            for item in self.quot_cart:
                try:
                    items.append(
                        QuotationItemDTO(
                            product_id=int(item["product_id"]) if item.get("product_id") else None,
                            product_variant_id=None,
                            quantity=float(item.get("quantity") or 1),
                            unit_price=float(item.get("unit_price") or 0),
                            discount_percentage=float(item.get("discount_percentage") or 0),
                        )
                    )
                except (ValueError, TypeError):
                    continue

            # Reusar la key estable del formulario; si por algún motivo no
            # fue inicializada (legacy/state hidratado) generar una nueva.
            idem_key = self.quot_idempotency_key or str(uuid.uuid4())
            self.quot_idempotency_key = idem_key

            dto = CreateQuotationDTO(
                client_id=int(self.quot_client_id) if self.quot_client_id else None,
                user_id=user_id,
                company_id=company_id,
                branch_id=branch_id,
                items=items,
                validity_days=int(self.quot_validity_days or 15),
                discount_percentage=float(self.quot_global_discount or 0),
                notes=self.quot_notes.strip() or None,
                idempotency_key=idem_key,
            )

            async with get_async_session() as session:
                quotation = await QuotationService.create_quotation(dto, session=session)
                await session.commit()

            self.show_quotation_form = False
            await self._load_quotations()
            yield rx.toast("Presupuesto creado exitosamente.", duration=3000)
        except Exception as exc:
            logger.exception("Error al crear presupuesto: %s", exc)
            yield rx.toast(f"Error: {exc}", duration=4000)
        finally:
            self.is_loading = False

    # ─── Detalle y cambio de estado ──────────────────────────────────

    @rx.event
    async def open_quotation_detail(self, quotation_id: int):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return

        from app.utils.tenant import set_tenant_context
        set_tenant_context(company_id, branch_id)
        with rx.session() as session:
            q = session.exec(select(Quotation).where(Quotation.id == quotation_id)).first()
            if not q:
                return
            items_stmt = select(QuotationItem).where(QuotationItem.quotation_id == quotation_id)
            items = session.exec(items_stmt).all()

        self.selected_quotation = {
            "id": q.id,
            "status": q.status,
            "status_label": _STATUS_LABEL.get(q.status, q.status),
            "status_color": _STATUS_COLOR.get(q.status, ""),
            "created_at": self._format_company_datetime(q.created_at, "%d/%m/%Y %H:%M"),
            "expires_at": self._format_company_datetime(q.expires_at, "%d/%m/%Y"),
            "total_amount": self._format_currency(float(q.total_amount or 0)),
            "discount_percentage": float(q.discount_percentage or 0),
            "notes": q.notes or "",
            "client_id": q.client_id,
            "converted_sale_id": q.converted_sale_id,
            "validity_days": q.validity_days,
        }
        self.selected_quotation_items = [
            {
                "description": qi.product_name_snapshot or "",
                "barcode": qi.product_barcode_snapshot or "",
                "quantity": float(qi.quantity or 0),
                "unit_price": self._format_currency(float(qi.unit_price or 0)),
                "discount_percentage": float(qi.discount_percentage or 0),
                "subtotal": self._format_currency(float(qi.subtotal or 0)),
            }
            for qi in items
        ]
        self.show_quotation_detail = True

    @rx.event
    def close_quotation_detail(self):
        self.show_quotation_detail = False

    @rx.event
    async def update_quotation_status(self, quotation_id: int, new_status: str):
        company_id = self._company_id()
        branch_id = self._branch_id()
        try:
            await QuotationService.update_status(
                quotation_id, new_status, company_id, branch_id
            )
            await self._load_quotations()
            self.show_quotation_detail = False
            yield rx.toast(f"Estado actualizado a: {_STATUS_LABEL.get(new_status, new_status)}", duration=3000)
        except Exception as exc:
            yield rx.toast(f"Error: {exc}", duration=4000)

    # ─── Exportar PDF ────────────────────────────────────────────────

    @rx.event
    async def download_quotation_pdf(self, quotation_id: int):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return

        from app.utils.tenant import set_tenant_context
        set_tenant_context(company_id, branch_id)
        with rx.session() as session:
            q = session.exec(select(Quotation).where(Quotation.id == quotation_id)).first()
            if not q:
                yield rx.toast("Presupuesto no encontrado.", duration=3000)
                return
            items_stmt = select(QuotationItem).where(QuotationItem.quotation_id == quotation_id)
            items = session.exec(items_stmt).all()

        # Resolver nombre de cliente
        client_name = ""
        if q.client_id:
            with rx.session() as session:
                cli = session.exec(select(Client).where(Client.id == q.client_id)).first()
                if cli:
                    client_name = cli.name

        settings = self._company_settings_snapshot()
        settings["client_name"] = client_name
        settings["currency_symbol"] = self.currency_symbol

        items_data = [
            {
                "product_name_snapshot": qi.product_name_snapshot,
                "quantity": float(qi.quantity or 0),
                "unit_price": float(qi.unit_price or 0),
                "discount_percentage": float(qi.discount_percentage or 0),
                "subtotal": float(qi.subtotal or 0),
            }
            for qi in items
        ]

        try:
            from app.services.quotation_service import QuotationService
            pdf_bytes = QuotationService.generate_pdf(q, items_data, settings)
            filename = f"presupuesto_{quotation_id:05d}.pdf"
            yield rx.download(data=pdf_bytes, filename=filename)
        except Exception as exc:
            logger.exception("Error generando PDF: %s", exc)
            yield rx.toast(f"Error al generar PDF: {exc}", duration=4000)

    # ─── Paginación ──────────────────────────────────────────────────

    @rx.event
    async def quotations_prev_page(self):
        if self.quotations_page > 1:
            self.quotations_page -= 1
            await self._load_quotations()

    @rx.event
    async def quotations_next_page(self):
        max_page = max(1, -(-self.quotations_total // self.quotations_page_size))
        if self.quotations_page < max_page:
            self.quotations_page += 1
            await self._load_quotations()

    @rx.event
    async def set_quotations_filter_status(self, value: str):
        self.quotations_filter_status = value
        self.quotations_page = 1
        await self._load_quotations()

    @rx.var(cache=False)
    def quotations_total_pages(self) -> int:
        return max(1, -(-self.quotations_total // self.quotations_page_size))

    # ─── Convertir presupuesto a Venta (pre-carga el carrito POS) ────

    @rx.event
    @require_permission("create_ventas")
    async def convert_quotation_to_cart(self, quotation_id: int):
        """Carga los ítems del presupuesto en el carrito POS y redirige a /ventas.

        Al confirmar la venta, confirm_sale() llama a mark_converted() para
        vincular el presupuesto a la sale resultante.
        """
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            yield rx.toast("Empresa no definida.", duration=3000)
            return

        from app.utils.tenant import set_tenant_context
        set_tenant_context(company_id, branch_id)

        with rx.session() as session:
            q = session.exec(
                select(Quotation).where(Quotation.id == quotation_id)
            ).first()
            if not q:
                yield rx.toast("Presupuesto no encontrado.", duration=3000)
                return
            if q.status == QuotationStatus.CONVERTED:
                yield rx.toast("Este presupuesto ya fue convertido a venta.", duration=3000)
                return
            if q.status == QuotationStatus.REJECTED:
                yield rx.toast("Este presupuesto fue rechazado y no puede convertirse.", duration=3000)
                return
            # Bloquear si está vencido (status=EXPIRED o expires_at en el pasado).
            now_check = utc_now_naive()
            if q.status == QuotationStatus.EXPIRED or (
                q.expires_at is not None and q.expires_at < now_check
            ):
                yield rx.toast(
                    "Este presupuesto está vencido. Renueva la fecha o crea uno nuevo.",
                    duration=3500,
                )
                return

            q_items = session.exec(
                select(QuotationItem).where(QuotationItem.quotation_id == quotation_id)
            ).all()

            product_ids = [qi.product_id for qi in q_items if qi.product_id]
            products_map: dict[int, Any] = {}
            if product_ids:
                from app.models import Product as ProductModel
                prods = session.exec(
                    select(ProductModel).where(ProductModel.id.in_(product_ids))
                ).all()
                products_map = {p.id: p for p in prods}

            client_data: dict[str, Any] | None = None
            if q.client_id:
                cli = session.exec(select(Client).where(Client.id == q.client_id)).first()
                if cli:
                    balance = float(max((cli.credit_limit or 0) - (cli.current_debt or 0), 0))
                    client_data = {
                        "id": cli.id,
                        "name": cli.name,
                        "credit_limit": float(cli.credit_limit or 0),
                        "current_debt": float(cli.current_debt or 0),
                        "balance": self._round_currency(balance),
                        "price_list_id": cli.price_list_id or 0,
                    }

            global_disc_factor = Decimal("1") - (
                Decimal(str(q.discount_percentage or 0)) / Decimal("100")
            )

            cart_items: list[dict[str, Any]] = []
            for qi in q_items:
                product = products_map.get(qi.product_id) if qi.product_id else None
                unit = (product.unit if product else None) or "Unidad"
                item_disc_factor = Decimal("1") - (
                    Decimal(str(qi.discount_percentage or 0)) / Decimal("100")
                )
                effective_price = self._round_currency(
                    float(Decimal(str(qi.unit_price or 0)) * item_disc_factor * global_disc_factor)
                )
                qty = float(qi.quantity or 1)
                cart_items.append({
                    "temp_id": str(uuid.uuid4()),
                    "barcode": qi.product_barcode_snapshot or "",
                    "description": qi.product_name_snapshot or "",
                    "category": qi.product_category_snapshot or "General",
                    "quantity": qty,
                    "unit": unit,
                    "price": effective_price,
                    "sale_price": effective_price,
                    "subtotal": self._round_currency(qty * effective_price),
                    "product_id": qi.product_id,
                    "variant_id": qi.product_variant_id,
                    "batch_id": None,
                    "batch_number": "",
                    "requires_batch": False,
                    "kit_product_id": None,
                    "kit_name": "",
                })

        if not cart_items:
            yield rx.toast("El presupuesto no tiene ítems válidos.", duration=3000)
            return

        # Reemplazar carrito POS con los ítems del presupuesto
        self.new_sale_items = cart_items
        self._reset_sale_form()
        self._pending_quotation_id = quotation_id

        if client_data:
            self.selected_client = client_data
            self._active_price_list_id = int(client_data.get("price_list_id") or 0)

        self.show_quotation_detail = False
        yield rx.toast(
            f"Presupuesto #{quotation_id} cargado en el POS ({len(cart_items)} ítem{'s' if len(cart_items) != 1 else ''}).",
            duration=3000,
        )
        yield rx.redirect("/venta")
