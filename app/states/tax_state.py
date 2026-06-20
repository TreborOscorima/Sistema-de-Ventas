"""Estado de configuración de impuestos por empresa.

Gestiona CRUD de ``CompanyTaxRate`` y el toggle ``show_tax_on_receipt``
de ``CompanySettings``.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

import reflex as rx
from sqlmodel import select

from app.models.sales import CompanySettings
from app.models.taxes import CompanyTaxRate
from app.services import tax_service
from app.utils.formatting import fmt_input_num
from app.utils.tax_presets import COUNTRY_TAX_PRESETS, get_presets_for_country

from .mixin_state import MixinState

_MAX_TAX_RATE = Decimal("100")
_MIN_TAX_RATE = Decimal("0")


class TaxConfigState(MixinState):
    """Administra las tasas de impuesto configurables por empresa."""

    # Lista de tasas activas (serializada para Reflex)
    tax_rates: List[Dict[str, Any]] = []

    # Toggle del recibo
    show_tax_on_receipt: bool = True

    # Dialog add/edit
    tax_dialog_open: bool = False
    editing_rate_id: int = -1  # -1 = nueva tasa
    editing_tax_name: str = ""
    editing_label: str = ""
    editing_rate_str: str = ""
    editing_is_default: bool = False

    # Diálogo de confirmación de borrado
    delete_confirm_open: bool = False
    deleting_rate_id: int = -1

    tax_config_loading: bool = False
    active_preset_country: str = ""

    # ── Computed vars ──────────────────────────────────────────────────────────

    @rx.var(cache=False)
    def default_tax_display(self) -> str:
        """Texto de la tasa default para el preview: 'IGV (18%)'."""
        for r in self.tax_rates:
            if r.get("is_default"):
                return f"{r['tax_name']} ({r['rate']}%)"
        if self.tax_rates:
            r = self.tax_rates[0]
            return f"{r['tax_name']} ({r['rate']}%)"
        return "Sin impuesto configurado"

    @rx.var(cache=False)
    def default_tax_rate_decimal(self) -> float:
        """Tasa default en fracción decimal (ej. 0.18) para el preview."""
        for r in self.tax_rates:
            if r.get("is_default"):
                try:
                    return float(r["rate"]) / 100.0
                except (TypeError, ValueError):
                    return 0.0
        if self.tax_rates:
            try:
                return float(self.tax_rates[0]["rate"]) / 100.0
            except (TypeError, ValueError):
                return 0.0
        return 0.0

    @rx.var(cache=False)
    def preview_tax_amount(self) -> str:
        """Monto de impuesto para S/100.00 con la tasa default."""
        return fmt_input_num(100.0 * self.default_tax_rate_decimal)

    @rx.var(cache=False)
    def preview_total(self) -> str:
        """Total para S/100.00 con la tasa default."""
        return fmt_input_num(100.0 * (1 + self.default_tax_rate_decimal))

    @rx.var(cache=False)
    def editing_is_new(self) -> bool:
        return self.editing_rate_id == -1

    # ── Carga ──────────────────────────────────────────────────────────────────

    def _detect_preset_country(self, rates: list) -> str:
        """Detecta qué preset de país coincide con las tasas actuales (por tax_name + rate)."""
        for code, presets in COUNTRY_TAX_PRESETS.items():
            if len(presets) != len(rates):
                continue
            try:
                sorted_presets = sorted(presets, key=lambda x: float(x["rate"]), reverse=True)
                sorted_rates = sorted(rates, key=lambda x: float(x["rate"]), reverse=True)
                if all(
                    str(p["tax_name"]).upper() == str(r["tax_name"]).upper()
                    and Decimal(str(p["rate"])) == Decimal(str(r["rate"]))
                    for p, r in zip(sorted_presets, sorted_rates)
                ):
                    return code
            except Exception:
                continue
        return ""

    @rx.event
    def load_tax_config(self):
        """Carga tasas y show_tax_on_receipt desde DB."""
        company_id = self._company_id()
        if not company_id:
            return
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            rates = tax_service.get_company_tax_rates(company_id, session)
            self.tax_rates = [
                {
                    "id": r.id,
                    "tax_name": r.tax_name,
                    "label": r.label,
                    "rate": fmt_input_num(float(r.rate or 0)),
                    "is_default": r.is_default,
                    "display_order": r.display_order,
                }
                for r in rates
            ]
            self.active_preset_country = self._detect_preset_country(self.tax_rates)
            # Leer show_tax_on_receipt desde CompanySettings
            settings = session.exec(
                select(CompanySettings).where(
                    CompanySettings.company_id == company_id
                )
            ).first()
            if settings and hasattr(settings, "show_tax_on_receipt"):
                self.show_tax_on_receipt = bool(settings.show_tax_on_receipt)

    # ── Toggle show_tax_on_receipt ─────────────────────────────────────────────

    @rx.event
    def set_show_tax_on_receipt(self, value: bool):
        toast = self._require_manage_config()
        if toast:
            return toast
        company_id = self._company_id()
        if not company_id:
            return
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            settings_list = session.exec(
                select(CompanySettings).where(
                    CompanySettings.company_id == company_id
                )
            ).all()
            for settings in settings_list:
                settings.show_tax_on_receipt = bool(value)
                session.add(settings)
            session.commit()
        self.show_tax_on_receipt = bool(value)

    # ── Dialog add/edit ────────────────────────────────────────────────────────

    @rx.event
    def open_add_tax_dialog(self):
        self.editing_rate_id = -1
        self.editing_tax_name = ""
        self.editing_label = ""
        self.editing_rate_str = ""
        self.editing_is_default = len(self.tax_rates) == 0
        self.tax_dialog_open = True

    @rx.event
    def open_edit_tax_dialog(self, rate_id: int):
        for r in self.tax_rates:
            if r["id"] == rate_id:
                self.editing_rate_id = rate_id
                self.editing_tax_name = r["tax_name"]
                self.editing_label = r["label"]
                self.editing_rate_str = str(r["rate"])
                self.editing_is_default = bool(r["is_default"])
                self.tax_dialog_open = True
                return

    @rx.event
    def close_tax_dialog(self):
        self.tax_dialog_open = False

    @rx.event
    def set_editing_tax_name(self, value: str):
        self.editing_tax_name = (value or "").upper().strip()[:20]

    @rx.event
    def set_editing_label(self, value: str):
        self.editing_label = (value or "").strip()[:50]

    @rx.event
    def set_editing_rate_str(self, value: str):
        self.editing_rate_str = value or ""

    @rx.event
    def set_editing_is_default(self, value: bool):
        self.editing_is_default = bool(value)

    @rx.event
    def save_tax_rate(self):
        toast = self._require_manage_config()
        if toast:
            return toast
        company_id = self._company_id()
        if not company_id:
            return rx.toast("Empresa no definida.", duration=3000)

        tax_name = self.editing_tax_name.strip()
        label = self.editing_label.strip()
        rate_str = self.editing_rate_str.strip().replace(",", ".")

        if not tax_name:
            return rx.toast("El nombre del impuesto es obligatorio.", duration=3000)
        if not label:
            return rx.toast("La etiqueta es obligatoria.", duration=3000)
        try:
            rate = Decimal(rate_str)
        except (InvalidOperation, ValueError):
            return rx.toast("El porcentaje debe ser un número válido.", duration=3000)
        if rate < _MIN_TAX_RATE or rate > _MAX_TAX_RATE:
            return rx.toast("El porcentaje debe estar entre 0 y 100.", duration=3000)

        rate_id = self.editing_rate_id if self.editing_rate_id != -1 else None
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            tax_service.upsert_tax_rate(
                company_id=company_id,
                tax_name=tax_name,
                label=label,
                rate=rate,
                is_default=self.editing_is_default,
                session=session,
                rate_id=rate_id,
            )
            session.commit()

        self.tax_dialog_open = False
        self.load_tax_config()
        action = "actualizada" if rate_id else "agregada"
        return rx.toast(f"Tasa {action} correctamente.", duration=2500)

    # ── Borrado ────────────────────────────────────────────────────────────────

    @rx.event
    def confirm_delete_tax_rate(self, rate_id: int):
        self.deleting_rate_id = rate_id
        self.delete_confirm_open = True

    @rx.event
    def close_delete_confirm(self):
        self.delete_confirm_open = False
        self.deleting_rate_id = -1

    @rx.event
    def execute_delete_tax_rate(self):
        toast = self._require_manage_config()
        if toast:
            return toast
        company_id = self._company_id()
        rate_id = self.deleting_rate_id
        if not company_id or rate_id == -1:
            return
        if len(self.tax_rates) <= 1:
            return rx.toast(
                "No se puede eliminar la última tasa activa.", duration=3500
            )
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            tax_service.delete_tax_rate(rate_id, company_id, session)
            session.commit()
        self.delete_confirm_open = False
        self.deleting_rate_id = -1
        self.load_tax_config()
        return rx.toast("Tasa eliminada.", duration=2000)

    # ── Set default ────────────────────────────────────────────────────────────

    @rx.event
    def set_as_default_rate(self, rate_id: int):
        toast = self._require_manage_config()
        if toast:
            return toast
        company_id = self._company_id()
        if not company_id:
            return
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            tax_service.set_default_rate(rate_id, company_id, session)
            session.commit()
        self.load_tax_config()

    # ── Presets de país ────────────────────────────────────────────────────────

    @rx.event
    def apply_country_presets(self, country_code: str):
        toast = self._require_manage_config()
        if toast:
            return toast
        company_id = self._company_id()
        if not company_id:
            return
        code = (country_code or "PE").upper()
        with rx.session() as session:
            session.info["tenant_bypass"] = True
            tax_service.initialize_country_defaults(company_id, code, session)
            session.commit()
        self.load_tax_config()
        self.active_preset_country = code
        presets = get_presets_for_country(code)
        tax_name = presets[0]["tax_name"] if presets else "IVA"
        return rx.toast(
            f"Tasas de {code} cargadas ({tax_name}).", duration=2500
        )
