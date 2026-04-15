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
)

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
            self.is_editing_product = True
            return

        def _read_value(key: str, default: Any = "") -> Any:
            if isinstance(product, dict):
                return product.get(key, default)
            return getattr(product, key, default)

        product_id = _read_value("id", None)

        # Convertir modelo a dict para edicion
        self.editing_product = {
            "id": product_id,
            "barcode": _read_value("barcode", ""),
            "description": _read_value("description", ""),
            "category": _read_value("category", ""),
            "stock": _read_value("stock", 0),
            "unit": _read_value("unit", ""),
            "purchase_price": _read_value("purchase_price", 0),
            "sale_price": _read_value("sale_price", 0),
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
        if company_id and branch_id and product_id:
            with rx.session() as session:
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
                            "price": float(tier.unit_price or 0),
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
                    self.kit_components = [
                        {
                            "id": c.id,
                            "component_barcode": (comp_map[c.component_product_id].barcode or "") if c.component_product_id in comp_map else "",
                            "component_name": (comp_map[c.component_product_id].description or "") if c.component_product_id in comp_map else "",
                            "component_product_id": c.component_product_id,
                            "quantity": float(c.quantity or 1),
                        }
                        for c in kit_comps
                    ]
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
        if field in ["stock", "purchase_price", "sale_price"]:
            try:
                if value == "":
                    self.editing_product[field] = 0
                else:
                    self.editing_product[field] = float(value)
            except ValueError:
                pass
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
            {"min_qty": 0, "price": 0.0},
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
                row[field] = float(value) if value not in ("", None) else 0
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
            {"id": None, "component_barcode": "", "component_name": "", "component_product_id": None, "quantity": 1.0},
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
        """Busca un producto por código de barras y lo asigna como componente del kit."""
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
            p = session.exec(
                select(Product)
                .where(Product.barcode == code)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
            ).first()
            if not p:
                return rx.toast(f"Producto con código '{code}' no encontrado.", duration=3000)
            comps = list(self.kit_components)
            row = dict(comps[index])
            row["component_barcode"] = p.barcode or ""
            row["component_name"] = p.description or ""
            row["component_product_id"] = p.id
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
            if len(comp_ids) != len(set(comp_ids)):
                return self.add_notification(
                    "Hay componentes duplicados en el kit.", "error"
                )

        self.is_loading = True
        yield

        msg = ""
        try:
            with rx.session() as session:
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
                    product.category = product_data.get("category", "General")
                    product.stock = (
                        self.variants_stock_total
                        if self.show_variants
                        else product_data.get("stock", 0)
                    )
                    product.unit = product_data.get("unit", "Unidad")
                    product.purchase_price = product_data.get("purchase_price", 0)
                    product.sale_price = product_data.get("sale_price", 0)

                    session.add(product)
                    msg = "Producto actualizado correctamente."
                else:
                    # Crear
                    new_product = Product(
                        barcode=barcode,
                        description=description,
                        category=product_data.get("category", "General"),
                        stock=(
                            self.variants_stock_total
                            if self.show_variants
                            else product_data.get("stock", 0)
                        ),
                        unit=product_data.get("unit", "Unidad"),
                        purchase_price=product_data.get("purchase_price", 0),
                        sale_price=product_data.get("sale_price", 0),
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
                            session.add(
                                ProductKit(
                                    kit_product_id=product_id,
                                    component_product_id=int(comp_pid),
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

        if deleted:
            self._refresh_inventory_cache()
            return self.add_notification("Producto eliminado.", "success")
