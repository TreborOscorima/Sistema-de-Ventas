"""Cash State — paquete compuesto por mixins de responsabilidad única.

CashState se construye combinando mixins vía herencia múltiple.
El orden de herencia es importante: MRO resuelve de izquierda a derecha.
"""
from typing import List, Dict

from app.enums import SaleStatus
from ..mixin_state import MixinState
from ..types import CashboxSale, CashboxSession, CashboxLogEntry

from ._petty_cash_mixin import PettyCashMixin
from ._session_mixin import SessionMixin
from ._history_mixin import HistoryMixin
from ._close_mixin import CloseMixin
from ._reports_mixin import ReportsMixin
from ._delete_mixin import DeleteMixin


class CashState(
    ReportsMixin,
    DeleteMixin,
    CloseMixin,
    HistoryMixin,
    SessionMixin,
    PettyCashMixin,
    MixinState,
):
    """Estado de gestión de caja registradora.

    Maneja sesiones de caja, movimientos, reportes y exportaciones.
    Requiere permisos 'view_cashbox' y 'manage_cashbox' según la operación.
    """

    # ── State variables (shared across mixins) ───────────────────
    cashbox_filter_start_date: str = ""
    cashbox_filter_end_date: str = ""
    cashbox_staged_start_date: str = ""
    cashbox_staged_end_date: str = ""
    cashbox_current_page: int = 1
    cashbox_items_per_page: int = 5
    show_cashbox_advances: bool = True
    sale_delete_modal_open: bool = False
    sale_to_delete: str = ""
    sale_delete_reason: str = ""
    cashbox_close_modal_open: bool = False
    summary_by_method: list[dict] = []
    cashbox_close_summary_sales: List[CashboxSale] = []
    cashbox_close_summary_date: str = ""
    cashbox_close_opening_amount: float = 0.0
    cashbox_close_income_total: float = 0.0
    cashbox_close_expense_total: float = 0.0
    cashbox_close_expected_total: float = 0.0
    # Arqueo por denominación
    denomination_counts: dict[str, int] = {}
    cashbox_close_counted_total: float = 0.0
    cashbox_logs: List[CashboxLogEntry] = []
    cashbox_log_filter_start_date: str = ""
    cashbox_log_filter_end_date: str = ""
    cashbox_log_staged_start_date: str = ""
    cashbox_log_staged_end_date: str = ""
    cashbox_log_current_page: int = 1
    cashbox_log_items_per_page: int = 10
    cashbox_log_modal_open: bool = False
    cashbox_log_selected: CashboxLogEntry | None = None
    expanded_cashbox_sale_id: str = ""
    petty_cash_movements: List[CashboxLogEntry] = []
    petty_cash_total_pages: int = 1
    filtered_cashbox_logs: list[CashboxLogEntry] = []
    cashbox_log_total_pages: int = 1
    filtered_cashbox_sales: list[CashboxSale] = []
    cashbox_total_pages: int = 1


__all__ = ["CashState"]
