"""Mixin de Generador Masivo de Etiquetas para InventoryState."""
from __future__ import annotations

import logging
from typing import Any

import reflex as rx

from app.services.label_service import LabelConfig, LabelService

logger = logging.getLogger(__name__)


class LabelMixin:
    """Mixin que agrega la funcionalidad de generación de etiquetas al estado de inventario."""

    # ── Modal ─────────────────────────────────────────────────────────
    show_label_generator: bool = False

    # ── Configuración de etiquetas ────────────────────────────────────
    label_size: str = "medium"          # small | medium | large
    label_filter: str = "all"           # all | price_changed | no_barcode | specific
    label_price_changed_days: int = 7
    label_copies: int = 1
    label_show_purchase_price: bool = False

    # ── Formato de página ─────────────────────────────────────────────
    label_page_format: str = "a4"        # a4 | thermal_58 | thermal_80

    # ── Filtro por categoría ──────────────────────────────────────────
    label_category: str = ""
    label_available_categories: list[str] = []

    # ── Preview de productos a etiquetar ─────────────────────────────
    label_preview_products: list[dict[str, Any]] = []
    label_preview_count: int = 0
    label_preview_loaded: bool = False

    # ── Productos específicos ─────────────────────────────────────────
    label_specific_items: list[dict[str, Any]] = []   # [{id, description, barcode, sale_price, sale_price_str, category, qty}]
    label_search_query: str = ""
    label_search_results: list[dict[str, Any]] = []

    # ─── Abrir/Cerrar modal ──────────────────────────────────────────

    @rx.event
    def open_label_generator(self):
        self.show_label_generator = True
        self.label_size = "medium"
        self.label_filter = "all"
        self.label_price_changed_days = 7
        self.label_copies = 1
        self.label_show_purchase_price = False
        self.label_page_format = "a4"
        self.label_category = ""
        self.label_preview_products = []
        self.label_preview_count = 0
        self.label_preview_loaded = False
        self.label_specific_items = []
        self.label_search_query = ""
        self.label_search_results = []

    @rx.event
    def close_label_generator(self):
        self.show_label_generator = False

    # ─── Setters ─────────────────────────────────────────────────────

    @rx.event
    def set_label_size(self, v: str):
        self.label_size = v

    @rx.event
    def set_label_filter(self, v: str):
        self.label_filter = v
        self.label_preview_loaded = False
        self.label_preview_products = []
        if v != "specific":
            self.label_specific_items = []
            self.label_search_query = ""
            self.label_search_results = []

    @rx.event
    def set_label_price_changed_days(self, v: str):
        try:
            self.label_price_changed_days = int(v or 7)
        except ValueError:
            self.label_price_changed_days = 7

    @rx.event
    def set_label_copies(self, v: str):
        try:
            self.label_copies = max(1, min(10, int(v or 1)))
        except ValueError:
            self.label_copies = 1

    @rx.event
    def set_label_show_purchase_price(self, v: bool):
        self.label_show_purchase_price = v

    @rx.event
    def set_label_page_format(self, v: str):
        self.label_page_format = v

    @rx.event
    def set_label_category(self, v: str):
        self.label_category = v
        self.label_preview_loaded = False
        self.label_preview_products = []

    # ─── Cargar categorías disponibles ───────────────────────────────

    @rx.event
    async def load_label_categories(self):
        """Carga las categorías distintas de productos activos del tenant."""
        from sqlmodel import select as sql_select
        from app.models import Product
        from app.utils.db import get_async_session
        from app.utils.tenant import set_tenant_context

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return
        try:
            set_tenant_context(company_id, branch_id)
            async with get_async_session() as s:
                stmt = (
                    sql_select(Product.category)
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                    .where(Product.is_active == True)
                    .where(Product.category != None)
                    .distinct()
                    .order_by(Product.category)
                )
                rows = (await s.execute(stmt)).scalars().all()
                self.label_available_categories = [r for r in rows if r]
        except Exception as exc:
            logger.exception("Error cargando categorías de etiquetas: %s", exc)
        finally:
            set_tenant_context(None, None)

    # ─── Búsqueda y selección de productos específicos ────────────────

    @rx.event
    async def set_label_search_query(self, v: str):
        """Actualiza la búsqueda: incluye variantes (ProductVariant) y productos sin variantes."""
        self.label_search_query = v
        query = v.strip()
        if len(query) < 2:
            self.label_search_results = []
            return

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return

        try:
            from sqlmodel import select as sql_select, or_
            from app.models import Product, ProductVariant
            from app.utils.db import get_async_session
            from app.utils.tenant import set_tenant_context

            _GENERIC = {"0000000000000", "0", "", "N/A", "n/a"}
            selected_keys = {item["item_key"] for item in self.label_specific_items}

            set_tenant_context(company_id, branch_id)
            async with get_async_session() as s:
                # ── Variantes que coinciden ─────────────────────────────
                stmt_v = (
                    sql_select(ProductVariant, Product)
                    .join(Product, ProductVariant.product_id == Product.id)
                    .where(ProductVariant.company_id == company_id)
                    .where(ProductVariant.branch_id == branch_id)
                    .where(Product.is_active == True)
                    .where(
                        or_(
                            Product.description.ilike(f"%{query}%"),
                            ProductVariant.sku.ilike(f"%{query}%"),
                            ProductVariant.size.ilike(f"%{query}%"),
                            ProductVariant.color.ilike(f"%{query}%"),
                        )
                    )
                    .limit(10)
                )
                variant_rows = (await s.execute(stmt_v)).all()

                # ── Productos sin variantes que coinciden ───────────────
                has_variant_sq = (
                    sql_select(ProductVariant.id)
                    .where(ProductVariant.product_id == Product.id)
                    .where(ProductVariant.company_id == company_id)
                    .where(ProductVariant.branch_id == branch_id)
                    .exists()
                )
                stmt_p = (
                    sql_select(Product)
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                    .where(Product.is_active == True)
                    .where(~has_variant_sq)
                    .where(
                        or_(
                            Product.description.ilike(f"%{query}%"),
                            Product.barcode.ilike(f"%{query}%"),
                        )
                    )
                    .limit(10)
                )
                product_rows = (await s.execute(stmt_p)).scalars().all()

            results: list[dict] = []
            for variant, product in variant_rows:
                item_key = f"v_{variant.id}"
                if item_key in selected_keys:
                    continue
                parts = []
                if variant.size:
                    parts.append(str(variant.size).strip())
                if variant.color:
                    parts.append(str(variant.color).strip())
                label = " ".join(parts)
                sku = (variant.sku or "").strip()
                # Solo nombre + talla/color; el SKU/barcode va bajo el código de barras
                description = (product.description or "") + (f" ({label})" if label else "")
                bc = sku if sku and sku not in _GENERIC else LabelService.resolve_barcode(product)
                results.append({
                    "item_key": item_key,
                    "id": product.id,
                    "variant_id": variant.id,
                    "description": description,
                    "barcode": bc,
                    "sale_price": float(product.sale_price or 0),
                    "sale_price_str": f"{float(product.sale_price or 0):.2f}",
                    "purchase_price": float(product.purchase_price or 0),
                    "category": product.category or "",
                    "unit": product.unit or "Unidad",
                })

            for p in product_rows:
                item_key = f"p_{p.id}"
                if item_key in selected_keys:
                    continue
                results.append({
                    "item_key": item_key,
                    "id": p.id,
                    "variant_id": None,
                    "description": p.description or "",
                    "barcode": LabelService.resolve_barcode(p),
                    "sale_price": float(p.sale_price or 0),
                    "sale_price_str": f"{float(p.sale_price or 0):.2f}",
                    "purchase_price": float(p.purchase_price or 0),
                    "category": p.category or "",
                    "unit": p.unit or "Unidad",
                })

            self.label_search_results = results[:10]
        except Exception as exc:
            logger.exception("Error buscando productos para etiquetas: %s", exc)
        finally:
            set_tenant_context(None, None)

    @rx.event
    def add_label_specific_product(self, item_key: str):
        """Agrega un item (producto o variante) de los resultados al listado seleccionado."""
        match = next((p for p in self.label_search_results if p["item_key"] == item_key), None)
        if not match:
            return
        if any(item["item_key"] == item_key for item in self.label_specific_items):
            return
        self.label_specific_items = [*self.label_specific_items, {**match, "qty": 1}]
        self.label_search_results = [r for r in self.label_search_results if r["item_key"] != item_key]
        self._sync_specific_preview()

    @rx.event
    def remove_label_specific_product(self, item_key: str):
        self.label_specific_items = [
            item for item in self.label_specific_items if item["item_key"] != item_key
        ]
        self._sync_specific_preview()

    @rx.event
    def increment_label_specific_qty(self, item_key: str):
        self.label_specific_items = [
            {**item, "qty": min(99, item["qty"] + 1)} if item["item_key"] == item_key else item
            for item in self.label_specific_items
        ]
        self._sync_specific_preview()

    @rx.event
    def decrement_label_specific_qty(self, item_key: str):
        self.label_specific_items = [
            {**item, "qty": max(1, item["qty"] - 1)} if item["item_key"] == item_key else item
            for item in self.label_specific_items
        ]
        self._sync_specific_preview()

    def _sync_specific_preview(self):
        """Actualiza las vars de preview a partir de label_specific_items."""
        self.label_preview_products = [
            {k: v for k, v in item.items() if k != "qty"}
            for item in self.label_specific_items
        ]
        self.label_preview_count = len(self.label_specific_items)
        self.label_preview_loaded = len(self.label_specific_items) > 0

    # ─── Preview ─────────────────────────────────────────────────────

    @rx.event
    async def load_label_preview(self):
        """Carga los primeros 20 productos que serán etiquetados (preview)."""
        # Modo específico: usar directamente los seleccionados
        if self.label_filter == "specific":
            self._sync_specific_preview()
            return

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return

        self.is_loading = True
        self.label_preview_loaded = False
        try:
            config = LabelConfig(
                size=self.label_size,
                filter_type=self.label_filter,
                price_changed_days=self.label_price_changed_days,
                copies=1,
                show_purchase_price=self.label_show_purchase_price,
                currency_symbol=self.currency_symbol,
                category=self.label_category or None,
                page_format=self.label_page_format,
            )
            products = await LabelService.get_products_for_labels(
                config, company_id, branch_id
            )
            self.label_preview_count = len(products)
            self.label_preview_products = []
            self.label_preview_loaded = True
        except Exception as exc:
            logger.exception("Error en preview de etiquetas: %s", exc)
            yield rx.toast(f"Error al cargar productos: {exc}", duration=4000)
        finally:
            self.is_loading = False

    # ─── Generar y descargar PDF ──────────────────────────────────────

    @rx.event
    async def download_label_pdf(self):
        """Genera y descarga el PDF con todas las etiquetas."""
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return

        self.is_loading = True
        try:
            settings = self._company_settings_snapshot()
            config = LabelConfig(
                size=self.label_size,
                filter_type=self.label_filter,
                price_changed_days=self.label_price_changed_days,
                copies=1 if self.label_filter == "specific" else self.label_copies,
                show_purchase_price=self.label_show_purchase_price,
                company_name=settings.get("company_name", ""),
                currency_symbol=self.currency_symbol,
                category=self.label_category or None,
                page_format=self.label_page_format,
            )

            if self.label_filter == "specific":
                if not self.label_specific_items:
                    yield rx.toast("No hay productos seleccionados.", duration=3000)
                    return
                products = [
                    {k: v for k, v in item.items() if k not in ("qty", "sale_price_str", "item_key")}
                    for item in self.label_specific_items
                    for _ in range(max(1, item.get("qty", 1)))
                ]
            else:
                products = await LabelService.get_products_for_labels(
                    config, company_id, branch_id
                )
                if not products:
                    yield rx.toast("No hay productos para etiquetar con los filtros actuales.", duration=3000)
                    return

            pdf_bytes = LabelService.generate_pdf(products, config)
            filter_suffix = {
                "all": "todos",
                "price_changed": f"precio-{self.label_price_changed_days}d",
                "no_barcode": "sin-barcode",
                "specific": "especificos",
            }.get(self.label_filter, self.label_filter)

            cat_suffix = f"_{self.label_category}" if self.label_category else ""
            filename = f"etiquetas_{filter_suffix}{cat_suffix}_{self.label_size}_{self.label_page_format}.pdf"
            yield rx.download(data=pdf_bytes, filename=filename)
        except Exception as exc:
            logger.exception("Error generando PDF de etiquetas: %s", exc)
            yield rx.toast(f"Error al generar PDF: {exc}", duration=4000)
        finally:
            self.is_loading = False
