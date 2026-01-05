import reflex as rx
from app.states.root_state import RootState
from app.states.types import (
    Product,
    TransactionItem,
    Movement,
    CurrencyOption,
    PaymentMethodConfig,
    PaymentBreakdownItem,
    FieldPrice,
    FieldReservation,
    ServiceLogEntry,
    ReservationReceipt,
    CashboxSale,
    CashboxSession,
    CashboxLogEntry,
    InventoryAdjustment,
    Privileges,
    NewUser,
    User,
)
from app.states.auth_state import (
    DEFAULT_USER_PRIVILEGES,
    ADMIN_PRIVILEGES,
    CASHIER_PRIVILEGES,
    SUPERADMIN_PRIVILEGES,
    EMPTY_PRIVILEGES,
    DEFAULT_ROLE_TEMPLATES,
)
from app.utils.db import AsyncSessionLocal
from app.utils.db_seeds import init_payment_methods

# Re-export State
class State(RootState):
    """
    Main application state class.
    Now inherits from RootState which combines all modular states.
    """

    notification_message: str = ""
    notification_type: str = "info"
    is_notification_open: bool = False

    @rx.event
    def notify(self, message: str, type: str = "info"):
        normalized_type = (type or "info").strip().lower()
        if normalized_type not in {"success", "error", "warning", "info"}:
            normalized_type = "info"
        self.notification_message = str(message or "")
        self.notification_type = normalized_type
        self.is_notification_open = True

    @rx.event
    def close_notification(self):
        self.is_notification_open = False

    @rx.event
    async def ensure_payment_methods(self):
        async with AsyncSessionLocal() as session:
            await init_payment_methods(session)
