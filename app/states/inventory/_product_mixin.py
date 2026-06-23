"""Mixin de Product CRUD y handlers de variantes/lotes/tiers/atributos/kits.

Extraído de inventory_state.py — métodos de edición, creación y eliminación
de productos junto con la gestión de UI para variantes, precios por mayor,
lotes con vencimiento, atributos dinámicos (EAV) y composición de kits.
"""

import reflex as rx
import datetime
import logging
from typing import List, Dict, Any
from decimal import Decimal, InvalidOperation
from sqlmodel import select

from app.models import (
    Product,
    ProductAttribute,
    ProductBatch,
    ProductKit,
    ProductVariant,
    PriceTier,
    SaleItem,
    Supplier,
)
from app.utils.formatting import fmt_input_num, fmt_price

logger = logging.getLogger(__name__)


class ProductMixin:
    """Mixin con métodos de Product CRUD y handlers de variantes/lotes/tiers/atributos/kits."""

    @rx.event
    def open_edit_product(self, product: Product | Dict[str, Any] | None = None):
        if not self.current_user["privileges"]["edit_inventario"]:
            return rx.toast("No tiene permisos para editar el inventario.", duration=3000)

        if product is None:
            self.editing_product = {
                "id": None,
                "barcode": "",
                "description": "",
                "category": "",
                "stock": 0,
                "unit": "",
                "purchase_price": 0,
                "sale_price": 0,
                "default_supplier_id": None,
            }
            self.show_variants = False
            self.show_wholesale = False
            self.show_batches = False
            self.show_attributes = False
            self.show_kit_components = False
            self.variants = []
            self.price_tiers = []
            self.batches = []
            self.attributes = []
            self.kit_components = []
            company_id = self._company_id()
            branch_id = self._branch_id()
            if company_id and branch_id:
                with rx.session() as session:
                    session.info["tenant_bypass"] = True
                    sups = session.exec(
                        select(Supplier)
                        .where(Supplier.company_id == company_id)
                        .where(Supplier.branch_id == branch_id)
                        .where(Supplier.is_active == True)
                        .order_by(Supplier.name)
                    ).all()
                    self.inventory_suppliers = [{"id": s.id, "name": s.name} for s in sups]
            self.is_editing_product = True
            return

        def _read_value(key: str, default: Any = "") -> Any:
            if isinstance(product, dict):
                return product.get(key, default)
            return getattr(product, key, default)

        product_id = _read_value("id", None)

        raw_margin = _read_value("custom_profit_margin", None)
        pp = float(_read_value("purchase_price", 0) or 0)
        variant_id = _read_value("variant_id", None)
        variant_has_own_price = bool(_read_value("variant_has_own_price", False))

        # Resolución de P. VENTA y % Ganancia para el formulario:
        #
        # Caso 1 — Variante con precio propio explícito (el usuario lo personalizó
        #   o redondeó): mostrar ese precio y calcular el margen efectivo real.
        #
        # Caso 2 — Producto/variante con margen personalizado (custom_profit_margin
        #   NOT NULL): recalcular P. VENTA desde ese margen.
        #
        # Caso 3 — Sin precio propio ni margen custom: el producto sigue el margen
        #   global/sucursal vigente → recalcular P. VENTA desde ese margen.
        #   Efecto: cambiar el margen global y abrir este modal ya muestra el
        #   precio actualizado listo para guardar.

        if variant_id and variant_has_own_price:
            # Caso 1
            sp = float(_read_value("sale_price", 0) or 0)
            if raw_margin is None and pp > 0 and sp > 0:
                eff = (sp - pp) / pp * 100
                raw_margin = round(eff, 2)
            sale_price_for_form = sp
        elif raw_margin is not None:
            # Caso 2
            try:
                sale_price_for_form = pp * (1 + float(raw_margin) / 100) if pp > 0 else 0.0
            except (TypeError, ValueError):
                sale_price_for_form = float(_read_value("sale_price", 0) or 0)
        else:
            # Caso 3 — margen global vigente
            global_margin = getattr(self, "effective_profit_margin_decimal", 0.0)
            sale_price_for_form = pp * (1 + global_margin / 100) if pp > 0 else 0.0

        self.editing_product = {
            "id": product_id,
            "variant_id": variant_id,
            "barcode": _read_value("barcode", ""),
            "description": _read_value("description", ""),
            "category": _read_value("category", ""),
            "stock": _read_value("stock", 0),
            "unit": _read_value("unit", ""),
            "purchase_price": fmt_price(pp),
            "sale_price": fmt_price(sale_price_for_form),
            "custom_profit_margin": str(raw_margin) if raw_margin is not None else "",
            "default_supplier_id": _read_value("default_supplier_id", None),
        }

        self.show_variants = False
        self.show_wholesale = False
        self.show_batches = False
        self.show_attributes = False
        self.show_kit_components = False
        self.variants = []
        self.price_tiers = []
        self.batches = []
        self.attributes = []
        self.kit_components = []

        company_id = self._company_id()
        branch_id = self._branch_id()
        if company_id and branch_id:
            with rx.session() as session:
                session.info["tenant_bypass"] = True
                sups = session.exec(
                    select(Supplier)
                    .where(Supplier.company_id == company_id)
                    .where(Supplier.branch_id == branch_id)
                    .where(Supplier.is_active == True)
                    .order_by(Supplier.name)
                ).all()
                self.inventory_suppliers = [{"id": s.id, "name": s.name} for s in sups]
        if company_id and branch_id and product_id:
            with rx.session() as session:
                session.info["tenant_bypass"] = True
                variants = session.exec(
                    select(ProductVariant)
                    .where(ProductVariant.product_id == product_id)
                    .where(ProductVariant.company_id == company_id)
                    .where(ProductVariant.branch_id == branch_id)
                    .order_by(ProductVariant.id)
                ).all()
                if variants:
                    self.variants = [
                        {
                            "sku": variant.sku,
                            "size": variant.size or "",
                            "color": variant.color or "",
                            "stock": float(variant.stock or 0),
                        }
                        for variant in variants
                    ]
                    total_stock = sum(
                        float(variant.stock or 0) for variant in variants
                    )
                    self.editing_product["stock"] = total_stock
                    self.show_variants = True

                tiers = session.exec(
                    select(PriceTier)
                    .where(PriceTier.product_id == product_id)
                    .where(PriceTier.company_id == company_id)
                    .where(PriceTier.branch_id == branch_id)
                    .order_by(PriceTier.min_quantity)
                ).all()
                if tiers:
                    self.price_tiers = [
                        {
                            "min_qty": tier.min_quantity,
                            "price": fmt_price(float(tier.unit_price or 0)),
                        }
                        for tier in tiers
                    ]
                    self.show_wholesale = True

                # Cargar lotes (batches) — sin variant_id, scoped al producto
                product_batches = session.exec(
                    select(ProductBatch)
                    .where(ProductBatch.product_id == product_id)
                    .where(ProductBatch.product_variant_id.is_(None))
                    .where(ProductBatch.company_id == company_id)
                    .where(ProductBatch.branch_id == branch_id)
                    .order_by(ProductBatch.expiration_date)
                ).all()
                if product_batches:
                    self.batches = [
                        {
                            "id": batch.id,
                            "batch_number": batch.batch_number,
                            "expiration_date": (
                                batch.expiration_date.strftime("%Y-%m-%d")
                                if batch.expiration_date
                                else ""
                            ),
                            "stock": float(batch.stock or 0),
                        }
                        for batch in product_batches
                    ]
                    self.show_batches = True

                # Cargar atributos dinámicos (EAV)
                product_attrs = session.exec(
                    select(ProductAttribute)
                    .where(ProductAttribute.product_id == product_id)
                    .where(ProductAttribute.company_id == company_id)
                    .where(ProductAttribute.branch_id == branch_id)
                    .order_by(ProductAttribute.attribute_name)
                ).all()
                if product_attrs:
                    self.attributes = [
                        {
                            "id": attr.id,
                            "name": attr.attribute_name,
                            "value": attr.attribute_value,
                        }
                        for attr in product_attrs
                    ]
                    self.show_attributes = True

                # Cargar componentes de kit
                kit_comps = session.exec(
                    select(ProductKit)
                    .where(ProductKit.kit_product_id == product_id)
                    .where(ProductKit.company_id == company_id)
                    .where(ProductKit.branch_id == branch_id)
                ).all()
                if kit_comps:
                    comp_ids = [c.component_product_id for c in kit_comps]
                    comp_products = session.exec(
                        select(Product).where(Product.id.in_(comp_ids))
                    ).all()
                    comp_map = {p.id: p for p in comp_products}
                    variant_ids = [c.component_variant_id for c in kit_comps if c.component_variant_id]
                    variant_map: dict = {}
                    if variant_ids:
                        variants = session.exec(
                            select(ProductVariant).where(ProductVariant.id.in_(variant_ids))
                        ).all()
                        variant_map = {v.id: v for v in variants}
                    rows = []
                    for c in kit_comps:
                        prod = comp_map.get(c.component_product_id)
                        variant = variant_map.get(c.component_variant_id) if c.component_variant_id else None
                        if variant:
                            display_barcode = variant.sku or ""
                            variant_label = " ".join(filter(None, [variant.size, variant.color]))
                        else:
                            display_barcode = (prod.barcode or "") if prod else ""
                            variant_label = ""
                        rows.append({
                            "id": c.id,
                            "component_barcode": display_barcode,
                            "component_name": (prod.description or "") if prod else "",
                            "component_product_id": c.component_product_id,
                            "component_variant_id": c.component_variant_id,
                            "variant_label": variant_label,
                            "quantity": float(c.quantity or 1),
                        })
                    self.kit_components = rows
                    self.show_kit_components = True

        self.is_editing_product = True

    @rx.event
    def open_create_product_modal(self):
        if not self.current_user["privileges"]["edit_inventario"]:
            return rx.toast("No tiene permisos para editar el inventario.", duration=3000)
        self.editing_product = {
            "id": None,
            "barcode": "",
            "description": "",
            "category": "",
            "stock": 0,
            "unit": "",
            "purchase_price": 0,
            "sale_price": 0,
            "default_supplier_id": None,
        }
        self.show_variants = False
        self.show_wholesale = False
        self.show_batches = False
        self.show_attributes = False
        self.show_kit_components = False
        self.confirm_disable_wholesale = False
        self.variants = []
        self.price_tiers = []
        self.batches = []
        self.attributes = []
        self.kit_components = []
        company_id = self._company_id()
        branch_id = self._branch_id()
        if company_id and branch_id:
            with rx.session() as session:
                session.info["tenant_bypass"] = True
                sups = session.exec(
                    select(Supplier)
                    .where(Supplier.company_id == company_id)
                    .where(Supplier.branch_id == branch_id)
                    .where(Supplier.is_active == True)
                    .order_by(Supplier.name)
                ).all()
                self.inventory_suppliers = [{"id": s.id, "name": s.name} for s in sups]
        self.is_editing_product = True

    @rx.event
    def open_stock_details(self, product: Product | Dict[str, Any]):
        if not self.current_user["privileges"]["view_inventario"]:
            return rx.toast("No tiene permisos para ver el inventario.", duration=3000)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)

        def _read_value(key: str, default: Any = "") -> Any:
            if isinstance(product, dict):
                return product.get(key, default)
            return getattr(product, key, default)

        product_id = _read_value("id", None)
        description = _read_value("description", "")
        if not product_id:
            return rx.toast("Producto no encontrado.", duration=3000)

        self.stock_details_title = str(description or "Detalle de stock")
        self.selected_product_details = []
        self.stock_details_mode = "simple"

        with rx.session() as session:
            session.info["tenant_bypass"] = True
            variants = session.exec(
                select(ProductVariant)
                .where(ProductVariant.product_id == product_id)
                .where(ProductVariant.company_id == company_id)
                .where(ProductVariant.branch_id == branch_id)
                .order_by(ProductVariant.sku)
            ).all()
            if variants:
                self.selected_product_details = [
                    {
                        "sku": variant.sku,
                        "size": variant.size or "",
                        "color": variant.color or "",
                        "stock": variant.stock,
                    }
                    for variant in variants
                ]
                self.stock_details_mode = "variant"
            else:
                batches = session.exec(
                    select(ProductBatch)
                    .where(ProductBatch.product_id == product_id)
                    .where(ProductBatch.company_id == company_id)
                    .where(ProductBatch.branch_id == branch_id)
                    .order_by(ProductBatch.expiration_date)
                ).all()
                if batches:
                    self.selected_product_details = [
                        {
                            "batch_number": batch.batch_number,
                            "expiration_date": (
                                batch.expiration_date.strftime("%Y-%m-%d")
                                if batch.expiration_date
                                else ""
                            ),
                            "stock": batch.stock,
                        }
                        for batch in batches
                    ]
                    self.stock_details_mode = "batch"

        self.stock_details_open = True

    @rx.event
    def close_stock_details(self):
        self.stock_details_open = False
        self.stock_details_title = ""
        self.stock_details_mode = "simple"
        self.selected_product_details = []

    @rx.event
    def cancel_edit_product(self):
        self.is_editing_product = False
        self.editing_product = {
            "id": None,
            "barcode": "",
            "description": "",
            "category": "",
            "stock": 0,
            "unit": "",
            "purchase_price": 0,
            "sale_price": 0,
            "default_supplier_id": None,
        }
        self.show_variants = False
        self.show_wholesale = False
        self.show_batches = False
        self.show_attributes = False
        self.show_kit_components = False
        self.confirm_disable_wholesale = False
        self.variants = []
        self.price_tiers = []
        self.batches = []
        self.attributes = []
        self.kit_components = []

    @rx.event
    def handle_edit_product_change(self, field: str, value: str):
        from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

        def _q(val: float) -> float:
            try:
                return float(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            except InvalidOperation:
                return val

        if field == "profit_margin":
            try:
                value_str = str(value)
            except Exception:
                value_str = ""
            self.editing_product["custom_profit_margin"] = value_str
            try:
                margin = float(value_str) if value_str.strip() else 0.0
                purchase = float(self.editing_product.get("purchase_price") or 0)
                if purchase > 0:
                    self.editing_product["sale_price"] = fmt_price(_q(purchase * (1 + margin / 100)))
                    self.edit_sale_price_key += 1
            except (ValueError, TypeError):
                pass

        elif field == "sale_price":
            try:
                sale = float(str(value)) if str(value).strip() else 0.0
                self.editing_product["sale_price"] = fmt_price(sale)
                purchase = float(self.editing_product.get("purchase_price") or 0)
                if purchase > 0 and sale > 0:
                    self.editing_product["custom_profit_margin"] = str(
                        _q((sale - purchase) / purchase * 100)
                    )
                else:
                    self.editing_product["custom_profit_margin"] = ""
                self.edit_margin_key += 1
            except (ValueError, TypeError):
                pass

        elif field == "purchase_price":
            try:
                purchase = float(str(value)) if str(value).strip() else 0.0
                self.editing_product["purchase_price"] = fmt_price(purchase)
                raw_margin = str(self.editing_product.get("custom_profit_margin") or "").strip()
                if raw_margin and purchase > 0:
                    margin = float(raw_margin)
                    self.editing_product["sale_price"] = fmt_price(_q(purchase * (1 + margin / 100)))
                    self.edit_sale_price_key += 1
                elif purchase > 0:
                    sale = float(self.editing_product.get("sale_price") or 0)
                    if sale > 0:
                        self.editing_product["custom_profit_margin"] = str(
                            _q((sale - purchase) / purchase * 100)
                        )
                        self.edit_margin_key += 1
            except (ValueError, TypeError):
                pass

        elif field == "stock":
            try:
                self.editing_product[field] = float(value) if str(value).strip() else 0.0
            except ValueError:
                pass

        elif field == "default_supplier_id":
            try:
                self.editing_product["default_supplier_id"] = int(value) if value else None
            except (ValueError, TypeError):
                self.editing_product["default_supplier_id"] = None

        else:
            self.editing_product[field] = value

    @rx.var(cache=True)
    def variant_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for index, variant in enumerate(self.variants):
            row = dict(variant)
            row["index"] = index
            rows.append(row)
        return rows

    @rx.var(cache=True)
    def price_tier_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for index, tier in enumerate(self.price_tiers):
            row = dict(tier)
            row["index"] = index
            rows.append(row)
        return rows

    @rx.var(cache=True)
    def variants_stock_total(self) -> float:
        total = 0.0
        for variant in self.variants:
            try:
                total += float(variant.get("stock", 0) or 0)
            except (TypeError, ValueError):
                continue
        return total

    @rx.event
    def set_show_variants(self, value: bool | str):
        if isinstance(value, str):
            value = value.lower() in ["true", "1", "on", "yes"]
        self.show_variants = bool(value)
        if self.show_variants and not self.variants:
            self.add_variant_row()

    @rx.event
    def set_show_wholesale(self, value: bool | str):
        if isinstance(value, str):
            value = value.lower() in ["true", "1", "on", "yes"]
        if not bool(value) and self.price_tiers:
            # Pedir confirmación antes de desactivar si hay tiers configurados
            self.confirm_disable_wholesale = True
            return
        self.show_wholesale = bool(value)
        if self.show_wholesale and not self.price_tiers:
            self.add_tier_row()

    @rx.event
    def confirm_disable_wholesale_yes(self):
        """El usuario confirmó que quiere desactivar mayoreo."""
        self.show_wholesale = False
        self.price_tiers = []
        self.confirm_disable_wholesale = False

    @rx.event
    def confirm_disable_wholesale_no(self):
        """El usuario canceló la desactivación de mayoreo."""
        self.confirm_disable_wholesale = False

    @rx.event
    def add_variant_row(self):
        self.variants = [
            *self.variants,
            {"sku": "", "size": "", "color": "", "stock": 0},
        ]

    @rx.event
    def remove_variant_row(self, index: int):
        if index < 0 or index >= len(self.variants):
            return
        self.variants = [row for idx, row in enumerate(self.variants) if idx != index]

    @rx.event
    def update_variant_field(self, index: int, field: str, value: Any):
        if index < 0 or index >= len(self.variants):
            return
        variants = list(self.variants)
        row = dict(variants[index])
        if field == "stock":
            try:
                row[field] = float(value) if value not in ("", None) else 0
            except (TypeError, ValueError):
                return
        else:
            row[field] = value
        variants[index] = row
        self.variants = variants

    @rx.event
    def handle_variant_sku_keydown(self, key: str, index: int):
        if key in ("Enter", "NumpadEnter", "Tab"):
            return rx.call_script(
                f"document.getElementById('variant_sku_{index}').blur()"
            )

    @rx.event
    def add_tier_row(self):
        self.price_tiers = [
            *self.price_tiers,
            {"min_qty": 0, "price": "0.00"},
        ]

    @rx.event
    def remove_tier_row(self, index: int):
        if index < 0 or index >= len(self.price_tiers):
            return
        self.price_tiers = [
            row for idx, row in enumerate(self.price_tiers) if idx != index
        ]

    @rx.event
    def update_tier_field(self, index: int, field: str, value: Any):
        if index < 0 or index >= len(self.price_tiers):
            return
        tiers = list(self.price_tiers)
        row = dict(tiers[index])
        if field == "min_qty":
            try:
                row[field] = int(float(value)) if value not in ("", None) else 0
            except (TypeError, ValueError):
                return
        elif field == "price":
            try:
                row[field] = fmt_price(float(value)) if value not in ("", None) else "0.00"
            except (TypeError, ValueError):
                return
        else:
            row[field] = value
        tiers[index] = row
        self.price_tiers = tiers

    # ─── Batches (lotes con vencimiento) — Farmacia / Supermercado ───
    @rx.event
    def set_show_batches(self, value: bool | str):
        if isinstance(value, str):
            value = value.lower() in ["true", "1", "on", "yes"]
        self.show_batches = bool(value)
        if self.show_batches and not self.batches:
            self.add_batch_row()

    @rx.event
    def add_batch_row(self):
        self.batches = [
            *self.batches,
            {
                "id": None,
                "batch_number": "",
                "expiration_date": "",
                "stock": 0.0,
            },
        ]

    @rx.event
    def remove_batch_row(self, index: int):
        if index < 0 or index >= len(self.batches):
            return
        self.batches = [
            row for idx, row in enumerate(self.batches) if idx != index
        ]

    @rx.event
    def update_batch_field(self, index: int, field: str, value: Any):
        if index < 0 or index >= len(self.batches):
            return
        batches = list(self.batches)
        row = dict(batches[index])
        if field == "stock":
            try:
                row[field] = float(value) if value not in ("", None) else 0.0
            except (TypeError, ValueError):
                return
        else:
            row[field] = value
        batches[index] = row
        self.batches = batches

    # ─── Attributes (EAV dinámicos) — Ferretería / Farmacia ───
    @rx.event
    def set_show_attributes(self, value: bool | str):
        if isinstance(value, str):
            value = value.lower() in ["true", "1", "on", "yes"]
        self.show_attributes = bool(value)
        if self.show_attributes and not self.attributes:
            self.add_attribute_row()

    @rx.event
    def add_attribute_row(self):
        self.attributes = [
            *self.attributes,
            {"id": None, "name": "", "value": ""},
        ]

    @rx.event
    def remove_attribute_row(self, index: int):
        if index < 0 or index >= len(self.attributes):
            return
        self.attributes = [
            row for idx, row in enumerate(self.attributes) if idx != index
        ]

    @rx.event
    def update_attribute_field(self, index: int, field: str, value: Any):
        if index < 0 or index >= len(self.attributes):
            return
        attrs = list(self.attributes)
        row = dict(attrs[index])
        row[field] = value
        attrs[index] = row
        self.attributes = attrs

    # ─── Kit Components (composición de kits/combos) ───
    @rx.event
    def set_show_kit_components(self, value: bool | str):
        if isinstance(value, str):
            value = value.lower() in ["true", "1", "on", "yes"]
        self.show_kit_components = bool(value)
        if self.show_kit_components and not self.kit_components:
            self.add_kit_component_row()

    @rx.event
    def add_kit_component_row(self):
        self.kit_components = [
            *self.kit_components,
            {
                "id": None,
                "component_barcode": "",
                "component_name": "",
                "component_product_id": None,
                "component_variant_id": None,
                "variant_label": "",
                "quantity": 1.0,
            },
        ]

    @rx.event
    def remove_kit_component_row(self, index: int):
        if index < 0 or index >= len(self.kit_components):
            return
        self.kit_components = [
            row for idx, row in enumerate(self.kit_components) if idx != index
        ]

    @rx.event
    def update_kit_component_field(self, index: int, field: str, value: Any):
        if index < 0 or index >= len(self.kit_components):
            return
        comps = list(self.kit_components)
        row = dict(comps[index])
        if field == "quantity":
            try:
                row[field] = float(value) if value not in ("", None) else 1.0
            except (TypeError, ValueError):
                return
        else:
            row[field] = value
        comps[index] = row
        self.kit_components = comps

    @rx.event
    def resolve_kit_component(self, index: int, barcode: str):
        """Busca producto/variante por código y lo asigna como componente del kit.

        Orden de búsqueda:
        1. Product.barcode → componente sin variante específica
        2. ProductVariant.sku → componente con variante específica
        """
        if index < 0 or index >= len(self.kit_components):
            return
        code = (barcode or "").strip()
        if not code:
            return
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            # 1. Buscar por barcode del producto padre
            p = session.exec(
                select(Product)
                .where(Product.barcode == code)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
            ).first()
            if p:
                comps = list(self.kit_components)
                row = dict(comps[index])
                row["component_barcode"] = p.barcode or ""
                row["component_name"] = p.description or ""
                row["component_product_id"] = p.id
                row["component_variant_id"] = None
                row["variant_label"] = ""
                comps[index] = row
                self.kit_components = comps
                return

            # 2. Buscar por SKU de variante
            variant = session.exec(
                select(ProductVariant)
                .where(ProductVariant.sku == code)
                .where(ProductVariant.company_id == company_id)
                .where(ProductVariant.branch_id == branch_id)
            ).first()
            if not variant:
                return rx.toast(f"Código '{code}' no encontrado como producto ni variante.", duration=3000)
            parent = session.exec(
                select(Product).where(Product.id == variant.product_id)
            ).first()
            variant_label = " ".join(filter(None, [variant.size, variant.color]))
            comps = list(self.kit_components)
            row = dict(comps[index])
            row["component_barcode"] = variant.sku or ""
            row["component_name"] = (parent.description or "") if parent else ""
            row["component_product_id"] = variant.product_id
            row["component_variant_id"] = variant.id
            row["variant_label"] = variant_label
            comps[index] = row
            self.kit_components = comps

    @rx.var(cache=True)
    def kit_component_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for index, comp in enumerate(self.kit_components):
            row = dict(comp)
            row["index"] = index
            rows.append(row)
        return rows

    @rx.var(cache=True)
    def batch_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for index, batch in enumerate(self.batches):
            row = dict(batch)
            row["index"] = index
            rows.append(row)
        return rows

    @rx.var(cache=True)
    def attribute_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for index, attr in enumerate(self.attributes):
            row = dict(attr)
            row["index"] = index
            rows.append(row)
        return rows

    @rx.var(cache=True)
    def batches_stock_total(self) -> float:
        total = 0.0
        for batch in self.batches:
            try:
                total += float(batch.get("stock", 0) or 0)
            except (TypeError, ValueError):
                continue
        return total

    @rx.event
    def save_edited_product(self):
        if not self.current_user["privileges"]["edit_inventario"]:
            return self.add_notification(
                "No tiene permisos para editar el inventario.", "error"
            )
        block = self._require_active_subscription()
        if block:
            return block

        product_data = self.editing_product
        product_id = product_data.get("id")
        barcode = product_data.get("barcode", "").strip()
        description = product_data.get("description", "").strip()
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return self.add_notification("Empresa no definida.", "error")

        if not description:
            return self.add_notification(
                "La descripción no puede estar vacía.", "error"
            )
        if not barcode:
            return self.add_notification(
                "El código de barras no puede estar vacío.", "error"
            )

        if self.show_wholesale and self.price_tiers:
            min_qtys = []
            for tier in self.price_tiers:
                mq = tier.get("min_qty", 0) or 0
                try:
                    mq = int(mq)
                except (TypeError, ValueError):
                    mq = 0
                if mq > 0:
                    if mq in min_qtys:
                        return self.add_notification(
                            f"Hay cantidades mínimas duplicadas ({mq}) en las escalas de mayoreo.",
                            "error",
                        )
                    min_qtys.append(mq)

        if self.show_variants:
            skus = [
                (variant.get("sku") or "").strip()
                for variant in self.variants
                if (variant.get("sku") or "").strip()
            ]
            if not skus:
                return self.add_notification(
                    "Agregue al menos una variante con SKU válido.", "error"
                )
            if len(skus) != len(set(skus)):
                return self.add_notification(
                    "Hay SKUs de variantes duplicados.", "error"
                )

        if self.show_batches:
            batch_numbers = [
                (b.get("batch_number") or "").strip()
                for b in self.batches
                if (b.get("batch_number") or "").strip()
            ]
            if not batch_numbers:
                return self.add_notification(
                    "Agregue al menos un lote con número válido.", "error"
                )
            if len(batch_numbers) != len(set(batch_numbers)):
                return self.add_notification(
                    "Hay números de lote duplicados.", "error"
                )
            for b in self.batches:
                exp = (b.get("expiration_date") or "").strip()
                if exp:
                    try:
                        datetime.datetime.strptime(exp, "%Y-%m-%d")
                    except ValueError:
                        return self.add_notification(
                            f"Fecha de vencimiento inválida: '{exp}' (use YYYY-MM-DD).",
                            "error",
                        )

        if self.show_attributes:
            names = [
                (a.get("name") or "").strip().lower()
                for a in self.attributes
                if (a.get("name") or "").strip()
            ]
            if not names:
                return self.add_notification(
                    "Agregue al menos un atributo con nombre válido.", "error"
                )
            if len(names) != len(set(names)):
                return self.add_notification(
                    "Hay nombres de atributo duplicados.", "error"
                )

        if self.show_kit_components:
            comp_ids = [
                c.get("component_product_id")
                for c in self.kit_components
                if c.get("component_product_id")
            ]
            if not comp_ids:
                return self.add_notification(
                    "Agregue al menos un componente válido al kit.", "error"
                )
            # Duplicado = mismo (product_id, variant_id); variantes distintas del mismo
            # producto son componentes válidos y distintos dentro del mismo kit.
            comp_keys = [
                (c.get("component_product_id"), c.get("component_variant_id"))
                for c in self.kit_components
                if c.get("component_product_id")
            ]
            if len(comp_keys) != len(set(comp_keys)):
                return self.add_notification(
                    "Hay componentes duplicados en el kit.", "error"
                )

        self.is_loading = True
        yield

        msg = ""
        try:
            with rx.session() as session:
                session.info["tenant_bypass"] = True
                # Verificar codigo de barras duplicado
                existing = session.exec(
                    select(Product)
                    .where(Product.barcode == barcode)
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                ).first()

                if existing and (product_id is None or existing.id != product_id):
                    return self.add_notification(
                        "Ya existe un producto con ese código de barras.",
                        "error",
                    )

                if self.show_variants:
                    variant_skus = [
                        (variant.get("sku") or "").strip()
                        for variant in self.variants
                        if (variant.get("sku") or "").strip()
                    ]
                    if variant_skus:
                        duplicate_query = (
                            select(ProductVariant)
                            .where(ProductVariant.company_id == company_id)
                            .where(ProductVariant.branch_id == branch_id)
                            .where(ProductVariant.sku.in_(variant_skus))
                        )
                        if product_id:
                            duplicate_query = duplicate_query.where(
                                ProductVariant.product_id != product_id
                            )
                        duplicate_variant = session.exec(duplicate_query).first()
                        if duplicate_variant:
                            return self.add_notification(
                                f"El SKU de variante '{duplicate_variant.sku}' ya existe en otro producto.",
                                "error",
                            )

                if product_id:
                    # Actualizar
                    # FIX 39b: with_for_update to prevent TOCTOU on stock/price
                    product = session.exec(
                        select(Product)
                        .where(Product.id == product_id)
                        .where(Product.company_id == company_id)
                        .where(Product.branch_id == branch_id)
                        .with_for_update()
                    ).first()
                    if not product:
                        return self.add_notification("Producto no encontrado.", "error")

                    product.barcode = barcode
                    product.description = description
                    product.category = (product_data.get("category", "GENERAL") or "GENERAL").strip().upper()
                    product.stock = (
                        self.variants_stock_total
                        if self.show_variants
                        else product_data.get("stock", 0)
                    )
                    product.unit = product_data.get("unit", "Unidad")
                    product.purchase_price = product_data.get("purchase_price", 0)
                    product.default_supplier_id = product_data.get("default_supplier_id") or None
                    new_sale_price_raw = product_data.get("sale_price", 0)
                    from decimal import Decimal, InvalidOperation
                    from app.utils.pricing import price_matches_margin as _pmm
                    editing_variant_id = product_data.get("variant_id")
                    _sp_val = float(new_sale_price_raw or 0)
                    _pp_val = float(product_data.get("purchase_price") or 0)
                    _raw_custom = str(product_data.get("custom_profit_margin") or "").strip()
                    _global_margin = getattr(self, "effective_profit_margin_decimal", 0.0)
                    # NULL cuando el precio guardado sigue el margen vigente (global o custom).
                    # El producto queda "dinámico": cambiar el margen recalcula el precio.
                    _use_margin = float(_raw_custom) if _raw_custom else _global_margin
                    _price_is_dynamic = _pmm(_sp_val, _pp_val, _use_margin) and not _raw_custom
                    explicit_price = None if _price_is_dynamic else (
                        Decimal(str(_sp_val)) if _sp_val > 0 else None
                    )
                    if editing_variant_id:
                        # Edición desde fila de variante: precio va solo a esa variante
                        ev = session.exec(
                            select(ProductVariant)
                            .where(ProductVariant.id == int(editing_variant_id))
                            .where(ProductVariant.company_id == company_id)
                            .where(ProductVariant.branch_id == branch_id)
                            .with_for_update()
                        ).first()
                        if ev:
                            ev.sale_price = explicit_price
                            session.add(ev)
                    else:
                        # Producto sin variante activa: actualizar precio del padre
                        old_price = product.sale_price
                        if Decimal(str(_sp_val or 0)) != Decimal(str(old_price or 0)):
                            from app.utils.timezone import utc_now_naive as _now
                            product.sale_price_updated_at = _now()
                        product.sale_price = explicit_price
                    # Persistir override de margen solo cuando se edita el producto
                    # completo (no una variante individual). Si viene de fila de
                    # variante el margen calculado es local a esa variante y no
                    # debe pisar el margen que heredan las demás variantes sin precio propio.
                    if not editing_variant_id:
                        raw_margin = str(product_data.get("custom_profit_margin") or "").strip()
                        try:
                            product.custom_profit_margin = (
                                Decimal(raw_margin).quantize(Decimal("0.01")) if raw_margin else None
                            )
                        except (InvalidOperation, ValueError):
                            product.custom_profit_margin = None

                    session.add(product)
                    msg = "Producto actualizado correctamente."
                else:
                    # Parsear margen custom para nuevo producto
                    from decimal import Decimal, InvalidOperation
                    raw_margin = str(product_data.get("custom_profit_margin") or "").strip()
                    try:
                        parsed_margin = (
                            Decimal(raw_margin).quantize(Decimal("0.01")) if raw_margin else None
                        )
                    except (InvalidOperation, ValueError):
                        parsed_margin = None
                    # Crear
                    new_product = Product(
                        barcode=barcode,
                        description=description,
                        category=(product_data.get("category", "GENERAL") or "GENERAL").strip().upper(),
                        stock=(
                            self.variants_stock_total
                            if self.show_variants
                            else product_data.get("stock", 0)
                        ),
                        unit=product_data.get("unit", "Unidad"),
                        purchase_price=product_data.get("purchase_price", 0),
                        sale_price=product_data.get("sale_price", 0),
                        custom_profit_margin=parsed_margin,
                        default_supplier_id=product_data.get("default_supplier_id") or None,
                        company_id=company_id,
                        branch_id=branch_id,
                    )
                    session.add(new_product)
                    session.flush()
                    product = new_product
                    msg = "Producto creado correctamente."

                if product_id:
                    session.flush()

                product_id = product.id if product else None

                if product_id:
                    if self.show_variants:
                        existing_variants = session.exec(
                            select(ProductVariant)
                            .where(ProductVariant.product_id == product_id)
                            .where(ProductVariant.company_id == company_id)
                            .where(ProductVariant.branch_id == branch_id)
                        ).all()
                        for variant in existing_variants:
                            session.delete(variant)
                        session.flush()

                        for variant in self.variants:
                            sku = (variant.get("sku") or "").strip()
                            if not sku:
                                continue
                            stock_value = variant.get("stock", 0) or 0
                            try:
                                stock_value = Decimal(str(stock_value))
                            except (TypeError, InvalidOperation):
                                stock_value = Decimal("0")
                            session.add(
                                ProductVariant(
                                    product_id=product_id,
                                    sku=sku,
                                    size=(variant.get("size") or "").strip() or None,
                                    color=(variant.get("color") or "").strip() or None,
                                    stock=stock_value,
                                    company_id=company_id,
                                    branch_id=branch_id,
                                )
                            )
                    else:
                        existing_variants = session.exec(
                            select(ProductVariant)
                            .where(ProductVariant.product_id == product_id)
                            .where(ProductVariant.company_id == company_id)
                            .where(ProductVariant.branch_id == branch_id)
                        ).all()
                        for variant in existing_variants:
                            session.delete(variant)

                    if self.show_wholesale:
                        existing_tiers = session.exec(
                            select(PriceTier)
                            .where(PriceTier.product_id == product_id)
                            .where(PriceTier.company_id == company_id)
                            .where(PriceTier.branch_id == branch_id)
                        ).all()
                        for tier in existing_tiers:
                            session.delete(tier)

                        for tier in self.price_tiers:
                            min_qty = tier.get("min_qty", 0) or 0
                            price_value = tier.get("price", 0) or 0
                            try:
                                min_qty = int(min_qty)
                            except (TypeError, ValueError):
                                min_qty = 0
                            try:
                                price_value = Decimal(str(price_value))
                            except (TypeError, InvalidOperation):
                                price_value = Decimal("0")
                            if min_qty <= 0:
                                continue
                            session.add(
                                PriceTier(
                                    product_id=product_id,
                                    min_quantity=min_qty,
                                    unit_price=price_value,
                                    company_id=company_id,
                                    branch_id=branch_id,
                                )
                            )
                    else:
                        existing_tiers = session.exec(
                            select(PriceTier)
                            .where(PriceTier.product_id == product_id)
                            .where(PriceTier.company_id == company_id)
                            .where(PriceTier.branch_id == branch_id)
                        ).all()
                        for tier in existing_tiers:
                            session.delete(tier)

                    # ─── Persistir lotes (batches) ───
                    if self.show_batches:
                        existing_batches = session.exec(
                            select(ProductBatch)
                            .where(ProductBatch.product_id == product_id)
                            .where(ProductBatch.product_variant_id.is_(None))
                            .where(ProductBatch.company_id == company_id)
                            .where(ProductBatch.branch_id == branch_id)
                        ).all()
                        for batch in existing_batches:
                            session.delete(batch)
                        session.flush()

                        for batch in self.batches:
                            batch_number = (batch.get("batch_number") or "").strip()
                            if not batch_number:
                                continue
                            stock_value = batch.get("stock", 0) or 0
                            try:
                                stock_value = Decimal(str(stock_value))
                            except (TypeError, InvalidOperation):
                                stock_value = Decimal("0")
                            expiration_raw = (batch.get("expiration_date") or "").strip()
                            expiration_dt = None
                            if expiration_raw:
                                try:
                                    expiration_dt = datetime.datetime.strptime(
                                        expiration_raw, "%Y-%m-%d"
                                    )
                                except ValueError:
                                    expiration_dt = None
                            session.add(
                                ProductBatch(
                                    product_id=product_id,
                                    batch_number=batch_number,
                                    expiration_date=expiration_dt,
                                    stock=stock_value,
                                    company_id=company_id,
                                    branch_id=branch_id,
                                )
                            )
                    else:
                        existing_batches = session.exec(
                            select(ProductBatch)
                            .where(ProductBatch.product_id == product_id)
                            .where(ProductBatch.product_variant_id.is_(None))
                            .where(ProductBatch.company_id == company_id)
                            .where(ProductBatch.branch_id == branch_id)
                        ).all()
                        for batch in existing_batches:
                            session.delete(batch)

                    # ─── Persistir atributos dinámicos (EAV) ───
                    if self.show_attributes:
                        existing_attrs = session.exec(
                            select(ProductAttribute)
                            .where(ProductAttribute.product_id == product_id)
                            .where(ProductAttribute.company_id == company_id)
                            .where(ProductAttribute.branch_id == branch_id)
                        ).all()
                        for attr in existing_attrs:
                            session.delete(attr)
                        session.flush()

                        for attr in self.attributes:
                            name = (attr.get("name") or "").strip()
                            value = (attr.get("value") or "").strip()
                            if not name:
                                continue
                            session.add(
                                ProductAttribute(
                                    product_id=product_id,
                                    attribute_name=name,
                                    attribute_value=value,
                                    company_id=company_id,
                                    branch_id=branch_id,
                                )
                            )
                    else:
                        existing_attrs = session.exec(
                            select(ProductAttribute)
                            .where(ProductAttribute.product_id == product_id)
                            .where(ProductAttribute.company_id == company_id)
                            .where(ProductAttribute.branch_id == branch_id)
                        ).all()
                        for attr in existing_attrs:
                            session.delete(attr)

                    # ─── Persistir componentes de kit ───
                    if self.show_kit_components:
                        existing_kit = session.exec(
                            select(ProductKit)
                            .where(ProductKit.kit_product_id == product_id)
                            .where(ProductKit.company_id == company_id)
                            .where(ProductKit.branch_id == branch_id)
                        ).all()
                        for k in existing_kit:
                            session.delete(k)
                        session.flush()

                        for comp in self.kit_components:
                            comp_pid = comp.get("component_product_id")
                            if not comp_pid:
                                continue
                            qty_value = comp.get("quantity", 1) or 1
                            try:
                                qty_value = Decimal(str(qty_value))
                            except (TypeError, InvalidOperation):
                                qty_value = Decimal("1")
                            comp_vid = comp.get("component_variant_id")
                            session.add(
                                ProductKit(
                                    kit_product_id=product_id,
                                    component_product_id=int(comp_pid),
                                    component_variant_id=int(comp_vid) if comp_vid else None,
                                    quantity=qty_value,
                                    company_id=company_id,
                                    branch_id=branch_id,
                                )
                            )
                    else:
                        existing_kit = session.exec(
                            select(ProductKit)
                            .where(ProductKit.kit_product_id == product_id)
                            .where(ProductKit.company_id == company_id)
                            .where(ProductKit.branch_id == branch_id)
                        ).all()
                        for k in existing_kit:
                            session.delete(k)

                session.commit()
        except Exception:
            logger.exception(
                "save_edited_product failed | company=%s branch=%s",
                self._company_id(),
                self._branch_id(),
            )
            return self.add_notification(
                "No se pudo guardar el producto.", "error"
            )
        finally:
            self.is_loading = False

        self._inventory_update_trigger += 1
        self._refresh_inventory_cache()
        self.is_editing_product = False
        self.show_variants = False
        self.show_wholesale = False
        self.show_batches = False
        self.show_attributes = False
        self.show_kit_components = False
        self.variants = []
        self.price_tiers = []
        self.batches = []
        self.attributes = []
        self.kit_components = []
        return self.add_notification(msg, "success")

    @rx.event
    def open_confirm_delete_product(self, product: dict):
        self.confirm_delete_product_id = product.get("id", 0)
        self.confirm_delete_product_name = product.get("description", "")

    @rx.event
    def cancel_delete_product(self):
        self.confirm_delete_product_id = 0
        self.confirm_delete_product_name = ""

    @rx.event
    def delete_product(self, product_id: int):
        if not self.current_user["privileges"]["edit_inventario"]:
            return self.add_notification(
                "No tiene permisos para eliminar productos.", "error"
            )
        block = self._require_active_subscription()
        if block:
            return block
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return self.add_notification("Empresa no definida.", "error")

        self.is_loading = True
        yield
        deleted = False

        try:
            with rx.session() as session:
                session.info["tenant_bypass"] = True
                product = session.exec(
                    select(Product)
                    .where(Product.id == product_id)
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                ).first()
                if product:
                    # Verificar si tiene historial de ventas
                    # FIX 38a: add company_id filter for tenant isolation
                    has_sales = session.exec(
                        select(SaleItem)
                        .where(SaleItem.product_id == product_id)
                        .where(SaleItem.company_id == company_id)
                        .where(SaleItem.branch_id == branch_id)
                    ).first()
                    if has_sales:
                        return self.add_notification(
                            "No se puede eliminar un producto con historial de ventas. Edítelo para desactivarlo.",
                            "warning",
                        )
                    session.delete(product)
                    session.commit()
                    self._inventory_update_trigger += 1
                    deleted = True
                else:
                    return self.add_notification("Producto no encontrado.", "error")
        finally:
            self.is_loading = False

        self.confirm_delete_product_id = 0
        self.confirm_delete_product_name = ""
        if deleted:
            self._refresh_inventory_cache()
            return self.add_notification("Producto eliminado.", "success")
