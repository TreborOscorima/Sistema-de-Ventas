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

# Re-export State
class State(RootState):
    """
    Main application state class.
    Now inherits from RootState which combines all modular states.
    """
    pass
