"""
Estado del backoffice de owners para gestión de empresas SaaS.

Autenticación completamente independiente del Sistema de Ventas.
Credenciales configurables vía variables de entorno:
  OWNER_ADMIN_EMAIL    (default: admin@tuwaykiapp.com)
  OWNER_ADMIN_PASSWORD (default: usa hash embebido)
"""

import os
import asyncio
import time
from collections import defaultdict

import bcrypt
import reflex as rx
from sqlmodel import select

from app.models.auth import User as UserModel
from app.models.company import PlanType, SubscriptionStatus
from app.services.owner_service import OwnerService, OwnerServiceError
from app.utils.db import AsyncSessionLocal
from app.utils.logger import get_logger
from app.utils.rate_limit import is_rate_limited, record_failed_attempt, clear_login_attempts
from app.utils.tenant import tenant_bypass

logger = get_logger("OwnerState")

APP_SURFACE: str = (os.getenv("APP_SURFACE") or "all").strip().lower()
if APP_SURFACE not in {"all", "landing", "app", "owner"}:
    APP_SURFACE = "all"

OWNER_ROOT_PATH: str = "/" if APP_SURFACE == "owner" else "/owner"
OWNER_LOGIN_PATH: str = "/login" if APP_SURFACE == "owner" else "/owner/login"

# ─── Credenciales del Owner Backoffice (independientes del Sistema de Ventas) ───
# Configurables vía variables de entorno para producción.
OWNER_ADMIN_EMAIL: str = os.environ.get(
    "OWNER_ADMIN_EMAIL", "admin@tuwaykiapp.com"
)

# Timeout de sesión del owner (30 minutos por defecto)
OWNER_SESSION_TIMEOUT_SECONDS: int = int(
    os.environ.get("OWNER_SESSION_TIMEOUT_SECONDS", "1800")
)


def _load_owner_password_hash() -> str:
    """Carga el hash de contraseña del owner de forma segura.

    Prioridad:
      1. Variable de entorno OWNER_ADMIN_PASSWORD_HASH (recomendado)
      2. Fallback temporal con advertencia en logs (para no romper deploys existentes)

    En un futuro deploy, configurá la env var y el fallback desaparece.
    """
    h = os.environ.get("OWNER_ADMIN_PASSWORD_HASH", "").strip()
    if h:
        return h

    # ── Fallback retrocompatible ──
    # Usa un hash de respaldo para no inutilizar el backoffice en deploys
    # que aún no tengan la variable configurada.
    # ACCIÓN REQUERIDA: configurar OWNER_ADMIN_PASSWORD_HASH en el .env
    # del servidor y eliminar este fallback en una versión futura.
    _fallback_hash = (
        "$2b$12$hJw0pC61BFXV0pGwNrtbDOBq6qPRFdJbziGx58sJmTt5FAteCBtXa"
    )

    _env = (os.getenv("ENV") or "dev").strip().lower()
    if _env in ("prod", "production"):
        logger.warning(
            "⚠️  OWNER_ADMIN_PASSWORD_HASH no configurado. "
            "Usando hash de respaldo temporal. "
            "ACCIÓN REQUERIDA: generar un hash con "
            "'python -c \"import bcrypt; print(bcrypt.hashpw(b\\\"TU_CLAVE\\\", bcrypt.gensalt(12)).decode())\"' "
            "y agregarlo al .env del servidor como OWNER_ADMIN_PASSWORD_HASH=..."
        )
        return _fallback_hash

    # En desarrollo: también usar el fallback (más práctico que generar temporal)
    logger.info(
        "Owner password hash: usando fallback. "
        "Configura OWNER_ADMIN_PASSWORD_HASH en .env para personalizarlo."
    )
    return _fallback_hash


_OWNER_ADMIN_PASSWORD_HASH: str = _load_owner_password_hash()


def _verify_owner_credentials(email: str, password: str) -> bool:
    """Valida credenciales contra las del Owner Backoffice (NO la tabla User)."""
    if email.lower() != OWNER_ADMIN_EMAIL.lower():
        return False
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            _OWNER_ADMIN_PASSWORD_HASH.encode("utf-8"),
        )
    except Exception:
        return False

# ─── Rate limiting para acciones owner ─────────────────
# Máximo OWNER_MAX_ACTIONS acciones por ventana de OWNER_ACTION_WINDOW_SECONDS
OWNER_MAX_ACTIONS: int = 10
OWNER_ACTION_WINDOW_SECONDS: int = 60

