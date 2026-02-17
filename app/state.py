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
    _runtime_ctx_loaded: bool = False
    _last_runtime_refresh_ts: float = rx.field(default=0.0, is_var=False)
    _runtime_refresh_ttl: float = 30.0

    # TTL para cargas de datos de página (evita recargas innecesarias en nav SPA)
    _last_suppliers_load_ts: float = 0.0
    _last_reservations_load_ts: float = 0.0
    _last_users_load_ts: float = 0.0
    _last_cashbox_data_ts: float = 0.0
    _PAGE_DATA_TTL: float = 15.0

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

        # --- Bloque 1: auth + caja + alertas (un solo delta) ---
        if hasattr(self, "refresh_auth_runtime_cache"):
            self.refresh_auth_runtime_cache()

        if hasattr(self, "refresh_cashbox_status"):
            self.refresh_cashbox_status()

        if hasattr(self, "check_overdue_alerts"):
            self.check_overdue_alerts()

        self._runtime_ctx_loaded = True
        yield  # delta parcial: permisos + caja + alertas (todo junto)

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

    # ------------------------------------------------------------------
    # Consolidated page-init handlers
    # Merge sync_page + ensure_view + page-specific loads + common_guards
    # into ONE event per page → 1 delta instead of 3-5 separate events.
    # ------------------------------------------------------------------

    def _check_auth_and_privilege(self, privilege_key: str, deny_msg: str):
        """Helper: returns redirect events if denied, else None."""
        if not self.is_authenticated:
            return [rx.redirect("/")]
        if not self.current_user["privileges"].get(privilege_key):
            return [
                rx.toast(deny_msg, duration=3000),
                rx.redirect("/dashboard"),
            ]
        return None

    @rx.event
    def page_init_default(self):
        """on_load for / and /dashboard (no privilege gate)."""
        self.sync_page_from_route()
        redirect = self.run_common_guards()
        if redirect:
            yield redirect

    @rx.event
    def page_init_ingreso(self):
        self.sync_page_from_route()
        denied = self._check_auth_and_privilege(
            "view_ingresos",
            "Acceso denegado: No tienes permiso para ver Ingresos.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect

    @rx.event
    def page_init_compras(self):
        self.sync_page_from_route()
        if not self.is_authenticated:
            yield rx.redirect("/")
            return
        privileges = self.current_user["privileges"]
        if not (privileges.get("view_compras") or privileges.get("view_ingresos")):
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Compras.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")
            return
        # load_suppliers con TTL (solo recarga on_load)
        now = time.time()
        if (now - self._last_suppliers_load_ts) >= self._PAGE_DATA_TTL:
            self._last_suppliers_load_ts = now
            self.load_suppliers()
        redirect = self.run_common_guards()
        if redirect:
            yield redirect

    @rx.event
    def page_init_venta(self):
        self.sync_page_from_route()
        denied = self._check_auth_and_privilege(
            "view_ventas",
            "Acceso denegado: No tienes permiso para ver Ventas.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect

    @rx.event
    def page_init_caja(self):
        self.sync_page_from_route()
        denied = self._check_auth_and_privilege(
            "view_cashbox",
            "Acceso denegado: No tienes permiso para ver Caja.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        # refresh_cashbox_data con TTL
        now = time.time()
        if (now - self._last_cashbox_data_ts) >= self._PAGE_DATA_TTL:
            self._last_cashbox_data_ts = now
            self.refresh_cashbox_data()
        redirect = self.run_common_guards()
        if redirect:
            yield redirect

    @rx.event
    def page_init_clientes(self):
        self.sync_page_from_route()
        if not self.is_authenticated:
            yield rx.redirect("/")
            return
        # can_view_clientes inline: plan != standard + privilege
        plan = (self.plan_actual or "").strip().lower()
        if plan == "standard" or not self.current_user["privileges"].get("view_clientes"):
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Clientes.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect

    @rx.event
    def page_init_cuentas(self):
        self.sync_page_from_route()
        if not self.is_authenticated:
            yield rx.redirect("/")
            return
        plan = (self.plan_actual or "").strip().lower()
        if plan == "standard" or not self.current_user["privileges"].get("view_cuentas"):
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Cuentas.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect

    @rx.event
    def page_init_inventario(self):
        self.sync_page_from_route()
        denied = self._check_auth_and_privilege(
            "view_inventario",
            "Acceso denegado: No tienes permiso para ver Inventario.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect

    @rx.event
    def page_init_historial(self):
        self.sync_page_from_route()
        denied = self._check_auth_and_privilege(
            "view_historial",
            "Acceso denegado: No tienes permiso para ver Historial.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect

    @rx.event
    def page_init_reportes(self):
        self.sync_page_from_route()
        denied = self._check_auth_and_privilege(
            "export_data",
            "Acceso denegado: No tienes permiso para exportar reportes.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect

    @rx.event
    def page_init_servicios(self):
        self.sync_page_from_route()
        if not self.is_authenticated:
            yield rx.redirect("/")
            return
        # can_view_servicios inline
        plan = (self.plan_actual or "").strip().lower()
        has_privilege = self.current_user["privileges"].get("view_servicios")
        has_reservations = self.company_has_reservations
        if plan == "standard" or not (has_privilege and has_reservations):
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Servicios.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")
            return
        # load_reservations con TTL
        now = time.time()
        if (now - self._last_reservations_load_ts) >= self._PAGE_DATA_TTL:
            self._last_reservations_load_ts = now
            self.load_reservations()
        redirect = self.run_common_guards()
        if redirect:
            yield redirect

    @rx.event
    def page_init_configuracion(self):
        self.sync_page_from_route()
        if not self.is_authenticated:
            yield rx.redirect("/")
            return
        if self.current_user["role"] not in ["Superadmin", "Administrador"]:
            yield rx.toast(
                "Acceso denegado: Se requiere nivel de Administrador.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")
            return
        # load_users con TTL
        now = time.time()
        if (now - self._last_users_load_ts) >= self._PAGE_DATA_TTL:
            self._last_users_load_ts = now
            self.load_users()
        redirect = self.run_common_guards()
        if redirect:
            yield redirect

    @rx.event
    def page_init_cambiar_clave(self):
        """on_load for /cambiar-clave."""
        self.sync_page_from_route()
        redirect = self.ensure_trial_active()
        if redirect:
            yield redirect
            return
        redirect = self.ensure_password_change()
        if redirect:
            yield redirect
