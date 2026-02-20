"""Mixin para mostrar movimientos recientes en el punto de venta."""
import reflex as rx
from typing import Any

from app.services.sale_service import SaleService
from app.utils.db import get_async_session
from app.utils.formatting import format_currency, round_currency
from app.states.types import RecentTransaction


class RecentMovesMixin:
    """Mixin para mostrar los movimientos recientes en el punto de venta.

    Muestra las últimas transacciones con formato resumido y permite
    reimprimir comprobantes.
    """

    show_recent_modal: bool = False
    recent_transactions: list[RecentTransaction] = []
    recent_loading: bool = False
    recent_expanded_id: str = ""

    def _format_qty(self, value: Any) -> str:
        try:
            qty = float(value or 0)
        except (TypeError, ValueError):
            return "0"
        if qty.is_integer():
            return str(int(qty))
        return f"{qty:.2f}".rstrip("0").rstrip(".")

    @rx.event
    async def toggle_recent_modal(self, value: bool | None = None):
        should_open = not self.show_recent_modal if value is None else bool(value)
        self.show_recent_modal = should_open
        self.recent_expanded_id = ""
        if not should_open:
            return

        self.recent_loading = True
        self.recent_transactions = []
        yield

        branch_id = self._branch_id() if hasattr(self, "_branch_id") else None
        if not branch_id:
            self.recent_loading = False
            yield rx.toast("Sucursal no definida.", duration=3000)
            return

        company_id = self._company_id() if hasattr(self, "_company_id") else None
        async with get_async_session() as session:
            rows = await SaleService.get_recent_activity(
                session=session,
                branch_id=branch_id,
                limit=15,
                company_id=company_id,
            )

        symbol = getattr(self, "currency_symbol", "S/ ")
        formatted: list[RecentTransaction] = []
        for row in rows:
            amount_value = round_currency(row.get("amount", 0))
            items = row.get("items") or []
            detail_full = row.get("detail_full", "")
            detail_short = row.get("detail_short", detail_full)
            detail_lines: list[dict[str, Any]] = []

            if items:
                for item in items:
                    description = str(item.get("description") or "Producto").strip()
                    qty_display = self._format_qty(item.get("quantity"))
                    unit_price_display = format_currency(
                        round_currency(item.get("unit_price", 0)),
                        symbol,
                    )
                    subtotal_display = format_currency(
                        round_currency(item.get("subtotal", 0)),
                        symbol,
                    )
                    detail_lines.append(
                        {
                            "left": f"{description} {qty_display} x {unit_price_display}",
                            "right": subtotal_display,
                        }
                    )

            formatted.append(
                {
                    "id": str(row.get("id", "")),
                    "timestamp": str(row.get("timestamp", "")),
                    "time": str(row.get("time", "")),
                    "time_display": str(row.get("time", "")),
                    "detail_full": detail_full,
                    "detail_short": detail_short,
                    "client": str(row.get("client", "")),
                    "client_display": row.get("client") or "-",
                    "amount": amount_value,
                    "amount_display": format_currency(amount_value, symbol),
                    "sale_id": str(row.get("sale_id", "")),
                    "detail_lines": detail_lines,
                }
            )

        self.recent_transactions = formatted
        self.recent_loading = False

    @rx.event
    def toggle_recent_detail(self, log_id: str):
        value = str(log_id or "").strip()
        if not value:
            return
        if self.recent_expanded_id == value:
            self.recent_expanded_id = ""
        else:
            self.recent_expanded_id = value

    @rx.event
    def reprint_recent_sale(self, sale_id: str | None):
        sale_value = str(sale_id or "").strip()
        if not sale_value:
            return rx.toast("No hay comprobante para reimprimir.", duration=2500)
        return self.print_sale_receipt_by_id(sale_value)
