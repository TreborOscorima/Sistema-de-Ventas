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
from sqlmodel import select
from sqlalchemy import or_, func
from app.models import Product, StockMovement, User as UserModel, Category, SaleItem
from .types import InventoryAdjustment
from .mixin_state import MixinState
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
        if not self.current_user["privileges"]["edit_inventario"]:
            return rx.toast(
                "No tiene permisos para editar categorias.", duration=3000
            )
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
        if not self.current_user["privileges"]["edit_inventario"]:
            return rx.toast(
                "No tiene permisos para editar categorias.", duration=3000
            )
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
                    search = f"%{search_term}%"
                    products = session.exec(
                        select(Product)
                        .where(
                            or_(
                                Product.description.ilike(search),
                                Product.barcode.ilike(search),
                            )
                        )
                        .limit(10)
                    ).all()
                    self.inventory_adjustment_suggestions = [
                        p.description for p in products
                    ]
            else:
                self.inventory_adjustment_suggestions = []

    @rx.var
    def inventory_list(self) -> list[Product]:
        # Usar trigger para forzar recálculo
        _ = self._inventory_update_trigger
        if not self.current_user["privileges"]["view_inventario"]:
            return []

        search = (self.inventory_search_term or "").strip().lower()

        with rx.session() as session:
            if search:
                query = select(Product).where(
                    or_(
                        Product.description.ilike(f"%{search}%"),
                        Product.barcode.ilike(f"%{search}%"),
                        Product.category.ilike(f"%{search}%"),
                    )
                )
            else:
                query = select(Product).order_by(Product.id.desc()).limit(self.inventory_recent_limit)
            products = session.exec(query).all()
            return sorted(products, key=lambda p: p.description)

    @rx.var
    def inventory_total_pages(self) -> int:
        total_items = len(self.inventory_list)
        if total_items == 0:
            return 1
        return (total_items + self.inventory_items_per_page - 1) // self.inventory_items_per_page

    @rx.var
    def inventory_display_page(self) -> int:
        if self.inventory_current_page < 1:
            return 1
        if self.inventory_current_page > self.inventory_total_pages:
            return self.inventory_total_pages
        return self.inventory_current_page

    @rx.var
    def inventory_paginated_list(self) -> list[Product]:
        start_index = (self.inventory_display_page - 1) * self.inventory_items_per_page
        end_index = start_index + self.inventory_items_per_page
        return self.inventory_list[start_index:end_index]

    @rx.event
    def set_inventory_search_term(self, value: str):
        self.inventory_search_term = value or ""
        self.inventory_current_page = 1

    @rx.event
    def set_inventory_page(self, page_num: int):
        if 1 <= page_num <= self.inventory_total_pages:
            self.inventory_current_page = page_num

    @rx.event
    def open_edit_product(self, product: Product):
        if not self.current_user["privileges"]["edit_inventario"]:
            return rx.toast("No tiene permisos para editar el inventario.", duration=3000)
        # Convertir modelo a dict para edicion
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
            # Verificar codigo de barras duplicado
            existing = session.exec(
                select(Product).where(Product.barcode == barcode)
            ).first()
            
            if existing and (product_id is None or existing.id != product_id):
                return rx.toast("Ya existe un producto con ese código de barras.", duration=3000)

            if product_id:
                # Actualizar
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
                # Crear
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

    def _find_adjustment_product(
        self, session, barcode: str, description: str
    ) -> Product | None:
        if barcode:
            product = session.exec(
                select(Product).where(Product.barcode == barcode)
            ).first()
            if product:
                return product
        if description:
            return session.exec(
                select(Product).where(Product.description == description)
            ).first()
        return None

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
        barcode = (self.inventory_adjustment_item.get("barcode") or "").strip()
        if not description and not barcode:
            return rx.toast("Seleccione un producto para ajustar.", duration=3000)
        
        with rx.session() as session:
            if description and not barcode:
                duplicate_count = session.exec(
                    select(func.count(Product.id)).where(
                        Product.description == description
                    )
                ).one()
                if duplicate_count and duplicate_count > 1:
                    return rx.toast(
                        "Descripcion duplicada en inventario. Use codigo de barras.",
                        duration=3000,
                    )
            product = self._find_adjustment_product(session, barcode, description)
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
            # Asegurar que la unidad se tome del producto si falta
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
                    description = (item.get("description") or "").strip()
                    barcode = (item.get("barcode") or "").strip()
                    if not description and not barcode:
                        continue
                    
                    product = self._find_adjustment_product(
                        session, barcode, description
                    )
                    if not product:
                        continue
                    
                    quantity = item.get("adjust_quantity", 0) or 0
                    if quantity <= 0:
                        continue
                    
                    available = product.stock
                    qty = min(quantity, available)
                    
                    # Actualizar stock
                    product.stock = max(available - qty, 0)
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
            "Costo Unitario (S/)",
            "Precio Venta (S/)",
            "Margen Unitario (S/)",
            "Margen (%)",
            "Valor al Costo (S/)",
            "Valor a Venta (S/)",
            "Estado Stock",
        ]
        style_header_row(ws, row, headers)
        data_start = row + 1
        row += 1
        
        with rx.session() as session:
            products = session.exec(select(Product).order_by(Product.description)).all()
        
        for product in products:
            barcode = product.barcode or "S/C"
            description = product.description or "Sin descripción"
            category = product.category or "Sin categoría"
            unit = product.unit or "Unid."
            stock = product.stock or 0
            purchase_price = float(product.purchase_price or 0)
            sale_price = float(product.sale_price or 0)
            
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
            ws.cell(row=row, column=6, value=purchase_price).number_format = CURRENCY_FORMAT
            ws.cell(row=row, column=7, value=sale_price).number_format = CURRENCY_FORMAT
            # Margen Unitario = Fórmula: Precio - Costo
            ws.cell(row=row, column=8, value=f"=G{row}-F{row}").number_format = CURRENCY_FORMAT
            # Margen % = Fórmula: (Margen / Costo) si Costo > 0
            ws.cell(row=row, column=9, value=f"=IF(F{row}>0,H{row}/F{row},0)").number_format = PERCENT_FORMAT
            # Valor al Costo = Fórmula: Stock × Costo
            ws.cell(row=row, column=10, value=f"=D{row}*F{row}").number_format = CURRENCY_FORMAT
            # Valor a Venta = Fórmula: Stock × Precio
            ws.cell(row=row, column=11, value=f"=D{row}*G{row}").number_format = CURRENCY_FORMAT
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
            {"type": "sum", "col_letter": "J", "number_format": CURRENCY_FORMAT},
            {"type": "sum", "col_letter": "K", "number_format": CURRENCY_FORMAT},
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
