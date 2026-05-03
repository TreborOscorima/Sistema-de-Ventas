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
    label_filter: str = "all"           # all | price_changed | no_barcode
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

    # ─── Preview ─────────────────────────────────────────────────────

    @rx.event
    async def load_label_preview(self):
        """Carga los primeros 20 productos que serán etiquetados (preview)."""
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
            self.label_preview_products = products[:20]
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
                copies=self.label_copies,
                show_purchase_price=self.label_show_purchase_price,
                company_name=settings.get("company_name", ""),
                currency_symbol=self.currency_symbol,
                category=self.label_category or None,
                page_format=self.label_page_format,
            )

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
            }.get(self.label_filter, self.label_filter)

            cat_suffix = f"_{self.label_category}" if self.label_category else ""
            filename = f"etiquetas_{filter_suffix}{cat_suffix}_{self.label_size}_{self.label_page_format}.pdf"
            yield rx.download(data=pdf_bytes, filename=filename)
        except Exception as exc:
            logger.exception("Error generando PDF de etiquetas: %s", exc)
            yield rx.toast(f"Error al generar PDF: {exc}", duration=4000)
        finally:
            self.is_loading = False
