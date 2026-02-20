"""Estado de Autenticación - Gestión de usuarios, roles y permisos.

Este módulo maneja toda la lógica de autenticación y autorización:

Funcionalidades principales:
- Login/logout con tokens JWT
- Rate limiting para prevenir fuerza bruta
- Gestión de usuarios (CRUD)
- Gestión de roles y permisos (RBAC)
- Cambio de contraseña obligatorio
- Cache de usuario para optimizar renders

Sistema de permisos:
    Los permisos se definen por rol y se almacenan en BD.
    Roles predefinidos: Superadmin, Administrador, Usuario, Cajero
    Cada permiso controla acceso a funcionalidades específicas.

Seguridad:
- Contraseñas hasheadas con bcrypt
- Tokens JWT con versionado para invalidación
- Rate limiting con soporte Redis (multi-worker)
- Sesiones con expiración configurable

Clases:
    AuthState: Estado principal de autenticación
"""
import os
import time
import reflex as rx
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlmodel import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from app.models import Branch, Company, Permission, Role, User as UserModel, UserBranch
from app.models.company import SubscriptionStatus
from app.utils.auth import create_access_token, decode_token
from app.utils.logger import get_logger
from app.utils.tenant import set_tenant_context, tenant_bypass
from app.utils.rate_limit import (
    is_rate_limited as _is_rate_limited,
    record_failed_attempt as _record_failed_attempt,
    clear_login_attempts as _clear_login_attempts,
    remaining_lockout_time as _remaining_lockout_time,
)
from app.utils.validators import validate_email, validate_password
from app.constants import (
    MAX_LOGIN_ATTEMPTS,
    LOGIN_LOCKOUT_MINUTES,
)
from .types import User, Privileges, NewUser
from .mixin_state import MixinState


# =============================================================================
# CONSTANTES DE PRIVILEGIOS
# =============================================================================

# Constantes
DEFAULT_USER_PRIVILEGES: Privileges = {
    "view_ingresos": True,
    "view_compras": True,
    "create_ingresos": True,
    "view_ventas": True,
    "create_ventas": True,
    "view_inventario": True,
    "edit_inventario": True,
    "view_historial": True,
    "export_data": False,
    "view_cashbox": True,
    "manage_cashbox": True,
    "delete_sales": False,
    "manage_users": False,
    "view_servicios": True,
    "manage_reservations": True,
    "manage_config": False,
    "view_clientes": True,
    "manage_clientes": True,
    "manage_proveedores": True,
    "view_cuentas": True,
    "manage_cuentas": False,
}

ADMIN_PRIVILEGES: Privileges = {
    "view_ingresos": True,
    "view_compras": True,
    "create_ingresos": True,
    "view_ventas": True,
    "create_ventas": True,
    "view_inventario": True,
    "edit_inventario": True,
    "view_historial": True,
    "export_data": True,
    "view_cashbox": True,
    "manage_cashbox": True,
    "delete_sales": True,
    "manage_users": True,
    "view_servicios": True,
    "manage_reservations": True,
    "manage_config": True,
    "view_clientes": True,
    "manage_clientes": True,
    "manage_proveedores": True,
    "view_cuentas": True,
    "manage_cuentas": True,
}

CASHIER_PRIVILEGES: Privileges = {
    "view_ingresos": False,
    "view_compras": False,
    "create_ingresos": False,
    "view_ventas": True,
    "create_ventas": True,
    "view_inventario": True,
    "edit_inventario": False,
    "view_historial": False,
    "export_data": False,
    "view_cashbox": True,
    "manage_cashbox": True,
    "delete_sales": False,
    "manage_users": False,
    "view_servicios": False,
    "manage_reservations": False,
    "manage_config": False,
    "view_clientes": True,
    "manage_clientes": True,
    "manage_proveedores": False,
    "view_cuentas": False,
    "manage_cuentas": False,
}

SUPERADMIN_PRIVILEGES: Privileges = {key: True for key in DEFAULT_USER_PRIVILEGES}

EMPTY_PRIVILEGES: Privileges = {key: False for key in DEFAULT_USER_PRIVILEGES}

DEFAULT_ROLE_TEMPLATES: Dict[str, Privileges] = {
    "Superadmin": SUPERADMIN_PRIVILEGES,
    "Administrador": ADMIN_PRIVILEGES,
    "Usuario": DEFAULT_USER_PRIVILEGES,
    "Cajero": CASHIER_PRIVILEGES,
}

logger = get_logger("AuthState")


