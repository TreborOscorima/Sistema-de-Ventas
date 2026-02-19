import reflex as rx
import uuid
from typing import List, Dict, Any, Set
from decimal import Decimal, ROUND_HALF_UP
from sqlmodel import select
from app.models import Unit, PaymentMethod, Currency, CompanySettings
from app.utils.db_seeds import SUPPORTED_COUNTRIES, get_payment_methods_for_country, get_country_config
from app.utils.timezone import is_valid_timezone
from app.enums import PaymentMethodType
from .types import CurrencyOption, PaymentMethodConfig
from .mixin_state import MixinState

WHATSAPP_SALES_URL = "https://wa.me/message/ULLEZ4HUFB5HA1"

_REGIONAL_TIMEZONES = [
    "America/Lima",
    "America/Bogota",
    "America/Guayaquil",
    "America/Santiago",
    "America/Argentina/Buenos_Aires",
    "America/Mexico_City",
    "America/New_York",
    "UTC",
]

_COUNTRY_TIMEZONES = [
    get_country_config(code).get("timezone", "UTC")
    for code in SUPPORTED_COUNTRIES.keys()
]
_BASE_TIMEZONE_OPTIONS = []
for _tz in [*_COUNTRY_TIMEZONES, *_REGIONAL_TIMEZONES]:
    if _tz and _tz not in _BASE_TIMEZONE_OPTIONS:
        _BASE_TIMEZONE_OPTIONS.append(_tz)

