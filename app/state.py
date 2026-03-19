import os
import datetime

import reflex as rx
import time
from sqlmodel import select
from sqlalchemy import func, or_
from app.models import Supplier, FieldReservation as FieldReservationModel
from app.enums import ReservationStatus
from app.utils.sanitization import escape_like
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
from app.utils.db import AsyncSessionLocal, get_async_session
from app.utils.db_seeds import init_payment_methods

APP_SURFACE: str = (os.getenv("APP_SURFACE") or "all").strip().lower()
if APP_SURFACE not in {"all", "landing", "app", "owner"}:
    APP_SURFACE = "all"

OWNER_ROOT_PATH: str = "/" if APP_SURFACE == "owner" else "/owner"
OWNER_LOGIN_PATH: str = "/login" if APP_SURFACE == "owner" else "/owner/login"

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
    _runtime_refresh_ttl: float = rx.field(default=30.0, is_var=False)

    # TTL para cargas de datos de página (evita recargas innecesarias en nav SPA)
    _last_suppliers_load_ts: float = rx.field(default=0.0, is_var=False)
    _last_reservations_load_ts: float = rx.field(default=0.0, is_var=False)
    _last_users_load_ts: float = rx.field(default=0.0, is_var=False)
    _last_cashbox_data_ts: float = rx.field(default=0.0, is_var=False)
    _last_config_data_load_ts: float = rx.field(default=0.0, is_var=False)
    _PAGE_DATA_TTL: float = rx.field(default=15.0, is_var=False)

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
        # Forzar refresh si subscription_snapshot está vacío (plan no cargado)
        snapshot_empty = not (self.subscription_snapshot or {}).get("plan_type")
        if not force and not snapshot_empty and (now - self._last_runtime_refresh_ts) < self._runtime_refresh_ttl:
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

        categories_loaded = getattr(self, "_categories_loaded_once", False)
        if (
            hasattr(self, "categories")
            and hasattr(self, "load_categories")
            and (force or not categories_loaded or not self.categories)
        ):
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
            self._refresh_payment_config_with_ttl(force=True)

    @rx.event
    async def refresh_runtime_context(self, force: bool = False):
        """Evento público de refresco (compatibilidad hacia atrás)."""
        await self._do_runtime_refresh(force)

    def _refresh_payment_config_with_ttl(self, force: bool = False):
        """Recarga configuración de pagos solo cuando vence TTL o forzado."""
        if not hasattr(self, "load_config_data"):
            return
        now = time.time()
        should_reload = force or (now - self._last_config_data_load_ts) >= self._PAGE_DATA_TTL
        if should_reload:
            self._last_config_data_load_ts = now
            self.load_config_data()

    # ------------------------------------------------------------------
    # Background data-loading methods (Phase 2)
    # Liberan el event loop mientras cargan datos de página.
    # El handler page_init_* hace yield (delta parcial → UI render)
    # y luego dispara el background event que carga sin bloquear.
    # ------------------------------------------------------------------

    @rx.event(background=True)
    async def bg_load_suppliers(self):
        """Background: carga proveedores para /compras.

        Patrón async óptimo: lee params con lock → async query sin lock → actualiza con lock.
        Minimiza el tiempo que el state lock bloquea otros eventos del usuario.
        """
        # 1° Leer parámetros (rápido, sin IO)
        async with self:
            now = time.time()
            if (now - self._last_suppliers_load_ts) < self._PAGE_DATA_TTL:
                return
            self._last_suppliers_load_ts = now
            company_id = self._company_id()
            branch_id = self._branch_id()
            term = (self.supplier_search_query or "").strip()
            if not company_id or not branch_id:
                self.suppliers = []
                return

        # 2° Query async SIN state lock (event loop libre)
        async with get_async_session() as session:
            query = (
                select(Supplier)
                .where(Supplier.company_id == company_id)
                .where(Supplier.branch_id == branch_id)
            )
            if term:
                like = f"%{escape_like(term)}%"
                query = query.where(
                    or_(
                        Supplier.name.ilike(like),
                        Supplier.tax_id.ilike(like),
                        Supplier.phone.ilike(like),
                        Supplier.email.ilike(like),
                    )
                )
            query = query.order_by(Supplier.name)
            results = (await session.exec(query)).all()
            suppliers_data = [
                {
                    "id": s.id,
                    "name": s.name,
                    "tax_id": s.tax_id,
                    "phone": s.phone,
                    "address": s.address,
                    "email": s.email,
                    "is_active": s.is_active,
                }
                for s in results
            ]

        # 3° Actualizar estado (rápido, sin IO)
        async with self:
            self.suppliers = suppliers_data

    @rx.event(background=True)
    async def bg_refresh_cashbox_data(self):
        """Background: recarga datos de caja para /caja."""
        async with self:
            now = time.time()
            if (now - self._last_cashbox_data_ts) >= self._PAGE_DATA_TTL:
                self._last_cashbox_data_ts = now
                self.refresh_cashbox_data()

    @rx.event(background=True)
    async def bg_load_reservations(self):
        """Background: carga reservaciones para /servicios.

        Patrón async óptimo: lee params con lock → async query sin lock → actualiza con lock.
        """
        # 1° Leer parámetros y validar acceso (rápido)
        async with self:
            now = time.time()
            if (now - self._last_reservations_load_ts) < self._PAGE_DATA_TTL:
                return
            self._last_reservations_load_ts = now
            if not self.current_user["privileges"].get("view_servicios"):
                self.service_reservations = []
                self.reservation_total_count = 0
                return
            company_id = self._company_id()
            branch_id = self._branch_id()
            if not company_id or not branch_id:
                self.service_reservations = []
                self.reservation_total_count = 0
                return
            # Snapshot de filtros
            page = max(self.reservation_current_page, 1)
            per_page = max(self.reservation_items_per_page, 1)
            sport = self.field_rental_sport
            filter_status = self.reservation_filter_status
            search_term = self.reservation_search
            filter_start = self.reservation_filter_start_date
            filter_end = self.reservation_filter_end_date

        # 2° Query async SIN state lock
        async with get_async_session() as session:
            # Construir filtros base
            def _apply_filters(q):
                q = q.where(FieldReservationModel.sport == sport)
                if company_id:
                    q = q.where(FieldReservationModel.company_id == company_id)
                if branch_id:
                    q = q.where(FieldReservationModel.branch_id == branch_id)
                if filter_status != "todos":
                    status_map = {
                        "pending": ReservationStatus.PENDING,
                        "pendiente": ReservationStatus.PENDING,
                        "paid": ReservationStatus.PAID,
                        "pagado": ReservationStatus.PAID,
                        "cancelled": ReservationStatus.CANCELLED,
                        "cancelado": ReservationStatus.CANCELLED,
                        "refunded": ReservationStatus.REFUNDED,
                        "reembolsado": ReservationStatus.REFUNDED,
                    }
                    db_status = status_map.get(filter_status.strip().lower())
                    if db_status is not None:
                        q = q.where(FieldReservationModel.status == db_status)
                if search_term:
                    like = f"%{escape_like(search_term.strip())}%"
                    q = q.where(
                        or_(
                            FieldReservationModel.client_name.ilike(like),
                            FieldReservationModel.field_name.ilike(like),
                        )
                    )
                if filter_start:
                    try:
                        sd = datetime.datetime.strptime(filter_start, "%Y-%m-%d")
                        q = q.where(FieldReservationModel.start_datetime >= sd)
                    except ValueError:
                        pass
                if filter_end:
                    try:
                        ed = datetime.datetime.strptime(filter_end, "%Y-%m-%d")
                        ed = ed.replace(hour=23, minute=59, second=59)
                        q = q.where(FieldReservationModel.start_datetime <= ed)
                    except ValueError:
                        pass
                return q

            count_q = _apply_filters(
                select(func.count()).select_from(FieldReservationModel)
            )
            total_count = (await session.exec(count_q)).one()

            data_q = _apply_filters(
                select(FieldReservationModel)
                .order_by(FieldReservationModel.start_datetime.desc())
            )
            total_pages = 1 if total_count == 0 else (total_count + per_page - 1) // per_page
            if page > total_pages:
                page = total_pages
            data_q = data_q.offset((page - 1) * per_page).limit(per_page)
            reservations = (await session.exec(data_q)).all()

        # 3° Formatear y actualizar estado
        formatted = []
        for r in reservations:
            sport_val = r.sport.value if hasattr(r.sport, "value") else str(r.sport)
            status_raw = r.status.value if hasattr(r.status, "value") else str(r.status or "")
            status_map_ui = {
                "pending": "pendiente", "paid": "pagado",
                "cancelled": "cancelado", "refunded": "reembolsado",
                "pendiente": "pendiente", "pagado": "pagado",
                "cancelado": "cancelado", "reembolsado": "reembolsado",
            }
            formatted.append({
                "id": str(r.id),
                "client_name": r.client_name,
                "dni": r.client_dni or "",
                "phone": r.client_phone or "",
                "sport": sport_val,
                "sport_label": sport_val.capitalize() if "futbol" not in sport_val.lower() and "voley" not in sport_val.lower() else ("Futbol" if "futbol" in sport_val.lower() else "Voley"),
                "field_name": r.field_name,
                "start_datetime": r.start_datetime.strftime("%Y-%m-%d %H:%M"),
                "end_datetime": r.end_datetime.strftime("%Y-%m-%d %H:%M"),
                "advance_amount": r.paid_amount,
                "total_amount": r.total_amount,
                "paid_amount": r.paid_amount,
                "status": status_map_ui.get(status_raw.strip().lower(), status_raw or "pendiente"),
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                "cancellation_reason": r.cancellation_reason or "",
                "delete_reason": r.delete_reason or "",
            })

        async with self:
            self.service_reservations = formatted
            self.reservation_total_count = int(total_count or 0)
            if page != self.reservation_current_page:
                self.reservation_current_page = page

    @rx.event(background=True)
    async def bg_load_users(self):
        """Background: carga usuarios para /configuracion."""
        async with self:
            now = time.time()
            if (now - self._last_users_load_ts) >= self._PAGE_DATA_TTL:
                self._last_users_load_ts = now
                self.load_users()

    @rx.event
    async def handle_cross_tab_runtime_sync(self):
        """Refresca estado en caliente cuando otra pestaña cambia configuración."""
        if not self.is_authenticated:
            return

        await self._do_runtime_refresh(force=True)
        self.sync_page_from_route()

        if hasattr(self, "load_settings"):
            self.load_settings()
        self._refresh_payment_config_with_ttl(force=True)
        if hasattr(self, "_ensure_payment_method_selected"):
            self._ensure_payment_method_selected()
        if hasattr(self, "_refresh_payment_feedback"):
            self._refresh_payment_feedback()

        current_path = ""
        router = getattr(self, "router", None)
        url = getattr(router, "url", None) if router else None
        if url:
            current_path = getattr(url, "path", "") or ""

        if current_path == "/configuracion":
            if hasattr(self, "load_users"):
                self.load_users()
            if hasattr(self, "load_branches"):
                self.load_branches()

    # ------------------------------------------------------------------
    # Manejadores consolidados de inicialización de página
    # Fusiona sync_page + ensure_view + cargas específicas de página + common_guards
    # en UN solo evento por página → 1 delta en vez de 3-5 eventos separados.
    # ------------------------------------------------------------------

    def _check_auth_and_privilege(self, privilege_key: str, deny_msg: str):
        """Retorna eventos de redirección si el acceso es denegado, sino None."""
        if not self.is_authenticated:
            return [rx.redirect("/")]
        if not self.current_user["privileges"].get(privilege_key):
            return [
                rx.toast(deny_msg, duration=3000),
                rx.redirect("/dashboard"),
            ]
        return None

    @rx.event
    async def page_init_default(self):
        """on_load para / y /dashboard (sin restricción de privilegio)."""
        if not self.is_authenticated:
            # Forzar sidebar abierto para mostrar contenido guest
            self.sidebar_open = True
            yield
            return
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
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        # Enviar delta parcial (la UI renderiza la página de inmediato)
        yield
        # Cargar proveedores en background (no bloquea event loop)
        yield State.bg_load_suppliers

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
        # Garantiza que Venta siempre use la configuración más reciente de métodos de pago.
        self._refresh_payment_config_with_ttl()
        if hasattr(self, "_ensure_payment_method_selected"):
            self._ensure_payment_method_selected()
        if hasattr(self, "_refresh_payment_feedback"):
            self._refresh_payment_feedback()
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
        # Cargar datos de caja en background (no bloquea event loop)
        yield State.bg_refresh_cashbox_data

    @rx.event
    async def page_init_clientes(self):
        """on_load para /clientes. Verifica plan y privilegio view_clientes."""
        await self._do_runtime_refresh()
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
        # Delta parcial: renderiza la UI de inmediato
        yield

    @rx.event
    async def page_init_cuentas(self):
        """on_load para /cuentas. Verifica plan y privilegio view_cuentas."""
        await self._do_runtime_refresh()
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
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        # Enviar delta parcial (UI renderiza estructura de servicios)
        yield
        # Cargar reservaciones en background (no bloquea event loop)
        yield State.bg_load_reservations

    @rx.event
    async def page_init_configuracion(self):
        """on_load para /configuracion. Requiere rol Administrador o Superadmin."""
        await self._do_runtime_refresh()
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
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        # Enviar delta parcial (UI renderiza estructura de config)
        yield
        # Cargar usuarios en background (no bloquea event loop)
        yield State.bg_load_users

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

    @rx.event
    async def page_init_login(self):
        """on_load para /login. Redirige al dashboard si ya está autenticado."""
        if self.is_authenticated:
            yield rx.redirect("/dashboard")
            return
        # Forzar sidebar abierto para mostrar contenido guest en producción
        self.sidebar_open = True

    @rx.event
    async def page_init_owner(self):
        """on_load para /owner. Verifica sesión activa del Owner Backoffice."""
        # No necesita _do_runtime_refresh del sistema de ventas
        # Solo verifica la sesión propia del owner
        if not self.owner_session_active:
            yield rx.redirect(OWNER_LOGIN_PATH)
            return
        # Delta parcial: renderiza la UI de inmediato
        yield
        # Cargar empresas INLINE para evitar race conditions en producción
        self.owner_loading = True
        yield
        try:
            async with AsyncSessionLocal() as session:
                from app.utils.tenant import tenant_bypass
                from app.services.owner_service import OwnerService
                with tenant_bypass():
                    items, total = await OwnerService.list_companies(
                        session,
                        search=self.owner_search,
                        page=self.owner_page,
                        per_page=self.owner_per_page,
                    )
                self.owner_companies = items
                self.owner_companies_total = total
        except Exception as e:
            import logging
            logging.getLogger("State").error(f"Error cargando empresas en page_init_owner: {e}")
        finally:
            self.owner_loading = False
        yield
        yield State.owner_load_audit_logs(0)  # type: ignore[attr-defined]

    @rx.event
    async def page_init_owner_login(self):
        """on_load para login del Owner Backoffice."""
        # Si ya tiene sesión activa de owner, redirigir al backoffice
        if self.owner_session_active:
            yield rx.redirect(OWNER_ROOT_PATH)
            return
