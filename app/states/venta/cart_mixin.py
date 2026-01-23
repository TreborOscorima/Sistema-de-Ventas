import logging
import uuid
from typing import Any, Dict, List, Union

import reflex as rx
from sqlmodel import select

from app.models import FieldReservation, Product
from app.utils.barcode import clean_barcode, validate_barcode
from ..types import TransactionItem


class CartMixin:
    new_sale_item: Dict[str, Any] = {
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
    new_sale_items: List[Dict[str, Any]] = []
    autocomplete_suggestions: List[str] = []

    @rx.event
    def handle_key_down(self, key: str):
        if key == "Enter":
            return self.add_item_to_sale()

    @rx.var
    def sale_subtotal(self) -> float:
        return self.new_sale_item["subtotal"]

    @rx.var
    def sale_total(self) -> float:
        reservation_balance = 0.0
        if hasattr(self, "reservation_payment_id") and self.reservation_payment_id:
            # Traer reserva desde BD
            with rx.session() as session:
                # Correccion: manejar UUIDs string correctamente
                reservation = session.exec(
                    select(FieldReservation).where(
                        FieldReservation.id == self.reservation_payment_id
                    )
                ).first()

                if reservation:
                    reservation_balance = self._round_currency(
                        reservation.total_amount - reservation.paid_amount
                    )
                    if reservation_balance < 0:
                        reservation_balance = 0.0

        # Alternativa: si no se encontro en BD (ej. UUID en memoria), usar el estado de Servicios
        if reservation_balance == 0 and hasattr(self, "selected_reservation_balance"):
            reservation_balance = self.selected_reservation_balance

        products_total = sum((item["subtotal"] for item in self.new_sale_items))
        return self._round_currency(products_total + reservation_balance)

    def _apply_item_rounding(self, item: TransactionItem):
        unit = item.get("unit", "")
        item["quantity"] = self._normalize_quantity_value(item.get("quantity", 0), unit)
        item["price"] = self._round_currency(item.get("price", 0))
        if "sale_price" in item:
            item["sale_price"] = self._round_currency(item.get("sale_price", 0))
        item["subtotal"] = self._round_currency(item["quantity"] * item["price"])

    def _fill_sale_item_from_product(self, product: Product, keep_quantity: bool = False):
        product_barcode = product.barcode

        quantity = (
            self.new_sale_item["quantity"]
            if keep_quantity and self.new_sale_item["quantity"] > 0
            else 1
        )

        self.new_sale_item["product_id"] = product.id
        self.new_sale_item["barcode"] = product_barcode
        self.new_sale_item["description"] = product.description
        self.new_sale_item["category"] = product.category
        self.new_sale_item["unit"] = product.unit
        self.new_sale_item["quantity"] = self._normalize_quantity_value(
            quantity, product.unit
        )
        self.new_sale_item["price"] = self._round_currency(product.sale_price)
        self.new_sale_item["sale_price"] = self._round_currency(product.sale_price)
        self.new_sale_item["subtotal"] = self._round_currency(
            self.new_sale_item["quantity"] * self.new_sale_item["price"]
        )

        if not keep_quantity:
            self.autocomplete_suggestions = []

        logging.info(
            f"[FILL-SALE] C▃igo corregido: escaneado incompleto  '{product_barcode}' completo (producto: {product.description})"
        )

    def _reset_sale_form(self):
        self.sale_form_key += 1
        self.new_sale_item = {
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
        self.autocomplete_suggestions = []

    @rx.event
    def handle_sale_change(self, field: str, value: Union[str, float]):
        try:
            if field in ["quantity", "price"]:
                numeric = float(value) if value else 0
                if field == "quantity":
                    self.new_sale_item[field] = self._normalize_quantity_value(
                        numeric, self.new_sale_item.get("unit", "")
                    )
                else:
                    self.new_sale_item[field] = self._round_currency(numeric)
            else:
                self.new_sale_item[field] = value
                if field == "unit":
                    self.new_sale_item["quantity"] = self._normalize_quantity_value(
                        self.new_sale_item["quantity"], value
                    )
            self.new_sale_item["subtotal"] = self._round_currency(
                self.new_sale_item["quantity"] * self.new_sale_item["price"]
            )
            if field == "description":
                if value and len(str(value)) > 1:
                    with rx.session() as session:
                        search = str(value).lower()
                        # Filtrado simple en Python sobre un conjunto limitado o SQL LIKE
                        # Para mejor rendimiento usar SQL LIKE
                        products = session.exec(
                            select(Product)
                            .where(Product.description.ilike(f"%{search}%"))
                            .limit(5)
                        ).all()
                        self.autocomplete_suggestions = [p.description for p in products]
                else:
                    self.autocomplete_suggestions = []
            elif field == "barcode":
                if not value or not str(value).strip():
                    self.new_sale_item["barcode"] = ""
                    self.new_sale_item["description"] = ""
                    self.new_sale_item["quantity"] = 0
                    self.new_sale_item["price"] = 0
                    self.new_sale_item["subtotal"] = 0
                    self.autocomplete_suggestions = []
                else:
                    code = clean_barcode(str(value))
                    if validate_barcode(code):
                        with rx.session() as session:
                            product = session.exec(
                                select(Product).where(Product.barcode == code)
                            ).first()
                            if product:
                                self._fill_sale_item_from_product(
                                    product, keep_quantity=False
                                )
                                self.autocomplete_suggestions = []
                                return
        except ValueError as e:
            logging.exception(f"Error parsing sale value: {e}")

    @rx.event
    def process_sale_barcode_from_input(self, barcode_value):
        self.new_sale_item["barcode"] = str(barcode_value) if barcode_value else ""

        if not barcode_value or not str(barcode_value).strip():
            self.new_sale_item["description"] = ""
            self.new_sale_item["quantity"] = 0
            self.new_sale_item["price"] = 0
            self.new_sale_item["subtotal"] = 0
            self.autocomplete_suggestions = []
            return

        code = clean_barcode(str(barcode_value))
        if validate_barcode(code):
            with rx.session() as session:
                product = session.exec(
                    select(Product).where(Product.barcode == code)
                ).first()
                if product:
                    self._fill_sale_item_from_product(product, keep_quantity=False)
                    self.autocomplete_suggestions = []
                    return

    @rx.event
    def select_product_for_sale(self, description: str):
        if isinstance(description, dict):
            description = (
                description.get("value")
                or description.get("description")
                or description.get("label")
                or ""
            )
        desc = description.strip()
        if desc:
            with rx.session() as session:
                product = session.exec(
                    select(Product).where(Product.description == desc)
                ).first()
                if product:
                    self._fill_sale_item_from_product(product)
        self.autocomplete_suggestions = []

    @rx.event
    def add_item_to_sale(self):
        if not self.current_user["privileges"]["create_ventas"]:
            return rx.toast("No tiene permisos para crear ventas.", duration=3000)
        self.sale_receipt_ready = False
        if (
            not self.new_sale_item["description"]
            or self.new_sale_item["quantity"] <= 0
            or self.new_sale_item["price"] <= 0
        ):
            return rx.toast(
                "Por favor, busque un producto y complete los campos.", duration=3000
            )

        description = self.new_sale_item["description"].strip()
        barcode = str(self.new_sale_item.get("barcode", "") or "").strip()

        existing_index = None
        existing_item = None
        for idx, item in enumerate(self.new_sale_items):
            item_barcode = str(item.get("barcode", "") or "").strip()
            item_description = str(item.get("description", "") or "").strip()
            if barcode and item_barcode == barcode:
                existing_index = idx
                existing_item = item
                break
            if item_description == description:
                existing_index = idx
                existing_item = item
                break

        existing_qty = float(existing_item["quantity"]) if existing_item else 0.0
        new_qty = float(self.new_sale_item["quantity"])
        total_qty = existing_qty + new_qty
        with rx.session() as session:
            if barcode:
                product = session.exec(
                    select(Product).where(Product.barcode == barcode)
                ).first()
            else:
                product = session.exec(
                    select(Product).where(Product.description == description)
                ).first()

            if not product:
                return rx.toast(
                    "Producto no encontrado en el inventario.", duration=3000
                )
            if product.stock < total_qty:
                remaining = max(product.stock - existing_qty, 0)
                unit = product.unit or self.new_sale_item.get("unit", "")
                in_cart_display = self._normalize_quantity_value(existing_qty, unit)
                remaining_display = self._normalize_quantity_value(remaining, unit)
                return rx.toast(
                    f"Stock insuficiente: ya tienes {in_cart_display} en el carrito y solo quedan {remaining_display} disponibles.",
                    duration=3000,
                )

        if existing_item is not None:
            updated_item = existing_item.copy()
            unit = updated_item.get("unit", "")
            updated_item["quantity"] = self._normalize_quantity_value(
                existing_qty + new_qty, unit
            )
            updated_item["subtotal"] = self._round_currency(
                updated_item["quantity"] * updated_item["price"]
            )
            items = list(self.new_sale_items)
            items[existing_index] = updated_item
            self.new_sale_items = items
            self._reset_sale_form()
            self._refresh_payment_feedback()
            return [
                rx.toast(
                    f"Cantidad actualizada a {updated_item['quantity']}",
                    duration=2000,
                ),
                rx.call_script(
                    "setTimeout(() => { const el = document.getElementById('venta_barcode_input'); if (el) { el.focus(); el.select(); } }, 0);"
                ),
            ]

        item_copy = self.new_sale_item.copy()
        item_copy["temp_id"] = str(uuid.uuid4())
        self._apply_item_rounding(item_copy)
        self.new_sale_items.append(item_copy)
        self._reset_sale_form()
        self._refresh_payment_feedback()
        return [
            rx.toast(
                f"Producto '{item_copy['description']}' agregado",
                duration=2000,
            ),
            rx.call_script(
                "setTimeout(() => { const el = document.getElementById('venta_barcode_input'); if (el) { el.focus(); el.select(); } }, 0);"
            ),
        ]

    @rx.event
    def remove_item_from_sale(self, temp_id: str):
        self.new_sale_items = [
            item for item in self.new_sale_items if item["temp_id"] != temp_id
        ]
        self.sale_receipt_ready = False
        self._refresh_payment_feedback()
        self.sale_receipt_ready = False

    @rx.event
    def clear_sale_items(self):
        self.new_sale_items = []
        self._reset_sale_form()
        self.sale_receipt_ready = False
        self._refresh_payment_feedback()