class ConfigState(MixinState):
    # Configuracion de empresa
    company_name: str = ""
    ruc: str = ""
    address: str = ""
    phone: str = ""
    footer_message: str = ""
    receipt_paper: str = "80"
    receipt_width: str = ""
    timezone: str = ""
    company_form_key: int = 0
    show_upgrade_modal: bool = False
    show_pricing_modal: bool = False

    # País de operación
    selected_country_code: str = "PE"

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

    @rx.var(cache=True)
    def available_countries(self) -> List[Dict[str, str]]:
        """Lista de países soportados para el selector."""
        return [
            {"code": code, "name": info["name"], "currency": info["currency"]}
            for code, info in SUPPORTED_COUNTRIES.items()
        ]

    @rx.var(cache=True)
    def country_config(self) -> Dict[str, Any]:
        """Configuración completa del país actual."""
        return get_country_config(self.selected_country_code)

    @rx.var(cache=True)
    def tax_id_label(self) -> str:
        """Label para identificación tributaria según el país.

        Perú/Ecuador: RUC, Argentina: CUIT, Colombia: NIT, Chile: RUT, México: RFC
        """
        return get_country_config(self.selected_country_code).get("tax_id_label", "ID Fiscal")

    @rx.var(cache=True)
    def personal_id_label(self) -> str:
        """Label para documento de identidad personal según el país.

        Perú/Argentina: DNI, Ecuador: Cédula, Colombia: C.C., Chile: RUN, México: CURP
        """
        return get_country_config(self.selected_country_code).get("personal_id_label", "Documento")

    @rx.var(cache=True)
    def tax_id_placeholder(self) -> str:
        """Placeholder para el campo de ID tributario."""
        return get_country_config(self.selected_country_code).get("tax_id_placeholder", "")

    @rx.var(cache=True)
    def personal_id_placeholder(self) -> str:
        """Placeholder para el campo de documento personal."""
        return get_country_config(self.selected_country_code).get("personal_id_placeholder", "")

    @rx.var(cache=True)
    def timezone_placeholder(self) -> str:
        """Zona horaria sugerida según el país."""
        return get_country_config(self.selected_country_code).get("timezone", "UTC")

    @rx.var(cache=True)
    def timezone_options(self) -> List[str]:
        """Opciones de zona horaria optimizadas para operación LATAM."""
        current = (self.timezone or "").strip()
        options = list(_BASE_TIMEZONE_OPTIONS)
        if current and current not in options:
            options.insert(0, current)
        return options

    def _require_manage_config(self):
        if hasattr(self, "current_user") and not self.current_user["privileges"].get(
            "manage_config"
        ):
            return rx.toast(
                "No tiene permisos para configurar el sistema.", duration=3000
            )
        return None

    def load_config_data(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        with rx.session() as session:
            # Cargar monedas
            currencies = session.exec(select(Currency)).all()
            if not currencies:
                # Fallback dinámico basado en el país configurado
                config = get_country_config(self.selected_country_code)
                self.available_currencies = [{
                    "code": config["currency"],
                    "name": f"{config['currency_name']} ({config['currency']})",
                    "symbol": config["currency_symbol"]
                }]
            else:
                self.available_currencies = [{"code": c.code, "name": c.name, "symbol": c.symbol} for c in currencies]

            # Cargar unidades
            units_db = []
            if company_id and branch_id:
                units_db = session.exec(
                    select(Unit)
                    .where(Unit.company_id == company_id)
                    .where(Unit.branch_id == branch_id)
                ).all()
            self.units = [u.name for u in units_db]
            self.decimal_units = {u.name for u in units_db if u.allows_decimal}
            self.unit_rows = [
                {"name": u.name, "allows_decimal": u.allows_decimal}
                for u in units_db
            ]

            # Cargar metodos de pago
            methods = []
            if company_id and branch_id:
                methods = session.exec(
                    select(PaymentMethod)
                    .where(PaymentMethod.company_id == company_id)
                    .where(PaymentMethod.branch_id == branch_id)
                ).all()
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
        """Carga la configuración de la empresa desde la base de datos.

        Incluye nombre, RUC, dirección, teléfono, mensaje de pie,
        configuración de recibo y la moneda por defecto del negocio.
        """
        self.company_name = ""
        self.ruc = ""
        self.address = ""
        self.phone = ""
        self.footer_message = ""
        self.receipt_paper = "80"
        self.receipt_width = ""
        self.timezone = ""
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            self.company_form_key += 1
            return
        with rx.session() as session:
            settings = None
            settings_stmt = select(CompanySettings).where(
                CompanySettings.company_id == company_id
            )
            if branch_id:
                settings = session.exec(
                    settings_stmt.where(CompanySettings.branch_id == branch_id)
                ).first()
            if not settings:
                settings = session.exec(
                    settings_stmt.order_by(
                        CompanySettings.branch_id, CompanySettings.id
                    )
                ).first()
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
                # Cargar la moneda persistida del negocio
                if hasattr(settings, 'default_currency_code') and settings.default_currency_code:
                    self.selected_currency_code = settings.default_currency_code
                # Cargar el país de operación
                if hasattr(settings, 'country_code') and settings.country_code:
                    self.selected_country_code = settings.country_code
                # Cargar la zona horaria (si existe)
                if hasattr(settings, "timezone") and settings.timezone:
                    self.timezone = settings.timezone
        self.company_form_key += 1

    @rx.event
    def load_config_page(self):
        """Carga datos necesarios para la pantalla de configuración."""
        self.load_settings()
        if hasattr(self, "load_config_data"):
            self.load_config_data()
        if hasattr(self, "load_users"):
            self.load_users()
        if hasattr(self, "load_branches"):
            self.load_branches()

    @rx.event(background=True)
    async def load_config_page_background(self):
        """Carga la configuración en segundo plano para mejorar la navegación."""
        async with self:
            self.load_config_page()

    @rx.event
    def open_upgrade_modal(self):
        self.show_upgrade_modal = True

    @rx.event
    def close_upgrade_modal(self):
        self.show_upgrade_modal = False

    @rx.event
    def set_upgrade_modal(self, value: bool):
        self.show_upgrade_modal = bool(value)

    @rx.event
    def open_pricing_modal(self):
        self.show_pricing_modal = True

    @rx.event
    def close_pricing_modal(self):
        self.show_pricing_modal = False

    @rx.event
    def set_pricing_modal(self, value: bool):
        self.show_pricing_modal = bool(value)

    @rx.event
    def contact_sales_whatsapp(self):
        self.show_upgrade_modal = False
        return rx.redirect(WHATSAPP_SALES_URL)

    @rx.event
    def set_country(self, code: str):
        """Establece el país de operación y carga los métodos de pago correspondientes.

        Al cambiar de país:
        1. Se actualiza el país en CompanySettings
        2. Se actualiza la moneda por defecto del país
        3. Se cargan los métodos de pago específicos del país

        Args:
            code: Código ISO del país (ej: 'PE', 'AR', 'EC')
        """
        toast = self._require_manage_config()
        if toast:
            return toast
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return rx.toast("Empresa no definida.", duration=3000)

        code = (code or "PE").upper()
        if code not in SUPPORTED_COUNTRIES:
            return rx.toast("País no soportado.", duration=3000)

        country_info = SUPPORTED_COUNTRIES[code]
        new_currency = country_info["currency"]

        with rx.session() as session:
            # Actualizar CompanySettings
            settings_list = session.exec(
                select(CompanySettings)
                .where(CompanySettings.company_id == company_id)
            ).all()
            if settings_list:
                for settings in settings_list:
                    settings.country_code = code
                    settings.default_currency_code = new_currency
                    session.add(settings)
            else:
                branch_id_value = int(branch_id) if branch_id else 1
                session.add(
                    CompanySettings(
                        company_id=company_id,
                        branch_id=branch_id_value,
                        country_code=code,
                        default_currency_code=new_currency,
                    )
                )

            # Limpiar métodos de pago existentes
            existing_methods = session.exec(
                select(PaymentMethod)
                .where(PaymentMethod.company_id == company_id)
                .where(PaymentMethod.branch_id == branch_id)
            ).all()
            for method in existing_methods:
                session.delete(method)

            # Insertar métodos de pago del nuevo país
            new_methods = get_payment_methods_for_country(code)
            for data in new_methods:
                method = PaymentMethod(
                    name=data["name"],
                    code=data["code"],
                    is_active=True,
                    allows_change=data["allows_change"],
                    method_id=data["method_id"],
                    description=data["description"],
                    kind=data["kind"],
                    enabled=True,
                    company_id=company_id,
                    branch_id=branch_id,
                )
                session.add(method)

            session.commit()

        self.selected_country_code = code
        self.selected_currency_code = new_currency
        self.load_config_data()  # Recargar métodos de pago

        return rx.toast(
            f"País cambiado a {country_info['name']}. Moneda: {new_currency}. "
            f"Métodos de pago actualizados.",
            duration=4000
        )

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
    def set_timezone(self, value: str):
        self.timezone = value or ""

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
        timezone_value = (self.timezone or "").strip()
        if not is_valid_timezone(timezone_value):
            return rx.toast(
                "Zona horaria invalida. Usa el formato IANA (ej: America/Lima).",
                duration=3500,
            )
        timezone_db_value = timezone_value or None

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id:
            return rx.toast("Empresa no definida.", duration=3000)
        with rx.session() as session:
            settings_list = session.exec(
                select(CompanySettings)
                .where(CompanySettings.company_id == company_id)
            ).all()
            if settings_list:
                has_branch_settings = False
                for settings in settings_list:
                    settings.company_name = company_name
                    settings.ruc = ruc
                    settings.address = address
                    settings.phone = phone or None
                    settings.footer_message = footer_message or None
                    settings.receipt_paper = receipt_paper
                    settings.receipt_width = receipt_width_value
                    if branch_id:
                        if settings.branch_id == branch_id:
                            settings.timezone = timezone_db_value
                            has_branch_settings = True
                    else:
                        settings.timezone = timezone_db_value
                    session.add(settings)
                if branch_id and not has_branch_settings:
                    session.add(
                        CompanySettings(
                            company_id=company_id,
                            branch_id=branch_id,
                            company_name=company_name,
                            ruc=ruc,
                            address=address,
                            phone=phone or None,
                            footer_message=footer_message or None,
                            receipt_paper=receipt_paper,
                            receipt_width=receipt_width_value,
                            timezone=timezone_db_value,
                            country_code=self.selected_country_code or "PE",
                            default_currency_code=self.selected_currency_code or "PEN",
                        )
                    )
            else:
                branch_id_value = int(branch_id) if branch_id else 1
                session.add(
                    CompanySettings(
                        company_id=company_id,
                        branch_id=branch_id_value,
                        company_name=company_name,
                        ruc=ruc,
                        address=address,
                        phone=phone or None,
                        footer_message=footer_message or None,
                        receipt_paper=receipt_paper,
                        receipt_width=receipt_width_value,
                        timezone=timezone_db_value,
                    )
                )
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
        self.timezone = timezone_value
        self.company_form_key += 1
        return rx.toast("Configuracion de empresa guardada.", duration=2500)

    @rx.event
    def go_to_config_tab(self, tab: str):
        return rx.redirect(f"/configuracion?tab={tab}")

    def add_unit(self):
        toast = self._require_manage_config()
        if toast:
            return toast
        name = self.new_unit_name.strip()
        if not name:
            return
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)

        with rx.session() as session:
            existing = session.exec(
                select(Unit)
                .where(Unit.name == name)
                .where(Unit.company_id == company_id)
                .where(Unit.branch_id == branch_id)
            ).first()
            if not existing:
                session.add(
                    Unit(
                        name=name,
                        allows_decimal=self.new_unit_allows_decimal,
                        company_id=company_id,
                        branch_id=branch_id,
                    )
                )
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
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return
        with rx.session() as session:
            unit = session.exec(
                select(Unit)
                .where(Unit.name == unit_name)
                .where(Unit.company_id == company_id)
                .where(Unit.branch_id == branch_id)
            ).first()
            if unit:
                unit.allows_decimal = allows_decimal
                session.add(unit)
                session.commit()
        self.load_config_data()

    def remove_unit(self, unit_name: str):
        toast = self._require_manage_config()
        if toast:
            return toast
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        with rx.session() as session:
            unit = session.exec(
                select(Unit)
                .where(Unit.name == unit_name)
                .where(Unit.company_id == company_id)
                .where(Unit.branch_id == branch_id)
            ).first()
            if unit:
                session.delete(unit)
                session.commit()
                self.load_config_data()
                return rx.toast(f"Unidad '{unit_name}' eliminada.", duration=2000)

    def ensure_default_data(self):
        """Inicializa datos por defecto basados en el país configurado."""
        config = get_country_config(self.selected_country_code)
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return

        with rx.session() as session:
            # Unidades (universales)
            if not session.exec(
                select(Unit)
                .where(Unit.company_id == company_id)
                .where(Unit.branch_id == branch_id)
            ).first():
                defaults = ["unidad", "pieza", "kg", "g", "l", "ml", "m", "cm", "paquete", "caja", "docena", "bolsa", "botella", "lata"]
                decimals = {"kg", "g", "l", "ml", "m", "cm"}
                for name in defaults:
                    session.add(
                        Unit(
                            name=name,
                            allows_decimal=name in decimals,
                            company_id=company_id,
                            branch_id=branch_id,
                        )
                    )

            # Currencies - basadas en el país configurado
            if not session.exec(select(Currency)).first():
                # Agregar moneda del país actual
                session.add(Currency(
                    code=config["currency"],
                    name=f"{config['currency_name']} ({config['currency']})",
                    symbol=config["currency_symbol"]
                ))
                # Agregar USD como moneda universal si no es la del país
                if config["currency"] != "USD":
                    session.add(Currency(code="USD", name="Dólar estadounidense (USD)", symbol="US$"))

            # Metodos de pago
            existing_methods = {
                method.method_id: method
                for method in session.exec(
                    select(PaymentMethod)
                    .where(PaymentMethod.company_id == company_id)
                    .where(PaymentMethod.branch_id == branch_id)
                ).all()
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
                    "method_id": "debit_card",
                    "name": "Tarjeta de Debito",
                    "description": "Pago con tarjeta debito",
                    "kind": "debit",
                },
                {
                    "method_id": "credit_card",
                    "name": "Tarjeta de Credito",
                    "description": "Pago con tarjeta credito",
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
                        company_id=company_id,
                        branch_id=branch_id,
                    )
                )

            session.commit()
        self.load_config_data()

    new_payment_method_name: str = ""
    new_payment_method_description: str = ""
    new_payment_method_kind: str = "other"

    @rx.var(cache=True)
    def currency_symbol(self) -> str:
        match = next(
            (c for c in self.available_currencies if c["code"] == self.selected_currency_code),
            None,
        )
        if match:
            return f"{match['symbol']} "
        # Fallback dinámico basado en el país
        config = get_country_config(self.selected_country_code)
        return f"{config.get('currency_symbol', '$')} "

    @rx.var(cache=True)
    def currency_name(self) -> str:
        match = next(
            (c for c in self.available_currencies if c["code"] == self.selected_currency_code),
            None,
        )
        if match:
            return match["name"]
        # Fallback dinámico basado en el país
        config = get_country_config(self.selected_country_code)
        return f"{config.get('currency_name', 'Moneda')} ({config.get('currency', 'USD')})"

    def _format_currency(self, value: float) -> str:
        return f"{self.currency_symbol}{self._round_currency(value):.2f}"

    @rx.event
    def set_currency(self, code: str):
        """Establece y persiste la moneda del negocio.

        La moneda se guarda en CompanySettings para que sea global
        para todos los usuarios de la instalación.

        Args:
            code: Código ISO de la moneda (ej: 'PEN', 'USD', 'ARS')
        """
        code = (code or "").upper()
        match = next((c for c in self.available_currencies if c["code"] == code), None)
        if not match:
            return rx.toast("Moneda no soportada.", duration=3000)

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        # Persistir la moneda en la base de datos
        with rx.session() as session:
            settings = session.exec(
                select(CompanySettings)
                .where(CompanySettings.company_id == company_id)
                .where(CompanySettings.branch_id == branch_id)
            ).first()
            if settings:
                settings.default_currency_code = code
                session.add(settings)
            else:
                settings = CompanySettings(
                    company_id=company_id,
                    branch_id=branch_id,
                    default_currency_code=code,
                )
                session.add(settings)
            session.commit()

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
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)

        with rx.session() as session:
            existing_unit = session.exec(
                select(Unit)
                .where(Unit.name == name)
                .where(Unit.company_id == company_id)
                .where(Unit.branch_id == branch_id)
            ).first()
            if existing_unit:
                existing_unit.allows_decimal = self.new_unit_allows_decimal
                session.add(existing_unit)
            else:
                new_unit = Unit(
                    name=name,
                    allows_decimal=self.new_unit_allows_decimal,
                    company_id=company_id,
                    branch_id=branch_id,
                )
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
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        with rx.session() as session:
            unit_db = session.exec(
                select(Unit)
                .where(Unit.name == unit)
                .where(Unit.company_id == company_id)
                .where(Unit.branch_id == branch_id)
            ).first()
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
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
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
                company_id=company_id,
                branch_id=branch_id,
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

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        with rx.session() as session:
            method_db = session.exec(
                select(PaymentMethod)
                .where(PaymentMethod.method_id == method_id)
                .where(PaymentMethod.company_id == company_id)
                .where(PaymentMethod.branch_id == branch_id)
            ).first()
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
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)
        with rx.session() as session:
            method_db = session.exec(
                select(PaymentMethod)
                .where(PaymentMethod.method_id == method_id)
                .where(PaymentMethod.company_id == company_id)
                .where(PaymentMethod.branch_id == branch_id)
            ).first()
            if method_db:
                session.delete(method_db)
                session.commit()

        self.load_config_data()
        self._ensure_payment_method_selected()
        return rx.toast(f"Metodo {method['name']} eliminado.", duration=2500)
