import reflex as rx
from typing import List, Dict, Any, Optional
import datetime
import uuid
import logging
import io
from sqlmodel import select
from app.models import Product, StockMovement, User as UserModel, Category, SaleItem
from .types import InventoryAdjustment
from .mixin_state import MixinState
from app.utils.exports import create_excel_workbook, style_header_row, add_data_rows, auto_adjust_column_widths

class InventoryState(MixinState):
    # inventory: Dict[str, Product] = {} # Removed in favor of DB
    # categories: List[str] = ["General"] # Replaced by DB
    new_category_name: str = ""
    inventory_search_term: str = ""
    
    editing_product: Dict[str, Any] = { # Changed type to Dict for form handling
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
    categories: List[str] = ["General"]
    _inventory_update_trigger: int = 0

    def load_categories(self):
        with rx.session() as session:
            cats = session.exec(select(Category).order_by(Category.name)).all()
            names = [c.name for c in cats]
            if "General" not in names:
                names.insert(0, "General")
            self.categories = names

    def update_new_category_name(self, value: str):
        self.new_category_name = value

    def add_category(self):
        name = (self.new_category_name or "").strip()
        if not name:
            return
        
        with rx.session() as session:
            existing = session.exec(select(Category).where(Category.name == name)).first()
            if not existing:
                session.add(Category(name=name))
                session.commit()
                self.new_category_name = ""
                self.load_categories()
                return rx.toast(f"Categoría '{name}' agregada.", duration=2000)
            else:
                return rx.toast("La categoría ya existe.", duration=2000)

    def remove_category(self, category: str):
        if category == "General":
            return rx.toast("No se puede eliminar la categoría General.", duration=3000)
            
        with rx.session() as session:
            cat = session.exec(select(Category).where(Category.name == category)).first()
            if cat:
                session.delete(cat)
                session.commit()
                self.load_categories()
                return rx.toast(f"Categoría '{category}' eliminada.", duration=2000)

    @rx.event
    def handle_inventory_adjustment_change(self, field: str, value: Any):
        self.inventory_adjustment_item[field] = value
        
        # Buscar productos cuando se escribe en el campo descripción
        if field == "description":
            search_term = str(value).strip().lower()
            if len(search_term) >= 2:
                with rx.session() as session:
                    products = session.exec(select(Product)).all()
                    # Filtrar productos que coincidan con el término de búsqueda
                    matching = [
                        p.description for p in products
                        if search_term in p.description.lower()
                        or search_term in p.barcode.lower()
                    ]
                    self.inventory_adjustment_suggestions = matching[:10]  # Limitar a 10 sugerencias
            else:
                self.inventory_adjustment_suggestions = []

    @rx.var
    def inventory_list(self) -> list[Product]:
        # Usar trigger para forzar recálculo
        _ = self._inventory_update_trigger
        if not self.current_user["privileges"]["view_inventario"]:
            return []
        
        with rx.session() as session:
            query = select(Product)
            products = session.exec(query).all()
            
            # Filter in python for flexibility with search terms
            if self.inventory_search_term:
                search = self.inventory_search_term.lower()
                products = [
                    p for p in products
                    if search in p.description.lower()
                    or search in p.barcode.lower()
                    or search in p.category.lower()
                ]
            
            return sorted(products, key=lambda p: p.description)

    @rx.event
    def set_inventory_search_term(self, value: str):
        self.inventory_search_term = value or ""

    @rx.event
    def open_edit_product(self, product: Product):
        if not self.current_user["privileges"]["edit_inventario"]:
            return rx.toast("No tiene permisos para editar el inventario.", duration=3000)
        # Convert model to dict for editing
        self.editing_product = {
            "id": product.id,
            "barcode": product.barcode,
            "description": product.description,
            "category": product.category,
            "stock": product.stock,
            "unit": product.unit,
            "purchase_price": product.purchase_price,
            "sale_price": product.sale_price,
        }
        self.is_editing_product = True

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
        
        product_data = self.editing_product
        product_id = product_data.get("id")
        barcode = product_data.get("barcode", "").strip()
        description = product_data.get("description", "").strip()
        
        if not description:
             return rx.toast("La descripción no puede estar vacía.", duration=3000)
        if not barcode:
             return rx.toast("El código de barras no puede estar vacío.", duration=3000)

        with rx.session() as session:
            # Check for duplicate barcode
            existing = session.exec(
                select(Product).where(Product.barcode == barcode)
            ).first()
            
            if existing and (product_id is None or existing.id != product_id):
                return rx.toast("Ya existe un producto con ese código de barras.", duration=3000)

            if product_id:
                # Update
                product = session.get(Product, product_id)
                if not product:
                    return rx.toast("Producto no encontrado.", duration=3000)
                
                product.barcode = barcode
                product.description = description
                product.category = product_data.get("category", "General")
                product.stock = product_data.get("stock", 0)
                product.unit = product_data.get("unit", "Unidad")
                product.purchase_price = product_data.get("purchase_price", 0)
                product.sale_price = product_data.get("sale_price", 0)
                
                session.add(product)
                msg = "Producto actualizado correctamente."
            else:
                # Create
                new_product = Product(
                    barcode=barcode,
                    description=description,
                    category=product_data.get("category", "General"),
                    stock=product_data.get("stock", 0),
                    unit=product_data.get("unit", "Unidad"),
                    purchase_price=product_data.get("purchase_price", 0),
                    sale_price=product_data.get("sale_price", 0),
                )
                session.add(new_product)
                msg = "Producto creado correctamente."
            
            session.commit()
            self._inventory_update_trigger += 1
            self.is_editing_product = False
            return rx.toast(msg, duration=3000)

    @rx.event
    def delete_product(self, product_id: int):
        if not self.current_user["privileges"]["edit_inventario"]:
             return rx.toast("No tiene permisos para eliminar productos.", duration=3000)
        
        with rx.session() as session:
            product = session.get(Product, product_id)
            if product:
                # Verificar si tiene historial de ventas
                has_sales = session.exec(select(SaleItem).where(SaleItem.product_id == product_id)).first()
                if has_sales:
                    return rx.toast(
                        "No se puede eliminar un producto con historial de ventas. Edítelo para desactivarlo.",
                        duration=4000
                    )
                session.delete(product)
                session.commit()
                self._inventory_update_trigger += 1
                return rx.toast("Producto eliminado.", duration=3000)
            else:
                return rx.toast("Producto no encontrado.", duration=3000)

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
        
        with rx.session() as session:
            product = session.exec(
                select(Product).where(Product.description == description)
            ).first()
            
            if product:
                self._fill_inventory_adjustment_from_product({
                    "barcode": product.barcode,
                    "description": product.description,
                    "category": product.category,
                    "stock": product.stock,
                    "unit": product.unit,
                    "purchase_price": product.purchase_price,
                    "sale_price": product.sale_price,
                })
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
        
        with rx.session() as session:
            product = session.exec(select(Product).where(Product.barcode == description)).first()
            if not product:
                return rx.toast("Producto no encontrado en el inventario.", duration=3000)
            
            quantity = self.inventory_adjustment_item["adjust_quantity"]
            if quantity <= 0:
                return rx.toast("Ingrese la cantidad a ajustar.", duration=3000)
            
            available = product.stock
            if quantity > available:
                return rx.toast(
                    "La cantidad supera el stock disponible.", duration=3000
                )
            
            item_copy = self.inventory_adjustment_item.copy()
            item_copy["temp_id"] = str(uuid.uuid4())
            item_copy["adjust_quantity"] = self._normalize_quantity_value(
                item_copy.get("adjust_quantity", 0), item_copy.get("unit", "")
            )
            # Ensure unit is set from product if missing
            if not item_copy.get("unit"):
                item_copy["unit"] = product.unit
                
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
        
        if status == "perfecto":
            rx.toast("Inventario verificado como perfecto.", duration=3000)
        else:
            if not self.inventory_adjustment_items:
                return rx.toast(
                    "Agregue los productos que requieren re ajuste.", duration=3000
                )
            
            recorded = False
            with rx.session() as session:
                for item in self.inventory_adjustment_items:
                    description = item["description"].strip()
                    if not description:
                        continue
                    
                    product = session.exec(select(Product).where(Product.barcode == description)).first()
                    if not product:
                        continue
                    
                    quantity = item.get("adjust_quantity", 0) or 0
                    if quantity <= 0:
                        continue
                    
                    available = product.stock
                    qty = min(quantity, available)
                    
                    # Update stock
                    product.stock = max(available - qty, 0)
                    session.add(product)
                    
                    # Create StockMovement
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
                        timestamp=datetime.datetime.now()
                    )
                    session.add(movement)
                    recorded = True
                
                if recorded:
                    session.commit()
                    self._inventory_update_trigger += 1
                else:
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
        
        with rx.session() as session:
            products = session.exec(select(Product).order_by(Product.description)).all()
        
        rows = []
        for product in products:
            barcode = product.barcode
            description = product.description
            category = product.category
            unit = product.unit
            stock = product.stock
            purchase_price = product.purchase_price
            sale_price = product.sale_price
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
