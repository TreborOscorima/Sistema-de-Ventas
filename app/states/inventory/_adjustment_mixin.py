"""Mixin de ajuste/verificación de inventario.

Extraído de InventoryState para reducir el tamaño del módulo principal.
Contiene toda la lógica de búsqueda, selección y procesamiento de
ajustes de inventario y verificación física de stock.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, List

import reflex as rx
from sqlalchemy import and_, or_, func
from sqlmodel import select

from app.models import (
    Product,
    ProductBatch,
    ProductVariant,
    StockMovement,
)
from app.utils.barcode import clean_barcode, validate_barcode
from app.utils.sanitization import escape_like
from app.utils.stock import recalculate_stock_totals


class AdjustmentMixin:
    """Métodos de ajuste y verificación de inventario.

    Mixin plano (sin herencia) que agrupa la lógica de:
    - Búsqueda de productos para ajuste
    - Apertura/cierre del modal de verificación
    - Agregado/eliminación de ítems de ajuste
    - Envío del formulario de verificación/ajuste
    """

    # ------------------------------------------------------------------
    # Handlers de cambio en formulario de ajuste (lines 680-699)
    # ------------------------------------------------------------------

    @rx.event
    def handle_inventory_adjustment_change(self, field: str, value: Any):
        self.inventory_adjustment_item[field] = value

        # Buscar productos cuando se escribe en el campo descripción
        if field == "description":
            self._process_inventory_adjustment_search(value)

    @rx.event
    def process_inventory_adjustment_search_blur(self, value: Any):
        """Procesa el buscador al perder foco (ideal para lector de código)."""
        return self._process_inventory_adjustment_search(value)

    @rx.event
    def handle_inventory_adjustment_search_enter(self, key: str, input_id: str):
        """Detecta Enter y fuerza blur para capturar el valor completo."""
        if key == "Enter":
            return rx.call_script(
                f"const el=document.getElementById('{input_id}'); if(el) el.blur();"
            )

    # ------------------------------------------------------------------
    # Modal de verificación de inventario (lines 1857-1903)
    # ------------------------------------------------------------------

    @rx.event
    def open_inventory_check_modal(self):
        if not self.current_user["privileges"]["edit_inventario"]:
            return rx.toast(
                "No tiene permisos para registrar inventario.", duration=3000
            )
        self.inventory_check_modal_open = True
        self.inventory_check_status = "perfecto"
        self.inventory_adjustment_notes = ""
        self.inventory_adjustment_items = []
        self._reset_inventory_adjustment_form()

    @rx.event
    def close_inventory_check_modal(self):
        self.inventory_check_modal_open = False
        self.inventory_check_status = "perfecto"
        self.inventory_adjustment_notes = ""
        self.inventory_adjustment_items = []
        self._reset_inventory_adjustment_form()

    @rx.event
    def set_inventory_check_status(self, status: str):
        if status not in ["perfecto", "ajuste"]:
            return
        self.inventory_check_status = status
        if status == "perfecto":
            self.inventory_adjustment_items = []
            self._reset_inventory_adjustment_form()

    @rx.event
    def set_inventory_adjustment_notes(self, notes: str):
        self.inventory_adjustment_notes = notes

    def _reset_inventory_adjustment_form(self):
        self.inventory_adjustment_item = {
            "temp_id": "",
            "barcode": "",
            "description": "",
            "category": "",
            "unit": "",
            "current_stock": 0,
            "adjust_quantity": 0,
            "reason": "",
            "product_id": None,
            "variant_id": None,
        }
        self.inventory_adjustment_suggestions = []

    # ------------------------------------------------------------------
    # Helpers privados de búsqueda/llenado (lines 1916-2080)
    # ------------------------------------------------------------------

    def _fill_inventory_adjustment_from_product(
        self, product: Product, variant: ProductVariant | None = None
    ):
        def _field(obj: Any, name: str, default: Any = "") -> Any:
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        barcode = variant.sku if variant else _field(product, "barcode", "")
        description = _field(product, "description", "")
        if variant:
            label = self._variant_label(variant)
            if label:
                description = f"{description} ({label})"
        self.inventory_adjustment_item["barcode"] = barcode or ""
        self.inventory_adjustment_item["description"] = description or ""
        self.inventory_adjustment_item["category"] = _field(product, "category", "")
        self.inventory_adjustment_item["unit"] = _field(product, "unit", "Unidad")
        self.inventory_adjustment_item["current_stock"] = (
            variant.stock if variant else _field(product, "stock", 0)
        )
        self.inventory_adjustment_item["product_id"] = _field(product, "id", None)
        self.inventory_adjustment_item["variant_id"] = variant.id if variant else None
        self.inventory_adjustment_item["adjust_quantity"] = 0
        self.inventory_adjustment_item["reason"] = ""

    def _product_has_variants(
        self,
        session,
        product_id: int,
        company_id: int,
        branch_id: int,
    ) -> bool:
        if not product_id:
            return False
        return (
            session.exec(
                select(ProductVariant.id)
                .where(ProductVariant.product_id == product_id)
                .where(ProductVariant.company_id == company_id)
                .where(ProductVariant.branch_id == branch_id)
                .limit(1)
            ).first()
            is not None
        )

    def _get_batches_for_adjustment(
        self,
        session,
        product: Product,
        variant: ProductVariant | None,
        company_id: int,
        branch_id: int,
        lock: bool = False,
    ) -> list[ProductBatch]:
        if variant:
            query = select(ProductBatch).where(
                ProductBatch.product_variant_id == variant.id
            )
        else:
            query = (
                select(ProductBatch)
                .where(ProductBatch.product_id == product.id)
                .where(ProductBatch.product_variant_id.is_(None))
            )
        query = (
            query.where(ProductBatch.company_id == company_id)
            .where(ProductBatch.branch_id == branch_id)
            .order_by(
                ProductBatch.expiration_date.is_(None),
                ProductBatch.expiration_date.asc(),
                ProductBatch.id.asc(),
            )
        )
        if lock:
            query = query.with_for_update()
        return session.exec(query).all()

    def _find_adjustment_product(
        self,
        session,
        barcode: str,
        description: str,
        variant_id: int | None = None,
        product_id: int | None = None,
        for_update: bool = False,
    ) -> tuple[Product | None, ProductVariant | None]:
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return None, None
        def _maybe_lock(statement):
            return statement.with_for_update() if for_update else statement
        if variant_id:
            variant = session.exec(
                _maybe_lock(
                    select(ProductVariant)
                    .where(ProductVariant.id == variant_id)
                    .where(ProductVariant.company_id == company_id)
                    .where(ProductVariant.branch_id == branch_id)
                )
            ).first()
            if variant:
                product = session.exec(
                    _maybe_lock(
                        select(Product)
                        .where(Product.id == variant.product_id)
                        .where(Product.company_id == company_id)
                        .where(Product.branch_id == branch_id)
                    )
                ).first()
                return product, variant
        if product_id:
            product = session.exec(
                _maybe_lock(
                    select(Product)
                    .where(Product.id == product_id)
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                )
            ).first()
            if product:
                return product, None
        if barcode:
            variant = session.exec(
                _maybe_lock(
                    select(ProductVariant)
                    .where(ProductVariant.sku == barcode)
                    .where(ProductVariant.company_id == company_id)
                    .where(ProductVariant.branch_id == branch_id)
                )
            ).first()
            if variant:
                product = session.exec(
                    _maybe_lock(
                        select(Product)
                        .where(Product.id == variant.product_id)
                        .where(Product.company_id == company_id)
                        .where(Product.branch_id == branch_id)
                    )
                ).first()
                return product, variant
            product = session.exec(
                _maybe_lock(
                    select(Product)
                    .where(Product.barcode == barcode)
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                )
            ).first()
            if product:
                return product, None
        if description:
            product = session.exec(
                _maybe_lock(
                    select(Product)
                    .where(Product.description == description)
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                )
            ).first()
            if product:
                return product, None
        return None, None

    # ------------------------------------------------------------------
    # Búsqueda y selección de productos para ajuste (lines 2081-2309)
    # ------------------------------------------------------------------

    def _process_inventory_adjustment_search(self, value: Any):
        term = str(value or "").strip()
        self.inventory_adjustment_item["description"] = term
        if not term:
            self.inventory_adjustment_suggestions = []
            return

        code = clean_barcode(term)
        if validate_barcode(code):
            with rx.session() as session:
                product, variant = self._find_adjustment_product(
                    session, code, "", None, None
                )
                if product:
                    self._fill_inventory_adjustment_from_product(product, variant)
                    self.inventory_adjustment_suggestions = []
                    return

        search_term = term.lower()
        if len(search_term) < 2:
            self.inventory_adjustment_suggestions = []
            return
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.inventory_adjustment_suggestions = []
            return
        with rx.session() as session:
            search = f"%{escape_like(search_term)}%"
            products = session.exec(
                select(Product)
                .where(
                    or_(
                        Product.description.ilike(search),
                        Product.barcode.ilike(search),
                    )
                )
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
                .limit(8)
            ).all()
            variant_rows = session.exec(
                select(ProductVariant, Product)
                .join(Product, ProductVariant.product_id == Product.id)
                .where(
                    or_(
                        ProductVariant.sku.ilike(search),
                        ProductVariant.size.ilike(search),
                        ProductVariant.color.ilike(search),
                        Product.description.ilike(search),
                    )
                )
                .where(ProductVariant.company_id == company_id)
                .where(ProductVariant.branch_id == branch_id)
                .limit(8)
            ).all()

        suggestions: list[dict] = []
        for product in products:
            suggestions.append(
                {
                    "label": product.description,
                    "kind": "product",
                    "product_id": product.id,
                    "variant_id": None,
                }
            )
        for variant, parent in variant_rows:
            label = self._variant_label(variant)
            full_label = parent.description
            if label:
                full_label = f"{parent.description} ({label})"
            suggestions.append(
                {
                    "label": full_label,
                    "kind": "variant",
                    "product_id": parent.id,
                    "variant_id": variant.id,
                }
            )
        self.inventory_adjustment_suggestions = suggestions

    @rx.event
    def select_inventory_adjustment_product(self, description: Any):
        variant_id = None
        product_id = None
        if isinstance(description, dict):
            variant_id = description.get("variant_id")
            product_id = description.get("product_id")
            description = (
                description.get("value")
                or description.get("description")
                or description.get("label")
                or ""
            )
        description = str(description or "").strip()
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return

        code = clean_barcode(description)
        barcode = code if validate_barcode(code) else ""
        with rx.session() as session:
            product, variant = self._find_adjustment_product(
                session,
                barcode,
                description,
                int(variant_id) if variant_id else None,
                int(product_id) if product_id else None,
            )
            if product:
                self._fill_inventory_adjustment_from_product(product, variant)
        self.inventory_adjustment_suggestions = []

    @rx.event
    def set_inventory_adjustment_item_barcode(self, value: str):
        self.inventory_adjustment_item["barcode"] = value

    @rx.event
    def set_inventory_adjustment_item_quantity(self, value: str):
        try:
            self.inventory_adjustment_item["adjust_quantity"] = float(value)
        except ValueError:
            self.inventory_adjustment_item["adjust_quantity"] = 0

    @rx.event
    def set_inventory_adjustment_item_reason(self, value: str):
        self.inventory_adjustment_item["reason"] = value

    @rx.event
    def add_inventory_adjustment_item(self):
        if not self.current_user["privileges"]["edit_inventario"]:
            return rx.toast("No tiene permisos para ajustar inventario.", duration=3000)
        description = self.inventory_adjustment_item["description"].strip()
        barcode = (self.inventory_adjustment_item.get("barcode") or "").strip()
        if not description and not barcode:
            return rx.toast("Seleccione un producto para ajustar.", duration=3000)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)

        with rx.session() as session:
            if description and not barcode:
                duplicate_count = session.exec(
                    select(func.count(Product.id))
                    .where(Product.description == description)
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                ).one()
                if duplicate_count and duplicate_count > 1:
                    return rx.toast(
                        "Descripcion duplicada en inventario. Use codigo de barras.",
                        duration=3000,
                    )
            product, variant = self._find_adjustment_product(
                session,
                barcode,
                description,
                self.inventory_adjustment_item.get("variant_id"),
                self.inventory_adjustment_item.get("product_id"),
            )
            if not product:
                return rx.toast("Producto no encontrado en el inventario.", duration=3000)

            if not variant and self._product_has_variants(
                session, product.id, company_id, branch_id
            ):
                return rx.toast(
                    "Producto con variantes. Seleccione la variante a ajustar.",
                    duration=3500,
                )

            try:
                quantity = Decimal(
                    str(self.inventory_adjustment_item.get("adjust_quantity", 0) or 0)
                )
            except (InvalidOperation, TypeError, ValueError):
                quantity = Decimal("0")
            if quantity <= 0:
                return rx.toast("Ingrese la cantidad a ajustar.", duration=3000)

            batches = self._get_batches_for_adjustment(
                session, product, variant, company_id, branch_id
            )
            if batches:
                available = sum(
                    (Decimal(str(batch.stock or 0)) for batch in batches),
                    Decimal("0"),
                )
            else:
                available = (
                    Decimal(str(variant.stock or 0))
                    if variant
                    else Decimal(str(product.stock or 0))
                )
            if quantity > available:
                return rx.toast(
                    "La cantidad supera el stock disponible.", duration=3000
                )

            item_copy = self.inventory_adjustment_item.copy()
            item_copy["temp_id"] = str(uuid.uuid4())
            item_copy["product_id"] = product.id
            item_copy["variant_id"] = variant.id if variant else None
            item_copy["adjust_quantity"] = self._normalize_quantity_value(
                item_copy.get("adjust_quantity", 0), item_copy.get("unit", "")
            )
            # Asegurar que la unidad se tome del producto si falta
            if not item_copy.get("unit"):
                item_copy["unit"] = product.unit
            if not item_copy.get("barcode"):
                item_copy["barcode"] = variant.sku if variant else product.barcode
            if not item_copy.get("description"):
                label = self._variant_label(variant) if variant else ""
                item_copy["description"] = (
                    f"{product.description} ({label})" if label else product.description
                )

            self.inventory_adjustment_items.append(item_copy)
            self._reset_inventory_adjustment_form()

    @rx.event
    def remove_inventory_adjustment_item(self, temp_id: str):
        self.inventory_adjustment_items = [
            item for item in self.inventory_adjustment_items if item["temp_id"] != temp_id
        ]

    # ------------------------------------------------------------------
    # Submit de verificación de inventario (lines 2311-2586)
    # ------------------------------------------------------------------

    @rx.event
    def submit_inventory_check(self):
        if not self.current_user["privileges"]["edit_inventario"]:
            return self.add_notification(
                "No tiene permisos para registrar inventario.", "error"
            )
        block = self._require_active_subscription()
        if block:
            return block
        status = (
            self.inventory_check_status
            if self.inventory_check_status in ["perfecto", "ajuste"]
            else "perfecto"
        )
        notes = self.inventory_adjustment_notes.strip()
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return self.add_notification("Empresa no definida.", "error")

        self.is_loading = True
        yield
        refresh_needed = False

        success_message = "Registro de inventario guardado."
        try:
            if status == "perfecto":
                success_message = "Inventario verificado como perfecto."
            else:
                if not self.inventory_adjustment_items:
                    return self.add_notification(
                        "Agregue los productos que requieren re ajuste.", "error"
                    )

                recorded = False
                def _to_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
                    try:
                        return Decimal(str(value))
                    except (InvalidOperation, TypeError, ValueError):
                        return default

                with rx.session() as session:
                    products_to_recalculate: set[int] = set()
                    products_recalc_batches: set[int] = set()
                    variants_recalc_batches: set[int] = set()

                    # ── Batch pre-load: reduce N+1 a queries fijas ──
                    _items = self.inventory_adjustment_items
                    _product_ids: set[int] = set()
                    _variant_ids: set[int] = set()
                    for _it in _items:
                        _pid = _it.get("product_id")
                        _vid = _it.get("variant_id")
                        if _pid:
                            _product_ids.add(int(_pid))
                        if _vid:
                            _variant_ids.add(int(_vid))

                    # Query 1: Productos (con lock)
                    _products_map: dict[int, Product] = {}
                    if _product_ids:
                        _prods = session.exec(
                            select(Product)
                            .where(Product.id.in_(_product_ids))
                            .where(Product.company_id == company_id)
                            .where(Product.branch_id == branch_id)
                            .with_for_update()
                        ).all()
                        _products_map = {p.id: p for p in _prods}

                    # Query 2: Variantes (con lock)
                    _variants_map: dict[int, ProductVariant] = {}
                    if _variant_ids:
                        _vars = session.exec(
                            select(ProductVariant)
                            .where(ProductVariant.id.in_(_variant_ids))
                            .where(ProductVariant.company_id == company_id)
                            .where(ProductVariant.branch_id == branch_id)
                            .with_for_update()
                        ).all()
                        _variants_map = {v.id: v for v in _vars}

                    # Query 3: Batches de variantes + productos (con lock)
                    _variant_batches: dict[int, list[ProductBatch]] = {}
                    _product_batches: dict[int, list[ProductBatch]] = {}
                    _batch_conditions = []
                    if _variant_ids:
                        _batch_conditions.append(
                            ProductBatch.product_variant_id.in_(_variant_ids)
                        )
                    if _product_ids:
                        _batch_conditions.append(
                            and_(
                                ProductBatch.product_id.in_(_product_ids),
                                ProductBatch.product_variant_id.is_(None),
                            )
                        )
                    if _batch_conditions:
                        _all_batches = session.exec(
                            select(ProductBatch)
                            .where(or_(*_batch_conditions))
                            .where(ProductBatch.company_id == company_id)
                            .where(ProductBatch.branch_id == branch_id)
                            .order_by(
                                ProductBatch.expiration_date.is_(None),
                                ProductBatch.expiration_date.asc(),
                                ProductBatch.id.asc(),
                            )
                            .with_for_update()
                        ).all()
                        for _b in _all_batches:
                            if _b.product_variant_id:
                                _variant_batches.setdefault(
                                    _b.product_variant_id, []
                                ).append(_b)
                            else:
                                _product_batches.setdefault(
                                    _b.product_id, []
                                ).append(_b)

                    # Query 4: Productos que tienen variantes (para skip)
                    _products_with_variants: set[int] = set()
                    if _product_ids:
                        _has_vars = session.exec(
                            select(ProductVariant.product_id)
                            .where(ProductVariant.product_id.in_(_product_ids))
                            .where(ProductVariant.company_id == company_id)
                            .where(ProductVariant.branch_id == branch_id)
                            .distinct()
                        ).all()
                        _products_with_variants = set(_has_vars)

                    for item in _items:
                        description = (item.get("description") or "").strip()
                        barcode = (item.get("barcode") or "").strip()
                        if not description and not barcode:
                            continue

                        # Lookup desde maps pre-cargados
                        _pid = item.get("product_id")
                        _vid = item.get("variant_id")
                        product = _products_map.get(int(_pid)) if _pid else None
                        variant = _variants_map.get(int(_vid)) if _vid else None

                        # Fallback a búsqueda individual (raro: item sin IDs)
                        if not product:
                            product, variant = self._find_adjustment_product(
                                session, barcode, description,
                                _vid, _pid, for_update=True,
                            )
                        if not product:
                            continue
                        if not variant and product.id in _products_with_variants:
                            continue

                        quantity = _to_decimal(item.get("adjust_quantity", 0) or 0)
                        if quantity <= 0:
                            continue

                        unit = product.unit or item.get("unit") or ""
                        # Batches desde maps pre-cargados
                        if variant:
                            batches = _variant_batches.get(variant.id, [])
                        else:
                            batches = _product_batches.get(product.id, [])
                        if batches:
                            available = sum(
                                (_to_decimal(batch.stock, Decimal("0")) for batch in batches),
                                Decimal("0"),
                            )
                            qty = quantity if quantity <= available else available
                            if qty <= 0:
                                continue
                            remaining = qty
                            for batch in batches:
                                if remaining <= 0:
                                    break
                                current_stock = _to_decimal(batch.stock, Decimal("0"))
                                if current_stock <= 0:
                                    continue
                                deduct = remaining if remaining <= current_stock else current_stock
                                batch.stock = current_stock - deduct
                                session.add(batch)
                                remaining -= deduct
                            total_after = sum(
                                (_to_decimal(batch.stock, Decimal("0")) for batch in batches),
                                Decimal("0"),
                            )
                            if variant:
                                variant.stock = self._normalize_quantity_value(
                                    total_after, unit
                                )
                                session.add(variant)
                                variants_recalc_batches.add(variant.id)
                                products_to_recalculate.add(product.id)
                            else:
                                product.stock = self._normalize_quantity_value(
                                    total_after, unit
                                )
                                session.add(product)
                                products_recalc_batches.add(product.id)
                        else:
                            available = _to_decimal(
                                (variant.stock if variant else product.stock) or 0
                            )
                            qty = quantity if quantity <= available else available
                            if qty <= 0:
                                continue

                            # Actualizar stock
                            if variant:
                                variant.stock = max(available - qty, Decimal("0"))
                                session.add(variant)
                                products_to_recalculate.add(product.id)
                            else:
                                product.stock = max(available - qty, Decimal("0"))
                                session.add(product)

                        # Crear StockMovement
                        detail_parts = []
                        if item.get("reason"):
                            detail_parts.append(item["reason"])
                        if notes:
                            detail_parts.append(notes)
                        details = (
                            " | ".join(part for part in detail_parts if part)
                            if detail_parts
                            else "Ajuste inventario"
                        )

                        movement = StockMovement(
                            product_id=product.id,
                            user_id=self.current_user.get("id"),
                            type="Re Ajuste Inventario",
                            quantity=-qty,
                            description=details,
                            timestamp=self._utc_now(),
                            company_id=company_id,
                            branch_id=branch_id,
                        )
                        session.add(movement)
                        recorded = True

                    # Recalcular totales de stock (3 fases) usando helper compartido
                    recalculate_stock_totals(
                        session=session,
                        company_id=company_id,
                        branch_id=branch_id,
                        variants_from_batches=variants_recalc_batches,
                        products_from_variants=products_to_recalculate,
                        products_from_batches=products_recalc_batches,
                        normalize_fn=lambda total, prod: self._normalize_quantity_value(
                            total, prod.unit or ""
                        ),
                    )

                    if recorded:
                        session.commit()
                        self._inventory_update_trigger += 1
                        refresh_needed = True
                    else:
                        return self.add_notification(
                            "No se pudo registrar el re ajuste. Verifique los productos.",
                            "error",
                        )
        finally:
            self.is_loading = False

        self.inventory_check_modal_open = False
        self.inventory_check_status = "perfecto"
        self.inventory_adjustment_notes = ""
        self.inventory_adjustment_items = []
        self._reset_inventory_adjustment_form()
        if refresh_needed:
            self._refresh_inventory_cache()
        return self.add_notification(success_message, "success")
