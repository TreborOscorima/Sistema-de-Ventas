import reflex as rx
from typing import List, Dict, Any
import datetime
import uuid
import logging
from .types import TransactionItem, Product
from .mixin_state import MixinState
from app.utils.barcode import clean_barcode, validate_barcode

class IngresoState(MixinState):
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
                self.new_entry_item["quantity"] * self.new_entry_item["price"]
            )
            if field == "description":
                if value:
                    search = str(value).lower()
                    if hasattr(self, "inventory"):
                        self.entry_autocomplete_suggestions = [
                            p["description"]
                            for p in self.inventory.values()
                            if search in p["description"].lower()
                        ][:5]
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
        
        if hasattr(self, "inventory"):
            for item in self.new_entry_items:
                product_id = item["description"].lower().strip()
                barcode = item.get("barcode", "").strip()
                sale_price = item.get("sale_price", 0)
                purchase_price = item["price"]
                if product_id in self.inventory:
                    if "barcode" not in self.inventory[product_id]:
                        self.inventory[product_id]["barcode"] = ""
                    self.inventory[product_id]["stock"] += item["quantity"]
                    self.inventory[product_id]["stock"] = self._normalize_quantity_value(
                        self.inventory[product_id]["stock"],
                        self.inventory[product_id]["unit"],
                    )
                    self.inventory[product_id]["purchase_price"] = purchase_price
                    if barcode:
                        self.inventory[product_id]["barcode"] = barcode
                    if sale_price > 0:
                        self.inventory[product_id]["sale_price"] = sale_price
                    self.inventory[product_id]["category"] = item["category"]
                else:
                    default_sale_price = (
                        sale_price if sale_price > 0 else purchase_price * 1.25
                    )
                    self.inventory[product_id] = {
                        "id": product_id,
                        "barcode": barcode,
                        "description": item["description"],
                        "category": item["category"],
                        "stock": item["quantity"],
                        "unit": item["unit"],
                        "purchase_price": purchase_price,
                        "sale_price": self._round_currency(default_sale_price),
                    }
                if hasattr(self, "history"):
                    self.history.append(
                        {
                            "id": str(uuid.uuid4()),
                            "timestamp": timestamp,
                            "type": "Ingreso",
                            "product_description": item["description"],
                            "quantity": item["quantity"],
                            "unit": item["unit"],
                            "total": item["subtotal"],
                            "payment_method": "",
                            "payment_details": "",
                            "user": self.current_user["username"],
                            "sale_id": "",
                        }
                    )
        self.new_entry_items = []
        self._reset_entry_form()
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
        }
        self.entry_autocomplete_suggestions = []

    def _find_product_by_barcode(self, barcode: str) -> Product | None:
        """Busca un producto por código de barras usando limpieza y validación"""
        code = clean_barcode(barcode)
        if not code or len(code) == 0:
            return None
        
        if not hasattr(self, "inventory"):
            return None

        logging.info(f"[BUSCAR] Código limpio: '{code}' (long: {len(code)})")
        
        # Buscar coincidencia exacta
        for product in self.inventory.values():
            product_code = product.get("barcode", "")
            if product_code:
                clean_product_code = clean_barcode(product_code)
                if clean_product_code == code:
                    logging.info(f"[BUSCAR] ✓ Exacta: '{clean_product_code}' = '{code}'")
                    return product
        
        logging.warning(f"[BUSCAR] ✗ Sin coincidencia exacta para: '{code}'")
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
            self.new_entry_item["quantity"] * self.new_entry_item["price"]
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
        product_id = description.lower().strip()
        if hasattr(self, "inventory") and product_id in self.inventory:
            self._fill_entry_item_from_product(self.inventory[product_id])
        self.entry_autocomplete_suggestions = []
