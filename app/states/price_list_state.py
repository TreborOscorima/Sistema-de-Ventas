"""Estado reactivo para Listas de Precios múltiples."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import reflex as rx
from sqlmodel import select

from app.models import Client, Product, ProductVariant
from app.models.price_lists import PriceList, PriceListItem
from app.utils.timezone import utc_now_naive

from .mixin_state import MixinState, require_permission

logger = logging.getLogger(__name__)


class PriceListState(MixinState):
    """Estado para el módulo de Listas de Precios."""

    # ── Listas ───────────────────────────────────────────────────────
    price_lists: list[dict[str, Any]] = []

    # ── Formulario de lista ──────────────────────────────────────────
    show_price_list_form: bool = False
    pl_form_key: int = 0
    pl_editing_id: int = 0
    pl_name: str = ""
    pl_description: str = ""
    pl_is_default: bool = False
    pl_currency_code: str = "PEN"

    # ── Detalle/ítems ────────────────────────────────────────────────
    show_price_list_detail: bool = False
    selected_price_list: dict[str, Any] = {}
    price_list_items: list[dict[str, Any]] = []

    # Formulario de ítem
    show_pl_item_form: bool = False
    pl_item_product_id: str = ""
    pl_item_product_search: str = ""
    pl_item_product_results: list[dict[str, Any]] = []
    pl_item_unit_price: str = ""
    pl_item_variant_id: str = ""

    # ─── Página init ─────────────────────────────────────────────────

    @rx.event
    async def page_init_listas_precios(self):
        guard = self._require_active_subscription()
        if guard:
            yield guard
            return
        await self._load_price_lists()

    # ─── Carga ───────────────────────────────────────────────────────

    async def _load_price_lists(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return

        from app.utils.tenant import set_tenant_context
        set_tenant_context(company_id, branch_id)
        with rx.session() as session:
            stmt = (
                select(PriceList)
                .where(PriceList.company_id == company_id)
                .where(PriceList.branch_id == branch_id)
                .order_by(PriceList.is_default.desc(), PriceList.name)
            )
            rows = session.exec(stmt).all()

            counts = {}
            for pl in rows:
                cnt = session.exec(
                    select(rx.func.count(PriceListItem.id))
                    .where(PriceListItem.price_list_id == pl.id)
                ).one()
                counts[pl.id] = cnt or 0

            client_counts = {}
            for pl in rows:
                cnt = session.exec(
                    select(rx.func.count(Client.id))
                    .where(Client.price_list_id == pl.id)
                ).one()
                client_counts[pl.id] = cnt or 0

        self.price_lists = [
            {
                "id": pl.id,
                "name": pl.name,
                "description": pl.description or "",
                "is_default": pl.is_default,
                "is_active": pl.is_active,
                "currency_code": pl.currency_code,
                "item_count": counts.get(pl.id, 0),
                "client_count": client_counts.get(pl.id, 0),
            }
            for pl in rows
        ]

    async def _load_price_list_items(self, price_list_id: int):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return

        from app.utils.tenant import set_tenant_context
        set_tenant_context(company_id, branch_id)
        with rx.session() as session:
            stmt = (
                select(PriceListItem)
                .where(PriceListItem.price_list_id == price_list_id)
                .where(PriceListItem.company_id == company_id)
                .order_by(PriceListItem.id)
            )
            items = session.exec(stmt).all()

            result = []
            for item in items:
                product_name = ""
                barcode = ""
                if item.product_id:
                    p = session.exec(select(Product).where(Product.id == item.product_id)).first()
                    if p:
                        product_name = p.description or ""
                        barcode = p.barcode or ""
                variant_desc = ""
                if item.product_variant_id:
                    v = session.exec(select(ProductVariant).where(ProductVariant.id == item.product_variant_id)).first()
                    if v:
                        parts = [v.size, v.color]
                        variant_desc = " / ".join(x for x in parts if x)

                result.append({
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name": product_name,
                    "barcode": barcode,
                    "variant_id": item.product_variant_id,
                    "variant_desc": variant_desc,
                    "unit_price": float(item.unit_price or 0),
                    "unit_price_display": self._format_currency(float(item.unit_price or 0)),
                })

        self.price_list_items = result

    # ─── Formulario de lista ─────────────────────────────────────────

    @rx.event
    def open_new_price_list(self):
        self.pl_editing_id = 0
        self.pl_name = ""
        self.pl_description = ""
        self.pl_is_default = False
        self.pl_currency_code = "PEN"
        self.show_price_list_form = True
        self.pl_form_key += 1

    @rx.event
    def open_edit_price_list(self, pl: dict):
        self.pl_editing_id = pl.get("id", 0)
        self.pl_name = pl.get("name", "")
        self.pl_description = pl.get("description", "")
        self.pl_is_default = pl.get("is_default", False)
        self.pl_currency_code = pl.get("currency_code", "PEN")
        self.show_price_list_form = True
        self.pl_form_key += 1

    @rx.event
    def close_price_list_form(self):
        self.show_price_list_form = False

    @rx.event
    def set_pl_name(self, v: str): self.pl_name = v
    @rx.event
    def set_pl_description(self, v: str): self.pl_description = v
    @rx.event
    def set_pl_is_default(self, v: bool): self.pl_is_default = v
    @rx.event
    def set_pl_currency_code(self, v: str): self.pl_currency_code = v

    @rx.event
    @require_permission("manage_config")
    async def save_price_list(self):
        if not self.pl_name.strip():
            yield rx.toast("El nombre de la lista es obligatorio.", duration=3000)
            return

        self.is_loading = True
        try:
            company_id = self._company_id()
            branch_id = self._branch_id()

            from app.utils.tenant import set_tenant_context
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                if self.pl_editing_id:
                    pl = session.exec(
                        select(PriceList).where(PriceList.id == self.pl_editing_id)
                    ).first()
                    if not pl:
                        yield rx.toast("Lista no encontrada.", duration=3000)
                        return
                else:
                    pl = PriceList(
                        company_id=company_id,
                        branch_id=branch_id,
                        created_at=utc_now_naive(),
                    )
                    session.add(pl)

                # Si se marca como default, quitar el flag a las demás
                if self.pl_is_default and not (self.pl_editing_id and pl.is_default):
                    others = session.exec(
                        select(PriceList)
                        .where(PriceList.company_id == company_id)
                        .where(PriceList.branch_id == branch_id)
                        .where(PriceList.is_default == True)
                    ).all()
                    for other in others:
                        other.is_default = False

                pl.name = self.pl_name.strip()
                pl.description = self.pl_description.strip() or None
                pl.is_default = self.pl_is_default
                pl.currency_code = self.pl_currency_code
                session.commit()

            self.show_price_list_form = False
            await self._load_price_lists()
            action = "actualizada" if self.pl_editing_id else "creada"
            yield rx.toast(f"Lista de precios {action}.", duration=3000)
        except Exception as exc:
            logger.exception("Error al guardar lista de precios: %s", exc)
            yield rx.toast(f"Error: {exc}", duration=4000)
        finally:
            self.is_loading = False

    # ─── Detalle de lista ────────────────────────────────────────────

    @rx.event
    async def open_price_list_detail(self, price_list_id: int):
        pl_data = next((p for p in self.price_lists if p["id"] == price_list_id), None)
        if pl_data:
            self.selected_price_list = pl_data
        self.show_price_list_detail = True
        self.pl_item_product_id = ""
        self.pl_item_unit_price = ""
        self.pl_item_product_search = ""
        self.pl_item_product_results = []
        await self._load_price_list_items(price_list_id)

    @rx.event
    def close_price_list_detail(self):
        self.show_price_list_detail = False

    # ─── Ítems de la lista ───────────────────────────────────────────

    @rx.event
    async def pl_search_products(self, query: str):
        self.pl_item_product_search = query
        if len(query.strip()) < 2:
            self.pl_item_product_results = []
            return

        company_id = self._company_id()
        branch_id = self._branch_id()
        from app.utils.tenant import set_tenant_context
        from sqlalchemy import func as sa_func
        set_tenant_context(company_id, branch_id)
        q_lower = query.strip().lower()
        with rx.session() as session:
            stmt = (
                select(Product)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
                .where(Product.is_active == True)
                .where(
                    (sa_func.lower(Product.description).contains(q_lower))
                    | (Product.barcode.contains(query.strip()))
                )
                .limit(10)
            )
            rows = session.exec(stmt).all()
        self.pl_item_product_results = [
            {
                "id": str(p.id),
                "description": p.description,
                "barcode": p.barcode,
                "sale_price": float(p.sale_price or 0),
            }
            for p in rows
        ]

    @rx.event
    def pl_select_product(self, product: dict):
        self.pl_item_product_id = product.get("id", "")
        self.pl_item_unit_price = str(product.get("sale_price", ""))
        self.pl_item_product_search = product.get("description", "")
        self.pl_item_product_results = []

    @rx.event
    def set_pl_item_price(self, v: str):
        self.pl_item_unit_price = v

    @rx.event
    @require_permission("manage_config")
    async def add_price_list_item(self):
        pl_id = self.selected_price_list.get("id")
        if not pl_id or not self.pl_item_product_id:
            yield rx.toast("Selecciona un producto primero.", duration=3000)
            return
        try:
            price = Decimal(self.pl_item_unit_price or "0")
        except Exception:
            yield rx.toast("Precio inválido.", duration=3000)
            return

        company_id = self._company_id()
        branch_id = self._branch_id()
        from app.utils.tenant import set_tenant_context
        set_tenant_context(company_id, branch_id)
        with rx.session() as session:
            # Verificar si ya existe
            existing = session.exec(
                select(PriceListItem)
                .where(PriceListItem.price_list_id == pl_id)
                .where(PriceListItem.product_id == int(self.pl_item_product_id))
                .where(PriceListItem.product_variant_id == None)
            ).first()
            if existing:
                existing.unit_price = price
            else:
                item = PriceListItem(
                    company_id=company_id,
                    branch_id=branch_id,
                    price_list_id=pl_id,
                    product_id=int(self.pl_item_product_id),
                    product_variant_id=None,
                    unit_price=price,
                    created_at=utc_now_naive(),
                )
                session.add(item)
            session.commit()

        self.pl_item_product_id = ""
        self.pl_item_unit_price = ""
        self.pl_item_product_search = ""
        await self._load_price_list_items(pl_id)
        await self._load_price_lists()
        yield rx.toast("Precio actualizado en la lista.", duration=3000)

    @rx.event
    @require_permission("manage_config")
    async def remove_price_list_item(self, item_id: int):
        pl_id = self.selected_price_list.get("id")
        company_id = self._company_id()
        from app.utils.tenant import set_tenant_context
        set_tenant_context(company_id, self._branch_id())
        with rx.session() as session:
            item = session.exec(
                select(PriceListItem).where(PriceListItem.id == item_id)
            ).first()
            if item:
                session.delete(item)
                session.commit()
        if pl_id:
            await self._load_price_list_items(pl_id)
            await self._load_price_lists()
        yield rx.toast("Precio eliminado de la lista.", duration=3000)
