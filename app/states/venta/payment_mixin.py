import uuid
from typing import List

import reflex as rx
from sqlmodel import select

from app.models import PaymentMethod
from ..types import PaymentBreakdownItem, PaymentMethodConfig


class PaymentMixin:
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
                    "enabled": m.enabled,
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
    payment_mixed_non_cash_kind: str = "credit"
    payment_mixed_message: str = ""
    payment_mixed_status: str = "neutral"
    payment_mixed_notes: str = ""
    new_payment_method_name: str = ""
    new_payment_method_description: str = ""
    new_payment_method_kind: str = "other"

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

    def _payment_method_by_identifier(
        self, identifier: str
    ) -> PaymentMethodConfig | None:
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
        mapping = {
            "debit": "Tarjeta de Débito",
            "credit": "Tarjeta de Crédito",
            "yape": "Billetera Digital (Yape)",
            "plin": "Billetera Digital (Plin)",
            "transfer": "Transferencia Bancaria",
        }
        if kind == "cash":
            detail = f"Monto {self._format_currency(self.payment_cash_amount)}"
            if self.payment_cash_message:
                detail += f" ({self.payment_cash_message})"
            return f"{method} - {detail}"
        if kind in ["debit", "credit", "yape", "plin", "transfer"]:
            return mapping.get(kind, method)
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
            non_cash_kind = (self.payment_mixed_non_cash_kind or "").lower()
            parts = []
            if self.payment_mixed_cash > 0:
                parts.append(f"Efectivo {self._format_currency(self.payment_mixed_cash)}")
            if self.payment_mixed_card > 0:
                card_label = mapping.get(
                    non_cash_kind,
                    f"Tarjeta ({self.payment_card_type})",
                )
                parts.append(
                    f"{card_label} {self._format_currency(self.payment_mixed_card)}"
                )
            if self.payment_mixed_wallet > 0:
                provider = (
                    self.payment_wallet_provider
                    or self.payment_wallet_choice
                    or "Billetera"
                )
                wallet_label = mapping.get(non_cash_kind, provider)
                parts.append(
                    f"{wallet_label} {self._format_currency(self.payment_mixed_wallet)}"
                )
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
            # Accediendo a selected_reservation_balance desde ServicesState (via RootState)
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
        if self.payment_mixed_non_cash_kind in ["wallet", "yape", "plin"]:
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
            kind = (method.get("kind", "other") or "other").lower()
            self.payment_method_kind = kind
        else:
            self.payment_method = ""
            self.payment_method_description = ""
            kind = "other"
            self.payment_method_kind = kind
        self.payment_cash_amount = 0
        self.payment_cash_message = ""
        self.payment_cash_status = "neutral"
        if kind == "debit":
            self.payment_card_type = "Debito"
        else:
            self.payment_card_type = "Credito"
        if kind == "plin":
            self.payment_wallet_choice = "Plin"
            self.payment_wallet_provider = "Plin"
        else:
            self.payment_wallet_choice = "Yape"
            self.payment_wallet_provider = "Yape"
        self.payment_mixed_cash = 0
        self.payment_mixed_card = 0
        self.payment_mixed_wallet = 0
        self.payment_mixed_non_cash_kind = "credit"
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
        if (
            self.payment_method_kind == "mixed"
            and self.payment_mixed_non_cash_kind in ["card", "debit", "credit", "transfer"]
        ):
            self._auto_allocate_mixed_amounts()
            self._update_mixed_message()

    @rx.event
    def choose_wallet_provider(self, provider: str):
        self.payment_wallet_choice = provider
        if provider == "Otro":
            self.payment_wallet_provider = ""
        else:
            self.payment_wallet_provider = provider
        if (
            self.payment_method_kind == "mixed"
            and self.payment_mixed_non_cash_kind in ["wallet", "yape", "plin"]
        ):
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
        if kind not in [
            "card",
            "wallet",
            "debit",
            "credit",
            "yape",
            "plin",
            "transfer",
        ]:
            return
        if kind == "debit":
            self.payment_card_type = "Debito"
        elif kind == "credit":
            self.payment_card_type = "Credito"
        elif kind == "yape":
            self.payment_wallet_choice = "Yape"
            self.payment_wallet_provider = "Yape"
        elif kind == "plin":
            self.payment_wallet_choice = "Plin"
            self.payment_wallet_provider = "Plin"
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

    def _payment_label_and_breakdown(
        self, sale_total: float
    ) -> tuple[str, list[PaymentBreakdownItem]]:
        kind = (self.payment_method_kind or "other").lower()
        method_name = self._normalize_wallet_label(self.payment_method or "Metodo")
        breakdown: list[PaymentBreakdownItem] = []
        label = method_name
        mapping = {
            "cash": "Efectivo",
            "debit": "Tarjeta de Débito",
            "credit": "Tarjeta de Crédito",
            "yape": "Billetera Digital (Yape)",
            "plin": "Billetera Digital (Plin)",
            "transfer": "Transferencia Bancaria",
            "mixed": "Pago Mixto",
            "other": "Otros",
        }
        if kind == "cash":
            label = mapping["cash"]
            breakdown = [{"label": label, "amount": self._round_currency(sale_total)}]
        elif kind in ["debit", "credit", "yape", "plin", "transfer"]:
            label = mapping[kind]
            breakdown = [{"label": label, "amount": self._round_currency(sale_total)}]
        elif kind == "card":
            card_type = (self.payment_card_type or "").lower()
            label = mapping["debit"] if "deb" in card_type else mapping["credit"]
            breakdown = [{"label": label, "amount": self._round_currency(sale_total)}]
        elif kind == "wallet":
            provider = (
                self.payment_wallet_provider
                or self.payment_wallet_choice
                or "Billetera"
            )
            provider_key = provider.strip().lower()
            if "plin" in provider_key:
                label = mapping["plin"]
            else:
                label = mapping["yape"]
            breakdown = [{"label": label, "amount": self._round_currency(sale_total)}]
        elif kind == "mixed":
            paid_cash = self._round_currency(self.payment_mixed_cash)
            paid_card = self._round_currency(self.payment_mixed_card)
            paid_wallet = self._round_currency(self.payment_mixed_wallet)
            non_cash_kind = (self.payment_mixed_non_cash_kind or "").lower()
            remaining = self._round_currency(sale_total)
            parts: list[PaymentBreakdownItem] = []

            if paid_card > 0:
                applied_card = min(paid_card, remaining)
                if applied_card > 0:
                    if non_cash_kind in ["debit", "credit", "transfer"]:
                        card_label = mapping[non_cash_kind]
                    elif non_cash_kind == "card":
                        card_type = (self.payment_card_type or "").lower()
                        card_label = (
                            mapping["debit"]
                            if "deb" in card_type
                            else mapping["credit"]
                        )
                    else:
                        card_label = mapping["credit"]
                    parts.append(
                        {
                            "label": card_label,
                            "amount": self._round_currency(applied_card),
                        }
                    )
                    remaining = self._round_currency(remaining - applied_card)

            if paid_wallet > 0 and remaining > 0:
                applied_wallet = min(paid_wallet, remaining)
                if applied_wallet > 0:
                    if non_cash_kind in ["yape", "plin"]:
                        wallet_label = mapping[non_cash_kind]
                    elif non_cash_kind == "wallet":
                        provider = (
                            self.payment_wallet_provider
                            or self.payment_wallet_choice
                            or "Billetera"
                        )
                        provider_key = provider.strip().lower()
                        wallet_label = (
                            mapping["plin"]
                            if "plin" in provider_key
                            else mapping["yape"]
                        )
                    else:
                        wallet_label = mapping["yape"]
                    parts.append(
                        {
                            "label": wallet_label,
                            "amount": self._round_currency(applied_wallet),
                        }
                    )
                    remaining = self._round_currency(remaining - applied_wallet)

            if paid_cash > 0 and remaining > 0:
                applied_cash = min(paid_cash, remaining)
                if applied_cash > 0:
                    parts.append(
                        {
                            "label": mapping["cash"],
                            "amount": self._round_currency(applied_cash),
                        }
                    )
                    remaining = self._round_currency(remaining - applied_cash)

            if not parts:
                breakdown = [
                    {"label": mapping["mixed"], "amount": self._round_currency(sale_total)}
                ]
            else:
                if remaining > 0:
                    parts[0]["amount"] = self._round_currency(
                        parts[0]["amount"] + remaining
                    )
                breakdown = parts
            labels = [p["label"] for p in breakdown]
            detail = ", ".join(labels) if labels else mapping["mixed"]
            label = f"{mapping['mixed']} ({detail})"
        else:
            label = method_name or mapping["other"]
            breakdown = [{"label": label, "amount": self._round_currency(sale_total)}]
        return label, breakdown
