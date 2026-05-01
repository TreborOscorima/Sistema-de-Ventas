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
    promo_product_ids: list[str] = []
    promo_product_search: str = ""
    promo_category: str = ""
    promo_is_active: bool = True

    # Días de aplicación (Mon..Sun)
    promo_day_mon: bool = True
    promo_day_tue: bool = True
    promo_day_wed: bool = True
    promo_day_thu: bool = True
    promo_day_fri: bool = True
    promo_day_sat: bool = True
    promo_day_sun: bool = True

    # Banda horaria opcional ("HH:MM"). Vacío = todo el día.
    promo_time_from: str = ""
    promo_time_to: str = ""

    # Código de cupón (opcional). Vacío = promo automática.
    promo_coupon_code: str = ""

    # Umbral de subtotal del carrito. "" o "0" = sin umbral.
    promo_min_cart_amount: str = ""

    # Categorías disponibles para selector
    promotion_categories: list[str] = []

    # Productos disponibles para selector (scope=PRODUCT)
    promotion_products: list[dict[str, Any]] = []

    # ─── Página init ─────────────────────────────────────────────────
    # Renombrado para evitar shadowing del guard en `State.page_init_promociones`
    # (ver nota en quotation_state.bg_load_quotations).

    @rx.var(cache=True)
    def filtered_promotion_products(self) -> list[dict[str, Any]]:
        """Productos filtrados por el buscador del formulario."""
        search = (self.promo_product_search or "").strip().lower()
        if not search:
            return self.promotion_products
        return [
            p for p in self.promotion_products
            if search in (p.get("description") or "").lower()
            or search in (p.get("barcode") or "").lower()
        ]

    @rx.event
    async def bg_load_promotions(self):
        guard = self._require_active_subscription()
        if guard:
            yield guard
            return
        await self._load_promotions()
        await self._load_promo_categories()
        await self._load_promo_products()

    # ─── Carga ───────────────────────────────────────────────────────

    async def _load_promotions(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return

        from app.models.promotions import PromotionProduct
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

            # Cargar product_ids multi-producto para promos con scope=PRODUCT
            promo_ids = [p.id for p in rows if p.scope == PromotionScope.PRODUCT]
            pp_map: dict[int, list[int]] = {}
            if promo_ids:
                pp_rows = session.exec(
                    select(PromotionProduct).where(
                        PromotionProduct.promotion_id.in_(promo_ids)
                    )
                ).all()
                for pp in pp_rows:
                    pp_map.setdefault(pp.promotion_id, []).append(pp.product_id)

        now = utc_now_naive()
        result = []
        for p in rows:
            product_ids = pp_map.get(p.id) or (
                [p.product_id] if p.product_id else []
            )
            scope_label = _SCOPE_LABELS.get(p.scope, p.scope)
            if p.scope == PromotionScope.CATEGORY and p.category:
                scope_label = f"Categoría: {p.category}"
            elif p.scope == PromotionScope.PRODUCT and product_ids:
                scope_label = (
                    f"Producto específico"
                    if len(product_ids) == 1
                    else f"{len(product_ids)} productos"
                )

            status, status_label = _compute_status(p, now)
            usage_label = _format_usage(p.current_uses or 0, p.max_uses)
            is_running = status == "active"

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
                "status": status,
                "status_label": status_label,
                "usage_label": usage_label,
                "current_uses": p.current_uses or 0,
                "max_uses": p.max_uses,
                "product_id": p.product_id,
                "product_ids": product_ids,
                "category": p.category or "",
                "weekdays_mask": p.weekdays_mask or 127,
                "weekdays_label": _format_weekdays(p.weekdays_mask or 127),
                "time_from": p.time_from.strftime("%H:%M") if p.time_from else "",
                "time_to": p.time_to.strftime("%H:%M") if p.time_to else "",
                "time_window_label": (
                    f"{p.time_from.strftime('%H:%M')}–{p.time_to.strftime('%H:%M')}"
                    if p.time_from and p.time_to
                    else ""
                ),
                "coupon_code": p.coupon_code or "",
                "min_cart_amount": float(p.min_cart_amount or 0),
                "min_cart_amount_label": _format_min_cart(p.min_cart_amount or 0),
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

    async def _load_promo_products(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return
        from app.models import Product
        from app.utils.tenant import set_tenant_context
        set_tenant_context(company_id, branch_id)
        with rx.session() as session:
            stmt = (
                select(Product.id, Product.description, Product.barcode, Product.category)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
                .where(Product.is_active == True)  # noqa: E712
                .order_by(Product.description)
            )
            rows = session.exec(stmt).all()
        self.promotion_products = [
            {
                "id": r[0],
                "description": r[1],
                "barcode": r[2] or "",
                "category": r[3] or "",
                "label": f"{r[1]} ({r[2]})" if r[2] else r[1],
            }
            for r in rows
        ]

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
        self.promo_product_ids = []
        self.promo_product_search = ""
        self.promo_category = ""
        self.promo_is_active = True
        self._set_weekdays_from_mask(127)
        self.promo_time_from = ""
        self.promo_time_to = ""
        self.promo_coupon_code = ""
        self.promo_min_cart_amount = ""
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
        # Multi-producto: cargar desde product_ids; fallback a product_id legacy
        saved_pids = promo.get("product_ids") or []
        if not saved_pids and promo.get("product_id"):
            saved_pids = [promo["product_id"]]
        self.promo_product_ids = [str(pid) for pid in saved_pids]
        self.promo_product_search = ""
        self.promo_category = promo.get("category", "")
        self.promo_is_active = promo.get("is_active", True)
        self._set_weekdays_from_mask(promo.get("weekdays_mask", 127) or 127)
        self.promo_time_from = promo.get("time_from", "") or ""
        self.promo_time_to = promo.get("time_to", "") or ""
        self.promo_coupon_code = promo.get("coupon_code", "") or ""
        min_cart = promo.get("min_cart_amount") or 0
        self.promo_min_cart_amount = (
            "" if not min_cart or float(min_cart) <= 0 else str(min_cart)
        )
        self.show_promotion_form = True
        self.promo_form_key += 1

    def _set_weekdays_from_mask(self, mask: int) -> None:
        self.promo_day_mon = bool(mask & 1)
        self.promo_day_tue = bool(mask & 2)
        self.promo_day_wed = bool(mask & 4)
        self.promo_day_thu = bool(mask & 8)
        self.promo_day_fri = bool(mask & 16)
        self.promo_day_sat = bool(mask & 32)
        self.promo_day_sun = bool(mask & 64)

    def _weekdays_to_mask(self) -> int:
        return (
            (1 if self.promo_day_mon else 0)
            | (2 if self.promo_day_tue else 0)
            | (4 if self.promo_day_wed else 0)
            | (8 if self.promo_day_thu else 0)
            | (16 if self.promo_day_fri else 0)
            | (32 if self.promo_day_sat else 0)
            | (64 if self.promo_day_sun else 0)
        )

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
    def toggle_promo_product_id(self, product_id_str: str):
        ids = list(self.promo_product_ids)
        if product_id_str in ids:
            ids.remove(product_id_str)
        else:
            ids.append(product_id_str)
        self.promo_product_ids = ids

    @rx.event
    def set_promo_product_search(self, v: str): self.promo_product_search = v

    @rx.event
    def set_promo_category(self, v: str): self.promo_category = v
    @rx.event
    def set_promo_is_active(self, v: bool): self.promo_is_active = v
    @rx.event
    def set_promo_day_mon(self, v: bool): self.promo_day_mon = v
    @rx.event
    def set_promo_day_tue(self, v: bool): self.promo_day_tue = v
    @rx.event
    def set_promo_day_wed(self, v: bool): self.promo_day_wed = v
    @rx.event
    def set_promo_day_thu(self, v: bool): self.promo_day_thu = v
    @rx.event
    def set_promo_day_fri(self, v: bool): self.promo_day_fri = v
    @rx.event
    def set_promo_day_sat(self, v: bool): self.promo_day_sat = v
    @rx.event
    def set_promo_day_sun(self, v: bool): self.promo_day_sun = v
    @rx.event
    def set_promo_time_from(self, v: str): self.promo_time_from = v
    @rx.event
    def set_promo_time_to(self, v: str): self.promo_time_to = v
    @rx.event
    def set_promo_coupon_code(self, v: str):
        self.promo_coupon_code = (v or "").upper().strip()
    @rx.event
    def set_promo_min_cart_amount(self, v: float):
        self.promo_min_cart_amount = "" if not v or v <= 0 else str(v)

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

            if self.promo_scope == PromotionScope.PRODUCT and not self.promo_product_ids:
                yield rx.toast(
                    "Seleccioná al menos un producto para el ámbito 'Producto específico'.",
                    duration=3500,
                )
                return
            if self.promo_scope == PromotionScope.CATEGORY and not self.promo_category.strip():
                yield rx.toast(
                    "Seleccioná una categoría para el ámbito 'Por categoría'.",
                    duration=3500,
                )
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

                # Validar y resolver los productos seleccionados.
                # Solo persiste product_id/join-rows cuando scope == PRODUCT.
                resolved_product_id: int | None = None
                resolved_product_ids: list[int] = []
                if self.promo_scope == PromotionScope.PRODUCT and self.promo_product_ids:
                    from app.models import Product as _Product
                    from app.models.promotions import PromotionProduct
                    for pid_str in self.promo_product_ids:
                        try:
                            candidate_pid = int(pid_str)
                        except (ValueError, TypeError):
                            continue
                        candidate = session.exec(
                            select(_Product)
                            .where(_Product.id == candidate_pid)
                            .where(_Product.company_id == company_id)
                            .where(_Product.branch_id == branch_id)
                        ).first()
                        if not candidate:
                            yield rx.toast(
                                f"Producto ID {candidate_pid} no pertenece a esta empresa/sucursal.",
                                duration=3500,
                            )
                            return
                        resolved_product_ids.append(candidate.id)
                    if resolved_product_ids:
                        resolved_product_id = resolved_product_ids[0]

                resolved_category: str | None = None
                if self.promo_scope == PromotionScope.CATEGORY:
                    resolved_category = self.promo_category.strip() or None

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
                promo.product_id = resolved_product_id
                promo.category = resolved_category
                promo.is_active = self.promo_is_active

                mask = self._weekdays_to_mask()
                if mask == 0:
                    yield rx.toast(
                        "Seleccioná al menos un día de la semana.",
                        duration=3500,
                    )
                    return
                promo.weekdays_mask = mask

                tf = _parse_time(self.promo_time_from)
                tt = _parse_time(self.promo_time_to)
                if (tf is None) ^ (tt is None):
                    yield rx.toast(
                        "Definí ambas horas (desde y hasta) o dejá las dos vacías.",
                        duration=3500,
                    )
                    return
                promo.time_from = tf
                promo.time_to = tt

                # Cupón: vacío = automática. Validar unicidad por company.
                coupon = (self.promo_coupon_code or "").strip().upper() or None
                if coupon:
                    existing = session.exec(
                        select(Promotion)
                        .where(Promotion.company_id == company_id)
                        .where(Promotion.coupon_code == coupon)
                        .where(Promotion.id != (promo.id or 0))
                    ).first()
                    if existing:
                        yield rx.toast(
                            f"El cupón '{coupon}' ya está en uso por otra promoción.",
                            duration=3500,
                        )
                        return
                promo.coupon_code = coupon

                # Umbral del carrito (opcional). Vacío o 0 = sin umbral.
                # Validamos signo no negativo aquí en vez de delegar al CHECK
                # de BD para devolver un mensaje claro al usuario.
                raw_min_cart = (self.promo_min_cart_amount or "").strip()
                if not raw_min_cart:
                    promo.min_cart_amount = Decimal("0.00")
                else:
                    try:
                        min_cart_val = Decimal(raw_min_cart)
                    except Exception:
                        yield rx.toast(
                            "El monto mínimo de carrito debe ser un número válido.",
                            duration=3500,
                        )
                        return
                    if min_cart_val < 0:
                        yield rx.toast(
                            "El monto mínimo de carrito no puede ser negativo.",
                            duration=3500,
                        )
                        return
                    promo.min_cart_amount = min_cart_val

                session.commit()
                session.refresh(promo)

                # Sync promotion_product join-table
                if self.promo_scope == PromotionScope.PRODUCT:
                    from app.models.promotions import PromotionProduct
                    existing_pp = session.exec(
                        select(PromotionProduct).where(
                            PromotionProduct.promotion_id == promo.id
                        )
                    ).all()
                    existing_ids = {pp.product_id for pp in existing_pp}
                    new_ids = set(resolved_product_ids)
                    for pp in existing_pp:
                        if pp.product_id not in new_ids:
                            session.delete(pp)
                    for pid in new_ids:
                        if pid not in existing_ids:
                            session.add(PromotionProduct(
                                promotion_id=promo.id,
                                product_id=pid,
                            ))
                    session.commit()
                else:
                    # Si se cambió el scope a algo distinto de PRODUCT, limpiar
                    from app.models.promotions import PromotionProduct
                    old_pp = session.exec(
                        select(PromotionProduct).where(
                            PromotionProduct.promotion_id == promo.id
                        )
                    ).all()
                    for pp in old_pp:
                        session.delete(pp)
                    if old_pp:
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


def _parse_time(value: str):
    """Convierte 'HH:MM' o 'HH:MM:SS' a datetime.time, o None si está vacío."""
    from datetime import time as _time
    if not value or not value.strip():
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value.strip(), fmt).time()
        except ValueError:
            continue
    return None


def _compute_status(p: Promotion, now: datetime) -> tuple[str, str]:
    """Determina el estado real de una promo respecto a `now`.

    Orden de prioridad: pausa manual > vencida > programada > agotada > activa.
    """
    if not p.is_active:
        return "paused", "Pausada"
    if p.ends_at.date() < now.date():
        return "expired", "Vencida"
    if p.starts_at > now:
        return "scheduled", "Programada"
    if p.max_uses is not None and (p.current_uses or 0) >= p.max_uses:
        return "exhausted", "Agotada"
    return "active", "Activa"


def _format_usage(current: int, maximum: int | None) -> str:
    if maximum is None:
        return f"{current} usos"
    return f"{current}/{maximum} usos"


_WEEKDAY_SHORT = ["L", "M", "X", "J", "V", "S", "D"]


def _format_min_cart(value) -> str:
    """Etiqueta legible del umbral de carrito. ``""`` cuando no hay umbral."""
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        return ""
    if amount <= 0:
        return ""
    if amount.is_integer():
        return f"Carrito ≥ {int(amount)}"
    return f"Carrito ≥ {amount:.2f}"


def _format_weekdays(mask: int) -> str:
    if mask == 127:
        return "Todos los días"
    if mask == 31:  # L-V
        return "Lunes a Viernes"
    if mask == 96:  # S+D
        return "Fines de semana"
    if mask == 0:
        return "(Ningún día)"
    return " ".join(d for i, d in enumerate(_WEEKDAY_SHORT) if mask & (1 << i))
