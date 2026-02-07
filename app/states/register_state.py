import uuid
from datetime import datetime, timedelta

import bcrypt
import reflex as rx
from sqlmodel import select

from app.models import Branch, Role, User as UserModel, UserBranch, CompanySettings
from app.models.company import Company, PlanType
from app.utils.auth import create_access_token
from app.utils.db_seeds import seed_new_branch_data
from app.utils.validators import validate_email, validate_password
from app.utils.sanitization import sanitize_name, sanitize_phone
from app.utils.rate_limit import (
    is_rate_limited as _is_rate_limited,
    record_failed_attempt as _record_failed_attempt,
    clear_login_attempts as _clear_login_attempts,
    remaining_lockout_time as _remaining_lockout_time,
)
from .auth_state import ADMIN_PRIVILEGES
from .mixin_state import MixinState


class RegisterState(MixinState):
    register_error: str = ""
    is_registering: bool = False

    @rx.event
    def handle_registration(self, form_data: dict):
        self.register_error = ""
        self.is_registering = True
        yield

        company_name = sanitize_name(form_data.get("company_name") or "").strip()
        username = sanitize_name(form_data.get("username") or "").strip().lower()
        email = (form_data.get("email") or "").strip().lower()
        contact_phone = sanitize_phone(form_data.get("contact_phone") or "").strip()
        password = form_data.get("password") or ""
        confirm_password = form_data.get("confirm_password") or ""

        identifier = email or username
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

        if _is_rate_limited(identifier, ip_address=client_ip):
            remaining = _remaining_lockout_time(identifier, ip_address=client_ip)
            self.register_error = (
                f"Demasiados intentos. Espere {remaining} minuto(s) para registrar."
            )
            self.is_registering = False
            return

        if not company_name:
            self.register_error = "El nombre de la empresa es obligatorio."
            self.is_registering = False
            return
        if not username:
            self.register_error = "El usuario es obligatorio."
            self.is_registering = False
            return
        if not email or not validate_email(email):
            self.register_error = "Ingrese un correo valido."
            self.is_registering = False
            return
        if not contact_phone:
            self.register_error = "El numero de contacto es obligatorio."
            self.is_registering = False
            return
        if password != confirm_password:
            self.register_error = "Las contrasenas no coinciden."
            self.is_registering = False
            return

        is_valid, error = validate_password(password)
        if not is_valid:
            self.register_error = error
            self.is_registering = False
            return

        company_id = None
        branch_id = None
        user_id = None
        token_version = 0
        with rx.session() as session:
            try:
                existing_email = session.exec(
                    select(UserModel)
                    .where(UserModel.email == email)
                    .execution_options(tenant_bypass=True)
                ).first()
                if existing_email:
                    self.register_error = "El correo ya esta registrado."
                    self.is_registering = False
                    _record_failed_attempt(identifier, ip_address=client_ip)
                    return

                role = None
                if hasattr(self, "_get_role_by_name"):
                    role = self._get_role_by_name(session, "Administrador")
                if not role:
                    if hasattr(self, "_ensure_role") and hasattr(self, "_normalize_privileges"):
                        role = self._ensure_role(
                            session,
                            "Administrador",
                            self._normalize_privileges(ADMIN_PRIVILEGES),
                            overwrite=True,
                        )
                    else:
                        role = session.exec(
                            select(Role).where(Role.name == "Administrador")
                        ).first()
                if not role:
                    self.register_error = "No se pudo crear el rol administrador."
                    self.is_registering = False
                    _record_failed_attempt(identifier, ip_address=client_ip)
                    return

                now = datetime.now()
                ruc_placeholder = f"TEMP{uuid.uuid4().hex[:11]}"
                company = Company(
                    name=company_name,
                    ruc=ruc_placeholder,
                    is_active=True,
                    trial_ends_at=now + timedelta(days=15),
                    created_at=now,
                    plan_type=PlanType.TRIAL,
                    max_branches=2,
                    max_users=3,
                    has_reservations_module=True,
                    has_electronic_billing=False,
                )
                session.add(company)
                session.flush()

                branch = Branch(
                    company_id=company.id,
                    name="Casa Matriz",
                    address="",
                )
                session.add(branch)
                session.flush()

                session.add(
                    CompanySettings(
                        company_id=company.id,
                        branch_id=branch.id,
                        company_name=company_name,
                        ruc=ruc_placeholder,
                        address="",
                        phone=contact_phone,
                    )
                )

                password_hash = bcrypt.hashpw(
                    password.encode("utf-8"), bcrypt.gensalt()
                ).decode()
                user = UserModel(
                    username=username,
                    email=email,
                    password_hash=password_hash,
                    role_id=role.id,
                    company_id=company.id,
                    branch_id=branch.id,
                )
                session.add(user)
                session.flush()

                company_id = company.id
                branch_id = branch.id
                user_id = user.id
                token_version = getattr(user, "token_version", 0)

                session.add(UserBranch(user_id=user.id, branch_id=branch.id))
                seed_new_branch_data(session, company_id, branch.id)

                session.commit()
            except Exception:
                session.rollback()
                self.register_error = "No se pudo completar el registro."
                self.is_registering = False
                _record_failed_attempt(identifier, ip_address=client_ip)
                return

        if not user_id or not company_id or not branch_id:
            self.register_error = "No se pudo completar el registro."
            self.is_registering = False
            _record_failed_attempt(identifier, ip_address=client_ip)
            return

        self.token = create_access_token(
            user_id,
            token_version=token_version,
            company_id=company_id,
        )
        _clear_login_attempts(identifier, ip_address=client_ip)
        if hasattr(self, "selected_branch_id"):
            self.selected_branch_id = str(branch_id)
        self.is_registering = False
        return rx.redirect("/dashboard")
