import reflex as rx
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any
from .types import CashboxSale, PaymentBreakdownItem

class MixinState:
    def _round_currency(self, value: float) -> float:
        return float(
            Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )

    def _payment_details_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, dict):
            for key in ("summary", "legacy", "label", "method"):
                text = value.get(key)
                if isinstance(text, str) and text.strip():
                    return text
            return str(value)
        if isinstance(value, list):
            return str(value)
        return str(value or "")

    def _wrap_receipt_lines(self, text: str, width: int) -> List[str]:
        if not text:
            return []
        parts = [part.strip() for part in text.splitlines() if part.strip()]
        if not parts:
            return []
        lines: List[str] = []
        for part in parts:
            words = part.split()
            if not words:
                continue
            current = words[0]
            for word in words[1:]:
                if len(current) + 1 + len(word) <= width:
                    current = f"{current} {word}"
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)
        return lines

    def _company_settings_snapshot(self) -> Dict[str, str]:
        defaults = {
            "company_name": "",
            "ruc": "",
            "address": "",
            "phone": "",
            "footer_message": "",
        }
        try:
            from sqlmodel import select
            from app.models import CompanySettings
        except Exception:
            return defaults
        try:
            with rx.session() as session:
                settings = session.exec(select(CompanySettings)).first()
        except Exception:
            return defaults
        if not settings:
            return defaults
        return {
            "company_name": settings.company_name or "",
            "ruc": settings.ruc or "",
            "address": settings.address or "",
            "phone": settings.phone or "",
            "footer_message": settings.footer_message or "",
        }

    @rx.var
    def currency_symbol(self) -> str:
        # Accessing available_currencies and selected_currency_code from RootState
        if not hasattr(self, "available_currencies") or not hasattr(self, "selected_currency_code"):
            return "S/ "
        match = next(
            (c for c in self.available_currencies if c["code"] == self.selected_currency_code),
            None,
        )
        return f"{match['symbol']} " if match else "S/ "

    @rx.var
    def currency_name(self) -> str:
        if not hasattr(self, "available_currencies") or not hasattr(self, "selected_currency_code"):
            return "Sol peruano (PEN)"
        match = next(
            (c for c in self.available_currencies if c["code"] == self.selected_currency_code),
            None,
        )
        return match["name"] if match else "Sol peruano (PEN)"

    def _format_currency(self, value: float) -> str:
        return f"{self.currency_symbol}{self._round_currency(value):.2f}"

    def _unit_allows_decimal(self, unit: str) -> bool:
        # Accessing decimal_units from RootState
        if not hasattr(self, "decimal_units"):
            return False
        return unit and unit.lower() in self.decimal_units

    def _normalize_quantity_value(self, value: float, unit: str) -> float:
        if self._unit_allows_decimal(unit):
            return float(
                Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )
        return int(
            Decimal(str(value or 0)).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )

    def _normalize_wallet_label(self, label: str) -> str:
        value = (label or "").strip()
        if not value:
            return value
        key = value.lower()
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
        if key in mapping:
            return mapping[key]
        if key == "card":
            return mapping["credit"]
        if key == "wallet":
            return mapping["yape"]
        if "mixto" in key and "(" in value and ")" in value:
            suffix = value[value.find("("):].strip()
            return f"{mapping['mixed']} {suffix}"
        if "mixto" in key:
            return mapping["mixed"]
        if "debito" in key or "débito" in key:
            return mapping["debit"]
        if "credito" in key or "crédito" in key or "tarjeta" in key:
            return mapping["credit"]
        if "yape" in key:
            return mapping["yape"]
        if "plin" in key:
            return mapping["plin"]
        if "billetera" in key or "qr" in key:
            return mapping["yape"]
        if "transfer" in key or "banco" in key:
            return mapping["transfer"]
        if "efectivo" in key:
            return mapping["cash"]
        return value

    def _payment_category(self, method: str, kind: str = "") -> str:
        normalized_kind = (kind or "").lower()
        label = method.lower() if method else ""
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
        if normalized_kind == "mixed" or "mixto" in label:
            return mapping["mixed"]
        if normalized_kind == "debit" or "debito" in label or "débito" in label:
            return mapping["debit"]
        if normalized_kind == "credit" or "credito" in label or "crédito" in label or "tarjeta" in label:
            return mapping["credit"]
        if normalized_kind == "yape" or "yape" in label:
            return mapping["yape"]
        if normalized_kind == "plin" or "plin" in label:
            return mapping["plin"]
        if normalized_kind == "transfer" or "transfer" in label or "banco" in label:
            return mapping["transfer"]
        if normalized_kind == "cash" or "efectivo" in label:
            return mapping["cash"]
        return mapping["other"]

    def _ensure_sale_payment_fields(self, sale: CashboxSale):
        if "payment_label" not in sale or not sale.get("payment_label"):
            sale["payment_label"] = sale.get("payment_method", "Metodo")
        sale["payment_label"] = self._normalize_wallet_label(sale.get("payment_label", ""))
        if (
            "payment_breakdown" not in sale
            or not isinstance(sale.get("payment_breakdown"), list)
            or len(sale.get("payment_breakdown") or []) == 0
        ):
            fallback_label = sale.get("payment_label", sale.get("payment_method", "Metodo"))
            sale["payment_breakdown"] = [
                {
                    "label": self._normalize_wallet_label(fallback_label),
                    "amount": self._round_currency(sale.get("total", 0)),
                }
            ]
        else:
            normalized_items: List[PaymentBreakdownItem] = []
            for item in sale.get("payment_breakdown", []):
                normalized_items.append(
                    {
                        "label": self._normalize_wallet_label(item.get("label", "")),
                        "amount": self._round_currency(item.get("amount", 0)),
                    }
                )
            target_total = self._round_currency(sale.get("total", 0))
            total_applied = sum(item["amount"] for item in normalized_items)
            if target_total > 0 and total_applied > target_total:
                factor = target_total / total_applied if total_applied else 0
                normalized_items = [
                    {
                        "label": item["label"],
                        "amount": self._round_currency(item["amount"] * factor),
                    }
                    for item in normalized_items
                ]
                total_applied = sum(item["amount"] for item in normalized_items)
            if target_total > 0 and normalized_items:
                diff = self._round_currency(target_total - total_applied)
                if diff != 0:
                    normalized_items[0]["amount"] = self._round_currency(
                        normalized_items[0]["amount"] + diff
                    )
            sale["payment_breakdown"] = normalized_items
        # Asegura campo de total de servicio para mostrar en caja
        service_total = sale.get("service_total")
        if service_total is None:
            sale["service_total"] = self._round_currency(sale.get("total", 0))
