"""Estado reactivo para Ofertas y Promociones."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import reflex as rx
from sqlmodel import select, func

from app.models import Promotion
from app.models.promotions import PromotionType, PromotionScope
from app.utils.timezone import utc_now_naive

from .mixin_state import MixinState, require_permission

logger = logging.getLogger(__name__)

_TYPE_LABELS = {
    PromotionType.PERCENTAGE: "Descuento %",
    PromotionType.FIXED_AMOUNT: "Monto fijo",
    PromotionType.BUY_X_GET_Y: "Lleva X paga Y",
}

_SCOPE_LABELS = {
    PromotionScope.ALL: "Todos los productos",
    PromotionScope.CATEGORY: "Por categoría",
    PromotionScope.PRODUCT: "Producto específico",
}


class PromotionsState(MixinState):
    """Estado para el módulo de Ofertas y Promociones."""

    # ── Lista ────────────────────────────────────────────────────────
    promotions: list[dict[str, Any]] = []
    promotions_filter_active: str = "all"  # all | active | inactive

    # ── Formulario ──────────────────────────────────────────────────
    show_promotion_form: bool = False
    promo_form_key: int = 0
    promo_editing_id: int = 0

    promo_name: str = ""
    promo_description: str = ""
    promo_type: str = PromotionType.PERCENTAGE
    promo_scope: str = PromotionScope.ALL
    promo_discount_value: str = "10"
    promo_min_quantity: str = "1"
    promo_free_quantity: str = "0"
    promo_starts_at: str = ""
    promo_ends_at: str = ""
    promo_max_uses: str = ""
    promo_product_id: str = ""
    promo_category: str = ""
    promo_is_active: bool = True

    # Categorías disponibles para selector
    promotion_categories: list[str] = []

    # ─── Página init ─────────────────────────────────────────────────

    @rx.event
    async def page_init_promociones(self):
        guard = self._require_active_subscription()
        if guard:
            yield guard
            return
        await self._load_promotions()
        await self._load_promo_categories()

    # ─── Carga ───────────────────────────────────────────────────────

    async def _load_promotions(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return

        from app.utils.tenant import set_tenant_context
        set_tenant_context(company_id, branch_id)
        with rx.session() as session:
            stmt = (
                select(Promotion)
                .where(Promotion.company_id == company_id)
                .where(Promotion.branch_id == branch_id)
            )
            if self.promotions_filter_active == "active":
                stmt = stmt.where(Promotion.is_active == True)
            elif self.promotions_filter_active == "inactive":
                stmt = stmt.where(Promotion.is_active == False)
            stmt = stmt.order_by(Promotion.starts_at.desc())
            rows = session.exec(stmt).all()

        now = utc_now_naive()
        result = []
        for p in rows:
            is_running = (
                p.is_active
                and p.starts_at <= now <= p.ends_at
            )
            scope_label = _SCOPE_LABELS.get(p.scope, p.scope)
            if p.scope == PromotionScope.CATEGORY and p.category:
                scope_label = f"Categoría: {p.category}"

            result.append({
                "id": p.id,
                "name": p.name,
                "description": p.description or "",
                "type": p.promotion_type,
                "type_label": _TYPE_LABELS.get(p.promotion_type, p.promotion_type),
                "scope": p.scope,
                "scope_label": scope_label,
                "discount_value": float(p.discount_value or 0),
                "min_quantity": p.min_quantity,
                "free_quantity": p.free_quantity,
                "starts_at": p.starts_at.strftime("%d/%m/%Y") if p.starts_at else "",
                "ends_at": p.ends_at.strftime("%d/%m/%Y") if p.ends_at else "",
                "starts_at_iso": p.starts_at.strftime("%Y-%m-%d") if p.starts_at else "",
                "ends_at_iso": p.ends_at.strftime("%Y-%m-%d") if p.ends_at else "",
                "is_active": p.is_active,
                "is_running": is_running,
                "current_uses": p.current_uses,
                "max_uses": p.max_uses,
                "product_id": p.product_id,
                "category": p.category or "",
            })
        self.promotions = result

    async def _load_promo_categories(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return
        from app.models import Product
        from app.utils.tenant import set_tenant_context
        set_tenant_context(company_id, branch_id)
        with rx.session() as session:
            stmt = (
                select(Product.category)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
                .where(Product.is_active == True)
                .distinct()
                .order_by(Product.category)
            )
            cats = session.exec(stmt).all()
        self.promotion_categories = [c for c in cats if c]

    # ─── Formulario ──────────────────────────────────────────────────

    @rx.event
    def open_new_promotion(self):
        self.promo_editing_id = 0
        self.promo_name = ""
        self.promo_description = ""
        self.promo_type = PromotionType.PERCENTAGE
        self.promo_scope = PromotionScope.ALL
        self.promo_discount_value = "10"
        self.promo_min_quantity = "1"
        self.promo_free_quantity = "0"
        self.promo_starts_at = utc_now_naive().strftime("%Y-%m-%d")
        self.promo_ends_at = (utc_now_naive() + timedelta(days=7)).strftime("%Y-%m-%d")
        self.promo_max_uses = ""
        self.promo_product_id = ""
        self.promo_category = ""
        self.promo_is_active = True
        self.show_promotion_form = True
        self.promo_form_key += 1

    @rx.event
    def open_edit_promotion(self, promo: dict):
        self.promo_editing_id = promo.get("id", 0)
        self.promo_name = promo.get("name", "")
        self.promo_description = promo.get("description", "")
        self.promo_type = promo.get("type", PromotionType.PERCENTAGE)
        self.promo_scope = promo.get("scope", PromotionScope.ALL)
        self.promo_discount_value = str(promo.get("discount_value", 10))
        self.promo_min_quantity = str(promo.get("min_quantity", 1))
        self.promo_free_quantity = str(promo.get("free_quantity", 0))
        self.promo_starts_at = promo.get("starts_at_iso", "")
        self.promo_ends_at = promo.get("ends_at_iso", "")
        self.promo_max_uses = str(promo.get("max_uses") or "")
        self.promo_product_id = str(promo.get("product_id") or "")
        self.promo_category = promo.get("category", "")
        self.promo_is_active = promo.get("is_active", True)
        self.show_promotion_form = True
        self.promo_form_key += 1

    @rx.event
    def close_promotion_form(self):
        self.show_promotion_form = False

    # Setters de formulario
    @rx.event
    def set_promo_name(self, v: str): self.promo_name = v
    @rx.event
    def set_promo_description(self, v: str): self.promo_description = v
    @rx.event
    def set_promo_type(self, v: str): self.promo_type = v
    @rx.event
    def set_promo_scope(self, v: str): self.promo_scope = v
    @rx.event
    def set_promo_discount_value(self, v: str): self.promo_discount_value = v
    @rx.event
    def set_promo_min_quantity(self, v: str): self.promo_min_quantity = v
    @rx.event
    def set_promo_free_quantity(self, v: str): self.promo_free_quantity = v
    @rx.event
    def set_promo_starts_at(self, v: str): self.promo_starts_at = v
    @rx.event
    def set_promo_ends_at(self, v: str): self.promo_ends_at = v
    @rx.event
    def set_promo_max_uses(self, v: str): self.promo_max_uses = v
    @rx.event
    def set_promo_product_id(self, v: str): self.promo_product_id = v
    @rx.event
    def set_promo_category(self, v: str): self.promo_category = v
    @rx.event
    def set_promo_is_active(self, v: bool): self.promo_is_active = v

    # ─── Guardar promoción ───────────────────────────────────────────

    @rx.event
    @require_permission("manage_config")
    async def save_promotion(self):
        if not self.promo_name.strip():
            yield rx.toast("El nombre es obligatorio.", duration=3000)
            return

        self.is_loading = True
        try:
            company_id = self._company_id()
            branch_id = self._branch_id()
            user_id = (self.current_user or {}).get("id")

            starts = _parse_date(self.promo_starts_at)
            ends = _parse_date(self.promo_ends_at)
            if not starts or not ends:
                yield rx.toast("Las fechas de vigencia son obligatorias.", duration=3000)
                return
            if starts > ends:
                yield rx.toast("La fecha de inicio debe ser anterior a la de fin.", duration=3000)
                return

            from app.utils.tenant import set_tenant_context
            set_tenant_context(company_id, branch_id)
            with rx.session() as session:
                if self.promo_editing_id:
                    promo = session.exec(
                        select(Promotion).where(Promotion.id == self.promo_editing_id)
                    ).first()
                    if not promo:
                        yield rx.toast("Promoción no encontrada.", duration=3000)
                        return
                else:
                    promo = Promotion(
                        company_id=company_id,
                        branch_id=branch_id,
                        created_at=utc_now_naive(),
                        created_by_user_id=user_id,
                    )
                    session.add(promo)

                promo.name = self.promo_name.strip()
                promo.description = self.promo_description.strip() or None
                promo.promotion_type = self.promo_type
                promo.scope = self.promo_scope
                promo.discount_value = Decimal(self.promo_discount_value or "0")
                promo.min_quantity = int(self.promo_min_quantity or 1)
                promo.free_quantity = int(self.promo_free_quantity or 0)
                promo.starts_at = starts
                promo.ends_at = ends
                promo.max_uses = int(self.promo_max_uses) if self.promo_max_uses.strip() else None
                promo.product_id = int(self.promo_product_id) if self.promo_product_id.strip() else None
                promo.category = self.promo_category.strip() or None
                promo.is_active = self.promo_is_active
                session.commit()

            self.show_promotion_form = False
            await self._load_promotions()
            action = "actualizada" if self.promo_editing_id else "creada"
            yield rx.toast(f"Promoción {action} exitosamente.", duration=3000)
        except Exception as exc:
            logger.exception("Error al guardar promoción: %s", exc)
            yield rx.toast(f"Error: {exc}", duration=4000)
        finally:
            self.is_loading = False

    # ─── Activar/Desactivar ──────────────────────────────────────────

    @rx.event
    @require_permission("manage_config")
    async def toggle_promotion(self, promo_id: int, new_active: bool):
        company_id = self._company_id()
        branch_id = self._branch_id()
        from app.utils.tenant import set_tenant_context
        set_tenant_context(company_id, branch_id)
        with rx.session() as session:
            promo = session.exec(select(Promotion).where(Promotion.id == promo_id)).first()
            if promo:
                promo.is_active = new_active
                session.commit()
        await self._load_promotions()
        label = "activada" if new_active else "desactivada"
        yield rx.toast(f"Promoción {label}.", duration=3000)

    # ─── Filtro ──────────────────────────────────────────────────────

    @rx.event
    async def set_promotions_filter(self, value: str):
        self.promotions_filter_active = value
        await self._load_promotions()


def _parse_date(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None
