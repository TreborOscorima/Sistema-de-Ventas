"""Mixin de busqueda, listado y categorias de inventario."""
import reflex as rx
from typing import List, Dict, Any

from sqlmodel import select
from sqlalchemy import or_, func, exists, literal, union_all, case, and_

from app.models import (
    Product,
    ProductVariant,
    ProductKit,
    Category,
)
from app.utils.tenant import set_tenant_context
from app.utils.sanitization import escape_like

DEFAULT_LOW_STOCK_THRESHOLD = 5


class SearchMixin:
    """Busqueda, listado paginado y gestion de categorias de inventario."""

    def _company_id(self) -> int | None:
        company_id, branch_id = self._tenant_ids()
        set_tenant_context(company_id, branch_id)
        return company_id

    def load_categories(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.categories = ["General"]
            self._categories_loaded_once = True
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
            self._categories_loaded_once = True

    def _inventory_search_clause(self, search: str, company_id: int, branch_id: int):
        term = f"%{escape_like(search)}%"
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

    def _inventory_row_from_product(self, product: Product, is_kit: bool = False) -> Dict[str, Any]:
        stock_value = float(product.stock or 0)
        purchase_value = float(product.purchase_price or 0)
        stock_total = self._round_currency(stock_value * purchase_value)
        min_alert = float(getattr(product, 'min_stock_alert', None) or DEFAULT_LOW_STOCK_THRESHOLD)
        return {
            "id": product.id,
            "variant_id": None,
            "is_variant": False,
            "is_kit": is_kit,
            "is_active": getattr(product, 'is_active', True),
            "barcode": product.barcode,
            "description": product.description,
            "category": product.category,
            "stock": product.stock,
            "stock_is_low": stock_value <= min_alert,
            "stock_is_medium": min_alert < stock_value <= min_alert * 2,
            "unit": product.unit,
            "purchase_price": product.purchase_price,
            "sale_price": product.sale_price,
            "stock_total_display": f"{stock_total:.2f}",
        }

    def _inventory_row_from_variant(
        self, product: Product, variant: ProductVariant, is_kit: bool = False
    ) -> Dict[str, Any]:
        label = self._variant_label(variant)
        description = product.description or ""
        if label:
            description = f"{description} ({label})"
        stock_value = float(variant.stock or 0)
        purchase_value = float(product.purchase_price or 0)
        stock_total = self._round_currency(stock_value * purchase_value)
        # Umbral por variante con fallback al Product padre.
        # variant.min_stock_alert == None significa "heredar del producto raiz".
        variant_alert = getattr(variant, 'min_stock_alert', None)
        if variant_alert is not None:
            min_alert = float(variant_alert)
        else:
            min_alert = float(
                getattr(product, 'min_stock_alert', None) or DEFAULT_LOW_STOCK_THRESHOLD
            )
        return {
            "id": product.id,
            "variant_id": variant.id,
            "is_variant": True,
            "is_kit": is_kit,
            "is_active": getattr(product, 'is_active', True),
            "barcode": variant.sku or product.barcode,
            "description": description,
            "category": product.category,
            "stock": variant.stock,
            "stock_is_low": stock_value <= min_alert,
            "stock_is_medium": min_alert < stock_value <= min_alert * 2,
            "unit": product.unit,
            "purchase_price": product.purchase_price,
            "sale_price": product.sale_price,
            "stock_total_display": f"{stock_total:.2f}",
        }

    def _inventory_search_count(
        self,
        session,
        search: str,
        company_id: int,
        branch_id: int,
    ) -> int:
        """Count total matching rows for search using SQL COUNT (no row loading)."""
        term = f"%{escape_like(search)}%"
        active_filter = [] if self.show_inactive_products else [Product.is_active == True]
        variant_count = int(
            session.exec(
                select(func.count(ProductVariant.id))
                .join(Product, ProductVariant.product_id == Product.id)
                .where(ProductVariant.company_id == company_id)
                .where(ProductVariant.branch_id == branch_id)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
                .where(*active_filter)
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
            ).one()
            or 0
        )
        no_variant = ~exists().where(ProductVariant.product_id == Product.id).where(
            ProductVariant.company_id == company_id
        ).where(ProductVariant.branch_id == branch_id)
        product_count = int(
            session.exec(
                select(func.count(Product.id))
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
                .where(no_variant)
                .where(*active_filter)
                .where(
                    or_(
                        Product.description.ilike(term),
                        Product.barcode.ilike(term),
                        Product.category.ilike(term),
                    )
                )
            ).one()
            or 0
        )
        return variant_count + product_count

    def _inventory_search_rows(
        self,
        session,
        search: str,
        company_id: int,
        branch_id: int,
        offset: int = 0,
        per_page: int = 20,
    ) -> List[Dict[str, Any]]:
        """Fetch one page of search results via SQL UNION ALL + OFFSET/LIMIT."""
        term = f"%{escape_like(search)}%"
        active_filter = [] if self.show_inactive_products else [Product.is_active == True]

        # Variant IDs matching search
        variant_ids_q = (
            select(
                Product.id.label("pid"),
                ProductVariant.id.label("vid"),
                Product.description.label("sort_desc"),
                func.coalesce(ProductVariant.sku, Product.barcode).label("sort_code"),
            )
            .join(Product, ProductVariant.product_id == Product.id)
            .where(ProductVariant.company_id == company_id)
            .where(ProductVariant.branch_id == branch_id)
            .where(Product.company_id == company_id)
            .where(Product.branch_id == branch_id)
            .where(*active_filter)
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
        )

        # Standalone product IDs matching search (no variants)
        no_variant = ~exists().where(ProductVariant.product_id == Product.id).where(
            ProductVariant.company_id == company_id
        ).where(ProductVariant.branch_id == branch_id)
        product_ids_q = (
            select(
                Product.id.label("pid"),
                literal(None).label("vid"),
                Product.description.label("sort_desc"),
                Product.barcode.label("sort_code"),
            )
            .where(Product.company_id == company_id)
            .where(Product.branch_id == branch_id)
            .where(no_variant)
            .where(*active_filter)
            .where(
                or_(
                    Product.description.ilike(term),
                    Product.barcode.ilike(term),
                    Product.category.ilike(term),
                )
            )
        )

        # SQL UNION ALL with ORDER BY + OFFSET + LIMIT
        unioned = union_all(variant_ids_q, product_ids_q).subquery()
        page_q = (
            select(unioned.c.pid, unioned.c.vid)
            .order_by(unioned.c.sort_desc, unioned.c.sort_code)
            .offset(offset)
            .limit(per_page)
        )
        page_id_rows = session.exec(page_q).all()

        if not page_id_rows:
            return []

        # Batch fetch ORM objects for this page only
        product_ids_needed = list({r[0] for r in page_id_rows})
        variant_ids_needed = [r[1] for r in page_id_rows if r[1] is not None]

        products_map = {
            p.id: p
            for p in session.exec(
                select(Product).where(Product.id.in_(product_ids_needed))
            ).all()
        }
        variants_map = {}
        if variant_ids_needed:
            variants_map = {
                v.id: v
                for v in session.exec(
                    select(ProductVariant).where(
                        ProductVariant.id.in_(variant_ids_needed)
                    )
                ).all()
            }
        kit_ids: set = set(
            session.exec(
                select(ProductKit.kit_product_id)
                .where(ProductKit.kit_product_id.in_(product_ids_needed))
                .where(ProductKit.company_id == company_id)
                .where(ProductKit.branch_id == branch_id)
            ).all()
        )

        # Build rows preserving SQL sort order
        rows: List[Dict[str, Any]] = []
        for pid, vid in page_id_rows:
            product = products_map.get(pid)
            if not product:
                continue
            if vid is not None:
                variant = variants_map.get(vid)
                if variant:
                    rows.append(self._inventory_row_from_variant(product, variant, is_kit=pid in kit_ids))
            else:
                rows.append(self._inventory_row_from_product(product, is_kit=pid in kit_ids))
        return rows

    def _refresh_inventory_cache(self):
        privileges = self.current_user["privileges"]
        if not privileges.get("view_inventario"):
            self.inventory_list = []
            self.inventory_total_pages = 1
            self.inventory_total_products = 0
            self.inventory_in_stock_count = 0
            self.inventory_low_stock_count = 0
            self.inventory_out_of_stock_count = 0
            return

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.inventory_list = []
            self.inventory_total_pages = 1
            self.inventory_total_products = 0
            self.inventory_in_stock_count = 0
            self.inventory_low_stock_count = 0
            self.inventory_out_of_stock_count = 0
            return

        search = (self.inventory_search_term or "").strip().lower()
        per_page = max(self.inventory_items_per_page, 1)
        page = max(self.inventory_current_page, 1)

        with rx.session() as session:
            if search:
                total_items = self._inventory_search_count(
                    session, search, company_id, branch_id
                )
                total_pages = (
                    1 if total_items == 0 else (total_items + per_page - 1) // per_page
                )
                if page > total_pages:
                    page = total_pages
                    self.inventory_current_page = page
                offset = (page - 1) * per_page
                page_rows = self._inventory_search_rows(
                    session, search, company_id, branch_id,
                    offset=offset, per_page=per_page,
                )
            else:
                active_filter = [] if self.show_inactive_products else [Product.is_active == True]
                total_items = int(
                    session.exec(
                        select(func.count(Product.id))
                        .where(Product.company_id == company_id)
                        .where(Product.branch_id == branch_id)
                        .where(*active_filter)
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
                    .where(*active_filter)
                    .order_by(Product.description, Product.id)
                    .offset(offset)
                    .limit(per_page)
                )
                products_page = session.exec(query).all()
                page_product_ids = [p.id for p in products_page]
                page_kit_ids: set = set(
                    session.exec(
                        select(ProductKit.kit_product_id)
                        .where(ProductKit.kit_product_id.in_(page_product_ids))
                        .where(ProductKit.company_id == company_id)
                        .where(ProductKit.branch_id == branch_id)
                    ).all()
                ) if page_product_ids else set()
                page_rows = [
                    self._inventory_row_from_product(product, is_kit=product.id in page_kit_ids)
                    for product in products_page
                ]

            # Single query con CASE para obtener los 4 contadores en 1 round-trip
            # Solo cuenta productos activos para las estadisticas.
            stock_stats = session.exec(
                select(
                    func.count(Product.id),
                    func.sum(case(
                        (Product.stock > Product.min_stock_alert, 1),
                        else_=0,
                    )),
                    func.sum(case(
                        (and_(Product.stock > 0, Product.stock <= Product.min_stock_alert), 1),
                        else_=0,
                    )),
                    func.sum(case(
                        (Product.stock <= 0, 1),
                        else_=0,
                    )),
                )
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
                .where(Product.is_active == True)
            ).one()
            total_products = int(stock_stats[0] or 0)
            in_stock_count = int(stock_stats[1] or 0)
            low_stock_count = int(stock_stats[2] or 0)
            out_of_stock_count = int(stock_stats[3] or 0)

        self.inventory_list = page_rows
        self.inventory_total_pages = total_pages
        self.inventory_total_products = total_products
        self.inventory_in_stock_count = in_stock_count
        self.inventory_low_stock_count = low_stock_count
        self.inventory_out_of_stock_count = out_of_stock_count

    @rx.event
    def refresh_inventory_cache(self):
        self.load_categories()
        self._refresh_inventory_cache()

    @rx.event
    def toggle_show_inactive_products(self, value: bool):
        """Muestra/oculta productos inactivos en el listado."""
        self.show_inactive_products = value
        self.inventory_current_page = 1
        self._refresh_inventory_cache()

    @rx.event
    def toggle_product_active(self, product_id: int):
        """Activa/desactiva un producto."""
        if not self.current_user["privileges"]["edit_inventario"]:
            return self.add_notification(
                "No tiene permisos para editar productos.", "error"
            )
        block = self._require_active_subscription()
        if block:
            return block
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return self.add_notification("Empresa no definida.", "error")
        with rx.session() as session:
            product = session.exec(
                select(Product)
                .where(Product.id == product_id)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
            ).first()
            if not product:
                return self.add_notification("Producto no encontrado.", "error")
            product.is_active = not product.is_active
            session.add(product)
            session.commit()
            status = "activado" if product.is_active else "desactivado"
            self._refresh_inventory_cache()
            return self.add_notification(
                f"Producto '{product.description}' {status}.", "success"
            )

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
                    events = [self._emit_runtime_sync_event()]
                    notification = self.add_notification(
                        f"Categoría '{name}' agregada.", "success"
                    )
                    if notification is not None:
                        events.append(notification)
                    return events
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
                    events = [self._emit_runtime_sync_event()]
                    notification = self.add_notification(
                        f"Categoría '{category}' eliminada.", "success"
                    )
                    if notification is not None:
                        events.append(notification)
                    return events
                return self.add_notification("Categoría no encontrada.", "warning")
        finally:
            self.is_loading = False

    @rx.var(cache=True)
    def inventory_display_page(self) -> int:
        if self.inventory_current_page < 1:
            return 1
        if self.inventory_current_page > self.inventory_total_pages:
            return self.inventory_total_pages
        return self.inventory_current_page

    @rx.event
    def set_inventory_search_term(self, value: str):
        self.inventory_search_term = value or ""
        self.inventory_current_page = 1
        self._refresh_inventory_cache()

    @rx.event
    def set_inventory_page(self, page_num: int):
        if 1 <= page_num <= self.inventory_total_pages:
            self.inventory_current_page = page_num
            self._refresh_inventory_cache()

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
