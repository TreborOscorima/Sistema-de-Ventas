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
    selected_supplier: Optional[Dict[str, Any]] = None

    entry_form_key: int = 0
    new_entry_item: TransactionItem = {
        "temp_id": "",
        "barcode": "",
        "description": "",
        "category": "General",
        "quantity": 0,
        "unit": "Unidad",
        "price": 0,
        "sale_price": 0,
        "subtotal": 0,
        "product_id": None,
    }
    new_entry_items: List[TransactionItem] = []
    entry_autocomplete_suggestions: List[str] = []

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
                if value:
                    search = str(value).lower()
                    with rx.session() as session:
                        products = session.exec(
                            select(Product)
                            .where(Product.description.contains(search))
                            .limit(5)
                        ).all()
                        self.entry_autocomplete_suggestions = [p.description for p in products]
                else:
                    self.entry_autocomplete_suggestions = []
            elif field == "barcode":
                # Si se borra el código de barras, limpiar todos los campos
                if not value or not str(value).strip():
                    self.new_entry_item["barcode"] = ""
                    self.new_entry_item["description"] = ""
                    self.new_entry_item["quantity"] = 0
                    self.new_entry_item["price"] = 0
                    self.new_entry_item["sale_price"] = 0
                    self.new_entry_item["subtotal"] = 0
                    self.entry_autocomplete_suggestions = []
                else:
                    # Limpiar el código de barras usando la utilidad
                    code = clean_barcode(str(value))
                    # Solo buscar si el código es válido
                    if validate_barcode(code):
                        product = self._find_product_by_barcode(code)
                        if product:
                            self._fill_entry_item_from_product(product)
                            self.entry_autocomplete_suggestions = []
                            return rx.toast(f"Producto '{product['description']}' cargado", duration=2000)
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
        search = f"%{term}%"
        with rx.session() as session:
            suppliers = session.exec(
                select(Supplier)
                .where(
                    or_(
                        Supplier.name.ilike(search),
                        Supplier.tax_id.ilike(search),
                    )
                )
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

    @rx.event
    def clear_selected_supplier(self):
        self.selected_supplier = None

    def _reset_purchase_form(self):
        self.purchase_doc_type = "boleta"
        self.purchase_series = ""
        self.purchase_number = ""
        self.purchase_issue_date = ""
        self.purchase_notes = ""
        self.purchase_supplier_query = ""
        self.purchase_supplier_suggestions = []
        self.selected_supplier = None

    @rx.event
    def process_entry_barcode_from_input(self, barcode_value):
        """Procesa el barcode del input cuando pierde el foco"""
        # Actualizar el estado con el valor del input
        self.new_entry_item["barcode"] = str(barcode_value) if barcode_value else ""
        
        if not barcode_value or not str(barcode_value).strip():
            self.new_entry_item["barcode"] = ""
            self.new_entry_item["description"] = ""
            self.new_entry_item["quantity"] = 0
            self.new_entry_item["price"] = 0
            self.new_entry_item["sale_price"] = 0
            self.new_entry_item["subtotal"] = 0
            self.entry_autocomplete_suggestions = []
            return
        
        code = clean_barcode(str(barcode_value))
        if validate_barcode(code):
            product = self._find_product_by_barcode(code)
            if product:
                self._fill_entry_item_from_product(product)
                self.entry_autocomplete_suggestions = []
                return rx.toast(f"Producto '{product['description']}' cargado", duration=2000)

    @rx.event
    def handle_barcode_enter(self, key: str, input_id: str):
        """Detecta la tecla Enter y fuerza el blur del input para procesar"""
        if key == "Enter":
            return rx.call_script(f"document.getElementById('{input_id}').blur()")

    @rx.event
    def add_item_to_entry(self):
        if not self.current_user["privileges"]["create_ingresos"]:
            return rx.toast("No tiene permisos para crear ingresos.", duration=3000)
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
        item_copy = self.new_entry_item.copy()
        item_copy["temp_id"] = str(uuid.uuid4())
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
                self.new_entry_items = [
                    entry for entry in self.new_entry_items if entry["temp_id"] != temp_id
                ]
                self.entry_autocomplete_suggestions = []
                return

    @rx.event
    def confirm_entry(self):
        if not self.current_user["privileges"]["create_ingresos"]:
            return rx.toast("No tiene permisos para crear ingresos.", duration=3000)
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

        with rx.session() as session:
            try:
                existing_doc = session.exec(
                    select(Purchase).where(
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
                user = session.exec(select(UserModel).where(UserModel.username == self.current_user["username"])).first()
                user_id = user.id if user else None

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
                    supplier_id=supplier_id,
                    user_id=user_id,
                )
                session.add(purchase)
                session.flush()

                for item in self.new_entry_items:
                    barcode = (item.get("barcode") or "").strip()
                    description = item["description"].strip()

                    product = None
                    if barcode:
                        product = session.exec(
                            select(Product).where(Product.barcode == barcode)
                        ).first()

                    if not product:
                        # Probar por descripcion si no hay barcode
                        product = session.exec(
                            select(Product).where(Product.description == description)
                        ).first()

                    quantity = Decimal(str(item["quantity"]))
                    unit_cost = Decimal(str(item["price"]))
                    subtotal = quantity * unit_cost

                    if product:
                        # Actualizar
                        product.stock += quantity
                        product.purchase_price = unit_cost
                        if item["sale_price"] > 0:
                            product.sale_price = Decimal(str(item["sale_price"]))
                        product.category = item["category"]
                        session.add(product)

                        # Registrar movimiento
                        movement = StockMovement(
                            type="Ingreso",
                            product_id=product.id,
                            quantity=quantity,
                            description=f"Ingreso: {description}",
                            user_id=user_id,
                        )
                        session.add(movement)
                        product_id = product.id
                        product_barcode = product.barcode
                        product_category = product.category
                    else:
                        # Crear
                        new_product = Product(
                            barcode=barcode or str(uuid.uuid4()),
                            description=description,
                            category=item["category"],
                            stock=quantity,
                            unit=item["unit"],
                            purchase_price=unit_cost,
                            sale_price=Decimal(str(item["sale_price"])),
                        )
                        session.add(new_product)
                        session.flush()  # Obtener ID

                        # Registrar movimiento
                        movement = StockMovement(
                            type="Ingreso",
                            product_id=new_product.id,
                            quantity=quantity,
                            description=f"Ingreso (Nuevo): {description}",
                            user_id=user_id,
                        )
                        session.add(movement)
                        product_id = new_product.id
                        product_barcode = new_product.barcode
                        product_category = new_product.category

                    purchase_item = PurchaseItem(
                        purchase_id=purchase.id,
                        product_id=product_id,
                        description_snapshot=description,
                        barcode_snapshot=product_barcode or barcode,
                        category_snapshot=product_category or item.get("category", ""),
                        quantity=quantity,
                        unit=item.get("unit", "Unidad"),
                        unit_cost=unit_cost,
                        subtotal=subtotal,
                    )
                    session.add(purchase_item)

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
            "category": self.categories[0] if hasattr(self, "categories") and self.categories else "",
            "quantity": 0,
            "unit": "Unidad",
            "price": 0,
            "sale_price": 0,
            "subtotal": 0,
            "product_id": None,
        }
        self.entry_autocomplete_suggestions = []

    def _find_product_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Busca un producto por código de barras usando limpieza y validación"""
        code = clean_barcode(barcode)
        if not code or len(code) == 0:
            return None
        
        with rx.session() as session:
            p = session.exec(select(Product).where(Product.barcode == code)).first()
            if p:
                return {
                    "id": str(p.id),
                    "barcode": p.barcode,
                    "description": p.description,
                    "category": p.category,
                    "stock": p.stock,
                    "unit": p.unit,
                    "purchase_price": p.purchase_price,
                    "sale_price": p.sale_price,
                }
        return None

    def _fill_entry_item_from_product(self, product: Product):
        self.new_entry_item["barcode"] = product.get("barcode", "")
        self.new_entry_item["description"] = product.get("description", "")
        self.new_entry_item["category"] = product.get("category", "")
        self.new_entry_item["unit"] = product.get("unit", "Unidad")
        self.new_entry_item["price"] = product.get("purchase_price", 0)
        self.new_entry_item["sale_price"] = product.get("sale_price", 0)
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
        
        with rx.session() as session:
            product = session.exec(
                select(Product).where(Product.description == description)
            ).first()
            
            if product:
                self._fill_entry_item_from_product({
                    "barcode": product.barcode,
                    "description": product.description,
                    "category": product.category,
                    "stock": product.stock,
                    "unit": product.unit,
                    "purchase_price": product.purchase_price,
                    "sale_price": product.sale_price,
                })
        self.entry_autocomplete_suggestions = []
