import os
import datetime

import reflex as rx
import time
from app.utils.logger import get_logger as _get_logger

_state_logger = _get_logger("State")
from sqlmodel import select
from sqlalchemy import func, or_
from app.models import Supplier, FieldReservation as FieldReservationModel, User as UserModel
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
from app.utils.tenant import tenant_bypass
from app.utils.logger import get_logger

_logger = get_logger("State")

from app.utils.env import APP_SURFACE

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
    # Último tenant (company_id, branch_id) procesado por _do_runtime_refresh.
    # Si el tenant actual difiere, el TTL se bypassa: garantiza que tras cambiar
    # de sucursal/empresa se fuerce refresh aunque el TTL aún no haya vencido.
    _last_runtime_company_id: int = rx.field(default=0, is_var=False)
    _last_runtime_branch_id: int = rx.field(default=0, is_var=False)

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
        self._resolve_current_user()
        if not self.is_authenticated:
            return

        now = time.time()
        # Forzar refresh si subscription_snapshot está vacío (plan no cargado)
        snapshot_empty = not (self.subscription_snapshot or {}).get("plan_type")
        # Bypass si el usuario está autenticado pero no tiene sucursales cargadas.
        # Cubre el race condition post STATE_RESET donde on_load disparó antes de
        # que LocalStorage sincronizara el token → refresh saltó con is_authenticated=False.
        branches_empty = not getattr(self, "available_branches", None)
        # Detectar cambio de tenant: si company/branch actual difiere del último
        # procesado, bypassamos el TTL. Esto cubre el caso de set_active_branch
        # + rx.redirect() donde el TTL aún no venció pero el tenant cambió.
        try:
            cur_company = int(self.current_user.get("company_id") or 0) if hasattr(self, "current_user") else 0
        except (TypeError, ValueError):
            cur_company = 0
        try:
            cur_branch = int(self.selected_branch_id) if getattr(self, "selected_branch_id", "") else 0
        except (TypeError, ValueError):
            cur_branch = 0
        last_company = getattr(self, "_last_runtime_company_id", 0) or 0
        last_branch = getattr(self, "_last_runtime_branch_id", 0) or 0
        tenant_changed = (cur_company != last_company) or (cur_branch != last_branch)
        if (
            not force
            and not snapshot_empty
            and not branches_empty
            and not tenant_changed
            and (now - self._last_runtime_refresh_ts) < self._runtime_refresh_ttl
        ):
            return
        self._last_runtime_refresh_ts = now
        # Evitar AttributeError en mocks de tests que no declaran estos campos.
        try:
            self._last_runtime_company_id = cur_company
            self._last_runtime_branch_id = cur_branch
        except AttributeError:
            pass

        # --- auth + caja + alertas ---
        if hasattr(self, "refresh_auth_runtime_cache"):
            self.refresh_auth_runtime_cache()

        if hasattr(self, "refresh_cashbox_status"):
            self.refresh_cashbox_status()

        if hasattr(self, "check_overdue_alerts"):
            self.check_overdue_alerts()

        # Billing: solo cargar flag is_active para sidebar (ligero)
        if hasattr(self, "_refresh_billing_active_flag"):
            self._refresh_billing_active_flag()

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
        elif (
            tenant_changed
            and not seeded_defaults
            and hasattr(self, "_refresh_payment_config_with_ttl")
        ):
            # Al cambiar de sucursal, los datos de config son del branch anterior.
            # Recargar explícitamente para el nuevo branch aunque payment_methods
            # no esté vacío (condición que el bloque anterior no cubre).
            self._refresh_payment_config_with_ttl(force=True)
            # Después del reload, si el nuevo branch no tiene datos base en la DB,
            # sembrarlos ahora. La condición en línea 163 se evaluó antes de que
            # load_config_data actualizara self.units con el contexto del branch
            # destino, por lo que no alcanzó a detectar el branch vacío.
            if hasattr(self, "units") and not self.units and hasattr(self, "ensure_default_data"):
                self.ensure_default_data()

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
            if (now - self._last_cashbox_data_ts) < self._PAGE_DATA_TTL:
                return
            self._last_cashbox_data_ts = now
        yield type(self).refresh_cashbox_data

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
            user_ids = list({r.user_id for r in reservations if r.user_id})
            user_name_map: dict[int, str] = {}
            if user_ids:
                user_rows = (await session.exec(
                    select(UserModel).where(UserModel.id.in_(user_ids))
                )).all()
                user_name_map = {u.id: u.username for u in user_rows}

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
                "created_by": user_name_map.get(r.user_id, "—") if r.user_id else "—",
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
        """Compat histórica: wrapper sobre _page_guard."""
        return self._page_guard(privilege_key=privilege_key, deny_msg=deny_msg)

    def _page_guard(
        self,
        *,
        privilege_key: str | None = None,
        plan_block: str | None = None,
        require_roles: tuple[str, ...] | None = None,
        extra_check: bool = True,
        deny_msg: str = "Acceso denegado.",
    ):
        """
        Guard unificado para on_load de páginas privadas.

        Retorna lista de eventos a despachar si se deniega acceso, o None si el
        acceso es permitido.

        - `privilege_key`: clave en `current_user["privileges"]` que debe ser truthy.
        - `plan_block`: plan que NO puede acceder (p.ej. "standard"). Se compara lowercase.
        - `require_roles`: roles permitidos; si el rol del usuario no está, deniega.
        - `extra_check`: condición adicional pre-evaluada por el caller (p.ej. feature flag).
        """
        if not self.is_authenticated:
            return [rx.call_script("window.location.replace('/login')")]
        if plan_block:
            plan = (self.plan_actual or "").strip().lower()
            if plan == plan_block:
                return [rx.toast(deny_msg, duration=3000), rx.redirect("/dashboard")]
        if require_roles and self.current_user["role"] not in require_roles:
            return [rx.toast(deny_msg, duration=3000), rx.redirect("/dashboard")]
        if privilege_key and not self.current_user["privileges"].get(privilege_key):
            return [rx.toast(deny_msg, duration=3000), rx.redirect("/dashboard")]
        if not extra_check:
            return [rx.toast(deny_msg, duration=3000), rx.redirect("/dashboard")]
        return None

    @rx.event
    async def page_init_default(self):
        """on_load para / y /dashboard (sin restricción de privilegio)."""
        self._resolve_current_user()
        _state_logger.info(
            "[page_init] is_authenticated=%s token_prefix=%s branches=%s",
            self.is_authenticated,
            (getattr(self, "token", "") or "")[:12],
            len(getattr(self, "available_branches", None) or []),
        )
        if not self.is_authenticated:
            # Forzar sidebar abierto para mostrar contenido guest
            self.sidebar_open = True
            yield
            # Race condition: on_load disparó antes de que LocalStorage sincronizara
            # el token. Agenda un reintento diferido; si para entonces el token ya
            # llegó al servidor, carga el runtime correctamente.
            yield State.deferred_branch_refresh
            return
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
            return
        # Delta parcial: renderiza la UI de inmediato
        yield
        # Carga explícita de datos del Dashboard en background: no depender
        # del on_mount del componente (frágil tras rx.redirect por branch switch).
        if hasattr(self, "load_dashboard_background"):
            yield State.load_dashboard_background

    @rx.event
    async def deferred_branch_refresh(self):
        """Reintento de runtime cache para cubrir race condition de hidratación.

        Se agenda desde page_init_default cuando on_load disparó antes de que
        LocalStorage sincronizara el token. Si el token ya está disponible al
        momento de ejecutar este evento, carga las sucursales y redirige
        correctamente. Si no, no hace nada (usuario genuinamente no autenticado).
        """
        self._resolve_current_user()
        _state_logger.info(
            "[deferred_refresh] is_authenticated=%s token_prefix=%s branches=%s",
            self.is_authenticated,
            (getattr(self, "token", "") or "")[:12],
            len(getattr(self, "available_branches", None) or []),
        )
        if not self.is_authenticated:
            # UPDATE_VARS_INTERNAL puede haber llegado con token vacío por race
            # condition entre applyClientStorageDelta y onLoadInternalEvent.
            # Si localStorage sí tiene un token válido, recargar fuerza un nuevo
            # HYDRATE completo que lee localStorage correctamente.
            _TOKEN_LS_KEY = (
                "reflex___state____state"
                ".app___states___root_state____root_state"
                ".token_rx_state_"
            )
            yield rx.call_script(
                f"(function(){{"
                f"var t=localStorage.getItem('{_TOKEN_LS_KEY}');"
                f"if(t&&t.length>20){{window.location.reload();}}"
                f"}})();"
            )
            return
        if getattr(self, "available_branches", None):
            return  # ya cargadas por otro camino
        await self._do_runtime_refresh(force=True)
        self.sync_page_from_route()
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
            return
        yield
        if hasattr(self, "load_dashboard_background"):
            yield State.load_dashboard_background

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
        # Cargar márgenes para el auto-cálculo del precio de venta
        if not getattr(self, "company_profit_margin", "").strip():
            if hasattr(self, "load_settings"):
                self.load_settings()
        # Delta parcial: renderiza la UI de inmediato
        yield

    @rx.event
    async def page_init_compras(self):
        """on_load para /compras. Verifica privilegio view_compras|view_ingresos y carga proveedores."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        # Privilegio compuesto: basta con tener compras o ingresos.
        privileges = self.current_user["privileges"] if self.is_authenticated else {}
        has_access = privileges.get("view_compras") or privileges.get("view_ingresos")
        denied = self._page_guard(
            extra_check=bool(has_access),
            deny_msg="Acceso denegado: No tienes permiso para ver Compras.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        yield
        yield State.bg_load_suppliers

    @rx.event
    async def page_init_reposicion(self):
        """on_load para /reposicion. Verifica privilegio view_compras|view_ingresos."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        privileges = self.current_user["privileges"] if self.is_authenticated else {}
        has_access = privileges.get("view_compras") or privileges.get("view_ingresos")
        denied = self._page_guard(
            extra_check=bool(has_access),
            deny_msg="Acceso denegado: No tienes permiso para ver Reposición.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        yield

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
        # Cargar configuración de facturación electrónica
        if hasattr(self, "load_billing_config"):
            self.load_billing_config()
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
        denied = self._page_guard(
            privilege_key="view_clientes",
            extra_check=bool(getattr(self, "company_has_clients", False)),
            deny_msg="Acceso denegado: No tienes permiso para ver Clientes.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        # Carga explícita de clientes (tenant-aware). load_clients es sync.
        if hasattr(self, "load_clients"):
            self.load_clients()
        yield

    @rx.event
    async def page_init_cuentas(self):
        """on_load para /cuentas. Verifica plan y privilegio view_cuentas."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        denied = self._page_guard(
            privilege_key="view_cuentas",
            extra_check=bool(getattr(self, "company_has_credits", False)),
            deny_msg="Acceso denegado: No tienes permiso para ver Cuentas.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        yield
        # Carga explícita de deudores en background (tenant-aware).
        if hasattr(self, "load_debtors_background"):
            yield State.load_debtors_background

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
        # Cargar márgenes para placeholder del modal de edición de producto
        if not getattr(self, "company_profit_margin", "").strip():
            if hasattr(self, "load_settings"):
                self.load_settings()
        # Delta parcial: renderiza la UI de inmediato
        yield

    @rx.event
    async def page_init_etiquetas(self):
        """on_load para /etiquetas. Verifica plan y privilegio view_etiquetas."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        denied = self._page_guard(
            privilege_key="view_etiquetas",
            extra_check=bool(getattr(self, "company_has_etiquetas", False)),
            deny_msg="Acceso denegado: No tienes permiso para ver Etiquetas.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
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
        # Carga explícita del historial en background (tenant-aware).
        if hasattr(self, "reload_history_background"):
            yield State.reload_history_background

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
        """on_load para /servicios. Verifica plan y privilegio view_servicios."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        has_module = bool(getattr(self, "company_has_services", False)) or bool(
            getattr(self, "company_has_reservations", False)
        )
        denied = self._page_guard(
            privilege_key="view_servicios",
            extra_check=has_module,
            deny_msg="Acceso denegado: No tienes permiso para ver Servicios.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        yield
        yield State.bg_load_reservations

    @rx.event
    async def page_init_presupuestos(self):
        """on_load para /presupuestos. Guard + carga de datos."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        denied = self._page_guard(
            privilege_key="view_presupuestos",
            extra_check=bool(getattr(self, "company_has_presupuestos", False)),
            deny_msg="Acceso denegado: No tienes permiso para ver Presupuestos.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
            return
        yield
        yield State.bg_load_quotations

    @rx.event
    async def page_init_promociones(self):
        """on_load para /promociones. Guard + carga de datos."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        denied = self._page_guard(
            privilege_key="manage_promociones",
            extra_check=bool(getattr(self, "company_has_promociones", False)),
            deny_msg="Acceso denegado: No tienes permiso para gestionar Promociones.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
            return
        yield
        yield State.bg_load_promotions

    @rx.event
    async def page_init_listas_precios(self):
        """on_load para /listas-precios. Guard + carga de datos."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        denied = self._page_guard(
            privilege_key="manage_listas_precios",
            extra_check=bool(getattr(self, "company_has_listas_precios", False)),
            deny_msg="Acceso denegado: No tienes permiso para gestionar Listas de Precios.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
            return
        yield
        yield State.bg_load_price_lists

    @rx.event
    async def page_init_documentos_fiscales(self):
        """on_load para /documentos-fiscales. Verifica privilegio view_ventas."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        # Bloquear acceso si el plan no incluye facturación electrónica.
        if not getattr(self, "company_has_electronic_billing", False):
            yield rx.redirect("/")
            return
        denied = self._page_guard(
            privilege_key="view_ventas",
            deny_msg="Acceso denegado: No tienes permiso para ver Documentos Fiscales.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        self.fiscal_docs_page = 0
        self.fiscal_docs_status_filter = "todos"
        self.fiscal_docs_receipt_filter = "todos"
        self.fiscal_docs_search = ""
        self.fiscal_docs_date_from = ""
        self.fiscal_docs_date_to = ""
        self.fiscal_doc_selected = {}
        self.fiscal_doc_detail_open = False
        self.load_fiscal_docs()
        yield

    @rx.event
    async def page_init_configuracion(self):
        """on_load para /configuracion. Requiere rol Administrador o Superadmin."""
        await self._do_runtime_refresh()
        self.sync_page_from_route()
        denied = self._page_guard(
            require_roles=("Superadmin", "Administrador"),
            deny_msg="Acceso denegado: Se requiere nivel de Administrador.",
        )
        if denied:
            for ev in denied:
                yield ev
            return
        redirect = self.run_common_guards()
        if redirect:
            yield redirect
        # Recargar datos de config para el branch activo en cada visita a la página.
        # _do_runtime_refresh solo lo hace cuando payment_methods está vacío, lo que
        # causa que al cambiar de sucursal la data no se refresque al re-navegar.
        if hasattr(self, "load_config_data"):
            self.load_config_data()
        # Si el branch activo no tiene datos base en la BD (units/payment_methods
        # vacíos), sembrarlos ahora. Cubre branches creados antes del seed automático
        # y el caso donde _do_runtime_refresh saltó el seeding por TTL.
        if hasattr(self, "units") and not self.units and hasattr(self, "ensure_default_data"):
            self.ensure_default_data()
        yield
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
            # assign(): full-page nav → evita React Router lazy-load del chunk del
            # dashboard que, si falla, causa window.location.reload() → bucle infinito.
            yield rx.call_script("window.location.assign('/dashboard')")
            return
        # No autenticado: reemplazar la entrada de historial actual con /login para que
        # "Atrás" desde /login vuelva directamente a la landing en vez de atravesar
        # páginas de la app que también muestran el formulario de login.
        yield rx.call_script("window.history.replaceState(null, '', '/login')")
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
            from app.services.owner_service import OwnerService
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    items, total = await OwnerService.list_companies(
                        session,
                        search=self.owner_search,
                        page=self.owner_page,
                        per_page=self.owner_per_page,
                    )
                self.owner_companies = items
                self.owner_companies_total = total
        except Exception:
            _logger.exception("Error cargando empresas en page_init_owner")
        finally:
            self.owner_loading = False
        yield
        yield State.owner_load_audit_logs(0)  # type: ignore[attr-defined]
        yield State.load_platform_billing_config()  # type: ignore[attr-defined]

    @rx.event
    async def page_init_owner_login(self):
        """on_load para login del Owner Backoffice."""
        # Si ya tiene sesión activa de owner, redirigir al backoffice
        if self.owner_session_active:
            yield rx.redirect(OWNER_ROOT_PATH)
            return