# Almacena timestamps de acciones por actor_email
_owner_action_timestamps: dict[str, list[float]] = defaultdict(list)


def _is_owner_rate_limited(actor_email: str) -> bool:
    """Verifica si el actor excedió el límite de acciones owner."""
    now = time.time()
    cutoff = now - OWNER_ACTION_WINDOW_SECONDS
    # Limpiar timestamps antiguos
    _owner_action_timestamps[actor_email] = [
        t for t in _owner_action_timestamps[actor_email] if t > cutoff
    ]
    return len(_owner_action_timestamps[actor_email]) >= OWNER_MAX_ACTIONS


def _record_owner_action(actor_email: str) -> None:
    """Registra una acción exitosa del owner."""
    _owner_action_timestamps[actor_email].append(time.time())


def _normalize_non_negative_int_input(value: str | float | int) -> str:
    """Normaliza input numérico de UI sin romper la escritura en tiempo real."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value) if value >= 0 else ""
    if isinstance(value, float):
        if value != value:  # NaN
            return ""
        return str(int(value)) if value >= 0 else ""

    text = str(value).strip()
    if text == "":
        return ""
    if text.isdigit():
        return text

    try:
        parsed = int(float(text))
        return str(parsed) if parsed >= 0 else ""
    except (TypeError, ValueError):
        # Fallback tolerante (ej. caracteres sueltos) para no romper el input.
        digits = "".join(ch for ch in text if ch.isdigit())
        return digits

# Opciones para selects del UI
PLAN_OPTIONS = [
    {"value": PlanType.TRIAL, "label": "Trial"},
    {"value": PlanType.STANDARD, "label": "Standard"},
    {"value": PlanType.PROFESSIONAL, "label": "Professional"},
    {"value": PlanType.ENTERPRISE, "label": "Enterprise"},
]

STATUS_OPTIONS = [
    {"value": SubscriptionStatus.ACTIVE, "label": "Activo"},
    {"value": SubscriptionStatus.WARNING, "label": "Advertencia"},
    {"value": SubscriptionStatus.PAST_DUE, "label": "Vencido"},
    {"value": SubscriptionStatus.SUSPENDED, "label": "Suspendido"},
]


class OwnerState:
    """Mixin de estado para el backoffice de owners.

    El Owner Backoffice tiene su propio flujo de autenticación independiente.
    Un usuario del Sistema de Ventas NO puede acceder al backoffice aunque
    esté logueado; debe autenticarse explícitamente en el login owner.
    """

    # ─── Sesión independiente del Owner Backoffice ─────
    owner_session_active: bool = False  # Solo True si se autentica via login owner
    owner_session_email: str = ""  # Email del owner autenticado
    owner_session_user_id: int = 0  # ID del usuario owner en BD (para auditoría)
    _owner_session_started_at: float = rx.field(default=0.0, is_var=False)

    # ─── Campos de login del owner ─────────────────────
    owner_login_email: str = ""
    owner_login_password: str = ""
    owner_login_error: str = ""
    owner_login_loading: bool = False

    # ─── Datos de listado ──────────────────────────────
    owner_companies: list[dict] = []
    owner_companies_total: int = 0
    owner_search: str = ""
    owner_page: int = 1
    owner_per_page: int = 15

    # ─── Detalle de empresa seleccionada ───────────────
    owner_selected_company: dict = {}

    # ─── Modal / formulario ────────────────────────────
    owner_modal_open: bool = False
    owner_modal_action: str = ""  # change_plan | change_status | extend_trial | adjust_limits
    owner_modal_company_id: int = 0
    owner_modal_company_name: str = ""

    # Campos del formulario
    owner_form_reason: str = ""
    owner_form_reason_preset: str = ""  # Motivo predefinido seleccionable
    owner_form_plan: str = ""
    owner_form_status: str = ""
    owner_form_extra_days: str = "7"
    owner_form_max_users: str = ""
    owner_form_max_branches: str = ""
    owner_form_has_reservations: bool = True
    owner_form_has_clients: bool = True
    owner_form_has_credits: bool = True
    owner_form_has_billing: bool = False
    owner_form_notes: str = ""  # Notas adicionales opcionales
    owner_form_activate_now: bool = True  # Activar inmediatamente al cambiar plan
    owner_form_subscription_months: str = "12"  # Duración de suscripción en meses

    # Info de contexto pre-cargada (solo lectura en UI)
    owner_form_current_plan: str = ""
    owner_form_current_status: str = ""
    owner_form_trial_ends_at: str = ""
    owner_form_effective_date: str = ""  # Fecha cuando se aplica la acción

    # ─── Auditoría ─────────────────────────────────────
    owner_audit_logs: list[dict] = []
    owner_audit_total: int = 0
    owner_audit_page: int = 1

    # ─── Reset de contraseña ────────────────────────────
    owner_reset_modal_open: bool = False
    owner_reset_company_id: int = 0
    owner_reset_company_name: str = ""
    owner_reset_users: list[dict[str, str]] = []
    owner_reset_temp_password: str = ""
    owner_reset_target_username: str = ""
    owner_reset_result_visible: bool = False
    owner_reset_loading: bool = False

    # ─── Loading ───────────────────────────────────────
    owner_loading: bool = False
    _owner_companies_load_seq: int = rx.field(default=0, is_var=False)
    _owner_search_debounce_seq: int = rx.field(default=0, is_var=False)

    # ─── Computed vars ─────────────────────────────────

    @rx.var(cache=True)
    def is_owner(self) -> bool:
        """Verifica si el usuario actual es owner de la plataforma."""
        return bool(self.current_user.get("is_platform_owner", False))

    @rx.var(cache=True)
    def is_owner_authenticated(self) -> bool:
        """True solo si el owner se autenticó explícitamente vía login owner.

        Completamente independiente del login del Sistema de Ventas.
        Incluye validación de timeout de sesión.
        """
        if not self.owner_session_active:
            return False
        # Validar timeout de sesión
        if self._owner_session_started_at > 0:
            elapsed = time.time() - self._owner_session_started_at
            if elapsed > OWNER_SESSION_TIMEOUT_SECONDS:
                return False
        return True

    @rx.var(cache=True)
    def owner_total_pages(self) -> int:
        if self.owner_companies_total == 0:
            return 1
        return max(1, -(-self.owner_companies_total // self.owner_per_page))

    @rx.var(cache=True)
    def owner_audit_total_pages(self) -> int:
        if self.owner_audit_total == 0:
            return 1
        return max(1, -(-self.owner_audit_total // 20))

    # ─── Login / Logout del Owner Backoffice ───────────

    @rx.event
    def owner_set_login_email(self, value: str):
        self.owner_login_email = value

    @rx.event
    def owner_set_login_password(self, value: str):
        self.owner_login_password = value

    @rx.event
    def owner_login(self, form_data: dict):
        """Autenticación dedicada del Owner Backoffice.

        Credenciales completamente independientes del Sistema de Ventas.
        Valida contra OWNER_ADMIN_EMAIL / OWNER_ADMIN_PASSWORD_HASH,
        NO contra la tabla de usuarios del sistema.
        Incluye rate limiting para prevenir ataques de fuerza bruta.
        """
        email = (
            form_data.get("owner_email", "") or self.owner_login_email
        ).strip().lower()
        raw_password = form_data.get("owner_password", "") or self.owner_login_password

        if not email or not raw_password:
            self.owner_login_error = "Ingrese email y contraseña."
            return

        self.owner_login_loading = True
        self.owner_login_error = ""

        # Rate limiting — prevenir fuerza bruta en login del owner
        rate_key = f"owner_login:{email}"
        if is_rate_limited(rate_key):
            self.owner_login_error = "Demasiados intentos. Espere 15 minutos."
            self.owner_login_loading = False
            logger.warning("Owner login rate-limited: %s", email[:20])
            return

        # Validar contra credenciales propias del Owner Backoffice
        if not _verify_owner_credentials(email, raw_password):
            record_failed_attempt(rate_key)
            self.owner_login_error = "Credenciales inválidas."
            self.owner_login_loading = False
            logger.warning("Owner login fallido: credenciales incorrectas (%s)", email[:20])
            return

        # Limpiar intentos fallidos tras login exitoso
        clear_login_attempts(rate_key)

        # Buscar al platform owner en la BD para auditoría
        owner_user_id = 0
        with rx.session() as session:
            owner_user = session.exec(
                select(UserModel)
                .where(UserModel.is_platform_owner == True)  # noqa: E712
                .execution_options(tenant_bypass=True)
            ).first()
            if not owner_user:
                owner_user = session.exec(
                    select(UserModel)
                    .where(UserModel.email == email)
                    .execution_options(tenant_bypass=True)
                ).first()
            if owner_user:
                owner_user_id = owner_user.id

        # ¡Login exitoso! Activar sesión owner con timestamp
        self.owner_session_active = True
        self.owner_session_email = email
        self.owner_session_user_id = owner_user_id
        self._owner_session_started_at = time.time()
        self.owner_login_email = ""
        self.owner_login_password = ""
        self.owner_login_error = ""
        self.owner_login_loading = False
        logger.info("Owner login exitoso: %s", email[:20])
        return rx.redirect(OWNER_ROOT_PATH)

    @rx.event
    def owner_logout(self):
        """Cierra sesión del Owner Backoffice sin afectar el Sistema de Ventas."""
        self.owner_session_active = False
        self.owner_session_email = ""
        self.owner_session_user_id = 0
        self._owner_session_started_at = 0.0
        self.owner_companies = []
        self.owner_audit_logs = []
        self.owner_login_email = ""
        self.owner_login_password = ""
        self.owner_login_error = ""
        logger.info("Owner logout")
        return rx.redirect(OWNER_LOGIN_PATH)

    # ─── Eventos de carga ──────────────────────────────

    @rx.event
    async def owner_load_companies(self):
        """Carga lista de empresas para el backoffice."""
        if not self.is_owner_authenticated:
            return
        self._owner_companies_load_seq += 1
        seq = self._owner_companies_load_seq
        self.owner_loading = True
        yield
        try:
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    items, total = await OwnerService.list_companies(
                        session,
                        search=self.owner_search,
                        page=self.owner_page,
                        per_page=self.owner_per_page,
                    )
                # Ignorar respuestas viejas (evita sobrescribir con datos stale).
                if seq != self._owner_companies_load_seq:
                    return
                self.owner_companies = items
                self.owner_companies_total = total
        except Exception as e:
            logger.exception("Error cargando empresas")
            if seq == self._owner_companies_load_seq:
                yield rx.toast("Error al cargar empresas. Revise los logs.", duration=4000)
        finally:
            if seq == self._owner_companies_load_seq:
                self.owner_loading = False

    @rx.event
    async def owner_search_companies(self, search: str):
        """Busca empresas por nombre o RUC."""
        if not self.is_owner_authenticated:
            return
        self.owner_search = (search or "").strip()
        self.owner_page = 1
        # Debounce para evitar query por cada tecla y mantener escritura fluida.
        self._owner_search_debounce_seq += 1
        seq = self._owner_search_debounce_seq
        await asyncio.sleep(0.25)
        if seq != self._owner_search_debounce_seq:
            return
        yield type(self).owner_load_companies

    @rx.event
    async def owner_goto_page(self, page: int):
        """Navega a una página específica."""
        self.owner_page = max(1, page)
        yield type(self).owner_load_companies

    @rx.event
    async def owner_next_page(self):
        if self.owner_page < self.owner_total_pages:
            self.owner_page += 1
            yield type(self).owner_load_companies

    @rx.event
    async def owner_prev_page(self):
        if self.owner_page > 1:
            self.owner_page -= 1
            yield type(self).owner_load_companies

    # ─── Auditoría ─────────────────────────────────────

    @rx.event
    async def owner_load_audit_logs(self, company_id: int = 0):
        """Carga logs de auditoría."""
        if not self.is_owner_authenticated:
            return
        try:
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    cid = company_id if company_id else None
                    items, total = await OwnerService.get_audit_logs(
                        session,
                        company_id=cid,
                        page=self.owner_audit_page,
                        per_page=20,
                    )
                self.owner_audit_logs = items
                self.owner_audit_total = total
        except Exception as e:
            logger.exception("Error cargando auditoría")

    @rx.event
    async def owner_audit_next_page(self):
        """Avanza página de auditoría."""
        if self.owner_audit_page < self.owner_audit_total_pages:
            self.owner_audit_page += 1
            yield type(self).owner_load_audit_logs

    @rx.event
    async def owner_audit_prev_page(self):
        """Retrocede página de auditoría."""
        if self.owner_audit_page > 1:
            self.owner_audit_page -= 1
            yield type(self).owner_load_audit_logs

    # ─── Modal de acciones ─────────────────────────────

    @rx.event
    def owner_open_modal(self, action: str, company_id: int, company_name: str):
        """Abre modal para una acción sobre una empresa."""
        self.owner_modal_open = True
        self.owner_modal_action = action
        self.owner_modal_company_id = company_id
        self.owner_modal_company_name = company_name
        from datetime import datetime as _dt
        self.owner_form_reason = ""
        self.owner_form_reason_preset = ""
        self.owner_form_plan = ""
        self.owner_form_status = ""
        self.owner_form_extra_days = "7"
        self.owner_form_max_users = ""
        self.owner_form_max_branches = ""
        self.owner_form_has_reservations = True
        self.owner_form_has_clients = True
        self.owner_form_has_credits = True
        self.owner_form_has_billing = False
        self.owner_form_notes = ""
        self.owner_form_activate_now = True
        self.owner_form_subscription_months = "12"
        self.owner_form_current_plan = ""
        self.owner_form_current_status = ""
        self.owner_form_trial_ends_at = ""
        self.owner_form_effective_date = _dt.now().strftime("%Y-%m-%d %H:%M")

        # Pre-cargar valores actuales de la empresa seleccionada
        for c in self.owner_companies:
            if c.get("id") == company_id:
                self.owner_form_plan = c.get("plan_type", "")
                self.owner_form_current_plan = c.get("plan_type", "")
                self.owner_form_status = c.get("subscription_status", "")
                self.owner_form_current_status = c.get("effective_status", c.get("subscription_status", ""))
                self.owner_form_max_users = str(c.get("max_users", ""))
                self.owner_form_max_branches = str(c.get("max_branches", ""))
                self.owner_form_has_reservations = c.get("has_reservations_module", True)
                self.owner_form_has_clients = c.get("has_clients_module", True)
                self.owner_form_has_credits = c.get("has_credits_module", True)
                self.owner_form_has_billing = c.get("has_electronic_billing", False)
                self.owner_form_trial_ends_at = c.get("trial_ends_at", "") or ""
                break

    @rx.event
    def owner_close_modal(self):
        """Cierra el modal."""
        self.owner_modal_open = False

    @rx.event
    def owner_set_form_reason(self, value: str):
        self.owner_form_reason = value

    @rx.event
    def owner_set_form_reason_preset(self, value: str):
        """Al seleccionar un motivo predefinido, lo copia al textarea."""
        self.owner_form_reason_preset = value
        if value and value != "custom":
            self.owner_form_reason = value

    @rx.event
    def owner_set_form_plan(self, value: str):
        self.owner_form_plan = value

    @rx.event
    def owner_set_form_status(self, value: str):
        self.owner_form_status = value

    @rx.event
    def owner_set_form_extra_days(self, value: str | float | int):
        self.owner_form_extra_days = _normalize_non_negative_int_input(value)

    @rx.event
    def owner_set_form_extra_days_preset(self, value: str):
        """Seleccionar días de extensión desde preset rápido."""
        if value:
            self.owner_form_extra_days = value

    @rx.event
    def owner_set_form_max_users(self, value: str | float | int):
        self.owner_form_max_users = _normalize_non_negative_int_input(value)

    @rx.event
    def owner_set_form_max_branches(self, value: str | float | int):
        self.owner_form_max_branches = _normalize_non_negative_int_input(value)

    @rx.event
    def owner_set_form_has_reservations(self, value: bool):
        self.owner_form_has_reservations = value

    @rx.event
    def owner_set_form_has_clients(self, value: bool):
        self.owner_form_has_clients = value

    @rx.event
    def owner_set_form_has_credits(self, value: bool):
        self.owner_form_has_credits = value

    @rx.event
    def owner_set_form_has_billing(self, value: bool):
        self.owner_form_has_billing = value

    @rx.event
    def owner_set_form_notes(self, value: str):
        self.owner_form_notes = value

    @rx.event
    def owner_set_form_subscription_months(self, value: str):
        self.owner_form_subscription_months = value

    @rx.event
    def owner_set_form_activate_now(self, value: bool):
        self.owner_form_activate_now = value

    # ─── Ejecución de acciones ─────────────────────────

    def _owner_actor_info(self) -> dict:
        """Extrae info del actor owner actual (desde sesión owner, no sistema de ventas)."""
        actor_user_id = self.owner_session_user_id
        if not actor_user_id:
            actor_user_id = (self.current_user or {}).get("id", 0)
        try:
            actor_user_id = int(actor_user_id or 0)
        except (TypeError, ValueError):
            actor_user_id = 0
        return {
            "actor_user_id": actor_user_id if actor_user_id > 0 else None,
            "actor_email": self.owner_session_email or "owner@platform",
        }

    @rx.event
    async def owner_execute_action(self):
        """Ejecuta la acción seleccionada en el modal."""
        if self.owner_loading:
            return
        if not self.is_owner_authenticated:
            yield rx.toast("Acceso denegado. Inicie sesión en el panel owner.", duration=3000)
            return

        if not self.owner_form_reason.strip():
            yield rx.toast("El motivo es obligatorio.", duration=3000)
            return

        # Construir razón completa (motivo + notas adicionales)
        full_reason = self.owner_form_reason.strip()
        if self.owner_form_notes.strip():
            full_reason += f" | Notas: {self.owner_form_notes.strip()}"

        # Rate limiting — prevenir abuso
        actor_email = self.owner_session_email or "unknown"
        if _is_owner_rate_limited(actor_email):
            yield rx.toast(
                f"Demasiadas acciones. Espera {OWNER_ACTION_WINDOW_SECONDS}s.",
                duration=5000,
            )
            return

        self.owner_loading = True
        yield

        actor = self._owner_actor_info()
        action = self.owner_modal_action
        company_id = self.owner_modal_company_id
        valid_actions = {"change_plan", "change_status", "extend_trial", "adjust_limits"}

        if action not in valid_actions:
            logger.warning(
                "Accion owner invalida. action=%s company_id=%s actor=%s",
                action,
                company_id,
                actor_email,
            )
            self.owner_loading = False
            yield rx.toast("Accion invalida. Cierra y vuelve a abrir el modal.", duration=3500)
            return

        logger.info(
            "Owner action requested action=%s company_id=%s actor=%s",
            action,
            company_id,
            actor_email,
        )

        try:
            async with AsyncSessionLocal() as session:
              with tenant_bypass():
                if action == "change_plan":
                    try:
                        sub_months = int(self.owner_form_subscription_months)
                    except (ValueError, TypeError):
                        sub_months = 12
                    await OwnerService.change_plan(
                        session,
                        company_id=company_id,
                        new_plan=self.owner_form_plan,
                        reason=full_reason,
                        subscription_months=sub_months if self.owner_form_plan != "trial" else 0,
                        **actor,
                    )
                    yield rx.toast("Plan actualizado correctamente.", duration=4000)

                elif action == "change_status":
                    await OwnerService.change_status(
                        session,
                        company_id=company_id,
                        new_status=self.owner_form_status,
                        reason=full_reason,
                        **actor,
                    )
                    yield rx.toast("Estado actualizado correctamente.", duration=4000)

                elif action == "extend_trial":
                    try:
                        days = int(self.owner_form_extra_days)
                    except (ValueError, TypeError):
                        days = 7
                    await OwnerService.extend_trial(
                        session,
                        company_id=company_id,
                        extra_days=days,
                        reason=full_reason,
                        **actor,
                    )
                    yield rx.toast(
                        f"Trial extendido {days} días.", duration=4000
                    )

                elif action == "adjust_limits":
                    max_users = None
                    max_branches = None
                    if self.owner_form_max_users.strip():
                        max_users = int(self.owner_form_max_users)
                    if self.owner_form_max_branches.strip():
                        max_branches = int(self.owner_form_max_branches)

                    await OwnerService.adjust_limits(
                        session,
                        company_id=company_id,
                        max_users=max_users,
                        max_branches=max_branches,
                        has_reservations_module=self.owner_form_has_reservations,
                        has_services_module=self.owner_form_has_reservations,
                        has_clients_module=self.owner_form_has_clients,
                        has_credits_module=self.owner_form_has_credits,
                        has_electronic_billing=self.owner_form_has_billing,
                        reason=full_reason,
                        **actor,
                    )
                    yield rx.toast("Límites ajustados correctamente.", duration=4000)

                else:
                    yield rx.toast(f"Acción desconocida: {action}", duration=3000)
                    self.owner_loading = False
                    return

        except OwnerServiceError as e:
            logger.warning(
                "OwnerServiceError action=%s company_id=%s actor=%s: %s",
                action,
                company_id,
                actor_email,
                e,
            )
            yield rx.toast(f"Error: {e}", duration=5000)
            self.owner_loading = False
            return
        except Exception as e:
            logger.exception("Error ejecutando acción owner")
            yield rx.toast("Error inesperado. Revise los logs del servidor.", duration=5000)
            self.owner_loading = False
            return

        _record_owner_action(actor_email)
        self.owner_modal_open = False
        self.owner_loading = False
        yield type(self).owner_load_companies

    # ─── Sincronización de trials expirados ────────────

    @rx.event
    async def owner_sync_expired(self):
        """Sincroniza BD: suspende todas las empresas con trial expirado."""
        if self.owner_loading:
            return
        if not self.is_owner_authenticated:
            yield rx.toast("Acceso denegado.", duration=3000)
            return

        actor = self._owner_actor_info()
        self.owner_loading = True
        yield

        try:
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    count = await OwnerService.sync_expired_trials(
                        session,
                        **actor,
                    )
            if count > 0:
                yield rx.toast(
                    f"{count} empresa(s) con trial expirado suspendida(s).",
                    duration=5000,
                )
            else:
                yield rx.toast(
                    "No hay trials expirados pendientes de sincronizar.",
                    duration=3000,
                )
        except Exception as e:
            logger.exception("Error sincronizando trials expirados")
            yield rx.toast("Error al sincronizar trials. Revise los logs.", duration=5000)
            self.owner_loading = False
            return

        self.owner_loading = False
        yield type(self).owner_load_companies

    # ─── Reset de contraseña de usuario ────────────────

    @rx.event
    async def owner_open_reset_modal(self, company_id: int, company_name: str):
        """Abre modal de reset de contraseña y carga usuarios de la empresa."""
        if not self.is_owner_authenticated:
            return
        self.owner_reset_modal_open = True
        self.owner_reset_company_id = company_id
        self.owner_reset_company_name = company_name
        self.owner_reset_temp_password = ""
        self.owner_reset_target_username = ""
        self.owner_reset_result_visible = False
        self.owner_reset_users = []
        self.owner_reset_loading = True
        yield
        try:
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    users = await OwnerService.list_company_users(
                        session, company_id=company_id,
                    )
                self.owner_reset_users = users
                self.owner_reset_loading = False
                yield
        except Exception as e:
            logger.exception("Error cargando usuarios para reset")
            self.owner_reset_loading = False
            yield rx.toast("Error al cargar usuarios. Revise los logs.", duration=4000)

    @rx.event
    def owner_close_reset_modal(self):
        """Cierra modal de reset."""
        self.owner_reset_modal_open = False
        self.owner_reset_temp_password = ""
        self.owner_reset_target_username = ""
        self.owner_reset_result_visible = False

    @rx.event
    async def owner_reset_password(self, user_id: str, username: str):
        """Resetea la contraseña del usuario seleccionado."""
        if not self.is_owner_authenticated:
            return

        actor_email = self.owner_session_email or "unknown"
        if _is_owner_rate_limited(actor_email):
            yield rx.toast(
                f"Demasiadas acciones. Espera {OWNER_ACTION_WINDOW_SECONDS}s.",
                duration=5000,
            )
            return

        self.owner_reset_loading = True
        self.owner_reset_temp_password = ""
        self.owner_reset_target_username = ""
        self.owner_reset_result_visible = False
        yield

        actor = self._owner_actor_info()
        try:
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    temp_password = await OwnerService.reset_user_password(
                        session,
                        company_id=self.owner_reset_company_id,
                        user_id=int(user_id),
                        reason="Reset de contraseña por admin de plataforma",
                        **actor,
                    )
            _record_owner_action(actor_email)
            self.owner_reset_temp_password = temp_password.strip()
            self.owner_reset_target_username = username
            self.owner_reset_result_visible = True
            # Fuerza rerender del listado para evitar UI stale dentro del modal.
            self.owner_reset_users = [dict(item) for item in self.owner_reset_users]
            self.owner_reset_loading = False
            yield
            yield rx.toast(f"Contraseña reseteada para {username}.", duration=4000)
        except OwnerServiceError as e:
            self.owner_reset_loading = False
            yield rx.toast(f"Error: {e}", duration=5000)
        except Exception as e:
            logger.exception("Error reseteando contraseña")
            self.owner_reset_loading = False
            yield rx.toast("Error inesperado al resetear. Revise los logs.", duration=5000)
