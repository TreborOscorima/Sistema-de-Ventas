import reflex as rx
from typing import List, Dict, Any
import datetime
import uuid
import logging
import io
from .types import Product, InventoryAdjustment
from .mixin_state import MixinState
from app.utils.exports import create_excel_workbook, style_header_row, add_data_rows, auto_adjust_column_widths

class InventoryState(MixinState):
    inventory: Dict[str, Product] = {}
    categories: List[str] = ["General"]
    new_category_name: str = ""
    inventory_search_term: str = ""
    
    editing_product: Product = {
        "id": "",
        "barcode": "",
        "description": "",
        "category": "",
        "stock": 0,
        "unit": "",
        "purchase_price": 0,
        "sale_price": 0,
    }
    is_editing_product: bool = False
    
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
    }
    inventory_adjustment_items: List[InventoryAdjustment] = []
    inventory_adjustment_suggestions: List[str] = []

    def update_new_category_name(self, value: str):
        self.new_category_name = value

    def add_category(self):
        if self.new_category_name and self.new_category_name not in self.categories:
            self.categories.append(self.new_category_name)
            self.new_category_name = ""

    def remove_category(self, category: str):
        if category in self.categories:
            self.categories.remove(category)

    def handle_inventory_adjustment_change(self, field: str, value: Any):
        self.inventory_adjustment_item[field] = value

    @rx.var
    def inventory_list(self) -> list[Product]:
        if not self.current_user["privileges"]["view_inventario"]:
            return []
        for product in self.inventory.values():
            if "barcode" not in product:
                product["barcode"] = ""
            if "category" not in product:
                product["category"] = self.categories[0] if self.categories else ""
        if self.inventory_search_term:
            search = self.inventory_search_term.lower()
            return sorted(
                [
                    p
                    for p in self.inventory.values()
                    if search in p["description"].lower()
                    or search in p.get("barcode", "").lower()
                    or search in p.get("category", "").lower()
                ],
                key=lambda p: p["description"],
            )
        return sorted(list(self.inventory.values()), key=lambda p: p["description"])

    @rx.event
    def set_inventory_search_term(self, value: str):
        self.inventory_search_term = value or ""

    @rx.event
    def open_edit_product(self, product: Product):
        if not self.current_user["privileges"]["edit_inventario"]:
            return rx.toast("No tiene permisos para editar el inventario.", duration=3000)
        self.editing_product = product.copy()
        self.is_editing_product = True

    @rx.event
    def cancel_edit_product(self):
        self.is_editing_product = False
        self.editing_product = {
            "id": "",
            "barcode": "",
            "description": "",
            "category": "",
            "stock": 0,
            "unit": "",
            "purchase_price": 0,
            "sale_price": 0,
        }

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

    @rx.event
    def save_edited_product(self):
        if not self.current_user["privileges"]["edit_inventario"]:
            return rx.toast("No tiene permisos para editar el inventario.", duration=3000)
        
        old_id = self.editing_product["id"]
        new_description = self.editing_product["description"].strip()
        new_id = new_description.lower()
        
        if not new_description:
             return rx.toast("La descripción no puede estar vacía.", duration=3000)

        if new_id != old_id:
            if new_id in self.inventory:
                 return rx.toast("Ya existe un producto con esa descripción.", duration=3000)
            del self.inventory[old_id]
            self.editing_product["id"] = new_id
        
        self.inventory[new_id] = self.editing_product
        self.is_editing_product = False
        return rx.toast("Producto actualizado correctamente.", duration=3000)

    @rx.event
    def delete_product(self, product_id: str):
        if not self.current_user["privileges"]["edit_inventario"]:
             return rx.toast("No tiene permisos para eliminar productos.", duration=3000)
        
        if product_id in self.inventory:
            del self.inventory[product_id]
            return rx.toast("Producto eliminado.", duration=3000)

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
        }
        self.inventory_adjustment_suggestions = []

    def _fill_inventory_adjustment_from_product(self, product: Product):
        self.inventory_adjustment_item["barcode"] = product.get("barcode", "")
        self.inventory_adjustment_item["description"] = product.get("description", "")
        self.inventory_adjustment_item["category"] = product.get("category", "")
        self.inventory_adjustment_item["unit"] = product.get("unit", "Unidad")
        self.inventory_adjustment_item["current_stock"] = product.get("stock", 0)
        self.inventory_adjustment_item["adjust_quantity"] = 0
        self.inventory_adjustment_item["reason"] = ""

    @rx.event
    def select_inventory_adjustment_product(self, description: str):
        if isinstance(description, dict):
            description = (
                description.get("value")
                or description.get("description")
                or description.get("label")
                or ""
            )
        product_id = description.lower().strip()
        if product_id in self.inventory:
            self._fill_inventory_adjustment_from_product(self.inventory[product_id])
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
        if not description:
            return rx.toast("Seleccione un producto para ajustar.", duration=3000)
        product_id = description.lower()
        if product_id not in self.inventory:
            return rx.toast("Producto no encontrado en el inventario.", duration=3000)
        quantity = self.inventory_adjustment_item["adjust_quantity"]
        if quantity <= 0:
            return rx.toast("Ingrese la cantidad a ajustar.", duration=3000)
        available = self.inventory[product_id]["stock"]
        if quantity > available:
            return rx.toast(
                "La cantidad supera el stock disponible.", duration=3000
            )
        item_copy = self.inventory_adjustment_item.copy()
        item_copy["temp_id"] = str(uuid.uuid4())
        item_copy["adjust_quantity"] = self._normalize_quantity_value(
            item_copy.get("adjust_quantity", 0), item_copy.get("unit", "")
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
            return rx.toast(
                "No tiene permisos para registrar inventario.", duration=3000
            )
        status = (
            self.inventory_check_status
            if self.inventory_check_status in ["perfecto", "ajuste"]
            else "perfecto"
        )
        notes = self.inventory_adjustment_notes.strip()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if status == "perfecto":
            if hasattr(self, "history"):
                self.history.append(
                    {
                        "id": str(uuid.uuid4()),
                        "timestamp": timestamp,
                        "type": "Inventario Perfecto",
                        "product_description": "Inventario fisico verificado sin diferencias.",
                        "quantity": 0,
                        "unit": "-",
                        "total": 0,
                        "payment_method": "Inventario Perfecto",
                        "payment_details": "Sin diferencias",
                        "user": self.current_user["username"],
                        "sale_id": "",
                    }
                )
        else:
            if not self.inventory_adjustment_items:
                return rx.toast(
                    "Agregue los productos que requieren re ajuste.", duration=3000
                )
            recorded = False
            for item in self.inventory_adjustment_items:
                description = item["description"].strip()
                if not description:
                    continue
                product_id = description.lower()
                if product_id not in self.inventory:
                    continue
                quantity = item.get("adjust_quantity", 0) or 0
                if quantity <= 0:
                    continue
                available = self.inventory[product_id]["stock"]
                qty = min(quantity, available)
                qty = self._normalize_quantity_value(
                    qty, item.get("unit") or self.inventory[product_id]["unit"]
                )
                new_stock = max(available - qty, 0)
                self.inventory[product_id]["stock"] = self._normalize_quantity_value(
                    new_stock, self.inventory[product_id]["unit"]
                )
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
                if hasattr(self, "history"):
                    self.history.append(
                        {
                            "id": str(uuid.uuid4()),
                            "timestamp": timestamp,
                            "type": "Re Ajuste Inventario",
                            "product_description": description,
                            "quantity": -qty,
                            "unit": item.get("unit") or "-",
                            "total": 0,
                            "payment_method": "Re Ajuste Inventario",
                            "payment_details": details,
                            "user": self.current_user["username"],
                            "sale_id": "",
                        }
                    )
                recorded = True
            if not recorded:
                return rx.toast(
                    "No se pudo registrar el re ajuste. Verifique los productos.",
                    duration=3000,
                )
        self.inventory_check_modal_open = False
        self.inventory_check_status = "perfecto"
        self.inventory_adjustment_notes = ""
        self.inventory_adjustment_items = []
        self._reset_inventory_adjustment_form()
        return rx.toast("Registro de inventario guardado.", duration=3000)

    @rx.event
    def export_inventory_to_excel(self):
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)
        
        wb, ws = create_excel_workbook("Inventario Actual")
        
        headers = [
            "Codigo de Barra",
            "Descripcion",
            "Categoria",
            "Unidad",
            "Stock Sistema",
            "Precio Compra",
            "Precio Venta",
            "Valor Total",
            "Conteo Fisico",
            "Diferencia",
            "Notas Adicionales",
        ]
        style_header_row(ws, 1, headers)
        
        products = sorted(
            self.inventory.values(), key=lambda p: p.get("description", "").lower()
        )
        
        rows = []
        for product in products:
            barcode = product.get("barcode", "")
            description = product.get("description", "")
            category = product.get(
                "category", self.categories[0] if self.categories else ""
            )
            unit = product.get("unit", "Unidad")
            stock = product.get("stock", 0)
            purchase_price = product.get("purchase_price", 0)
            sale_price = product.get("sale_price", 0)
            total_value = stock * purchase_price
            
            rows.append([
                barcode,
                description,
                category,
                unit,
                stock,
                purchase_price,
                sale_price,
                total_value,
                "",  # Conteo Fisico
                "",  # Diferencia
                "",  # Notas Adicionales
            ])
            
        add_data_rows(ws, rows, 2)
        auto_adjust_column_widths(ws)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return rx.download(data=output.getvalue(), filename="inventario_actual.xlsx")
