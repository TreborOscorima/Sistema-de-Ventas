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
    runtime_ctx_loaded: bool = False
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

    async def _do_runtime_refresh(self, force: bool = False):
        """Helper interno: refresca caches de runtime SIN yield.

        Al no hacer yield, todo el delta se envía junto al final del
        evento page_init_*, eliminando un roundtrip WS adicional.
        """
        if not self.is_authenticated:
            return

        now = time.time()
        if not force and (now - self._last_runtime_refresh_ts) < self._runtime_refresh_ttl:
            return
        self._last_runtime_refresh_ts = now

        # --- auth + caja + alertas ---
        if hasattr(self, "refresh_auth_runtime_cache"):
            self.refresh_auth_runtime_cache()

        if hasattr(self, "refresh_cashbox_status"):
            self.refresh_cashbox_status()

        if hasattr(self, "check_overdue_alerts"):
            self.check_overdue_alerts()

        self.runtime_ctx_loaded = True

        # --- datos base (solo primer carga) ---
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

    @rx.event
    async def refresh_runtime_context(self, force: bool = False):
        """Evento público de refresco (compatibilidad hacia atrás)."""
        await self._do_runtime_refresh(force)

    # ------------------------------------------------------------------
    # Manejadores consolidados de inicialización de página
    # Fusiona sync_page + ensure_view + cargas específicas de página + common_guards
    # en UN solo evento por página → 1 delta en vez de 3-5 eventos separados.
    # ------------------------------------------------------------------

    def _check_auth_and_privilege(self, privilege_key: str, deny_msg: str):
        """Retorna eventos de redirección si el acceso es denegado, sino None."""
        if not self.is_authenticated:
            return [rx.redirect("/ingreso")]
        if not self.current_user["privileges"].get(privilege_key):
            return [
                rx.toast(deny_msg, duration=3000),
                rx.redirect("/dashboard"),
            ]
        return None

    @rx.event
    async def page_init_default(self):
        """on_load para / y /dashboard (sin restricción de privilegio)."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        # Delta parcial: renderiza la UI de inmediato
        yield

    @rx.event
    async def page_init_ingreso(self):
        """on_load para /ingreso. Verifica autenticación y privilegio view_ingresos."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        if not self.is_authenticated:
            return  # authenticated_layout muestra login_page()
        if not self.current_user["privileges"].get("view_ingresos"):
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Ingresos.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        # Delta parcial: renderiza la UI de inmediato
        yield

    @rx.event
    async def page_init_compras(self):
        """on_load para /compras. Verifica privilegio view_compras y carga proveedores."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
            return
        privileges = self.current_user["privileges"]
        if not (privileges.get("view_compras") or privileges.get("view_ingresos")):
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Compras.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        # Enviar delta parcial (la UI renderiza la página de inmediato)
        yield
        # Cargar proveedores en segundo plano (segundo delta)
        now = time.time()
        if (now - self._last_suppliers_load_ts) >= self._PAGE_DATA_TTL:
            self._last_suppliers_load_ts = now
            self.load_suppliers()

    @rx.event
    async def page_init_venta(self):
        """on_load para /venta. Verifica privilegio view_ventas."""
        await self._do_runtime_refresh()
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
        # Delta parcial: renderiza la UI de inmediato
        yield

    @rx.event
    async def page_init_caja(self):
        """on_load para /caja. Verifica privilegio view_cashbox y carga datos de caja."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        denied = self._check_auth_and_privilege(
            "view_cashbox",
            "Acceso denegado: No tienes permiso para ver Caja.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        # Enviar delta parcial (UI renderiza estructura de caja)
        yield
        # Cargar datos de caja en segundo plano
        now = time.time()
        if (now - self._last_cashbox_data_ts) >= self._PAGE_DATA_TTL:
            self._last_cashbox_data_ts = now
            self.refresh_cashbox_data()

    @rx.event
    async def page_init_clientes(self):
        """on_load para /clientes. Verifica plan y privilegio view_clientes."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
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
        # Delta parcial: renderiza la UI de inmediato
        yield

    @rx.event
    async def page_init_cuentas(self):
        """on_load para /cuentas. Verifica plan y privilegio view_cuentas."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
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
        # Delta parcial: renderiza la UI de inmediato
        yield

    @rx.event
    async def page_init_inventario(self):
        """on_load para /inventario. Verifica privilegio view_inventario."""
        await self._do_runtime_refresh()
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
        # Delta parcial: renderiza la UI de inmediato
        yield

    @rx.event
    async def page_init_historial(self):
        """on_load para /historial. Verifica privilegio view_historial."""
        await self._do_runtime_refresh()
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
        # Delta parcial: renderiza la UI de inmediato
        yield

    @rx.event
    async def page_init_reportes(self):
        """on_load para /reportes. Verifica privilegio export_data."""
        await self._do_runtime_refresh()
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
        # Delta parcial: renderiza la UI de inmediato
        yield

    @rx.event
    async def page_init_servicios(self):
        """on_load para /servicios. Verifica plan, privilegio view_servicios y reservas habilitadas."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
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
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        # Enviar delta parcial (UI renderiza estructura de servicios)
        yield
        # Cargar reservaciones en segundo plano
        now = time.time()
        if (now - self._last_reservations_load_ts) >= self._PAGE_DATA_TTL:
            self._last_reservations_load_ts = now
            self.load_reservations()

    @rx.event
    async def page_init_configuracion(self):
        """on_load para /configuracion. Requiere rol Administrador o Superadmin."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
            return
        if self.current_user["role"] not in ["Superadmin", "Administrador"]:
            yield rx.toast(
                "Acceso denegado: Se requiere nivel de Administrador.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        # Enviar delta parcial (UI renderiza estructura de config)
        yield
        # Cargar usuarios en segundo plano
        now = time.time()
        if (now - self._last_users_load_ts) >= self._PAGE_DATA_TTL:
            self._last_users_load_ts = now
            self.load_users()

    @rx.event
    async def page_init_cambiar_clave(self):
        """on_load para /cambiar-clave."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        redirect = self.ensure_trial_active()
        if redirect:
            yield redirect
            return
        redirect = self.ensure_password_change()
        if redirect:
            yield redirect
        # Delta parcial: renderiza la UI de inmediato
        yield
