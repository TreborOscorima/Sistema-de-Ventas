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
from .types import TransactionItem
from .mixin_state import MixinState
from app.utils.barcode import clean_barcode, validate_barcode
from app.utils.sanitization import sanitize_text

class IngresoState(MixinState):
    purchase_doc_type: str = "boleta"
    purchase_series: str = ""
    purchase_number: str = ""
    purchase_issue_date: str = ""
    purchase_notes: str = ""
    purchase_supplier_query: str = ""
    purchase_supplier_suggestions: List[Dict[str, Any]] = []
    purchase_supplier_input_key: int = 0
    selected_supplier: Optional[Dict[str, Any]] = None
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
    new_entry_item: TransactionItem = {
        "temp_id": "",
        "barcode": "",
        "description": "",
        "display_description": "",
        "category": "General",
        "quantity": 0,
        "unit": "Unidad",
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
    }
    new_entry_items: List[TransactionItem] = []
    entry_autocomplete_suggestions: List[str] = []
    last_processed_entry_barcode: str = ""

    @rx.var
    def entry_subtotal(self) -> float:
        return self.new_entry_item["subtotal"]

    @rx.var
    def entry_total(self) -> float:
        return self._round_currency(
            sum((item["subtotal"] for item in self.new_entry_items))
        )

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
                else:
                    self.new_entry_item[field] = self._round_currency(numeric)
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
                term = (str(value) if value is not None else "").strip()
                if len(term) >= 2:
                    description_prefix = f"{term}%"
                    description_contains = f"%{term}%"
                    barcode_prefix = f"{term}%"
                    company_id = self._company_id()
                    branch_id = self._branch_id()
                    if not company_id or not branch_id:
                        self.entry_autocomplete_suggestions = []
                        return
                    with rx.session() as session:
                        products = session.exec(
                            select(Product)
                            .where(
                                or_(
                                    Product.description.ilike(description_prefix),
                                    Product.barcode.ilike(barcode_prefix),
                                )
                            )
                            .where(Product.company_id == company_id)
                            .where(Product.branch_id == branch_id)
                            .order_by(Product.description)
                            .limit(8)
                        ).all()
                        if not products and len(term) >= 4:
                            products = session.exec(
                                select(Product)
                                .where(Product.description.ilike(description_contains))
                                .where(Product.company_id == company_id)
                                .where(Product.branch_id == branch_id)
                                .order_by(Product.description)
                                .limit(8)
                            ).all()
                        self.entry_autocomplete_suggestions = [p.description for p in products]
                else:
                    self.entry_autocomplete_suggestions = []
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
            return
        name_prefix = f"{term}%"
        name_search = f"%{term}%"
        tax_id_prefix = f"{term}%"
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.purchase_supplier_suggestions = []
            return
        with rx.session() as session:
            suppliers = session.exec(
                select(Supplier)
                .where(
                    or_(
                        Supplier.name.ilike(name_prefix),
                        Supplier.tax_id.ilike(tax_id_prefix),
                    )
                )
                .where(Supplier.company_id == company_id)
                .where(Supplier.branch_id == branch_id)
                .order_by(Supplier.name)
                .limit(6)
            ).all()
            if not suppliers and len(term) >= 4:
                suppliers = session.exec(
                    select(Supplier)
                    .where(Supplier.name.ilike(name_search))
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
        self.purchase_supplier_input_key += 1

    @rx.event
    def clear_selected_supplier(self):
        self.selected_supplier = None

    @rx.event
    def clear_supplier_search(self):
        self.selected_supplier = None
        self.purchase_supplier_query = ""
        self.purchase_supplier_suggestions = []
        self.purchase_supplier_input_key += 1

    def _reset_purchase_form(self):
        self.purchase_doc_type = "boleta"
        self.purchase_series = ""
        self.purchase_number = ""
        self.purchase_issue_date = ""
        self.purchase_notes = ""
        self.purchase_supplier_query = ""
        self.purchase_supplier_suggestions = []
        self.purchase_supplier_input_key += 1
        self.selected_supplier = None

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

    def _process_entry_barcode(self, barcode_value: str | None):
        raw_barcode = str(barcode_value) if barcode_value is not None else ""
        self.new_entry_item["barcode"] = raw_barcode
        if not raw_barcode.strip():
            self.new_entry_item["barcode"] = ""
            self.new_entry_item["description"] = ""
            self.new_entry_item["quantity"] = 0
            self.new_entry_item["price"] = 0
            self.new_entry_item["sale_price"] = 0
            self.new_entry_item["subtotal"] = 0
            self.entry_autocomplete_suggestions = []
            self.last_processed_entry_barcode = ""
            self._set_new_product_mode()
            return

        code = clean_barcode(raw_barcode)
        if not code:
            return
        if code == self.last_processed_entry_barcode:
            return
        if len(code) < 6:
            return
        if validate_barcode(code):
            product = self._find_product_by_barcode(code)
            self.last_processed_entry_barcode = code
            if product:
                self._apply_existing_product_context(product)
                self.entry_autocomplete_suggestions = []
                return rx.toast(
                    f"Producto '{product['description']}' cargado",
                    duration=1500,
                )
        self._set_new_product_mode()

    @rx.event
    def process_entry_barcode_from_input(self, barcode_value):
        """Procesa el barcode del input cuando pierde el foco"""
        return self._process_entry_barcode(barcode_value)

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
                else "General"
            )
            self.new_entry_item["category"] = fallback_category
        if (
            not self.new_entry_item["description"]
            or not self.new_entry_item["category"]
            or self.new_entry_item["quantity"] <= 0
            or self.new_entry_item["price"] <= 0
            or self.new_entry_item["sale_price"] <= 0
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
        self.new_entry_items.append(item_copy)
        self._reset_entry_form()

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
                self.entry_autocomplete_suggestions = []
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
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
            issue_date_raw = datetime.datetime.now().strftime("%Y-%m-%d")
        try:
            issue_date = datetime.datetime.strptime(issue_date_raw, "%Y-%m-%d")
        except ValueError:
            return rx.toast("Fecha de documento invalida.", duration=3000)

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)

        with rx.session() as session:
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
                        "Documento ya registrado para este proveedor.",
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

                currency_code = getattr(self, "selected_currency_code", "PEN")
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

                    product = None
                    variant = None
                    if variant_id_raw:
                        try:
                            variant_id = int(variant_id_raw)
                        except (TypeError, ValueError):
                            variant_id = None
                        if variant_id:
                            variant = session.exec(
                                select(ProductVariant)
                                .where(ProductVariant.id == variant_id)
                                .where(ProductVariant.company_id == company_id)
                                .where(ProductVariant.branch_id == branch_id)
                            ).first()
                            if variant:
                                product = session.exec(
                                    select(Product)
                                    .where(Product.id == variant.product_id)
                                    .where(Product.company_id == company_id)
                                    .where(Product.branch_id == branch_id)
                                ).first()

                    if not product:
                        product_id = item.get("product_id")
                        if product_id:
                            product = session.exec(
                                select(Product)
                                .where(Product.id == product_id)
                                .where(Product.company_id == company_id)
                                .where(Product.branch_id == branch_id)
                            ).first()

                    if not product and barcode:
                        product = session.exec(
                            select(Product)
                            .where(Product.barcode == barcode)
                            .where(Product.company_id == company_id)
                            .where(Product.branch_id == branch_id)
                        ).first()

                    if not product and description:
                        product = session.exec(
                            select(Product)
                            .where(Product.description == description)
                            .where(Product.company_id == company_id)
                            .where(Product.branch_id == branch_id)
                        ).first()

                    quantity = Decimal(str(item["quantity"]))
                    unit_cost = Decimal(str(item["price"]))
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
                        )
                        session.add(new_product)
                        session.flush()

                        product = new_product
                        product_id = new_product.id

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
                        if item["sale_price"] > 0:
                            product.sale_price = Decimal(str(item["sale_price"]))
                        product.purchase_price = unit_cost
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

                    purchase_item = PurchaseItem(
                        purchase_id=purchase.id,
                        product_id=product.id if product else None,
                        company_id=company_id,
                        branch_id=branch_id,
                        description_snapshot=description_snapshot,
                        barcode_snapshot=product_barcode or barcode,
                        category_snapshot=product_category or item.get("category", ""),
                        quantity=quantity,
                        unit=item.get("unit", "Unidad"),
                        unit_cost=unit_cost,
                        subtotal=subtotal,
                    )
                    session.add(purchase_item)

                if variants_recalc_batches:
                    for variant_id in variants_recalc_batches:
                        total_query = (
                            select(func.coalesce(func.sum(ProductBatch.stock), 0))
                            .where(ProductBatch.product_variant_id == variant_id)
                            .where(ProductBatch.company_id == company_id)
                            .where(ProductBatch.branch_id == branch_id)
                        )
                        total_row = session.exec(total_query).first()
                        if total_row is None:
                            total_stock = Decimal("0.0000")
                        elif isinstance(total_row, tuple):
                            total_stock = total_row[0]
                        else:
                            total_stock = total_row
                        variant = session.exec(
                            select(ProductVariant)
                            .where(ProductVariant.id == variant_id)
                            .where(ProductVariant.company_id == company_id)
                            .where(ProductVariant.branch_id == branch_id)
                        ).first()
                        if variant:
                            variant.stock = total_stock
                            session.add(variant)

                if products_recalc_variants:
                    for product_id in products_recalc_variants:
                        total_query = (
                            select(func.coalesce(func.sum(ProductVariant.stock), 0))
                            .where(ProductVariant.product_id == product_id)
                            .where(ProductVariant.company_id == company_id)
                            .where(ProductVariant.branch_id == branch_id)
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
                            product.stock = total_stock
                            session.add(product)

                if products_recalc_batches:
                    for product_id in (
                        products_recalc_batches - products_recalc_variants
                    ):
                        total_query = (
                            select(func.coalesce(func.sum(ProductBatch.stock), 0))
                            .where(ProductBatch.product_id == product_id)
                            .where(ProductBatch.product_variant_id.is_(None))
                            .where(ProductBatch.company_id == company_id)
                            .where(ProductBatch.branch_id == branch_id)
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
                            product.stock = total_stock
                            session.add(product)

                session.commit()
            except Exception:
                session.rollback()
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
        self.new_entry_item = {
            "temp_id": "",
            "barcode": "",
            "description": "",
            "display_description": "",
            "category": self.categories[0] if hasattr(self, "categories") and self.categories else "",
            "quantity": 0,
            "unit": "Unidad",
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
        }
        self.entry_autocomplete_suggestions = []
        self.last_processed_entry_barcode = ""
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
            p = session.exec(
                select(Product)
                .where(Product.barcode == code)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
            ).first()
            if p:
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
                    "sale_price": p.sale_price,
                }

            variant_row = session.exec(
                select(ProductVariant, Product)
                .join(Product, Product.id == ProductVariant.product_id)
                .where(ProductVariant.sku == code)
                .where(ProductVariant.company_id == company_id)
                .where(ProductVariant.branch_id == branch_id)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
            ).first()
            if variant_row:
                variant, parent = variant_row
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
                    "sale_price": parent.sale_price,
                }
        return None

    def _fill_entry_item_from_product(self, product: Dict[str, Any]):
        self.new_entry_item["barcode"] = product.get("barcode", "")
        self.new_entry_item["description"] = product.get("description", "")
        self.new_entry_item["category"] = product.get("category") or "General"
        self.new_entry_item["unit"] = product.get("unit") or "Unidad"
        self.new_entry_item["price"] = product.get("purchase_price", 0)
        self.new_entry_item["sale_price"] = product.get("sale_price", 0)
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
            return
        with rx.session() as session:
            product = session.exec(
                select(Product)
                .where(Product.description == description)
                .where(Product.company_id == company_id)
                .where(Product.branch_id == branch_id)
            ).first()
            
            if product:
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
                        "sale_price": product.sale_price,
                    }
                )
        self.entry_autocomplete_suggestions = []
