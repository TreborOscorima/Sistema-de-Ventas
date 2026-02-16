import reflex as rx
import time
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

# Reexportar State
class State(RootState):
    """
    Clase principal de estado de la aplicacion.
    Ahora hereda de RootState, que combina todos los estados modulares.
    """

    notification_message: str = ""
    notification_type: str = "info"
    is_notification_open: bool = False
    _last_runtime_refresh_ts: float = rx.field(default=0.0, is_var=False)
    _runtime_refresh_ttl: float = 30.0

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
        company_id = None
        if hasattr(self, "current_user"):
            company_id = self.current_user.get("company_id")
        branch_id = None
        if hasattr(self, "_branch_id"):
            branch_id = self._branch_id()
        if not company_id or not branch_id:
            return
        async with AsyncSessionLocal() as session:
            await init_payment_methods(session, int(company_id), int(branch_id))

    @rx.event
    async def refresh_runtime_context(self, force: bool = False):
        """Carga caches y datos base con baja frecuencia para navegación fluida.

        Usa yield para enviar deltas parciales y que el UI responda
        progresivamente en vez de esperar a que termine todo.
        """
        if not self.is_authenticated:
            return

        now = time.time()
        if not force and (now - self._last_runtime_refresh_ts) < self._runtime_refresh_ttl:
            return
        self._last_runtime_refresh_ts = now

        # --- Bloque 1: auth (permisos, sidebar, badge trial) ---
        if hasattr(self, "refresh_auth_runtime_cache"):
            self.refresh_auth_runtime_cache()
        yield  # delta parcial: permisos + sidebar actualizados

        # --- Bloque 2: caja + alertas (badge sidebar) ---
        if hasattr(self, "refresh_cashbox_status"):
            self.refresh_cashbox_status()

        if hasattr(self, "check_overdue_alerts"):
            self.check_overdue_alerts()
        yield  # delta parcial: estado de caja + alertas

        # --- Bloque 3: datos base (solo primer carga) ---
        seeded_defaults = False
        if hasattr(self, "units") and not self.units and hasattr(self, "ensure_default_data"):
            self.ensure_default_data()
            seeded_defaults = True

        if hasattr(self, "categories") and not self.categories and hasattr(self, "load_categories"):
            self.load_categories()

        if hasattr(self, "field_prices") and not self.field_prices and hasattr(self, "load_field_prices"):
            self.load_field_prices()

        if (
            not seeded_defaults
            and hasattr(self, "available_currencies")
            and hasattr(self, "payment_methods")
            and (not self.available_currencies or not self.payment_methods)
        ):
            await self.ensure_payment_methods()
            if hasattr(self, "load_config_data"):
                self.load_config_data()
