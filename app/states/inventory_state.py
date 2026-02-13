"""Estado de Inventario - Gestión de productos y stock.

Este módulo maneja toda la lógica relacionada con el inventario:

Funcionalidades principales:
- CRUD de productos (crear, leer, actualizar, eliminar)
- Gestión de categorías
- Ajustes de inventario con registro de movimientos
- Búsqueda y filtrado de productos
- Verificación de inventario físico
- Exportación de reportes

Permisos requeridos:
- view_inventario: Ver listado de productos
- edit_inventario: Crear, editar, eliminar productos y categorías

Clases:
    InventoryState: Estado principal del módulo de inventario
"""
import reflex as rx
from typing import List, Dict, Any, Optional
import datetime
import uuid
import logging
import io
from decimal import Decimal, InvalidOperation
from sqlmodel import select
from sqlalchemy import and_, or_, func, exists
from sqlalchemy.orm import selectinload
from app.models import (
    Product,
    ProductBatch,
    ProductVariant,
    PriceTier,
    StockMovement,
    User as UserModel,
    Category,
    SaleItem,
)
from .types import InventoryAdjustment
from .mixin_state import MixinState
from app.utils.tenant import set_tenant_context
from app.utils.barcode import clean_barcode, validate_barcode
from app.utils.exports import (
    create_excel_workbook,
    style_header_row,
    add_data_rows,
    auto_adjust_column_widths,
    add_company_header,
    add_totals_row_with_formulas,
    add_notes_section,
    CURRENCY_FORMAT,
    PERCENT_FORMAT,
    THIN_BORDER,
    POSITIVE_FILL,
    NEGATIVE_FILL,
    WARNING_FILL,
)


LOW_STOCK_THRESHOLD = 5


