import reflex as rx
import uuid
from typing import List, Dict, Any, Set
from decimal import Decimal, ROUND_HALF_UP
from .types import CurrencyOption, PaymentMethodConfig
from .mixin_state import MixinState

class ConfigState(MixinState):
    # Currency
    available_currencies: List[CurrencyOption] = [
        {"code": "PEN", "name": "Sol peruano (PEN)", "symbol": "S/"},
        {"code": "ARS", "name": "Peso argentino (ARS)", "symbol": "$"},
        {"code": "USD", "name": "Dolar estadounidense (USD)", "symbol": "US$"},
    ]
    selected_currency_code: str = "PEN"
    new_currency_name: str = ""
    new_currency_code: str = ""
    new_currency_symbol: str = ""
    
    # Units
    units: List[str] = [
        "unidad",
        "pieza",
        "kg",
        "g",
        "l",
        "ml",
        "m",
        "cm",
        "paquete",
        "caja",
        "docena",
        "bolsa",
        "botella",
        "lata",
    ]
    decimal_units: Set[str] = {
        "kg",
        "kilogramo",
        "kilogramos",
        "g",
        "gramo",
        "gramos",
        "l",
        "litro",
        "litros",
        "ml",
        "metro",
        "metros",
    }
    new_unit_name: str = ""
    new_unit_allows_decimal: bool = False

    @rx.event
    def go_to_config_tab(self, tab: str):
        self.config_active_tab = tab

    def add_unit(self):
        if self.new_unit_name and self.new_unit_name not in self.units:
            self.units.append(self.new_unit_name)
            if self.new_unit_allows_decimal:
                self.decimal_units.add(self.new_unit_name)
            self.new_unit_name = ""
            self.new_unit_allows_decimal = False

    @rx.var
    def unit_rows(self) -> List[Dict[str, Any]]:
        return [
            {"name": unit, "allows_decimal": unit in self.decimal_units}
            for unit in self.units
        ]

    def set_unit_decimal(self, unit: str, allows_decimal: bool):
        if allows_decimal:
            self.decimal_units.add(unit)
        elif unit in self.decimal_units:
            self.decimal_units.remove(unit)

    def remove_unit(self, unit: str):
        if unit in self.units:
            self.units.remove(unit)
        if unit in self.decimal_units:
            self.decimal_units.remove(unit)

    # Payment Methods
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
    new_payment_method_name: str = ""
    new_payment_method_description: str = ""
    new_payment_method_kind: str = "other"

    @rx.var
    def currency_symbol(self) -> str:
        match = next(
            (c for c in self.available_currencies if c["code"] == self.selected_currency_code),
            None,
        )
        return f"{match['symbol']} " if match else "S/ "

    @rx.var
    def currency_name(self) -> str:
        match = next(
            (c for c in self.available_currencies if c["code"] == self.selected_currency_code),
            None,
        )
        return match["name"] if match else "Sol peruano (PEN)"

    def _format_currency(self, value: float) -> str:
        return f"{self.currency_symbol}{self._round_currency(value):.2f}"

    @rx.event
    def set_currency(self, code: str):
        code = (code or "").upper()
        match = next((c for c in self.available_currencies if c["code"] == code), None)
        if not match:
            return rx.toast("Moneda no soportada.", duration=3000)
        self.selected_currency_code = code
        if hasattr(self, "_refresh_payment_feedback"):
            self._refresh_payment_feedback()
        return rx.toast(f"Moneda cambiada a {match['name']}.", duration=2500)

    @rx.event
    def set_new_currency_code(self, value: str):
        self.new_currency_code = (value or "").upper()

    @rx.event
    def set_new_currency_name(self, value: str):
        self.new_currency_name = value

    @rx.event
    def set_new_currency_symbol(self, value: str):
        self.new_currency_symbol = value

    @rx.event
    def add_currency(self):
        code = (self.new_currency_code or "").strip().upper()
        name = (self.new_currency_name or "").strip()
        symbol = (self.new_currency_symbol or "").strip()
        if not code or not name or not symbol:
            return rx.toast("Complete codigo, nombre y simbolo.", duration=3000)
        if any(c["code"] == code for c in self.available_currencies):
            return rx.toast("La moneda ya existe.", duration=3000)
        self.available_currencies.append({"code": code, "name": name, "symbol": symbol})
        self.selected_currency_code = code
        self.new_currency_code = ""
        self.new_currency_name = ""
        self.new_currency_symbol = ""
        if hasattr(self, "_refresh_payment_feedback"):
            self._refresh_payment_feedback()
        return rx.toast(f"Moneda {name} agregado.", duration=2500)

    @rx.event
    def remove_currency(self, code: str):
        code = (code or "").upper()
        if len(self.available_currencies) <= 1:
            return rx.toast("Debe quedar al menos una moneda.", duration=3000)
        if not any(c["code"] == code for c in self.available_currencies):
            return
        self.available_currencies = [
            currency for currency in self.available_currencies if currency["code"] != code
        ]
        if self.selected_currency_code == code and self.available_currencies:
            self.selected_currency_code = self.available_currencies[0]["code"]
        if hasattr(self, "_refresh_payment_feedback"):
            self._refresh_payment_feedback()
        return rx.toast("Moneda eliminada.", duration=2500)

    def _unit_allows_decimal(self, unit: str) -> bool:
        return unit and unit.lower() in self.decimal_units

    def _normalize_quantity_value(self, value: float, unit: str) -> float:
        if self._unit_allows_decimal(unit):
            return float(
                Decimal(str(value or 0)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            )
        return float(int(value))

    @rx.event
    def set_new_unit_name(self, value: str):
        self.new_unit_name = value

    @rx.event
    def set_new_unit_allows_decimal(self, value: bool):
        self.new_unit_allows_decimal = value

    @rx.event
    def add_decimal_unit(self):
        name = (self.new_unit_name or "").strip().lower()
        if not name:
            return rx.toast("Ingrese el nombre de la unidad.", duration=3000)
        if name in self.decimal_units:
            return rx.toast("Esa unidad ya esta registrada.", duration=3000)
        if self.new_unit_allows_decimal:
            self.decimal_units.add(name)
        # Note: If it doesn't allow decimal, we just don't add it to the set, 
        # but maybe we should track all units? The original code only tracked decimal_units set.
        # Assuming 'categories' or similar tracks units elsewhere if needed, but here we only manage the decimal flag set.
        self.new_unit_name = ""
        self.new_unit_allows_decimal = False
        return rx.toast(f"Unidad {name} configurada.", duration=2500)

    @rx.event
    def remove_decimal_unit(self, unit: str):
        unit = (unit or "").lower()
        if unit in self.decimal_units:
            self.decimal_units.remove(unit)
            return rx.toast(f"Unidad {unit} ya no permite decimales.", duration=2500)

    # Payment Methods
    def _payment_method_by_identifier(self, identifier: str) -> PaymentMethodConfig | None:
        target = (identifier or "").strip().lower()
        if not target:
            return None
        for method in self.payment_methods:
            if method["id"].lower() == target or method["name"].lower() == target:
                return method
        return None

    def _enabled_payment_methods_list(self) -> List[PaymentMethodConfig]:
        return [m for m in self.payment_methods if m.get("enabled", True)]

    def _default_payment_method(self) -> PaymentMethodConfig | None:
        enabled = self._enabled_payment_methods_list()
        if enabled:
            return enabled[0]
        return None

    def _ensure_payment_method_selected(self):
        available = self._enabled_payment_methods_list()
        if not available:
            # Assuming these are on VentaState or similar, but we can set them if we are mixed in
            if hasattr(self, "payment_method"):
                self.payment_method = ""
            if hasattr(self, "payment_method_description"):
                self.payment_method_description = ""
            if hasattr(self, "payment_method_kind"):
                self.payment_method_kind = "other"
            return
        
        # Check if current selection is valid
        current_name = getattr(self, "payment_method", "")
        if not any(m["name"] == current_name for m in available):
            if hasattr(self, "_set_payment_method"):
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
        if hasattr(self, "current_user") and not self.current_user["privileges"]["manage_config"]:
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
        if hasattr(self, "_set_payment_method"):
            self._set_payment_method(method)
        return rx.toast(f"Metodo {name} agregado.", duration=2500)

    @rx.event
    def toggle_payment_method_enabled(self, method_id: str, enabled: bool | str):
        if hasattr(self, "current_user") and not self.current_user["privileges"]["manage_config"]:
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
