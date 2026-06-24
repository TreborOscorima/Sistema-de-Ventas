import reflex as rx
from typing import List, Dict, Any, Optional
import datetime
import uuid
import logging
from decimal import Decimal
from sqlmodel import select
from sqlalchemy import func, or_
from app.models import (
    Product,
    ProductBatch,
    ProductVariant,
    StockMovement,
    User as UserModel,
    Supplier,
    Purchase,
    PurchaseItem,
)
from app.i18n import MSG
from .types import TransactionItem
from .mixin_state import MixinState
from app.utils.barcode import clean_barcode, validate_barcode
from app.utils.formatting import fmt_input_num, fmt_price
from app.utils.sanitization import escape_like, sanitize_text
from app.utils.stock import recalculate_stock_totals
from app.utils.pricing import resolve_effective_price, price_matches_margin

logger = logging.getLogger(__name__)

class IngresoState(MixinState):
    """Estado para el ingreso de productos al inventario.

    Maneja el formulario de ingreso de mercadería con soporte para
    variantes, lotes, autocompletado por código de barras y
    vinculación a órdenes de compra.
    """

    purchase_doc_type: str = "boleta"
    purchase_series: str = ""
    purchase_number: str = ""
    purchase_issue_date: str = ""
    purchase_notes: str = ""
    purchase_supplier_query: str = ""
    purchase_supplier_suggestions: List[Dict[str, Any]] = []
    purchase_supplier_active_index: int = -1
    purchase_supplier_input_key: int = 0
    selected_supplier: Optional[Dict[str, Any]] = None
    purchase_currency_code: str = ""
    purchase_exchange_rate: float = 0.0
    is_existing_product: bool = False
    has_variants: bool = False
    requires_batches: bool = False
    variants_list: List[Dict[str, Any]] = []
    selected_variant_id: str = ""
    variant_size: str = ""
    variant_color: str = ""
    entry_mode: str = "standard"
    batch_code: str = ""
    batch_date: str = ""

    entry_form_key: int = 0
    entry_sale_price_key: int = 0
    new_entry_item: TransactionItem = {
        "temp_id": "",
        "barcode": "",
        "description": "",
        "display_description": "",
        "category": MSG.FALLBACK_GENERAL,
        "quantity": 0,
        "unit": MSG.FALLBACK_UNIT,
        "price": 0,
        "sale_price": 0,
        "subtotal": 0,
        "product_id": None,
        "variant_id": None,
        "variant_size": "",
        "variant_color": "",
        "batch_code": "",
        "batch_date": "",
        "is_existing_product": False,
        "has_variants": False,
        "requires_batches": False,
        "original_cost": 0,
        "original_currency": "",
        "purchase_rate": 0,
    }
    new_entry_items: List[TransactionItem] = []
    entry_autocomplete_suggestions: List[str] = []
    entry_autocomplete_active_index: int = -1
    # True cuando el usuario escribió el precio de venta manualmente;
    # False = el precio se calcula automáticamente desde el margen.
    _entry_sale_price_manual: bool = rx.field(default=False, is_var=False)

    @rx.var(cache=False)
    def entry_price_display(self) -> str:
        """P. COMPRA formateado con 2 decimales; vacío si es 0."""
        try:
            val = float(self.new_entry_item.get("price", 0) or 0)
        except (TypeError, ValueError):
            val = 0.0
        return f"{val:.2f}" if val > 0 else ""

    @rx.var(cache=False)
    def entry_sale_price_display(self) -> str:
        """P. VENTA formateado con 2 decimales; vacío si es 0 (para mostrar placeholder)."""
        try:
            val = float(self.new_entry_item.get("sale_price", 0) or 0)
        except (TypeError, ValueError):
            val = 0.0
        return f"{val:.2f}" if val > 0 else ""

    @rx.var(cache=False)
    def entry_effective_margin(self) -> str:
        """Margen efectivo real basado en P. COMPRA y P. VENTA actuales."""
        pc = float(self.new_entry_item.get("price") or 0)
        pv = float(self.new_entry_item.get("sale_price") or 0)
        if pc > 0 and pv > 0:
            m = round((pv - pc) / pc * 100, 1)
            return str(int(m)) if m == int(m) else f"{m:g}"
        return ""

    @rx.var(cache=True)
    def entry_subtotal(self) -> float:
        return float(self.new_entry_item.get("subtotal") or 0)

    @rx.var(cache=True)
    def entry_subtotal_display(self) -> str:
        return f"{float(self.new_entry_item.get('subtotal') or 0):.2f}"

    @rx.var(cache=True)
    def purchase_is_foreign_currency(self) -> bool:
        """True cuando la moneda del documento difiere de la moneda de la empresa."""
        code = self.purchase_currency_code
        if not code:
            return False
        return code != getattr(self, "selected_currency_code", "PEN")

    @rx.var(cache=True)
    def purchase_exchange_rate_float(self) -> float:
        return max(0.0, self.purchase_exchange_rate)

    @rx.var(cache=False)
    def purchase_exchange_rate_display(self) -> str:
        """Para el campo input: vacío cuando es 0, sin decimales innecesarios."""
        v = self.purchase_exchange_rate
        if v <= 0:
            return ""
        return str(int(v)) if v == int(v) else f"{v:g}"

    @rx.var(cache=False)
    def entry_local_price_display(self) -> str:
        """Precio convertido a moneda local (read-only) cuando hay moneda extranjera."""
        price = float(self.new_entry_item.get("price") or 0)
        return f"{price:.2f}" if price > 0 else "0.00"

    @rx.var(cache=True)
    def effective_purchase_currency_code(self) -> str:
        """Moneda efectiva del documento: la elegida o la de la empresa."""
        return self.purchase_currency_code or getattr(self, "selected_currency_code", "PEN")

    @rx.var(cache=True)
    def entry_total(self) -> float:
        return self._round_currency(
            sum(float(item.get("subtotal") or 0) for item in self.new_entry_items)
        )

    @rx.var(cache=False)
    def entry_total_display(self) -> str:
        return fmt_price(self.entry_total)

    @rx.var(cache=True)
    def purchase_supplier_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for index, supplier in enumerate(self.purchase_supplier_suggestions):
            row = dict(supplier)
            row["index"] = index
            rows.append(row)
        return rows

    @rx.var(cache=True)
    def entry_autocomplete_rows(self) -> List[Dict[str, Any]]:
        return [
            {"value": suggestion, "index": index}
            for index, suggestion in enumerate(self.entry_autocomplete_suggestions)
        ]

    @rx.event
    def set_purchase_currency_code_handler(self, val: str):
        self.purchase_currency_code = val
        company_currency = getattr(self, "selected_currency_code", "PEN")
        if val == company_currency:
            self.purchase_exchange_rate = 0.0
            self.new_entry_item["original_cost"] = 0
            self.new_entry_item["original_currency"] = ""
            self.new_entry_item["purchase_rate"] = 0

    @rx.event
    def handle_exchange_rate_change(self, val: float):
        try:
            self.purchase_exchange_rate = max(0.0, float(val or 0))
        except (ValueError, TypeError):
            self.purchase_exchange_rate = 0.0

    @rx.event
    def handle_foreign_price_change(self, val: str):
        """Precio en moneda del proveedor → convierte a moneda local y actualiza el ítem."""
        try:
            foreign = float(val) if val else 0.0
        except ValueError:
            foreign = 0.0
        rate = self.purchase_exchange_rate_float
        local = self._round_currency(foreign * rate) if (foreign > 0 and rate > 0) else 0.0
        self.new_entry_item["price"] = local
        self.new_entry_item["original_cost"] = foreign
        self.new_entry_item["original_currency"] = self.purchase_currency_code
        self.new_entry_item["purchase_rate"] = rate
        self.new_entry_item["subtotal"] = self._round_currency(
            float(self.new_entry_item["quantity"]) * local
        )
        if not self._entry_sale_price_manual:
            margin = getattr(self, "effective_profit_margin_decimal", 0.0)
            if margin > 0 and local > 0:
                self.new_entry_item["sale_price"] = self._round_currency(
                    local * (1 + margin / 100)
                )
                self.entry_sale_price_key += 1

    @rx.event
    def handle_entry_change(self, field: str, value: str):
        try:
            if self.is_existing_product and field in {
                "description",
                "category",
            }:
                return
            if field in ["quantity", "price", "sale_price"]:
                numeric = float(value) if value else 0
                if field == "quantity":
                    self.new_entry_item[field] = self._normalize_quantity_value(
                        numeric, self.new_entry_item.get("unit", "")
                    )
                elif field == "sale_price":
                    self._entry_sale_price_manual = True
                    self.new_entry_item[field] = self._round_currency(numeric)
                else:
                    self.new_entry_item[field] = self._round_currency(numeric)
                    # Auto-calcular precio de venta si no fue editado manualmente
                    if field == "price" and not self._entry_sale_price_manual:
                        margin = getattr(self, "effective_profit_margin_decimal", 0.0)
                        if margin > 0:
                            self.new_entry_item["sale_price"] = self._round_currency(
                                numeric * (1 + margin / 100)
                            )
                            self.entry_sale_price_key += 1
            else:
                self.new_entry_item[field] = value
                if field == "unit":
                    self.new_entry_item["quantity"] = self._normalize_quantity_value(
                        self.new_entry_item["quantity"], value
                    )
            self.new_entry_item["subtotal"] = self._round_currency(
                float(self.new_entry_item["quantity"]) * float(self.new_entry_item["price"])
            )
            if field == "description":
                if value:
                    search = str(value).lower()
                    company_id = self._company_id()
                    branch_id = self._branch_id()
                    if not company_id or not branch_id:
                        self.entry_autocomplete_suggestions = []
                        self.entry_autocomplete_active_index = -1
                        return
                    with rx.session() as session:
                        session.info["tenant_bypass"] = True
                        products = session.exec(
                            select(Product)
                            .where(Product.description.contains(search))
                            .where(Product.company_id == company_id)
                            .where(Product.branch_id == branch_id)
                            .limit(5)
                        ).all()
                        self.entry_autocomplete_suggestions = [p.description for p in products]
                        self.entry_autocomplete_active_index = (
                            0 if self.entry_autocomplete_suggestions else -1
                        )
                else:
                    self.entry_autocomplete_suggestions = []
                    self.entry_autocomplete_active_index = -1
            elif field == "barcode":
                return self._process_entry_barcode(value)
        except ValueError as e:
            logging.exception(f"Error parsing entry value: {e}")

    @rx.event
    def set_purchase_doc_type(self, value: str):
        doc_type = (value or "").strip().lower()
        if doc_type not in {"boleta", "factura"}:
            return
        self.purchase_doc_type = doc_type

    @rx.event
    def set_purchase_series(self, value: str):
        self.purchase_series = value or ""

    @rx.event
    def set_purchase_number(self, value: str):
        self.purchase_number = value or ""

    @rx.event
    def set_purchase_issue_date(self, value: str):
        self.purchase_issue_date = value or ""

    @rx.event
    def set_purchase_notes(self, value: str):
        self.purchase_notes = value or ""

    @rx.event
    def search_supplier_change(self, query: str):
        self.purchase_supplier_query = query or ""
        term = (query or "").strip()
        if len(term) < 2:
            self.purchase_supplier_suggestions = []
            self.purchase_supplier_active_index = -1
            return
        search = f"%{escape_like(term)}%"
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.purchase_supplier_suggestions = []
            self.purchase_supplier_active_index = -1
            return
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            suppliers = session.exec(
                select(Supplier)
                .where(
                    or_(
                        Supplier.name.ilike(search),
                        Supplier.tax_id.ilike(search),
                    )
                )
                .where(Supplier.company_id == company_id)
                .where(Supplier.branch_id == branch_id)
                .order_by(Supplier.name)
                .limit(6)
            ).all()
        self.purchase_supplier_suggestions = [
            {
                "id": supplier.id,
                "name": supplier.name,
                "tax_id": supplier.tax_id,
            }
            for supplier in suppliers
        ]
        self.purchase_supplier_active_index = (
            0 if self.purchase_supplier_suggestions else -1
        )

    @rx.event
    def handle_supplier_search_keydown(self, key: str):
        if not self.purchase_supplier_suggestions:
            return
        total = len(self.purchase_supplier_suggestions)
        if key == "ArrowDown":
            if self.purchase_supplier_active_index < 0:
                self.purchase_supplier_active_index = 0
            else:
                self.purchase_supplier_active_index = min(
                    self.purchase_supplier_active_index + 1,
                    total - 1,
                )
            return
        if key == "ArrowUp":
            if self.purchase_supplier_active_index < 0:
                self.purchase_supplier_active_index = 0
            else:
                self.purchase_supplier_active_index = max(
                    self.purchase_supplier_active_index - 1,
                    0,
                )
            return
        if key in ("Enter", "NumpadEnter"):
            idx = self.purchase_supplier_active_index
            if idx < 0:
                idx = 0
            if 0 <= idx < total:
                return self.select_supplier(self.purchase_supplier_suggestions[idx])
            return
        if key == "Escape":
            self.purchase_supplier_suggestions = []
            self.purchase_supplier_active_index = -1

    @rx.event
    def set_purchase_supplier_active_index(self, index: int):
        self.purchase_supplier_active_index = index

    @rx.event
    def select_supplier(self, supplier_data: dict | Supplier):
        selected = None
        if isinstance(supplier_data, Supplier):
            selected = {
                "id": supplier_data.id,
                "name": supplier_data.name,
                "tax_id": supplier_data.tax_id,
            }
        elif isinstance(supplier_data, dict) and supplier_data:
            selected = dict(supplier_data)
        self.selected_supplier = selected
        self.purchase_supplier_query = ""
        self.purchase_supplier_suggestions = []
        self.purchase_supplier_active_index = -1
        self.purchase_supplier_input_key += 1

    @rx.event
    def clear_selected_supplier(self):
        self.selected_supplier = None

    @rx.event
    def clear_supplier_search(self):
        self.selected_supplier = None
        self.purchase_supplier_query = ""
        self.purchase_supplier_suggestions = []
        self.purchase_supplier_active_index = -1
        self.purchase_supplier_input_key += 1

    def _reset_purchase_form(self):
        self.purchase_doc_type = "boleta"
        self.purchase_series = ""
        self.purchase_number = ""
        self.purchase_issue_date = ""
        self.purchase_notes = ""
        self.purchase_supplier_query = ""
        self.purchase_supplier_suggestions = []
        self.purchase_supplier_active_index = -1
        self.purchase_supplier_input_key += 1
        self.selected_supplier = None
        self.purchase_currency_code = ""
        self.purchase_exchange_rate = 0.0

    def _set_new_product_mode(self):
        self.is_existing_product = False
        self.has_variants = False
        self.requires_batches = False
        self.variants_list = []
        self.selected_variant_id = ""
        self.variant_size = ""
        self.variant_color = ""
        self.entry_mode = "standard"
        self.batch_code = ""
        self.batch_date = ""
        self.new_entry_item["product_id"] = None
        self.new_entry_item["variant_id"] = None
        self.new_entry_item["variant_size"] = ""
        self.new_entry_item["variant_color"] = ""
        self.new_entry_item["batch_code"] = ""
        self.new_entry_item["batch_date"] = ""
        self.new_entry_item["is_existing_product"] = False
        self.new_entry_item["has_variants"] = False
        self.new_entry_item["requires_batches"] = False

    def _category_requires_batches(self, category: str) -> bool:
        value = (category or "").strip().lower()
        if not value:
            return False
        keywords = ("farmacia", "farmaceut", "medic", "botica", "drog")
        return any(keyword in value for keyword in keywords)

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

    def _load_variants_for_product(self, product_id: int | None):
        self.variants_list = []
        self.has_variants = False
        if not product_id:
            self.selected_variant_id = ""
            return
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.selected_variant_id = ""
            return
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            variants = session.exec(
                select(ProductVariant)
                .where(ProductVariant.product_id == product_id)
                .where(ProductVariant.company_id == company_id)
                .where(ProductVariant.branch_id == branch_id)
                .order_by(ProductVariant.size, ProductVariant.color, ProductVariant.sku)
            ).all()
        if not variants:
            self.selected_variant_id = ""
            return
        self.variants_list = [
            {
                "id": str(variant.id),
                "label": self._variant_label(variant),
            }
            for variant in variants
        ]
        self.has_variants = True
        valid_ids = {variant["id"] for variant in self.variants_list}
        if self.selected_variant_id not in valid_ids:
            self.selected_variant_id = ""

    def _apply_existing_product_context(self, product: Dict[str, Any]):
        self.is_existing_product = True
        self._fill_entry_item_from_product(product)
        product_id = product.get("product_id") or product.get("id")
        self.selected_variant_id = str(product.get("variant_id") or "")
        self._load_variants_for_product(int(product_id) if product_id else None)
        self.requires_batches = self._category_requires_batches(product.get("category", ""))
        self.batch_code = ""
        self.batch_date = ""
        if self.has_variants:
            self.entry_mode = "variant"
        elif self.requires_batches:
            self.entry_mode = "batch"
        else:
            self.entry_mode = "standard"
        self.variant_size = ""
        self.variant_color = ""
        _loaded_sp = float(self.new_entry_item.get("sale_price") or 0)
        if product.get("has_explicit_price"):
            # Precio personalizado en DB: protegerlo de auto-recalculación al tabear
            self._entry_sale_price_manual = True
        else:
            self._entry_sale_price_manual = False
            # Sin precio explícito: auto-calcular desde margen si hace falta
            if not _loaded_sp > 0:
                purchase_price = float(self.new_entry_item.get("price") or 0)
                margin = getattr(self, "effective_profit_margin_decimal", 0.0)
                if purchase_price > 0 and margin > 0:
                    self.new_entry_item["sale_price"] = self._round_currency(
                        purchase_price * (1 + margin / 100)
                    )
        self.entry_sale_price_key += 1
        # Force remount of uncontrolled fields (qty, price) to reflect product data
        self.entry_form_key += 1

    def _process_entry_barcode(self, barcode_value: str | None):
        self.new_entry_item["barcode"] = str(barcode_value) if barcode_value else ""
        if not barcode_value or not str(barcode_value).strip():
            self.new_entry_item["barcode"] = ""
            self.new_entry_item["description"] = ""
            self.new_entry_item["quantity"] = 0
            self.new_entry_item["price"] = 0
            self.new_entry_item["sale_price"] = 0
            self.new_entry_item["subtotal"] = 0
            self.entry_autocomplete_suggestions = []
            self.entry_autocomplete_active_index = -1
            self._set_new_product_mode()
            return

        code = clean_barcode(str(barcode_value))
        if validate_barcode(code):
            product = self._find_product_by_barcode(code)
            if product:
                self._apply_existing_product_context(product)
                self.entry_autocomplete_suggestions = []
                self.entry_autocomplete_active_index = -1
                return rx.toast(
                    f"Producto '{product['description']}' cargado",
                    duration=2000,
                )
        self._set_new_product_mode()

    @rx.event
    def handle_entry_barcode_form_submit(self, form_data: dict):
        """Procesa el barcode desde el formulario (Enter o scanner)."""
        barcode = str(form_data.get("barcode", "") or "").strip()
        if barcode:
            return self._process_entry_barcode(barcode)

    @rx.event
    def process_entry_barcode_from_input(self, barcode_value):
        """Procesa el barcode del input cuando pierde el foco"""
        return self._process_entry_barcode(barcode_value)

    @rx.event
    def set_entry_barcode_value(self, barcode_value: str):
        """Persiste el barcode del input en el estado al perder foco (sin lookup)."""
        barcode = (barcode_value or "").strip()
        if barcode:
            self.new_entry_item["barcode"] = barcode

    @rx.event
    def handle_barcode_enter(self, key: str, input_id: str):
        """Detecta la tecla Enter y fuerza el blur del input para procesar"""
        if key == "Enter":
            return rx.call_script(f"document.getElementById('{input_id}').blur()")

    @rx.event
    def set_selected_variant(self, value: str):
        self.selected_variant_id = str(value) if value else ""

    @rx.event
    def set_entry_mode(self, value: str):
        mode = (value or "").strip().lower()
        if mode not in {"standard", "variant", "batch"}:
            mode = "standard"
        self.entry_mode = mode
        if mode == "variant":
            self.has_variants = True
            self.requires_batches = False
        elif mode == "batch":
            self.has_variants = False
            self.requires_batches = True
        else:
            self.has_variants = False
            self.requires_batches = False
        if not self.has_variants:
            self.selected_variant_id = ""
            self.variant_size = ""
            self.variant_color = ""
        if not self.requires_batches:
            self.batch_code = ""
            self.batch_date = ""

    @rx.event
    def set_variant_size(self, value: str):
        self.variant_size = value or ""

    @rx.event
    def set_variant_color(self, value: str):
        self.variant_color = value or ""

    @rx.event
    def set_batch_code(self, value: str):
        self.batch_code = value or ""

    @rx.event
    def set_batch_date(self, value: str):
        self.batch_date = value or ""

    @rx.event
    def add_item_to_entry(self):
        if not self.current_user["privileges"]["create_ingresos"]:
            return rx.toast("No tiene permisos para crear ingresos.", duration=3000)
        if not (self.new_entry_item.get("category") or "").strip():
            fallback_category = (
                self.categories[0]
                if hasattr(self, "categories") and self.categories
                else MSG.FALLBACK_GENERAL
            )
            self.new_entry_item["category"] = fallback_category
        if (
            not self.new_entry_item["description"]
            or not self.new_entry_item["category"]
            or float(self.new_entry_item.get("quantity") or 0) <= 0
            or float(self.new_entry_item.get("price") or 0) <= 0
            or float(self.new_entry_item.get("sale_price") or 0) <= 0
        ):
            return rx.toast(
                "Por favor, complete todos los campos correctamente.", duration=3000
            )
        if self.has_variants and self.is_existing_product and not self.selected_variant_id:
            return rx.toast("Seleccione la talla o variante.", duration=3000)
        if self.requires_batches and not (self.batch_code or "").strip():
            return rx.toast("Ingrese el número de lote.", duration=3000)
        item_copy = self.new_entry_item.copy()
        item_copy["temp_id"] = str(uuid.uuid4())
        item_copy["variant_id"] = self.selected_variant_id or None
        item_copy["variant_size"] = (self.variant_size or "").strip()
        item_copy["variant_color"] = (self.variant_color or "").strip()
        item_copy["batch_code"] = (self.batch_code or "").strip()
        item_copy["batch_date"] = (self.batch_date or "").strip()
        item_copy["is_existing_product"] = self.is_existing_product
        item_copy["has_variants"] = self.has_variants
        item_copy["requires_batches"] = self.requires_batches
        display_description = ""
        variant_label = ""
        if item_copy.get("variant_id"):
            variant_id_str = str(item_copy.get("variant_id"))
            for variant in self.variants_list:
                if str(variant.get("id")) == variant_id_str:
                    variant_label = variant.get("label", "") or ""
                    break
        elif self.has_variants and not self.is_existing_product:
            size_value = (item_copy.get("variant_size") or "").strip()
            color_value = (item_copy.get("variant_color") or "").strip()
            parts = [part for part in (size_value, color_value) if part]
            if parts:
                variant_label = " ".join(parts)
        if variant_label:
            display_description = f"{item_copy['description']} ({variant_label})"
        if not display_description:
            display_description = item_copy["description"]
        item_copy["display_description"] = display_description
        self._apply_item_rounding(item_copy)
        item_copy["subtotal"] = fmt_price(float(item_copy.get("subtotal") or 0))
        item_copy["price"] = fmt_price(float(item_copy.get("price") or 0))
        item_copy["sale_price"] = fmt_price(float(item_copy.get("sale_price") or 0))
        self.new_entry_items.append(item_copy)
        self._reset_entry_form()
        return rx.call_script(
            "setTimeout(() => { const el = document.getElementById('barcode-input-entry'); if (el) { el.focus(); el.select(); } }, 50);"
        )

    @rx.event
    def clear_entry_item_form(self):
        """Limpia el formulario de AÑADIR PRODUCTOS sin afectar la lista."""
        self._reset_entry_form()
        return rx.call_script(
            "setTimeout(() => { const el = document.getElementById('barcode-input-entry'); if (el) { el.focus(); el.select(); } }, 50);"
        )

    @rx.event
    def handle_entry_field_keydown(self, key: str):
        """Si se presiona Enter en cantidad/precio, blur + click Añadir."""
        if key == "Enter":
            return rx.call_script(
                "document.activeElement.blur(); setTimeout(() => { const btn = document.getElementById('entry-add-btn'); if (btn) btn.click(); }, 100);"
            )

    @rx.event
    def handle_entry_description_keydown(self, key: str):
        if not self.entry_autocomplete_suggestions:
            return
        total = len(self.entry_autocomplete_suggestions)
        if key == "ArrowDown":
            if self.entry_autocomplete_active_index < 0:
                self.entry_autocomplete_active_index = 0
            else:
                self.entry_autocomplete_active_index = min(
                    self.entry_autocomplete_active_index + 1,
                    total - 1,
                )
            return
        if key == "ArrowUp":
            if self.entry_autocomplete_active_index < 0:
                self.entry_autocomplete_active_index = 0
            else:
                self.entry_autocomplete_active_index = max(
                    self.entry_autocomplete_active_index - 1,
                    0,
                )
            return
        if key in ("Enter", "NumpadEnter"):
            idx = self.entry_autocomplete_active_index
            if idx < 0:
                idx = 0
            if 0 <= idx < total:
                return self.select_product_for_entry(
                    self.entry_autocomplete_suggestions[idx]
                )
            return
        if key == "Escape":
            self.entry_autocomplete_suggestions = []
            self.entry_autocomplete_active_index = -1

    @rx.event
    def set_entry_autocomplete_active_index(self, index: int):
        self.entry_autocomplete_active_index = index

    @rx.event
    def remove_item_from_entry(self, temp_id: str):
        self.new_entry_items = [
            item for item in self.new_entry_items if item["temp_id"] != temp_id
        ]

    @rx.event
    def update_entry_item_category(self, temp_id: str, category: str):
        for item in self.new_entry_items:
            if item["temp_id"] == temp_id:
                item["category"] = category
                break

    @rx.event
    def edit_item_from_entry(self, temp_id: str):
        for item in self.new_entry_items:
            if item["temp_id"] == temp_id:
                self.new_entry_item = item.copy()
                self.new_entry_item.setdefault("variant_id", None)
                self.new_entry_item.setdefault("variant_size", "")
                self.new_entry_item.setdefault("variant_color", "")
                self.new_entry_item.setdefault("display_description", self.new_entry_item.get("description", ""))
                self.new_entry_item.setdefault("batch_code", "")
                self.new_entry_item.setdefault("batch_date", "")
                self.new_entry_item.setdefault("is_existing_product", False)
                self.new_entry_item.setdefault("has_variants", False)
                self.new_entry_item.setdefault("requires_batches", False)
                self.is_existing_product = bool(
                    item.get("is_existing_product") or item.get("product_id")
                )
                self.selected_variant_id = str(item.get("variant_id") or "")
                self.batch_code = item.get("batch_code", "") or ""
                self.batch_date = item.get("batch_date", "") or ""
                self.variant_size = item.get("variant_size", "") or ""
                self.variant_color = item.get("variant_color", "") or ""
                self.requires_batches = bool(
                    item.get("requires_batches")
                    or self._category_requires_batches(item.get("category", ""))
                )
                product_id = item.get("product_id")
                if product_id:
                    self._load_variants_for_product(int(product_id))
                else:
                    self.has_variants = False
                    self.variants_list = []
                    if not self.selected_variant_id:
                        self.selected_variant_id = ""
                if self.has_variants:
                    self.entry_mode = "variant"
                elif self.requires_batches:
                    self.entry_mode = "batch"
                else:
                    self.entry_mode = "standard"
                self.new_entry_items = [
                    entry for entry in self.new_entry_items if entry["temp_id"] != temp_id
                ]
                self._entry_sale_price_manual = False
                self.entry_form_key += 1
                self.entry_sale_price_key += 1
                self.entry_autocomplete_suggestions = []
                self.entry_autocomplete_active_index = -1
                return

    @rx.event
    def confirm_entry(self):
        if not self.current_user["privileges"]["create_ingresos"]:
            return rx.toast("No tiene permisos para crear ingresos.", duration=3000)
        block = self._require_active_subscription()
        if block:
            return block
        if not self.new_entry_items:
            return rx.toast("No hay productos para ingresar.", duration=3000)

        doc_type = (self.purchase_doc_type or "").strip().lower()
        series = sanitize_text(self.purchase_series, max_length=20)
        number = sanitize_text(self.purchase_number, max_length=30)
        notes = sanitize_text(self.purchase_notes, max_length=500)
        supplier_id = None
        if isinstance(self.selected_supplier, dict):
            supplier_id = self.selected_supplier.get("id")

        if doc_type not in {"boleta", "factura"}:
            return rx.toast("Seleccione tipo de documento valido.", duration=3000)
        if not number:
            return rx.toast("Ingrese numero de documento.", duration=3000)
        if not supplier_id:
            return rx.toast("Seleccione un proveedor.", duration=3000)

        issue_date_raw = (self.purchase_issue_date or "").strip()
        if not issue_date_raw:
            issue_date_raw = self._display_now().strftime("%Y-%m-%d")
        try:
            issue_date = datetime.datetime.strptime(issue_date_raw, "%Y-%m-%d")
        except ValueError:
            return rx.toast("Fecha de documento invalida.", duration=3000)

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)

        with rx.session() as session:
            session.info["tenant_bypass"] = True
            try:
                existing_doc = session.exec(
                    select(Purchase).where(
                        Purchase.company_id == company_id,
                        Purchase.branch_id == branch_id,
                        Purchase.supplier_id == supplier_id,
                        Purchase.doc_type == doc_type,
                        Purchase.series == series,
                        Purchase.number == number,
                    )
                ).first()
                if existing_doc:
                    return rx.toast(
                        MSG.INGRESO_DUPLICATE_DOC,
                        duration=3000,
                    )

                # Obtener ID de usuario actual
                user_id = self.current_user.get("id")

                descriptions_missing_barcode = [
                    (item.get("description") or "").strip()
                    for item in self.new_entry_items
                    if not (item.get("barcode") or "").strip()
                ]
                if descriptions_missing_barcode:
                    unique_descriptions = list(
                        dict.fromkeys(
                            desc for desc in descriptions_missing_barcode if desc
                        )
                    )
                    if unique_descriptions:
                        duplicates = session.exec(
                            select(
                                Product.description,
                                func.count(Product.id),
                            )
                            .where(Product.description.in_(unique_descriptions))
                            .where(Product.company_id == company_id)
                            .where(Product.branch_id == branch_id)
                            .group_by(Product.description)
                            .having(func.count(Product.id) > 1)
                        ).all()
                        if duplicates:
                            duplicate_name = duplicates[0][0]
                            return rx.toast(
                                f"Descripcion duplicada en inventario: {duplicate_name}. "
                                "Use codigo de barras.",
                                duration=4000,
                            )

                currency_code = self.effective_purchase_currency_code or getattr(self, "selected_currency_code", "PEN")
                purchase = Purchase(
                    doc_type=doc_type,
                    series=series,
                    number=number,
                    issue_date=issue_date,
                    total_amount=Decimal(str(self.entry_total or 0)),
                    currency_code=str(currency_code or "PEN"),
                    notes=notes,
                    company_id=company_id,
                    branch_id=branch_id,
                    supplier_id=supplier_id,
                    user_id=user_id,
                )
                session.add(purchase)
                session.flush()

                products_recalc_variants: set[int] = set()
                products_recalc_batches: set[int] = set()
                variants_recalc_batches: set[int] = set()

                # --- FIX 34: Batch pre-load products/variants (5N → 2 queries) ---
                _variant_ids: set[int] = set()
                _product_ids: set[int] = set()
                _barcodes: set[str] = set()
                _descriptions: set[str] = set()

                for _item in self.new_entry_items:
                    _vid = _item.get("variant_id") or ""
                    if _vid:
                        try:
                            _variant_ids.add(int(_vid))
                        except (TypeError, ValueError):
                            pass
                    _pid = _item.get("product_id")
                    if _pid:
                        try:
                            _product_ids.add(int(_pid))
                        except (TypeError, ValueError):
                            pass
                    _bc = (_item.get("barcode") or "").strip()
                    if _bc:
                        _barcodes.add(_bc)
                    _desc = (_item.get("description") or "").strip()
                    if _desc:
                        _descriptions.add(_desc)

                _variants_map: dict[int, ProductVariant] = {}
                if _variant_ids:
                    _vlist = session.exec(
                        select(ProductVariant)
                        .where(ProductVariant.id.in_(_variant_ids))
                        .where(ProductVariant.company_id == company_id)
                        .where(ProductVariant.branch_id == branch_id)
                        .with_for_update()
                    ).all()
                    _variants_map = {v.id: v for v in _vlist}
                    for _v in _vlist:
                        if _v.product_id:
                            _product_ids.add(_v.product_id)

                _products_by_id: dict[int, Product] = {}
                _products_by_barcode: dict[str, Product] = {}
                _products_by_desc: dict[str, Product] = {}

                _prod_conditions = []
                if _product_ids:
                    _prod_conditions.append(Product.id.in_(_product_ids))
                if _barcodes:
                    _prod_conditions.append(Product.barcode.in_(_barcodes))
                if _descriptions:
                    _prod_conditions.append(Product.description.in_(_descriptions))

                if _prod_conditions:
                    _prods = session.exec(
                        select(Product)
                        .where(Product.company_id == company_id)
                        .where(Product.branch_id == branch_id)
                        .where(or_(*_prod_conditions))
                        .with_for_update()
                    ).all()
                    for _p in _prods:
                        _products_by_id[_p.id] = _p
                        if _p.barcode:
                            _products_by_barcode[_p.barcode] = _p
                        if _p.description:
                            _products_by_desc[_p.description] = _p
                # --- END FIX 34 pre-load ---

                for item in self.new_entry_items:
                    barcode = (item.get("barcode") or "").strip()
                    description = (item.get("description") or "").strip()
                    variant_id_raw = item.get("variant_id") or ""
                    batch_number = sanitize_text(
                        item.get("batch_code") or "", max_length=60
                    )
                    batch_date_raw = (item.get("batch_date") or "").strip()
                    expiration_date = None
                    if batch_date_raw:
                        try:
                            expiration_date = datetime.datetime.strptime(
                                batch_date_raw, "%Y-%m-%d"
                            )
                        except ValueError:
                            return rx.toast(
                                "Fecha de vencimiento invalida.", duration=3000
                            )

                    # FIX 34: Use pre-loaded maps instead of per-item queries
                    product = None
                    variant = None
                    variant_id = None
                    if variant_id_raw:
                        try:
                            variant_id = int(variant_id_raw)
                        except (TypeError, ValueError):
                            variant_id = None
                        if variant_id:
                            variant = _variants_map.get(variant_id)
                            if variant:
                                product = _products_by_id.get(variant.product_id)

                    if not product:
                        product_id = item.get("product_id")
                        if product_id:
                            try:
                                product = _products_by_id.get(int(product_id))
                            except (TypeError, ValueError):
                                pass

                    if not product and barcode:
                        product = _products_by_barcode.get(barcode)

                    if not product and description:
                        product = _products_by_desc.get(description)

                    quantity = Decimal(str(item["quantity"]))
                    unit_cost = Decimal(str(item["price"]))
                    # FIX 45: reject negative quantities/prices at commit point
                    if quantity <= 0 or unit_cost < 0:
                        continue
                    subtotal = quantity * unit_cost
                    is_batch = bool(batch_number)

                    if not product:
                        has_variants = bool(item.get("has_variants"))
                        if has_variants:
                            product_barcode = str(uuid.uuid4())
                        else:
                            product_barcode = barcode or str(uuid.uuid4())
                        new_product = Product(
                            barcode=product_barcode,
                            description=description,
                            category=item["category"],
                            company_id=company_id,
                            branch_id=branch_id,
                            stock=quantity,
                            unit=item["unit"],
                            purchase_price=unit_cost,
                            sale_price=Decimal(str(item["sale_price"])),
                            default_supplier_id=supplier_id,
                        )
                        session.add(new_product)
                        session.flush()

                        product = new_product
                        product_id = new_product.id
                        # Update pre-loaded maps for later items in same batch
                        _products_by_id[product_id] = new_product
                        if new_product.barcode:
                            _products_by_barcode[new_product.barcode] = new_product
                        if new_product.description:
                            _products_by_desc[new_product.description] = new_product

                        if has_variants:
                            sku = barcode or str(uuid.uuid4())
                            size = (item.get("variant_size") or "").strip() or None
                            color = (item.get("variant_color") or "").strip() or None
                            variant = ProductVariant(
                                product_id=product_id,
                                sku=sku,
                                size=size,
                                color=color,
                                stock=quantity if not is_batch else Decimal("0.0000"),
                                company_id=company_id,
                                branch_id=branch_id,
                            )
                            session.add(variant)
                            session.flush()
                            _variants_map[variant.id] = variant
                            if is_batch:
                                batch = ProductBatch(
                                    batch_number=batch_number,
                                    expiration_date=expiration_date,
                                    stock=quantity,
                                    product_variant_id=variant.id,
                                    company_id=company_id,
                                    branch_id=branch_id,
                                )
                                session.add(batch)
                                variants_recalc_batches.add(variant.id)
                                products_recalc_variants.add(product_id)
                            else:
                                products_recalc_variants.add(product_id)
                        else:
                            if is_batch:
                                batch = session.exec(
                                    select(ProductBatch)
                                    .where(ProductBatch.product_id == product_id)
                                    .where(ProductBatch.product_variant_id.is_(None))
                                    .where(ProductBatch.batch_number == batch_number)
                                    .where(ProductBatch.company_id == company_id)
                                    .where(ProductBatch.branch_id == branch_id)
                                    .with_for_update()
                                ).first()
                                if batch:
                                    batch.stock = (
                                        Decimal(str(batch.stock or 0)) + quantity
                                    )
                                    if expiration_date:
                                        batch.expiration_date = expiration_date
                                else:
                                    batch = ProductBatch(
                                        batch_number=batch_number,
                                        expiration_date=expiration_date,
                                        stock=quantity,
                                        product_id=product_id,
                                        product_variant_id=None,
                                        company_id=company_id,
                                        branch_id=branch_id,
                                    )
                                session.add(batch)
                                products_recalc_batches.add(product_id)

                        movement = StockMovement(
                            type="Ingreso",
                            product_id=product.id,
                            quantity=quantity,
                            description=f"Ingreso (Nuevo): {description}",
                            user_id=user_id,
                            company_id=company_id,
                            branch_id=branch_id,
                        )
                        session.add(movement)
                    else:
                        _sp_val = float(item.get("sale_price") or 0)
                        _pp_val = float(item.get("price") or 0)
                        _global_margin = getattr(self, "effective_profit_margin_decimal", 0.0)
                        # Si el precio coincide con el margen global → dinámico (NULL).
                        # Si el usuario lo personalizó → guardar precio Y calcular el
                        # margen resultante, para que Inventario lo muestre correctamente.
                        if _sp_val > 0 and price_matches_margin(_sp_val, _pp_val, _global_margin):
                            new_sale_price = None
                            new_custom_margin = None
                        else:
                            new_sale_price = Decimal(str(_sp_val)) if _sp_val > 0 else None
                            if new_sale_price is not None and _pp_val > 0:
                                _calc = round((_sp_val - _pp_val) / _pp_val * 100, 2)
                                new_custom_margin = Decimal(str(_calc))
                            else:
                                new_custom_margin = None
                        if variant:
                            variant.sale_price = new_sale_price
                            session.add(variant)
                        else:
                            product.sale_price = new_sale_price
                            product.custom_profit_margin = new_custom_margin
                        product.purchase_price = unit_cost
                        if supplier_id:
                            product.default_supplier_id = supplier_id
                        session.add(product)

                        if variant:
                            if is_batch:
                                batch = session.exec(
                                    select(ProductBatch)
                                    .where(
                                        ProductBatch.product_variant_id == variant.id
                                    )
                                    .where(ProductBatch.batch_number == batch_number)
                                    .where(ProductBatch.company_id == company_id)
                                    .where(ProductBatch.branch_id == branch_id)
                                    .with_for_update()
                                ).first()
                                if batch:
                                    batch.stock = (
                                        Decimal(str(batch.stock or 0)) + quantity
                                    )
                                    if expiration_date:
                                        batch.expiration_date = expiration_date
                                else:
                                    batch = ProductBatch(
                                        batch_number=batch_number,
                                        expiration_date=expiration_date,
                                        stock=quantity,
                                        product_variant_id=variant.id,
                                        company_id=company_id,
                                        branch_id=branch_id,
                                    )
                                session.add(batch)
                                variants_recalc_batches.add(variant.id)
                                products_recalc_variants.add(product.id)
                            else:
                                variant.stock = (
                                    Decimal(str(variant.stock or 0)) + quantity
                                )
                                session.add(variant)
                                products_recalc_variants.add(product.id)
                        else:
                            if is_batch:
                                batch = session.exec(
                                    select(ProductBatch)
                                    .where(ProductBatch.product_id == product.id)
                                    .where(ProductBatch.product_variant_id.is_(None))
                                    .where(ProductBatch.batch_number == batch_number)
                                    .where(ProductBatch.company_id == company_id)
                                    .where(ProductBatch.branch_id == branch_id)
                                    .with_for_update()
                                ).first()
                                if batch:
                                    batch.stock = (
                                        Decimal(str(batch.stock or 0)) + quantity
                                    )
                                    if expiration_date:
                                        batch.expiration_date = expiration_date
                                else:
                                    batch = ProductBatch(
                                        batch_number=batch_number,
                                        expiration_date=expiration_date,
                                        stock=quantity,
                                        product_id=product.id,
                                        product_variant_id=None,
                                        company_id=company_id,
                                        branch_id=branch_id,
                                    )
                                session.add(batch)
                                products_recalc_batches.add(product.id)
                            else:
                                product.stock = (
                                    Decimal(str(product.stock or 0)) + quantity
                                )
                                session.add(product)

                        movement = StockMovement(
                            type="Ingreso",
                            product_id=product.id,
                            quantity=quantity,
                            description=f"Ingreso: {description}",
                            user_id=user_id,
                            company_id=company_id,
                            branch_id=branch_id,
                        )
                        session.add(movement)

                    variant_label = self._variant_label(variant) if variant else ""
                    description_snapshot = (
                        product.description if product else description
                    )
                    if variant_label:
                        description_snapshot = (
                            f"{description_snapshot} ({variant_label})"
                        )
                    product_barcode = variant.sku if variant else product.barcode
                    product_category = (
                        product.category if product else item.get("category", "")
                    )

                    _orig_cost = item.get("original_cost") or 0
                    _orig_rate = item.get("purchase_rate") or 0
                    _orig_curr = item.get("original_currency") or ""
                    purchase_item = PurchaseItem(
                        purchase_id=purchase.id,
                        product_id=product.id if product else None,
                        company_id=company_id,
                        branch_id=branch_id,
                        description_snapshot=description_snapshot,
                        barcode_snapshot=product_barcode or barcode,
                        category_snapshot=product_category or item.get("category", ""),
                        quantity=quantity,
                        unit=item.get("unit", MSG.FALLBACK_UNIT),
                        unit_cost=unit_cost,
                        subtotal=subtotal,
                        original_price=Decimal(str(_orig_cost)) if _orig_cost else None,
                        exchange_rate=Decimal(str(_orig_rate)) if _orig_rate else None,
                        original_currency_code=_orig_curr if _orig_curr else None,
                    )
                    session.add(purchase_item)

                # Recalcular totales de stock (3 fases) usando helper compartido
                recalculate_stock_totals(
                    session=session,
                    company_id=company_id,
                    branch_id=branch_id,
                    variants_from_batches=variants_recalc_batches,
                    products_from_variants=products_recalc_variants,
                    products_from_batches=products_recalc_batches,
                )

                session.commit()
            except Exception:
                session.rollback()
                logger.exception(
                    "confirm_entry failed | company=%s branch=%s items=%d",
                    company_id,
                    branch_id,
                    len(self.new_entry_items),
                )
                return rx.toast(
                    "Error al registrar el ingreso. Verifique los datos.",
                    duration=4000,
                )

        # Forzar actualización del inventario en la UI
        if hasattr(self, "_inventory_update_trigger"):
            self._inventory_update_trigger += 1
        if hasattr(self, "_purchase_update_trigger"):
            self._purchase_update_trigger += 1

        self.new_entry_items = []
        self._reset_entry_form()
        self._reset_purchase_form()
        return rx.toast("Ingreso de productos confirmado.", duration=3000)

    def _reset_entry_form(self):
        self.entry_form_key += 1
        self.entry_sale_price_key += 1
        self.new_entry_item = {
            "temp_id": "",
            "barcode": "",
            "description": "",
            "display_description": "",
            "category": self.categories[0] if hasattr(self, "categories") and self.categories else "",
            "quantity": 0,
            "unit": MSG.FALLBACK_UNIT,
            "price": 0,
            "sale_price": 0,
            "subtotal": 0,
            "product_id": None,
            "variant_id": None,
            "variant_size": "",
            "variant_color": "",
            "batch_code": "",
            "batch_date": "",
            "is_existing_product": False,
            "has_variants": False,
            "requires_batches": False,
            "original_cost": 0,
            "original_currency": "",
            "purchase_rate": 0,
        }
        self.entry_autocomplete_suggestions = []
        self.entry_autocomplete_active_index = -1
        self._entry_sale_price_manual = False
        self._set_new_product_mode()

    def _find_product_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Busca un producto por código de barras usando limpieza y validación"""
        code = clean_barcode(barcode)
        if not code or len(code) == 0:
            return None
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return None
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            variant = session.exec(
                select(ProductVariant)
                .where(ProductVariant.sku == code)
                .where(ProductVariant.company_id == company_id)
                .where(ProductVariant.branch_id == branch_id)
            ).first()
            if variant:
                parent = session.exec(
                    select(Product)
                    .where(Product.id == variant.product_id)
                    .where(Product.company_id == company_id)
                    .where(Product.branch_id == branch_id)
                ).first()
                if parent:
                    global_margin = getattr(self, "effective_profit_margin_decimal", 0.0)
                    effective_price = resolve_effective_price(parent, variant, global_margin)
                    return {
                        "id": str(parent.id),
                        "product_id": parent.id,
                        "variant_id": variant.id,
                        "barcode": variant.sku,
                        "description": parent.description,
                        "category": parent.category,
                        "stock": variant.stock,
                        "unit": parent.unit,
                        "purchase_price": parent.purchase_price,
                        "sale_price": effective_price,
                        "has_explicit_price": (
                            variant.sale_price is not None
                            or parent.sale_price is not None
                            or parent.custom_profit_margin is not None
                        ),
                    }

            p = session.exec(
                select(Product)
                .where(Product.barcode == code)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
            ).first()
            if p:
                global_margin = getattr(self, "effective_profit_margin_decimal", 0.0)
                effective_price = resolve_effective_price(p, global_margin=global_margin)
                return {
                    "id": str(p.id),
                    "product_id": p.id,
                    "variant_id": None,
                    "barcode": p.barcode,
                    "description": p.description,
                    "category": p.category,
                    "stock": p.stock,
                    "unit": p.unit,
                    "purchase_price": p.purchase_price,
                    "sale_price": effective_price,
                    "has_explicit_price": (
                        p.sale_price is not None or p.custom_profit_margin is not None
                    ),
                }
        return None

    def _fill_entry_item_from_product(self, product: Dict[str, Any]):
        db_barcode = product.get("barcode")
        self.new_entry_item["barcode"] = str(db_barcode) if db_barcode else (self.new_entry_item.get("barcode") or "")
        self.new_entry_item["description"] = product.get("description", "")
        self.new_entry_item["category"] = product.get("category") or MSG.FALLBACK_GENERAL
        self.new_entry_item["unit"] = product.get("unit") or MSG.FALLBACK_UNIT
        self.new_entry_item["price"] = float(product.get("purchase_price", 0) or 0)
        self.new_entry_item["sale_price"] = float(product.get("sale_price", 0) or 0)
        self.new_entry_item["product_id"] = product.get("product_id") or product.get("id")
        self.new_entry_item["quantity"] = 1
        self.new_entry_item["subtotal"] = self._round_currency(
            float(self.new_entry_item["quantity"]) * float(self.new_entry_item["price"])
        )

    @rx.event
    def select_product_for_entry(self, description: str):
        if isinstance(description, dict):
            description = (
                description.get("value")
                or description.get("description")
                or description.get("label")
                or ""
            )
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.entry_autocomplete_suggestions = []
            self.entry_autocomplete_active_index = -1
            return
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            product = session.exec(
                select(Product)
                .where(Product.description == description)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
            ).first()

            if product:
                _gm = getattr(self, "effective_profit_margin_decimal", 0.0)
                self._apply_existing_product_context(
                    {
                        "id": str(product.id),
                        "product_id": product.id,
                        "variant_id": None,
                        "barcode": product.barcode,
                        "description": product.description,
                        "category": product.category,
                        "stock": product.stock,
                        "unit": product.unit,
                        "purchase_price": product.purchase_price,
                        "sale_price": resolve_effective_price(product, global_margin=_gm),
                        "has_explicit_price": (product.sale_price is not None or product.custom_profit_margin is not None),
                    }
                )
        self.entry_autocomplete_suggestions = []
        self.entry_autocomplete_active_index = -1