class InventoryState(MixinState):
    """Estado de gestión de inventario y productos.
    
    Maneja productos, categorías, ajustes de stock y reportes.
    Los productos se persisten en BD, no en memoria de estado.
    
    Attributes:
        new_category_name: Nombre para nueva categoría
        inventory_search_term: Término de búsqueda actual
        inventory_current_page: Página de paginación
        editing_product: Producto en edición (dict temporal)
        is_editing_product: True si hay modal de edición abierto
        inventory_check_modal_open: Modal de verificación de inventario
        inventory_adjustment_item: Item siendo ajustado
    """
    # inventory: Dict[str, Product] = {} # Eliminado a favor de la BD
    # categories: List[str] = ["General"] # Reemplazado por BD
    new_category_name: str = ""
    new_category_input_key: int = 0
    inventory_search_term: str = ""
    inventory_current_page: int = 1
    inventory_items_per_page: int = 10
    inventory_recent_limit: int = 100
    
    editing_product: Dict[str, Any] = { # Tipo cambiado a Dict para manejo de formularios
        "id": None,
        "barcode": "",
        "description": "",
        "category": "",
        "stock": 0,
        "unit": "",
        "purchase_price": 0,
        "sale_price": 0,
    }
    is_editing_product: bool = False
    show_variants: bool = False
    show_wholesale: bool = False
    variants: List[Dict[str, Any]] = []
    price_tiers: List[Dict[str, Any]] = []
    stock_details_open: bool = False
    stock_details_title: str = ""
    stock_details_mode: str = "simple"
    selected_product_details: List[Dict[str, Any]] = []
    
    inventory_check_modal_open: bool = False
    inventory_check_status: str = "perfecto"
    inventory_adjustment_notes: str = ""
    inventory_adjustment_item: InventoryAdjustment = {
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
    inventory_adjustment_items: List[InventoryAdjustment] = []
    inventory_adjustment_suggestions: List[Dict[str, Any]] = []
    categories: List[str] = ["General"]
    categories_panel_expanded: bool = False
    _inventory_update_trigger: int = 0
    inventory_list_cache: list[dict] = []
    inventory_total_pages_cache: int = 1
    inventory_total_products_cache: int = 0
    inventory_in_stock_count_cache: int = 0
    inventory_low_stock_count_cache: int = 0
    inventory_out_of_stock_count_cache: int = 0

    def _company_id(self) -> int | None:
        company_id, branch_id = self._tenant_ids()
        set_tenant_context(company_id, branch_id)
        return company_id

    def load_categories(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.categories = ["General"]
            return
        with rx.session() as session:
            cats = session.exec(
                select(Category)
                .where(Category.company_id == company_id)
                .where(Category.branch_id == branch_id)
                .order_by(Category.name)
            ).all()
            names = [c.name for c in cats]
            if "General" not in names:
                names.insert(0, "General")
            self.categories = names

    def _inventory_search_clause(self, search: str, company_id: int, branch_id: int):
        term = f"%{search}%"
        variant_match = (
            exists()
            .where(ProductVariant.product_id == Product.id)
            .where(ProductVariant.company_id == company_id)
            .where(ProductVariant.branch_id == branch_id)
            .where(
                or_(
                    ProductVariant.sku.ilike(term),
                    ProductVariant.size.ilike(term),
                    ProductVariant.color.ilike(term),
                )
            )
        )
        return or_(
            Product.description.ilike(term),
            Product.barcode.ilike(term),
            Product.category.ilike(term),
            variant_match,
        )

    def _inventory_row_from_product(self, product: Product) -> Dict[str, Any]:
        stock_value = float(product.stock or 0)
        purchase_value = float(product.purchase_price or 0)
        stock_total = self._round_currency(stock_value * purchase_value)
        return {
            "id": product.id,
            "variant_id": None,
            "is_variant": False,
            "barcode": product.barcode,
            "description": product.description,
            "category": product.category,
            "stock": product.stock,
            "stock_is_low": stock_value <= 5,
            "stock_is_medium": 5 < stock_value <= 10,
            "unit": product.unit,
            "purchase_price": product.purchase_price,
            "sale_price": product.sale_price,
            "stock_total_display": f"{stock_total:.2f}",
        }

    def _inventory_row_from_variant(
        self, product: Product, variant: ProductVariant
    ) -> Dict[str, Any]:
        label = self._variant_label(variant)
        description = product.description or ""
        if label:
            description = f"{description} ({label})"
        stock_value = float(variant.stock or 0)
        purchase_value = float(product.purchase_price or 0)
        stock_total = self._round_currency(stock_value * purchase_value)
        return {
            "id": product.id,
            "variant_id": variant.id,
            "is_variant": True,
            "barcode": variant.sku or product.barcode,
            "description": description,
            "category": product.category,
            "stock": variant.stock,
            "stock_is_low": stock_value <= 5,
            "stock_is_medium": 5 < stock_value <= 10,
            "unit": product.unit,
            "purchase_price": product.purchase_price,
            "sale_price": product.sale_price,
            "stock_total_display": f"{stock_total:.2f}",
        }

    def _inventory_search_rows(
        self,
        session,
        search: str,
        company_id: int,
        branch_id: int,
    ) -> List[Dict[str, Any]]:
        term = f"%{search}%"
        variant_query = (
            select(ProductVariant, Product)
            .join(Product, ProductVariant.product_id == Product.id)
            .where(ProductVariant.company_id == company_id)
            .where(ProductVariant.branch_id == branch_id)
            .where(Product.company_id == company_id)
            .where(Product.branch_id == branch_id)
            .where(
                or_(
                    ProductVariant.sku.ilike(term),
                    ProductVariant.size.ilike(term),
                    ProductVariant.color.ilike(term),
                    Product.description.ilike(term),
                    Product.barcode.ilike(term),
                    Product.category.ilike(term),
                )
            )
            .order_by(Product.description, ProductVariant.sku)
        )

        variant_rows = [
            self._inventory_row_from_variant(parent, variant)
            for variant, parent in session.exec(variant_query).all()
        ]

        no_variant = ~exists().where(ProductVariant.product_id == Product.id).where(
            ProductVariant.company_id == company_id
        ).where(ProductVariant.branch_id == branch_id)
        product_query = (
            select(Product)
            .where(Product.company_id == company_id)
            .where(Product.branch_id == branch_id)
            .where(no_variant)
            .where(
                or_(
                    Product.description.ilike(term),
                    Product.barcode.ilike(term),
                    Product.category.ilike(term),
                )
            )
            .order_by(Product.description, Product.id)
        )
        product_rows = [
            self._inventory_row_from_product(product)
            for product in session.exec(product_query).all()
        ]

        rows = [*variant_rows, *product_rows]
        rows.sort(
            key=lambda row: (
                str(row.get("description") or "").lower(),
                str(row.get("barcode") or "").lower(),
            )
        )
        return rows

    def _refresh_inventory_cache(self):
        privileges = self.current_user["privileges"]
        if not privileges.get("view_inventario"):
            self.inventory_list_cache = []
            self.inventory_total_pages_cache = 1
            self.inventory_total_products_cache = 0
            self.inventory_in_stock_count_cache = 0
            self.inventory_low_stock_count_cache = 0
            self.inventory_out_of_stock_count_cache = 0
            return

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.inventory_list_cache = []
            self.inventory_total_pages_cache = 1
            self.inventory_total_products_cache = 0
            self.inventory_in_stock_count_cache = 0
            self.inventory_low_stock_count_cache = 0
            self.inventory_out_of_stock_count_cache = 0
            return

        search = (self.inventory_search_term or "").strip().lower()
        per_page = max(self.inventory_items_per_page, 1)
        page = max(self.inventory_current_page, 1)

        with rx.session() as session:
            if search:
                rows = self._inventory_search_rows(
                    session, search, company_id, branch_id
                )
                total_items = len(rows)
                total_pages = (
                    1 if total_items == 0 else (total_items + per_page - 1) // per_page
                )
                if page > total_pages:
                    page = total_pages
                    self.inventory_current_page = page
                offset = (page - 1) * per_page
                page_rows = rows[offset : offset + per_page]
            else:
                total_items = int(
                    session.exec(
                        select(func.count(Product.id))
                        .where(Product.company_id == company_id)
                        .where(Product.branch_id == branch_id)
                    ).one()
                    or 0
                )
                total_pages = (
                    1 if total_items == 0 else (total_items + per_page - 1) // per_page
                )
                if page > total_pages:
                    page = total_pages
                    self.inventory_current_page = page
                offset = (page - 1) * per_page
                query = (
                    select(Product)
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                    .order_by(Product.description, Product.id)
                    .offset(offset)
                    .limit(per_page)
                )
                page_rows = [
                    self._inventory_row_from_product(product)
                    for product in session.exec(query).all()
                ]

            total_products = int(
                session.exec(
                    select(func.count(Product.id))
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                ).one()
                or 0
            )
            in_stock_count = int(
                session.exec(
                    select(func.count(Product.id))
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                    .where(Product.stock > LOW_STOCK_THRESHOLD)
                ).one()
                or 0
            )
            low_stock_count = int(
                session.exec(
                    select(func.count(Product.id))
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                    .where(
                        and_(
                            Product.stock > 0,
                            Product.stock <= LOW_STOCK_THRESHOLD,
                        )
                    )
                ).one()
                or 0
            )
            out_of_stock_count = int(
                session.exec(
                    select(func.count(Product.id))
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                    .where(Product.stock <= 0)
                ).one()
                or 0
            )

        self.inventory_list_cache = page_rows
        self.inventory_total_pages_cache = total_pages
        self.inventory_total_products_cache = total_products
        self.inventory_in_stock_count_cache = in_stock_count
        self.inventory_low_stock_count_cache = low_stock_count
        self.inventory_out_of_stock_count_cache = out_of_stock_count

    @rx.event
    def refresh_inventory_cache(self):
        self.load_categories()
        self._refresh_inventory_cache()

    @rx.event
    def update_new_category_name(self, value: str):
        self.new_category_name = value

    @rx.event
    def toggle_categories_panel(self):
        self.categories_panel_expanded = not self.categories_panel_expanded

    @rx.event
    def add_category(self):
        if not self.current_user["privileges"]["edit_inventario"]:
            return self.add_notification(
                "No tiene permisos para editar categorias.", "error"
            )
        block = self._require_active_subscription()
        if block:
            return block
        name = (self.new_category_name or "").strip()
        if not name:
            return
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return self.add_notification("Empresa no definida.", "error")

        self.is_loading = True
        
        try:
            with rx.session() as session:
                existing = session.exec(
                    select(Category)
                    .where(Category.name == name)
                    .where(Category.company_id == company_id)
                    .where(Category.branch_id == branch_id)
                ).first()
                if not existing:
                    session.add(
                        Category(name=name, company_id=company_id, branch_id=branch_id)
                    )
                    session.commit()
                    self.new_category_name = ""
                    self.new_category_input_key += 1
                    self.load_categories()
                    return self.add_notification(
                        f"Categoría '{name}' agregada.", "success"
                    )
                return self.add_notification("La categoría ya existe.", "warning")
        finally:
            self.is_loading = False

    @rx.event
    def remove_category(self, category: str):
        if not self.current_user["privileges"]["edit_inventario"]:
            return self.add_notification(
                "No tiene permisos para editar categorias.", "error"
            )
        block = self._require_active_subscription()
        if block:
            return block
        if category == "General":
            return self.add_notification(
                "No se puede eliminar la categoría General.", "error"
            )
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return self.add_notification("Empresa no definida.", "error")

        self.is_loading = True
            
        try:
            with rx.session() as session:
                cat = session.exec(
                    select(Category)
                    .where(Category.name == category)
                    .where(Category.company_id == company_id)
                    .where(Category.branch_id == branch_id)
                ).first()
                if cat:
                    session.delete(cat)
                    session.commit()
                    self.load_categories()
                    return self.add_notification(
                        f"Categoría '{category}' eliminada.", "success"
                    )
                return self.add_notification("Categoría no encontrada.", "warning")
        finally:
            self.is_loading = False

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

    @rx.var
    def inventory_list(self) -> list[dict]:
        return self.inventory_list_cache

    @rx.var
    def inventory_total_pages(self) -> int:
        return self.inventory_total_pages_cache

    @rx.var
    def inventory_display_page(self) -> int:
        if self.inventory_current_page < 1:
            return 1
        if self.inventory_current_page > self.inventory_total_pages:
            return self.inventory_total_pages
        return self.inventory_current_page

    @rx.var
    def inventory_paginated_list(self) -> list[dict]:
        # Alias para compatibilidad con UI existente, ya que inventory_list ahora está paginado
        return self.inventory_list

    @rx.var
    def inventory_total_products(self) -> int:
        return self.inventory_total_products_cache

    @rx.var
    def inventory_in_stock_count(self) -> int:
        return self.inventory_in_stock_count_cache

    @rx.var
    def inventory_low_stock_count(self) -> int:
        return self.inventory_low_stock_count_cache

    @rx.var
    def inventory_out_of_stock_count(self) -> int:
        return self.inventory_out_of_stock_count_cache

    @rx.event
    def set_inventory_search_term(self, value: str):
        self.inventory_search_term = value or ""
        self.inventory_current_page = 1
        self._refresh_inventory_cache()

    @rx.event
    def set_inventory_page(self, page_num: int):
        if 1 <= page_num <= self.inventory_total_pages_cache:
            self.inventory_current_page = page_num
            self._refresh_inventory_cache()

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
            self.variants = []
            self.price_tiers = []
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
        self.variants = []
        self.price_tiers = []

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
        self.variants = []
        self.price_tiers = []
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
        self.variants = []
        self.price_tiers = []

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

    @rx.var
    def variant_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for index, variant in enumerate(self.variants):
            row = dict(variant)
            row["index"] = index
            rows.append(row)
        return rows

    @rx.var
    def price_tier_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for index, tier in enumerate(self.price_tiers):
            row = dict(tier)
            row["index"] = index
            rows.append(row)
        return rows

    @rx.var
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
        self.show_wholesale = bool(value)
        if self.show_wholesale and not self.price_tiers:
            self.add_tier_row()

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
                    product = session.exec(
                        select(Product)
                        .where(Product.id == product_id)
                        .where(Product.company_id == company_id)
                        .where(Product.branch_id == branch_id)
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
                
                session.commit()
        except Exception:
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
        self.variants = []
        self.price_tiers = []
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
                    has_sales = session.exec(
                        select(SaleItem)
                        .where(SaleItem.product_id == product_id)
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

    def _variant_label(self, variant: ProductVariant) -> str:
        parts: List[str] = []
        if variant.size:
            parts.append(str(variant.size).strip())
        if variant.color:
            parts.append(str(variant.color).strip())
        label = " ".join([p for p in parts if p])
        sku = (variant.sku or "").strip()
        if label and sku:
            return f"{label} ({sku})"
        return label or sku or "Variante"

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
            search = f"%{search_term}%"
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
                    for item in self.inventory_adjustment_items:
                        description = (item.get("description") or "").strip()
                        barcode = (item.get("barcode") or "").strip()
                        if not description and not barcode:
                            continue
                        
                        product, variant = self._find_adjustment_product(
                            session,
                            barcode,
                            description,
                            item.get("variant_id"),
                            item.get("product_id"),
                            for_update=True,
                        )
                        if not product:
                            continue
                        if not variant and self._product_has_variants(
                            session, product.id, company_id, branch_id
                        ):
                            continue
                        
                        quantity = _to_decimal(item.get("adjust_quantity", 0) or 0)
                        if quantity <= 0:
                            continue

                        unit = product.unit or item.get("unit") or ""
                        batches = self._get_batches_for_adjustment(
                            session, product, variant, company_id, branch_id, lock=True
                        )
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
                            timestamp=datetime.datetime.now(),
                            company_id=company_id,
                            branch_id=branch_id,
                        )
                        session.add(movement)
                        recorded = True

                    if variants_recalc_batches:
                        for variant_id in variants_recalc_batches:
                            total_query = select(
                                func.coalesce(func.sum(ProductBatch.stock), 0)
                            ).where(ProductBatch.product_variant_id == variant_id)
                            total_query = total_query.where(
                                ProductBatch.company_id == company_id
                            ).where(ProductBatch.branch_id == branch_id)
                            total_row = session.exec(total_query).first()
                            if total_row is None:
                                total_stock = Decimal("0.0000")
                            elif isinstance(total_row, tuple):
                                total_stock = total_row[0]
                            else:
                                total_stock = total_row
                            variant_row = session.exec(
                                select(ProductVariant)
                                .where(ProductVariant.id == variant_id)
                                .where(ProductVariant.company_id == company_id)
                                .where(ProductVariant.branch_id == branch_id)
                            ).first()
                            if variant_row:
                                variant_row.stock = total_stock
                                session.add(variant_row)
                                products_to_recalculate.add(variant_row.product_id)

                    if products_to_recalculate:
                        for product_id in products_to_recalculate:
                            total_query = select(
                                func.coalesce(func.sum(ProductVariant.stock), 0)
                            ).where(ProductVariant.product_id == product_id)
                            total_query = total_query.where(
                                ProductVariant.company_id == company_id
                            ).where(ProductVariant.branch_id == branch_id)
                            total_row = session.exec(total_query).first()
                            if total_row is None:
                                total_stock = Decimal("0.0000")
                            elif isinstance(total_row, tuple):
                                total_stock = total_row[0]
                            else:
                                total_stock = total_row
                            product = session.exec(
                                select(Product)
                                .where(Product.id == product_id)
                                .where(Product.company_id == company_id)
                                .where(Product.branch_id == branch_id)
                            ).first()
                            if product:
                                product.stock = self._normalize_quantity_value(
                                    total_stock, product.unit or ""
                                )
                                session.add(product)

                    if products_recalc_batches:
                        for product_id in (
                            products_recalc_batches - products_to_recalculate
                        ):
                            total_query = select(
                                func.coalesce(func.sum(ProductBatch.stock), 0)
                            ).where(ProductBatch.product_id == product_id)
                            total_query = total_query.where(
                                ProductBatch.product_variant_id.is_(None)
                            ).where(ProductBatch.company_id == company_id).where(
                                ProductBatch.branch_id == branch_id
                            )
                            total_row = session.exec(total_query).first()
                            if total_row is None:
                                total_stock = Decimal("0.0000")
                            elif isinstance(total_row, tuple):
                                total_stock = total_row[0]
                            else:
                                total_stock = total_row
                            product = session.exec(
                                select(Product)
                                .where(Product.id == product_id)
                                .where(Product.company_id == company_id)
                                .where(Product.branch_id == branch_id)
                            ).first()
                            if product:
                                product.stock = self._normalize_quantity_value(
                                    total_stock, product.unit or ""
                                )
                                session.add(product)

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

    @rx.event
    def export_inventory_to_excel(self):
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)

        currency_label = self._currency_symbol_clean()
        currency_format = self._currency_excel_format()

        company_name = getattr(self, "company_name", "") or "EMPRESA"
        today = datetime.datetime.now().strftime("%d/%m/%Y")
        
        wb, ws = create_excel_workbook("Inventario Valorizado")
        
        # Encabezado profesional
        row = add_company_header(ws, company_name, "INVENTARIO VALORIZADO ACTUAL", f"Al {today}", columns=12)
        
        headers = [
            "Código/SKU",
            "Descripción del Producto",
            "Categoría",
            "Stock Actual",
            "Unidad",
            f"Costo Unitario ({currency_label})",
            f"Precio Venta ({currency_label})",
            f"Margen Unitario ({currency_label})",
            "Margen (%)",
            f"Valor al Costo ({currency_label})",
            f"Valor a Venta ({currency_label})",
            "Estado Stock",
        ]
        
        with rx.session() as session:
            products = session.exec(
                select(Product)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
                .order_by(Product.description)
                .options(selectinload(Product.variants))
            ).all()

        def _variant_label(variant: ProductVariant) -> str:
            parts: list[str] = []
            if variant.size:
                parts.append(str(variant.size).strip())
            if variant.color:
                parts.append(str(variant.color).strip())
            return " ".join([p for p in parts if p]).strip()

        export_rows: list[dict[str, Any]] = []
        for product in products:
            variants = list(product.variants or [])
            if variants:
                for variant in variants:
                    label = _variant_label(variant)
                    description = product.description or "Sin descripción"
                    if label:
                        description = f"{description} ({label})"
                    export_rows.append(
                        {
                            "sku": variant.sku or product.barcode or "S/C",
                            "description": description,
                            "category": product.category or "Sin categoría",
                            "unit": product.unit or "Unid.",
                            "stock": variant.stock or 0,
                            "purchase_price": float(product.purchase_price or 0),
                            "sale_price": float(product.sale_price or 0),
                        }
                    )
            else:
                export_rows.append(
                    {
                        "sku": product.barcode or "S/C",
                        "description": product.description or "Sin descripción",
                        "category": product.category or "Sin categoría",
                        "unit": product.unit or "Unid.",
                        "stock": product.stock or 0,
                        "purchase_price": float(product.purchase_price or 0),
                        "sale_price": float(product.sale_price or 0),
                    }
                )

        total_items = len(export_rows)
        total_units = sum(float(item.get("stock", 0) or 0) for item in export_rows)
        total_cost_value = sum(
            float(item.get("stock", 0) or 0) * float(item.get("purchase_price", 0) or 0)
            for item in export_rows
        )
        total_sale_value = sum(
            float(item.get("stock", 0) or 0) * float(item.get("sale_price", 0) or 0)
            for item in export_rows
        )
        stock_zero = sum(1 for item in export_rows if float(item.get("stock", 0) or 0) == 0)
        stock_critical = sum(
            1 for item in export_rows if 0 < float(item.get("stock", 0) or 0) <= 5
        )
        stock_low = sum(
            1 for item in export_rows if 5 < float(item.get("stock", 0) or 0) <= 10
        )

        row += 1
        ws.cell(row=row, column=1, value="RESUMEN EJECUTIVO")
        row += 1
        ws.cell(row=row, column=1, value="Total SKUs:")
        ws.cell(row=row, column=2, value=total_items)
        row += 1
        ws.cell(row=row, column=1, value="Total unidades en stock:")
        ws.cell(row=row, column=2, value=total_units)
        row += 1
        ws.cell(row=row, column=1, value=f"Valor total al costo ({currency_label}):")
        ws.cell(row=row, column=2, value=total_cost_value).number_format = currency_format
        row += 1
        ws.cell(row=row, column=1, value=f"Valor total a venta ({currency_label}):")
        ws.cell(row=row, column=2, value=total_sale_value).number_format = currency_format
        row += 1
        ws.cell(row=row, column=1, value="Productos sin stock:")
        ws.cell(row=row, column=2, value=stock_zero)
        row += 1
        ws.cell(row=row, column=1, value="Productos críticos (1-5):")
        ws.cell(row=row, column=2, value=stock_critical)
        row += 1
        ws.cell(row=row, column=1, value="Productos bajos (6-10):")
        ws.cell(row=row, column=2, value=stock_low)
        row += 2

        style_header_row(ws, row, headers)
        data_start = row + 1
        row += 1

        for row_data in export_rows:
            barcode = row_data["sku"]
            description = row_data["description"]
            category = row_data["category"]
            unit = row_data["unit"]
            stock = row_data["stock"] or 0
            purchase_price = row_data["purchase_price"]
            sale_price = row_data["sale_price"]

            # Estado del stock
            if stock == 0:
                status = "SIN STOCK"
            elif stock <= 5:
                status = "CRÍTICO"
            elif stock <= 10:
                status = "BAJO"
            else:
                status = "NORMAL"

            ws.cell(row=row, column=1, value=barcode)
            ws.cell(row=row, column=2, value=description)
            ws.cell(row=row, column=3, value=category)
            ws.cell(row=row, column=4, value=stock)
            ws.cell(row=row, column=5, value=unit)
            ws.cell(row=row, column=6, value=purchase_price).number_format = currency_format
            ws.cell(row=row, column=7, value=sale_price).number_format = currency_format
            # Margen Unitario = Fórmula: Precio - Costo
            ws.cell(row=row, column=8, value=f"=G{row}-F{row}").number_format = currency_format
            # Margen % = Fórmula: (Margen / Costo) si Costo > 0
            ws.cell(row=row, column=9, value=f"=IF(F{row}>0,H{row}/F{row},0)").number_format = PERCENT_FORMAT
            # Valor al Costo = Fórmula: Stock × Costo
            ws.cell(row=row, column=10, value=f"=D{row}*F{row}").number_format = currency_format
            # Valor a Venta = Fórmula: Stock × Precio
            ws.cell(row=row, column=11, value=f"=D{row}*G{row}").number_format = currency_format
            ws.cell(row=row, column=12, value=status)

            # Color según estado
            status_cell = ws.cell(row=row, column=12)
            if "SIN STOCK" in status:
                status_cell.fill = NEGATIVE_FILL
            elif "CRÍTICO" in status:
                status_cell.fill = NEGATIVE_FILL
            elif "BAJO" in status:
                status_cell.fill = WARNING_FILL
            else:
                status_cell.fill = POSITIVE_FILL

            for col in range(1, 13):
                ws.cell(row=row, column=col).border = THIN_BORDER
            row += 1
        
        # Fila de totales
        totals_row = row
        add_totals_row_with_formulas(ws, totals_row, data_start, [
            {"type": "label", "value": "TOTALES"},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "sum", "col_letter": "D"},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "text", "value": ""},
            {"type": "sum", "col_letter": "J", "number_format": currency_format},
            {"type": "sum", "col_letter": "K", "number_format": currency_format},
            {"type": "text", "value": ""},
        ])
        
        # Notas explicativas
        add_notes_section(ws, totals_row, [
            "Costo Unitario: Precio al que se compró el producto al proveedor.",
            "Precio Venta: Precio de venta al público.",
            "Margen Unitario = Precio Venta - Costo Unitario (ganancia por unidad).",
            "Margen % = Margen Unitario ÷ Costo Unitario × 100.",
            "Valor al Costo: Inversión total = Stock × Costo Unitario.",
            "Valor a Venta: Potencial de ventas = Stock × Precio Venta.",
            "SIN STOCK: Producto agotado. CRÍTICO: ≤5 unidades. BAJO: ≤10 unidades.",
        ], columns=12)
        
        auto_adjust_column_widths(ws)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return rx.download(data=output.getvalue(), filename="inventario_valorizado.xlsx")
