import reflex as rx
import uuid
from typing import List, Dict, Any, Set
from decimal import Decimal, ROUND_HALF_UP
from sqlmodel import select
from app.models import Unit, PaymentMethod, Currency, CompanySettings
from .types import CurrencyOption, PaymentMethodConfig
from .mixin_state import MixinState

class ConfigState(MixinState):
    # Configuracion de empresa
    company_name: str = ""
    ruc: str = ""
    address: str = ""
    phone: str = ""
    footer_message: str = ""
    receipt_paper: str = "80"
    receipt_width: str = ""
    company_form_key: int = 0

    # Monedas
    selected_currency_code: str = "PEN"
    new_currency_name: str = ""
    new_currency_code: str = ""
    new_currency_symbol: str = ""
    
    # Unidades
    new_unit_name: str = ""
    new_unit_allows_decimal: bool = False
    
    available_currencies: List[CurrencyOption] = []
    units: List[str] = []
    decimal_units: Set[str] = set()
    unit_rows: List[Dict[str, Any]] = []
    payment_methods: List[PaymentMethodConfig] = []

    def _require_manage_config(self):
        if hasattr(self, "current_user") and not self.current_user["privileges"].get(
            "manage_config"
        ):
            return rx.toast(
                "No tiene permisos para configurar el sistema.", duration=3000
            )
        return None

    def load_config_data(self):
        with rx.session() as session:
            # Cargar monedas
            currencies = session.exec(select(Currency)).all()
            if not currencies:
                self.available_currencies = [{"code": "PEN", "name": "Sol peruano (PEN)", "symbol": "S/"}]
            else:
                self.available_currencies = [{"code": c.code, "name": c.name, "symbol": c.symbol} for c in currencies]

            # Cargar unidades
            units_db = session.exec(select(Unit)).all()
            self.units = [u.name for u in units_db]
            self.decimal_units = {u.name for u in units_db if u.allows_decimal}
            self.unit_rows = [
                {"name": u.name, "allows_decimal": u.allows_decimal}
                for u in units_db
            ]

            # Cargar metodos de pago
            methods = session.exec(select(PaymentMethod)).all()
            self.payment_methods = [
                {
                    "id": m.method_id,
                    "name": m.name,
                    "description": m.description,
                    "kind": m.kind,
                    "enabled": m.enabled
                }
                for m in methods
            ]

    @rx.event
    def load_settings(self):
        self.company_name = ""
        self.ruc = ""
        self.address = ""
        self.phone = ""
        self.footer_message = ""
        self.receipt_paper = "80"
        self.receipt_width = ""
        with rx.session() as session:
            settings = session.exec(select(CompanySettings)).first()
            if settings:
                self.company_name = settings.company_name or ""
                self.ruc = settings.ruc or ""
                self.address = settings.address or ""
                self.phone = settings.phone or ""
                self.footer_message = settings.footer_message or ""
                receipt_paper = settings.receipt_paper or "80"
                self.receipt_paper = receipt_paper if receipt_paper in {"58", "80"} else "80"
                self.receipt_width = (
                    str(settings.receipt_width)
                    if settings.receipt_width is not None
                    else ""
                )
        self.company_form_key += 1

    @rx.event
    def set_company_name(self, value: str):
        self.company_name = value or ""

    @rx.event
    def set_ruc(self, value: str):
        self.ruc = value or ""

    @rx.event
    def set_address(self, value: str):
        self.address = value or ""

    @rx.event
    def set_phone(self, value: str):
        self.phone = value or ""

    @rx.event
    def set_footer_message(self, value: str):
        self.footer_message = value or ""

    @rx.event
    def set_receipt_paper(self, value: str):
        self.receipt_paper = value or "80"

    @rx.event
    def set_receipt_width(self, value: str):
        self.receipt_width = value or ""

    @rx.event
    def save_settings(self):
        toast = self._require_manage_config()
        if toast:
            return toast
        company_name = (self.company_name or "").strip()
        ruc = (self.ruc or "").strip()
        address = (self.address or "").strip()
        phone = (self.phone or "").strip()
        footer_message = (self.footer_message or "").strip()
        receipt_paper = (self.receipt_paper or "80").strip()
        if receipt_paper not in {"58", "80"}:
            receipt_paper = "80"
        receipt_width_value = None
        receipt_width_raw = (self.receipt_width or "").strip()
        if receipt_width_raw:
            try:
                receipt_width_value = int(receipt_width_raw)
            except ValueError:
                return rx.toast(
                    "El ancho de recibo debe ser un numero.",
                    duration=3000,
                )
            if receipt_width_value < 24 or receipt_width_value > 64:
                return rx.toast(
                    "El ancho de recibo debe estar entre 24 y 64.",
                    duration=3000,
                )

        with rx.session() as session:
            settings = session.exec(select(CompanySettings)).first()
            if settings:
                settings.company_name = company_name
                settings.ruc = ruc
                settings.address = address
                settings.phone = phone or None
                settings.footer_message = footer_message or None
                settings.receipt_paper = receipt_paper
                settings.receipt_width = receipt_width_value
                session.add(settings)
            else:
                settings = CompanySettings(
                    company_name=company_name,
                    ruc=ruc,
                    address=address,
                    phone=phone or None,
                    footer_message=footer_message or None,
                    receipt_paper=receipt_paper,
                    receipt_width=receipt_width_value,
                )
                session.add(settings)
            session.commit()
        self.company_name = company_name
        self.ruc = ruc
        self.address = address
        self.phone = phone
        self.footer_message = footer_message
        self.receipt_paper = receipt_paper
        self.receipt_width = (
            str(receipt_width_value) if receipt_width_value is not None else ""
        )
        self.company_form_key += 1
        return rx.toast("Configuracion de empresa guardada.", duration=2500)

    @rx.event
    def go_to_config_tab(self, tab: str):
        self.config_active_tab = tab

    def add_unit(self):
        toast = self._require_manage_config()
        if toast:
            return toast
        name = self.new_unit_name.strip()
        if not name:
            return
            
        with rx.session() as session:
            existing = session.exec(select(Unit).where(Unit.name == name)).first()
            if not existing:
                session.add(Unit(name=name, allows_decimal=self.new_unit_allows_decimal))
                session.commit()
                self.new_unit_name = ""
                self.new_unit_allows_decimal = False
                self.load_config_data()
                return rx.toast(f"Unidad '{name}' agregada.", duration=2000)
            else:
                return rx.toast("La unidad ya existe.", duration=2000)

    def set_unit_decimal(self, unit_name: str, allows_decimal: bool):
        toast = self._require_manage_config()
        if toast:
            return toast
        with rx.session() as session:
            unit = session.exec(select(Unit).where(Unit.name == unit_name)).first()
            if unit:
                unit.allows_decimal = allows_decimal
                session.add(unit)
                session.commit()
        self.load_config_data()

    def remove_unit(self, unit_name: str):
        toast = self._require_manage_config()
        if toast:
            return toast
        with rx.session() as session:
            unit = session.exec(select(Unit).where(Unit.name == unit_name)).first()
            if unit:
                session.delete(unit)
                session.commit()
                self.load_config_data()
                return rx.toast(f"Unidad '{unit_name}' eliminada.", duration=2000)

    def ensure_default_data(self):
        with rx.session() as session:
            # Unidades
            if not session.exec(select(Unit)).first():
                defaults = ["unidad", "pieza", "kg", "g", "l", "ml", "m", "cm", "paquete", "caja", "docena", "bolsa", "botella", "lata"]
                decimals = {"kg", "g", "l", "ml", "m", "cm"}
                for name in defaults:
                    session.add(Unit(name=name, allows_decimal=name in decimals))
            
            # Currencies
            if not session.exec(select(Currency)).first():
                session.add(Currency(code="PEN", name="Sol peruano (PEN)", symbol="S/"))
                session.add(Currency(code="ARS", name="Peso argentino (ARS)", symbol="$"))
                session.add(Currency(code="USD", name="Dolar estadounidense (USD)", symbol="US$"))

            # Metodos de pago
            existing_methods = {
                method.method_id: method
                for method in session.exec(select(PaymentMethod)).all()
                if method.method_id
            }
            defaults = [
                {
                    "method_id": "cash",
                    "name": "Efectivo",
                    "description": "Billetes, Monedas",
                    "kind": "cash",
                },
                {
                    "method_id": "debit",
                    "name": "T. Débito",
                    "description": "Pago con tarjeta débito",
                    "kind": "debit",
                },
                {
                    "method_id": "credit",
                    "name": "T. Crédito",
                    "description": "Pago con tarjeta crédito",
                    "kind": "credit",
                },
                {
                    "method_id": "yape",
                    "name": "Yape",
                    "description": "Pago con Yape",
                    "kind": "yape",
                },
                {
                    "method_id": "plin",
                    "name": "Plin",
                    "description": "Pago con Plin",
                    "kind": "plin",
                },
                {
                    "method_id": "transfer",
                    "name": "Transferencia",
                    "description": "Transferencia",
                    "kind": "transfer",
                },
                {
                    "method_id": "mixed",
                    "name": "Pago Mixto",
                    "description": "Combinacion",
                    "kind": "mixed",
                },
            ]
            for method in defaults:
                if method["method_id"] in existing_methods:
                    continue
                session.add(
                    PaymentMethod(
                        method_id=method["method_id"],
                        code=method["method_id"],
                        name=method["name"],
                        description=method["description"],
                        kind=method["kind"],
                        enabled=True,
                        is_active=True,
                        allows_change=method["method_id"] == "cash",
                    )
                )
            
            session.commit()
        self.load_config_data()

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
        toast = self._require_manage_config()
        if toast:
            return toast
        code = (self.new_currency_code or "").strip().upper()
        name = (self.new_currency_name or "").strip()
        symbol = (self.new_currency_symbol or "").strip()
        if not code or not name or not symbol:
            return rx.toast("Complete codigo, nombre y simbolo.", duration=3000)
        if any(c["code"] == code for c in self.available_currencies):
            return rx.toast("La moneda ya existe.", duration=3000)
        
        with rx.session() as session:
            new_currency = Currency(code=code, name=name, symbol=symbol)
            session.add(new_currency)
            session.commit()
        
        self.load_config_data()
        self.selected_currency_code = code
        self.new_currency_code = ""
        self.new_currency_name = ""
        self.new_currency_symbol = ""
        if hasattr(self, "_refresh_payment_feedback"):
            self._refresh_payment_feedback()
        return rx.toast(f"Moneda {name} agregado.", duration=2500)

    @rx.event
    def remove_currency(self, code: str):
        toast = self._require_manage_config()
        if toast:
            return toast
        code = (code or "").upper()
        if len(self.available_currencies) <= 1:
            return rx.toast("Debe quedar al menos una moneda.", duration=3000)
        if not any(c["code"] == code for c in self.available_currencies):
            return
        
        with rx.session() as session:
            currency_db = session.exec(select(Currency).where(Currency.code == code)).first()
            if currency_db:
                session.delete(currency_db)
                session.commit()
        
        self.load_config_data()
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
        toast = self._require_manage_config()
        if toast:
            return toast
        name = (self.new_unit_name or "").strip().lower()
        if not name:
            return rx.toast("Ingrese el nombre de la unidad.", duration=3000)
        if name in self.decimal_units:
            return rx.toast("Esa unidad ya esta registrada.", duration=3000)
        
        with rx.session() as session:
            existing_unit = session.exec(select(Unit).where(Unit.name == name)).first()
            if existing_unit:
                existing_unit.allows_decimal = self.new_unit_allows_decimal
                session.add(existing_unit)
            else:
                new_unit = Unit(name=name, allows_decimal=self.new_unit_allows_decimal)
                session.add(new_unit)
            session.commit()
        
        self.load_config_data()
        self.new_unit_name = ""
        self.new_unit_allows_decimal = False
        return rx.toast(f"Unidad {name} configurada.", duration=2500)

    @rx.event
    def remove_decimal_unit(self, unit: str):
        toast = self._require_manage_config()
        if toast:
            return toast
        unit = (unit or "").lower()
        with rx.session() as session:
            unit_db = session.exec(select(Unit).where(Unit.name == unit)).first()
            if unit_db and unit_db.allows_decimal:
                unit_db.allows_decimal = False
                session.add(unit_db)
                session.commit()
                self.load_config_data()
                return rx.toast(f"Unidad {unit} ya no permite decimales.", duration=2500)

    # Metodos de pago
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
            # Se asume que estan en VentaState o similar, pero los seteamos si aplica el mixin
            if hasattr(self, "payment_method"):
                self.payment_method = ""
            if hasattr(self, "payment_method_description"):
                self.payment_method_description = ""
            if hasattr(self, "payment_method_kind"):
                self.payment_method_kind = "other"
            return
        
        # Verificar si la seleccion actual es valida
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
        if kind not in [
            "cash",
            "debit",
            "credit",
            "yape",
            "plin",
            "transfer",
            "card",
            "wallet",
            "mixed",
            "other",
        ]:
            kind = "other"
        if any(m["name"].lower() == name.lower() for m in self.payment_methods):
            return rx.toast("Ya existe un metodo con ese nombre.", duration=3000)
        
        method_id = str(uuid.uuid4())
        with rx.session() as session:
            new_method = PaymentMethod(
                method_id=method_id,
                code=method_id,
                name=name,
                description=description or "Sin descripcion",
                kind=kind,
                enabled=True,
                is_active=True,
                allows_change=kind == "cash",
            )
            session.add(new_method)
            session.commit()
        
        self.load_config_data()
        self.new_payment_method_name = ""
        self.new_payment_method_description = ""
        self.new_payment_method_kind = "other"
        method: PaymentMethodConfig = {
            "id": method_id,
            "name": name,
            "description": description or "Sin descripcion",
            "kind": kind,
            "enabled": True,
        }
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
        
        method = self._payment_method_by_identifier(method_id)
        if not method:
            return
        
        if not enabled and method.get("enabled", True) and len(active_methods) <= 1:
            return rx.toast("Debe haber al menos un metodo activo.", duration=3000)
        
        with rx.session() as session:
            method_db = session.exec(select(PaymentMethod).where(PaymentMethod.method_id == method_id)).first()
            if method_db:
                method_db.enabled = enabled
                method_db.is_active = enabled
                session.add(method_db)
                session.commit()
        
        self.load_config_data()
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
        
        with rx.session() as session:
            method_db = session.exec(select(PaymentMethod).where(PaymentMethod.method_id == method_id)).first()
            if method_db:
                session.delete(method_db)
                session.commit()
        
        self.load_config_data()
        self._ensure_payment_method_selected()
        return rx.toast(f"Metodo {method['name']} eliminado.", duration=2500)
