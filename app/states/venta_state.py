import reflex as rx
from typing import List, Dict, Any, Union
import datetime
import uuid
import logging
import json
from .types import TransactionItem, PaymentMethodConfig, Movement, CashboxSale, Product, PaymentBreakdownItem
from app.utils.barcode import clean_barcode, validate_barcode
from .mixin_state import MixinState

class VentaState(MixinState):
    sale_form_key: int = 0
    new_sale_item: TransactionItem = {
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
    new_sale_items: List[TransactionItem] = []
    autocomplete_suggestions: List[str] = []
    last_sale_receipt: List[TransactionItem] = []
    last_sale_total: float = 0
    last_sale_timestamp: str = ""
    sale_receipt_ready: bool = False
    last_sale_reservation_context: Dict | None = None
    
    payment_methods: List[PaymentMethodConfig] = [
        {
            "id": "cash",
            "name": "Efectivo",
            "description": "Billetes, Monedas",
            "kind": "cash",
            "enabled": True,
        },
        {
            "id": "card",
            "name": "Tarjeta",
            "description": "Credito, Debito",
            "kind": "card",
            "enabled": True,
        },
        {
            "id": "wallet",
            "name": "Billetera Digital / QR",
            "description": "Yape, Plin, Billeteras Bancarias",
            "kind": "wallet",
            "enabled": True,
        },
        {
            "id": "mixed",
            "name": "Pagos Mixtos",
            "description": "Combinacion de metodos",
            "kind": "mixed",
            "enabled": True,
        },
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
        reservation = None
        if hasattr(self, "reservation_payment_id") and self.reservation_payment_id:
            if hasattr(self, "_find_reservation_by_id"):
                reservation = self._find_reservation_by_id(self.reservation_payment_id)
        
        balance = 0.0
        if reservation:
            balance = max(reservation["total_amount"] - reservation["paid_amount"], 0)
        products_total = sum((item["subtotal"] for item in self.new_sale_items))
        return self._round_currency(products_total + balance)

    @rx.var
    def enabled_payment_methods(self) -> list[PaymentMethodConfig]:
        return [m for m in self.payment_methods if m.get("enabled", True)]

    @rx.var
    def payment_summary(self) -> str:
        return self._generate_payment_summary()

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

    def _update_mixed_message(self, total_override: float | None = None):
        total = 0
        if total_override is not None:
            total = total_override
        else:
            res_balance = 0
            if hasattr(self, "selected_reservation_balance"):
                res_balance = self.selected_reservation_balance
            total = self.sale_total if self.sale_total > 0 else res_balance
            
        total = self._round_currency(total)
        
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
            self.payment_mixed_message = "Montos completos."
            self.payment_mixed_status = "exact"

    def _refresh_payment_feedback(self, total_override: float | None = None):
        if self.payment_method_kind == "cash":
            self._update_cash_feedback(total_override=total_override)
        elif self.payment_method_kind == "mixed":
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

    @rx.event
    def choose_wallet_provider(self, provider: str):
        self.payment_wallet_choice = provider
        if provider == "Otro":
            self.payment_wallet_provider = ""
        else:
            self.payment_wallet_provider = provider

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
        product_barcode = product.get("barcode", "")
        
        quantity = (
            self.new_sale_item["quantity"]
            if keep_quantity and self.new_sale_item["quantity"] > 0
            else 1
        )
        
        self.new_sale_item["barcode"] = product_barcode
        self.new_sale_item["description"] = product["description"]
        self.new_sale_item["category"] = product.get("category", self.categories[0] if hasattr(self, "categories") and self.categories else "")
        self.new_sale_item["unit"] = product["unit"]
        self.new_sale_item["quantity"] = self._normalize_quantity_value(quantity, product["unit"])
        self.new_sale_item["price"] = self._round_currency(product["sale_price"])
        self.new_sale_item["sale_price"] = self._round_currency(product["sale_price"])
        self.new_sale_item["subtotal"] = self._round_currency(
            self.new_sale_item["quantity"] * self.new_sale_item["price"]
        )
        
        if not keep_quantity:
            self.autocomplete_suggestions = []
        
        logging.info(f"[FILL-SALE] Código corregido: escaneado incompleto → '{product_barcode}' completo (producto: {product['description']})")

    def _reset_sale_form(self):
        self.sale_form_key += 1
        self.new_sale_item = {
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
                if value:
                    self.autocomplete_suggestions = [
                        p["description"]
                        for p in self.inventory.values()
                        if str(value).lower() in p["description"].lower()
                    ][:5]
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
                        # Accessing _find_product_by_barcode from InventoryState
                        if hasattr(self, "_find_product_by_barcode"):
                            product = self._find_product_by_barcode(code)
                            if product:
                                self._fill_sale_item_from_product(product, keep_quantity=False)
                                self.autocomplete_suggestions = []
                                return rx.toast(f"Producto '{product['description']}' cargado", duration=2000)
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
            if hasattr(self, "_find_product_by_barcode"):
                product = self._find_product_by_barcode(code)
                if product:
                    self._fill_sale_item_from_product(product, keep_quantity=False)
                    self.autocomplete_suggestions = []
                    return rx.toast(f"Producto '{product['description']}' cargado", duration=2000)

    @rx.event
    def select_product_for_sale(self, description: str):
        if isinstance(description, dict):
            description = (
                description.get("value")
                or description.get("description")
                or description.get("label")
                or ""
            )
        product_id = description.lower().strip()
        if hasattr(self, "inventory") and product_id in self.inventory:
            product = self.inventory[product_id]
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
        product_id = self.new_sale_item["description"].lower().strip()
        if hasattr(self, "inventory"):
            if product_id not in self.inventory:
                return rx.toast("Producto no encontrado en el inventario.", duration=3000)
            if self.inventory[product_id]["stock"] < self.new_sale_item["quantity"]:
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
        
        reservation = None
        if hasattr(self, "reservation_payment_id") and self.reservation_payment_id:
            if hasattr(self, "_find_reservation_by_id"):
                reservation = self._find_reservation_by_id(self.reservation_payment_id)
        
        if reservation and reservation["status"] in ["cancelado", "eliminado"]:
            return rx.toast("No se puede cobrar una reserva cancelada o eliminada.", duration=3000)
        
        reservation_balance = 0
        if reservation:
            reservation_balance = self._round_currency(
                max(reservation["total_amount"] - reservation["paid_amount"], 0)
            )

        if not self.new_sale_items and reservation_balance <= 0:
            if reservation:
                return rx.toast("La reserva ya esta pagada.", duration=3000)
            return rx.toast("No hay productos en la venta.", duration=3000)
        if not self.payment_method:
            return rx.toast("Seleccione un metodo de pago.", duration=3000)

        product_snapshot: list[TransactionItem] = []
        for item in self.new_sale_items:
            snapshot_item = item.copy()
            self._apply_item_rounding(snapshot_item)
            product_snapshot.append(snapshot_item)
        sale_snapshot: list[TransactionItem] = list(product_snapshot)
        if reservation_balance > 0:
            sale_snapshot.insert(
                0,
                {
                    "temp_id": reservation["id"],
                    "barcode": reservation["id"],
                    "description": (
                        f"Alquiler {reservation['field_name']} "
                        f"({reservation['start_datetime']} - {reservation['end_datetime']})"
                    ),
                    "category": "Servicios",
                    "quantity": 1,
                    "unit": "Servicio",
                    "price": reservation_balance,
                    "sale_price": reservation_balance,
                    "subtotal": reservation_balance,
                },
            )
        sale_total = self._round_currency(sum(item["subtotal"] for item in sale_snapshot))
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
        
        # Verifica stock antes de aplicar descuentos.
        if hasattr(self, "inventory"):
            for item in product_snapshot:
                product_id = item["description"].lower().strip()
                if product_id not in self.inventory:
                    return rx.toast(f"Producto {item['description']} no encontrado en inventario.", duration=3000)
                if self.inventory[product_id]["stock"] < item["quantity"]:
                    return rx.toast(f"Stock insuficiente para {item['description']}.", duration=3000)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payment_summary = self._generate_payment_summary()
        payment_label, payment_breakdown = self._payment_label_and_breakdown(sale_total)
        sale_id = str(uuid.uuid4())
        history_entries: list[Movement] = []
        
        if hasattr(self, "inventory"):
            for item in product_snapshot:
                product_id = item["description"].lower().strip()
                new_stock = self.inventory[product_id]["stock"] - item["quantity"]
                if new_stock < 0:
                    new_stock = 0
                self.inventory[product_id]["stock"] = self._normalize_quantity_value(
                    new_stock, self.inventory[product_id]["unit"]
                )
                history_entry = {
                    "id": str(uuid.uuid4()),
                    "timestamp": timestamp,
                    "type": "Venta",
                    "product_description": item["description"],
                    "quantity": item["quantity"],
                    "unit": item["unit"],
                    "total": item["subtotal"],
                    "payment_method": self.payment_method,
                    "payment_kind": self.payment_method_kind,
                    "payment_label": payment_label,
                    "payment_breakdown": [p.copy() for p in payment_breakdown],
                    "payment_details": payment_summary,
                    "user": self.current_user["username"],
                    "sale_id": sale_id,
                }
                history_entries.append(history_entry)

        applied_amount = 0.0
        if reservation_balance > 0:
            applied_amount = reservation_balance
            paid_before = reservation["paid_amount"]
            reservation["paid_amount"] = self._round_currency(reservation["paid_amount"] + applied_amount)
            if hasattr(self, "_update_reservation_status"):
                self._update_reservation_status(reservation)
            entry_type = "pago" if reservation["paid_amount"] >= reservation["total_amount"] else "adelanto"
            balance_after = max(reservation["total_amount"] - reservation["paid_amount"], 0)
            reservation_note = (
                f"{payment_summary} | Total: {self._format_currency(reservation['total_amount'])} "
                f"| Adelanto: {self._format_currency(paid_before)} "
                f"| Pago: {self._format_currency(applied_amount)} "
                f"| Saldo: {self._format_currency(balance_after)}"
            )
            payment_summary = reservation_note
            if hasattr(self, "_log_service_action"):
                self._log_service_action(
                    reservation,
                    entry_type,
                    applied_amount,
                    notes=reservation_note,
                    status=reservation["status"],
                )
            if hasattr(self, "reservation_payment_amount"):
                self.reservation_payment_amount = ""
            if hasattr(self, "_set_last_reservation_receipt"):
                self._set_last_reservation_receipt(reservation)
            self.last_sale_reservation_context = {
                "total": reservation["total_amount"],
                "paid_before": paid_before,
                "paid_now": applied_amount,
                "paid_after": reservation["paid_amount"],
                "balance_after": balance_after,
                "header": f"Alquiler {reservation['field_name']} ({reservation['start_datetime']} - {reservation['end_datetime']})",
                "products_total": self._round_currency(sum(item["subtotal"] for item in product_snapshot)),
                "charged_total": sale_total,
            }
        else:
            self.last_sale_reservation_context = None
            
        for entry in history_entries:
            entry["payment_details"] = payment_summary
            
        if hasattr(self, "history"):
            self.history.extend(history_entries)
            
        if hasattr(self, "cashbox_sales"):
            self.cashbox_sales.append(
                {
                    "sale_id": sale_id,
                    "timestamp": timestamp,
                    "user": self.current_user["username"],
                    "payment_method": self.payment_method,
                    "payment_kind": self.payment_method_kind,
                    "payment_label": payment_label,
                    "payment_breakdown": [p.copy() for p in payment_breakdown],
                    "payment_details": payment_summary,
                    "total": sale_total,
                    "service_total": sale_total,
                    "items": [item.copy() for item in sale_snapshot],
                    "is_deleted": False,
                    "delete_reason": "",
                }
            )
            
        self.last_sale_receipt = sale_snapshot
        self.last_sale_total = sale_total
        self.last_sale_timestamp = timestamp
        self.last_payment_summary = payment_summary
        self.sale_receipt_ready = True
        self.new_sale_items = []
        self._reset_sale_form()
        self._reset_payment_fields()
        self._refresh_payment_feedback()
        return rx.toast("Venta confirmada.", duration=3000)

    @rx.event
    def print_sale_receipt(self):
        if not self.sale_receipt_ready or not self.last_sale_receipt:
            return rx.toast(
                "No hay comprobante disponible. Confirme una venta primero.",
                duration=3000,
            )
        rows = "".join(
            f"<tr><td colspan='2' style='font-weight:bold;text-align:center;font-size:13px;'>{item['description']}</td></tr>"
            f"<tr><td>{item['quantity']} {item['unit']} x {self._format_currency(item['price'])}</td><td style='text-align:right;'>{self._format_currency(item['subtotal'])}</td></tr>"
            for item in self.last_sale_receipt
        )
        summary_rows = ""
        if self.last_sale_reservation_context:
            ctx = self.last_sale_reservation_context
            header = ctx.get("header", "")
            header_row = ""
            if header:
                header_row = (
                    f"<tr><td colspan='2' style='text-align:center;font-weight:bold;font-size:13px;'>"
                    f"{header}"
                    f"</td></tr>"
                )
            products_total = ctx.get("products_total", 0)
            summary_rows = (
                header_row
                + "<tr><td colspan='2' style='height:4px;'></td></tr>"
                + f"<tr><td>Total reserva</td><td style='text-align:right;'>{self._format_currency(ctx['total'])}</td></tr>"
                + "<tr><td colspan='2' style='height:4px;'></td></tr>"
                + f"<tr><td>Adelanto previo</td><td style='text-align:right;'>{self._format_currency(ctx['paid_before'])}</td></tr>"
                + f"<tr><td style='font-weight:bold;'>Pago actual</td><td style='text-align:right;font-weight:bold;'>{self._format_currency(ctx['paid_now'])}</td></tr>"
                + (
                    f"<tr><td>Productos adicionales</td><td style='text-align:right;'>{self._format_currency(products_total)}</td></tr>"
                    if products_total > 0
                    else ""
                )
                + f"<tr><td>Saldo pendiente</td><td style='text-align:right;'>{self._format_currency(ctx.get('balance_after', 0))}</td></tr>"
                + "<tr><td colspan='2' style='height:6px;'></td></tr>"
            )
        display_rows = summary_rows + rows
        display_total = (
            self.last_sale_reservation_context.get("charged_total", self.last_sale_total)
            if self.last_sale_reservation_context
            else self.last_sale_total
        )
        html_content = f"""
        <html>
            <head>
                <meta charset='utf-8' />
                <title>Comprobante de Pago</title>
                <style>
                    @page {{
                        size: 58mm auto;
                        margin: 2mm;
                    }}
                    body {{
                        font-family: 'Courier New', monospace;
                        width: 56mm;
                        margin: 0 auto;
                        font-size: 11px;
                    }}
                    h1 {{
                        text-align: center;
                        font-size: 14px;
                        margin: 0 0 6px 0;
                    }}
                    .section {{
                        margin-bottom: 6px;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                    }}
                    td {{
                        padding: 2px 0;
                        text-align: left;
                    }}
                    td:last-child {{
                        text-align: right;
                    }}
                    hr {{
                        border: 0;
                        border-top: 1px dashed #000;
                        margin: 6px 0;
                    }}
                </style>
            </head>
            <body>
                <h1>Comprobante de Pago</h1>
                <div class="section"><strong>Fecha:</strong> {self.last_sale_timestamp}</div>
                <hr />
                <table>
                    {display_rows}
                </table>
                <hr />
                <div class="section"><strong>Total General:</strong> <strong>{self._format_currency(display_total)}</strong></div>
                <div class="section"><strong>Metodo de Pago:</strong> {self.last_payment_summary}</div>
            </body>
        </html>
        """
        script = f"""
        const receiptWindow = window.open('', '_blank');
        receiptWindow.document.write({json.dumps(html_content)});
        receiptWindow.document.close();
        receiptWindow.focus();
        receiptWindow.print();
        """
        # Para cobros de reserva, libera seleccion despues de imprimir
        if self.last_sale_reservation_context:
            if hasattr(self, "reservation_payment_id"):
                self.reservation_payment_id = ""
            if hasattr(self, "reservation_payment_amount"):
                self.reservation_payment_amount = ""
            self.last_sale_reservation_context = None
        self._reset_payment_fields()
        self._refresh_payment_feedback()
        return rx.call_script(script)
