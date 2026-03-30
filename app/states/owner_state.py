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
from app.models.billing import CompanyBillingConfig
from app.models.company import PlanType, SubscriptionStatus
from app.services.owner_service import OwnerService, OwnerServiceError
from app.utils.crypto import encrypt_credential, encrypt_text
from app.utils.fiscal_validators import (
    validate_environment,
    validate_nubefact_url,
    validate_tax_id,
    validate_business_name,
)
from app.utils.db import AsyncSessionLocal
from app.utils.logger import get_logger
from app.utils.rate_limit import is_rate_limited, record_failed_attempt, clear_login_attempts
from app.utils.tenant import tenant_bypass
from app.utils.timezone import utc_now_naive

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
        # Limpiar estado residual de modals y formularios
        self.owner_modal_open = False
        self.owner_reset_modal_open = False
        self.owner_billing_modal_open = False
        self.owner_reset_users = []
        self.owner_reset_temp_password = ""
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
                        has_services_module=self.owner_form_has_services,
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

    # ═══════════════════════════════════════════════════════════
    # GESTIÓN DE BILLING POR EMPRESA (campos técnicos del Owner)
    # ═══════════════════════════════════════════════════════════

    # ── Configuración Global de Billing (nivel plataforma SaaS) ──────
    platform_billing_configured: bool = False
    platform_nubefact_url: str = ""
    platform_nubefact_token_display: str = ""  # masked para UI
    platform_billing_loading: bool = False

    owner_billing_modal_open: bool = False
    owner_billing_company_id: int = 0
    owner_billing_company_name: str = ""
    owner_billing_loading: bool = False

    # Form fields — campos técnicos que solo el Owner gestiona
    owner_billing_is_active: bool = False
    owner_billing_environment: str = "sandbox"
    owner_billing_nubefact_url: str = ""
    owner_billing_nubefact_token_display: str = ""
    owner_billing_serie_factura: str = "F001"
    owner_billing_serie_boleta: str = "B001"
    owner_billing_max_limit: str = "500"
    owner_billing_afip_punto_venta: str = "1"
    owner_billing_emisor_iva: str = "RI"
    owner_billing_afip_concepto: str = "1"
    owner_billing_ar_threshold: str = "68782"
    # Read-only context
    owner_billing_country: str = "PE"
    owner_billing_tax_id: str = ""
    owner_billing_business_name: str = ""
    owner_billing_config_exists: bool = False

    @rx.event
    async def load_platform_billing_config(self):
        """Carga la configuración global de billing (singleton) desde DB."""
        if not self.is_owner_authenticated:
            return
        try:
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    from app.models.platform_config import PlatformBillingSettings, PLATFORM_CONFIG_ID
                    platform = await session.get(PlatformBillingSettings, PLATFORM_CONFIG_ID)
                    if platform:
                        self.platform_nubefact_url = platform.pe_nubefact_master_url or ""
                        self.platform_nubefact_token_display = (
                            "****configurado****" if platform.pe_nubefact_master_token else ""
                        )
                        self.platform_billing_configured = bool(
                            platform.pe_nubefact_master_url
                            and platform.pe_nubefact_master_token
                        )
                    else:
                        self.platform_nubefact_url = ""
                        self.platform_nubefact_token_display = ""
                        self.platform_billing_configured = False
        except Exception:
            logger.exception("Error cargando platform billing config")

    @rx.event
    def platform_set_nubefact_url(self, value: str):
        """Setter para la URL maestra de Nubefact."""
        self.platform_nubefact_url = value or ""

    @rx.event
    async def save_platform_nubefact_url(self):
        """Persiste la URL maestra de Nubefact en DB."""
        if not self.is_owner_authenticated:
            return
        url = self.platform_nubefact_url.strip()
        if url:
            from app.utils.fiscal_validators import validate_nubefact_url
            ok, err = validate_nubefact_url(url)
            if not ok:
                yield rx.toast(err, duration=4000)
                return
        try:
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    from app.models.platform_config import PlatformBillingSettings, PLATFORM_CONFIG_ID
                    from app.utils.timezone import utc_now_naive
                    platform = await session.get(PlatformBillingSettings, PLATFORM_CONFIG_ID)
                    if platform is None:
                        platform = PlatformBillingSettings(id=PLATFORM_CONFIG_ID)
                        session.add(platform)
                    platform.pe_nubefact_master_url = url or None
                    platform.updated_at = utc_now_naive()
                    await session.commit()
            self.platform_billing_configured = bool(
                url and self.platform_nubefact_token_display
            )
            yield rx.toast("URL Nubefact maestra guardada.", duration=3000)
        except Exception:
            logger.exception("Error guardando platform nubefact url")
            yield rx.toast("Error al guardar URL.", duration=4000)

    @rx.event
    async def save_platform_nubefact_token(self, token: str):
        """Persiste el token maestro de Nubefact encriptado en DB."""
        if not self.is_owner_authenticated:
            return
        token = (token or "").strip()
        if not token:
            yield rx.toast("El token no puede estar vacío.", duration=3000)
            return
        try:
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    from app.models.platform_config import PlatformBillingSettings, PLATFORM_CONFIG_ID
                    from app.utils.timezone import utc_now_naive
                    platform = await session.get(PlatformBillingSettings, PLATFORM_CONFIG_ID)
                    if platform is None:
                        platform = PlatformBillingSettings(id=PLATFORM_CONFIG_ID)
                        session.add(platform)
                    platform.pe_nubefact_master_token = encrypt_text(token)
                    platform.updated_at = utc_now_naive()
                    await session.commit()
            self.platform_nubefact_token_display = "****configurado****"
            self.platform_billing_configured = bool(self.platform_nubefact_url)
            yield rx.toast("Token Nubefact maestro guardado y encriptado.", duration=3000)
        except Exception:
            logger.exception("Error guardando platform nubefact token")
            yield rx.toast("Error al guardar token.", duration=4000)

    @rx.event
    async def owner_open_billing_modal(self, company_id: int, company_name: str):
        """Abre modal de gestión de billing y carga config existente."""
        if not self.is_owner_authenticated:
            return
        self.owner_billing_modal_open = True
        self.owner_billing_company_id = company_id
        self.owner_billing_company_name = company_name
        self.owner_billing_loading = True
        yield

        try:
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    from sqlmodel import select as sel_
                    config = (await session.execute(
                        sel_(CompanyBillingConfig).where(
                            CompanyBillingConfig.company_id == company_id
                        )
                    )).scalars().first()

                    if config:
                        self.owner_billing_config_exists = True
                        self.owner_billing_is_active = config.is_active
                        self.owner_billing_environment = config.environment or "sandbox"
                        self.owner_billing_country = config.country or "PE"
                        self.owner_billing_tax_id = config.tax_id or ""
                        self.owner_billing_business_name = config.business_name or ""
                        self.owner_billing_nubefact_url = config.nubefact_url or ""
                        self.owner_billing_nubefact_token_display = (
                            "****configurado****" if config.nubefact_token else ""
                        )
                        self.owner_billing_serie_factura = config.serie_factura or "F001"
                        self.owner_billing_serie_boleta = config.serie_boleta or "B001"
                        self.owner_billing_max_limit = str(config.max_billing_limit or 500)
                        self.owner_billing_afip_punto_venta = str(config.afip_punto_venta or 1)
                        self.owner_billing_emisor_iva = config.emisor_iva_condition or "RI"
                        self.owner_billing_afip_concepto = str(getattr(config, "afip_concepto", 1) or 1)
                        self.owner_billing_ar_threshold = str(
                            config.ar_identification_threshold or "68782"
                        )
                        # Estado de certificados AFIP
                        self.owner_billing_cert_display = (
                            "****certificado****"
                            if config.encrypted_certificate else ""
                        )
                        self.owner_billing_key_display = (
                            "****clave_privada****"
                            if config.encrypted_private_key else ""
                        )
                    else:
                        self.owner_billing_config_exists = False
                        self.owner_billing_is_active = False
                        self.owner_billing_environment = "sandbox"
                        self.owner_billing_country = "PE"
                        self.owner_billing_tax_id = ""
                        self.owner_billing_business_name = ""
                        self.owner_billing_nubefact_url = ""
                        self.owner_billing_nubefact_token_display = ""
                        self.owner_billing_serie_factura = "F001"
                        self.owner_billing_serie_boleta = "B001"
                        self.owner_billing_max_limit = "500"
                        self.owner_billing_afip_punto_venta = "1"
                        self.owner_billing_emisor_iva = "RI"
                        self.owner_billing_afip_concepto = "1"
                        self.owner_billing_ar_threshold = "68782"
                        self.owner_billing_cert_display = ""
                        self.owner_billing_key_display = ""
        except Exception as e:
            logger.exception("Error cargando billing config para owner")
            yield rx.toast("Error al cargar config de billing.", duration=4000)
        finally:
            self.owner_billing_loading = False

    @rx.event
    def owner_close_billing_modal(self):
        self.owner_billing_modal_open = False

    @rx.event
    def owner_set_billing_is_active(self, value: bool):
        self.owner_billing_is_active = value

    @rx.event
    def owner_set_billing_environment(self, value: str):
        self.owner_billing_environment = value or "sandbox"

    @rx.event
    def owner_set_billing_nubefact_url(self, value: str):
        self.owner_billing_nubefact_url = value or ""

    @rx.event
    def owner_set_billing_serie_factura(self, value: str):
        value = (value or "F001").strip().upper()
        import re
        if not re.match(r'^[A-Z]\d{3}$', value):
            return rx.toast("Formato inválido. Usar: F001, F002, etc.", duration=3000)
        self.owner_billing_serie_factura = value

    @rx.event
    def owner_set_billing_serie_boleta(self, value: str):
        value = (value or "B001").strip().upper()
        import re
        if not re.match(r'^[A-Z]\d{3}$', value):
            return rx.toast("Formato inválido. Usar: B001, B002, etc.", duration=3000)
        self.owner_billing_serie_boleta = value

    @rx.event
    def owner_set_billing_max_limit(self, value: str | float):
        self.owner_billing_max_limit = _normalize_non_negative_int_input(str(value))

    @rx.event
    def owner_set_billing_afip_punto_venta(self, value: str | float):
        self.owner_billing_afip_punto_venta = _normalize_non_negative_int_input(str(value))

    @rx.event
    def owner_set_billing_emisor_iva(self, value: str):
        self.owner_billing_emisor_iva = value or "RI"

    @rx.event
    def owner_set_billing_afip_concepto(self, value: str):
        self.owner_billing_afip_concepto = value if value in ("1", "2", "3") else "1"

    @rx.event
    def owner_set_billing_ar_threshold(self, value: str | float):
        self.owner_billing_ar_threshold = _normalize_non_negative_int_input(str(value))

    @rx.event
    async def owner_save_billing_config(self):
        """Guarda la configuración técnica de billing desde el Owner panel."""
        if not self.is_owner_authenticated:
            yield rx.toast("Acceso denegado.", duration=3000)
            return

        company_id = self.owner_billing_company_id
        if not company_id:
            yield rx.toast("Empresa no seleccionada.", duration=3000)
            return

        actor_email = self.owner_session_email or "unknown"
        if _is_owner_rate_limited(actor_email):
            yield rx.toast(
                f"Demasiadas acciones. Espera {OWNER_ACTION_WINDOW_SECONDS}s.",
                duration=5000,
            )
            return

        # ── Validaciones técnicas ──────────────────────────────
        # 1. Validar environment siempre
        env_ok, env_err = validate_environment(
            self.owner_billing_environment
        )
        if not env_ok:
            yield rx.toast(env_err, duration=4000)
            return

        if self.owner_billing_is_active:
            # 2. Razón social obligatoria si billing activo
            bname_ok, bname_err = validate_business_name(
                self.owner_billing_business_name
            )
            if not bname_ok:
                yield rx.toast(
                    f"Razón social: {bname_err}", duration=4000
                )
                return

            # 3. Validar RUC/CUIT según país
            if self.owner_billing_tax_id.strip():
                tid_ok, tid_err = validate_tax_id(
                    self.owner_billing_tax_id,
                    self.owner_billing_country,
                )
                if not tid_ok:
                    yield rx.toast(tid_err, duration=5000)
                    return

            # 4. Validaciones específicas por país
            # Para PE: verificar que la plataforma tenga credenciales maestras
            if self.owner_billing_country == "PE" and self.owner_billing_is_active:
                if not self.platform_billing_configured:
                    yield rx.toast(
                        "Configure primero las credenciales maestras de Nubefact "
                        "en 'Configuración Global de Billing' antes de activar una empresa PE.",
                        duration=6000,
                    )
                    return

        self.owner_billing_loading = True
        yield

        try:
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    from sqlmodel import select as sel_
                    config = (await session.execute(
                        sel_(CompanyBillingConfig).where(
                            CompanyBillingConfig.company_id == company_id
                        )
                    )).scalars().first()

                    if config is None:
                        config = CompanyBillingConfig(company_id=company_id)
                        session.add(config)

                    # Campos técnicos gestionados por el Owner
                    config.is_active = self.owner_billing_is_active
                    config.environment = self.owner_billing_environment.strip()
                    # nubefact_url per-empresa desactivado — se usa credencial maestra de plataforma
                    # config.nubefact_url = self.owner_billing_nubefact_url.strip() or None
                    config.serie_factura = self.owner_billing_serie_factura.strip() or "F001"
                    config.serie_boleta = self.owner_billing_serie_boleta.strip() or "B001"
                    config.afip_punto_venta = max(1, int(
                        self.owner_billing_afip_punto_venta or "1"
                    ))
                    config.emisor_iva_condition = self.owner_billing_emisor_iva.strip() or "RI"
                    try:
                        concepto_val = int(self.owner_billing_afip_concepto or "1")
                        config.afip_concepto = concepto_val if concepto_val in (1, 2, 3) else 1
                    except (TypeError, ValueError):
                        config.afip_concepto = 1
                    try:
                        config.ar_identification_threshold = max(
                            0, int(float(self.owner_billing_ar_threshold or "68782"))
                        )
                    except (TypeError, ValueError):
                        config.ar_identification_threshold = 68782
                    try:
                        config.max_billing_limit = max(
                            0, int(self.owner_billing_max_limit or "500")
                        )
                    except (TypeError, ValueError):
                        config.max_billing_limit = 500
                    config.updated_at = utc_now_naive()

                    session.add(config)
                    await session.commit()

            _record_owner_action(actor_email)
            self.owner_billing_config_exists = True
            logger.info(
                "Owner billing config saved company_id=%s actor=%s active=%s",
                company_id, actor_email, self.owner_billing_is_active,
            )
            yield rx.toast("Configuración de billing guardada.", duration=4000)
        except Exception as e:
            logger.exception("Error guardando billing config desde owner")
            yield rx.toast("Error al guardar config de billing.", duration=5000)
        finally:
            self.owner_billing_loading = False

    @rx.event
    async def owner_save_billing_nubefact_token(self, token: str):
        """Guarda el token de Nubefact encriptado desde el Owner panel."""
        if not self.is_owner_authenticated:
            return
        token = (token or "").strip()
        if not token:
            yield rx.toast("El token no puede estar vacío.", duration=3000)
            return

        company_id = self.owner_billing_company_id
        if not company_id:
            return

        try:
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    from sqlmodel import select as sel_
                    config = (await session.execute(
                        sel_(CompanyBillingConfig).where(
                            CompanyBillingConfig.company_id == company_id
                        )
                    )).scalars().first()

                    if config is None:
                        yield rx.toast(
                            "Guarde la configuración de billing primero.", duration=4000
                        )
                        return

                    config.nubefact_token = encrypt_text(token)
                    config.updated_at = utc_now_naive()
                    session.add(config)
                    await session.commit()

            self.owner_billing_nubefact_token_display = "****configurado****"
            yield rx.toast("Token de Nubefact guardado.", duration=3000)
        except Exception as e:
            logger.exception("Error guardando nubefact token desde owner")
            yield rx.toast("Error al guardar token.", duration=5000)

    # ── Certificados AFIP (Argentina) ─────────────────────────
    owner_billing_cert_display: str = ""
    owner_billing_key_display: str = ""

    @rx.event
    async def owner_save_afip_certificate(self, cert_pem: str):
        """Guarda certificado X.509 PEM encriptado para AFIP."""
        if not self.is_owner_authenticated:
            return
        cert_pem = (cert_pem or "").strip()
        if not cert_pem:
            yield rx.toast("El certificado no puede estar vacío.", duration=3000)
            return
        if "BEGIN CERTIFICATE" not in cert_pem:
            yield rx.toast(
                "Formato inválido. Pegue el contenido completo del .pem "
                "(incluyendo BEGIN/END CERTIFICATE).",
                duration=5000,
            )
            return

        company_id = self.owner_billing_company_id
        if not company_id:
            return

        try:
            # Validar que es un certificado X.509 válido
            from cryptography import x509 as x509_mod
            x509_mod.load_pem_x509_certificate(cert_pem.encode("utf-8"))
        except Exception as exc:
            yield rx.toast(
                f"Certificado inválido: {exc}", duration=5000
            )
            return

        try:
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    from sqlmodel import select as sel_
                    config = (await session.execute(
                        sel_(CompanyBillingConfig).where(
                            CompanyBillingConfig.company_id == company_id
                        )
                    )).scalars().first()
                    if config is None:
                        yield rx.toast(
                            "Guarde la configuración de billing primero.",
                            duration=4000,
                        )
                        return
                    config.encrypted_certificate = encrypt_credential(
                        cert_pem.encode("utf-8")
                    )
                    config.updated_at = utc_now_naive()
                    session.add(config)
                    await session.commit()

            self.owner_billing_cert_display = "****certificado****"
            logger.info(
                "Owner saved AFIP certificate company_id=%s",
                company_id,
            )
            yield rx.toast("Certificado AFIP guardado.", duration=3000)
        except Exception as e:
            logger.exception("Error guardando certificado AFIP")
            yield rx.toast("Error al guardar certificado.", duration=5000)

    @rx.event
    async def owner_save_afip_private_key(self, key_pem: str):
        """Guarda clave privada RSA PEM encriptada para AFIP."""
        if not self.is_owner_authenticated:
            return
        key_pem = (key_pem or "").strip()
        if not key_pem:
            yield rx.toast("La clave privada no puede estar vacía.", duration=3000)
            return
        if "BEGIN" not in key_pem or "KEY" not in key_pem:
            yield rx.toast(
                "Formato inválido. Pegue el contenido completo del .key "
                "(incluyendo BEGIN/END ...KEY).",
                duration=5000,
            )
            return

        company_id = self.owner_billing_company_id
        if not company_id:
            return

        try:
            # Validar que es una clave privada válida
            from cryptography.hazmat.primitives import serialization as ser_
            ser_.load_pem_private_key(key_pem.encode("utf-8"), password=None)
        except Exception as exc:
            yield rx.toast(
                f"Clave privada inválida: {exc}", duration=5000
            )
            return

        try:
            async with AsyncSessionLocal() as session:
                with tenant_bypass():
                    from sqlmodel import select as sel_
                    config = (await session.execute(
                        sel_(CompanyBillingConfig).where(
                            CompanyBillingConfig.company_id == company_id
                        )
                    )).scalars().first()
                    if config is None:
                        yield rx.toast(
                            "Guarde la configuración de billing primero.",
                            duration=4000,
                        )
                        return
                    config.encrypted_private_key = encrypt_credential(
                        key_pem.encode("utf-8")
                    )
                    config.updated_at = utc_now_naive()
                    session.add(config)
                    await session.commit()

            self.owner_billing_key_display = "****clave_privada****"
            logger.info(
                "Owner saved AFIP private key company_id=%s",
                company_id,
            )
            yield rx.toast("Clave privada AFIP guardada.", duration=3000)
        except Exception as e:
            logger.exception("Error guardando clave privada AFIP")
            yield rx.toast("Error al guardar clave privada.", duration=5000)