class AuthState(MixinState):
    """Estado de autenticación y gestión de usuarios.

    Maneja login, logout, sesiones JWT y administración de usuarios.
    Implementa RBAC (Role-Based Access Control) con permisos granulares.

    Attributes:
        token: JWT almacenado en LocalStorage del navegador
        roles: Lista de nombres de roles disponibles
        role_privileges: Mapeo rol -> dict de permisos
        error_message: Error de login para mostrar al usuario
        show_user_form: Estado del modal de crear/editar usuario
        new_user_data: Datos del formulario de usuario
        editing_user: Usuario siendo editado (None = crear nuevo)

    Variables computadas (rx.var):
        is_authenticated: True si hay sesión válida
        current_user: Usuario actual con permisos (cacheado 30s)

    Eventos principales:
        login(form_data): Inicia sesión
        logout(): Cierra sesión
        change_password(form_data): Cambia contraseña
        save_user(): Crea o actualiza usuario
        delete_user(username): Elimina usuario
    """
    token: str = rx.LocalStorage("")
    selected_branch_id: str = rx.LocalStorage("")
    # users: Dict[str, User] = {} # Eliminado a favor de la BD
    roles: List[str] = ["Superadmin", "Administrador", "Usuario", "Cajero"]
    role_privileges: Dict[str, Privileges] = DEFAULT_ROLE_TEMPLATES.copy()

    error_message: str = ""
    password_change_error: str = ""
    show_login_password: bool = False
    show_user_form_password: bool = False
    show_user_form_confirm_password: bool = False
    needs_initial_admin: bool = False
    show_user_form: bool = False
    user_form_key: int = 0
    branch_access_revision: int = 0
    available_branches: List[Dict[str, Any]] = []
    active_branch_name: str = ""
    plan_actual: str = "unknown"
    company_has_reservations: bool = False
    subscription_snapshot: Dict[str, Any] = {
        "plan_type": "",
        "plan_display": "PLAN",
        "status_label": "Activo",
        "status_tone": "success",
        "is_trial": False,
        "trial_days_left": 0,
        "trial_ends_on": "",
        "max_branches": 0,
        "max_users": 0,
        "branches_used": 0,
        "users_used": 0,
        "branches_percent": 0,
        "users_percent": 0,
        "branches_full": False,
        "users_full": False,
        "branches_limit_label": "0",
        "users_limit_label": "0",
        "users_unlimited": False,
        "branches_unlimited": False,
    }
    payment_alert_info: Dict[str, Any] = {
        "show": False,
        "color": "yellow",
        "message": "",
    }
    new_user_data: NewUser = {
        "username": "",
        "email": "",
        "password": "",
        "confirm_password": "",
        "role": "Usuario",
        "privileges": DEFAULT_USER_PRIVILEGES.copy(),
    }
    editing_user: Optional[Dict[str, Any]] = None
    new_role_name: str = ""
    show_user_limit_modal: bool = False
    user_limit_modal_message: str = ""

    # Cache de usuario para evitar consultas repetidas a BD (backend-only).
    # Usamos campos no-reactivos para evitar recursión al calcular vars.
    _cached_user: Optional[User] = rx.field(default=None, is_var=False)
    _cached_user_token: str = rx.field(default="", is_var=False)
    _cached_user_time: float = rx.field(default=0.0, is_var=False)
    _roles_bootstrap_ts: float = rx.field(default=0.0, is_var=False)
    _subscription_check_ts: float = rx.field(default=0.0, is_var=False)
    _USER_CACHE_TTL: float = 30.0  # Segundos de validez del cache

    @rx.event
    def toggle_login_password_visibility(self):
        self.show_login_password = not self.show_login_password

    @rx.event
    def toggle_user_form_password_visibility(self):
        self.show_user_form_password = not self.show_user_form_password

    @rx.event
    def toggle_user_form_confirm_password_visibility(self):
        self.show_user_form_confirm_password = (
            not self.show_user_form_confirm_password
        )

    @rx.var(cache=True)
    def is_authenticated(self) -> bool:
        user = self.current_user
        return bool(user and user.get("username") != "Invitado")

    @rx.var(cache=True)
    def current_user(self) -> User:
        # Verificar cache válido
        now = time.time()
        if (
            self._cached_user is not None
            and self._cached_user_token == self.token
            and (now - self._cached_user_time) < self._USER_CACHE_TTL
        ):
            return self._cached_user

        # Cache inválido, recargar
        payload = decode_token(self.token)
        if not payload:
            self._cached_user = self._guest_user()
            self._cached_user_token = self.token
            self._cached_user_time = now
            return self._cached_user

        subject = payload.get("sub")
        if subject is None:
            self._cached_user = self._guest_user()
            self._cached_user_token = self.token
            self._cached_user_time = now
            return self._cached_user

        subject_str = str(subject).strip()
        if not subject_str:
            self._cached_user = self._guest_user()
            self._cached_user_token = self.token
            self._cached_user_time = now
            return self._cached_user

        token_version = payload.get("ver", 0)
        try:
            token_version = int(token_version or 0)
        except (TypeError, ValueError):
            token_version = 0

        user_id = None
        try:
            user_id = int(subject_str)
        except (TypeError, ValueError):
            user_id = None

        with rx.session() as session:
            user = None
            query = (
                select(UserModel)
                .options(selectinload(UserModel.role).selectinload(Role.permissions))
                .execution_options(tenant_bypass=True)
            )
            if user_id is not None:
                user = session.exec(
                    query.where(UserModel.id == user_id)
                ).first()
            else:
                lookup = subject_str.lower()
                if "@" in lookup:
                    user = session.exec(
                        query.where(UserModel.email == lookup)
                    ).first()
                else:
                    users = session.exec(
                        query.where(UserModel.username == lookup)
                    ).all()
                    if len(users) == 1:
                        user = users[0]

            if user and user.is_active:
                if getattr(user, "token_version", 0) != token_version:
                    self._cached_user = self._guest_user()
                else:
                    role_name = user.role.name if user.role else "Sin rol"
                    set_tenant_context(
                        getattr(user, "company_id", None),
                        getattr(user, "branch_id", None),
                    )
                    self._cached_user = {
                        "id": user.id,
                        "company_id": getattr(user, "company_id", None),
                        "username": user.username,
                        "email": getattr(user, "email", "") or "",
                        "role": role_name,
                        "privileges": self._get_privileges_dict(user),
                        "must_change_password": bool(
                            getattr(user, "must_change_password", False)
                        ),
                    }
            else:
                self._cached_user = self._guest_user()

        self._cached_user_token = self.token
        self._cached_user_time = now
        return self._cached_user

    @rx.var(cache=True)
    def active_branch_id(self) -> int | None:
        value = self.selected_branch_id
        if not value:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _default_subscription_snapshot(self) -> Dict[str, Any]:
        return {
            "plan_type": "",
            "plan_display": "PLAN",
            "status_label": "Activo",
            "status_tone": "success",
            "is_trial": False,
            "trial_days_left": 0,
            "trial_ends_on": "",
            "max_branches": 0,
            "max_users": 0,
            "branches_used": 0,
            "users_used": 0,
            "branches_percent": 0,
            "users_percent": 0,
            "branches_full": False,
            "users_full": False,
            "branches_limit_label": "0",
            "users_limit_label": "0",
            "users_unlimited": False,
            "branches_unlimited": False,
        }

    def _default_payment_alert_info(self) -> Dict[str, Any]:
        return {"show": False, "color": "yellow", "message": ""}

    def _safe_int(self, value: Any, fallback: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def _build_subscription_snapshot(
        self,
        company: Company | None,
        branches_used: int = 0,
        users_used: int = 0,
    ) -> Dict[str, Any]:
        if not company:
            return self._default_subscription_snapshot()

        plan_type = getattr(company, "plan_type", "") or ""
        if hasattr(plan_type, "value"):
            plan_type = plan_type.value
        plan_type = str(plan_type or "").strip().lower()
        is_trial = plan_type == "trial"

        trial_ends_at = getattr(company, "trial_ends_at", None)
        now = datetime.now()
        is_expired = bool(is_trial and trial_ends_at and trial_ends_at < now)
        status_label = "Vencido" if is_expired else "Activo"
        status_tone = "danger" if is_expired else ("warning" if is_trial else "success")
        if not is_trial:
            sub_status = getattr(company, "subscription_status", "")
            if hasattr(sub_status, "value"):
                sub_status = sub_status.value
            sub_status = str(sub_status or "").strip().lower()
            if sub_status == SubscriptionStatus.WARNING.value:
                status_label = "Por vencer"
                status_tone = "warning"
            elif sub_status == SubscriptionStatus.PAST_DUE.value:
                status_label = "Pago vencido"
                status_tone = "danger"
            elif sub_status == SubscriptionStatus.SUSPENDED.value:
                status_label = "Suspendido"
                status_tone = "danger"

        trial_days_left = 0
        trial_ends_on = ""
        if is_trial and trial_ends_at:
            trial_days_left = max((trial_ends_at.date() - now.date()).days, 0)
            trial_ends_on = trial_ends_at.strftime("%d/%m/%Y")

        max_branches = self._safe_int(getattr(company, "max_branches", 0), 0)
        max_users = self._safe_int(getattr(company, "max_users", 0), 0)
        branches_used = self._safe_int(branches_used, 0)
        users_used = self._safe_int(users_used, 0)

        users_unlimited = max_users < 0 or max_users >= 999
        branches_unlimited = max_branches < 0 or max_branches >= 999

        branches_percent = (
            0
            if branches_unlimited
            else min(int(round((branches_used / max_branches) * 100)), 100)
        ) if max_branches > 0 else 0
        users_percent = (
            0
            if users_unlimited
            else min(int(round((users_used / max_users) * 100)), 100)
        ) if max_users > 0 else 0

        branches_full = (
            False if branches_unlimited else (max_branches > 0 and branches_used >= max_branches)
        )
        users_full = (
            False if users_unlimited else (max_users > 0 and users_used >= max_users)
        )

        return {
            "plan_type": plan_type,
            "plan_display": f"PLAN {plan_type.upper()}" if plan_type else "PLAN",
            "status_label": status_label,
            "status_tone": status_tone,
            "is_trial": is_trial,
            "trial_days_left": trial_days_left,
            "trial_ends_on": trial_ends_on,
            "max_branches": max_branches,
            "max_users": max_users,
            "branches_used": branches_used,
            "users_used": users_used,
            "branches_percent": branches_percent,
            "users_percent": users_percent,
            "branches_full": branches_full,
            "users_full": users_full,
            "branches_limit_label": "Ilimitado" if branches_unlimited else str(max_branches),
            "users_limit_label": "Ilimitado" if users_unlimited else str(max_users),
            "users_unlimited": users_unlimited,
            "branches_unlimited": branches_unlimited,
        }

    @rx.event
    def refresh_subscription_snapshot(self):
        company_id = self._company_id()
        if not company_id:
            self.plan_actual = "unknown"
            self.company_has_reservations = False
            self.subscription_snapshot = self._default_subscription_snapshot()
            return

        with rx.session() as session:
            company = session.exec(
                select(Company).where(Company.id == company_id)
            ).first()
            if not company:
                self.plan_actual = "unknown"
                self.company_has_reservations = False
                self.subscription_snapshot = self._default_subscription_snapshot()
                return

            branches_used = session.exec(
                select(func.count(Branch.id)).where(Branch.company_id == company_id)
            ).one()
            users_used = session.exec(
                select(func.count(UserModel.id))
                .where(UserModel.company_id == company_id)
                .where(UserModel.is_active == True)
            ).one()

        self.subscription_snapshot = self._build_subscription_snapshot(
            company,
            branches_used=self._safe_int(branches_used, 0),
            users_used=self._safe_int(users_used, 0),
        )
        self.plan_actual = self.subscription_snapshot.get("plan_type", "") or "unknown"
        self.company_has_reservations = bool(
            getattr(company, "has_reservations_module", False)
        )

    @rx.event
    def refresh_payment_alert_info(self):
        default = self._default_payment_alert_info()
        company_id = self._company_id()
        if not company_id:
            self.payment_alert_info = default
            return
        with rx.session() as session:
            company = session.exec(
                select(Company).where(Company.id == company_id)
            ).first()
        if not company:
            self.payment_alert_info = default
            return

        plan_type = getattr(company, "plan_type", "")
        if hasattr(plan_type, "value"):
            plan_type = plan_type.value
        plan_type = str(plan_type or "").strip().lower()
        if plan_type == "trial":
            self.payment_alert_info = default
            return

        subscription_ends_at = getattr(company, "subscription_ends_at", None)
        if not subscription_ends_at:
            self.payment_alert_info = default
            return

        now = datetime.now()
        days_remaining = (subscription_ends_at.date() - now.date()).days
        if days_remaining > 5:
            self.payment_alert_info = default
            return
        if days_remaining >= 0:
            self.payment_alert_info = {
                "show": True,
                "color": "yellow",
                "message": f"Tu plan vence en {days_remaining} días.",
            }
            return
        if days_remaining >= -5:
            grace_left = max(0, 5 - abs(days_remaining))
            self.payment_alert_info = {
                "show": True,
                "color": "red",
                "message": (
                    "¡Pago vencido! "
                    f"Tienes {grace_left} días de gracia antes del corte."
                ),
            }
            return
        self.payment_alert_info = default

    @rx.event
    def refresh_branch_access_cache(self):
        _ = self.branch_access_revision
        user_id = self.current_user.get("id")
        company_id = self.current_user.get("company_id")
        if not user_id or not company_id:
            self.available_branches = []
            self.active_branch_name = ""
            return

        set_tenant_context(company_id, None)
        with rx.session() as session:
            user = session.exec(
                select(UserModel)
                .where(UserModel.id == user_id)
                .where(UserModel.company_id == company_id)
            ).first()
            if not user:
                self.available_branches = []
                self.active_branch_name = ""
                return

            branch_ids = self._user_branch_ids(session, user_id)
            if not branch_ids:
                self.available_branches = []
                self.active_branch_name = ""
                return

            rows = session.exec(
                select(Branch)
                .where(Branch.id.in_(branch_ids))
                .where(Branch.company_id == company_id)
                .order_by(Branch.name)
            ).all()

        self.available_branches = [
            {"id": str(branch.id), "name": branch.name}
            for branch in rows
        ]

        active_id = self.active_branch_id
        if not active_id and self.available_branches:
            self.selected_branch_id = self.available_branches[0]["id"]
            active_id = self.active_branch_id

        selected = next(
            (
                branch
                for branch in self.available_branches
                if int(branch["id"]) == int(active_id)
            ),
            None,
        ) if active_id else None
        self.active_branch_name = selected["name"] if selected else ""

    @rx.event
    def refresh_auth_runtime_cache(self):
        self._refresh_subscription_and_payment_alert()
        self.refresh_branch_access_cache()

    def _refresh_subscription_and_payment_alert(self):
        """Consolidar Company query: subscription + payment alert en una sola lectura."""
        company_id = self._company_id()
        default_alert = self._default_payment_alert_info()
        if not company_id:
            self.plan_actual = "unknown"
            self.company_has_reservations = False
            self.subscription_snapshot = self._default_subscription_snapshot()
            self.payment_alert_info = default_alert
            return

        with rx.session() as session:
            company = session.exec(
                select(Company).where(Company.id == company_id)
            ).first()
            if not company:
                self.plan_actual = "unknown"
                self.company_has_reservations = False
                self.subscription_snapshot = self._default_subscription_snapshot()
                self.payment_alert_info = default_alert
                return

            branches_used = session.exec(
                select(func.count(Branch.id)).where(Branch.company_id == company_id)
            ).one()
            users_used = session.exec(
                select(func.count(UserModel.id))
                .where(UserModel.company_id == company_id)
                .where(UserModel.is_active == True)
            ).one()

        # --- Subscription snapshot ---
        self.subscription_snapshot = self._build_subscription_snapshot(
            company,
            branches_used=self._safe_int(branches_used, 0),
            users_used=self._safe_int(users_used, 0),
        )
        self.plan_actual = self.subscription_snapshot.get("plan_type", "") or "unknown"
        self.company_has_reservations = bool(
            getattr(company, "has_reservations_module", False)
        )

        # --- Payment alert (reutiliza el mismo company object) ---
        plan_type = getattr(company, "plan_type", "")
        if hasattr(plan_type, "value"):
            plan_type = plan_type.value
        plan_type = str(plan_type or "").strip().lower()
        if plan_type == "trial":
            self.payment_alert_info = default_alert
            return

        subscription_ends_at = getattr(company, "subscription_ends_at", None)
        if not subscription_ends_at:
            self.payment_alert_info = default_alert
            return

        now = datetime.now()
        days_remaining = (subscription_ends_at.date() - now.date()).days
        if days_remaining > 5:
            self.payment_alert_info = default_alert
            return
        if days_remaining >= 0:
            self.payment_alert_info = {
                "show": True,
                "color": "yellow",
                "message": f"Tu plan vence en {days_remaining} días.",
            }
            return
        if days_remaining >= -5:
            grace_left = max(0, 5 - abs(days_remaining))
            self.payment_alert_info = {
                "show": True,
                "color": "red",
                "message": (
                    "¡Pago vencido! "
                    f"Tienes {grace_left} días de gracia antes del corte."
                ),
            }
            return
        self.payment_alert_info = default_alert

    def invalidate_user_cache(self) -> None:
        """Invalida el cache de usuario (llamar tras cambios de permisos)."""
        self._cached_user = None
        self._cached_user_token = ""
        self._cached_user_time = 0.0
        self.available_branches = []
        self.active_branch_name = ""
        self.plan_actual = "unknown"
        self.company_has_reservations = False
        self.subscription_snapshot = self._default_subscription_snapshot()
        self.payment_alert_info = self._default_payment_alert_info()

    # =========================================================================
    # COMPUTED VARS DE PERMISOS - Para renderizado condicional en páginas
    # =========================================================================

    @rx.var(cache=True)
    def plan_actual_str(self) -> str:
        return (self.plan_actual or "").strip().lower() or "unknown"

    @rx.var(cache=True)
    def can_view_ingresos(self) -> bool:
        return bool(self.current_user["privileges"].get("view_ingresos"))

    @rx.var(cache=True)
    def can_view_compras(self) -> bool:
        privileges = self.current_user["privileges"]
        return bool(privileges.get("view_compras") or privileges.get("view_ingresos"))

    @rx.var(cache=True)
    def can_manage_compras(self) -> bool:
        return bool(self.current_user["privileges"].get("create_ingresos"))

    @rx.var(cache=True)
    def can_view_ventas(self) -> bool:
        return bool(self.current_user["privileges"].get("view_ventas"))

    @rx.var(cache=True)
    def can_view_cashbox(self) -> bool:
        return bool(self.current_user["privileges"].get("view_cashbox"))

    @rx.var(cache=True)
    def can_view_inventario(self) -> bool:
        return bool(self.current_user["privileges"].get("view_inventario"))

    @rx.var(cache=True)
    def can_view_historial(self) -> bool:
        return bool(self.current_user["privileges"].get("view_historial"))

    @rx.var(cache=True)
    def can_export_data(self) -> bool:
        return bool(self.current_user["privileges"].get("export_data"))

    @rx.var(cache=True)
    def can_view_servicios(self) -> bool:
        plan = self.plan_actual_str
        if plan == "standard":
            return False
        return bool(
            self.current_user["privileges"].get("view_servicios")
            and self.company_has_reservations
        )

    @rx.var(cache=True)
    def can_view_clientes(self) -> bool:
        if self.plan_actual_str == "standard":
            return False
        return bool(self.current_user["privileges"].get("view_clientes"))

    @rx.var(cache=True)
    def can_manage_proveedores(self) -> bool:
        privileges = self.current_user["privileges"]
        return bool(
            privileges.get("manage_proveedores") or privileges.get("manage_clientes")
        )

    @rx.var(cache=True)
    def can_view_cuentas(self) -> bool:
        if self.plan_actual_str == "standard":
            return False
        return bool(self.current_user["privileges"].get("view_cuentas"))

    @rx.var(cache=True)
    def can_manage_config(self) -> bool:
        return bool(self.current_user["privileges"].get("manage_config"))

    @rx.var(cache=True)
    def plan_name(self) -> str:
        return str(self.subscription_snapshot.get("plan_type", "") or "")

    @rx.var(cache=True)
    def is_admin(self) -> bool:
        return self.current_user["role"] in ["Superadmin", "Administrador"]

    users_list: List[User] = []

    def load_users(self):
        if not self.current_user["privileges"].get("manage_users"):
            self.users_list = []
            return
        company_id = self._company_id()
        if not company_id:
            self.users_list = []
            return
        # Refuerza el contexto tenant para evitar errores en background/write queue.
        set_tenant_context(company_id, None)
        with rx.session() as session:
            users = session.exec(
                select(UserModel)
                .where(UserModel.company_id == company_id)
                .options(selectinload(UserModel.role).selectinload(Role.permissions))
                .execution_options(tenant_company_id=company_id)
            ).all()
            self._load_roles_cache(session, company_id=company_id)
            normalized_users = []
            for user in users:
                role_name = user.role.name if user.role else "Sin rol"
                normalized_users.append({
                    "id": user.id,
                    "company_id": getattr(user, "company_id", None),
                    "username": user.username,
                    "email": getattr(user, "email", "") or "",
                    "role": role_name,
                    "privileges": self._get_privileges_dict(user),
                    "must_change_password": bool(
                        getattr(user, "must_change_password", False)
                    ),
                })
            self.users_list = sorted(normalized_users, key=lambda u: u["username"])

    def _guest_user(self) -> User:
        return {
            "id": None,
            "company_id": None,
            "username": "Invitado",
            "email": "",
            "role": "Invitado",
            "privileges": EMPTY_PRIVILEGES.copy(),
            "must_change_password": False,
        }

    def _normalize_privileges(self, privileges: Dict[str, bool]) -> Privileges:
        normalized = EMPTY_PRIVILEGES.copy()
        normalized.update(privileges)
        return normalized

    def _get_privileges_dict(self, user: UserModel | None) -> Privileges:
        if not user or not user.role:
            return EMPTY_PRIVILEGES.copy()
        permissions = {
            perm.codename: True
            for perm in (user.role.permissions or [])
            if perm.codename
        }
        role_name = (user.role.name or "").strip().lower()
        if role_name == "superadmin":
            all_privileges = {key: True for key in DEFAULT_USER_PRIVILEGES}
            all_privileges.update(permissions)
            return self._normalize_privileges(all_privileges)
        return self._normalize_privileges(permissions)

    def _load_roles_cache(self, session, company_id: int | None = None):
        scoped_company_id = int(company_id) if company_id else None
        if not scoped_company_id:
            self.roles = list(DEFAULT_ROLE_TEMPLATES)
            self.role_privileges = DEFAULT_ROLE_TEMPLATES.copy()
            return

        roles = session.exec(
            select(Role)
            .where(Role.company_id == scoped_company_id)
            .options(selectinload(Role.permissions))
        ).all()
        if not roles:
            self.roles = list(DEFAULT_ROLE_TEMPLATES)
            self.role_privileges = DEFAULT_ROLE_TEMPLATES.copy()
            return
        self.roles = [role.name for role in roles]
        self.role_privileges = {
            role.name: self._normalize_privileges(
                {
                    perm.codename: True
                    for perm in (role.permissions or [])
                    if perm.codename
                }
            )
            for role in roles
        }

    def _user_branch_ids(self, session, user_id: int) -> list[int]:
        if not user_id:
            return []
        rows = session.exec(
            select(UserBranch.branch_id).where(UserBranch.user_id == user_id)
        ).all()
        return [int(row) for row in rows if row]

    def _ensure_user_branch_access(self, session, user: UserModel) -> tuple[list[int], bool]:
        if not user:
            return [], False
        return self._user_branch_ids(session, user.id), False

    def _select_default_branch(
        self,
        session,
        user: UserModel,
        branch_ids: list[int],
    ) -> int | None:
        if not branch_ids:
            return None
        stored = getattr(self, "selected_branch_id", "") or ""
        try:
            stored_id = int(stored) if stored else None
        except (TypeError, ValueError):
            stored_id = None
        if stored_id and stored_id in branch_ids:
            return stored_id
        default_branch_id = getattr(user, "branch_id", None)
        if default_branch_id and default_branch_id in branch_ids:
            return int(default_branch_id)
        return branch_ids[0]

    def _ensure_permissions(self, session, codenames: list[str]) -> Dict[str, Permission]:
        if not codenames:
            return {}
        existing = session.exec(
            select(Permission).where(Permission.codename.in_(codenames))
        ).all()
        by_code = {perm.codename: perm for perm in existing if perm.codename}
        for code in codenames:
            if code not in by_code:
                perm = Permission(codename=code, description="")
                session.add(perm)
                by_code[code] = perm
        session.flush()
        return by_code

    def _get_role_by_name(
        self,
        session,
        role_name: str,
        company_id: int | None = None,
    ) -> Role | None:
        target = (role_name or "").strip().lower()
        if not target:
            return None
        scoped_company_id = int(company_id) if company_id else None
        if scoped_company_id is None:
            return None
        return session.exec(
            select(Role)
            .where(func.lower(Role.name) == target)
            .where(Role.company_id == scoped_company_id)
            .options(selectinload(Role.permissions))
            .execution_options(tenant_company_id=scoped_company_id)
        ).first()

    def _ensure_role(
        self,
        session,
        role_name: str,
        privileges: Privileges,
        company_id: int | None = None,
        overwrite: bool = False,
    ) -> Role:
        scoped_company_id = int(company_id) if company_id else None
        if scoped_company_id is None:
            raise RuntimeError("company_id requerido para crear/editar roles.")

        role = self._get_role_by_name(
            session,
            role_name,
            company_id=scoped_company_id,
        )
        if not role:
            role = Role(
                company_id=scoped_company_id,
                name=role_name,
                description="",
            )
            session.add(role)
            session.flush()
        if overwrite or not role.permissions:
            permission_map = self._ensure_permissions(
                session, list(privileges.keys())
            )
            role.permissions = [
                permission_map[code]
                for code, enabled in privileges.items()
                if enabled
            ]
            session.add(role)
        return role

    def _bootstrap_default_roles(self, session, company_id: int | None):
        scoped_company_id = int(company_id) if company_id else None
        # Siempre asegurar catálogo de permisos global.
        permission_map = self._ensure_permissions(
            session, list(DEFAULT_USER_PRIVILEGES.keys())
        )
        if scoped_company_id is None:
            self._load_roles_cache(session, None)
            return

        created_any = False
        for role_name, privileges in DEFAULT_ROLE_TEMPLATES.items():
            existing_role = self._get_role_by_name(
                session,
                role_name,
                company_id=scoped_company_id,
            )
            if existing_role:
                continue
            role = Role(
                company_id=scoped_company_id,
                name=role_name,
                description="",
            )
            role.permissions = [
                permission_map[code]
                for code, enabled in privileges.items()
                if enabled
            ]
            session.add(role)
            created_any = True
        if created_any:
            session.flush()
        self._load_roles_cache(session, scoped_company_id)

    def _role_privileges(self, role: str) -> Privileges:
        role_key = self._find_role_key(role)
        if role_key and role_key in self.role_privileges:
            return self._normalize_privileges(self.role_privileges[role_key])
        return self._normalize_privileges(DEFAULT_USER_PRIVILEGES)

    def _find_role_key(self, role_name: str) -> str | None:
        target = (role_name or "").lower().strip()
        for r in self.roles:
            if r.lower() == target:
                return r
        return None

    def _reset_new_user_form(self):
        self.new_user_data = {
            "username": "",
            "email": "",
            "password": "",
            "confirm_password": "",
            "role": "Usuario",
            "privileges": self._role_privileges("Usuario"),
        }
        self.editing_user = None
        self.new_role_name = ""
        self.show_user_form_password = False
        self.show_user_form_confirm_password = False

    def _resolve_env(self) -> str:
        value = (os.getenv("ENV") or "dev").strip().lower()
        if value in {"prod", "production"}:
            return "prod"
        return "dev"

    def _trial_enforced(self) -> bool:
        value = os.getenv("TRIAL_ENFORCEMENT")
        if value is not None:
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return self._resolve_env() != "dev"

    def _initial_admin_password(self) -> str | None:
        value = (os.getenv("INITIAL_ADMIN_PASSWORD") or "").strip()
        return value or None

    def _allow_default_admin(self) -> bool:
        value = (os.getenv("ALLOW_DEFAULT_ADMIN") or "").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _get_or_create_bootstrap_company_and_branch(
        self,
        session,
    ) -> tuple[Company, Branch]:
        company = session.exec(
            select(Company).order_by(Company.id.asc())
        ).first()
        if not company:
            now = datetime.now()
            company = Company(
                name="Empresa Inicial",
                ruc=f"BOOT{time.time_ns()}",
                is_active=True,
                trial_ends_at=now + timedelta(days=3650),
                created_at=now,
                plan_type="enterprise",
                max_branches=999,
                max_users=999,
                has_reservations_module=True,
                has_electronic_billing=False,
                subscription_status=SubscriptionStatus.ACTIVE.value,
            )
            session.add(company)
            session.flush()

        branch = session.exec(
            select(Branch)
            .where(Branch.company_id == company.id)
            .order_by(Branch.id.asc())
        ).first()
        if not branch:
            branch = Branch(
                company_id=company.id,
                name="Casa Matriz",
                address="",
            )
            session.add(branch)
            session.flush()
        return company, branch

    def _default_route_for_privileges(self, privileges: Dict[str, bool]) -> str:
        """Determina la ruta inicial según los privilegios del usuario.

        El Dashboard es accesible para todos, por lo que siempre es una opción válida.
        La prioridad es: Dashboard > Ingreso > Venta > Caja > etc.
        """
        # Dashboard siempre es accesible para todos
        # Pero priorizamos la página que el usuario use más frecuentemente
        if privileges.get("view_ingresos"):
            return "/ingreso"
        if privileges.get("view_compras"):
            return "/compras"
        if privileges.get("view_ventas"):
            return "/venta"
        if privileges.get("view_cashbox"):
            return "/caja"
        if privileges.get("view_inventario"):
            return "/inventario"
        if privileges.get("view_historial"):
            return "/historial"
        if privileges.get("view_servicios"):
            return "/servicios"
        if privileges.get("view_clientes"):
            return "/clientes"
        if privileges.get("view_cuentas"):
            return "/cuentas"
        if privileges.get("manage_config"):
            return "/configuracion"
        # Fallback: Dashboard es accesible para todos
        return "/dashboard"

    @rx.event
    def ensure_roles_and_permissions(self):
        now = time.time()
        # Evita recalcular catálogo de roles/permisos en cada navegación.
        if (now - self._roles_bootstrap_ts) < 300:
            return
        self._roles_bootstrap_ts = now
        # En arranque puede no existir tenant seleccionado.
        company_id = self._company_id()
        with tenant_bypass():
            with rx.session() as session:
                self._bootstrap_default_roles(session, company_id)
                session.commit()
                user_count = session.exec(select(func.count(UserModel.id))).one()
                self.needs_initial_admin = not user_count or user_count == 0

    @rx.event
    def run_common_guards(self):
        """Agrupa validaciones globales para minimizar eventos on_load encadenados."""
        self.ensure_roles_and_permissions()
        redirect_action = self.check_subscription_status()
        if redirect_action:
            return redirect_action
        redirect_action = self.ensure_subscription_active()
        if redirect_action:
            return redirect_action
        redirect_action = self.ensure_trial_active()
        if redirect_action:
            return redirect_action
        redirect_action = self.ensure_password_change()
        if redirect_action:
            return redirect_action

    @rx.event
    def ensure_view_ingresos(self):
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
            return
        if not self.current_user["privileges"].get("view_ingresos"):
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Ingresos.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")

    @rx.event
    def ensure_view_compras(self):
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

    @rx.event
    def ensure_view_ventas(self):
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
            return
        if not self.current_user["privileges"].get("view_ventas"):
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Ventas.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")

    @rx.event
    def ensure_view_cashbox(self):
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
            return
        if not self.current_user["privileges"].get("view_cashbox"):
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Caja.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")

    @rx.event
    def ensure_view_inventario(self):
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
            return
        if not self.current_user["privileges"].get("view_inventario"):
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Inventario.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")

    @rx.event
    def ensure_view_historial(self):
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
            return
        if not self.current_user["privileges"].get("view_historial"):
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Historial.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")

    @rx.event
    def ensure_export_data(self):
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
            return
        if not self.current_user["privileges"].get("export_data"):
            yield rx.toast(
                "Acceso denegado: No tienes permiso para exportar reportes.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")

    @rx.event
    def ensure_view_servicios(self):
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
            return
        if not self.can_view_servicios:
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Servicios.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")

    @rx.event
    def ensure_view_clientes(self):
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
            return
        if not self.can_view_clientes:
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Clientes.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")

    @rx.event
    def ensure_view_cuentas(self):
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
            return
        if not self.can_view_cuentas:
            yield rx.toast(
                "Acceso denegado: No tienes permiso para ver Cuentas.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")

    @rx.event
    def ensure_admin_access(self):
        if not self.is_authenticated:
            yield rx.redirect("/ingreso")
            return
        # Verifica roles exactos segun tu DB (Mayusculas importan)
        if self.current_user["role"] not in ["Superadmin", "Administrador"]:
            yield rx.toast(
                "Acceso denegado: Se requiere nivel de Administrador.",
                duration=3000,
            )
            yield rx.redirect("/dashboard")

    @rx.event
    def check_subscription_status(self):
        """Verifica el estado de suscripción usando el snapshot cacheado.

        Solo hace query a DB si necesita MODIFICAR el estado de suscripción
        (trial expirado, plan vencido). En caso normal, lee del snapshot
        que ya cargó refresh_auth_runtime_cache() — sin query extra.
        """
        if not self.is_authenticated:
            return
        now_epoch = time.time()
        if (now_epoch - self._subscription_check_ts) < 30:
            return
        self._subscription_check_ts = now_epoch

        # Usar el snapshot que ya cargó refresh_auth_runtime_cache (sin DB query)
        snapshot = self.subscription_snapshot
        current_path = self.router.url.path
        status_label = str(snapshot.get("status_label", "") or "").strip().lower()
        is_trial = bool(snapshot.get("is_trial"))
        plan_type = str(snapshot.get("plan_type", "") or "").strip().lower()

        # --- Trial expirado: necesita ir a DB para actualizar status ---
        if is_trial:
            trial_end = snapshot.get("trial_ends_on", "")
            if trial_end:
                try:
                    from datetime import datetime as dt_cls
                    trial_ends_at = dt_cls.strptime(trial_end, "%d/%m/%Y")
                    if trial_ends_at < datetime.now():
                        # Trial expirado — actualizar en DB
                        company_id = self.current_user.get("company_id")
                        if company_id:
                            with rx.session() as session:
                                company = session.exec(
                                    select(Company).where(Company.id == company_id)
                                ).first()
                                if company:
                                    current_status = getattr(company, "subscription_status", "")
                                    if hasattr(current_status, "value"):
                                        current_status = current_status.value
                                    if str(current_status or "") != SubscriptionStatus.SUSPENDED.value:
                                        company.subscription_status = SubscriptionStatus.SUSPENDED.value
                                        session.add(company)
                                        session.commit()
                                    self.refresh_subscription_snapshot()
                        if current_path != "/periodo-prueba-finalizado":
                            return rx.redirect("/periodo-prueba-finalizado")
                        return
                except (ValueError, TypeError):
                    pass
            return  # Trial activo, nada que hacer

        # --- Plan pago: verificar vencimiento desde snapshot ---
        if status_label == "suspendido" and current_path != "/cuenta-suspendida":
            return rx.redirect("/cuenta-suspendida")

    @rx.event
    def ensure_subscription_active(self):
        if not self.is_authenticated:
            return
        current_path = self.router.url.path
        if current_path in {"/cuenta-suspendida", "/periodo-prueba-finalizado"}:
            return
        snapshot = self.subscription_snapshot
        if bool(snapshot.get("is_trial")):
            return
        status_label = str(snapshot.get("status_label", "") or "").strip().lower()
        if status_label == "suspendido":
            return rx.redirect("/cuenta-suspendida")

    @rx.event
    def ensure_trial_active(self):
        if not self.is_authenticated:
            return
        if not self._trial_enforced():
            return
        current_path = self.router.url.path
        if current_path == "/periodo-prueba-finalizado":
            return
        snapshot = self.subscription_snapshot
        if not bool(snapshot.get("is_trial")):
            return
        status_label = str(snapshot.get("status_label", "") or "").strip().lower()
        if status_label == "vencido":
            return rx.redirect("/periodo-prueba-finalizado")

    @rx.event
    def ensure_password_change(self):
        if not self.is_authenticated:
            if self.router.url.path != "/ingreso":
                return rx.redirect("/ingreso")
            return
        must_change = self.current_user.get("must_change_password", False)
        current_path = self.router.url.path
        if must_change and current_path != "/cambiar-clave":
            return rx.redirect("/cambiar-clave")
        if not must_change and current_path == "/cambiar-clave":
            return rx.redirect(
                self._default_route_for_privileges(
                    self.current_user["privileges"]
                )
            )

    @rx.event
    async def set_active_branch(self, branch_id: str):
        user_id = self.current_user.get("id")
        company_id = self.current_user.get("company_id")
        if not user_id or not company_id:
            return rx.toast("Usuario no encontrado.", duration=3000)
        try:
            branch_id_int = int(branch_id)
        except (TypeError, ValueError):
            return rx.toast("Sucursal invalida.", duration=3000)
        with rx.session() as session:
            allowed = session.exec(
                select(UserBranch)
                .join(Branch, Branch.id == UserBranch.branch_id)
                .where(UserBranch.user_id == user_id)
                .where(UserBranch.branch_id == branch_id_int)
                .where(Branch.company_id == company_id)
            ).first()
            if not allowed:
                return rx.toast("No tiene acceso a esta sucursal.", duration=3000)
        self.selected_branch_id = str(branch_id_int)
        self.refresh_auth_runtime_cache()
        if hasattr(self, "refresh_cashbox_status"):
            self.refresh_cashbox_status()

        # Invalidar TTLs para que page_init_* recargue datos al navegar
        if hasattr(self, "_last_suppliers_load_ts"):
            self._last_suppliers_load_ts = 0.0
        if hasattr(self, "_last_reservations_load_ts"):
            self._last_reservations_load_ts = 0.0
        if hasattr(self, "_last_users_load_ts"):
            self._last_users_load_ts = 0.0
        if hasattr(self, "_last_cashbox_data_ts"):
            self._last_cashbox_data_ts = 0.0
        if hasattr(self, "_last_dashboard_load_ts"):
            self._last_dashboard_load_ts = 0.0
        if hasattr(self, "_last_overdue_check_ts"):
            self._last_overdue_check_ts = 0.0

        # Forzar refresco de triggers reactivos
        if hasattr(self, "_cashbox_update_trigger"):
            self._cashbox_update_trigger += 1
        if hasattr(self, "_inventory_update_trigger"):
            self._inventory_update_trigger += 1
        if hasattr(self, "_purchase_update_trigger"):
            self._purchase_update_trigger += 1
        if hasattr(self, "_history_update_trigger"):
            self._history_update_trigger += 1
        if hasattr(self, "_report_update_trigger"):
            self._report_update_trigger += 1

        # Cargar solo datos comunes esenciales + datos del módulo activo
        if hasattr(self, "load_categories"):
            self.load_categories()
        if hasattr(self, "check_overdue_alerts"):
            self.check_overdue_alerts()

        current = getattr(self, "current_page", "")
        if current == "Dashboard" and hasattr(self, "load_dashboard"):
            self.load_dashboard()
        elif current == "Gestion de Caja":
            if hasattr(self, "_refresh_cashbox_caches"):
                self._refresh_cashbox_caches()
        elif current == "Historial" and hasattr(self, "reload_history"):
            self.reload_history()
        elif current == "Inventario":
            pass  # triggers reactivos ya invalidan
        elif current == "Compras" and hasattr(self, "load_suppliers"):
            self.load_suppliers()
        elif current == "Servicios":
            if hasattr(self, "load_reservations"):
                self.load_reservations()
            if hasattr(self, "load_field_prices"):
                self.load_field_prices()
        elif current == "Configuracion":
            if hasattr(self, "load_users"):
                self.load_users()
            if hasattr(self, "load_branches"):
                self.load_branches()
            if hasattr(self, "load_config_data"):
                self.load_config_data()
        elif current == "Clientes" and hasattr(self, "load_clients"):
            self.load_clients()
        elif current == "Cuentas Corrientes" and hasattr(self, "load_debtors"):
            import asyncio
            asyncio.ensure_future(self.load_debtors())

        # Reset paginación de caja
        if hasattr(self, "cashbox_current_page"):
            self.cashbox_current_page = 1
        if hasattr(self, "cashbox_log_current_page"):
            self.cashbox_log_current_page = 1
        if hasattr(self, "petty_cash_current_page"):
            self.petty_cash_current_page = 1
        if hasattr(self, "cashbox_filter_start_date"):
            self.cashbox_filter_start_date = ""
            self.cashbox_filter_end_date = ""
            self.cashbox_staged_start_date = ""
            self.cashbox_staged_end_date = ""
        if hasattr(self, "cashbox_log_filter_start_date"):
            self.cashbox_log_filter_start_date = ""
            self.cashbox_log_filter_end_date = ""
            self.cashbox_log_staged_start_date = ""
            self.cashbox_log_staged_end_date = ""
        return rx.toast("Sucursal actualizada.", duration=2000)

    @rx.event
    def login(self, form_data: dict):
        identifier = (
            form_data.get("email")
            or form_data.get("identifier")
            or form_data.get("username")
            or ""
        ).strip().lower()
        raw_password = form_data.get("password") or ""
        password = raw_password.encode("utf-8")

        client_ip = None
        router = getattr(self, "router", None)
        session_ctx = getattr(router, "session", None)
        if session_ctx is not None:
            for attr in ("client_ip", "client_host", "client_address"):
                value = getattr(session_ctx, attr, None)
                if value:
                    client_ip = value
                    break
        headers = getattr(router, "headers", None)
        if isinstance(headers, dict):
            client_ip = (
                headers.get("x-forwarded-for")
                or headers.get("X-Forwarded-For")
                or headers.get("x-real-ip")
                or client_ip
            )

        # Rate limiting: verificar si el usuario está bloqueado
        if _is_rate_limited(identifier, ip_address=client_ip):
            remaining = _remaining_lockout_time(identifier, ip_address=client_ip)
            self.error_message = (
                f"Demasiados intentos fallidos. Espere {remaining} minuto(s)."
            )
            logger.warning(
                "Login bloqueado por rate limit para usuario: %s",
                identifier[:20],  # No logear identificador completo por seguridad
            )
            return

        with rx.session() as session:
            admin_user = session.exec(
                select(UserModel)
                .where(UserModel.username == "admin")
                .execution_options(tenant_bypass=True)
            ).first()
            if admin_user and self.needs_initial_admin:
                self.needs_initial_admin = False

            if self.needs_initial_admin and not admin_user:
                env = self._resolve_env()
                initial_password = self._initial_admin_password()
                if not initial_password:
                    if env == "dev" and self._allow_default_admin():
                        initial_password = "admin"
                        logger.warning(
                            "WARNING: usando credenciales inseguras por defecto para desarrollo."
                        )
                    else:
                        self.error_message = (
                            "Sistema no inicializado. Configure INITIAL_ADMIN_PASSWORD."
                        )
                        return

                if identifier == "admin" and raw_password == initial_password:
                    # Crear superadmin asociado a un tenant válido.
                    company, branch = self._get_or_create_bootstrap_company_and_branch(
                        session
                    )
                    password_hash = bcrypt.hashpw(
                        password, bcrypt.gensalt()
                    ).decode()
                    role = self._get_role_by_name(
                        session,
                        "Superadmin",
                        company_id=company.id,
                    )
                    if not role:
                        role = self._ensure_role(
                            session,
                            "Superadmin",
                            self._normalize_privileges(SUPERADMIN_PRIVILEGES),
                            company_id=company.id,
                            overwrite=True,
                        )
                    must_change_password = env == "prod"
                    admin_user = UserModel(
                        username="admin",
                        password_hash=password_hash,
                        role_id=role.id,
                        company_id=company.id,
                        branch_id=branch.id,
                        must_change_password=must_change_password,
                    )
                    session.add(admin_user)
                    session.flush()
                    session.add(
                        UserBranch(user_id=admin_user.id, branch_id=branch.id)
                    )
                    session.commit()

                    _clear_login_attempts(identifier, ip_address=client_ip)
                    self.token = create_access_token(
                        admin_user.id,
                        token_version=getattr(admin_user, "token_version", 0),
                        company_id=getattr(admin_user, "company_id", None),
                    )
                    self.selected_branch_id = str(branch.id)
                    self.refresh_auth_runtime_cache()
                    if hasattr(self, "refresh_cashbox_status"):
                        self.refresh_cashbox_status()
                    self.error_message = ""
                    self.password_change_error = ""
                    self.needs_initial_admin = False
                    if must_change_password:
                        return rx.redirect("/cambiar-clave")
                    return rx.redirect("/ingreso")

                _record_failed_attempt(identifier, ip_address=client_ip)
                self.error_message = (
                    "Sistema no inicializado. Ingrese la contraseña inicial."
                )
                return

            user = None
            password_ok = False
            if "@" in identifier:
                user = session.exec(
                    select(UserModel)
                    .where(UserModel.email == identifier)
                    .execution_options(tenant_bypass=True)
                ).first()
                if user and bcrypt.checkpw(password, user.password_hash.encode("utf-8")):
                    password_ok = True
            else:
                users = session.exec(
                    select(UserModel)
                    .where(UserModel.username == identifier)
                    .execution_options(tenant_bypass=True)
                ).all()
                if users:
                    matches = [
                        candidate
                        for candidate in users
                        if bcrypt.checkpw(
                            password, candidate.password_hash.encode("utf-8")
                        )
                    ]
                    if len(matches) > 1:
                        self.error_message = (
                            "Hay mas de un usuario con ese nombre. Inicie sesion con su correo."
                        )
                        return
                    if len(matches) == 1:
                        user = matches[0]
                        password_ok = True

            if user and password_ok:
                if not user.is_active:
                    self.error_message = "Usuario inactivo. Contacte al administrador."
                    return
                if not user.role_id:
                    fallback_role = (
                        "Superadmin" if user.username == "admin" else "Usuario"
                    )
                    role = self._get_role_by_name(
                        session,
                        fallback_role,
                        company_id=getattr(user, "company_id", None),
                    )
                    if not role:
                        default_privileges = (
                            SUPERADMIN_PRIVILEGES
                            if fallback_role == "Superadmin"
                            else DEFAULT_USER_PRIVILEGES
                        )
                        role = self._ensure_role(
                            session,
                            fallback_role,
                            self._normalize_privileges(default_privileges),
                            company_id=getattr(user, "company_id", None),
                            overwrite=True,
                        )
                    user.role_id = role.id
                    session.add(user)
                    session.commit()

                # Login exitoso: limpiar intentos fallidos
                _clear_login_attempts(identifier, ip_address=client_ip)
                self.token = create_access_token(
                    user.id,
                    token_version=getattr(user, "token_version", 0),
                    company_id=getattr(user, "company_id", None),
                )
                branch_ids, branch_access_changed = self._ensure_user_branch_access(session, user)
                if branch_access_changed:
                    session.commit()
                selected_branch = self._select_default_branch(
                    session, user, branch_ids
                )
                self.selected_branch_id = (
                    str(selected_branch) if selected_branch else ""
                )
                self.refresh_auth_runtime_cache()
                if hasattr(self, "refresh_cashbox_status"):
                    self.refresh_cashbox_status()
                if hasattr(self, "load_settings"):
                    self.load_settings()
                if hasattr(self, "load_config_data"):
                    self.load_config_data()
                self.error_message = ""
                self.password_change_error = ""
                self._load_roles_cache(
                    session,
                    company_id=getattr(user, "company_id", None),
                )
                privileges = self._get_privileges_dict(user) or {}
                if getattr(user, "must_change_password", False):
                    return rx.redirect("/cambiar-clave")
                return rx.redirect(self._default_route_for_privileges(privileges))

        # Login fallido: registrar intento
        _record_failed_attempt(identifier, ip_address=client_ip)
        self.error_message = "Usuario o contraseña incorrectos."

    @rx.event
    def change_password(self, form_data: dict):
        if not self.is_authenticated:
            return rx.redirect("/ingreso")
        new_password = (form_data.get("password") or "").strip()
        confirm_password = (form_data.get("confirm_password") or "").strip()
        username = (self.current_user.get("username") or "").strip()
        user_id = self.current_user.get("id")
        company_id = self.current_user.get("company_id")
        if not company_id:
            self.password_change_error = "Empresa no definida."
            return
        set_tenant_context(company_id, None)

        is_valid, error = validate_password(new_password)
        if not is_valid:
            self.password_change_error = error
            return
        if username and new_password.lower() == username.lower():
            self.password_change_error = (
                "La contraseña no puede ser igual al usuario."
            )
            return
        if new_password != confirm_password:
            self.password_change_error = "Las contraseñas no coinciden."
            return

        with rx.session() as session:
            user = session.exec(
                select(UserModel)
                .where(UserModel.id == user_id)
                .where(UserModel.company_id == company_id)
            ).first()
            if not user:
                self.password_change_error = "Usuario no encontrado."
                return
            password_hash = bcrypt.hashpw(
                new_password.encode("utf-8"), bcrypt.gensalt()
            ).decode()
            user.password_hash = password_hash
            user.must_change_password = False
            user.token_version = (getattr(user, "token_version", 0) or 0) + 1
            session.add(user)
            session.commit()

        # Invalidar cache para forzar recarga con nuevos datos
        self.invalidate_user_cache()
        self.password_change_error = ""
        yield rx.toast("Contraseña actualizada.", duration=3000)
        yield rx.redirect(
            self._default_route_for_privileges(
                self.current_user["privileges"]
            )
        )

    @rx.event
    def logout(self):
        self.token = ""
        self.password_change_error = ""
        self.invalidate_user_cache()
        if hasattr(self, "cashbox_is_open_cached"):
            self.cashbox_is_open_cached = False
        return rx.redirect("/ingreso")

    @rx.event
    def show_create_user_form(self):
        if not self.current_user["privileges"].get("manage_users"):
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
        self._reset_new_user_form()
        self.user_form_key += 1
        self.show_user_form = True

    def _open_user_editor(self, user: User):
        merged_privileges = self._normalize_privileges(user.get("privileges", {}))
        role_key = self._find_role_key(user["role"]) or user["role"]

        # Asegurar que el rol exista en nuestro registro
        if role_key not in self.role_privileges:
            self.role_privileges[role_key] = merged_privileges.copy()
            if role_key not in self.roles:
                self.roles.append(role_key)

        self.new_user_data = {
            "username": user["username"],
            "email": (user.get("email") or ""),
            "password": "",
            "confirm_password": "",
            "role": role_key,
            "privileges": merged_privileges,
        }
        self.user_form_key += 1
        self.editing_user = user
        self.show_user_form_password = False
        self.show_user_form_confirm_password = False
        self.show_user_form = True

    @rx.event
    def show_edit_user_form(self, user: User):
        if not self.current_user["privileges"].get("manage_users"):
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
        self._open_user_editor(user)

    @rx.event
    def show_edit_user_form_by_username(self, username: str):
        if not self.current_user["privileges"].get("manage_users"):
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
        key = (username or "").strip().lower()
        company_id = self._company_id()
        if not company_id:
            return rx.toast("Empresa no definida.", duration=3000)
        # La edición de usuarios es a nivel empresa, no de sucursal.
        set_tenant_context(company_id, None)

        with rx.session() as session:
            user = session.exec(
                select(UserModel)
                .where(UserModel.username == key)
                .where(UserModel.company_id == company_id)
                .options(selectinload(UserModel.role).selectinload(Role.permissions))
                .execution_options(tenant_company_id=company_id)
            ).first()

            if not user:
                return rx.toast("Usuario a editar no encontrado.", duration=3000)

            # Convertir a dict
            role_name = user.role.name if user.role else "Sin rol"
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": getattr(user, "email", "") or "",
                "role": role_name,
                "privileges": self._get_privileges_dict(user),
                "company_id": getattr(user, "company_id", None),
                "must_change_password": bool(
                    getattr(user, "must_change_password", False)
                ),
            }
            self._open_user_editor(user_dict)

    @rx.event
    def set_user_form_open(self, is_open: bool):
        self.show_user_form = bool(is_open)
        if not is_open:
            self._reset_new_user_form()

    @rx.event
    def hide_user_form(self):
        self.show_user_form = False
        self._reset_new_user_form()

    @rx.event
    def close_user_limit_modal(self):
        self.show_user_limit_modal = False
        self.user_limit_modal_message = ""

    @rx.event
    def handle_new_user_change(self, field: str, value: str):
        if field == "role":
            self.new_user_data["role"] = value
            self.new_user_data["privileges"] = self._role_privileges(value)
            return
        if field == "username":
            self.new_user_data["username"] = value
            return
        if field == "email":
            self.new_user_data["email"] = value
            return
        self.new_user_data[field] = value

    @rx.event
    def toggle_privilege(self, privilege: str):
        privileges = self._normalize_privileges(self.new_user_data["privileges"])
        privileges[privilege] = not privileges[privilege]
        self.new_user_data["privileges"] = privileges

    @rx.event
    def apply_role_privileges(self):
        role = self.new_user_data.get("role") or "Usuario"
        self.new_user_data["privileges"] = self._role_privileges(role)

    @rx.event
    def update_new_role_name(self, value: str):
        self.new_role_name = value.strip()

    @rx.event
    def create_role_from_current_privileges(self):
        if not self.current_user["privileges"].get("manage_users"):
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
        name = (self.new_role_name or "").strip()
        if not name:
            return rx.toast("Ingrese un nombre para el rol nuevo.", duration=3000)
        if name.lower() == "superadmin":
            return rx.toast("Superadmin ya existe como rol principal.", duration=3000)
        existing = self._find_role_key(name)
        if existing:
            return rx.toast("Ese rol ya existe.", duration=3000)
        company_id = self._company_id()
        if not company_id:
            return rx.toast("Empresa no definida.", duration=3000)

        privileges = self._normalize_privileges(self.new_user_data["privileges"])
        set_tenant_context(company_id, None)
        with rx.session() as session:
            if self._get_role_by_name(session, name, company_id=company_id):
                return rx.toast("Ese rol ya existe.", duration=3000)
            self._ensure_role(
                session,
                name,
                privileges,
                company_id=company_id,
                overwrite=True,
            )
            session.commit()
            self._load_roles_cache(session, company_id=company_id)

        self.new_role_name = ""
        self.new_user_data["role"] = name
        self.new_user_data["privileges"] = privileges.copy()
        return rx.toast(f"Rol {name} creado con los privilegios actuales.", duration=3000)

    @rx.event
    def save_role_template(self):
        if not self.current_user["privileges"].get("manage_users"):
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
        role = (self.new_user_data.get("role") or "").strip()
        if not role:
            return rx.toast("Seleccione un rol para guardar sus privilegios.", duration=3000)
        if role.lower() == "superadmin":
            return rx.toast("No se puede modificar los privilegios de Superadmin.", duration=3000)
        company_id = self._company_id()
        if not company_id:
            return rx.toast("Empresa no definida.", duration=3000)

        privileges = self._normalize_privileges(self.new_user_data["privileges"])
        set_tenant_context(company_id, None)
        with rx.session() as session:
            self._ensure_role(
                session,
                role,
                privileges,
                company_id=company_id,
                overwrite=True,
            )
            session.commit()
            self._load_roles_cache(session, company_id=company_id)

        return rx.toast(f"Plantilla de rol {role} actualizada.", duration=3000)

    @rx.event
    def save_user(self):
        if not self.current_user["privileges"]["manage_users"]:
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
        block = self._require_active_subscription()
        if block:
            return block

        username = self.new_user_data["username"].lower().strip()
        if not username:
            return rx.toast("El nombre de usuario no puede estar vacío.", duration=3000)
        email = (self.new_user_data.get("email") or "").strip().lower()
        role_name = (self.new_user_data.get("role") or "").strip()
        if not role_name:
            return rx.toast("Debe asignar un rol al usuario.", duration=3000)
        company_id = self._company_id()
        if not company_id:
            return rx.toast("Empresa no definida.", duration=3000)
        branch_id = self._branch_id()
        if not branch_id:
            return rx.toast("Sucursal no definida.", duration=3000)
        if not self.editing_user and not email:
            return rx.toast("El correo es obligatorio.", duration=3000)
        if email and not validate_email(email):
            return rx.toast("Ingrese un correo valido.", duration=3000)

        self.new_user_data["privileges"] = self._normalize_privileges(
            self.new_user_data["privileges"]
        )

        # Gestión de usuarios: alcance por empresa (sin filtrar por sucursal actual).
        set_tenant_context(company_id, None)
        with rx.session() as session:
            role = self._get_role_by_name(
                session,
                role_name,
                company_id=company_id,
            )
            # CASO 1: El rol no existe -> Lo creamos nuevo con los permisos del form
            if not role:
                role = self._ensure_role(
                    session,
                    role_name,
                    self.new_user_data["privileges"],
                    company_id=company_id,
                    overwrite=True,
                )
            # CASO 2: El rol YA existe y NO es Superadmin -> Actualizamos sus permisos
            # Esto permite redefinir qué puede hacer un 'Cajero' o 'Admin' desde la UI
            elif role.name != "Superadmin":
                role = self._ensure_role(
                    session,
                    role_name,
                    self.new_user_data["privileges"],
                    company_id=company_id,
                    overwrite=True, # <--- La clave: fuerza la actualización en la DB
                )
            if not self.editing_user:
                company = session.exec(
                    select(Company).where(Company.id == company_id)
                ).first()
                if not company:
                    return rx.toast("Empresa no definida.", duration=3000)
                max_users_raw = getattr(company, "max_users", None)
                try:
                    max_users = int(max_users_raw)
                except (TypeError, ValueError):
                    max_users = None
                if max_users is not None and max_users >= 0:
                    current_count = session.exec(
                        select(func.count(UserModel.id))
                        .where(UserModel.company_id == company_id)
                        .where(UserModel.is_active == True)
                    ).one()
                    if int(current_count or 0) >= max_users:
                        plan_type = getattr(company, "plan_type", "")
                        if hasattr(plan_type, "value"):
                            plan_type = plan_type.value
                        plan_label = str(plan_type or "").strip() or "desconocido"
                        self.user_limit_modal_message = (
                            f"Límite alcanzado. Tu plan {plan_label} "
                            f"solo permite {max_users} usuarios."
                        )
                        self.show_user_limit_modal = True
                        return
            if self.editing_user:
                # Actualizar usuario existente
                user_to_update = session.exec(
                    select(UserModel)
                    .where(UserModel.username == self.editing_user["username"])
                    .where(UserModel.company_id == company_id)
                ).first()

                if not user_to_update:
                    return rx.toast("Usuario a editar no encontrado.", duration=3000)
                if email:
                    existing_email = session.exec(
                        select(UserModel).where(UserModel.email == email)
                    ).first()
                    if existing_email and existing_email.id != user_to_update.id:
                        return rx.toast("El correo ya esta registrado.", duration=3000)
                    user_to_update.email = email

                if self.new_user_data["password"]:
                    password = self.new_user_data["password"]
                    is_valid, error = validate_password(password)
                    if not is_valid:
                        return rx.toast(error, duration=3000)
                    if password.lower() == username:
                        return rx.toast(
                            "La contraseña no puede ser igual al usuario.",
                            duration=3000,
                        )
                    if password != self.new_user_data["confirm_password"]:
                        return rx.toast(
                            "Las contraseñas no coinciden.", duration=3000
                        )
                    password_hash = bcrypt.hashpw(
                        password.encode(), bcrypt.gensalt()
                    ).decode()
                    user_to_update.password_hash = password_hash
                    user_to_update.token_version = (
                        getattr(user_to_update, "token_version", 0) or 0
                    ) + 1

                user_to_update.role_id = role.id

                session.add(user_to_update)
                session.commit()
                self._load_roles_cache(session, company_id=company_id)

                self.hide_user_form()
                self.load_users()
                return rx.toast(f"Usuario {username} actualizado.", duration=3000)
            else:
                # Crear nuevo usuario
                existing_user = session.exec(
                    select(UserModel)
                    .where(UserModel.username == username)
                    .where(UserModel.company_id == company_id)
                ).first()

                if existing_user:
                    return rx.toast("El nombre de usuario ya existe.", duration=3000)
                existing_email = session.exec(
                    select(UserModel).where(UserModel.email == email)
                ).first()
                if existing_email:
                    return rx.toast("El correo ya esta registrado.", duration=3000)
                password = self.new_user_data["password"]
                if not password:
                    return rx.toast(
                        "La contraseña no puede estar vacía.", duration=3000
                    )
                is_valid, error = validate_password(password)
                if not is_valid:
                    return rx.toast(error, duration=3000)
                if password.lower() == username:
                    return rx.toast(
                        "La contraseña no puede ser igual al usuario.",
                        duration=3000,
                    )
                if password != self.new_user_data["confirm_password"]:
                    return rx.toast("Las contraseñas no coinciden.", duration=3000)

                password_hash = bcrypt.hashpw(
                    password.encode(), bcrypt.gensalt()
                ).decode()

                new_user = UserModel(
                    username=username,
                    email=email or None,
                    password_hash=password_hash,
                    role_id=role.id,
                    company_id=company_id,
                    branch_id=branch_id,
                )
                session.add(new_user)
                session.flush()
                session.add(
                    UserBranch(user_id=new_user.id, branch_id=branch_id)
                )
                session.commit()
                self._load_roles_cache(session, company_id=company_id)

                self.hide_user_form()
                self.load_users()
                return rx.toast(f"Usuario {username} creado.", duration=3000)

    @rx.event
    def delete_user(self, username: str):
        if not self.current_user["privileges"]["manage_users"]:
            return rx.toast("No tiene permisos para eliminar usuarios.", duration=3000)
        block = self._require_active_subscription()
        if block:
            return block
        if username == self.current_user["username"]:
            return rx.toast("No puedes eliminar tu propio usuario.", duration=3000)
        company_id = self._company_id()
        if not company_id:
            return rx.toast("Empresa no definida.", duration=3000)

        # Eliminación de usuarios: alcance por empresa (sin filtrar por sucursal actual).
        set_tenant_context(company_id, None)
        with rx.session() as session:
            user = session.exec(
                select(UserModel)
                .where(UserModel.username == username)
                .where(UserModel.company_id == company_id)
                .options(selectinload(UserModel.role))
                .execution_options(tenant_company_id=company_id)
            ).first()

            if not user:
                return rx.toast(f"Usuario {username} no encontrado.", duration=3000)
            role_name = (user.role.name if user.role else "").strip().lower()
            if role_name == "superadmin":
                return rx.toast("No se puede eliminar al superadmin.", duration=3000)
            session.delete(user)
            session.commit()
            self.load_users()
            return rx.toast(f"Usuario {username} eliminado.", duration=3000)

        return rx.toast(f"Usuario {username} no encontrado.", duration=3000)
