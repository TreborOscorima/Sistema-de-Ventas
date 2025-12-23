import reflex as rx
from typing import List, Dict, Any, Union, Optional
import datetime
import uuid
import logging
import json
from sqlmodel import select
from app.models import Product, Sale, SaleItem, User, FieldReservation, PaymentMethod
from .types import TransactionItem, PaymentMethodConfig, Movement, CashboxSale, PaymentBreakdownItem
from app.utils.barcode import clean_barcode, validate_barcode
from .mixin_state import MixinState

class VentaState(MixinState):
    sale_form_key: int = 0
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
    }
    new_sale_items: List[Dict[str, Any]] = []
    autocomplete_suggestions: List[str] = []
    last_sale_receipt: List[Dict[str, Any]] = []
    last_sale_total: float = 0
    last_sale_timestamp: str = ""
    sale_receipt_ready: bool = False
    last_sale_reservation_context: Dict | None = None
    
    @rx.var
    def payment_methods(self) -> List[PaymentMethodConfig]:
        with rx.session() as session:
            methods = session.exec(select(PaymentMethod)).all()
            if not methods:
                return []
            return [
                {
                    "id": m.method_id,
                    "name": m.name,
                    "description": m.description,
                    "kind": m.kind,
                    "enabled": m.enabled
                }
                for m in methods
            ]

    payment_method: str = "Efectivo"
    payment_method_description: str = "Billetes, Monedas"
    payment_method_kind: str = "cash"
    payment_cash_amount: float = 0
    payment_cash_message: str = ""
    payment_cash_status: str = "neutral"
    payment_card_type: str = "Credito"
    payment_wallet_choice: str = "Yape"
    payment_wallet_provider: str = "Yape"
    payment_mixed_cash: float = 0
    payment_mixed_card: float = 0
    payment_mixed_wallet: float = 0
    payment_mixed_non_cash_kind: str = "card"
    payment_mixed_message: str = ""
    payment_mixed_status: str = "neutral"
    payment_mixed_notes: str = ""
    last_payment_summary: str = ""
    new_payment_method_name: str = ""
    new_payment_method_description: str = ""
    new_payment_method_kind: str = "other"

    @rx.var
    def sale_subtotal(self) -> float:
        return self.new_sale_item["subtotal"]

    @rx.var
    def sale_total(self) -> float:
        reservation_balance = 0.0
        if hasattr(self, "reservation_payment_id") and self.reservation_payment_id:
            # Fetch reservation from DB
            with rx.session() as session:
                # Fix: Handle string UUIDs correctly
                reservation = session.exec(
                    select(FieldReservation).where(FieldReservation.id == self.reservation_payment_id)
                ).first()
                
                if reservation:
                    reservation_balance = max(reservation.total_amount - reservation.paid_amount, 0)
        
        # Fallback: Si no se encontro en DB (ej. es UUID en memoria), usar el estado de Servicios
        if reservation_balance == 0 and hasattr(self, "selected_reservation_balance"):
            reservation_balance = self.selected_reservation_balance
        
        products_total = sum((item["subtotal"] for item in self.new_sale_items))
        return self._round_currency(products_total + reservation_balance)

    @rx.var
    def enabled_payment_methods(self) -> list[PaymentMethodConfig]:
        return [m for m in self.payment_methods if m.get("enabled", True)]

    @rx.var
    def payment_summary(self) -> str:
        return self._generate_payment_summary()

    @rx.var
    def payment_mixed_complement(self) -> float:
        total = self._mixed_effective_total()
        paid_cash = self._round_currency(self.payment_mixed_cash)
        remaining = max(total - paid_cash, 0)
        return self._round_currency(remaining)

    def _payment_method_by_identifier(self, identifier: str) -> PaymentMethodConfig | None:
        target = (identifier or "").strip().lower()
        if not target:
            return None
        for method in self.payment_methods:
            if method["id"].lower() == target or method["name"].lower() == target:
                return method
        return None

    def _enabled_payment_methods_list(self) -> list[PaymentMethodConfig]:
        return [m for m in self.payment_methods if m.get("enabled", True)]

    def _default_payment_method(self) -> PaymentMethodConfig | None:
        enabled = self._enabled_payment_methods_list()
        if enabled:
            return enabled[0]
        return None

    def _ensure_payment_method_selected(self):
        available = self._enabled_payment_methods_list()
        if not available:
            self.payment_method = ""
            self.payment_method_description = ""
            self.payment_method_kind = "other"
            return
        if not any(m["name"] == self.payment_method for m in available):
            self._set_payment_method(available[0])

    @rx.event
    def set_new_payment_method_name(self, value: str):
        self.new_payment_method_name = value

    @rx.event
    def set_new_payment_method_description(self, value: str):
        self.new_payment_method_description = value

    @rx.event
    def set_new_payment_method_kind(self, value: str):
        self.new_payment_method_kind = (value or "").strip().lower() or "other"

    @rx.event
    def add_payment_method(self):
        if not self.current_user["privileges"]["manage_config"]:
            return rx.toast("No tiene permisos para configurar el sistema.", duration=3000)
        name = (self.new_payment_method_name or "").strip()
        description = (self.new_payment_method_description or "").strip()
        kind = (self.new_payment_method_kind or "other").strip().lower()
        if not name:
            return rx.toast("Asigne un nombre al metodo de pago.", duration=3000)
        if kind not in ["cash", "card", "wallet", "mixed", "other"]:
            kind = "other"
        if any(m["name"].lower() == name.lower() for m in self.payment_methods):
            return rx.toast("Ya existe un metodo con ese nombre.", duration=3000)
        method: PaymentMethodConfig = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description or "Sin descripcion",
            "kind": kind,
            "enabled": True,
        }
        self.payment_methods.append(method)
        self.new_payment_method_name = ""
        self.new_payment_method_description = ""
        self.new_payment_method_kind = "other"
        self._set_payment_method(method)
        return rx.toast(f"Metodo {name} agregado.", duration=2500)

    @rx.event
    def toggle_payment_method_enabled(self, method_id: str, enabled: bool | str):
        if not self.current_user["privileges"]["manage_config"]:
            return rx.toast("No tiene permisos para configurar el sistema.", duration=3000)
        if isinstance(enabled, str):
            enabled = enabled.lower() in ["true", "1", "on", "yes"]
        active_methods = self._enabled_payment_methods_list()
        for method in self.payment_methods:
            if method["id"] == method_id:
                if not enabled and method.get("enabled", True) and len(active_methods) <= 1:
                    return rx.toast("Debe haber al menos un metodo activo.", duration=3000)
                method["enabled"] = enabled
                break
        self._ensure_payment_method_selected()

    @rx.event
    def remove_payment_method(self, method_id: str):
        method = self._payment_method_by_identifier(method_id)
        if not method:
            return
        remaining_enabled = [
            m for m in self._enabled_payment_methods_list() if m["id"] != method_id
        ]
        if not remaining_enabled:
            return rx.toast("No puedes eliminar el unico metodo activo.", duration=3000)
        self.payment_methods = [m for m in self.payment_methods if m["id"] != method_id]
        self._ensure_payment_method_selected()
        return rx.toast(f"Metodo {method['name']} eliminado.", duration=2500)

    def _generate_payment_summary(self) -> str:
        method = self.payment_method or "No especificado"
        kind = (self.payment_method_kind or "other").lower()
        if kind == "cash":
            detail = f"Monto {self._format_currency(self.payment_cash_amount)}"
            if self.payment_cash_message:
                detail += f" ({self.payment_cash_message})"
            return f"{method} - {detail}"
        if kind == "card":
            return f"{method} - {self.payment_card_type}"
        if kind == "wallet":
            provider = (
                self.payment_wallet_provider
                or self.payment_wallet_choice
                or "Proveedor no especificado"
            )
            return f"{method} - {provider}"
        if kind == "mixed":
            parts = []
            if self.payment_mixed_cash > 0:
                parts.append(f"Efectivo {self._format_currency(self.payment_mixed_cash)}")
            if self.payment_mixed_card > 0:
                parts.append(
                    f"Tarjeta ({self.payment_card_type}) {self._format_currency(self.payment_mixed_card)}"
                )
            if self.payment_mixed_wallet > 0:
                provider = (
                    self.payment_wallet_provider
                    or self.payment_wallet_choice
                    or "Billetera"
                )
                parts.append(f"{provider} {self._format_currency(self.payment_mixed_wallet)}")
            if self.payment_mixed_notes:
                parts.append(self.payment_mixed_notes)
            if not parts:
                parts.append("Sin detalle")
            if self.payment_mixed_message:
                parts.append(self.payment_mixed_message)
            return f"{method} - {' / '.join(parts)}"
        return f"{method} - {self.payment_method_description}"

    def _safe_amount(self, value: str) -> float:
        try:
            amount = float(value) if value else 0
        except ValueError:
            amount = 0
        return self._round_currency(amount)

    def _update_cash_feedback(self, total_override: float | None = None):
        effective_total = 0
        if total_override is not None:
            effective_total = total_override
        else:
            # Accessing selected_reservation_balance from ServicesState (via RootState)
            res_balance = 0
            if hasattr(self, "selected_reservation_balance"):
                res_balance = self.selected_reservation_balance
            effective_total = self.sale_total if self.sale_total > 0 else res_balance

        amount = self.payment_cash_amount
        diff = amount - effective_total
        if amount <= 0:
            self.payment_cash_message = "Ingrese un monto valido."
            self.payment_cash_status = "warning"
        elif diff > 0:
            self.payment_cash_message = f"Vuelto {self._format_currency(diff)}"
            self.payment_cash_status = "change"
        elif diff < 0:
            self.payment_cash_message = f"Faltan {self._format_currency(abs(diff))}"
            self.payment_cash_status = "due"
        else:
            self.payment_cash_message = "Monto exacto."
            self.payment_cash_status = "exact"

    def _mixed_effective_total(self, total_override: float | None = None) -> float:
        if total_override is not None:
            total = total_override
        else:
            res_balance = 0
            if hasattr(self, "selected_reservation_balance"):
                res_balance = self.selected_reservation_balance
            total = self.sale_total if self.sale_total > 0 else res_balance
        return self._round_currency(total)

    def _auto_allocate_mixed_amounts(self, total_override: float | None = None):
        total = self._mixed_effective_total(total_override)
        paid_cash = self._round_currency(self.payment_mixed_cash)
        remaining = self._round_currency(max(total - paid_cash, 0))
        if self.payment_mixed_non_cash_kind == "wallet":
            self.payment_mixed_wallet = remaining
            self.payment_mixed_card = 0
        else:
            self.payment_mixed_card = remaining
            self.payment_mixed_wallet = 0

    def _update_mixed_message(self, total_override: float | None = None):
        total = self._mixed_effective_total(total_override)
        paid_cash = self._round_currency(self.payment_mixed_cash)
        paid_card = self._round_currency(self.payment_mixed_card)
        paid_wallet = self._round_currency(self.payment_mixed_wallet)
        
        total_paid = self._round_currency(paid_cash + paid_card + paid_wallet)
        
        if total_paid <= 0:
            self.payment_mixed_message = "Ingrese montos para los metodos seleccionados."
            self.payment_mixed_status = "warning"
            return
            
        diff = self._round_currency(total - total_paid)
        
        if diff > 0:
            self.payment_mixed_message = f"Restan {self._format_currency(diff)}"
            self.payment_mixed_status = "due"
            return
            
        change = abs(diff)
        
        if change > 0:
            self.payment_mixed_message = f"Vuelto {self._format_currency(change)}"
            self.payment_mixed_status = "change"
        else:
            complemento = self._round_currency(paid_card + paid_wallet)
            if complemento > 0 and paid_cash < total:
                self.payment_mixed_message = f"Complemento {self._format_currency(complemento)}"
            else:
                self.payment_mixed_message = "Montos completos."
            self.payment_mixed_status = "exact"

    def _refresh_payment_feedback(self, total_override: float | None = None):
        if self.payment_method_kind == "cash":
            self._update_cash_feedback(total_override=total_override)
        elif self.payment_method_kind == "mixed":
            self._auto_allocate_mixed_amounts(total_override=total_override)
            self._update_mixed_message(total_override=total_override)
        else:
            self.payment_cash_message = ""
            self.payment_mixed_message = ""

    def _set_payment_method(self, method: PaymentMethodConfig | None):
        if method:
            self.payment_method = method.get("name", "")
            self.payment_method_description = method.get("description", "")
            self.payment_method_kind = (method.get("kind", "other") or "other").lower()
        else:
            self.payment_method = ""
            self.payment_method_description = ""
            self.payment_method_kind = "other"
        self.payment_cash_amount = 0
        self.payment_cash_message = ""
        self.payment_cash_status = "neutral"
        self.payment_card_type = "Credito"
        self.payment_wallet_choice = "Yape"
        self.payment_wallet_provider = "Yape"
        self.payment_mixed_cash = 0
        self.payment_mixed_card = 0
        self.payment_mixed_wallet = 0
        self.payment_mixed_non_cash_kind = "card"
        self.payment_mixed_message = ""
        self.payment_mixed_status = "neutral"
        self.payment_mixed_notes = ""
        self._refresh_payment_feedback()

    def _reset_payment_fields(self):
        default_method = self._default_payment_method()
        self._set_payment_method(default_method)

    @rx.event
    def select_payment_method(self, method: str, description: str = ""):
        match = self._payment_method_by_identifier(method)
        if not match:
            return rx.toast("Metodo de pago no disponible.", duration=3000)
        if not match.get("enabled", True):
            return rx.toast("Este metodo esta inactivo.", duration=3000)
        self._set_payment_method(match)

    @rx.event
    def set_cash_amount(self, value: str):
        try:
            amount = float(value) if value else 0
        except ValueError:
            amount = 0
        self.payment_cash_amount = self._round_currency(amount)
        self._update_cash_feedback()

    @rx.event
    def set_card_type(self, card_type: str):
        self.payment_card_type = card_type
        if self.payment_method_kind == "mixed" and self.payment_mixed_non_cash_kind == "card":
            self._auto_allocate_mixed_amounts()
            self._update_mixed_message()

    @rx.event
    def choose_wallet_provider(self, provider: str):
        self.payment_wallet_choice = provider
        if provider == "Otro":
            self.payment_wallet_provider = ""
        else:
            self.payment_wallet_provider = provider
        if self.payment_method_kind == "mixed" and self.payment_mixed_non_cash_kind == "wallet":
            self._auto_allocate_mixed_amounts()
            self._update_mixed_message()

    @rx.event
    def set_wallet_provider_custom(self, value: str):
        self.payment_wallet_provider = value
        self.payment_wallet_choice = "Otro"

    @rx.event
    def set_mixed_notes(self, notes: str):
        self.payment_mixed_notes = notes

    @rx.event
    def set_mixed_cash_amount(self, value: str):
        self.payment_mixed_cash = self._safe_amount(value)
        self._auto_allocate_mixed_amounts()
        self._update_mixed_message()

    @rx.event
    def set_mixed_non_cash_kind(self, kind: str):
        if kind not in ["card", "wallet"]:
            return
        self.payment_mixed_non_cash_kind = kind
        self._auto_allocate_mixed_amounts()
        self._update_mixed_message()

    @rx.event
    def set_mixed_card_amount(self, value: str):
        self.payment_mixed_card = self._safe_amount(value)
        self._update_mixed_message()

    @rx.event
    def set_mixed_wallet_amount(self, value: str):
        self.payment_mixed_wallet = self._safe_amount(value)
        self._update_mixed_message()

    def _apply_item_rounding(self, item: TransactionItem):
        unit = item.get("unit", "")
        item["quantity"] = self._normalize_quantity_value(
            item.get("quantity", 0), unit
        )
        item["price"] = self._round_currency(item.get("price", 0))
        if "sale_price" in item:
            item["sale_price"] = self._round_currency(item.get("sale_price", 0))
        item["subtotal"] = self._round_currency(item["quantity"] * item["price"])

    def _fill_sale_item_from_product(
        self, product: Product, keep_quantity: bool = False
    ):
        product_barcode = product.barcode
        
        quantity = (
            self.new_sale_item["quantity"]
            if keep_quantity and self.new_sale_item["quantity"] > 0
            else 1
        )
        
        self.new_sale_item["barcode"] = product_barcode
        self.new_sale_item["description"] = product.description
        self.new_sale_item["category"] = product.category
        self.new_sale_item["unit"] = product.unit
        self.new_sale_item["quantity"] = self._normalize_quantity_value(quantity, product.unit)
        self.new_sale_item["price"] = self._round_currency(product.sale_price)
        self.new_sale_item["sale_price"] = self._round_currency(product.sale_price)
        self.new_sale_item["subtotal"] = self._round_currency(
            self.new_sale_item["quantity"] * self.new_sale_item["price"]
        )
        
        if not keep_quantity:
            self.autocomplete_suggestions = []
        
        logging.info(f"[FILL-SALE] Código corregido: escaneado incompleto → '{product_barcode}' completo (producto: {product.description})")

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
                        # Simple python filtering on a limited set or SQL LIKE
                        # For better performance use SQL LIKE
                        products = session.exec(
                            select(Product).where(Product.description.ilike(f"%{search}%")).limit(5)
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
                                self._fill_sale_item_from_product(product, keep_quantity=False)
                                self.autocomplete_suggestions = []
                                return rx.toast(f"Producto '{product.description}' cargado", duration=2000)
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
                    return rx.toast(f"Producto '{product.description}' cargado", duration=2000)

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
        with rx.session() as session:
            product = session.exec(
                select(Product).where(Product.description == description)
            ).first()
            
            if not product:
                return rx.toast("Producto no encontrado en el inventario.", duration=3000)
            if product.stock < self.new_sale_item["quantity"]:
                return rx.toast("Stock insuficiente para realizar la venta.", duration=3000)
        
        item_copy = self.new_sale_item.copy()
        item_copy["temp_id"] = str(uuid.uuid4())
        self._apply_item_rounding(item_copy)
        self.new_sale_items.append(item_copy)
        self._reset_sale_form()
        self._refresh_payment_feedback()

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

    def _payment_label_and_breakdown(self, sale_total: float) -> tuple[str, list[PaymentBreakdownItem]]:
        kind = (self.payment_method_kind or "other").lower()
        method_name = self._normalize_wallet_label(self.payment_method or "Metodo")
        breakdown: list[PaymentBreakdownItem] = []
        label = method_name
        if kind == "cash":
            label = "Efectivo"
            breakdown = [{"label": label, "amount": self._round_currency(sale_total)}]
        elif kind == "card":
            card_type = self.payment_card_type or "Tarjeta"
            label = f"{method_name} ({card_type})"
            breakdown = [{"label": label, "amount": self._round_currency(sale_total)}]
        elif kind == "wallet":
            provider = self.payment_wallet_provider or self.payment_wallet_choice or "Billetera"
            label = f"{method_name} ({provider})"
            breakdown = [{"label": label, "amount": self._round_currency(sale_total)}]
        elif kind == "mixed":
            paid_cash = self._round_currency(self.payment_mixed_cash)
            paid_card = self._round_currency(self.payment_mixed_card)
            paid_wallet = self._round_currency(self.payment_mixed_wallet)
            provider = self.payment_wallet_provider or self.payment_wallet_choice or "Billetera"
            remaining = self._round_currency(sale_total)
            parts: list[PaymentBreakdownItem] = []
            if paid_card > 0:
                applied_card = min(paid_card, remaining)
                if applied_card > 0:
                    parts.append(
                        {
                            "label": f"Tarjeta ({self.payment_card_type})",
                            "amount": self._round_currency(applied_card),
                        }
                    )
                    remaining = self._round_currency(remaining - applied_card)
            if paid_wallet > 0 and remaining > 0:
                applied_wallet = min(paid_wallet, remaining)
                if applied_wallet > 0:
                    parts.append({"label": provider, "amount": self._round_currency(applied_wallet)})
                    remaining = self._round_currency(remaining - applied_wallet)
            if paid_cash > 0 and remaining > 0:
                applied_cash = min(paid_cash, remaining)
                if applied_cash > 0:
                    parts.append({"label": "Efectivo", "amount": self._round_currency(applied_cash)})
                    remaining = self._round_currency(remaining - applied_cash)
            if not parts:
                breakdown = [{"label": method_name, "amount": self._round_currency(sale_total)}]
            else:
                if remaining > 0:
                    parts[0]["amount"] = self._round_currency(parts[0]["amount"] + remaining)
                breakdown = parts
            labels = [p["label"] for p in breakdown]
            detail = ", ".join(labels) if labels else method_name
            label = f"{method_name} ({detail})"
        else:
            label = method_name or "Otros"
            breakdown = [{"label": label, "amount": self._round_currency(sale_total)}]
        return label, breakdown

    @rx.event
    def confirm_sale(self):
        if not self.current_user["privileges"]["create_ventas"]:
            return rx.toast("No tiene permisos para crear ventas.", duration=3000)
        
        if hasattr(self, "_require_cashbox_open"):
            denial = self._require_cashbox_open()
            if denial:
                return denial
        
        with rx.session() as session:
            reservation = None
            if hasattr(self, "reservation_payment_id") and self.reservation_payment_id:
                # Fix: Handle string UUIDs correctly
                reservation = session.exec(
                    select(FieldReservation).where(FieldReservation.id == self.reservation_payment_id)
                ).first()
            
            if reservation and reservation.status in ["cancelado", "eliminado"]:
                return rx.toast("No se puede cobrar una reserva cancelada o eliminada.", duration=3000)
            
            reservation_balance = 0
            if reservation:
                reservation_balance = self._round_currency(
                    max(reservation.total_amount - reservation.paid_amount, 0)
                )

            if not self.new_sale_items and reservation_balance <= 0:
                if reservation:
                    return rx.toast("La reserva ya esta pagada.", duration=3000)
                return rx.toast("No hay productos en la venta.", duration=3000)
            if not self.payment_method:
                return rx.toast("Seleccione un metodo de pago.", duration=3000)

            product_snapshot: list[Dict[str, Any]] = []
            for item in self.new_sale_items:
                snapshot_item = item.copy()
                self._apply_item_rounding(snapshot_item)
                product_snapshot.append(snapshot_item)
            
            # Check stock availability
            for item in product_snapshot:
                description = item["description"].strip()
                product = session.exec(
                    select(Product).where(Product.description == description)
                ).first()
                
                if not product:
                    return rx.toast(f"Producto {item['description']} no encontrado en inventario.", duration=3000)
                if product.stock < item["quantity"]:
                    return rx.toast(f"Stock insuficiente para {item['description']}.", duration=3000)

            sale_total = self._round_currency(sum(item["subtotal"] for item in product_snapshot) + reservation_balance)
            if sale_total <= 0:
                return rx.toast("No hay importe para cobrar.", duration=3000)

            self._refresh_payment_feedback(total_override=sale_total)
            if self.payment_method_kind == "cash":
                if self.payment_cash_status not in ["exact", "change"]:
                    message = (
                        self.payment_cash_message or "Ingrese un monto valido en efectivo."
                    )
                    return rx.toast(message, duration=3000)
            if self.payment_method_kind == "mixed":
                if self.payment_mixed_status not in ["exact", "change"]:
                    message = (
                        self.payment_mixed_message
                        or "Complete los montos del pago mixto."
                    )
                    return rx.toast(message, duration=3000)
            
            timestamp = datetime.datetime.now()
            payment_summary = self._generate_payment_summary()
            payment_label, payment_breakdown = self._payment_label_and_breakdown(sale_total)
            
            # Create Sale
            user_id = None
            user_obj = session.exec(select(User).where(User.username == self.current_user["username"])).first()
            if user_obj:
                user_id = user_obj.id

            new_sale = Sale(
                timestamp=timestamp,
                total_amount=sale_total,
                payment_method=self.payment_method,
                payment_details=payment_summary, # Storing summary string for now
                user_id=user_id,
                is_deleted=False
            )
            session.add(new_sale)
            session.flush() # Get ID

            # Process Products
            for item in product_snapshot:
                description = item["description"].strip()
                product = session.exec(
                    select(Product).where(Product.description == description)
                ).first()
                
                # Update stock
                new_stock = max(product.stock - item["quantity"], 0)
                product.stock = self._normalize_quantity_value(new_stock, product.unit)
                session.add(product)
                
                # Create SaleItem
                sale_item = SaleItem(
                    sale_id=new_sale.id,
                    product_id=product.id,
                    quantity=item["quantity"],
                    unit_price=item["price"],
                    subtotal=item["subtotal"],
                    product_name_snapshot=product.description,
                    product_barcode_snapshot=product.barcode
                )
                session.add(sale_item)

            # Process Reservation Payment
            if reservation_balance > 0:
                applied_amount = reservation_balance
                paid_before = reservation.paid_amount
                reservation.paid_amount = self._round_currency(reservation.paid_amount + applied_amount)
                
                if reservation.paid_amount >= reservation.total_amount:
                    reservation.status = "pagado"
                
                session.add(reservation)
                
                # Create SaleItem for reservation (no product_id)
                res_item = SaleItem(
                    sale_id=new_sale.id,
                    product_id=None,
                    quantity=1,
                    unit_price=applied_amount,
                    subtotal=applied_amount,
                    product_name_snapshot=f"Alquiler {reservation.field_name} ({reservation.start_datetime} - {reservation.end_datetime})",
                    product_barcode_snapshot=str(reservation.id)
                )
                session.add(res_item)
                
                balance_after = max(reservation.total_amount - reservation.paid_amount, 0)
                self.last_sale_reservation_context = {
                    "total": reservation.total_amount,
                    "paid_before": paid_before,
                    "paid_now": applied_amount,
                    "paid_after": reservation.paid_amount,
                    "balance_after": balance_after,
                    "header": f"Alquiler {reservation.field_name} ({reservation.start_datetime} - {reservation.end_datetime})",
                    "products_total": self._round_currency(sum(item["subtotal"] for item in product_snapshot)),
                    "charged_total": sale_total,
                }
            else:
                self.last_sale_reservation_context = None
            
            session.commit()
            
            # Prepare receipt data (in memory for display)
            self.last_sale_receipt = product_snapshot
            if reservation_balance > 0:
                 self.last_sale_receipt.insert(0, {
                    "description": f"Alquiler {reservation.field_name}",
                    "quantity": 1,
                    "unit": "Servicio",
                    "price": reservation_balance,
                    "subtotal": reservation_balance
                 })

            self.last_sale_total = sale_total
            self.last_sale_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            self.last_payment_summary = payment_summary
            self.sale_receipt_ready = True
            self.new_sale_items = []
            self._reset_sale_form()
            self._reset_payment_fields()
            self._refresh_payment_feedback()
            
            # Trigger updates in other states
            if hasattr(self, "reload_history"):
                self.reload_history()
            if hasattr(self, "_cashbox_update_trigger"):
                self._cashbox_update_trigger += 1

            return rx.toast("Venta confirmada.", duration=3000)

    def _print_receipt_logic(self, receipt_id: str | None = None):
        # Determine data source
        receipt_items = []
        total = 0.0
        timestamp = ""
        user_name = ""
        payment_summary = ""
        reservation_context = None

        if receipt_id:
            # Fetch from DB for reprint
            with rx.session() as session:
                try:
                    sale = session.exec(select(Sale).where(Sale.id == int(receipt_id))).first()
                    if not sale:
                        return rx.toast("Venta no encontrada.", duration=3000)
                    
                    timestamp = sale.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    total = sale.total_amount
                    payment_summary = sale.payment_details or sale.payment_method
                    user_name = sale.user.username if sale.user else "Desconocido"
                    
                    for item in sale.items:
                        receipt_items.append({
                            "description": item.product_name_snapshot,
                            "quantity": item.quantity,
                            "unit": "Unidad", 
                            "price": item.unit_price,
                            "subtotal": item.subtotal
                        })
                except ValueError:
                    return rx.toast("ID de venta inválido.", duration=3000)
        else:
            # Use current state
            if not self.sale_receipt_ready or not self.last_sale_receipt:
                return rx.toast(
                    "No hay comprobante disponible. Confirme una venta primero.",
                    duration=3000,
                )
            receipt_items = self.last_sale_receipt
            reservation_context = self.last_sale_reservation_context
            total = (
                reservation_context.get("charged_total", self.last_sale_total)
                if reservation_context
                else self.last_sale_total
            )
            timestamp = self.last_sale_timestamp
            user_name = self.current_user.get('username', 'Desconocido')
            payment_summary = self.last_payment_summary

        # Funciones auxiliares para formato de texto plano
        def center(text, width=42):
            return text.center(width)
        
        def line(width=42):
            return "-" * width
        
        def row(left, right, width=42):
            spaces = width - len(left) - len(right)
            return left + " " * max(spaces, 1) + right

        # Construir recibo línea por línea
        receipt_lines = [
            "",
            center("LUXETY SPORT S.A.C."),
            "",
            center("RUC: 20601348676"),
            "",
            center("AV. ALFONSO UGARTE NRO. 096"),
            center("LIMA-LIMA"),
            "",
            line(),
            center("COMPROBANTE DE PAGO"),
            line(),
            "",
            f"Fecha: {timestamp}",
            "",
            f"Atendido por: {user_name}",
            "",
            line(),
        ]
        
        # Agregar contexto de reserva si existe
        if reservation_context:
            ctx = reservation_context
            header = ctx.get("header", "")
            products_total = ctx.get("products_total", 0)
            
            if header:
                receipt_lines.append("")
                receipt_lines.append(center(header))
                receipt_lines.append("")
                receipt_lines.append(line())
            
            receipt_lines.append("")
            receipt_lines.append(row("TOTAL RESERVA:", self._format_currency(ctx['total'])))
            receipt_lines.append("")
            receipt_lines.append(row("Adelanto previo:", self._format_currency(ctx['paid_before'])))
            receipt_lines.append("")
            receipt_lines.append(row("PAGO ACTUAL:", self._format_currency(ctx['paid_now'])))
            receipt_lines.append("")
            
            if products_total > 0:
                receipt_lines.append(row("PRODUCTOS:", self._format_currency(products_total)))
                receipt_lines.append("")
            
            receipt_lines.append(row("Saldo pendiente:", self._format_currency(ctx.get('balance_after', 0))))
            receipt_lines.append("")
            receipt_lines.append(line())
        
        # Agregar ítems
        for item in receipt_items:
            receipt_lines.append("")
            receipt_lines.append(item['description'])
            receipt_lines.append(f"{item['quantity']} {item['unit']} x {self._format_currency(item['price'])}    {self._format_currency(item['subtotal'])}")
            receipt_lines.append("")
            receipt_lines.append(line())
        
        # Total y método de pago
        receipt_lines.extend([
            "",
            row("TOTAL A PAGAR:", self._format_currency(total)),
            "",
            f"Metodo de Pago: {payment_summary}",
            "",
            line(),
            "",
            center("GRACIAS POR SU PREFERENCIA"),
            " ",
            " ",
            " ",
        ])
        
        receipt_text = chr(10).join(receipt_lines)
        
        html_content = f"""<html>
<head>
<meta charset='utf-8'/>
<title>Comprobante de Pago</title>
<style>
@page {{ size: 80mm auto; margin: 0; }}
body {{ margin: 0; padding: 2mm; }}
pre {{ font-family: monospace; font-size: 12px; margin: 0; white-space: pre-wrap; }}
</style>
</head>
<body>
<pre>{receipt_text}</pre>
</body>
</html>"""
        
        script = f"""
        const receiptWindow = window.open('', '_blank');
        receiptWindow.document.write({json.dumps(html_content)});
        receiptWindow.document.close();
        receiptWindow.focus();
        receiptWindow.print();
        """
        # Para cobros de reserva, libera seleccion despues de imprimir
        if self.last_sale_reservation_context and not receipt_id:
            if hasattr(self, "reservation_payment_id"):
                self.reservation_payment_id = ""
            if hasattr(self, "reservation_payment_amount"):
                self.reservation_payment_amount = ""
            self.last_sale_reservation_context = None
        
        if not receipt_id:
            self._reset_payment_fields()
            self._refresh_payment_feedback()
            
        return rx.call_script(script)

    @rx.event
    def print_sale_receipt(self):
        return self._print_receipt_logic(None)

    @rx.event
    def print_sale_receipt_by_id(self, receipt_id: str):
        return self._print_receipt_logic(receipt_id)
